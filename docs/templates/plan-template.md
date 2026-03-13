# Plan: [TASK TITLE]

**Date:** YYYY-MM-DD
**Task ID:** [short slug, e.g. `sg90-servo-model`]
**Requested by:** [user / overseer]

## Task Summary

One paragraph describing the scope, goal, and constraints.

## Coordinate System

| Axis | Direction | Origin reference |
|---|---|---|
| X | | |
| Y | | |
| Z | | |

Mapping notes (STEP ↔ model coordinate relationship, if applicable):

## Pre-resolved Decisions

Ambiguities identified by the Planner and resolved before execution.

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | | | |

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
**Resolution:** *(filled by Planner)*
