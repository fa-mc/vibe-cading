# Agentic Workflow

This project uses a structured workflow for complex tasks, divided into **Contributor Roles** (included in the repository) and **Maintainer Roles** (handled by the human user or their own custom agents).

## Roles

| Role | Type | Responsibility |
|---|---|---|
| **Admin** | Maintainer | Has responsibility for the instruction set (`CLAUDE.md`). Works with the user to clarify requirements. Open-source contributors act as the Admin manually; maintainers may supply their own personal admin agent (loaded from `~/.claude/`). |
| **Designer** | Contributor | Domain reasoning and brainstorming. Pre-digests reference material, resolves design ambiguity, chooses dimensions and constraints. Produces a design brief — *what* to build and *why*. Reviews Developer output against acceptance criteria. |
| **Developer** | Contributor | Has responsibility for code structure (classes, methods, build pipeline). Implements the design brief, runs analysis tools, validates output. Escalates design blockers to the Designer. |
| **TL (Ad-hoc)** | Maintainer | Auxiliary software architecture role. Invoked *only* for major codebase refactors, rewriting CLI tools, or planning shared base classes (`cq_utils.py`). Not involved in everyday 3D CAD part creation. |

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
│     On completion → proceed to Review (phase 4).          │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤
│  3a. ESCALATION           Developer → Designer                  │
│     Developer pauses, documents the blocker in the brief.       │
│     Designer resolves it, updates the brief, Developer resumes. │
├─────────────────────────────────────────────────────────────────┤
│  4. REVIEW                Designer validates output              │
│     Designer checks deliverables against acceptance criteria.   │
│     If criteria not met → back to phase 3 with corrections.     │
└─────────────────────────────────────────────────────────────────┘
```

## Invoking Roles

Each contributor role's canonical persona is tracked under `vibe/agents/` (tool-neutral). For Claude Code specifically, `tools/init-claude-runtime.sh` regenerates per-clone runtime aliases at `.claude/agents/<name>.md` that delegate back to the canonical content; the `.claude/` tree itself is git-ignored. Note that `Admin` and `TL` are **Maintainer Roles** and are intentionally not shipped with this repository — open-source contributors drive those phases manually, while maintainers who prefer dedicated maintainer-role agents load their own personas from `~/.claude/` per-host.

| Role | Canonical persona | How to invoke (Claude Code) |
|---|---|---|
| Designer | `vibe/agents/designer.md` | Ask *"use the designer agent to ..."*, or invoke directly via the `Agent` tool with `subagent_type: "designer"` |
| Developer | `vibe/agents/developer.md` | Ask *"use the developer agent to ..."*, or invoke directly via the `Agent` tool with `subagent_type: "developer"` |

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
4. **Invoke the Designer** (the `designer` subagent) to resolve the escalation.
5. The Designer updates the brief and the Developer resumes.

