# Design: Pip Package Structure
<!-- Filename: 2026-06-12-pip-package-structure_design.md  (tracked in git under docs/design_plans/) -->

## Meta
- **Requirements ref**: Issue #27
- **Requester role**: TL
- **Date**: 2026-06-12
- **Dialog rounds**: 2

---

## Objective
Package the engine as a pip-installable `vibe_cading` wheel containing all necessary tools and runtime data (`engine_api.json`, `print_profiles.json`), while replacing brittle `_REPO_ROOT` path-hopping with robust standard library data loading and establishing a clean configuration cascade.

## Architecture / Approach

### Approach chosen
1. **Structural Refactor:** Move the executable CLI tool scripts (`tools/`) and the shipped runtime JSON data (`engine_api.json`, `print_profiles.json`) inside the `vibe_cading/` directory. This aligns the git source tree with the target package structure and eliminates the need for build-time path mapping.
2. **Build System:** Introduce a modern `pyproject.toml` with `hatchling`.
3. **Full-SHA Build Identifier:** Implement a lightweight `hatch_build.py` hook to natively invoke `git rev-parse HEAD` and inject the 40-character SHA into `vibe_cading/__commit__.py` at wheel-build time. `vibe_cading/__init__.py` will import and expose it.
4. **Data Loading (importlib.resources):** Update internal data loaders (like `print_settings.py`) to load shipped JSON files using `importlib.resources.files("vibe_cading")`, dropping `_REPO_ROOT`.
5. **Configuration Cascades:** Standardize user-overrides (`print_profiles_user.json` and `.env`) using a tiered cascade: 1) explicit environment variable, 2) current working directory, 3) fallback to `_REPO_ROOT`.
6. **Constants Cleanup:** Demote `DEFAULT_CORNER_RADIUS` and `DEFAULT_LEAD_IN` from `.env` overrides to plain geometric constants (`CORNER_RADIUS`, `LEAD_IN`), keeping `PRINT_PROFILE` as the sole `.env` variable.

### Alternatives rejected
- **Build-Time Mapping (Hatchling `force-include`):** Rejected. While expedient, it perpetuates a messy source tree by leaving package data and executable sub-packages at the repository root. A structural refactor is preferred for long-term project health.
- **`setuptools_scm` for SHA extraction:** Rejected. It defaults to a short SHA and focuses on SemVer strings, whereas the platform explicitly requires the full-precision 40-char SHA for strict reproducible builds. A 10-line `hatch_build.py` hook is precise and unambiguous.

## Implementation Plan
- [ ] **T1: Constants Cleanup** – In `vibe_cading/lego/constants.py`, remove `os.getenv` for `DEFAULT_CORNER_RADIUS` and `DEFAULT_LEAD_IN`. Rename them to `CORNER_RADIUS` and `LEAD_IN`. Update all references in `lego/technic_axle.py`, `lego/technic_beam.py`, and `lego_adapters/axle_to_pin_bore_adapter.py`.
- [ ] **T2: Structural Moves** – Move `tools/` to `vibe_cading/tools/`. Move `engine_api.json` and `print_profiles.json` to `vibe_cading/`. Do NOT move `print_profiles_user.json` (it remains a workspace override).
- [ ] **T3: Package Data & Config Loading** – 
      * Update `vibe_cading/print_settings.py` `_resolve_shipped_file()` to use `importlib.resources.files("vibe_cading").joinpath("print_profiles.json")`.
      * Update `_resolve_user_file()` to check: `os.getenv("VIBE_PRINT_PROFILES_USER_PATH")` -> `Path.cwd() / "print_profiles_user.json"` -> `_REPO_ROOT / "print_profiles_user.json"`.
      * Update `vibe_cading/_env.py` to check: `os.getenv("VIBE_ENV_PATH")` -> `Path.cwd() / ".env"` -> `_REPO_ROOT / ".env"`.
- [ ] **T4: Engine API Generator Fixes** – Update `vibe_cading/tools/gen_engine_api.py`, `validate_engine_api.py`, and `extractor.py` to read/write `engine_api.json` to the new `vibe_cading/` path. Ensure `--check` modes use `importlib.resources.files("vibe_cading")` or relative paths. 
- [ ] **T5: Build Infrastructure** – Create `pyproject.toml` (hatchling backend). Create `hatch_build.py` custom build hook to run `git rev-parse HEAD` -> `vibe_cading/__commit__.py`. Update `vibe_cading/__init__.py` to import `__commit__` (with fallback).
- [ ] **T6: CI & Documentation Sweep** – Update all `.github/workflows/` (ci.yml, engine-api.yml), `build.toml`, `build.py`, `pytest.ini` (`testpaths = tests`), and `CONTRIBUTING.md` to point to `vibe_cading/tools/` and the new JSON locations.

## Tests
| # | Test description | Expected assertion | File / location |
|---|------------------|--------------------|-----------------|
| 1 | `print_profiles.json` loads correctly via importlib | Tests pass, no deprecation warnings | `pytest` |
| 2 | End-to-end geometry build (`build.py`) | byte-identical to previous master | `python build.py` |
| 3 | Package installation simulation | `import vibe_cading; vibe_cading.__commit__` resolves, CLI scripts runnable as modules (`python -m vibe_cading.tools.preview`) | Local shell test |

## Success Criteria
1. The repository root contains no shipped JSON data files and no `tools/` directory.
2. `pip install .` works cleanly in a fresh environment.
3. `python -m vibe_cading.tools.preview` is executable.
4. `vibe_cading.__commit__` evaluates to the 40-character git SHA.
5. All CI workflows and local build scripts succeed against the new structure.

## Out of Scope
- Changing the geometric logic or output of any models.
- Publishing to PyPI.

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CI path drift | Update all workflow files and run the full CI suite locally before finalizing. |
| Missing package data in wheel | Ensure `pyproject.toml` implicitly or explicitly includes `*.json` in the build via hatchling configurations if needed. |

---

## Design Dialog Log

### Round 1
**TL proposal:**
> Use `pyproject.toml` with `hatchling`'s `force-include` to build-time map `tools/` and JSON files into the package, leaving the repo layout as-is.

**Requester challenge / contribution:**
> Rejected path of least resistance. Requested a principled architectural refactor to clean up the root directory and explicitly resolve user-override flows.

**Resolution:**
> Moving `tools/` and shipped JSON data into `vibe_cading/` structurally. Adopt standard `importlib.resources` and formal path cascades for `.env` and user overrides.

### Round 2
**Requester challenge / contribution:**
> Questioned whether `DEFAULT_CORNER_RADIUS` and `DEFAULT_LEAD_IN` should still be environment-variable tunable.

**Resolution:**
> Stripped `os.getenv` overrides. Locked as pure geometric constants `CORNER_RADIUS` and `LEAD_IN`. 

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(required if domain integrity gate is YES; skip if NO)*
- [x] Requester sign-off
- [x] TL sign-off

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [ ] Independent TL
- [ ] Independent Developer
- [ ] Independent Researcher

---

## Implementation Status
- [ ] All Implementation Plan tasks completed
- [ ] Test suite executed
- [ ] No new linter / static-check errors
- Developer note: 

---

## Post-Implementation Sign-Off

### TL Review
- [ ] **TL sign-off**
- TL review notes: 
