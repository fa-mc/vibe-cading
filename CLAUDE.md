@vibe/INSTRUCTIONS.md

# Claude Code Specifics

The canonical, tool-neutral instruction set for this project is imported above
from [vibe/INSTRUCTIONS.md](vibe/INSTRUCTIONS.md). This file holds only the
instructions that depend on Claude Code's specific mechanisms (subagent
invocation, slash-command paths, runtime alias scaffolding). Other AI-coding
hosts have their own equivalent file (`.github/copilot-instructions.md`,
`.cursor/rules/`, etc.) that imports the same canonical instructions and adds
host-specific sections.

## Subagent Invocation

The Designer and Developer roles defined in [vibe/agents/](vibe/agents/) are
surfaced through Claude Code's subagent mechanism:

- Delegate domain/design work via the `designer` subagent — `Agent` tool with
  `subagent_type: "designer"`, or via user prompt *"use the designer agent
  to ..."*.
- Delegate implementation/execution via the `developer` subagent —
  `subagent_type: "developer"`.
- *Note:* `admin`, `tl`, and `pm` are intentionally not shipped as tracked
  subagents or slash commands in this repository. Maintainers who want them
  install the [core-agents](https://github.com/fa-mc/core-agents) Claude
  Code plugin per-host (`/plugin marketplace add` + `/plugin install
  core-agents@core-agents`) and either invoke its bare
  `/core-agents-admin`, `/core-agents-tl`, `/core-agents-pm` commands or
  drop personal wrappers into `~/.claude/`. Open-source contributors act
  as the Admin manually.

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
