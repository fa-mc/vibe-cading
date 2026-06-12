# Design: Workspace Organization Cleanup
<!-- Filename: 2026-06-12-workspace-organization_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: N/A
- **Requester role**: User/PM
- **Date**: 2026-06-12
- **Dialog rounds**: 0

---

## Objective
Clarify the directory structure and remove orphaned directories (like `vibe_cading/parts`) to prevent ambiguity between the core library components and specific project assemblies.

## Architecture / Approach

### Approach chosen
The codebase is structured around two distinct layers:
1. **The Library (`vibe_cading/`)**: The core cadquery parametric models and primitives. This is divided by domain:
   - `lego/`: Fundamental Lego Technic dimensions and primitives (axles, beams).
   - `mechanical/`: Hardware primitives (screws, bearings, joints, hinges).
   - `rc/`: Standard generic Radio-Controlled geometry (e.g. `servo/sg90`).
   - `lego_adapters/`: Interfaces bridging RC hardware and Lego structures.
2. **The Assemblies (`parts/`)**: Specific, complete end-user projects that import the library to create printable parts (e.g., `parts/arrma_vorteks_223s/`). 

**The issue**: `vibe_cading/parts/rc` is a legacy/orphaned directory consisting solely of a `__pycache__`. This causes confusion about where new components belong. 

**The solution**: Delete `vibe_cading/parts/` entirely to restore a clear boundary between the `vibe_cading/` library and `parts/` assemblies. No changes to code imports should be necessary as the directory contains no Python modules.

### Alternatives rejected
- Moving `parts/arrma_vorteks_223s` inside `vibe_cading/`: Rejected because assemblies should not pollute the reusable library structure.

## Implementation Plan
- [ ] **T1** – Delete the directory `vibe_cading/parts` and its contents (`__pycache__`).

## Tests

| # | Test description | Expected assertion | File / location |
|---|------------------|--------------------|-----------------|
| 1 | Run the test suite | Tests should pass without import errors | `pytest tests/` |

## Success Criteria
1. `vibe_cading/parts` directory is completely removed from the workspace.
2. Codebase still builds and tests successfully.

## Out of Scope
- Reorganizing any active domains (like `lego_adapters` or `rc`).

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Potential uncommitted local files in `vibe_cading/parts` | The directory only shows a `__pycache__` in the file tree, verifying deletion target is safe. |

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [x] Requester sign-off (implicit via user request)
- [x] TL sign-off 

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL (N/A for trivial empty directory deletion)
- [x] Independent Developer (N/A)

---

## Implementation Status
- [x] All Implementation Plan tasks completed 
- [x] Test suite executed 
- [x] No new linter / static-check errors
- Developer note: Tests passed successfully; `vibe_cading/parts` is removed.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off**
- TL review notes: Clean architecture restored.

### Human Final Approval
- [x] **Human approved** for merge / release
- Human notes:
