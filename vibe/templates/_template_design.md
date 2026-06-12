# Design: [Task Name]
<!-- Filename: YYYY-MM-DD-<task-slug>_design.md  (tracked in git under docs/design_plans/) -->

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

### Visual contract (CAD tasks)
<!-- REQUIRED for new CAD model classes and tasks changing visible geometry
     (axis convention, hole pattern, mating-face datum, dimensions affecting
     orientation). See vibe/INSTRUCTIONS.md → "Visual Contract Deliverable".
     Embed the co-located iso_ne preview SVG immediately below.
     Optional for refactors / internal API changes / non-CAD tasks. -->

![Design preview — iso_ne](../../visual_contracts/<YYYY-MM-DD>-<task-slug>_design_iso_ne.svg)

<!-- Optional additional views for asymmetric or hole-pattern-bearing geometry:
     ![top](../../visual_contracts/<slug>_design_top.svg)  ![front](../../visual_contracts/<slug>_design_front.svg) -->

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
<!-- Concrete test cases with explicit assertions. Reference existing test files or describe new ones.
     PRE-MERGE REPRESENTATIVE-SCALE ROW (required when the deliverable is a new
     model class, a build.toml geometry change, or a tool whose only true
     exercise is the full `python build.py` rebuild or a full-reference
     `boolean_diff.py`): include at least one row that runs that real full-scale
     path once before merge. Fast single-class preview/section probes do not
     substitute. See vibe/INSTRUCTIONS.md §4 "Representative-Scale Verification". -->

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

### Author sign-off (drafting role — Step 3 termination)
<!-- The drafting author (the Designer for a domain brief, or the TL for an architecture plan)
     self-marks these once all Step 3 termination conditions are met. This is the author's approval,
     not an independent verdict — the Independent reviewer block below collects the latter. -->
- [ ] Domain expert co-sign  *(required if domain integrity gate is YES; skip if NO)*
- [ ] Requester sign-off
- [ ] TL sign-off  *(for architecturally-significant work; the drafting role signs off otherwise)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
<!-- Each independent reviewer's findings live in `## Independent <Role> Review` sections appended
     below this artifact. Tick the matching box once that reviewer's verdict is APPROVE, or once
     APPROVE-WITH-CONDITIONS conditions have been applied AND re-confirmed by the same reviewer.
     Step 4 (human review) MUST NOT begin until every applicable box here is checked.
     Vibe-cading note: the Independent TL review is performed by a fresh-context `tl` subagent
     (the drafting author cannot self-sign here); the human Admin may perform it for trivial cases. -->
- [ ] Independent TL  *(always required; drafting author cannot self-sign here)*
- [ ] Independent Developer  *(always required)*
- [ ] Independent Researcher  *(required if domain integrity gate is YES; skip if NO)*

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
