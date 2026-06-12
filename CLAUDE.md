@vibe/INSTRUCTIONS.md

## Universal Safety Invariants

- **Never Leak Secrets:** Never copy-paste, echo, or embed literal secret values (like API keys, tokens, or passwords) into command-line invocations, tool arguments, or conversational text. This creates a severe security breach by exposing credentials in command histories, agent transcripts, and logs. Always parse and source secrets dynamically using safe shell mechanisms (e.g. `export $(grep GH_TOKEN .env | xargs) && gh ...`).

# Claude Code Specifics

The canonical, tool-neutral instruction set for this project is imported above
from [vibe/INSTRUCTIONS.md](vibe/INSTRUCTIONS.md). This file holds only the
instructions that depend on Claude Code's specific mechanisms (subagent
invocation, slash-command paths, runtime alias scaffolding). Agents on any other host enter
through the universal [AGENTS.md](AGENTS.md) at the repo root, which routes to
the same canonical `vibe/INSTRUCTIONS.md`. A host that prefers a native file
(`.github/copilot-instructions.md`, `.cursor/rules/`, etc.) can add one that
likewise imports the canonical instructions; none ship yet.

## Subagent Invocation

The Admin, Designer, TL, and Developer roles defined in
[vibe/agents/](vibe/agents/) are surfaced through Claude Code's subagent
mechanism:

- Delegate workflow governance, instruction maintenance, mid-session
  interventions, and design-flow orchestration via the `admin` subagent —
  `Agent` tool with `subagent_type: "admin"`, or via user prompt *"use the
  admin agent to ..."* (or an `@admin` mention).
- Delegate domain/design work via the `designer` subagent —
  `subagent_type: "designer"`.
- Delegate code/system architecture — shared abstractions, base-class and
  `Protocol`/`ABC` contracts, cross-cutting refactors, post-implementation
  architectural review — via the `tl` subagent — `subagent_type: "tl"`.
  Invoke the TL only for architecturally-significant work; everyday
  single-part creation flows Designer → Developer without it.
- Delegate implementation/execution via the `developer` subagent —
  `subagent_type: "developer"`.
- *Note:* `pm` (Project Manager — backlog curation, cross-task
  prioritisation) is intentionally *not* shipped as a tracked subagent or
  slash command. On an open-source clone the human contributor drives
  backlog prioritisation directly; maintainers who prefer a dedicated PM
  agent can load their own persona from `~/.claude/` per-host. The `admin`,
  `designer`, `tl`, and `developer` subagents are the complete contributor
  toolkit; no additional install is required.

## `.claude/` runtime aliases

Claude Code discovers subagents at `.claude/agents/<name>.md` and project
slash commands at `.claude/commands/<name>.md`. The canonical content for
this project lives at [vibe/agents/](vibe/agents/) and
[vibe/commands/](vibe/commands/) (tracked); the entire `.claude/` tree is
per-clone scratch (git-ignored, except for `.claude/settings.json`).

To populate `.claude/agents/` and `.claude/commands/` with runtime aliases
that delegate to the canonical content under `vibe/`, run:

    tools/init-claude-runtime.sh

This script is idempotent and safe to re-run. Run it after every fresh clone,
and again after editing any file under `vibe/agents/` or `vibe/commands/` so
the runtime aliases stay in sync.

## Workspace Initialization (Claude Code addendum)

Steps 1–2 of workspace initialization are described in
[vibe/INSTRUCTIONS.md](vibe/INSTRUCTIONS.md) (universal). For a Claude Code
session specifically, also run step 3:

3. Seed the per-clone `.claude/` runtime aliases by running
   `tools/init-claude-runtime.sh` (see *`.claude/` runtime aliases* above).
