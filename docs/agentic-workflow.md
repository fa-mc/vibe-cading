# Agentic Workflow

This project uses a structured three-role workflow for complex tasks.  The
roles are **Overseer**, **Planner**, and **Developer**, each with a distinct
responsibility and recommended model tier.

## Roles

| Role | Model | Responsibility |
|---|---|---|
| **Overseer** | Claude Opus 4.6 | Owns the instruction set (`copilot-instructions.md`). Works with the user to clarify requirements. Reviews lookback reports and decides corrective actions. |
| **Planner** | Claude Opus 4.6 | Translates requirements into a structured, unambiguous plan. Pre-digests coordinate systems, dimension choices, and feature priorities so the Developer receives clear directives. Reviews Developer output against acceptance criteria. |
| **Developer** | Claude Sonnet 4.6 | Executes the plan. Writes code, runs analysis tools, validates output. Escalates blockers mid-task. Produces a lookback report at the end. |

## Phases

```
┌─────────────────────────────────────────────────────────────────┐
│  1. REQUIREMENTS          User ←→ Overseer                     │
│     Clarify scope, constraints, and acceptance criteria.        │
│     Overseer ensures instructions cover the task domain.        │
├─────────────────────────────────────────────────────────────────┤
│  2. PLANNING              User ←→ Planner                      │
│     Planner produces a structured plan (tmp/plans/).            │
│     All ambiguous decisions are resolved here, not deferred.    │
│     User approves the plan before proceeding.                   │
├─────────────────────────────────────────────────────────────────┤
│  3. EXECUTION             Developer (autonomous)                │
│     Developer follows the plan step-by-step.                    │
│     On blockers → escalate to Planner (phase 3a).               │
│     On completion → produce lookback report (phase 4).          │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤
│  3a. ESCALATION           Developer → Planner                   │
│     Developer pauses, documents the blocker in the plan file.   │
│     Planner resolves it, updates the plan, Developer resumes.   │
├─────────────────────────────────────────────────────────────────┤
│  4. REVIEW                Planner validates output               │
│     Planner checks deliverables against acceptance criteria.    │
│     If criteria not met → back to phase 3 with corrections.     │
├─────────────────────────────────────────────────────────────────┤
│  5. LOOKBACK              Developer → Overseer → User           │
│     Developer writes a structured lookback report.              │
│     Overseer reviews, decides actions, reports to user.         │
└─────────────────────────────────────────────────────────────────┘
```

## Invoking Roles

Each role has a prompt file in `.github/prompts/`:

| Prompt file | How to invoke |
|---|---|
| `overseer.prompt.md` | Type `#overseer` in Copilot Chat |
| `planner.prompt.md` | Type `#planner` in Copilot Chat |
| `developer.prompt.md` | Type `#developer` in Copilot Chat |
| `lookback.prompt.md` | Type `#lookback` in Copilot Chat |

Switch models in the VS Code Copilot model picker to match the
recommended tier for each role.

## Plan Format

Plans are stored in `tmp/plans/` (git-ignored).  See
[docs/templates/plan-template.md](templates/plan-template.md) for the
required format.

A plan must contain:

1. **Task summary** — one-paragraph scope statement.
2. **Coordinate system** — axis mapping, origin, orientation decisions
   (resolved by the Planner, not deferred to the Developer).
3. **Deliverables** — a numbered checklist, each with:
   - Feature name
   - Acceptance criteria (dimensions, tolerances, tool commands to validate)
   - Dependencies on other deliverables
4. **Pre-resolved decisions** — any ambiguity the Planner identified and
   resolved (e.g. "simplify fillet as sharp edge", "use body-centred origin").
5. **Validation commands** — exact tool invocations to run after completion.

## Escalation Protocol

When the Developer encounters a blocker during execution:

1. **Stop work** on the blocked deliverable.
2. **Document the blocker** by appending to the plan file under
   `## Escalations`:
   - What was attempted
   - What failed or is ambiguous
   - What decision is needed
3. **Continue** with unblocked deliverables if possible.
4. **Invoke the Planner** (`#planner`) to resolve the escalation.
5. The Planner updates the plan and the Developer resumes.

## Lookback Report

Lookback reports are stored in `tmp/lookback/` (git-ignored).  See
[docs/templates/lookback-template.md](templates/lookback-template.md) for
the required format.

Feedback is categorised into four buckets:

| Category | Description | Routed to |
|---|---|---|
| **Instruction gap** | A class of error or edge case not covered by `copilot-instructions.md` | Overseer |
| **Missing tool** | A capability that would have saved significant time or avoided errors | Planner (to spec) → Developer (to build) |
| **Plan deficiency** | Ambiguity, missing detail, or incorrect assumption in the plan | Planner |
| **Tooling bug** | An existing tool produced incorrect output or crashed | Developer (to fix) |

The Overseer reviews the lookback and takes one or more actions:

- **Update instructions** — amend `copilot-instructions.md` to close the gap.
- **Commission a tool** — ask the Planner to spec a new tool, then the
  Developer to implement it.
- **No action** — the feedback is noted but no change is warranted.
- **Discuss with user** — the feedback raises a design question that needs
  human input.
