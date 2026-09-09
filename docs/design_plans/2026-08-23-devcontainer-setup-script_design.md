# Design: Explicit-Opt-In Workspace Setup Script (replaces #81 + #83)

<!-- Filename: 2026-08-23-devcontainer-setup-script_design.md (tracked in git) -->

## Meta
- **Requirements ref**: N/A — unifies two deadlocked, independently-BLOCKed PRs
- **Requester role**: User/PM
- **Date**: 2026-08-23
- **Dialog rounds**: 9 (round 1 — BLOCK, 6 fixes; round 2 — BLOCK, 2 blocking + 4 lesser fixes;
  round 3 — BLOCK, 2 blocking + 5 major/moderate fixes; round 4 — BLOCK, 4 blocking + 5
  moderate/minor fixes; round 5 — BLOCK on one contract-coverage gap (F3) + 8 lesser fixes,
  reviewer confirmed the guard mechanism itself had converged; round 6 — BLOCK, all findings
  confined to T5 (an injection reintroduced by round 5's own fix, plus 3 lesser contract issues) —
  reviewer re-confirmed the guard mechanism (lib, both scripts) has no outstanding issue; round 7 —
  BLOCK on one small shell-semantics bug in T5's round-6 fix (`for` loop exit-status), + 2
  lesser fixes; reviewer independently re-verified the guard mechanism and the round-6 injection
  fix, and found nothing else; round 8 — BLOCK on one silent-failure bug in T5's round-7 fix
  (unset `VIBE_OPENED`) + 3 lesser fixes to the T9c task added in round 7; reviewer confirmed the
  guard mechanism has now converged across three consecutive rounds; round 9 — BLOCK on one
  unimplementable/unsafe test-harness spec in T9c's own item (d) + 2 minor corrections; reviewer
  confirmed the shipped mechanism (lib, both scripts, T5's fragment) has now converged across four
  consecutive rounds — remaining risk is confined to the CI regression harness protecting it. See
  §Round-1/2/3/4/5/6/7/8/9 Review Response)
- **Supersedes**: fa-mc/vibe-cading#81 (BLOCKed ×4, converted to split; layout half stayed
  draft), fa-mc/vibe-cading#83 (BLOCKed ×2, both rounds security-severity)
- **Not touched / already merged**: #80 (standalone viewer), #82 (image → `docker/`, compose —
  the split-A half of #81, verified correct every round it was reviewed)

---

## Objective

`#81` and `#83` deadlocked on each other: `#81`'s clone-guidance docs needed `#83`'s path
de-hardcoding to not contradict `devcontainer.json`; `#83`'s path fix needed `#81`'s layout
guard to not silently over-mount. Both PRs also independently patched the *same* mechanism
(inferring workspace safety from directory contents) and both patches were shown, empirically,
to reintroduce a hole worse than the hardcoded literal they replaced.

This design replaces both with one mechanism: move the safety judgment from *inferred at every
container start* to *decided once, explicitly, with a human present* — **and re-validated live,
at every start, against the exact directory that will actually be mounted**, not merely against
a marker's existence. A tracked setup script run once after cloning validates the layout —
requiring the nested `main/` + sibling-worktree layout unconditionally — and writes an explicit
marker. `devcontainer.json`'s `initializeCommand` gains one array-form entry that checks the
marker **and** independently re-derives and re-validates the real mount source every time,
because (round 2 found) a marker written for one directory does not license a bind-mount of a
different one.

## Why the prior approach failed (carried findings, not re-derived)

1. **Content-based inference cannot distinguish intent.** `[ -d "$root/main" ]` is satisfied by
   the opened folder itself when the checkout is named `main` — a clone at `~/main` passes the
   guard and `workspaceMount` then binds `$HOME` read-write. Reproduced end-to-end in `#83` round
   2 with a real `devcontainer up`: guard passed, `docker inspect` showed `Source: <home>`,
   `RW: true`, and the reviewer appended to a simulated `~/.ssh/id_rsa` from inside the container.
   `git clone <url> main` is exactly what this project's nested convention invites, so this is a
   likely path, not a contrived one. **No content-based predicate closes this** — the fix has to
   be an explicit host opt-in.
2. **String-form `initializeCommand` is not safely quotable.** The devcontainer CLI substitutes
   `${localWorkspaceFolder}` as a literal string *before* the shell parses the command line. A
   `'` in the path breaks out of any quoting written in the JSON; a `$(...)` executes. `#83`
   round 2 demonstrated a false accept where the guard validated one path while Docker mounted a
   different, injected one — despite the commit message claiming the path was quoted. **Verified
   fix direction, not just diagnosis**: array-form `initializeCommand` passes each array element
   as data (execve argv), never through a shell — reproduced below (§Verification) with a path
   containing `$(touch …)`, which reached the target script verbatim and did not execute.
3. **Coupling the fix to undocumented, unenforced doc drift.** `#83`'s guard shipped as a silent
   behavior change with no updated Quick start; `README.md`'s clone-and-open instructions broke
   for a flat clone the moment the guard existed, and its own error message was malformed
   (`\main\` — an artifact of the same string-interpolation bug in the error `printf`).

## Round-1 Review Response

A fresh-context independent `tl` review (brief: this artifact's path only, no framing) returned
**BLOCK** against the round-1 draft, with 8 findings, several reproduced against real Docker /
`@devcontainers/cli` runs.

| Finding | Fix adopted |
|---|---|
| F1 (blocking, reproduced) — a flat clone's mount source is `${localWorkspaceFolder}/..`, i.e. the clone's *parent*, not the repo; round-1 validated the repo root but mounted its parent, reopening the `$HOME`-exposure hole for any flat clone | **Drop flat-clone support entirely** — round 1's own approach; superseded in its details by round 2's B1 fix below, but the "nested only" decision itself survived to round 2 unchanged |
| F2 (blocking, reproduced) — string equality between `$HOME` and the candidate root fails to detect the two paths being the *same directory* reached via a symlink (`/home`→`/var/home` on Fedora Silverblue/systemd-homed is a **default**, not exotic) | Physically resolve both sides (plain `cd` then `pwd -P` — see `home_is_at_or_under`'s actual code block below; there is no `..` in this specific resolution, so plain `cd` and `cd -P` happen to coincide here, unlike `literal_mount_source` below where the distinction is safety-critical — round-4 review, M10) before comparing, trailing-slash-safe |
| F3 (blocking, reproduced) — `initializeCommand` is a single JSON key already carrying `.claude-creds` seeding; an array-form replacement would silently delete it, and the seeding is load-bearing | Object/map-form `initializeCommand`, preserving the seeding entry verbatim |
| F4 (major, reproduced) — `git rev-parse --show-toplevel` returns the *opened worktree's own* top level, misclassifying a correctly-nested sibling worktree as flat | Resolve the primary checkout via `--path-format=absolute --git-common-dir` |
| F5 (moderate, reproduced) — empty/unset `$HOME` makes the predicate vacuous | Fail closed on unset/empty/non-absolute `$HOME` |
| F6 (major, design-level) — `init-docker-env.sh` doesn't exist on this branch; Compose isn't gated by any guard | Specify `docker/.env` content directly; state Compose is documented-not-enforced |
| F8 (process) — round-1's own §Verification table asserted results F2 then contradicted | §Verification re-run against the fixed predicate |

## Round-2 Review Response

A **second**, independently fresh-context `tl` review of the round-1-fixed draft again returned
**BLOCK** — the round-1 fixes to the *predicate* (symlink-safe, fail-closed, worktree-aware) were
verified correct, but two new, more fundamental problems surfaced:

### B1 (blocking, reproduced end-to-end with an actual private-key write) — a marker written for the correct root does not constrain what actually gets mounted when a *different* directory is opened

The round-1 guard validated `resolve_project_root($1)` — a **git-derived** answer, always
`main`'s parent, regardless of which directory `$1` actually is. Docker mounts the **lexically
and filesystem-resolved** `${localWorkspaceFolder}/..` — a function of `$1` itself. These agree
only when `$1` is a direct child of the project root. A `git worktree add` to any other location
(fully legal git, no special privilege) breaks that assumption:

```
$ git worktree add /tmp/fakehome/rogue-wt          # main is elsewhere, this is legal
$ devcontainer up --workspace-folder /tmp/fakehome/rogue-wt
GUARD validates root=<main's real project root>   -> marker present there -> PASS
Docker mounts source=/tmp/fakehome/rogue-wt/.. = /tmp/fakehome (= $HOME)
$ docker exec ... 'cat ~/.ssh/id_rsa' → real key material, RW mount
```

The design's round-1 claim — *"Because layout is now nested-only, the mount expression's
parent-of-checkout assumption always holds when the guard has passed"* — is **false**:
nested-only constrains where `main` lives, not where a worktree lives, and nothing stops a
worktree from being created anywhere on the filesystem.

**Fix (this revision):** the guard computes **both** the git-derived project root **and** the
literal directory Docker will mount (`cd "$1/.." && pwd -P` — **plain `cd`, explicitly NOT
`cd -P`** — verified below to compute the *same* directory Docker's bind-mount source resolves
to, including through symlinks. Docker's `/..` handling and a **logical** `cd`'s "collapse the
trailing `component/..` pair lexically before resolving any remaining symlink" behavior coincide;
`cd -P` does the opposite — it resolves `component` as a symlink *before* applying `..`, which
diverges from Docker and was shown in round 3 to reopen the exposure this whole mechanism exists
to close (see §Round-3 Review Response, B3). `pwd -P` after a plain `cd` is still needed, to
normalize whatever symlink-free-but-not-yet-canonical result the plain `cd` lands on), and
refuses unless they are the same directory. It
also re-runs the `$HOME`/`/` safety predicate against that mount source **live, every start** —
not only once, historically, in `setup-workspace.sh` — so a marker can never authorize a mount
it was never actually checked against.

### B2 (blocking, design-level) — the mount expression this design depends on doesn't exist on any branch it can inherit from

Round 1 said `workspaceMount`/`workspaceFolder` "keep the `#83` form" — but `#83` is one of the
two PRs this design *supersedes and closes*, not a merge base. `main` (and this branch, forked
from it) still carries the pre-`#83` hardcoded literal
(`source=/workspaces/vibe-cading,target=/workspaces/vibe-cading`). There is nothing to "keep."
**Fix:** the de-hardcoding is pulled into this design's own Implementation Plan as an explicit
task (T5 below) with its own before/after text, re-verified as part of this PR rather than
assumed inherited.

### Lesser findings, all fixed in this revision

- **M1 (major, reproduced)** — the `root == /` clause's stated rationale ("redundant, since
  `$HOME` is always under `/`") was reproducibly false: the prefix-match pattern
  `"$root_p"/*` becomes `//*` when `root_p="/"`, which matches nothing, so `home_is_at_or_under
  "/"` incorrectly returned "safe." Fixed pattern: `"${root_p%/}"/*`; prose corrected to state the
  clause is load-bearing, not redundant.
- **M2 (major, design-level)** — the migration step (`mv` of the directory the script is
  currently executing from) leaves `$0`/`$PWD`/sourced-lib paths stale mid-script. **Fixed by not
  continuing in-process**: after a successful migration, the script prints the new location and
  exits 0 with instructions to re-run from there, rather than attempting to self-relocate.
- **M3 (moderate)** — marker-before-`docker/.env` ordering meant a `docker/.env`-write refusal
  (existing file, no `--force`) could leave the marker passing permanently against stale compose
  config. **Fixed**: write/validate `docker/.env` first; only write the marker once it is known
  current.
- **M4 (moderate)** — `VIBE_ROOT` in the originally-specified `docker/.env` has zero consumers
  (`docker/compose.yaml` reads only `VIBE_WORKDIR`, `VIBE_PROJECT`, `VIBE_VIEWER_PORT`,
  `USER_UID`/`USER_GID`). **Dropped** — `docker/.env` now writes only `VIBE_WORKDIR`.
- **m1 (minor)** — a sentence named the wrong `initializeCommand` key (said
  `checkWorkspaceSetup` where it meant `seedClaudeCredentials`). Corrected.
- **m2/m3 (minor)** — noted for implementation: a pre-existing worktree on an older branch
  lacks the new check script (document the resulting error is self-explanatory enough, no code
  fix needed); shared-lib helper functions should use function-local variable scoping where the
  shell supports it, to avoid caller-namespace collisions.

Nested-only also mechanically resolves the round-1 draft's own flagged open decisions: the marker
now *always* lives outside the git repository (parent of `main`), so **Open Decision 2 (gitignore
status) disappears**.

## Round-3 Review Response

A **third** fresh-context `tl` review of the round-2-fixed draft again returned **BLOCK**. Two of
the finding were genuinely new — not re-derivations of prior rounds — and one (B3) meant the
round-2 fix's own worked examples were reproducible only under a form of the code the design
never actually specified.

### B3 (blocking, reproduced with a live `docker run` and private-key read) — the design's own prose named the wrong primitive for `literal_mount_source`, and the named-but-wrong one reopens B1

The **code block** for `literal_mount_source` was always `( cd "$1/.." && pwd -P )` — a
**logical** `cd` (no `-P`) followed by `pwd -P`. But every piece of narrative prose around it
(the round-2 fix description, the function's own in-code comment, the §Verification rows, the
§Known Risks entry) called this "`cd -P`" — which is a **different, physical** `cd` that
resolves a symlinked path component *before* applying `..`, not after. Round 3 constructed the
case that tells them apart and is realistic, not contrived: a symlink named `main` placed
directly inside `$HOME`, pointing at the real nested checkout (`ln -s /srv/proj/main
"$HOME/main"`; no `git worktree`, no special privilege). Opening `$HOME/main`:

- Logical `cd` (what the code block actually says): `mount_src` = `$HOME` → mismatches the
  git-derived root → **correctly REFUSEd**.
- Physical `cd -P` (what the prose said, and what a reader "fixing" the code to match the prose
  would produce): `mount_src` collapses through the symlink to the real project root → **matches**
  the git-derived root → **incorrectly ACCEPTs** → `docker inspect` confirmed `$HOME` mounted
  read-write; a planted `~/.ssh/id_rsa` was read from inside the container.

**Fix:** every prose occurrence corrected to describe the plain-`cd`-then-`pwd -P` form, with an
explicit "do NOT add `-P` to the `cd`" warning at both the function definition and every place
that previously said "`cd -P`" (§Architecture code block and comment, updated in place above).
The distinction is genuinely non-obvious — `-P` reads as "more correct/more resolved," which is
exactly backwards for this specific use — so the warning is deliberately loud rather than a
one-line aside.

### B4 (blocking, reproduced) — the M1 "fixed" glob pattern still failed under bash, the shell the guard actually runs under

`"${_wr_root_p%/}"/*` (parameter expansion, unquoted `/*` outside the quotes) does not match
anything in bash when `_wr_root_p` is `/` (the stripped value is empty, and bash — unlike dash —
does not treat a quoted-empty-prefix-plus-bare-glob the same as a single quoted pattern string).
The round-2 §Verification row asserting this fixed pattern REFUSEs `root == "/"` was run under a
shell where it happens to work (`sh`/dash), not bash — and the guard's `initializeCommand` invokes
`bash` explicitly. **Fix:** move the `/` inside the quotes — `"${_wr_root_p%/}/"*` — verified
correct under both bash 5.2 and dash in this round (§Architecture code block updated; both shells
now produce the same, correct verdict). The standalone `root == "/"` clause at both call sites was
never removed and remains a second, independent line of defense regardless.

### M5–M9 (major/moderate) — adopted without further dialog, changes below

- **M5** — `resolve_project_root`'s failure path didn't give `setup-workspace.sh` a way to learn
  the flat clone's own path (needed to print it and build the migration recipe), which risked the
  exact "two independent implementations disagree" pattern the shared lib exists to prevent.
  **Fix as originally proposed in this round (SUPERSEDED — see §Round-4 Review Response, B6,
  which reproduced this exact fix reintroducing F4):** `setup-workspace.sh` locates its own
  checkout directly via `git rev-parse --path-format=absolute --show-toplevel` from `$PWD`, on the
  claim that "this specific caller does not have the F4 problem, since the script is never invoked
  against an arbitrary `$1` the way the guard is." **That claim was wrong** — invoked from a
  worktree of a flat clone, `--show-toplevel` still returns the worktree's own path, not the flat
  clone being migrated. **Do not implement this version.** The design's actual, current mechanism
  is `resolve_primary_checkout` (§Architecture, §Round-4 Review Response B6) — a single primitive
  shared by both scripts, invariant to which worktree asks.
- **M6** — the migration (`mv`) ran before the `$HOME`/`/` safety predicate, and hardcoded the
  literal name `vibe-cading` rather than the actual clone's basename. **Fix:** compute the
  *prospective* post-migration root and run `home_is_at_or_under`/`== "/"` against it **before**
  performing any `mv`; build the migration recipe from `$(basename "$checkout")`, not a literal.
- **M7** — the marker-before-`docker/.env` reorder didn't close the staleness scenario it was
  introduced for (a pre-existing marker survives regardless of `docker/.env`'s state, since the
  guard never reads `docker/.env`). **Fix — correcting the claim, not adding code:** state plainly
  that the marker (devcontainer safety) and `docker/.env` (Compose correctness) are independent
  artifacts with independent staleness stories; the devcontainer guard's safety property never
  depended on `docker/.env` being current, only Compose's did, and Compose is already
  documented-not-enforced (§Scope: Compose entry point) — so a stale `docker/.env` is a Compose
  usability issue a re-run with `--force` fixes, not a safety gap.
- **M8** — verification throughout is against `@devcontainers/cli`/VS Code Dev Containers only;
  this repo's devcontainer is also used from Google Antigravity (PR #23), and object-form
  `initializeCommand` (T4) is a new requirement this design introduces — the prior string-form
  entry may have worked there without ever exercising object-form support. **Fix:** added as an
  explicit pre-merge verification task (T10) rather than a design change — there is no Antigravity
  binary available to test against in this environment, so the design states the risk and gates
  merge on it rather than asserting untested compatibility. **Round-4 correction:** the round-3
  draft proposed a fallback for "Antigravity doesn't support object-form" — chaining both commands
  into one string via `&&`. Round 4 found that fallback reintroduces exactly the string-interpolation
  injection this whole design exists to close: `${localWorkspaceFolder}` would again reach a shell
  as a literal, substituted string, and the new check is precisely the entry that takes
  attacker-influenced path input (the credentials-seeding string never did). **There is no
  fallback.** T10 is a hard merge gate: if Antigravity does not support object-form
  `initializeCommand`, this design does not ship until that is resolved by further design work —
  not by silently reintroducing the injection vector under a different name.
- **M9** — 13 of 15 Tests rows were "manual," despite the three shared-lib functions being pure,
  path-taking, and exactly the kind of thing `tests/tools/` already covers by shelling out (per
  `test_check_doc_links.py`). **Fix:** added T9 — a `tests/tools/test_workspace_root.py` driving
  `resolve_project_root`/`literal_mount_source`/`home_is_at_or_under` under both `bash` and `sh`,
  covering every edge case in this document's verification tables (symlinked `main`, symlinked
  ancestor, rogue worktree, sibling worktree, `root == /`, unset/empty/relative `$HOME`,
  spaces/glob characters in paths) as a required implementation task, not a deferred manual step.
  **Round-4 correction:** this would have caught **B4** mechanically (a shell-specific pattern bug
  in the code itself). It would **not** have caught **B3** — B3 was the document's *prose*
  mislabeling code that was already correct, which a test of that code cannot detect by
  construction (the same code passes identically whether the surrounding comment is right or
  wrong). B3's actual mitigation is the loud in-code "do NOT add `-P`" warning, kept as its own,
  separate defense — not superseded by T9.

Minor findings (m4–m7) folded in: a minimum git version is stated (`--path-format` needs git
≥ 2.31) with git-failure and not-a-repo distinguished in the error message; the mismatch error
message in `check-workspace-setup.sh` is broadened beyond "a worktree lives outside its project
directory" (it also fires for a subdirectory of `main` or a worktree nested inside the project,
both correctly refused but previously mis-described); `check-workspace-setup.sh`'s listing gains
its shebang, `set -u`, and lib-sourcing line; a Known Risks entry notes the unexamined case of a
host project root shadowing an already-used container path.

## Round-4 Review Response

A **fourth** fresh-context `tl` review confirmed the round-3 code-level fixes (B3's `cd`-vs-`cd -P`
divergence, B4's pattern fix) were correct and reproduced them independently — but found the
round-3 *prose* fixes for M5, M6, and M8 were each themselves flawed, plus one more instance of
B3's own failure class (a prose claim describing a fix the code didn't contain).

### B5 (blocking, reproduced) — round-3's "prospective post-migration root" computed the wrong directory, refusing the mainstream flat-clone case

Round 3's step 2 checked `dirname "$checkout"` before migrating. The migration recipe nests the
checkout one level deeper (`$checkout` → `$checkout/main`), so the post-migration project root
**is `$checkout` itself** — the parenthetical justifying `dirname` ("unchanged by the migration,
which only adds one path segment *below* it") was self-refuting: adding a segment below
`$checkout` is exactly what promotes `$checkout` to project root. Reproduced: a flat clone at
`$HOME/vibe-cading` (the mainstream case) was refused migration under the round-3 predicate, while
a checkout that *is* `$HOME` itself (the actual danger case) was — by coincidence of the same
wrong predicate — still correctly refused. **Fix:** evaluate `home_is_at_or_under`/`== "/"`
against `$checkout` directly (§`setup-workspace.sh` step 2, updated above); verified against both
cases (accept the mainstream shape, refuse the `$HOME`-is-the-checkout shape) before writing it
into this document, not asserted from reasoning alone.

### B6 (blocking, reproduced) — round-3's M5 fix (`--show-toplevel` from the script's own `$PWD`) migrates the wrong directory when invoked from a worktree of a flat clone

`--show-toplevel` returns the *asking* worktree's own top level — this is F4 again, merely masked
for the common case because the result still fed correctly into the nested/flat determination.
Reproduced: with a flat clone at `$HOME/vibe-cading` and a worktree at `$HOME/wt-x`, running the
script from inside `wt-x` computed `checkout = $HOME/wt-x` and would have offered to migrate the
**worktree**, not the primary checkout — breaking the worktree's gitdir link and leaving the real
checkout unmigrated. **Fix:** replaced with `resolve_primary_checkout` (new, in the shared lib) —
a single primitive, used uniformly by both scripts, that always resolves to the one real checkout
via `--git-common-dir` regardless of which worktree asks. Verified directly: invoking it from both
`$HOME/vibe-cading` and `$HOME/wt-x` returns the identical, correct checkout path.

### B7 (blocking, design-level) — round-3's M8 fallback ("chain both commands into one string if Antigravity lacks object-form support") reintroduces the exact injection this design exists to close

That fallback would substitute `${localWorkspaceFolder}` into a shell string again — precisely
what §"Why the prior approach failed" item 2 and Success Criterion 3 forbid, and specifically on
the one entry that takes attacker-influenced path input (the pre-existing credentials-seeding
string never did). **Fix:** the fallback is removed, not replaced. T10 is now a hard pre-merge
gate with no degraded-but-shipped fallback — if Antigravity doesn't support object-form
`initializeCommand`, this design returns to authoring rather than shipping a weaker mechanism
under the same name.

### B8 (blocking, reproduced) — the same "prose describes a fix the code doesn't implement" failure as B3, this time about the git-version/error-message handling

Round 3's own minor-findings list claimed `resolve_project_root` "distinguishes git-failure from
not-a-repo" and "states a minimum git version" — neither was true of the code block at the time;
it still had one `2>/dev/null` and one collapsed error message. **Fix:** the split
`resolve_primary_checkout`/`resolve_project_root` (adopted for B6 above) captures git's own stderr
via `2>&1` instead of discarding it, states the git ≥ 2.31 requirement in its header comment, and
keeps the "not named `main`" failure as a genuinely separate code path with its own message — so
the two failure classes are now actually distinguishable, not just described as such.

### Moderate/minor findings (M10–M14), adopted

- **M10** — the F2 verification-table row (§Round-1 Review Response) still said "`cd -P && pwd`"
  for `home_is_at_or_under`'s resolution, even though that function's actual code uses plain
  `cd`/`pwd -P` (functionally fine there, since there is no `..` step — but the same "prose says a
  different primitive than the code" pattern B3 was about). Corrected, with an explicit note on
  why this specific function doesn't share `literal_mount_source`'s hazard.
- **M11** — corrected an overclaim (repeated three times) that the T9 test suite "would have
  caught B3 and B4." It would have caught B4 (a shell-specific bug in the code). It could not have
  caught B3 (correct code, wrong surrounding prose) — a test of code that was never wrong cannot
  detect a comment that was. Reworded in all three places (§Round-3 Review Response's M9 bullet,
  T9's implementation-plan entry, Success Criterion 8) to state this precisely, and to keep the
  in-code warning as B3's actual, independent mitigation.
- **M12** — the Tests table's 13 "manual (confirm whether a harness exists)" rows were stale once
  T9 mandated building exactly that harness; re-attributed to T9, with new rows for the B5/B6/M14
  migration-safety cases and the B8 error-distinction case.
- **M13** — `setup-workspace.sh` step 1 now exits 1 explicitly on a `resolve_primary_checkout`
  failure rather than allowing an empty `checkout` value to flow into the migration branch.
- **M14** — migration now refuses outright if any worktree besides the primary checkout already
  exists (`git worktree list --porcelain` count > 1) — the `mv` would otherwise silently break
  every such worktree's absolute-path gitdir links.

Also folded in without further dialog: explicit `|| exit 1` on the lib-sourcing line; a documented
(not fixed) residual gap for `git --separate-git-dir` layouts, which fail closed rather than
misresolve; an explicit failure message for the `mkdir "$name.tmp"` collision case; and a Known
Risks row noting a comma in a host path breaks T5's string-form mount spec (loud failure, not a
new injection vector — out of scope for this design's argv-safety concerns, which apply to the
guard's array-form entry, not this pre-existing string-form field).

## Round-5 Review Response

A **fifth** fresh-context `tl` review reproduced every round-4 fix independently (including a new,
more direct end-to-end verification of the central mount-vs-guard claim, through T5's actual
substitution expression rather than a proxy) and found **no new mechanism or security defect** —
stating plainly that the security mechanism has converged. The remaining findings were entirely
contract/prose consistency, concentrated in exactly the failure class this design kept
re-encountering: claims of coverage or correctness that the code didn't actually back up.

- **F3 (blocking)** — the Tests table attributed this round's own new fixes (B5's argument choice,
  M14's worktree-count refusal) to **T9**, whose scope is explicitly the four lib functions in
  isolation — which cannot distinguish a caller passing the right argument from the wrong one (the
  same structural gap M11 already named for B3). **Fix:** split into **T9** (lib-only, unchanged
  scope) and new **T9b** (script-level end-to-end fixtures for both scripts as processes); Tests
  table rows re-attributed row-by-row.
- **F1 (major)** — `check-workspace-setup.sh`'s own preamble prose still claimed the "too old" vs.
  "not a repo" distinction that B8 disproved for the *lib's* comment but hadn't corrected here —
  another live B3/B8-class instance. **Fixed in place** (§`check-workspace-setup.sh`, above): the
  actual distinction is git-failure vs. not-named-`main`, not two flavors of git failure.
- **F2 (major)** — §Round-3 Review Response's own M5 bullet still read as an instruction to
  implement the `--show-toplevel` approach B6 reproduced as broken, with no annotation (unlike M8
  and M9 in the same list, which both got "Round-4 correction:" notes). **Fixed:** M5's bullet now
  states plainly it was superseded and must not be implemented, pointing at the real mechanism.
- **F4 (moderate)** — T2/T3 (Implementation Plan) didn't list several fixes this document already
  specifies in the Architecture section (M14, B5, `--yes`/`--force`, the marker filename, the
  `$name.tmp` collision message). **Fixed:** T2/T3 rewritten to enumerate them explicitly.
- **F5 (moderate)** — T5 (mount de-hardcoding) left a stale in-file comment claiming the container
  "always opens in `main`," and didn't widen `postCreateCommand`'s `chown`/`safe.directory` scope
  to match `workspaceFolder` no longer being a fixed literal — opening a sibling worktree directly
  would leave `main` un-prepared even though that worktree's git operations write into it. **Fixed
  in place** (§T5, above): comment corrected, `postCreateCommand` widened to the whole mounted
  project root and looped over every top-level checkout.
- **F6–F9 (minor)**, all fixed in place: `resolve_primary_checkout`'s error capture now covers the
  `cd` step too, not only `git` (verified: a nonexistent path previously produced a message with
  nothing after the colon; now includes the real reason); M14's refusal message names
  `git worktree prune` as the remedy for a *stale* (not just live) worktree entry — verified a
  `prunable` entry still trips the same count-based refusal; `docker/.env`'s generated header notes
  that `--force` rewrites the file wholesale, so hand-added `VIBE_PROJECT`/`VIBE_VIEWER_PORT`
  aren't preserved across it; step 5 now says `$checkout/docker/.env` explicitly, since this script
  may run from a worktree with its own `docker/`.

## Round-6 Review Response

A **sixth** fresh-context `tl` review confirmed every round-5 fix independently (re-deriving B3
and B4 rather than trusting the document) and stated plainly that **the guard mechanism itself has
converged** — no new finding anywhere in the shared lib, `check-workspace-setup.sh`, or
`setup-workspace.sh`. The block was entirely inside **T5**, the section round 5 amended last and
therefore the least-scrutinized:

- **Finding 1 (blocking, reproduced with a live `docker run` and an executed injected command)** —
  round 5's own fix for `postCreateCommand`'s widened `chown`/`safe.directory` scope interpolated
  `${containerWorkspaceFolder}` directly into the `postCreateCommand` **shell string** — the exact
  injection class B7 rejected a fallback over in round 4, reproduced concretely: a host directory
  named `` pr$(touch PWNED)oj `` executed the embedded command, and the guard has no visibility
  into `postCreateCommand` to stop it (guard-pass is a precondition for reaching this step, not a
  defense against it). **Fixed** (§T5, above) by routing the path through `remoteEnv` — a real
  environment variable, referenced as a shell variable inside `postCreateCommand`, never
  re-interpolated as substituted text — verified against the same hostile fixture: correct path
  resolved, nothing executed.
- **Finding 2 (major, reproduced)** — independently of Finding 1, the Implementation-Plan
  checkbox text for this same fix used the unbraced token `$containerWorkspaceFolder`, which is
  not a devcontainer substitution and is not set in the container environment — probed directly
  and confirmed unset, meaning the widening would have silently done nothing (`chown` of `.`,
  no error) even before Finding 1's injection concern. **Fixed**: the Implementation Plan now
  points at the same `remoteEnv`-indirection form as the Architecture section, rather than
  carrying an independently-worded (and wrong) restatement.
- **Finding 3 (moderate)** — T9b (round 5's new task) left its own file format and CI enforcement
  undecided ("`.sh` … or a pytest module … confirm during implementation"), and was never marked
  CI-enforced anywhere it was referenced, unlike T9. Round 6 found the repo's actual convention is
  unambiguous (`tests/tools/` holds only pytest modules; CI collects `pytest tests/`, which would
  never run a `.sh` file). **Fixed**: T9b is now `tests/tools/test_setup_workspace.py`, explicitly
  CI-enforced, referenced in Tests row 17 and Success Criterion 8.
- **Finding 4 (minor)** — the `safe.directory` loop's membership test (originally implied to be
  `git worktree list`) would miss a sibling clone under the project root that is not a worktree of
  `main` at all (this repo has exactly one such case — a wiki clone). **Fixed**: the loop tests
  `-e "${d}.git"` over top-level directories instead, covering any git checkout regardless of
  whether it's a worktree.

No other new issues were found; round 6 explicitly re-measured the performance and ownership-reach
concerns for the widened `chown` (a 3% file-count increase on this repo's actual project root, and
no new directory reach since the whole root was already bind-mounted) and found neither a problem.

## Round-7 Review Response

A **seventh** fresh-context `tl` review confirmed all four round-6 fixes with independent live
reproduction (a real `devcontainer up` against the hostile `$(touch PWNED)` fixture through the
*current* `remoteEnv`-indirection form, confirming no re-parsing surface anywhere in the
substitution path; independently re-derived B3 and B4 from scratch rather than trusting six
rounds of prior prose) and stated the guard mechanism (shared lib, both scripts) has **converged
with nothing new found there**. One blocking finding remained, again in T5 — the section that has
now been wrong in two consecutive rounds:

- **Finding 1 (blocking, reproduced)** — the `safe.directory` loop's body,
  `[ -e "${d}.git" ] && git config …`, is a `for` loop whose exit status is its *last executed
  command's*; when the lexically-last top-level directory under the project root has no `.git`,
  that final iteration's `&&` left side is false, so the whole loop — and the single `&&`-chained
  `postCreateCommand` string it lands in — exits 1, silently aborting every step after it (the
  SSH-key copy, the `chmod`s). Reproduced with a real `devcontainer up` against a project root
  ending in a non-git directory. This repo's current project root happens to hold only git
  checkouts, which is exactly why this would have shipped unnoticed. **Fixed** (§T5, above): the
  loop body is now `if [ -e "${d}.git" ]; then git config …; fi`, which returns 0 regardless of
  match count — verified under both `bash` and `dash`, including the zero-match case.
- **Finding 2 (moderate, adopted)** — the T5 injection class (round-5's defect, round-6's finding
  1) had no automated regression guard; only a manual fixture (Tests row 15b). **Fixed:** added
  **T9c** — a cheap, Docker-free, CI-enforced static test asserting `postCreateCommand` contains no
  devcontainer-substitution token and `checkWorkspaceSetup` stays array-form, catching the whole
  class mechanically rather than just the one fixture, per this project's Post-Fix Hardening
  convention (two consecutive rounds reintroducing the same shape of mistake is exactly the signal
  that convention exists for).
- **Finding 3 (minor, adopted)** — T9b's filename (`test_setup_workspace.py`) undersells that it
  also covers `check-workspace-setup.sh`; noted as a non-blocking naming choice for implementation,
  either name is fine and neither collides with T9's.

The reviewer's closing assessment: the guard mechanism (lib + both scripts) is settled and was
re-verified independently rather than assumed; T5 (`devcontainer.json`'s de-hardcoding +
`postCreateCommand`) was the only section with an outstanding defect, and it was small and
proportionate to fix inline rather than requiring a further architectural round.

## Round-8 Review Response

An **eighth** fresh-context `tl` review reproduced round-7's fix live (built the discriminating
fixture — a project root whose lexically-last top-level directory is not a git checkout — and
confirmed the buggy `&&`-only form fails while the `if`/`fi` form succeeds and every post-loop
step actually runs, not just that the loop returns 0 in isolation) and confirmed the guard
mechanism (lib + both scripts) has now converged across **three consecutive rounds**. It found one
new blocking issue and several smaller ones, all confined to T5's `postCreateCommand` fragment and
the T9c task added in response to round 7:

- **Finding 1 (blocking, reproduced)** — an unset `VIBE_OPENED` (a `remoteEnv` misconfiguration,
  or a host that doesn't honor it) makes `dirname ""` resolve to `.`, silently narrowing `chown`
  back to the pre-F5 un-widened behavior and leaving the `safe.directory` loop matching nothing —
  while `postCreateCommand` still exits 0 and `devcontainer up` reports success. **Fixed**: a
  `: "${VIBE_OPENED:?…}"` guard placed *outside* any `$(...)` subshell (verified: the same
  expansion written *inside* a subshell, e.g. as part of the `dirname "$(...)"` call, only kills
  the subshell and the chain silently continues — a subtler version of the same bug, checked and
  rejected before settling on the top-level form). T10 — the design's own Antigravity gate — is
  given a concrete observable (`git config --global --get-all safe.directory` must list every
  top-level checkout, not just the one opened) since "the container starts" cannot detect this
  failure mode.
- **Finding 2 (major, adopted)** — T9c's round-7 wording ("no `${...}` token") would false-positive
  on this same fragment's own `${d}`/`${d%/}` shell parameter expansions. **Fixed**: T9c now
  enumerates the exact devcontainer-substitution token set to match, verified against both the
  current fragment (zero matches) and the round-5 defective form (one match) before being written
  into this document.
- **Finding 3 (moderate, adopted)** — Tests row 15c and T9c both claimed T9c was "the CI-enforced
  complement" for round-7's loop-exit-status bug, but T9c as scoped was purely static/lexical and
  cannot execute the fragment to observe a loop-exit-status bug. **Fixed**: T9c gained an
  execution-based item (feeding the composed `postCreateCommand` string to `sh -c` against a
  non-git-sibling-last fixture and asserting exit 0) as its actual regression guard for this class.
  **Round-9 correction:** this wording (the *entire* composed string) was itself unimplementable
  and unsafe — see §Round-9 Review Response and T9c item (d) for the corrected, isolated-fragment,
  `HOME`-scoped form with a negative control, which is the authoritative spec.
- **Finding 4 (minor, adopted)** — T9c wasn't referenced from Tests row 17 or Success Criterion 8.
  **Fixed**, folded into both.

The reviewer noted this T5/T9c fragment has now been wrong in three consecutive rounds (5, 6, 7)
before this revision — all four items above are confined to it; the guard mechanism itself
required no further change.

## Round-9 Review Response

A **ninth** fresh-context `tl` review reproduced round-8's fix live (real `devcontainer up` with
`remoteEnv` missing `VIBE_OPENED` → loud abort, confirmed; a single fixture combining all three
prior stressors — hostile `$(...)` path, sibling worktree opened directly, non-git lexically-last
sibling — all together → clean success, confirming rounds 6/7/8's fixes compose without
interaction) and confirmed the guard mechanism has now converged across **four consecutive
rounds**. One blocking issue and two minor corrections remained, confined to **T9c's own item (d)**
— the test-harness task round 8 added specifically to guard the T5 fragment:

- **Blocking (reproduced in both possible environments)** — item (d), as round 8 specified it,
  fed the *entire* composed `postCreateCommand` string (including the container-only `sudo
  chown`/SSH-key/`chmod` tail) to a bare `sh -c` check. On a host without passwordless `sudo`
  (this review environment included) that fails immediately and identically regardless of whether
  the `safe.directory` loop is the fixed or the round-7-buggy form — red on arrival, and not
  diagnostic even where it runs. On a host **with** passwordless `sudo` (e.g. default GitHub
  Actions runners) it instead **silently mutates the invoking user's real `~/.gitconfig` and
  `~/.ssh` permissions** — reproduced directly (repeated `safe.directory` entries with no dedupe;
  `chmod` applied to a real SSH keypair). **Fixed**: item (d) now executes only the isolated T5
  fragment (guard line + `VIBE_ROOT` assignment + loop, `&&`-joined as shipped), with `HOME`
  pointed at a fixture `tmp_path` and an explicit negative control (the round-7-buggy form must
  fail the same fixture that the shipped form passes) — verified this discriminates cleanly under
  both `bash` and `dash`, with all writes confined to scratch.
- **Minor** — the round-8 narrative cited a specific example (`VIBE_ROOT="$(dirname
  "${VIBE_OPENED:?msg}")"` as a standalone assignment) as one that "silently continues" if the
  guard were written inside a subshell instead of at the top level. Reproduced that this specific
  example does **not** silently continue (a failed assignment's status still short-circuits a
  following `&&`) — the shape that genuinely does is the substitution consumed inside a `for`
  loop's word list. **Corrected** the cited example; the top-level form itself was never in
  question and needed no change.
- **Minor** — T9c parses JSONC (`.devcontainer/devcontainer.json` carries comments), which
  `json.loads` cannot handle and this project has no JSONC-parsing dependency for. **Noted**: strip
  comments with a small, string-literal-safe stdlib approach, or extract the two target fields via
  a comment-tolerant regex — either is fine, decided during implementation.

The reviewer's closing note: the shipped mechanism (shared lib, both scripts, and now T5's
`postCreateCommand` fragment itself) has converged and required no further change this round; the
block was entirely in the CI regression harness meant to protect that fragment going forward.

## Architecture / Approach

### Approach chosen: marker + live mount-source re-validation, nested layout only

**Split of responsibility:**

| Concern | Where it runs | When |
|---|---|---|
| Judge whether the layout is safe; migrate a flat clone into nested; write the marker; write `docker/.env` | `vibe_cading/tools/setup-workspace.sh`, **on the host**, run directly by the human (or an agent on the human's instruction) | Once, after cloning (and once more after any migration, per M2), before first `Reopen in Container` |
| Refuse to start unless (a) the marker is present, **and** (b) the directory Docker will actually mount is, live, the same directory the marker was written for and still passes the `$HOME`/`/` safety predicate | `.devcontainer/devcontainer.json`'s `checkWorkspaceSetup` `initializeCommand` entry, array-form, invoking a tiny tracked check script | Every container start |

The marker is necessary but **not sufficient** — it proves a human validated *some* project root
once; the live re-check proves the directory about to be mounted *right now* is that same root,
closing B1. This is not two independent guards bolted together for defense-in-depth theater: the
live check alone (with no marker) would re-litigate the whole `$HOME`-inference question on every
start, which is the exact failure mode this design exists to move away from — the marker is what
makes the live check's *predicate parameters* (which directory counts as "validated") a one-time
human decision rather than a per-start inference, while the live check is what makes that
decision actually bind to reality.

*Note on "human present": nothing technically prevents an agent from running the setup script.
The property this design provides is not "no automation touches it" — it is "the judgment is
made once, explicitly, against one real invocation with real error messages," not re-derived from
directory-content heuristics on every container start. An agent running the script still sees and
must act on a REFUSE.*

### Shared resolution logic — one place, sourced by both scripts

Both scripts need identical "find the primary checkout, its parent, and the literal mount
source" logic; F4 and B1 both trace back to the two implementations disagreeing. One sourced
file:

`vibe_cading/tools/lib/workspace_root.sh` (new, tracked, POSIX `sh`-compatible, AGPLv3 header
per this repo's existing convention for tracked shell scripts — `init-claude-runtime.sh` /
`init-agy-runtime.sh` both carry it, and `check_license_headers.py` not globbing `.sh` today is
an existing gap, not license to skip the header on new files):

```sh
# resolve_primary_checkout <opened-folder-path>
# Prints the absolute path of the PRIMARY checkout (the one holding the real
# .git) on stdout -- invariant to whether <opened-folder-path> IS that
# checkout or any worktree of it, because --git-common-dir always resolves
# to the ONE real .git no matter which worktree you ask from (unlike
# --show-toplevel, which returns the ASKING worktree's own top level -- F4).
# This is the single source of truth for "where is the checkout," used by
# BOTH scripts and by every step of setup-workspace.sh's own migration logic
# (round-4 review, B6: a caller that instead used --show-toplevel from its
# own $PWD would migrate the WORKTREE it happened to be invoked from, not
# the primary checkout, when run from a worktree of a flat clone).
# Requires git >= 2.31 (--path-format). Distinguishes a git failure (wrong
# git version, not a repo at all, permission error -- whatever git itself
# reported, captured via 2>&1) from a git SUCCESS that simply isn't named
# `main` -- that second case is resolve_project_root's job below, not this
# function's; this function has no opinion on naming.
# Residual gap (round-4 review, not fixed here): this assumes the toplevel's
# .git is reached normally. A checkout using `git --separate-git-dir` (an
# uncommon, deliberate choice, not this repo's convention) could make
# dirname(--git-common-dir) resolve somewhere other than the toplevel. That
# fails CLOSED today (the result's basename is then unlikely to be `main`,
# so resolve_project_root refuses) rather than silently misresolving -- but
# it has not been constructed and tested. Accepted as a known limitation
# rather than blocking on a layout this project doesn't use.
resolve_primary_checkout() {
    _wr_opened="$1"
    if ! _wr_common="$(cd "$_wr_opened" 2>&1 && git rev-parse --path-format=absolute --git-common-dir 2>&1)"; then
        echo "git could not resolve a checkout at $_wr_opened (requires git >= 2.31 for --path-format): $_wr_common" >&2
        return 1
    fi
    ( cd "$(dirname "$_wr_common")" && pwd -P )
}

# resolve_project_root <opened-folder-path>
# Prints the project root on stdout (git-derived, via resolve_primary_checkout
# above); exits 1 with a message on stderr if the primary checkout is not
# named `main`.
resolve_project_root() {
    _wr_opened="$1"
    _wr_main="$(resolve_primary_checkout "$_wr_opened")" || return 1
    case "$(basename "$_wr_main")" in
        main) : ;;
        *) echo "primary checkout is not named 'main': $_wr_main" >&2; return 1 ;;
    esac
    dirname "$_wr_main"
}

# literal_mount_source <opened-folder-path>
# Prints the directory Docker will actually bind-mount for
# source=${localWorkspaceFolder}/... Verified (see design body) to agree with
# Docker's real resolution, including through a symlinked ancestor OR a
# symlinked checkout itself: both a LOGICAL `cd "$opened/.."` (note: NOT
# `cd -P`) followed by `pwd -P`, and Docker's own /.. handling, collapse the
# trailing "component/.." pair lexically before resolving any remaining
# symlink, rather than resolving `component` first. This is a DIFFERENT (and
# for this purpose, the CORRECT) result than either (a) fully realpath-ing
# $opened first and then taking dirname, or (b) using `cd -P` for this step --
# `cd -P` resolves `component` as a symlink BEFORE applying `..`, which
# diverges from Docker (round-3 review, finding B3: `cd -P` here mounts
# $HOME through a symlink named `main` placed inside it, a real exploit
# reproduced with a live `docker run`). Do NOT add `-P` to the `cd` below.
literal_mount_source() {
    ( cd "$1/.." && pwd -P )
}

# home_is_at_or_under <candidate-root>
# Fails closed on unset/empty/non-absolute $HOME (F5). Both sides physically
# resolved (F2), trailing-slash-safe (M1's fixed pattern).
home_is_at_or_under() {
    _wr_root="$1"
    case "${HOME:-}" in
        /*) : ;;
        *) return 0 ;;   # unset, empty, or relative -> unsafe -> caller refuses
    esac
    _wr_home_p="$(cd "$HOME" && pwd -P)" || return 0
    _wr_root_p="$(cd "$_wr_root" && pwd -P)" || return 0
    case "$_wr_home_p" in
        "$_wr_root_p") return 0 ;;
        "${_wr_root_p%/}/"*) return 0 ;;   # M1/B4: the "/" MUST be inside the quotes -- "${x%/}"/* left
                                            # bare fails to match anything in bash (though not dash) when
                                            # $_wr_root_p is "/" (the stripped value is empty, and a quoted
                                            # empty prefix followed by an UNQUOTED /* is not the same case
                                            # pattern as one quoted string "empty/*"). Verified under both
                                            # bash and dash before relying on it (round-3 review, B4) --
                                            # the explicit `root == "/"` clause at both call sites is
                                            # ALSO kept regardless (belt-and-suspenders, not redundant).
        *) return 1 ;;
    esac
}
```

(`_wr_`-prefixed locals per m3, to avoid caller-namespace collisions — `sh` lacks `local` in the
strict POSIX sense but every shell this design targets — bash, and WSL2's bash — supports it;
prefixing is cheap insurance regardless.)

### `vibe_cading/tools/setup-workspace.sh`

Run once after cloning:

```bash
vibe_cading/tools/setup-workspace.sh
```

Steps, in order (sources `lib/workspace_root.sh`):

1. **Locate the primary checkout via `resolve_primary_checkout "$PWD"`** (this script is meant to
   be run from inside the checkout it ships in — `cd vibe-cading/main &&
   vibe_cading/tools/setup-workspace.sh` — but §Round-4 Review Response's B6 found that using
   `--show-toplevel` directly, instead of the shared `resolve_primary_checkout`, migrates the
   **worktree** the script happens to be invoked from rather than the primary checkout, if run
   from a worktree of a flat clone. `resolve_primary_checkout` is invariant to that — it always
   returns the one real checkout regardless of which worktree asked — so this is now the *same*
   primitive the guard uses, not a second, independently-reasoned one). Exit 1 on failure (git too
   old, not a repo, or any other git error) with the message `resolve_primary_checkout` already
   produces — do not swallow it or fall through to the migration branch (round-4, M13: a git
   failure must not be misread as "flat clone, offer to migrate").
2. **If not nested** (the checkout's basename isn't `main`, i.e. a flat clone): print the current
   location and require (interactive prompt, or `--yes` to accept non-interactively) the
   migration recipe already fixed in `#81` round 4 (temp-name two-step, since a direct
   `mkdir X && mv X X/main` fails twice over):
   ```bash
   name="$(basename "$checkout")"        # M6: derived, not the literal "vibe-cading"
   cd "$(dirname "$checkout")"
   mkdir "$name.tmp" || { echo "ERROR: $name.tmp already exists at $(pwd) -- remove or rename it and re-run." >&2; exit 1; }
   mv "$name" "$name.tmp/main" && mv "$name.tmp" "$name"
   ```
   **Before performing the `mv`:** two checks, in order.
   - **(M14) Refuse if `git -C "$checkout" worktree list --porcelain | grep -c '^worktree '`
     is more than 1** — i.e. any worktree besides the primary checkout already exists. Every
     worktree's `.git` file and every entry under `main/.git/worktrees/` holds an *absolute* path
     into the checkout being moved; the `mv` silently breaks all of them. **Round-5 note (F7):**
     this count also includes *stale/prunable* entries (a worktree directory removed by `rm -rf`
     rather than `git worktree remove` still counts). Verified: it correctly still refuses in that
     case (fails closed), but the actual remedy for a stale entry is `git worktree prune`, not
     removing a live directory — so the message names both possibilities explicitly: *"remove
     unwanted worktrees with `git worktree remove <path>`, or if one was deleted outside git,
     `git worktree prune`, then re-run."*
   - **(round-4, B5) Compute the prospective post-migration project root — `$checkout` itself**,
     **not** `dirname "$checkout"`. The migration nests the checkout one level deeper
     (`$checkout` → `$checkout/main`), so `$checkout` *becomes* the project root; it does not stay
     the checkout. (Round-4 found the round-3 draft's parenthetical — "unchanged by the migration,
     which only adds one path segment *below* it" — self-refuting: adding a segment below
     `$checkout` is exactly what makes `$checkout` the new root, not `dirname "$checkout"`. Tested
     directly: a flat clone at `$HOME/vibe-cading` — the mainstream case — must be **accepted**
     for migration; a checkout that *is* `$HOME` itself (e.g. a `git init`'d dotfiles-style home
     directory) must be **refused**. Verified both outcomes against this corrected predicate
     before writing it here, not assumed.) Run the same `home_is_at_or_under`/`== "/"` refusal
     from step 4 against `$checkout`.

   Failing either check exits 1 with no `mv` performed. **Per M2, the script does not continue
   past a successful migration** — it prints the new `main` path and exits 0 with: *"Layout
   migrated. Re-run this script from `<new-path>`."* — avoiding any reliance on
   `$0`/`$PWD`/sourced-lib paths the `mv` just invalidated. Declining the migration exits 1; no
   marker, no `docker/.env` write, nothing moved.
3. **Resolve the candidate project root** = `dirname(main_checkout)`, now guaranteed nested (this
   run only proceeds past step 2 when already nested, whether from a fresh clone or a
   just-completed re-run after migration).
4. **Refuse** (exit 1, explanatory message, no `docker/.env` write, no marker) if:
   - `home_is_at_or_under(root)` — subsumes `root == $HOME` (the `~/main` case) and `root` an
     ancestor of `$HOME` (`/home`, `/var/home`), fails closed on unset/empty/relative `$HOME`.
   - `root == /`, kept as its own explicit clause — **load-bearing, not redundant** (round 3, B4:
     even the trailing-slash-fixed glob pattern needed the `/` moved *inside* the quotes to work
     under bash; the standalone clause is kept regardless of that fix's correctness).
5. **Write/validate `$checkout/docker/.env`** (round-5, F9: explicit about *which* checkout's
   `docker/` — step 1 deliberately tolerates this script being run from a sibling worktree, and
   every worktree has its own `docker/`, so "inside the repo" alone is ambiguous; it is always the
   `main` checkout's, i.e. `<project root>/main/docker/.env`, gitignored):
   ```
   # Generated by vibe_cading/tools/setup-workspace.sh — safe to edit or delete.
   # A --force re-run REWRITES THIS FILE ENTIRELY (round-5, F8): if you hand-added
   # VIBE_PROJECT / VIBE_VIEWER_PORT to run a second checkout concurrently, re-add
   # them after a --force re-run; they are not preserved across it.
   VIBE_WORKDIR=<project root>/main
   ```
   (`VIBE_ROOT` dropped — grepped `docker/compose.yaml`: it is never read.) If `docker/.env`
   exists already: if its `VIBE_WORKDIR` already equals the resolved path, no-op; if it differs,
   refuse with a message showing both values and requiring `--force` to overwrite. **M7 —
   corrected claim, not a code fix:** this refusal is a **Compose-correctness** concern only, not
   a devcontainer-safety one — the guard (below) never reads `docker/.env`, so its ordering
   relative to the marker has no bearing on what the guard will accept. Compose is already
   documented-not-enforced (§Scope: Compose entry point); a stale `docker/.env` is something
   `--force` fixes on the next run, independent of the marker's state.
6. **Write the marker** at the project root: `<project-root>/.vibe-cading-project-root`,
   containing one line: the ISO date the check was performed (informational only — the guard
   checks existence, not content). Always outside the git repository (parent of `main`) — never
   needs a `.gitignore` entry.

### `.devcontainer/devcontainer.json` guard — object-form `initializeCommand`, marker **and** live mount-source re-check

`initializeCommand` already carries the `.claude-creds` seeding command
(`devcontainer.json:56` on `main` today). Replacing it with an array (F3) would silently delete
that seeding, and the seeding is load-bearing — `--mount type=bind` hard-fails on a missing
source, so a fresh clone's first container start would fail outright. This design keeps it,
adding the new check as a second, independent map entry:

```jsonc
"initializeCommand": {
    "seedClaudeCredentials": "mkdir -p ${localEnv:HOME}${localEnv:USERPROFILE}/.claude-creds/vibe-cading && { [ -f ${localEnv:HOME}${localEnv:USERPROFILE}/.claude-creds/vibe-cading/.credentials.json ] || cp ${localEnv:HOME}${localEnv:USERPROFILE}/.claude/.credentials.json ${localEnv:HOME}${localEnv:USERPROFILE}/.claude-creds/vibe-cading/.credentials.json 2>/dev/null || touch ${localEnv:HOME}${localEnv:USERPROFILE}/.claude-creds/vibe-cading/.credentials.json; }",
    "checkWorkspaceSetup": [
        "bash",
        "${localWorkspaceFolder}/vibe_cading/tools/check-workspace-setup.sh",
        "${localWorkspaceFolder}"
    ]
},
```

`checkWorkspaceSetup`'s array is new; `seedClaudeCredentials`'s string is byte-identical to the
existing `initializeCommand` value today — untouched by this design (m1: naming this correctly
matters specifically because this is the entry F3 exists to protect).

`check-workspace-setup.sh` (new, tracked; `#!/usr/bin/env bash` — this design's `initializeCommand`
always invokes it via `["bash", …]`, so the shebang is documentation, not the interpreter
selector; requires **git ≥ 2.31** for `--path-format`, called out in a header comment. **Round-5
correction (F1):** the actual distinction the lib makes is `resolve_primary_checkout`'s **git
failure** (surfaced via `2>&1`, not swallowed — covers "too old" and "not a repo" alike, since
both are just whatever git itself reports) **vs.** `resolve_project_root`'s separate **"resolved,
but not named `main`"** case. It does *not* distinguish "too old" from "not a repo" from each
other — both produce the identical git-failure message, because neither this script nor the human
reading its output needs to tell them apart, only "git" from "wrong name." An earlier draft of
this paragraph claimed the former distinction; round 5 found that claim didn't match the code
(the same B3/B8 class of defect: prose ahead of what the code actually does) — corrected here.
Sources `lib/workspace_root.sh` via `. "$(dirname "$0")/lib/workspace_root.sh" || exit 1` — `$0`
is the absolute path the CLI invoked, per the array-form `initializeCommand` entry above; takes
the opened folder as `$1`, arrives as `argv[1]`, never shell-interpolated):

```sh
#!/usr/bin/env bash
set -u
. "$(dirname "$0")/lib/workspace_root.sh" || exit 1

opened="$1"
git_root="$(resolve_project_root "$opened")" || exit 1          # F4-safe
mount_src="$(literal_mount_source "$opened")"                    # B1/B3: what Docker will ACTUALLY mount (plain cd, NOT cd -P -- see lib comment)

if [ "$mount_src" != "$git_root" ]; then
    echo "REFUSE: this checkout's git-resolved project root ($git_root) does not" >&2
    echo "match what would actually be mounted ($mount_src)." >&2
    echo "This happens when a worktree (or the opened folder itself) is not" >&2
    echo "exactly a sibling of main inside its project directory -- e.g. a" >&2
    echo "worktree created elsewhere, a subdirectory of main opened directly," >&2
    echo "or a worktree nested more than one level deep." >&2
    exit 1
fi
if [ "$mount_src" = "/" ] || home_is_at_or_under "$mount_src"; then
    echo "REFUSE: would bind-mount $mount_src, which is \$HOME or an ancestor of it." >&2
    exit 1
fi
if [ ! -f "$mount_src/.vibe-cading-project-root" ]; then
    echo "ERROR: no project-root marker at $mount_src." >&2
    echo "Run vibe_cading/tools/setup-workspace.sh once after cloning." >&2
    exit 1
fi
```

Three independent conditions, all required: git-derived root and live mount source must agree
(B1/B3), the mount source must independently re-pass the `$HOME`/`/` predicate at start time (not
only once, historically), and the marker must be present. Verified end-to-end below — a rogue
worktree outside the project directory (git-valid, requires no special privilege), and a symlink
named `main` placed inside `$HOME` (round 3, B3 — no `git worktree` needed at all), are both
refused even though the marker at the *real* project root is present and valid; a legitimate
sibling worktree still proceeds.

### T5: de-hardcoding `workspaceMount`/`workspaceFolder` (this design's own task — see B2)

Neither `main` nor any branch this design forks from carries a de-hardcoded mount expression —
`#83`, the PR that introduced one, is being closed/superseded, not merged. This design pulls that
change in directly, carrying forward `#83`'s own verified reasoning (Docker normalizes `/..`,
substitutions resolve per-field, source==target preserves path identity) since the mount
*expression* itself isn't what round 2 found wrong — only the false assumption that it already
existed on this branch:

```diff
-    "workspaceMount": "source=/workspaces/vibe-cading,target=/workspaces/vibe-cading,type=bind",
-    "workspaceFolder": "/workspaces/vibe-cading/main",
+    "workspaceMount": "source=${localWorkspaceFolder}/..,target=${localWorkspaceFolder}/..,type=bind",
+    "workspaceFolder": "${localWorkspaceFolder}",
```

`PYTHONPATH` moves to `${containerWorkspaceFolder}` (same substitution `#83` used) rather than
repeating any literal.

**Round-5 addition (F5) — two consequences of `workspaceFolder` now following whatever was
opened, neither addressed by `#83`'s original diff (which this design is not blindly re-adopting
wholesale, per the note above about only carrying forward what round 2 didn't find wrong):**

1. **A stale in-file comment.** The current `devcontainer.json` (lines 33-38 on `main` today)
   justifies the single project-root mount partly on *"The container always opens in `main` (the
   only checkout that runs Claude); work in sibling worktrees by `cd`-ing to them within this same
   container."* That statement becomes false the moment `workspaceFolder` follows the opened
   folder rather than a fixed literal — this design's own Tests row 10 exercises opening a sibling
   worktree directly. T5 updates this comment to state plainly that any checkout under the mounted
   root may be opened directly, not only `main`, and that the guard (T3/T4) validates whichever one
   is.
2. **`postCreateCommand`'s scope must widen with it.** Today `postCreateCommand` unconditionally
   targets `main` (the only thing ever opened); after T5 it targets
   `${containerWorkspaceFolder}` — *whatever* was opened. Open a sibling worktree directly and
   `main` itself is left neither `chown`ed nor marked `git safe.directory` — a real regression,
   since that worktree's git operations still write into `main/.git/worktrees/`, which needs the
   same ownership/trust as the worktree itself. **Round-6 finding (F1, blocking) and its fix:** the
   round-5 draft's answer here interpolated `${containerWorkspaceFolder}` **directly into the
   `postCreateCommand` shell string** — reproduced end-to-end as exactly the injection class this
   design exists to close (§"Why the prior approach failed" item 2, forbidden by Success
   Criterion 3, the same ground B7 rejected round 3's `initializeCommand` fallback on): a host
   directory named `pr$(touch PWNED)oj` executed the embedded command at `postCreateCommand` time,
   *after* the guard had already ACCEPTed (the guard has no visibility into `postCreateCommand` —
   guard-pass is the precondition for reaching this vector, not a defense against it). **Corrected
   fix, verified against the same hostile fixture (no execution, correct path resolved):** pass the
   opened path through `remoteEnv` — a real environment variable set inside the container, not
   text re-interpolated into a shell command string — and reference it as a shell variable, never
   as a devcontainer substitution, inside `postCreateCommand`:
   ```jsonc
   "remoteEnv": {
       "SSH_AUTH_SOCK": "/ssh-agent",
       "PYTHONPATH": "${containerWorkspaceFolder}",
       "VIBE_OPENED": "${containerWorkspaceFolder}"
   },
   ```
   ```bash
   # inside postCreateCommand, as a literal string -- $VIBE_OPENED and $VIBE_ROOT
   # are real shell variable references, NOT devcontainer substitutions; nothing
   # here is built by interpolating a host path into the command text.
   : "${VIBE_OPENED:?VIBE_OPENED unset -- remoteEnv did not reach postCreateCommand}"
   VIBE_ROOT="$(dirname "$VIBE_OPENED")"
   sudo chown -R "$(id -u):$(id -g)" "$VIBE_ROOT"
   for d in "$VIBE_ROOT"/*/; do
       if [ -e "${d}.git" ]; then git config --global --add safe.directory "${d%/}"; fi
   done
   ```
   **Round-8 addition (finding 1, blocking):** without the `: "${VIBE_OPENED:?…}"` guard, an
   unset `VIBE_OPENED` (`remoteEnv` misconfigured, or a host that ignores it) makes
   `dirname ""` silently resolve to `.` — the postCreate **cwd**, i.e. whatever was opened — so
   `chown -R … .` narrows back to the un-widened, pre-F5 behavior, the loop matches nothing, and
   **the whole thing exits 0**: `devcontainer up` reports success, `~/.gitconfig` never gets a
   `safe.directory` entry, and nothing points at why. This is *exactly* what T10 is supposed to
   catch on Antigravity — but a human running T10 by opening `main` directly would see it "work"
   (root narrows to `main`, which looks correct), so the failure is invisible unless a sibling
   worktree is opened too. **The `: "${VIBE_OPENED:?msg}"` form, placed OUTSIDE any `$(...)`
   subshell, is required** — the same fail-fast expansion written *inside* a subshell can still
   let the surrounding chain continue silently, depending on exactly where it's consumed.
   **Round-9 correction:** the specific example first cited here (`VIBE_ROOT="$(dirname
   "${VIBE_OPENED:?msg}")"`, as a standalone assignment) turns out to *not* silently continue — a
   failed assignment's status still short-circuits a following `&&`, verified directly. The shape
   that genuinely does continue silently is the substitution consumed **inside a `for` loop's word
   list** (e.g. `for d in "$(dirname "${VIBE_OPENED:?msg}")"/*/; do …`) — the loop's word-list
   expansion failing just produces an empty/unexpected glob, and the `for` proceeds (or, per
   round-7's finding, degenerately no-ops) with exit 0 regardless. Either way, the standalone
   top-level `:` form used above is the one verified to fail loudly in every arrangement tested,
   which is why it's specified rather than folding the check into an existing expansion. T10's
   pre-merge check must have a concrete observable, not just "the container starts": run
   `git config --global --get-all safe.directory` inside the started container and confirm it
   lists every top-level checkout under the project root, not zero and not just the one opened.
   **Round-7 correction (finding 1, blocking):** the loop body was originally written as
   `[ -e "${d}.git" ] && git config …` — a `for` loop's exit status is its **last executed
   command's**, so whenever the lexically-last top-level directory has no `.git`, the `&&`'s
   left side evaluates false, nothing runs, and the whole loop (and therefore the whole `&&`-chained
   `postCreateCommand` this fragment lands in — see `.devcontainer/devcontainer.json`'s existing
   single-line chain) exits 1, aborting every remaining step (the SSH-key copy, `chmod`s) silently
   without a specific error pointing at this line. Reproduced with a real `devcontainer up` against
   a project root ending in a non-git directory: `postCreateCommand … failed with exit code 1`.
   This repo's current project root happens to hold only git checkouts, which is exactly why it
   would have shipped unnoticed. **The `if`/`fi` form above always returns 0 regardless of match
   count** (verified under both `bash` and `dash`, including the zero-match case) — use it, not the
   `&&`-only one-liner, in the implementation.
   The membership test for the loop is `-e "${d}.git"` over every top-level directory, **not**
   `git worktree list`: the real project root can (and, in this repo, does) also hold sibling
   clones that are not worktrees of `main` at all (e.g. a wiki clone) — those still need
   `safe.directory` for git operations to work inside them, and a worktree-specific enumeration
   would silently skip them (round-6 review, minor finding 4).

### Scope: layout (nested only — flat is a migration waypoint, not a supported end state)

A flat clone is detected and offered mandatory migration by `setup-workspace.sh`; it is never a
state the setup script completes successfully in. Consequence: `README.md`'s Quick start changes
from clone→open to clone→setup→open — stated as a requirement in the brief's target design (§3),
not new scope.

### Scope: Compose entry point (documented requirement, not runtime-enforced — stated explicitly)

`docker/compose.yaml`'s `dev` service has no equivalent hook to `initializeCommand` — Compose has
no pre-mount lifecycle step, and this design does not bolt one on (an in-container check runs
after the mount already happened; a wrapper script around `docker compose up` is a second
mechanism this design's whole point was to avoid multiplying). `CONTRIBUTING.md` states that
`setup-workspace.sh` must be run before `docker compose up`. Compose's mount expression
(`..` relative to `docker/`, i.e. the repo — narrower than the devcontainer's project-root mount
either way) and its hardcoded fallback default are both untouched by this design. The asymmetry
is intentional and named: Compose is always a human typing an explicit command, never an
automatic "Reopen in Container" trigger.

### Scope: OS (Linux / macOS / WSL2 only, stated explicitly)

Both scripts are host-side shell (`bash`/POSIX `sh`); they do not run under native Windows
PowerShell/cmd. Stated explicitly in both scripts' header comments and `CONTRIBUTING.md`:
**supported host shells are Linux, macOS, and WSL2** (matching the WSL2-with-Linux-filesystem
case `devcontainer.json` already documents as the recommended Windows path). No speculative
`.ps1`; revisit only if a Windows-native contributor actually shows up.

## Open decisions — resolved

1. **Marker filename**: `.vibe-cading-project-root`, content an informational timestamp only.
2. **Marker gitignore status**: moot — nested-only means the marker is always outside the git
   repository. No `.gitignore` entry needed.
3. **Windows scope**: explicitly out of scope beyond WSL2. See §Scope: OS.

## Verification (reproduced, not assumed — content spans rounds 3-5; see per-round Review Response sections above and below for rounds 6-10)

| Claim | Method | Result |
|---|---|---|
| Object-form `initializeCommand`, exact two-entry shape (string + array), both run, failure in either aborts creation | `@devcontainers/cli` 0.88.0, two-entry fixture | Both entries executed; a failing `checkWorkspaceSetup` produced `"outcome":"error"`, zero containers created |
| Array-form entry passes path as data | Workspace folder literally containing `` $(touch …) `` | Reached `argv[1]` verbatim, no execution (re-confirmed rounds 2 and 3, exact object-form shape) |
| `literal_mount_source` — **plain `cd`, then `pwd -P`** — agrees with what Docker actually mounts, through a symlinked ancestor directory | Fixture: `sym-proj -> real-proj`, opened `sym-proj/main` | Both resolve through the symlink to `real-proj`; `docker run -v` confirmed via container `ls` |
| Same, when the checkout itself (`main`) is a symlink to an unrelated target | Fixture: `proj2/main -> elsewhere/deep` | Both collapse to `proj2` (the trailing `main/..` pair is cancelled lexically before any symlink in `main` is followed) — **not** `elsewhere`, confirmed via container `ls` |
| **B3 — the `cd -P` variant (what the design's prose incorrectly said before round 3) diverges from Docker and reopens the exposure** | Fixture: `ln -s /srv/proj/main "$HOME/main"`, opened `$HOME/main`. Ran both variants side by side | Plain `cd` (specified): `mount_src=$HOME`, mismatches git root, REFUSE — correct. `cd -P` (what the prose wrongly said): `mount_src` resolves through the symlink to the real root, matches, ACCEPT — **wrong**; a live `docker run` with this variant mounted `$HOME` read-write and a planted `~/.ssh/id_rsa` was read from inside the container. This is why every prose reference was corrected in §Round-3 Review Response and the code comments now carry an explicit "do NOT add `-P`" warning |
| B1 fix (round 2) holds: a worktree created outside the project directory is refused even though the marker at the real root is valid | Standalone harness mirroring `check-workspace-setup.sh`'s exact logic: `git_root` (via `--git-common-dir`) vs. `mount_src` (via `literal_mount_source`) for a worktree added under a simulated `$HOME` | Mismatch detected, REFUSE |
| No false reject: a legitimate sibling worktree, a subdirectory of `main`, and a worktree nested two levels inside the project all resolve/refuse correctly | Same harness, all three shapes | Sibling worktree: match, ACCEPT. Subdir-of-`main` and nested worktree: mismatch, REFUSE (correct — neither is `main` itself or a proper sibling) |
| `home_is_at_or_under` — 14 round-1/2 cases plus round-3's additions (root-is-prefix-of-HOME-without-separator both directions, spaces, unicode, glob metacharacters in the root, nonexistent root, root-is-a-file, `HOME=/`) | Standalone harness, bash and dash both | All correct except `root == "/"` — see B4 |
| **B4 — the round-2 "fixed" pattern `"${_wr_root_p%/}"/*` still failed under bash** (only worked under dash/`sh`, not the shell the guard actually invokes) | Harness, `root_p="/"`, `HOME=/home/alice`, run explicitly under `bash` | round-2 pattern: ACCEPT (wrong — round-2's own verification row asserting REFUSE here was run under the wrong shell). **Fixed pattern** `"${_wr_root_p%/}/"*` (slash moved inside the quotes): REFUSE under both bash 5.2 and dash — confirmed |
| `resolve_project_root` on worktrees / flat clone | Sibling worktree and subdir-of-`main` both resolve to the same root; flat clone refused (`primary checkout is not named 'main'`) | Correct (F4 re-confirmed) |
| `docker/.env` gitignored | `.gitignore:43` `.env`, unanchored, matches at any depth | Confirmed |
| Marker-present + mount-source-matches → `devcontainer up` proceeds, `.claude-creds` still seeded | Fixture with both `initializeCommand` entries and a valid marker | Container starts, both entries' effects present |
| T5's premise: no branch this design forks from already carries a de-hardcoded mount expression | Read `.devcontainer/devcontainer.json` on `feat/devcontainer-setup-script` directly | Confirmed — hardcoded literal present; T5's diff applied and re-verified end-to-end (`SRC`/`DST` both resolve to the opened project root, `RW=true`, substitutions correct in `PYTHONPATH`/`postCreateCommand`) |
| `docker inspect` / `--mount` normalization of `/..`, `destination can't be '/'` refusal, non-existent-source failure | Carried from `#83` (unchanged by this design) | Not re-run |

Every throwaway container created across all three review rounds was removed (`docker rm -f`).
Scratch directories under `/tmp` from review sessions could not be removed in this session
(`rm -rf` denied by sandbox policy) — outside any tracked path, flagged for manual cleanup.

## Implementation Plan

- [x] **T1** — `vibe_cading/tools/lib/workspace_root.sh`: `resolve_primary_checkout`,
      `resolve_project_root`, `literal_mount_source`, `home_is_at_or_under` (as specified above,
      scoped locals), AGPLv3 header.
- [x] **T2** — `vibe_cading/tools/setup-workspace.sh`: locate checkout via `resolve_primary_checkout`
      (§step 1); mandatory flat→nested migration with `--yes` for non-interactive acceptance
      (§step 2) — including the **M14 refusal** if `git worktree list --porcelain` shows more than
      the primary checkout, and the **B5 pre-`mv` safety check against `$checkout` itself** (not
      `dirname "$checkout"`); `$HOME`/`/` refusal (§step 4); `docker/.env` write-or-validate at
      `$checkout/docker/.env` with `--force` to overwrite (§step 5, and F9: explicit about *which*
      checkout's `docker/`, since this script may run from a worktree); marker write (§step 6);
      `$name.tmp` pre-existing-collision message; exit-after-migrate, no self-relocation attempt;
      AGPLv3 header.
- [x] **T3** — `vibe_cading/tools/check-workspace-setup.sh`: git-root vs. live-mount-source
      agreement check, live `$HOME`/`/` re-check, `.vibe-cading-project-root` marker check — all
      three required; shebang, `set -u`, explicit `|| exit 1` on sourcing the lib; header comment
      states git ≥ 2.31 and the **actual** failure-mode distinction the code makes (git-failure vs.
      not-named-`main` — **not** "too old" vs. "not a repo," which round 5 found this file's own
      draft prose still claimed after B8 fixed the *lib's* comment but not this one — F1); AGPLv3
      header.
- [x] **T4** — `.devcontainer/devcontainer.json`: `initializeCommand` becomes object-form with
      the existing credentials-seeding string preserved verbatim and the new
      `checkWorkspaceSetup` array as the second entry.
- [x] **T5** — `.devcontainer/devcontainer.json`: de-hardcode `workspaceMount`/`workspaceFolder`
      per the diff above (this design's own change — not inherited from any branch); update the
      stale in-file comment claiming *"the container always opens in `main`"* (round 5, F5 — no
      longer true once `workspaceFolder` follows whatever was opened); extend
      `postCreateCommand`'s `safe.directory`/`chown` to cover the **whole mounted project root**,
      not only `${containerWorkspaceFolder}` — round 5 found that opening a sibling worktree
      directly would otherwise leave `main` un-chowned and not marked `safe.directory`, even though
      that worktree's git operations write into `main/.git/worktrees/`. **Round-6 correction:** do
      this via the `remoteEnv`-indirection form specified in §T5 above (`VIBE_OPENED` env var,
      `$VIBE_OPENED`/`$VIBE_ROOT` as real shell variables inside `postCreateCommand`) — **not** by
      interpolating `${containerWorkspaceFolder}` directly into the `postCreateCommand` string,
      which round 6 found reproducibly reintroduces the injection this design exists to close (F1),
      and which round 6 also found used the wrong, unbraced `$containerWorkspaceFolder` token (not
      a devcontainer substitution at all, silently unset — F2). Loop over top-level directories
      using `-e "${d}.git"`, not `git worktree list`, so non-worktree sibling clones under the
      project root are also covered (round-6, minor finding 4).
- [x] **T6** — `README.md` Quick start: clone → `setup-workspace.sh` → Reopen in Container.
- [x] **T7** — `CONTRIBUTING.md`: "where to clone" (unconditional) / "running it without VS Code"
      (state the documented-not-enforced Compose requirement) / OS scope statement.
- [x] **T8** — `docker/compose.yaml`: no change (mount expression + fallback defaults untouched;
      confirmed — grepped, only `VIBE_WORKDIR`/`VIBE_PROJECT`/`VIBE_VIEWER_PORT`/`USER_UID`/
      `USER_GID` are consumed).
- [x] **T9 (round 3, M9)** — `tests/tools/test_workspace_root.py`: pytest module shelling out to
      the four **lib** functions — `resolve_primary_checkout`/`resolve_project_root`/
      `literal_mount_source`/`home_is_at_or_under` — run under **both** `bash` and `sh`, covering
      every lib-level edge case in §Verification (symlinked `main`, symlinked ancestor, rogue
      worktree, sibling worktree, subdir-of-`main`, nested worktree, `root == /`, unset/empty/
      relative `$HOME`, spaces/glob characters in paths). CI-enforced. Would have caught **B4**
      mechanically (a shell-specific pattern bug in the code); would **not** have caught **B3** (a
      prose/comment defect against already-correct code — see the M9 correction above for why that
      class needs the in-code warning, not a test, as its mitigation). **Scope is deliberately
      narrow to these four functions — see T9b for what it does NOT cover.**
- [x] **T9b (round 5, F3; scope fixed round 6, finding 3)** — `tests/tools/test_setup_workspace.py`
      (pytest, matching this repo's existing shell-testing convention — `tests/tools/` holds
      pytest modules that shell out, e.g. `test_check_doc_links.py`; there is no precedent for a
      standalone `.sh` test file, and CI's `pytest tests/` would not collect one anyway — round 6
      found the round-5 draft left this undecided and consequently left T9b **out** of CI, unlike
      T9). **Naming note (round 7, finding 3, non-blocking):** the module covers both
      `setup-workspace.sh` *and* `check-workspace-setup.sh` end-to-end — `test_setup_workspace.py`
      slightly undersells that scope; `test_workspace_scripts.py` is an equally fine alternative,
      pick either during implementation, it does not collide with T9's `test_workspace_root.py`
      either way. Drives both scripts as subprocesses with `--yes`/`--force`. **CI-enforced**, same
      as T9. End-to-end fixtures for `setup-workspace.sh` and `check-workspace-setup.sh` **as
      scripts**, not just the lib functions they call — specifically the cases T9 structurally
      cannot cover because the lib function behaves identically regardless of which caller argument
      is right or wrong: **the B5 case** (setup-workspace.sh passes `$checkout` to the safety
      check, not `dirname "$checkout"` — a flat clone at `$HOME/vibe-cading` must be accepted for
      migration, `$HOME` itself must be refused), **the M14 case** (migration refuses when
      `git worktree list --porcelain` shows more than the primary checkout, including a *stale*
      entry per round-5 F7), and the full happy-path/refusal sequences from the Tests table below.
- [x] **T9c (round 7, finding 2; token set + scope fixed round 8, findings 2–4; item (d) rescoped round 9)** — a small,
      Docker-free, **CI-enforced** static test (in T9b's module — folding it in also resolves
      round-8 finding 4, that T9c wasn't referenced from Tests row 17 / Success Criterion 8).
      **Round-9 note (minor):** `.devcontainer/devcontainer.json` is JSONC (`//` comments — 41
      lines of them today, T5 adds one more), so `json.loads` fails outright; there is no JSON5/
      JSONC parser in this project's dependencies. Strip `//`-style comments with a small stdlib
      regex/line-scan **that does not touch string literals** (a comment stripper naive about
      quoting could corrupt a path value containing `//`, though none currently does) before
      parsing, or extract the two target fields (`postCreateCommand`, `initializeCommand`) via a
      comment-tolerant regex instead of full JSON parsing — either is fine, pick one during
      implementation. T9c parses the tracked `.devcontainer/devcontainer.json` (however it gets
      there) and asserts:
      - **(a)** `postCreateCommand`'s string contains **none** of the specific devcontainer
        substitution tokens — `${localWorkspaceFolder}`, `${containerWorkspaceFolder}`,
        `${localWorkspaceFolderBasename}`, `${containerWorkspaceFolderBasename}`,
        `${devcontainerId}`, `${localEnv:...}`, `${containerEnv:...}` — matched by an **explicit,
        enumerated pattern**, not a bare "no `${...}`" check. **Round-8 correction:** the literal
        "no `${...}` token" wording from round 7 would false-positive on this same fragment's own
        `${d}`/`${d%/}` — ordinary shell parameter expansions introduced by round 7's `if`/`fi`
        loop fix, not devcontainer substitutions. Verified: the enumerated pattern matches zero
        times against the current fragment and matches once against the round-5 defective
        `${containerWorkspaceFolder}` form, before writing it into this document.
      - **(b)** `postCreateCommand`'s string contains the literal substring `$VIBE_OPENED` (a
        real shell variable reference) **and** `remoteEnv` defines a `VIBE_OPENED` key — this is
        the cheap complement round 8 added for **finding 1** (the unset-`VIBE_OPENED` silent
        no-op): it doesn't reproduce the runtime failure, but it catches the *editing* mistake
        that would reintroduce it (e.g. a future edit renaming the `remoteEnv` key without
        updating the reference, or vice versa) — no Docker needed for that class either.
      - **(c)** `initializeCommand`'s `checkWorkspaceSetup` entry remains array-form (guards F3's
        class the same way).
      - **(d, round-8 finding 3; scope corrected round 9, blocking finding)** A **non-Docker
        fixture** executing **only the T5 fragment itself** — the `: "${VIBE_OPENED:?…}"` guard
        line, the `VIBE_ROOT` assignment, and the `safe.directory` loop, `&&`-joined exactly as
        they are joined in the shipped `postCreateCommand` — **not** the full chain. **Round-9
        correction:** feeding the *entire* composed `postCreateCommand` string (as round 8's
        wording literally said) is both unimplementable and unsafe as a CI check: the tail's
        `sudo chown`/`mkdir -p "$HOME/.ssh"`/host-SSH-copy/`chmod` steps either fail immediately on
        any host without passwordless `sudo` (this design/review environment included — the
        assertion would be red on arrival, and identically so whether the loop is fixed or buggy,
        so it would not actually be diagnostic even where it happens to run) or, on a host with
        passwordless `sudo` (e.g. GitHub Actions' default runner), **silently mutate the invoking
        user's real `~/.gitconfig` and `~/.ssh` permissions** — reproduced both ways before
        settling on the corrected scope below. Run the isolated fragment with:
        - **`HOME` pointed at a fixture `tmp_path`**, so `git config --global --add safe.directory`
          writes to the fixture's `.gitconfig`, never the invoking user's real one;
        - **`VIBE_OPENED`** set to a fixture path whose lexically-last sibling under its parent is
          not a git checkout;
        - a **negative control**: assert the shipped `if`/`fi` form exits **0** and reaches a
          post-loop sentinel, **and** that the round-7-buggy `&&`-only form exits **non-zero** on
          the *same* fixture — without both directions, the test cannot prove it still detects the
          class it exists to guard (a check that only ever asserts one form is red-or-green is not
          distinguishing "the fragment is right" from "the fixture happens to pass either way").
        This is the actual CI-enforced regression guard for round-7's `for`-loop finding, which
        (a)-(c) above do **not** cover (they are static/lexical checks; the loop-exit-status class
        needs an actual execution, but of the fragment under test, not of steps unrelated to it).
        Tests row 15c is this fixture's manual precursor; T9c's job is to make the isolated,
        `HOME`-scoped version of it CI-enforced, not the full chain.
      Durable per this project's Post-Fix Hardening convention (`vibe/INSTRUCTIONS.md` §4) — this
      T5 fragment has now been wrong in three consecutive rounds (5, 6, 7) before converging in
      round 8; a mechanical, CI-enforced assertion covering all of (a)-(d) is what stops a fourth
      recurrence during any future edit to this file, which nothing prior to this round did.
- [ ] **T10 (round 3, M8; fallback removed round 4, B7; scope widened round 6)** — Pre-merge
      **hard gate**, not a manual nice-to-have: confirm object-form `initializeCommand` (T4), the
      de-hardcoded mount expression (T5), **and the `remoteEnv`-indirection form of
      `postCreateCommand` (T5, round-6 fix for F1/F2)** all work from Google Antigravity, not only
      `@devcontainers/cli`/VS Code. No Antigravity binary is available in this design/review
      environment. **There is no fallback if this fails** — chaining commands into one string (the
      round-3 draft's proposed `initializeCommand` fallback, and the shape round 6 found reproduced
      in round 5's `postCreateCommand` draft) reintroduces the exact injection vector this design
      exists to close (round-4 review, B7; round-6 review, finding 1). If Antigravity does not
      support object-form `initializeCommand` or `remoteEnv`-derived shell variables in
      `postCreateCommand`, this design returns to authoring, not to a weaker shipped mechanism.
      **Round-8 addition (finding 1):** "the container starts" is not a sufficient pass condition —
      round 8 found a `remoteEnv` misconfiguration can leave `postCreateCommand` exiting 0 having
      silently done none of its provisioning (caught structurally by the `: "${VIBE_OPENED:?…}"`
      guard in §T5 above, but T10 still needs its own concrete check since it exists specifically
      to catch host-*specific* behavior differences). T10's pass condition is: open a sibling
      worktree directly (not `main`), then inside the running container run
      `git config --global --get-all safe.directory` and confirm it lists **every** top-level
      checkout under the project root — not zero entries, and not only the one opened.

## Tests

**Attribution note (round 5, F3):** T9 covers only the four lib functions in isolation — it cannot
distinguish "the script called the lib function with the right argument" from "with the wrong
one," which is exactly the class of bug B5 and M14 were. Rows exercising `setup-workspace.sh` or
`check-workspace-setup.sh` **as scripts** are attributed to **T9b**, not T9, below.

| # | Test description | Expected assertion | File / location |
|---|---|---|---|
| 1 | `setup-workspace.sh` refuses at `$HOME` (nested at `~/main`) | exit 1, no `docker/.env`, no marker | T9b |
| 2 | `setup-workspace.sh` refuses at `/` | exit 1 | T9b |
| 3 | `setup-workspace.sh` refuses at `$HOME` reached via a symlinked `/home` | exit 1 | T9b |
| 4 | `setup-workspace.sh` fails closed with `HOME` unset | exit 1 | T9b |
| 5 | `setup-workspace.sh` nested happy path | `docker/.env` written, then marker, exit 0 | T9b |
| 6 | `setup-workspace.sh` flat input, migration accepted, migrated root is the mainstream `$HOME/vibe-cading` shape (round-4, B5) | exits 0 after migration with re-run instructions, no marker yet | T9b |
| 6b | `setup-workspace.sh` flat input where the checkout itself *is* `$HOME` (round-4, B5's negative case) | refuses the migration itself, before any `mv` | T9b |
| 7 | Re-running after migration | nested happy path (test 5) from the new location | T9b |
| 7b | `setup-workspace.sh` invoked from a worktree of a flat clone (round-4, B6) | migrates the primary checkout, not the worktree it was invoked from | T9b |
| 7c | `setup-workspace.sh` migration attempted while a second worktree already exists (round-4, M14) | refuses, no `mv` | T9b |
| 8 | `setup-workspace.sh` flat input, migration declined | exit 1, no marker, no `docker/.env` | T9b |
| 9 | `setup-workspace.sh` re-run against a `docker/.env` with a stale `VIBE_WORKDIR` | refuses without `--force`, marker not (re)written | T9b |
| 10 | `check-workspace-setup.sh` run from a legitimate sibling worktree | `mount_src == git_root`, passes (given a valid marker) | T9b |
| 11 | `check-workspace-setup.sh` run from a worktree created outside the project directory | `mount_src != git_root`, REFUSE — even with a valid marker at the real root | T9b |
| 12 | `check-workspace-setup.sh` run against `$HOME/main` where `main` is a symlink to the real nested checkout (round-3, B3's exploit case — no worktree involved) | `mount_src == $HOME`, mismatches `git_root`, REFUSE | T9b |
| 13 | `home_is_at_or_under "/"` under `bash` specifically (round-3, B4) | REFUSE | T9 (lib-level — this one genuinely is a direct lib-function call) |
| 13b | `resolve_primary_checkout` against a non-repo directory | distinct, non-swallowed error message (git's own stderr surfaced, not `2>/dev/null`-discarded); not misread as "flat clone" by the caller | T9 (lib-level; the pre-2.31-git half of B8's claim is untestable without a second git binary — noted, not gating) |
| 14 | `devcontainer up`, full fixture, no marker | aborts before container creation | manual, throwaway fixture, re-run against the real tracked scripts post-implementation |
| 15 | `devcontainer up`, full fixture, valid marker + matching mount source | proceeds, `.claude-creds` still seeded, mount matches T5's expression, sibling `main` still `chown`ed/`safe.directory` per T5's widened `postCreateCommand` (round-5, F5) | manual (full CLI round-trip; T9/T9b cover the scripts and lib in isolation, not the real container start) |
| 15b | `devcontainer up` against a project root containing a shell-metacharacter host directory name (e.g. `` pr$(touch PWNED)oj ``), full fixture through `postCreateCommand` | correct `VIBE_ROOT` resolved via `$VIBE_OPENED`, no `PWNED` artifact created, no injected command executes (round-6, finding 1 — this is the regression test for the `remoteEnv`-indirection fix) | manual, throwaway fixture, re-run against the real tracked `devcontainer.json` post-implementation |
| 15c | `devcontainer up` against a project root whose **lexically-last** top-level directory is not a git checkout (round-7, finding 1) | `postCreateCommand` exits 0, every step after the `safe.directory` loop still runs (SSH copy, `chmod`s) — not silently aborted | manual, full CLI round-trip; **T9c's item (d)** (round-8 correction: items (a)-(c) are static/lexical and cannot detect a loop-exit-status bug — only (d)'s actual `sh -c` execution can) is the CI-enforced regression guard for this specific class |
| 15d | `devcontainer up` with `VIBE_OPENED` absent from `remoteEnv` (round-8, finding 1) | `postCreateCommand` aborts loudly (non-zero exit, explicit message) rather than succeeding with zero provisioning done | manual, full CLI round-trip; T9c item (b) is the static (editing-mistake) complement, not a substitute for exercising the runtime guard itself |
| 16 | `check_doc_links.py` | green | CI |
| 17 | Full suite, including T9's, T9b's, and T9c's new/extended modules under both `bash` and `sh` | green | CI |

## Success Criteria

1. A fresh clone that has not run `setup-workspace.sh` cannot start a devcontainer that
   bind-mounts anything wider than the (nested) project directory it actually occupies.
2. `~/main`, any layout where `$HOME` is at/under the resolved root (including via a symlink), or
   any worktree opened from outside its project directory, is refused **live, at start time** —
   not merely by a marker's historical existence.
3. No path reaching a shell is ever built by string interpolation in either new script.
4. The pre-existing `.claude-creds` seeding in `initializeCommand` keeps working unchanged.
5. `workspaceMount`/`workspaceFolder` are de-hardcoded as part of this PR (not assumed inherited).
6. `README.md`/`CONTRIBUTING.md` describe the actual required flow — no undocumented mandatory
   step, no broken Quick start.
7. `#81` and `#83` are both superseded (closed, referencing the new PR) once this merges.
8. The shared-lib predicates are CI-enforced (T9), under both `bash` and `sh`, not left to
   manual/one-off verification — round 3 found one of them correct under one shell but not the one
   actually used (B4); T9 catches that class of defect going forward. Both scripts' end-to-end
   behavior (including caller-argument-correctness cases like B5/M14 that T9 structurally cannot
   reach) is likewise CI-enforced via **T9b** (round 6, finding 3 — T9b was in scope but not
   declared CI-enforced in the round-5 draft). The `devcontainer.json` `postCreateCommand`/
   `initializeCommand` fragment — the section wrong in three consecutive rounds (5, 6, 7) — is
   CI-enforced via **T9c** (round 7, finding 2; token set and execution-based item (d) fixed
   rounds 8-9), covering the injection-token class, the `VIBE_OPENED` wiring, `initializeCommand`'s
   array-form, and (via actual `bash`/`sh` execution of the isolated fragment, `HOME`-scoped, not
   just static parsing) the loop-exit-status
   class round 7 found. It does not, and cannot,
   catch B3's class (correct code, incorrect surrounding prose) — that class's mitigation is the
   loud in-code warning added in response to B3, kept as an independent defense, not superseded by
   T9.
9. Object-form `initializeCommand` and the de-hardcoded mount expression are confirmed working
   under Google Antigravity before merge (T10), not merely under `@devcontainers/cli`.

## Out of Scope

- Native Windows (non-WSL2) support.
- Flat clone as a permanently supported end state.
- Runtime-enforcing the Compose entry point (documented requirement instead).
- Changing the image build or anything from the already-merged `#82`.
- A machine-parsed marker format (existence-only is sufficient).

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| A contributor manually creates the marker file without running the real checks | Accepted — same trust boundary as any local dev setup step; the live mount-source re-check (B1 fix) means a forged marker alone still can't authorize a mismatched mount, only a mount that's already git-valid and passes the `$HOME`/`/` predicate |
| Case-insensitive filesystem (macOS APFS default) could theoretically defeat the string-based comparison if `$HOME` and the root differ only in case | Accepted residual gap — macOS's default `$HOME` isn't reached via the kind of default symlink indirection that made F2/B1 concrete; revisit if a concrete case surfaces |
| Compose entry point relies on documentation, not enforcement | Stated explicitly here and in `CONTRIBUTING.md` |
| Migration recipe still has an edge case | Re-verify the exact recipe text against `#81`'s round-4 fix during implementation |
| `literal_mount_source`'s plain-`cd`-then-`pwd -P` semantics are a genuinely non-obvious POSIX/Docker coincidence, and the "obviously more correct-looking" `cd -P` variant is the wrong one | Documented in-code with an explicit "do NOT add `-P`" warning; round 3 (B3) demonstrated the concrete exploit `cd -P` would reopen, with a live `docker run` reading a planted private key, specifically because the design's own prose got this backwards until this round — the warning is loud on purpose |
| A future edit could re-introduce a shell-specific glob/case-pattern bug in `home_is_at_or_under` the way round 2's fix (correct under dash, wrong under bash) did | T9 runs the predicate under both `bash` and `sh` in CI, so a regression on either shell fails the suite rather than surfacing only in a future review round |
| A host project root shadows a container path already in use by another mount (e.g. a host directory structure that happens to collide with `/home/vscode/...` targets used by the `.claude`/`.claude-creds` mounts) | Not evaluated in this design — flagged as a residual gap; low likelihood (requires a specific host layout coincidence) and the failure mode is a container start error, not a silent security issue, so it is deferred rather than blocking this design |
| Google Antigravity's `initializeCommand` support for object-form (and `${localWorkspaceFolder}` in `workspaceMount`) is unverified in this environment | Gated as a required pre-merge hard check (T10); no fallback exists — a fallback considered and rejected in round 4 (B7) would have reintroduced the injection vector this design exists to close |
| A host path containing a comma breaks T5's `workspaceMount` string form (`source=…,target=…,type=bind` — a comma in the path is indistinguishable from the field separator) | Not defended against — this is the same string-form field (not the argv-form guard entry), so it is out of scope for this design's injection concerns; fails loudly (malformed mount spec) rather than silently, consistent with how the pre-`#83` hardcoded literal already failed loudly on any mismatch. Noted here rather than left undiscovered (round-4 review, minor) |

---

## Implementation Notes (2026-09-04)

T1–T9c implemented as specified. Decisions the design explicitly left to implementation, and the
one place the shipped tests deviate from the Tests table:

- **T9b/T9c module name** — `tests/tools/test_workspace_scripts.py` (the alternative round 7
  offered, since the module covers both scripts *and* the `devcontainer.json` fragment). T9c is
  folded into it as specified, not a separate file.
- **T9c JSONC parsing** — a small string-literal-aware `//`-comment stripper in the test module,
  then `json.loads`. No new dependency; a stripper naive about quoting would corrupt a value
  containing `//`, so the scanner tracks string state and escapes.
- **T9c item (a) carries its own positive control** (`test_the_token_pattern_can_actually_fail`):
  the enumerated pattern is asserted to match the round-5 defective `${containerWorkspaceFolder}`
  form exactly once, so a pattern that had quietly stopped matching anything could not pass as a
  green check.
- **Tests-table row 2 (`setup-workspace.sh` refuses at `/`) is SKIPPED, not passing** — the
  fixture needs a checkout at `/main`, i.e. a writable `/`. The test is present and runs if
  invoked as root; otherwise it skips with that reason stated. The `/` refusal is not left
  unguarded: `home_is_at_or_under "/"` is CI-tested under both `bash` and `sh` (T9's
  `test_root_slash_is_unsafe_under_every_shell`), and `/` is an ancestor of any real `$HOME`, so
  both clauses of `refuse_unsafe_root` fire. Flagged rather than faked.
- **Mutation-checked, not merely green** — before sign-off, two deliberate regressions were
  introduced into the lib and the suite confirmed to go red, then reverted:
  (i) `cd -P` in `literal_mount_source` → 3 failures, including
  `test_guard_refuses_a_main_symlink_planted_in_home` flipping to ACCEPT (i.e. the guard would
  have bind-mounted `$HOME`) — round-3's B3 exploit, caught;
  (ii) the round-2 `"${_wr_root_p%/}"/*` pattern → `test_root_slash_is_unsafe_under_every_shell`
  red under `bash`, green under `sh`, reproducing B4's shell-specific split exactly.
  T9c item (d) carries the same discipline inline (shipped form exits 0 and reaches the sentinel;
  round-7 buggy form exits non-zero on the identical fixture).
- **`/bin/sh` on the dev image is `dash`**, so the `sh` half of every parametrized test is a real
  second shell rather than a bash alias.

### Manual `devcontainer up` round-trips — rows 14, 15, 15b, 15c, 15d all RUN and PASSING

`@devcontainers/cli` 0.88.0 (the version the design rounds used) against the now-tracked files,
Docker 29.4.2 via the mounted socket:

| Row | Fixture | Result |
|---|---|---|
| 14 | project with **no marker**, the **real tracked** `.devcontainer/devcontainer.json` | Both `initializeCommand` entries ran in order (`seedClaudeCredentials`, then `checkWorkspaceSetup`); the guard printed *"no project-root marker at …"* and the CLI returned `{"outcome":"error"}` — **zero containers created**. Object-form `initializeCommand` confirmed working in the CLI. |
| 15 + 15c | marker present; **a sibling worktree opened directly** (not `main`); project root also holds `zz-plain`, a lexically-last non-git directory | `{"outcome":"success"}`. `docker inspect`: `source == target ==` the project root, `RW=true` — path identity preserved by T5's derived expression. Inside the container, `git config --global --get-all safe.directory` lists **both** `feature-x` and `main` and **not** `zz-plain` — i.e. `remoteEnv` reached `postCreateCommand`, the widened scope works when a non-`main` checkout is opened, and the `if`/`fi` loop survived the non-git last directory. This is also the **T10 pass-condition observable**, satisfied here on the CLI. |
| 15b | project root literally named `` pr$(touch PWNED)oj `` | `{"outcome":"success"}`, both checkouts marked `safe.directory`, and **no `PWNED` artifact** on the host or in the container. The hostile path is data at every hop: `argv[1]` to the guard, the mount `source`/`target`, and `$VIBE_OPENED`. |
| 15d | `VIBE_OPENED` removed from `remoteEnv` | `postCreateCommand` aborted **loudly**: `/bin/sh: 1: VIBE_OPENED: VIBE_OPENED unset -- remoteEnv did not reach postCreateCommand`, *"failed with exit code 2. Skipping any further user-provided commands"*, `{"outcome":"error"}`. Round-8's silent-no-op is closed. |

Fixture caveats, stated rather than buried: (a) fixtures live under `/workspaces/vibe-cading/…`
because that path is mounted host==container — a fixture in the container's own `/tmp` would bind
a *nonexistent* host path and the round-trip would be measuring nothing; (b) the fixture
`devcontainer.json` is derived from the tracked one with exactly two removals — the `mounts` array
(host `~/.ssh` / `~/.claude` / `~/.gemini`, whose sources do not exist on the host daemon from in
here) and, with them, `initializeCommand`'s `seedClaudeCredentials` entry. Row 14 exercised the
**unmodified** tracked file including that entry. Everything under test — `workspaceMount`,
`workspaceFolder`, `remoteEnv`, `postCreateCommand`, `checkWorkspaceSetup` — was carried verbatim.

One incidental finding, not a defect in this design: **opening a worktree uses the worktree's
committed `devcontainer.json`**, not `main`'s working copy. The first 15d attempt mutated `main`'s
file and opened the worktree, so the mutation never took effect and the run merely re-passed row
15. Re-run against `main`, it failed as designed. Worth knowing when editing this file from a
stream worktree.

All throwaway containers were `docker rm -f`'d and the 8 fixture images `docker rmi`'d.

**Not done — T10 remains open, deferred by the human (2026-09-04).** No Google Antigravity binary
exists in this container. The CLI rows above cover the same *mechanisms* (object-form
`initializeCommand`, the derived mount expression, `remoteEnv`-derived shell variables, and T10's
own `safe.directory` observable) but on `@devcontainers/cli`, which is exactly the host T10 exists
to look past — its whole purpose is catching host-*specific* behaviour differences. Per §T10 there
is no fallback: if Antigravity fails any part, this returns to authoring, not to a weaker shipped
mechanism.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Requester sign-off
- [ ] TL sign-off

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL — **APPROVED, round 10.** Round 10 built T9c item (d) from the document's own
  wording alone and confirmed it discriminates the shipped `if`/`fi` loop form from the round-7
  buggy form under both `bash` and `dash`, with all writes confined to a scratch `HOME` — no
  further reproduction gap. The two minor prose corrections (the subshell-continuation example,
  the JSONC-parsing note) were confirmed sound. One cosmetic staleness item (a stale historical
  bullet in §Round-8 Review Response) was fixed in this pass; the rest were judged genuinely
  cosmetic and left to implementation-time judgment, consistent with round 10's explicit finding
  that "the safety-critical decisions are locked in… nothing in this round touched any of them."
  Ten rounds of fresh-context adversarial review, five of them (rounds 6-10) independently
  re-confirming no defect in the shipped guard mechanism, is the convergence signal this design
  flow's Step 3.5 gate exists to produce. Proceeding to implementation.

### Human Design Review (Step 4)
- [x] Human approved for implementation to begin — 2026-09-04
