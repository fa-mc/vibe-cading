# Design: CI Baseline (lint + import-check)

## Meta
- **Requirements ref**: [2026-05-08-ci-baseline_req.md](2026-05-08-ci-baseline_req.md)
- **Requester role**: @pm
- **Date**: 2026-05-08
- **Dialog rounds**: 4 (Round 4 added post-implementation per Escalation E1)

---

## Objective

Ship `.github/workflows/ci.yml` plus a curated `.flake8` so every PR and
`main` push gets pyflakes-strict + bytecode-compile signal in under two
minutes, without forcing CadQuery into the runner.

## Architecture / Approach

### Approach chosen

**Two-step CI workflow, one job, GitHub-hosted Ubuntu runner, Python 3.11.**

1. **Step `lint`** — `flake8 .` from the repo root. Configuration is
   **fully** in `.flake8`; the workflow does not pass CLI flags. flake8
   honors the file's `exclude` list, so `.` resolves to `models/`,
   `tools/`, plus any future top-level `.py` (e.g. `build.py` itself).

2. **Step `import-check`** — walk `models/` and `tools/` for `.py` files
   (excluding empty `__init__.py`, the `tmp/` and `build/` trees, and any
   path matching `.flake8`'s `exclude`) and run `python -m py_compile` on
   each. py_compile is a stdlib parser — it produces `.pyc` bytecode
   without executing module-level code, so it does not import CadQuery.
   Implemented as a small inline shell loop in the workflow YAML; no new
   helper script under `tools/`.

`.flake8` lives at the repo root with the curated config (see
*Configuration Contracts* below).

**Pyflakes-strict, pycodestyle-deferred.** Because `main` currently has
723 violations under the requirements-mandated config (max-line-length
120, ignore E203/W503), and the requirements §"Non-Functional Constraints"
forbid >20-line refactors in this PR, the workflow ships with all
pycodestyle E/W classes added to `extend-ignore` *except* the original
E203, W503. The literal class list is therefore `E1, E2, E3, E4, E5, E7,
W1, W2, W3, W5, W6` — every pycodestyle group except E203 and W503,
which remain ignored as originally specified. All pyflakes (F-class)
checks remain active and the 45 existing F-class violations are fixed in
this PR (mechanical: 36 unused imports + 7 unused locals + 1 redefinition
+ 1 vacuous f-string). E/W re-enablement is a follow-up task tracked via
a `# TODO(ci-v2)` comment in `.flake8`. v2's recommended entry point is
**E722** (bare `except`) — the only deferred class with a real-bug
character; the rest is style.

The `max-line-length = 120` value is retained in the config even though
E501 is in `extend-ignore`, so a future v2 task that drops `E5` from
`extend-ignore` immediately enforces the documented limit without a
config edit.

### Alternatives rejected

- **Custom Python script for import-check** (`tools/check_imports.py`).
  Rejected: an inline `find … -exec python -m py_compile {} +` is two
  lines of YAML; a script would need its own AGPLv3 header, a CLI
  contract, and a place in the codebase. The req §"Out of Scope"
  explicitly defers the reusable composite action — same logic applies
  to a reusable Python helper. Inline wins until a second workflow needs
  the same step.

- **`python -c "import <module>"` per importable module.** Rejected:
  triggers `import cadquery` for every file under `models/`, forcing
  CadQuery into the runner. Violates Requirement 2 directly.

- **`compileall` instead of `py_compile`.** `python -m compileall -q
  models tools` would do the same job in one command, but it returns
  exit code 0 even when individual files fail (it prints errors to
  stderr but the *batch* succeeds if at least one file compiles). The
  per-file loop with `py_compile` short-circuits on the first failure,
  which is what we want.

- **Pyflakes-only via `flake8 --select=F`.** Rejected during Discovery
  (user chose "curated `.flake8`" over "pyflakes only"). The chosen
  approach ships under the `flake8` brand and leaves the path open to
  re-enable pycodestyle classes incrementally.

- **One-time formatter sweep (autopep8 / black) to clear the 723
  violations.** Rejected: would touch nearly every file, polluting the
  PR diff, breaking `git blame`, and conflicting with the req's
  >20-line refactor cap. Out of scope per Discovery.

- **Path-filtered triggers** (mirror the engine-api workflow's
  `paths:` filter). Rejected during Discovery; the user chose
  "no path filter" for the baseline, and a baseline that runs
  unconditionally is simpler and harder to silently bypass.

- **Self-hosted runner.** Out of scope; project has no infra for it.

## Configuration Contracts

This task introduces three tracked artifacts. Their exact shape is part
of the design contract.

### `.flake8`

```ini
[flake8]
max-line-length = 120
# E203, W503: black-style false positives (PEP 8 disagreement, see
#   https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html)
# E1, E2, E3, E4, E5, W1, W2, W3, W5: pycodestyle classes deferred to a
#   v2 cleanup task (see .agents/plans/2026-05-08-ci-baseline_design.md
#   §"Pyflakes-strict, pycodestyle-deferred"). DO NOT remove without
#   re-running flake8 against the full tree and confirming the
#   resulting violation count is fixable within the >20-line rule.
# E722 (bare except) is the highest-value class to re-enable in v2 — it
#   hides real exception-type bugs. Spec'd as the v2 entry point.
extend-ignore = E1, E2, E3, E4, E5, E7, W1, W2, W3, W5, W6
exclude =
    tmp,
    build,
    .agents,
    .git,
    __pycache__,
    *.egg-info
```

Rationale for the broad `E1..E5, W1..W5` ignore: per-class is cleaner
than enumerating every individual code (E501, E502, …, W293, W291, …).
Future un-ignore is one line per class.

### `.github/workflows/ci.yml`

```yaml
name: ci

# Baseline lint + import-check. See
# .agents/plans/2026-05-08-ci-baseline_design.md.

on:
  pull_request:
  push:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install flake8
        run: pip install flake8
      - name: Lint (flake8)
        run: flake8 .
      - name: Import-check (py_compile)
        run: |
          set -euo pipefail
          mapfile -t files < <(
            find models tools -type f -name '*.py' \
              ! -path '*/tmp/*' \
              ! -path '*/__pycache__/*'
          )
          empty=0
          checked=0
          for f in "${files[@]}"; do
            if [[ "$(basename "$f")" == "__init__.py" && ! -s "$f" ]]; then
              empty=$((empty + 1))
              continue
            fi
            python -m py_compile "$f"
            checked=$((checked + 1))
          done
          echo "py_compile: $checked file(s) checked, $empty empty __init__.py skipped"
```

Notes on the YAML:
- Triggers: `pull_request` (no branch filter — runs on every PR target)
  and `push: branches: [main]`.
- No path filter (Discovery decision Q3).
- No CadQuery install (Requirement 2 + non-functional constraint).
- The import-check loop counts skipped empty `__init__.py` files and
  prints the totals for traceability in failure forensics.

### F-class fix manifest

Single mechanical commit fixing the 45 F-class violations identified by
running `flake8 --max-line-length=120 --extend-ignore=E203,W503
--exclude=tmp,build,.agents,.git,__pycache__,*.egg-info --select=F
models tools` on `main` at SHA `e5d224d`. The developer reproduces this
command after pulling the branch to confirm the manifest is current
before editing.

| Class | Count | Treatment |
|---|---|---|
| F401 (unused import) in non-`__init__.py` | 25 | Delete the import. |
| F401 (unused import) in `__init__.py` re-exports | 11 | Add an `__all__ = [...]` declaration listing every re-exported symbol. flake8 treats `__all__` membership as "used" and the F401 disappears without `# noqa`. Files affected: `models/lego/__init__.py`, `models/mechanical/__init__.py`, `models/mechanical/screws/__init__.py`, `models/xlego/slipper_gear/__init__.py`. |
| F841 (unused local) | 7 | Delete the assignment. None are guard-style "intentionally unused" — confirmed by inspection during design (e.g. `radial_allowance` in `models/mechanical/nuts/metric.py:61` is genuinely dead, not "ignored API parameter"). If any case turns out to be a guarded debug variable, prefix with `_` and document. |
| F811 (`tools/view.py:197` redefinition of `cq`) | 1 | Delete the inner `import cadquery as cq` (line 197) — it shadows the module-level import on line 166. Same for line 237. |
| F541 (`tools/section_slicer.py:207` vacuous f-string) | 1 | Drop the `f` prefix — the string has no `{}`. |

Total files touched by the mechanical commit: ~25. Each individual edit
is single-line deletion or one-line declaration; the >20-line "refactor"
clause does not apply (the clause is about logic refactors, not dead-
code removal — see Round 1 of the dialog log below).

## Acceptance Contract

This is the standalone contract for PR review. It is the single section a
reviewer needs in addition to `req.md` and `diff.patch`.

### Tracked artifacts in the diff

The PR MUST add exactly these two new files at the listed paths (no other
new tracked files):

1. `.flake8` (repo root) — INI format, must contain literally:
   - `max-line-length = 120`
   - `extend-ignore = E1, E2, E3, E4, E5, E7, W1, W2, W3, W5, W6` (note:
     E203 and W503 are present in addition by virtue of pycodestyle's
     default behavior, but the literal ignore list MUST contain the
     11-class set above; comment lines documenting E203/W503 and the
     v2 deferral plan are part of the contract).
   - `exclude` list containing at minimum: `tmp, build, .agents, .git,
     __pycache__, *.egg-info`.
2. `.github/workflows/ci.yml` — must:
   - Trigger on `pull_request` (no branch filter) AND on `push:
     branches: [main]`.
   - Run on `ubuntu-latest` with `actions/setup-python@v5` resolving
     `python-version: "3.11"`.
   - Install `flake8` and ONLY flake8 (no CadQuery / no other pip
     installs in v1).
   - Run `flake8 .` as a step.
   - Run a `python -m py_compile` loop over `find models tools -type f
     -name '*.py'` (excluding `tmp/` and `__pycache__/`), skipping empty
     `__init__.py` files.

### Source-code edits in the diff

The PR MUST modify exactly the following 25 files for F-class lint
clean-up. Total line delta MUST be on the order of `26 insertions(+),
59 deletions(-)` (mechanical dead-code removal — small swing in either
direction acceptable; large swing flags scope creep). Files:

```
models/lego/__init__.py
models/lego/gears/gear_28t.py
models/mechanical/__init__.py
models/mechanical/enclosures/pcb_standoff.py
models/mechanical/enclosures/zip_tie.py
models/mechanical/hinge.py
models/mechanical/nuts/metric.py
models/mechanical/screws/__init__.py
models/mechanical/screws/imperial.py
models/mechanical/tolerance_gauge.py
models/mechanical/trailer_hitch_cover.py
models/rc/servo/sg90.py
models/xlego/servos/sg90/servo_mount.py
models/xlego/servos/shaft_body.py
models/xlego/slipper_gear/__init__.py
models/xlego/slipper_gear/directional/parts/slipper_plate.py
models/xlego/slipper_gear/directional/parts/slipper_ring.py
tools/check_license_headers.py
tools/face_catalog.py
tools/face_distances.py
tools/hole_finder.py
tools/section_slicer.py
tools/step_preview.py
tools/step_summary.py
tools/view.py
```

The four `__init__.py` files in `models/lego`, `models/mechanical`,
`models/mechanical/screws`, `models/xlego/slipper_gear` MUST gain
`__all__ = [...]` declarations naming every previously-imported symbol.
Per-line `# noqa: F401` is **not** acceptable (explicitly rejected in
design Round 3).

### Files that MUST NOT change

- `.github/workflows/cla.yml` — byte-identical to pre-PR `main`.
- `.github/workflows/engine-api.yml` — byte-identical to pre-PR `main`.
- `build.toml`, `models/print_settings.py`, `models/cq_utils.py`,
  `models/lego/constants.py` — no changes (out of scope).

### Success criteria (binary, all required)

1. `flake8 .` from repo root, post-merge, exits 0 with empty stdout.
2. `python -m py_compile` over every non-empty `.py` under `models/`
   and `tools/` exits 0 (expected count: 80 files checked, 7 empty
   `__init__.py` skipped — the workflow's import-check step prints
   exactly this).
3. `from models.lego import TechnicAxleHole, TechnicPinHole` resolves.
4. `from models.mechanical import ClearanceHole, CounterboreHole,
   TeardropHole` resolves.
5. `from models.mechanical.screws import PlasticsScrew, SetScrew,
   ImperialMachineScrew` resolves.
6. `from models.xlego.slipper_gear import SlipperGear, SlipperRing,
   SlipperPlate, SlipperSpring` resolves.
7. The `ci / check` workflow run on this PR completes green in under
   120 seconds wall-clock.
8. Pre-existing `engine-api / check` and `cla` workflow runs on this
   PR remain green and unchanged in shape.
9. After merge, the `ci / check` workflow fires once on the merge
   commit pushed to `main` and completes green.

### Requirement → criterion mapping (greppable)

| Requirement (`req.md`) | Satisfied by |
|---|---|
| R1 (flake8 fails on violation) | Criterion 1, 7 |
| R2 (import-check without CadQuery) | Criterion 2, 7 |
| R3 (PR + main push triggers, no path filter) | Criterion 7, 9; YAML `on:` block in diff |
| R4 (Python 3.11 pin) | YAML `setup-python@v5` block in diff |
| R5 (curated `.flake8` contents) | "Tracked artifacts in the diff" §1 above |
| R6 (workflow path = `.github/workflows/ci.yml`) | "Tracked artifacts in the diff" §2 above |

## Implementation Plan

- [x] **T1 — Add `.flake8` at repo root** with the exact contents shown
      under *Configuration Contracts*. Verify with
      `flake8 --select=F .` returning the 45-violation manifest above
      *before* T2 starts (a different count means the branch has
      diverged from `main@e5d224d` and the manifest must be regenerated).
- [x] **T2 — Apply the F-class fix manifest** in a single commit. Edits
      are per the manifest table. After completion, re-run
      `flake8 .` from the repo root and confirm exit code 0 (i.e., zero
      reported violations under the curated config).
- [x] **T3 — Add `.github/workflows/ci.yml`** with the exact contents
      shown under *Configuration Contracts*. Validate locally with
      `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
      to confirm parseable YAML. (Project has no `act` or YAML linter
      installed; YAML parsability + the workflow's two `run:` blocks
      being independently runnable as bash is sufficient pre-merge
      validation. Real-environment validation happens when the PR is
      opened and CI fires for the first time.)
- [x] **T4 — Run both workflow steps locally end-to-end.** From the
      repo root:
      ```bash
      flake8 .
      mapfile -t files < <(find models tools -type f -name '*.py' \
        ! -path '*/tmp/*' ! -path '*/__pycache__/*')
      for f in "${files[@]}"; do
        if [[ "$(basename "$f")" == "__init__.py" && ! -s "$f" ]]; then continue; fi
        python -m py_compile "$f"
      done
      ```
      Both must exit 0. Capture the output for the Implementation Status
      section. **Complete (post-E1 resolution):** lint exit 0 (zero
      violations under the widened `extend-ignore`); import-check exit 0
      (80 checked / 7 empty skipped). F-class sub-check
      (`flake8 --select=F .`) also exit 0.
- [x] **T5 — Update [INDEX.md](INDEX.md)**: archive the obsolete row
      pointing at `ci-baseline.md` (the original backlog stub) and
      delete `ci-baseline.md` itself — superseded by this design.
      Status of the new row stays `in-flight` until human final approval.
      *(No INDEX row referenced the stub; ci-baseline.md deleted.)*
- [x] **T6 — Update Implementation Status section** of this design with
      T1–T5 outcomes plus the lint/import-check console output from T4.

## Tests

The workflow itself is the test harness. Each functional requirement is
exercised by either the lint step, the import-check step, or a
configuration assertion. No new pytest files are introduced — this is
deliberate, since the only behavioral surface is the YAML and the
`.flake8`, both of which are exercised by the live CI run on this very
PR.

| # | Test description | Expected assertion | File / location | Maps to |
|---|---|---|---|---|
| 1 | `flake8 .` from repo root with the curated `.flake8` returns exit 0 on the post-T2 tree | Exit 0; stdout empty | T4 (local) + GitHub Actions log on this PR | R1, R5 |
| 2 | `python -m py_compile` on every non-empty `.py` under `models/` and `tools/` returns exit 0 on the post-T2 tree | Exit 0 from every iteration; final `echo` prints `checked=80`, `empty=7` (87 files − 7 empty `__init__.py`) | T4 (local) + GitHub Actions log on this PR | R2 |
| 3 | Workflow triggers on a PR opened from any branch | GitHub Actions UI shows `ci / check` queued and run | First PR carrying this change | R3 |
| 4 | Workflow triggers on `push` to `main` after merge | `ci / check` run appears under the post-merge commit on `main` | Post-merge GitHub Actions log | R3 |
| 5 | `actions/setup-python@v5` resolves Python 3.11 | "Successfully set up CPython (3.11.x)" in the runner log | GitHub Actions log on this PR | R4 |
| 6 | `.flake8` contains the contractual keys | Grep proof: `max-line-length = 120`, `extend-ignore` mentions `E203, W503`, `exclude` mentions `tmp, build, .agents, .git, __pycache__, *.egg-info` | T1 local validation + grep on the merged tree | R5 |
| 7 | `.github/workflows/ci.yml` exists at the contractual path | File exists; `yaml.safe_load` parses without error | T3 local + GitHub Actions detection | R6 |
| 8 | Existing workflows (`cla.yml`, `engine-api.yml`) still trigger and succeed on this PR | Both runs go green on this PR | GitHub Actions log on this PR | NFR (existing-workflow stability) |
| 9 | F-class violation count post-T2 is zero | `flake8 --select=F .` exits 0 with empty stdout | T4 (local) | R1 (mechanical fix manifest correctness) |
| 10 | Workflow run wall-clock time | Total `ci / check` job duration < 120 s under nominal GitHub-hosted runner load | GitHub Actions UI on this PR | NFR (under 2 min) |

## Success Criteria

1. The PR for this task includes exactly three new tracked files
   (`.flake8`, `.github/workflows/ci.yml`, this design artifact) plus
   the F-class fix-up edits across the 25 files in the manifest. No
   other files modified except [INDEX.md](INDEX.md) and the deletion of
   [ci-baseline.md](ci-baseline.md).
2. `flake8 .` and the import-check loop both exit 0 locally on the
   developer's machine before the PR is opened (T4 evidence in
   Implementation Status).
3. The `ci / check` workflow run on the PR completes green in under
   120 seconds (Test 10).
4. The pre-existing `engine-api / check` and `cla` workflow runs on the
   PR remain green and unchanged in shape (Test 8).
5. After merge, a `push` to `main` (the merge commit itself) fires
   `ci / check` once and it completes green (Test 4).

## Out of Scope

Mirrored from `_req.md` §"Out of Scope". Co-design surfaced one
expansion:

- **Re-enabling pycodestyle E/W classes.** Tracked as a follow-up
  ("ci-v2: lint hardening pass"). The TODO comment in `.flake8` is the
  in-tree pointer. Not a new plan file until someone picks it up — keeps
  `.agents/plans/` clean of speculative work.
  *Predicted cost if blocking:* PRs continue to ship with cosmetic
  style drift (whitespace, blank-line counts, alignment) until v2 lands.
  No correctness implications. Worst case: a few hours of mechanical
  cleanup when v2 is picked up. Well below the project's blocking
  threshold.
- **Switch to a reusable composite action for the import-check loop.**
  Already deferred in `_req.md`; reaffirmed in dialog Round 2.
  *Predicted cost if blocking:* if a third workflow ever needs the
  same loop, ~15 lines of YAML get copied. The cost of premature
  abstraction (action versioning, action repo placement, action input
  schema design) exceeds the cost of one duplication. Below threshold.
- **`python build.py` smoke and AGPLv3 header check.** Both deferred per
  `_req.md`. *Predicted cost if blocking:* a CadQuery-runtime regression
  (e.g. an OCCT API change consumed via a versioned `cadquery` install)
  ships green through CI and is caught only by a contributor running
  `python build.py` locally. Single re-roll PR to fix; no production
  impact (this project ships STEP files, not a service). AGPLv3 header
  drift cost: a header is missing on a new file, caught at the next
  manual review. Both well below threshold.

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| GitHub-hosted runner Python 3.11 patch version drifts from devcontainer's `python:3.11-slim` patch level. Behavior diverges silently. | `setup-python@v5` with `python-version: "3.11"` resolves to the latest `3.11.x` on both surfaces, and the v1 surface (flake8 + py_compile) does not exercise patch-version-sensitive features. Acceptable. Re-evaluate if a CadQuery-runtime smoke is added in v2. |
| 45 F-class fixes are mechanical, but a hand-edit slip-up could introduce a real bug (e.g. deleting an import that *is* used at runtime via a dynamic `getattr` lookup, which flake8 cannot see). | Developer runs `python -m py_compile` on every edited file after each batch of edits in T2 (cheap), and then runs `python build.py` against the *full* `build.toml` once at the end of T2 as a one-shot full-tree smoke (this is the only place the design invokes the full build — it is final-pass validation, not iterative debugging, per `vibe/INSTRUCTIONS.md` §4 "Fast-Feedback Gate"). If `build.py` regresses on any model, the F-class deletion is the suspect; revert that specific deletion and add `# noqa: F401` with a comment naming the dynamic lookup. |
| `__all__` declarations in re-export `__init__.py` files miss a symbol, breaking downstream `from models.lego import TechnicAxleHole`. | Developer runs a focused `python -c "from models.lego import TechnicAxleHole; from models.lego import TechnicPinHole"` (and equivalent for the other three `__init__.py` files) after T2 to confirm the public surface still resolves. |
| Future contributor adds a `# noqa` line and the lint passes silently when it should not. | Out of scope for v1. v2 cleanup pass can introduce a `# noqa` audit if needed; no point gating v1 on a problem that does not yet exist. |
| `flake8 .` from repo root accidentally lints files outside `models/` and `tools/` (e.g. a top-level `build.py`). | Intentional. The `.flake8` `exclude` list scopes the surface; anything *not* excluded *should* be linted. The repo currently has only `build.py` at the top level; running flake8 against it is a feature, not a bug. Verified during T1 by running `flake8 .` and confirming the surface matches expectations. |

---

## Design Dialog Log

### Round 1 — The 723-violation collision with the >20-line rule

**TL proposal:**
> Ship a single workflow with `flake8 .` and a per-file `py_compile`
> loop. Use the `.flake8` config exactly as specified in `_req.md` §R5
> (max-line-length 120, extend-ignore E203/W503, the listed excludes).
> Fix any pre-existing violations in the same PR. Done.

**Requester challenge / contribution:**
> Probed `main@e5d224d` with the proposed config and got **723
> violations** across 87 files. Top categories: W293 (169), E221 (136),
> E501 (74), E302 (57). Fixing 723 violations is a >700-line touch —
> the req's "Non-Functional Constraints" §"non-trivial refactor (>20
> lines touched)" clause forbids that here. But the same clause
> *requires* lint to pass at merge time. The requirements as written
> are therefore self-contradictory under the proposed config.
>
> Two ways out: (a) widen `extend-ignore` to absorb the cosmetic noise
> in v1 and re-enable later; (b) change the config to be lighter than
> what `_req.md` §R5 stipulates. (a) preserves the requirements as the
> requester wrote them and just defers a chunk of enforcement; (b)
> rewrites the requirements artifact mid-design. (a) is correct.

**Resolution:**
> Adopt **pyflakes-strict, pycodestyle-deferred** for v1. Add `E1, E2,
> E3, E4, E5, W1, W2, W3, W5` to `extend-ignore` so all pycodestyle
> classes are deferred. Keep all F-class (pyflakes) checks active.
> Investigation showed F-class has only **45 violations** (36 F401, 7
> F841, 1 F811, 1 F541) — entirely dead-code removal, well within the
> *intent* of the >20-line clause (the clause forbids logic refactors,
> not mechanical dead-code deletion). Track v2 cleanup as a TODO comment
> in `.flake8` rather than a new plan file. Updates `_req.md` §R5 only
> by *expansion* of `extend-ignore`; the original two ignores remain
> intact.

### Round 2 — Import-check primitive selection

**TL proposal:**
> Walk `models/` and `tools/`, run `python -c "import <dotted.path>"`
> on each. Catches undefined names, missing dependencies, and circular
> imports — the highest-signal class of broken-import failure.

**Requester challenge / contribution:**
> Requirement 2 says explicitly: "without invoking CadQuery or OCCT."
> Almost every file under `models/` does `import cadquery` at module
> top. `python -c "import models.lego.constants"` will trigger that.
> So either we install CadQuery in CI (violates Requirement 2 and the
> "under 2 minutes" non-functional constraint), or we use a primitive
> that doesn't execute imports. `py_compile` is parser-only — produces
> bytecode without running module code. Verified locally that `python
> -m py_compile models/lego/constants.py` succeeds without CadQuery
> installed.
>
> Counter-question: what does `py_compile` *not* catch that `import`
> would? Answer: undefined names referenced from module scope (e.g.
> `import nonexistent_module` parses fine, only fails at runtime).
> But flake8's pyflakes (F821 undefined name, F401 unused import,
> F811 redefinition) catches the static class of that — between
> py_compile and pyflakes, the net coverage is "no syntax errors, no
> undefined names statically visible to pyflakes." Anything beyond
> that requires running CadQuery, which is the v2 build-smoke task,
> not v1.

**Resolution:**
> Use `python -m py_compile` per file in a bash loop. Skip empty
> `__init__.py` files explicitly (they would compile fine but the skip
> is documented for forensics). Inline in the workflow YAML — no
> `tools/check_imports.py` until a second consumer materializes (per
> req §"Out of Scope": no reusable composite action in v1).

### Round 3 — F401 in `__init__.py` re-export files

**TL proposal:**
> Suppress F401 on the eleven re-export lines with `# noqa: F401`
> per line. Cheap and explicit.

**Requester challenge / contribution:**
> Per-line `# noqa` is noisy on files where the entire purpose is
> re-export (e.g. `models/xlego/slipper_gear/__init__.py` has four
> back-to-back re-export lines). PEP 8 / flake8 idiomatic answer for
> this exact case: declare `__all__ = [...]` listing the re-exported
> symbols. flake8 treats `__all__` membership as a "use" and the F401
> disappears with zero `# noqa` lines. Bonus: `__all__` is also the
> contract `from package import *` consults, so we get a real public
> API declaration as a side effect.

**Resolution:**
> Use `__all__ = [...]` declarations in the four affected
> `__init__.py` files (`models/lego`, `models/mechanical`,
> `models/mechanical/screws`, `models/xlego/slipper_gear`). Per-line
> `# noqa: F401` reserved for cases where a non-re-export import has
> a side-effect-only purpose (none in the current 36 F401 set —
> verified by inspection during the dialog).

### Round 4 — `.flake8` literal contract diverges from stated intent (post-implementation patch)

**TL proposal:**
> [Round 4 added 2026-05-08 after Escalation E1 surfaced during T4]
> Round 1 stated intent as "all pycodestyle E/W classes added to
> `extend-ignore` *except* E203/W503." Original literal config on
> line 110 was `E1, E2, E3, E4, E5, W1, W2, W3, W5` — missing E7
> (statement-level) and W6 (deprecation). 16 E7 violations on `main`
> were not surfaced in the original 723-violation probe top-10 (E7 is
> 2.2% of total; cut off below E261). Resolution: align literal to
> intent. Add E7 and W6.

**Requester challenge / contribution:**
> The 16 newly-surfaced E7 violations include 3× E722 (bare `except`),
> which is a real-bug class — bare excepts hide exception types and
> mask real failures. Should we fix those three in this PR rather
> than defer them? Cost is six lines (rename `except:` → `except
> Exception:` × 3, with the `except` clause body already correct).

**Resolution:**
> Defer per the design's "pyflakes-strict, pycodestyle-deferred"
> architectural decision (Round 1). E722 is real-bug-class but it is
> *pycodestyle*, not pyflakes — mixing classes mid-implementation
> dilutes the v1 contract. Instead, **call out E722 explicitly as the
> v2 entry point** in both the `.flake8` comment and the narrative
> §"Pyflakes-strict, pycodestyle-deferred". Net effect: zero source-
> code edits in v1; one `.flake8` line widened; one breadcrumb in
> the comment for whoever picks up v2. Matches developer
> recommendation (option 3 in Escalation E1).

---

## Sign-off
- [x] Domain expert co-sign  *(N/A — domain integrity gate is NO; bypassed per design-flow Step 3 termination condition #5)*
- [x] Requester sign-off (human acting as @pm-equivalent, 2026-05-08, "approve")
- [x] TL sign-off

---

## Implementation Status
<!-- Populated by @developer at the start of Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (T1, T2, T3, T4, T5, T6
  done; E1 resolution applied to `.flake8`)
- [x] Test suite executed — result:
  - **F-class lint** (`flake8 --select=F .`): exit 0, 0 violations
    (down from 45 pre-T2). ✓
  - **Full lint** (`flake8 .`): exit 0, 0 violations under the
    post-E1 `.flake8` (`extend-ignore = E1, E2, E3, E4, E5, E7, W1,
    W2, W3, W5, W6`). ✓
  - **Import-check** (py_compile loop): exit 0,
    `py_compile: 80 file(s) checked, 7 empty __init__.py skipped`. ✓
  - **Re-export resolution** (Known Risks mitigation): all four
    `__init__.py` files import their declared symbols and expose
    `__all__` correctly. Post-E1 re-confirmed via four
    `python -c "from ... import ..."` invocations — all OK. ✓
  - **YAML parse** (`yaml.safe_load`): exit 0. ✓
- [x] No new linter / static-check errors *introduced by the manifest
  edits*. Post-E1 resolution, the previously-surfaced 16 E7 violations
  are absorbed into `extend-ignore` per the design's "pyflakes-strict,
  pycodestyle-deferred" architecture; E722 is breadcrumbed in `.flake8`
  as the v2 entry point.
- Developer note: E1 resolution applied (one-line `.flake8`
  `extend-ignore` widening + one comment line about E722); T4 now
  green (lint exit 0, import-check exit 0); T1–T6 all complete. Ready
  for PR.

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes: All 9 review checks pass. `.flake8` and
  `.github/workflows/ci.yml` are byte-identical to the §"Configuration
  Contracts" blocks (verified via `diff -u`). `flake8 --select=F .` and
  `flake8 .` both exit 0 with empty stdout. Inline import-check loop
  (run verbatim in a clean bash subshell) reports
  `py_compile: 80 file(s) checked, 7 empty __init__.py skipped` exactly
  as the contract requires. All four re-export `python -c` invocations
  succeed. F841 spot-check on `models/mechanical/nuts/metric.py:61`
  (`radial_allowance`) confirms the deletion is method-local and the
  surviving `to_captive_slot` / `MetricSquareNut.to_cutter` definitions
  in the same file are untouched; `hole_radius=8.0` and `gear_boss_h`
  spot-checks equally clean. `cla.yml` and `engine-api.yml` byte-identical
  to `e5d224d`. No new files under `tmp/`, no committed `.pyc`, no
  AGPLv3-header drift on the 25 modified source files. `grep -c "R[1-6]"
  → 11` (≥6). Implementation cleared for human final approval.

### Domain Expert Review *(required if domain integrity gate is YES; skip if NO)*
- [ ] **Domain expert sign-off** — N/A (domain integrity gate is NO)
- Domain expert review notes: skipped

### Human Final Approval
- [x] **Human approved** for merge / release (2026-05-08, "Approve & commit + open PR")
- Human notes: PR to be opened with two commits (F-class mechanical fixes; CI infrastructure).

---

## Escalations

### E1 — `.flake8` `extend-ignore` does not cover E7 / W6 classes; T4 `flake8 .` cannot exit 0 under the literal contract

**Discovered:** 2026-05-08 by @developer during T2/T4 validation, after the F-class fix manifest was applied cleanly (45 → 0 F-class violations confirmed via `flake8 --select=F .`).

**Symptom:** `flake8 .` from the repo root with the `.flake8` literally
copied from §"Configuration Contracts" exits **1** with **16 remaining
violations**, all in pycodestyle classes E7 and (none triggered) W6:

```
6  E702  multiple statements on one line (semicolon)
4  E701  multiple statements on one line (colon)
3  E741  ambiguous variable name 'l'
3  E722  do not use bare 'except'
```

Affected files:
- `models/mechanical/holes.py` (2× E741)
- `models/mechanical/screws/metric.py` (1× E722)
- `models/mechanical/screws/plastics.py` (1× E722)
- `models/mechanical/screws/wood.py` (1× E722)
- `models/mechanical/tolerance_gauge.py` (1× E741)
- `models/xlego/slipper_gear/directional/parts/slipper_ring.py` (8× E701/E702)
- `tools/check_topology.py` (2× E701)

**Root cause:** The `.flake8` contract (line 110) reads
`extend-ignore = E1, E2, E3, E4, E5, W1, W2, W3, W5`. The design's
narrative §"Pyflakes-strict, pycodestyle-deferred" (lines 41–48) and
Round 1 of the dialog log (lines 343–354) describe the intent as "all
pycodestyle E/W classes added to `extend-ignore` *except* E203 and
W503". The literal config omits **E7** (statement-level pycodestyle)
and **W6** (deprecation warnings). The 16 unfixed E7 violations were
not surfaced during the design's "723 violations" probe because that
probe used the same incomplete config and reported only the *types*
that actually triggered (E1/E2/E5/W2/W3, etc.) — E7 was a small enough
slice (16/723 = 2.2%) to be missed in the breakdown.

**Contradiction:** §"Implementation Plan" T4 (lines 219–231) requires
`flake8 .` to exit 0 locally. With the literal `.flake8` config, it
cannot, on `main@e5d224d` post-T2.

**Options:**
1. **Add `E7, W6` to `extend-ignore`.** One-line `.flake8` edit. Honors
   the stated intent exactly (defer all pycodestyle classes except the
   originally-ignored E203/W503). Cost: zero source-code edits;
   `.flake8` line count unchanged; the v2 cleanup task absorbs E7/W6
   along with the rest. Recommended.
2. **Fix the 16 E7 violations in this PR.** Adds ~20 single-line
   mechanical edits (rename `l` → `length`, `except:` →
   `except Exception:`, split joined statements onto separate lines).
   All cosmetic, none change behavior. Stays within the spirit of the
   F-class manifest (mechanical, not refactor) but expands the scope
   the design explicitly bounded at "45 violations". Borderline —
   would technically violate the design's "single mechanical commit"
   and "exactly three new tracked files" success criteria #1.
3. **Adopt path 1 *and* track path 2 as a v2 follow-up.** Same as path
   1 with an explicit TODO note in `.flake8` listing E7/W6 alongside
   the existing v2 deferral comment.

**Side effect already absorbed (for the record):** Deleting the inner
`import cadquery as cq` on lines 197 and 237 of `tools/view.py` per
the F811/F401 manifest exposed the outer `import cadquery as cq` at
line 166 as unused (pyflakes had previously seen it as "used" via the
shadowed inner imports). Post-fix, line 166 was deleted as well — a
1-line expansion of the F401 manifest entry for `tools/view.py`.
Total view.py F401 lines deleted: 3 (166, 197, 237) instead of the
manifest-listed 2 (197, 237). Recorded here for transparency; does
not require an orchestrator decision.

**Action requested:** Orchestrator to choose option 1, 2, or 3. Pending
that decision, T4 cannot be marked complete and the PR cannot be
opened. T1, T2, T3, T5 are complete; T4 is **partially complete**
(import-check ✓, lint ✗ pending option choice); T6 is pending T4.

**Developer recommendation:** Option 3. Honors the design's stated
intent, is one tracked-file edit (one line of `.flake8`), and leaves
a clean breadcrumb for the v2 cleanup pass that already exists in the
config. Cost-of-being-wrong analysis: if option 3 is wrong, cost is a
one-line revert in a future PR. Below blocking threshold.

**Resolution (TL, 2026-05-08):** **Option 3 adopted.** `.flake8`
`extend-ignore` widened from `E1, E2, E3, E4, E5, W1, W2, W3, W5` to
`E1, E2, E3, E4, E5, E7, W1, W2, W3, W5, W6`. Comment block in
`.flake8` now also names E722 as the recommended v2 entry point (the
single deferred class with real-bug character). Narrative
§"Pyflakes-strict, pycodestyle-deferred" updated to spell out the
literal class list so future readers do not have to reverse-engineer
intent from the abbreviated phrase. Round 4 added to Design Dialog
Log capturing the requester challenge ("should we fix the 3 E722 in
this PR?") and resolution. Escalation **resolved**; developer to
re-run T4, complete T6, and return.

