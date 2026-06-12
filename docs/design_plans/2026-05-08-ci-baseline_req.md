# Requirements: CI Baseline (lint + import-check)

## Meta
- **Initiator role**: @pm
- **Date**: 2026-05-08
- **Domain integrity gate**: NO — touches CI infrastructure only; no model/data contracts.

---

## Problem Statement

The repo has only `cla.yml` (legal) and `engine-api.yml` (engine_api drift
guard) under `.github/workflows/`. There is no general lint, import, or
build pipeline. The recently-shipped `engine-api.yml` runs into a CI
vacuum — its `--check` gate works but every other class of regression
(syntax errors, broken imports, lint violations, AGPLv3 header drift) ships
unchallenged through PRs. This task establishes the v1 baseline so that
every subsequent PR gets honest automated signal.

Background: raised by TL during the engine-api brief on 2026-05-08 and
parked in [ci-baseline.md](ci-baseline.md). Picked up by PM on 2026-05-08
on user direction.

## User Story / Motivation

As an open-source contributor (or maintainer reviewing a PR), I need the CI
to fail loudly when a PR introduces undefined names, broken imports,
lint-rule violations, or shadow-imports, so that I do not have to manually
run `flake8` and `python -c "import ..."` against every changed file
before trusting the diff.

## Functional Requirements

1. CI MUST run `flake8` against `models/` and `tools/` and fail the workflow
   on any violation.
2. CI MUST verify every `.py` file under `models/` and `tools/` (excluding
   empty `__init__.py` and `tmp/`) imports cleanly under Python 3.11
   without invoking CadQuery or OCCT — i.e., the import-check MUST work
   even when CadQuery is not installed in the runner. *Rationale: keeps
   the workflow fast and avoids the heavy OCCT install in v1; the user
   chose "skip build-smoke in v1" during Discovery.*
3. CI MUST trigger on `pull_request` (any branch) and on `push` to
   `main`, with NO path filter.
4. CI MUST pin Python to `3.11` (matches `.devcontainer/Dockerfile` and
   the existing `engine-api.yml`).
5. The repo MUST contain a `.flake8` config at the workspace root with:
   - `max-line-length = 120` (CadQuery code uses long descriptive names).
   - `extend-ignore = E203, W503` (common false positives with
     black-style formatting; black is not enforced in v1 but the lint
     config should be compatible if added later).
   - `exclude = tmp, build, .agents, .git, __pycache__, *.egg-info`
   - No additional `select` — flake8's default checks apply.
6. The new workflow MUST live at `.github/workflows/ci.yml`.

## Non-Functional Constraints

- Workflow MUST run in under 2 minutes on a clean GitHub-hosted runner.
  Lint + import-check only; no CadQuery install in v1.
- The workflow MUST NOT install any pip package beyond `flake8`. CadQuery,
  ocp-vscode, and other heavy dependencies stay out of v1.
- Existing workflows (`cla.yml`, `engine-api.yml`) MUST continue to run
  unchanged.
- Lint MUST pass on the current `main` at the moment of merge — i.e., this
  task includes whatever minimal codebase fix-ups are needed to satisfy the
  curated `.flake8` rules. If the existing code violates the new rules in
  ways that require non-trivial refactor (>20 lines touched), the
  violations MUST be added to `extend-ignore` with a one-line comment
  explaining the deferral, rather than rewritten in this PR.

## Known Domain Constraints

- Project rule (`vibe/INSTRUCTIONS.md` §4): "After code modifications,
  proactively run static linters (e.g. `flake8`)." CI now enforces this
  rule for every contributor.
- AGPLv3 header rule (`CLAUDE.md`): every new `.py` in `models/` or
  `tools/` (except empty `__init__.py`) must carry the AGPLv3 header.
  Out of scope for v1 (header-check is a separate task) — see Out of
  Scope below.
- Devcontainer uses `python:3.11-slim`. CI matches.

## Out of Scope

- `python build.py` smoke runs (deferred per user direction during
  Discovery; can be revisited if a CadQuery-runtime regression slips
  through).
- AGPLv3 header presence check.
- Full coverage gates or a Python version matrix.
- Any restructuring of `cla.yml` or `engine-api.yml`.
- A reusable composite action for the import-check (defer until a second
  workflow needs the same step).
- Caching pip wheels — the only dependency is flake8; not worth the cache
  config in v1.

## Open Questions

- [ ] How should the import-check enumerate modules? Two candidates:
  (a) walk `models/` and `tools/` for `.py` files and run
  `python -m py_compile` per file (fast, no real import); (b) walk for
  importable module paths and run `python -c "import <path>"` (heavier;
  triggers CadQuery import on most files in `models/`, which would force
  CadQuery into CI). Decision belongs to TL — strongly bias toward (a)
  given Requirement 2.
- [ ] Should `flake8` run as `flake8 .` (scoped by `.flake8` excludes) or
  `flake8 models tools`? Both work; (a) is simpler, (b) is more explicit.
  TL chooses; trivial.
- [ ] After applying the curated `.flake8`, how many violations does the
  current `main` produce? If the count is large, do we (i) fix in this
  PR, (ii) add per-file `# noqa` or `extend-ignore`, or (iii) split the
  fixes into a follow-up? Answer depends on actual count — TL probes,
  developer reports.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human (2026-05-08, "approve")
<!-- Do not proceed to design until this box is checked. -->
