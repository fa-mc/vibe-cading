# Agentic Workflow

This project uses a structured three-role workflow for complex tasks.  The
roles are **Admin**, **Designer**, and **Developer**, each with a distinct
responsibility and recommended model tier.

## Roles

| Role | Model | Responsibility |
|---|---|---|
| **Admin** | Claude Opus 4.6 | Owns the instruction set (`copilot-instructions.md`). Works with the user to clarify requirements. Reviews lookback reports and decides corrective actions. |
| **Designer** | Claude Opus 4.6 | Domain reasoning and brainstorming. Pre-digests reference material, resolves design ambiguity, chooses dimensions and constraints. Produces a design brief — *what* to build and *why*. Reviews Developer output against acceptance criteria. |
| **Developer** | Claude Sonnet 4.6 | Owns code structure (classes, methods, build pipeline). Implements the design brief, runs analysis tools, validates output. Escalates design blockers to the Designer. Produces a lookback report at the end. |

## Phases

```
┌─────────────────────────────────────────────────────────────────┐
│  1. REQUIREMENTS          User ←→ Admin                        │
│     Clarify scope, constraints, and acceptance criteria.        │
│     Admin ensures instructions cover the task domain.           │
├─────────────────────────────────────────────────────────────────┤
│  2. DESIGN                User ←→ Designer                     │
│     Designer produces a design brief (.agents/plans/).              │
│     All domain ambiguities are resolved here, not deferred.     │
│     User approves the brief before proceeding.                  │
├─────────────────────────────────────────────────────────────────┤
│  3. EXECUTION             Developer (autonomous)                │
│     Developer designs code structure, then implements.          │
│     On design blockers → escalate to Designer (phase 3a).       │
│     On completion → produce lookback report (phase 4).          │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤
│  3a. ESCALATION           Developer → Designer                  │
│     Developer pauses, documents the blocker in the brief.       │
│     Designer resolves it, updates the brief, Developer resumes. │
├─────────────────────────────────────────────────────────────────┤
│  4. REVIEW                Designer validates output              │
│     Designer checks deliverables against acceptance criteria.   │
│     If criteria not met → back to phase 3 with corrections.     │
├─────────────────────────────────────────────────────────────────┤
│  5. LOOKBACK              Developer → Admin → User              │
│     Developer writes a structured lookback report.              │
│     Admin reviews, decides actions, reports to user.            │
└─────────────────────────────────────────────────────────────────┘
```

## Invoking Roles

Each role has a prompt file in `.github/prompts/`:

| Prompt file | How to invoke |
|---|---|
| `admin.prompt.md` | Type `#admin` in Copilot Chat |
| `designer.prompt.md` | Type `#designer` in Copilot Chat |
| `developer.prompt.md` | Type `#developer` in Copilot Chat |
| `lookback.prompt.md` | Type `#lookback` in Copilot Chat |

Switch models in the VS Code Copilot model picker to match the
recommended tier for each role.

## Design Brief Format

Design briefs are stored in `.agents/plans/` (git-ignored).  See
[docs/templates/design-brief-template.md](templates/design-brief-template.md)
for the required format.

A design brief must contain:

1. **Task summary** — one-paragraph scope statement.
2. **Coordinate system** — axis mapping, origin, orientation decisions
   (resolved by the Designer, not deferred to the Developer).
3. **Dimension table** — every key dimension with its source (STEP
   analysis, reference drawing, Lego spec, user input).
4. **Deliverables** — a numbered checklist, each with:
   - Feature name
   - Acceptance criteria (dimensions, tolerances, tool commands to validate)
   - Dependencies on other deliverables
5. **Design decisions** — any ambiguity the Designer identified and
   resolved (e.g. "simplify fillet as sharp edge", "use body-centred origin").
6. **Special considerations** — tolerances, print orientation, assembly
   order, interference risks, material constraints.
7. **Validation commands** — exact tool invocations to run after completion.

**What the brief does NOT contain:** Code structure, class names, method
signatures, or build pipeline — those are the Developer's responsibility.

## Escalation Protocol

When the Developer encounters a design blocker during execution:

1. **Stop work** on the blocked deliverable.
2. **Document the blocker** by appending to the design brief under
   `## Escalations`:
   - What was attempted
   - What failed or is ambiguous
   - What decision is needed
3. **Continue** with unblocked deliverables if possible.
4. **Invoke the Designer** (`#designer`) to resolve the escalation.
5. The Designer updates the brief and the Developer resumes.

## Lookback Report

Lookback reports are stored in `.agents/lookback/` (git-ignored).  See
[docs/templates/lookback-template.md](templates/lookback-template.md) for
the required format.

Feedback is categorised into four buckets:

| Category | Description | Routed to |
|---|---|---|
| **Instruction gap** | A class of error or edge case not covered by `copilot-instructions.md` | Admin |
| **Missing tool** | A capability that would have saved significant time or avoided errors | Designer (to spec) → Developer (to build) |
| **Design deficiency** | Ambiguity, missing detail, or incorrect assumption in the design brief | Designer |
| **Tooling bug** | An existing tool produced incorrect output or crashed | Developer (to fix) |

The Admin reviews the lookback and takes one or more actions:

- **Update instructions** — amend `copilot-instructions.md` to close the gap.
- **Commission a tool** — ask the Designer to spec a new tool, then the
  Developer to implement it.
- **No action** — the feedback is noted but no change is warranted.
- **Discuss with user** — the feedback raises a design question that needs
  human input.
