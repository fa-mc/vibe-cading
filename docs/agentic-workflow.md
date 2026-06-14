# Agentic Workflow

This project uses a structured workflow for complex tasks. Four **Contributor Roles** are shipped as agent personas under `vibe/agents/`; backlog prioritisation (PM) is left to the human contributor, who also remains the final acceptance authority for merges and project policy above all shipped roles.

## Roles

| Role | Type | Responsibility |
|---|---|---|
| **Admin** | Contributor | Workflow governance and the instruction set (`vibe/INSTRUCTIONS.md`, role files, docs, and the active host instruction file — e.g. `CLAUDE.md` for Claude Code). Clarifies requirements, runs mid-session interventions, initiates the design flow, and orchestrates wrap-ups. Diagnoses and routes; does not write model code, design briefs, or architectural blueprints. Surfaces policy-level changes to the human for sign-off. |
| **Designer** | Contributor | Domain reasoning and brainstorming. Pre-digests reference material, resolves design ambiguity, chooses dimensions and constraints. Produces a design brief — *what* to build and *why*. Reviews Developer output against acceptance criteria. |
| **TL** | Contributor | Code/system architecture: shared abstractions, component boundaries, base-class and `Protocol`/`ABC` contracts, cross-cutting refactors, `vibe_cading/tools/` CLI design, and post-implementation architectural review. **Invoked for architecturally-significant work only** — a new shared abstraction, a `cq_utils.py` / base-class change, a refactor spanning multiple model families. Everyday single-part creation flows Designer → Developer without it. |
| **Developer** | Contributor | Per-part code structure (classes, methods, build pipeline). Implements the design brief, runs analysis tools, validates output. Escalates design blockers to the Designer and architecturally-significant decisions to the TL. |

## Phases

```
┌─────────────────────────────────────────────────────────────────┐
│  1. REQUIREMENTS          User ←→ Admin                          │
│     Clarify scope, constraints, and acceptance criteria.         │
│     Admin ensures instructions cover the task domain, then       │
│     routes: trivial → Developer; non-trivial → Designer.         │
├─────────────────────────────────────────────────────────────────┤
│  2. DESIGN                User ←→ Designer                        │
│     Designer produces a design brief (.agents/plans/).           │
│     All domain ambiguities are resolved here, not deferred.      │
│     User approves the brief before proceeding.                   │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│  2b. ARCHITECTURE (only if architecturally significant)          │
│     Admin pulls in the TL. TL designs shared abstractions,       │
│     contracts, and boundaries in an architecture plan before     │
│     the Developer writes code. Skipped for everyday parts.       │
├─────────────────────────────────────────────────────────────────┤
│  3. EXECUTION             Developer (autonomous)                 │
│     Developer owns per-part code structure, then implements.     │
│     On design blockers → Designer (3a); on architectural         │
│     blockers → TL (3a). On completion → Review (phase 4).        │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│  3a. ESCALATION   Developer → Designer (design) / TL (arch)      │
│     Developer pauses, documents the blocker in the brief/plan.   │
│     The resolving role updates it; the Developer resumes.        │
├─────────────────────────────────────────────────────────────────┤
│  4. REVIEW                Designer + TL validate output          │
│     Designer checks deliverables against acceptance criteria.    │
│     TL reviews code architecture against structural invariants   │
│     (architecturally-significant work only).                     │
│     If criteria not met → back to phase 3 with corrections.      │
└─────────────────────────────────────────────────────────────────┘
```

## Invoking Roles

Each contributor role's canonical persona is tracked under `vibe/agents/` (tool-neutral). For Claude Code, `vibe_cading/tools/init-claude-runtime.sh` regenerates per-clone runtime aliases at `.claude/agents/<name>.md` that delegate back to the canonical content; the `.claude/` tree itself is git-ignored. For Google Antigravity (agy), you can define a subagent dynamically by loading the system prompt from the canonical file. The four roles below are shipped; **PM** (backlog prioritisation) is intentionally not shipped — the human contributor drives it. The human also remains the final acceptance authority for merges and project policy.

| Role | Canonical persona | How to invoke (Claude Code) | How to invoke (Google Antigravity) |
|---|---|---|---|
| Admin | `vibe/agents/admin.md` | Ask *"use the admin agent to ..."* / `@admin`, or invoke directly via the `Agent` tool with `subagent_type: "admin"` | Invoke a subagent defined with the system prompt from `vibe/agents/admin.md` |
| Designer | `vibe/agents/designer.md` | Ask *"use the designer agent to ..."*, or invoke directly via the `Agent` tool with `subagent_type: "designer"` | Invoke a subagent defined with the system prompt from `vibe/agents/designer.md` |
| TL | `vibe/agents/tl.md` | Ask *"use the tl agent to ..."* / `@tl`, or invoke directly via the `Agent` tool with `subagent_type: "tl"` (architecturally-significant work only) | Invoke a subagent defined with the system prompt from `vibe/agents/tl.md` (architecturally-significant work only) |
| Developer | `vibe/agents/developer.md` | Ask *"use the developer agent to ..."*, or invoke directly via the `Agent` tool with `subagent_type: "developer"` | Invoke a subagent defined with the system prompt from `vibe/agents/developer.md` |

## Design Brief Format

Design briefs are stored in `.agents/plans/` (git-ignored).  See
[vibe/templates/_template_design.md](../vibe/templates/_template_design.md)
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
signatures, or build pipeline — per-part structure is the Developer's
responsibility; architecturally-significant structure (shared abstractions,
base-class and `Protocol`/`ABC` contracts) is decided by the TL in a separate
architecture plan, not deferred to the Developer ad hoc.

## Escalation Protocol

When the Developer encounters a blocker during execution:

1. **Stop work** on the blocked deliverable.
2. **Document the blocker** by appending to the design brief (or the TL's
   architecture plan) under `## Escalations`:
   - What was attempted
   - What failed or is ambiguous
   - What decision is needed
3. **Continue** with unblocked deliverables if possible.
4. **Route by blocker type:**
   - **Design blocker** (a dimension, feature intent, or geometry question) →
     invoke the **Designer** (the `designer` subagent).
   - **Architectural blocker** (a shared contract that won't generalise, an
     abstraction forcing boundary hacks) → invoke the **TL** (the `tl` subagent).
5. The resolving role updates the brief/plan and the Developer resumes.

