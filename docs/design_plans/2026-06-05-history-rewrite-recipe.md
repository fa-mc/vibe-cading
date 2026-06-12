# Git-History Leak-Expunge Recipe — `fa-mc/vibe-cading` (pre-public-flip)

**Authored:** 2026-06-05 by Admin (read-only survey + authoring; no rewrite run).
**Status:** READY TO RUN by the human maintainer. Admin executed nothing destructive.
**VALIDATED 2026-06-05** via a non-destructive dry run (`tmp/run_rewrite_validation.sh`)
on a throwaway clone — the combined `filter-repo` command ran clean and all four
verification gates passed: removed-files-gone, zero leak strings across all history,
false-positive guards intact, and the DEFINITIVE check that the rewritten tip tree is
byte-identical to the current public tip `a017734` (zero live-content change). The dry
run also caught + fixed two bugs now reflected below — see §0d.
**Goal:** Remove private-strategy leak strings from the OLD commit history of
`fa-mc/vibe-cading` before flipping the repo PUBLIC. The working-tree scrub
already merged (PR #28, `main` = `a017734`); only HISTORY still carries the strings.

> ⚠️ **This file and `history-rewrite-expressions.txt` CONTAIN the leak strings.**
> Both live under `.agents/` which is git-ignored. Confirmed before authoring:
> `git check-ignore` returns both paths; `git status --porcelain` shows them
> neither staged nor tracked. **Never `git add` either file.** Delete both after
> the rewrite is done and verified.

---

## 0. Survey result — the exact leak surface (read-only, already done)

### 0a. Leak strings confirmed present in history

| Leak string | All-refs commits touching it | Where (historical files) |
|---|---|---|
| `vibe-cading-platform` | 14 | TODO.md, todo.md, docs/business-strategy.md, docs/{archive/,}mcp-integration-plan.md, docs/knowledge_base/mcp_architecture_rules.md, .agents/plans/2026-05-13-pre-oss-models-structure_{design,req}.md, .agents/plans/INDEX.md |
| `new SaaS strategy` | 4 | TODO.md |
| `query_engine_api` | 4 | CONTRIBUTING.md, .github/workflows/engine-api.yml (historical versions; scrubbed on main) |
| `HE Phase 1` | 5 | TODO.md, todo.md |
| `private platform worker` | 6 | TODO.md, TODO_ARCHIVE.md |
| `the platform team` | 8 | todo.md, .agents/plans/2026-05-13-pre-oss-models-structure_design.md |
| `FastAPI SSE` | 3 | todo.md |
| `Docker sandbox` | 4 | todo.md, docs/archive/mcp-integration-plan.md, docs/knowledge_base/mcp_architecture_rules.md |
| `/tmp/vibe-cading-prepurge-backup.git` | 3 | todo.md |
| `vibe-cading-prepurge` | 3 | todo.md |
| `business-strategy.md` (as a referenced path string) | 5 | todo.md |
| `mcp-integration-plan.md` (path string) | 5 | todo.md |
| `mcp_architecture_rules.md` (path string) | 5 | todo.md |

`Open Core Engine` — **0 hits**, not present in history (drop from the candidate set).

Verbatim high-value TODO.md leak line (commit `bf43f6c~1`, line 129):
> `Based on the new SaaS strategy, this repository (`vibe-cading`) will act as the public core engine for the `vibe-cading-platform`. We need to prepare it for external consumption:`

### 0b. False-positive guards — these MUST survive (NOT redacted)

- **`SaaS loophole` / closed-source `SaaS`** in `LICENSE-FAQ.md` (and the
  TODO.md "DONE" note) — legitimate AGPLv3 §13 wording. The redaction targets
  the *distinct* phrase `new SaaS strategy`, which never overlaps it.
- **`Phase 1` / `Phase 1-7`** refactor-tracking text in `tests/`, `tools/`,
  `TODO.md` — benign. The redaction targets the *distinct* phrase `HE Phase 1`.
- **`engine_api` / `engine_api.json`** — shipped OSS feature (PR #26), present
  on current main and intentionally kept. Redaction targets only the *distinct*
  historical variant `query_engine_api`.

All redaction literals were verified **absent from current `main` (HEAD)** —
so `--replace-text` corrupts no live/tracked file.

### 0c. Targeting plan: `--invert-paths` (whole-file deletion) vs `--replace-text`

**Wholesale historical removal via `--invert-paths`** — every path below is
absent from `main`'s tip tree but reachable in history; safe to remove entirely:

```
todo.md
TODO_ARCHIVE.md
docs/business-strategy.md
docs/mcp-integration-plan.md
docs/archive/mcp-integration-plan.md          # same doc, post-move path — target BOTH
docs/knowledge_base/mcp_architecture_rules.md
.agents/plans/2026-05-13-pre-oss-models-structure_design.md
.agents/plans/2026-05-13-pre-oss-models-structure_req.md
.agents/plans/INDEX.md
```

> **Correction to the prior assumption:** the three docs
> (`business-strategy.md`, `mcp-integration-plan.md`, `mcp_architecture_rules.md`)
> were assumed already gone from history by a prior purge. They are **NOT** —
> their blobs are still reachable (e.g. in commit tree `2e34b8b`), only removed
> from `main`'s *tip*. They DO need `--invert-paths` targeting.

> **Do NOT `--invert-paths` the tracked `.agents/plans/*.svg` visual contracts** —
> those 9 files are intentional OSS deliverables and contain no leaks. Only the
> three leaky `.agents/plans/*.md` files above are targeted.

**In-place redaction via `--replace-text`** — for the survivor `TODO.md` (kept
on main, but its historical revisions carry `vibe-cading-platform`,
`new SaaS strategy`, `HE Phase 1`, `private platform worker`) and as
defense-in-depth across any other retained blob. Driven by
`.agents/plans/history-rewrite-expressions.txt`.

### 0d. Two bugs the dry run caught (already fixed in the expressions file)

The validation run (`tmp/run_rewrite_validation.sh`) surfaced two issues that
would have **corrupted live files** had the recipe been run as first drafted.
Both are fixed; documented here so they are not reintroduced:

1. **Expressions file MUST be rules-only — NO `#` comment lines.** This
   `git-filter-repo` build parses `#`-prefixed lines in a `--replace-text` file
   as replacement *rules*, not comments. The original expressions file had a
   `#` documentation header, which caused filter-repo to replace **every `#`
   comment marker in the entire repo** with `***REMOVED***` (e.g.
   `.devcontainer/Dockerfile`'s `# Install …` → `***REMOVED*** Install …`). The
   expressions file is now stripped to bare `literal:…==>…` lines only; ALL
   documentation lives here in the recipe instead. **Never add a `#` line to the
   expressions file.**
2. **Use the full phrase `HE Phase 1 effort`, not bare `HE Phase 1`.**
   `filter-repo` literal matching is substring-based and ignores word
   boundaries, so `HE Phase 1` matches inside `t`**`HE Phase 1`**`-7 refactor`
   (a benign comment in `tests/test_protocols.py`). The expressions file uses
   the distinctive full phrase `HE Phase 1 effort==>***REMOVED*** effort`, which
   cannot collide with the Phase-1-7 text. (The same lesson applies to any
   verification grep — match the specific phrase, not the bare token.)

> Re-validate after ANY edit to the expressions file: `bash tmp/run_rewrite_validation.sh`
> (non-destructive; must end `VALIDATION PASSED` with the tree-diff at 0 lines).

---

## 1. Preconditions (verify before starting)

1. **Origin backup branch exists** (the recoverability net):
   `backup/pre-history-scrub-2026-06-05` → `a017734` on `origin`.
   Verify: `git ls-remote --heads origin backup/pre-history-scrub-2026-06-05`
   (already confirmed present).
2. **No open PRs.** `gh pr list --repo fa-mc/vibe-cading --state open` returns
   empty (confirmed 2026-06-05). A force-push mid-review would invalidate review
   state — do not run the rewrite while any PR is open.
3. **Run on your own machine**, with push rights to `git@github.com:fa-mc/vibe-cading.git`.
4. **`git filter-repo` installed.** It is **not** currently on PATH in the
   devcontainer — install it first (Step 2.0 below).
5. **Repo stays PRIVATE** until post-rewrite verification AND the backup-branch
   teardown (Step 4) AND the GitHub-retention decision (Step 5) are all resolved.

---

## 2. Step-by-step commands (copy-pasteable)

> Replace `~/vibe-rewrite` / `~/vibe-mirror-backup.git` with paths you prefer,
> all OUTSIDE the working dev clone.

### 2.0 — Install `git filter-repo`

```bash
pip3 install --user git-filter-repo
# confirm:
git filter-repo --version    # should print a version, e.g. 2.47.0
# if 'git filter-repo' is not found, ensure ~/.local/bin is on PATH, or use:
#   python3 -m git_filter_repo --version
```

### 2.1 — SECOND independent off-machine backup (belt-and-suspenders)

Beyond the `origin` backup branch, take a full mirror to a path OUTSIDE the repo:

```bash
git clone --mirror git@github.com:fa-mc/vibe-cading.git ~/vibe-mirror-backup.git
# this captures ALL refs (branches, tags, and notably refs/pull/* are NOT in a
# normal mirror — but every branch + tag is). Keep it untouched until launch is done.
ls -la ~/vibe-mirror-backup.git    # sanity: it exists and is non-empty
```

### 2.2 — Fresh clone for the rewrite (filter-repo refuses a non-fresh clone)

```bash
git clone git@github.com:fa-mc/vibe-cading.git ~/vibe-rewrite
cd ~/vibe-rewrite
git log --oneline -1            # expect: a017734 docs: scrub private-strategy leakage ...
```

> ⚠️ **Corrected after validation:** this `filter-repo` build converts
> remote-tracking refs (incl. `origin/backup/pre-history-scrub-2026-06-05`) into
> local branches and **rewrites them too** — so the clone's *local* backup
> branch ends up pointing at the rewritten tip. That is harmless **only if you
> push exactly `main` and nothing else.** The recoverability net is the
> **origin** backup branch (still at the original `a017734`) plus the offline
> mirror — both untouched as long as you never push the backup branch.
> **Therefore: push ONLY `main` (Step 2.6). Never `git push --all` / `--mirror`
> / the backup branch** — doing so would overwrite the origin backup's original
> history with rewritten history and destroy the net. (`refs/pull/*` are not
> fetched by a normal clone.)

### 2.3 — Copy the expressions file into the rewrite clone

The expressions file lives in the dev clone under `.agents/plans/` (git-ignored).
Copy it next to the rewrite clone (NOT into its tracked tree):

```bash
cp /workspaces/vibe-cading/.agents/plans/history-rewrite-expressions.txt ~/history-rewrite-expressions.txt
```

### 2.4 — Run the rewrite

`git filter-repo` accepts `--invert-paths` (with `--path`/`--path-glob`) and
`--replace-text` **in the same invocation**. Single combined run:

```bash
cd ~/vibe-rewrite
git filter-repo \
  --invert-paths \
  --path todo.md \
  --path TODO_ARCHIVE.md \
  --path docs/business-strategy.md \
  --path docs/mcp-integration-plan.md \
  --path docs/archive/mcp-integration-plan.md \
  --path docs/knowledge_base/mcp_architecture_rules.md \
  --path '.agents/plans/2026-05-13-pre-oss-models-structure_design.md' \
  --path '.agents/plans/2026-05-13-pre-oss-models-structure_req.md' \
  --path '.agents/plans/INDEX.md' \
  --replace-text ~/history-rewrite-expressions.txt
```

> **If your filter-repo version rejects combining the two passes** (older builds
> can), run them sequentially — `--invert-paths` first, then `--replace-text`:
> ```bash
> git filter-repo --invert-paths \
>   --path todo.md --path TODO_ARCHIVE.md \
>   --path docs/business-strategy.md --path docs/mcp-integration-plan.md \
>   --path docs/archive/mcp-integration-plan.md \
>   --path docs/knowledge_base/mcp_architecture_rules.md \
>   --path '.agents/plans/2026-05-13-pre-oss-models-structure_design.md' \
>   --path '.agents/plans/2026-05-13-pre-oss-models-structure_req.md' \
>   --path '.agents/plans/INDEX.md'
> git filter-repo --replace-text ~/history-rewrite-expressions.txt --force
> ```
> (The second run needs `--force` because the repo is no longer a pristine clone
> after the first pass.)

filter-repo automatically removes the `origin` remote after a successful run
(its standard safety behavior). Re-add it before pushing (Step 2.6).

### 2.5 — Local verification BEFORE pushing (the validated gate)

> The canonical, already-passing version of these checks is
> `tmp/run_rewrite_validation.sh` (it does its own throwaway clone + rewrite +
> all four gates). The commands below are the same gates run in-place in
> `~/vibe-rewrite`; the DEFINITIVE one is the tree-diff (d).

```bash
cd ~/vibe-rewrite
git log --oneline -1                       # main tip is now a NEW sha (rewritten)

# re-add origin + fetch the CURRENT public tip (read-only) so we can tree-diff:
git remote add origin git@github.com:fa-mc/vibe-cading.git 2>/dev/null || true
git fetch origin main                      # origin/main should be a017734

# (a) wholesale-removed files gone from ALL history — expect EMPTY:
git log --all --oneline -- todo.md TODO_ARCHIVE.md \
  docs/business-strategy.md docs/mcp-integration-plan.md \
  docs/archive/mcp-integration-plan.md docs/knowledge_base/mcp_architecture_rules.md \
  '.agents/plans/2026-05-13-pre-oss-models-structure_design.md' \
  '.agents/plans/2026-05-13-pre-oss-models-structure_req.md' \
  '.agents/plans/INDEX.md'

# (b) no leak string in any blob across ALL history — expect EMPTY.
#     NOTE: 'HE Phase 1 effort' (full phrase), NOT bare 'HE Phase 1' (see §0d):
git grep -niE 'vibe-cading-platform|new SaaS strategy|query_engine_api|HE Phase 1 effort|private platform worker|the platform team|FastAPI SSE|Docker sandbox|vibe-cading-prepurge' $(git rev-list --all)

# (d) DEFINITIVE — rewritten tip tree must be byte-identical to the current
#     public tip a017734 (the rewrite changes history ONLY, never live content):
git diff --stat origin/main HEAD          # expect: EMPTY (zero lines)
```

Only proceed to push if (a) and (b) are empty AND (d) shows zero diff.

### 2.6 — HUMAN RUNS THIS — publish the rewritten history

> **🔴 HUMAN RUNS THIS — Force-Push Policy clause 1.** This is the single step
> Admin/agents must NOT run: it force-rewrites `origin/main`, the stable base
> branch. Clause 1 is absolute (never force-push `main`, no override) — so this
> exact command is reserved for the human maintainer, who is consciously
> accepting the history rewrite ahead of the public flip. Every other step above
> is non-destructive (clones, local rewrite, grep).

```bash
cd ~/vibe-rewrite
git remote add origin git@github.com:fa-mc/vibe-cading.git   # filter-repo removed it
git push --force-with-lease origin main
```

`--force-with-lease` guards against clobbering an unexpected concurrent push.
(If lease fails because the local clone has no remote-tracking ref for the new
tip, fetch first: `git fetch origin main`, re-verify origin still equals
`a017734`, then retry. Use bare `--force` only if you have confirmed origin/main
is exactly `a017734` and no collaborator has pushed.)

After pushing, re-clone fresh and re-run Step 3 grep against the AS-SHIPPED
origin to confirm what consumers will actually get:

```bash
git clone git@github.com:fa-mc/vibe-cading.git ~/vibe-verify && cd ~/vibe-verify
git grep -niE 'vibe-cading-platform|new SaaS strategy|query_engine_api|HE Phase 1 effort|private platform worker|the platform team|FastAPI SSE|Docker sandbox|vibe-cading-prepurge' $(git rev-list --all)   # expect EMPTY
```

---

## 3. Post-rewrite verification (must be clean before any public flip)

Run in a **fresh clone** of the rewritten origin (`~/vibe-verify` above):

```bash
cd ~/vibe-verify

# (a) the wholesale-removed files are gone from ALL history:
git log --all --oneline -- \
  todo.md TODO_ARCHIVE.md \
  docs/business-strategy.md docs/mcp-integration-plan.md \
  docs/archive/mcp-integration-plan.md \
  docs/knowledge_base/mcp_architecture_rules.md \
  '.agents/plans/2026-05-13-pre-oss-models-structure_design.md' \
  '.agents/plans/2026-05-13-pre-oss-models-structure_req.md' \
  '.agents/plans/INDEX.md'
# EXPECT: empty output.

# (b) no leak string survives in any blob across all history:
git grep -niE \
  'vibe-cading-platform|new SaaS strategy|query_engine_api|HE Phase 1 effort|private platform worker|the platform team|FastAPI SSE|Docker sandbox|vibe-cading-prepurge' \
  $(git rev-list --all)
# EXPECT: empty output.

# (c) the false-positive guards STILL EXIST (we did not over-redact):
git grep -nI 'SaaS loophole' main -- LICENSE-FAQ.md     # EXPECT: present
git grep -nI 'Phase 1-7' main                            # EXPECT: present (tests/test_protocols.py)
git grep -nI 'engine_api' main -- CONTRIBUTING.md        # EXPECT: present (the live OSS feature)

# (d) the build still works on the rewritten main (sanity, optional but recommended):
python3 -m pytest -q   ||  echo "investigate before flipping public"
```

If any of (a) or (b) is non-empty, STOP — do not flip public; investigate
(likely a missed path variant or a leak string not in the expressions file).

---

## 4. Backup-branch teardown — HARD GATE on the public flip

The `backup/pre-history-scrub-2026-06-05` branch on origin points at the
**un-rewritten** tip `a017734` — it preserves the full pre-rewrite leak history.
It MUST be deleted from origin **before** the repo goes public, otherwise the
rewrite is pointless (the leaks remain one branch-name away).

> Keep your local `~/vibe-mirror-backup.git` (Step 2.1) as the offline net so
> you are not relying on the origin branch for recoverability.

```bash
# delete the backup branch from origin (HARD GATE — do this before public flip):
git push origin --delete backup/pre-history-scrub-2026-06-05

# delete any local copy if one exists:
git branch -D backup/pre-history-scrub-2026-06-05 2>/dev/null || true

# confirm it is gone from origin:
git ls-remote --heads origin backup/pre-history-scrub-2026-06-05   # EXPECT: empty
```

> This is a deliberate destructive deletion of an *unmerged* recoverability
> branch (Branch-Deletion Policy clause 2 — confirm-first). It is correct here
> because (1) the human is running it knowingly as the launch gate, and (2) the
> offline mirror backup is the retained safety net. **Do not delete it until
> Step 3 verification is fully clean.**

---

## 5. HONEST GitHub-retention caveats — read before trusting the public flip

**A force-push does NOT immediately purge the old commits from GitHub.** This is
the single most important thing to understand. After Step 2.6, the rewritten
`main` is live, but the OLD leak commits remain on GitHub's servers and stay
**reachable** in three ways until GitHub garbage-collects (which it does **not**
do on any published schedule, and not at all while a ref keeps them reachable):

1. **By direct SHA.** Anyone who knows or guesses an old commit hash can fetch
   it via `https://github.com/fa-mc/vibe-cading/commit/<sha>` — e.g. the
   leak-introducing commits `0a7a562` (business-strategy), `b842160` (mcp
   archive), `c732e78`/`59af178` (TODO_ARCHIVE move), `7432c34`/`78d119b`. These
   remain resolvable after the rewrite until GC.

2. **Via `refs/pull/*` PR refs.** Every merged/closed PR keeps a permanent
   `refs/pull/<n>/head` (and `/merge`) ref that GitHub does **not** rewrite when
   you force-push a branch. The pre-scrub leak blobs are pinned by:
   - **PR #28** ("scrub private-strategy leakage…") — its own head/merge refs
     contain the *pre-scrub* TODO.md / todo.md / TODO_ARCHIVE.md (the scrub's
     "before" state) — the richest leak snapshot of all.
   - **Earlier merged PRs** that carried the leak files into history (the
     business-strategy / mcp-archive / TODO_ARCHIVE / ToleranceProfile-refactor
     work). Note many leak commits (`0a7a562`, `b842160`, `c732e78`, `7432c34`)
     are **NOT ancestors of `main`** — they live ONLY on these PR refs /
     orphaned branches, so filter-repo on a normal clone never even sees them.
     **Deleting branches and force-pushing main does not remove PR refs.**

3. **Search-index / cache lag.** GitHub code search and any third-party mirror
   (e.g. someone who already cloned) can retain copies independently.

### What actually guarantees expunging — pick one (human decides)

| Option | Effort | Guarantee | Notes |
|---|---|---|---|
| **A. Force-push + delete backup branch, keep PRIVATE, then contact GitHub Support** to GC unreachable objects (and to confirm PR-ref handling). | Low + a support round-trip | High *after Support confirms GC* | Only Support can force GC of unreachable objects; they can also advise on `refs/pull/*`. Do NOT flip public until they confirm. |
| **B. Publish from a fresh history-less repository** — create a brand-new repo, push a single squashed "Initial public release" commit of the current `main` tree (`a017734` working tree, leak-free), and make THAT repo public. Archive/keep-private the old repo. | Medium | **Highest** — the public repo has zero leak history, zero PR refs to old commits. | Loses public commit history & blame; acceptable for an OSS launch where pre-launch history isn't a selling point. PR/issue numbers reset. |
| **C. Force-push only, flip public immediately.** | Lowest | **Low / not guaranteed** | Old commits remain SHA- and PR-ref-reachable until GitHub GCs on its own undocumented timeline. **Not recommended for a clean launch.** |

### Mitigation while you decide

**Keeping the repo PRIVATE until GC/confirmation is the primary mitigation** —
exposure is bounded to existing collaborators while old objects are still
reachable. Do not flip public on the strength of the force-push alone.

### Recommendation (human's call)

For a *clean public launch with the strongest guarantee*, **Option B (publish
from a fresh history-less repo)** is the safest — it structurally cannot leak
old history or PR refs, at the cost of losing pre-launch commit history. If
preserving commit history/blame matters, use **Option A** (rewrite + private +
GitHub Support GC confirmation) and flip public only after Support confirms the
unreachable objects and PR refs are purged. **Option C alone is not sufficient**
for a confident leak-free public launch.

---

## 5A. Option A — chosen path: execution order + GitHub Support request

> **User decision 2026-06-05:** Option A (rewrite + keep PRIVATE + GitHub
> Support GC), prep-now / execute-later. This section is the turnkey ordering
> for Option A specifically. Everything non-destructive is already prepared
> (recipe + expressions file). You run the destructive/launch steps when ready.

### Execution order (do NOT flip public until the last gate)

1. **§2.0** install `git filter-repo`.
2. **§2.1** off-machine mirror backup (`~/vibe-mirror-backup.git`).
3. **§2.2–2.5** fresh clone → run the rewrite → local verification.
4. **§2.6** 🔴 **you** force-push the rewritten `main` (clause-1 step).
5. **§3** post-rewrite verification in a fresh clone — must be fully clean.
6. **§4** delete the `backup/pre-history-scrub-2026-06-05` branch from origin
   (HARD GATE; keep the offline mirror).
7. **§5A** send the GitHub Support request below. **Repo stays PRIVATE.**
8. **Wait** for Support to confirm unreachable-object GC + PR-ref / cached-view
   removal.
9. **Only after Support confirms** → flip the repo PUBLIC.
10. **§6** delete the local leak-bearing artifacts.

> The whole point of Option A vs. Option C is gate 7–9: the force-push alone
> does not expunge GitHub-side copies (orphaned commits, `refs/pull/*`, SHA
> cache). Support action is what closes that gap. Flipping public before their
> confirmation reduces Option A back to the insufficient Option C.

### Ready-to-send GitHub Support request

Open a **private** ticket at <https://support.github.com/contact> (category:
*Account or data → sensitive data removal*). Paste and fill the bracketed parts
**after** you have force-pushed (so you can list the now-unreachable SHAs):

```text
Subject: Purge unreachable commits + PR refs after sensitive-data history rewrite — fa-mc/vibe-cading

Repository: fa-mc/vibe-cading (currently PRIVATE; preparing for first public release)

We removed confidential pre-release material from this repository's git history
using git filter-repo and force-pushed the rewritten `main`. The repository is
still PRIVATE and we will NOT make it public until you confirm the steps below.

Please:
1. Run garbage collection to purge the now-unreachable objects/commits so they
   are no longer fetchable by SHA (e.g. via the commit URL form
   https://github.com/fa-mc/vibe-cading/commit/<sha>).
2. Remove cached commit/diff views that may still serve the removed content.
3. Remove or expire the pull-request refs (refs/pull/*) that still pin the
   pre-rewrite blobs — in particular PR #28, whose head/merge refs hold the
   "before" state of the scrub, and the earlier merged PRs that introduced the
   removed files. We understand force-pushing a branch does not rewrite PR refs.

Representative old commit SHAs that should become unreachable after GC
(non-exhaustive — please GC all unreachable objects):
  - 0a7a562  (introduced docs/business-strategy.md)
  - b842160  (docs/archive/mcp-integration-plan.md)
  - [add the pre-rewrite main tip a017734 and any SHAs filter-repo reports as
     rewritten — see the filter-repo commit-map in
     ~/vibe-rewrite/.git/filter-repo/commit-map]

Please confirm once GC and ref/cache removal are complete so we can safely make
the repository public. Thank you.
```

> After Support confirms, re-run the **§3 verification** one final time against a
> fresh clone of origin AND spot-check a couple of the old commit-SHA URLs
> return 404 before flipping public.

## 6. Cleanup (after launch is done and verified)

```bash
# remove the leak-bearing local artifacts (they contain the strings):
rm -f /workspaces/vibe-cading/.agents/plans/2026-06-05-history-rewrite-recipe.md
rm -f /workspaces/vibe-cading/.agents/plans/history-rewrite-expressions.txt
rm -f ~/history-rewrite-expressions.txt
# keep ~/vibe-mirror-backup.git until you are 100% confident the launch is stable,
# then delete it too (it is a full pre-rewrite leak snapshot):
# rm -rf ~/vibe-mirror-backup.git ~/vibe-rewrite ~/vibe-verify
```
