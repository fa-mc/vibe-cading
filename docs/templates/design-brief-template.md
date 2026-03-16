# Design Brief: [TASK TITLE]

**Date:** YYYY-MM-DD
**Task ID:** [short slug, e.g. `sg90-servo-model`]
**Requested by:** [user / admin]

## Task Summary

One paragraph describing the scope, goal, and constraints.

## Coordinate System

| Axis | Direction | Origin reference |
|---|---|---|
| X | | |
| Y | | |
| Z | | |

Mapping notes (STEP ↔ model coordinate relationship, if applicable):

## Dimension Table

All key dimensions with their source.

| Dimension | Value | Source |
|---|---|---|
| | | STEP analysis / reference drawing / Lego spec / user input |

## Design Decisions

Domain ambiguities identified by the Designer and resolved before execution.

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | | | |

## Special Considerations

Tolerances, print orientation, assembly order, interference risks, material
constraints, or other domain-specific concerns.

-

## Deliverables

Each deliverable is a discrete, testable unit of work.

### D1 — [Feature name]

**Description:** What to build or change.

**Acceptance criteria:**
- [ ] Criterion 1 (e.g. "body width = 22.6 mm in Y")
- [ ] Criterion 2

**Dependencies:** None | D2, D3

---

### D2 — [Feature name]

**Description:**

**Acceptance criteria:**
- [ ] Criterion 1

**Dependencies:** D1

---

*(Add more deliverables as needed)*

## Validation Commands

Exact commands to run after all deliverables are complete:

```bash
# Example: visual preview
python3 tools/preview.py models.module.ClassName --views top front left

# Example: internal geometry check (vital for blind holes/snap rings)
python3 tools/section_slicer.py tmp/output.step --axis Z --at 4.0 --report
# Example: topological validation for single contiguous solid
# Developer should assert len(result.solids().vals()) == 1 in their python execution script, or run a python check like:
python3 -c "from models.module import ClassName; assert len(ClassName().solid.val().solids()) == 1"


# Example: volume comparison against reference STEP
python3 tools/boolean_diff.py reference.step models.module.ClassName --model --align-bbox
```

## Escalations

*(Appended by the Developer during execution if blockers arise)*

### E1 — [Blocker title]

**Date:**
**Blocked deliverable:** D?
**What was attempted:**
**What failed / is ambiguous:**
**Decision needed:**
**Resolution:** *(filled by Designer)*
