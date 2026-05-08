# Design: [Task Name]
<!-- Filename: YYYY-MM-DD-<task-slug>_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: <!-- path to YYYY-MM-DD-<task-slug>_req.md -->
- **Requester role**: <!-- whoever authored the requirements -->
- **Date**: <!-- YYYY-MM-DD (must match the filename prefix) -->
- **Dialog rounds**: <!-- number of TL-requester rounds before sign-off -->

---

## Objective
<!-- One sentence restatement of goal, derived from requirements. -->

## Architecture / Approach

### Approach chosen
<!-- Describe the solution: modules, classes, data flow, interface contracts. -->

### Alternatives rejected
<!-- - Option X: rejected because ... -->

## Data & Interface Contracts
<!-- REQUIRED if domain integrity gate was YES.
     Specify schemas, types, field names, invariants, and error semantics. -->
-

## Implementation Plan
<!-- Sequenced tasks for @developer. Each task is atomic and independently verifiable. -->
- [ ] **T1** –
- [ ] **T2** –
- [ ] **T3** –

## Tests
<!-- Concrete test cases with explicit assertions. Reference existing test files or describe new ones. -->

| # | Test description | Expected assertion | File / location |
|---|------------------|--------------------|-----------------|
| 1 | | | |
| 2 | | | |

## Success Criteria
<!-- Measurable, objectively verifiable conditions for @developer to claim the task done. -->
1.
2.

## Out of Scope
<!-- Mirror from requirements; expand if the design dialog surfaced new exclusions. -->
-

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| | |

---

## Design Dialog Log
<!-- Record each round of the TL-requester co-design dialog. Auto-populated during dialog. -->

### Round 1
**TL proposal:**
>

**Requester challenge / contribution:**
>

**Resolution:**
>

<!-- Add rounds as needed -->

---

## Sign-off
<!-- All applicable boxes must be checked before presenting to the human (Step 4). -->
- [ ] Domain expert co-sign  *(required if domain integrity gate is YES; skip if NO)*
- [ ] Requester sign-off
- [ ] TL sign-off

---

## Implementation Status
<!-- Populated by #developer at the start of Step 5 Phase A. -->
- [ ] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [ ] Test suite executed — result: <!-- "N/N tests pass" or paste summary -->
- [ ] No new linter / static-check errors
- Developer note: <!-- one-line summary of what was done and any approved deviations from the plan -->

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [ ] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes: <!-- If issues found, list them here and transition back to #developer. Leave empty when clean. -->

### Domain Expert Review *(required if domain integrity gate is YES; skip if NO)*
- [ ] **Domain expert sign-off** — data contracts, interface schemas, and domain invariants verified against Data & Interface Contracts
- Domain expert review notes: <!-- If issues found, list them here and transition back to #developer. Leave empty when clean. -->

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes: <!-- optional directions or conditions -->
