# Provider-Agnostic Audit — Agent Assets

**Date:** 2026-06-02
**Role:** Admin (workspace audit / instruction-graph maintenance)
**Trigger:** Goal to make the repo LLM-provider-agnostic so collaborators on
non-Claude harnesses (named: Google Antigravity; also Copilot, Cursor, Aider)
can onboard. Question posed: *"Are we currently clean?"*
**Method:** Multi-agent audit (`provider-agnostic-audit` workflow, 38 agents) —
one classifier per neutral-file group, each leak adversarially re-verified by an
independent skeptic, plus a host-isolation-boundary + collaborator-gap pass.

## Verdict: NO — not clean. Two distinct problems.

The repo has a **two-layer** design:

1. **Data layer** — canonical, tool-neutral content under `vibe/`
   (`vibe/INSTRUCTIONS.md`, `vibe/agents/*.md`, `vibe/commands/*.md`,
   `vibe/templates/*`). *(Note: the neutral tree is `vibe/`, NOT `.agents/`.
   `.agents/` is git-ignored plans/scratch — `.agents/plans/` is the only
   tracked part.)*
2. **Entry layer** — per-host glue that imports the data layer. Today only
   `CLAUDE.md` (+ the git-ignored `.claude/` runtime-alias tree) exists.

**Problem 1 — Claude-isms have leaked INTO the neutral `vibe/` tree.** ~20
confirmed leaks, dominated by one pattern: neutral files cite **`CLAUDE.md`** as
the home of conventions/procedures that actually live in **`vibe/INSTRUCTIONS.md`**.
These are *doubly wrong*: (a) they name a provider-specific file, and (b) the
cited content is not even in that file.

> **Why it went unnoticed:** `CLAUDE.md` line 1 is `@vibe/INSTRUCTIONS.md`, so in
> a *Claude Code* session the neutral content is pulled into context and
> "per CLAUDE.md under 'Asset Validation'" resolves fine. For a non-Claude host,
> `CLAUDE.md` is never loaded and the citation points at the wrong file. The
> leak is invisible to the only host currently wired in.

**Problem 2 — The entry layer is wired for exactly one provider.** The
quarantine boundary is *strong* (Claude glue is cleanly isolated; no neutral
content is duplicated into `CLAUDE.md`/`.claude/`). But **no non-Claude host file
exists** — verified absent: `.github/copilot-instructions.md`, `.cursor/rules/`,
`AGENTS.md`, `GEMINI.md`, any Antigravity/`.idx` config. Three files
(`CLAUDE.md:9-10`, `CONTRIBUTING.md:84`, `vibe/INSTRUCTIONS.md:5`) assert in
present tense that other hosts "have their own equivalent file… that imports the
same canonical instructions" — that claim is currently **false/aspirational**. An
Antigravity collaborator today gets *no* auto-loaded entry point and is actively
misled by onboarding docs into thinking their host is already wired.

---

## Confirmed leaks (Problem 1) — grouped by fix

### A. `per CLAUDE.md` → should be `per vibe/INSTRUCTIONS.md` (HIGH — doubly wrong)

| File:line | Snippet | Real home of cited content |
|---|---|---|
| `vibe/agents/developer.md:31` | "Follow all conventions in `CLAUDE.md`" — Developer's **primary** convention pointer | conventions live in `vibe/INSTRUCTIONS.md` (Code Quality, Zero-Datum, Tolerance, OCP Viewer, Modelling Pitfalls) |
| `vibe/agents/tl.md:56-57` | Deep-Modules Dual-Lens Rule "(`CLAUDE.md`)" | `vibe/INSTRUCTIONS.md:133` |
| `vibe/commands/diff.md:12` | "Per `CLAUDE.md`…" feature reconciliation | `vibe/INSTRUCTIONS.md` "Reverse-engineering from STEP files" |
| `vibe/commands/preview.md:6,15` | "documented in `CLAUDE.md` under 'Asset Validation'" / "Step 0" | `vibe/INSTRUCTIONS.md` "Asset Validation" |
| `vibe/commands/section.md:12` | "Per `CLAUDE.md` ('Blind Holes…' / 'Validating Internal Intersections…')" | `vibe/INSTRUCTIONS.md` (both headings) |
| `vibe/commands/step-analyze.md:6,14` | "documented in `CLAUDE.md` under 'Reverse-engineering from STEP files'" | `vibe/INSTRUCTIONS.md` |
| `vibe/commands/view.md:12` | "Per `CLAUDE.md` ('OCP Viewer — Dedicated Entry Point')" | `vibe/INSTRUCTIONS.md:217` |
| `vibe/commands/init-workspace.md:5` | "steps documented in `CLAUDE.md` under 'Workspace Initialization'" | `vibe/INSTRUCTIONS.md` "Workspace Initialization" |

### B. `CLAUDE.md` hardcoded as the instruction-graph / do-not-edit file (MEDIUM)

Generalize to "the instruction graph (`vibe/INSTRUCTIONS.md`, role/command/
template files) and your host's instruction file (e.g. `CLAUDE.md` for Claude
Code)":

| File:line | Snippet |
|---|---|
| `vibe/agents/admin.md:44` | lists `CLAUDE.md` first in the instruction graph Admin edits |
| `vibe/agents/designer.md:85` | "Modify `CLAUDE.md` (that is the Admin's job)" |
| `vibe/agents/tl.md:113` | "Modify `CLAUDE.md` or the instruction graph" |
| `vibe/agents/developer.md:61` | "Modify `CLAUDE.md` — flag gaps to the user" |
| `docs/agentic-workflow.md:9` | "instruction set (`CLAUDE.md`, `vibe/INSTRUCTIONS.md`, role files, docs)" |

### C. Claude-only paths/tool-names in the neutral `vibe/INSTRUCTIONS.md` (MEDIUM/LOW)

| File:line | Snippet | Fix |
|---|---|---|
| `vibe/INSTRUCTIONS.md:80` | "loaded their own PM persona from `~/.claude/`" | "via their host's user-config dir (Claude Code: `~/.claude/`)" |
| `vibe/INSTRUCTIONS.md:84` | "tighten the `Task` block" (`Task` = Claude tool) | "tighten the spawn brief" |
| `vibe/INSTRUCTIONS.md:88` | "`/review` skill" in a universal reviewer list | "an automated review pass / the host's review command" |

### D. `.claude/` runtime-alias seeding baked into a neutral command (HIGH)

`vibe/commands/init-workspace.md:10-20` (step 4) hardcodes
`tools/init-claude-runtime.sh` + `.claude/agents|commands` regeneration as a
*universal* init step. **Fix:** move step 4 into `CLAUDE.md` (it already has a
"Workspace Initialization (Claude Code addendum)" section); leave a host-neutral
pointer in the canonical command ("run your host's runtime scaffolder, if any —
see your host instruction file").

### Deliberately NOT flagged (verified actually-fine / borderline-acceptable)

- **"subagent" terminology** throughout `vibe/` — the canonical file
  deliberately uses it as a *cross-host* concept with a "host's … mechanism"
  hedge (`INSTRUCTIONS.md:64,78,81`). Skeptics ruled these fine. Leave.
- **`@role` mentions** (`@admin`, `@developer`, …) — cross-host naming
  convention; resolves to neutral persona files. Leave.
- **`docs/agentic-workflow.md:52,54-59`** — the "How to invoke (Claude Code)"
  table is explicitly *labeled* for Claude Code → honestly scoped, not a leak.
  (But see Problem 2: it is the *only* invocation guidance, so a non-Claude
  reader gets no on-ramp — add a neutral framing sentence + per-host appendix.)
- **`tools/view.py` `ocp_vscode`** references — that's the CAD viewer tool, not
  an AI host. Not a leak.

---

## Boundary + collaborator gap (Problem 2)

- **Quarantine: STRONG.** `CLAUDE.md` is a thin shim (`@vibe/INSTRUCTIONS.md` +
  3 genuinely-Claude sections). `.claude/` is git-ignored scratch (except
  `settings.json`, which holds only Claude permission lists).
  `tools/init-claude-runtime.sh` touches only `.claude/`. **No Claude mechanism
  leaks the *other* direction into a place it shouldn't be** — the isolation
  itself is clean.
- **Missing host support.** Only `CLAUDE.md` performs the canonical import, via
  Claude's `@`-syntax no other host parses. An Antigravity/Copilot/Cursor
  collaborator's harness auto-loads nothing project-specific.
- **False present-tense claims** at `CLAUDE.md:9-10`, `CONTRIBUTING.md:84`,
  `vibe/INSTRUCTIONS.md:5` ("other hosts have their own equivalent file").
- **TODO.md does not track this gap.**

**Minimum fix to make the agnostic claim true:** add a root **`AGENTS.md`** (the
emerging cross-host convention read by Antigravity, Cursor, Copilot, Aider)
containing a pointer to `vibe/INSTRUCTIONS.md` + a note that `.claude/`,
subagents, and `tools/init-claude-runtime.sh` are Claude-only and should be
ignored by other hosts. Reword the three claims from fact to honest aspiration
until a real host file lands.

---

## Remediation

**Batch A — mechanical, low-risk — ✅ APPLIED 2026-06-02 (working tree, not yet committed):**
sections A–D above. Edited: `vibe/commands/{preview,section,step-analyze,diff,view,init-workspace}.md`,
`vibe/agents/{developer,tl,designer,admin}.md`, `docs/agentic-workflow.md`,
`vibe/INSTRUCTIONS.md`. Net effect: the neutral tree stops naming `CLAUDE.md` as a
content/convention home and points at `vibe/INSTRUCTIONS.md`; every residual
`CLAUDE.md` mention is now a labeled "for Claude Code" example. `.claude/`
runtime aliases re-synced via `tools/init-claude-runtime.sh`. No policy change.

> Verified post-edit: only labeled-example `CLAUDE.md` mentions remain in the
> neutral tree (`admin.md:46`, `developer.md:31`, `init-workspace.md:13`,
> `docs/agentic-workflow.md:9`, `INSTRUCTIONS.md:5`); `` `Task` `` block and
> `` `/review` `` skill tokens removed; `~/.claude/` demoted to a labeled example.

**Batch B — single access point — ✅ APPLIED 2026-06-02 (same branch):**
User asked for "one access point for all agents." Delivered:
1. Added root **`AGENTS.md`** — the universal entry for any host (Claude Code,
   Copilot, Cursor, Aider, Antigravity); routes to canonical `vibe/INSTRUCTIONS.md`,
   documents the `vibe/` layout + role-onboarding steps, and quarantines the
   Claude-only glue (`CLAUDE.md`, `.claude/`, `init-claude-runtime.sh`) as
   "ignore what isn't yours". Single canonical content, single discoverable entry.
2. Reworded the false present-tense multi-host claims at `CLAUDE.md:8-11` and
   `CONTRIBUTING.md:84` to reference `AGENTS.md` and mark native per-host files as
   "none ship yet". (`vibe/INSTRUCTIONS.md:5` was already correctly host-neutral.)

> Design note — true "one access point": content is single-sourced
> (`vibe/INSTRUCTIONS.md`). `AGENTS.md` is the universal *entry filename* that
> non-Claude hosts auto-discover; Claude Code keeps its native `CLAUDE.md` (which
> imports the same file). So one canonical source + one universal front door.

**Remaining (optional, not done):** a `TODO.md` row tracking native per-host
files if/when a contributor wants Copilot/Cursor-native entries. The human will
onboard Antigravity directly by pointing it at `AGENTS.md` / `vibe/INSTRUCTIONS.md`.
