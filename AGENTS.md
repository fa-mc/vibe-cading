# AGENTS.md — universal agent entry point

This is the single, host-neutral entry point for **any** AI coding agent working
in this repository (Claude Code, GitHub Copilot, Cursor, Aider, Google
Antigravity, etc.). Whatever harness you run, start here.

## Read this first

**All project, workflow, and convention instructions live in one canonical,
tool-neutral file:**

> ### → [`vibe/INSTRUCTIONS.md`](vibe/INSTRUCTIONS.md)

Read it in full before doing any work. It is the source of truth for agent
behaviour, workspace hygiene, validation gates, the multi-role workflow, CAD
conventions, and known modelling pitfalls. Nothing in this file overrides it.

## Repository layout for agents

| Path | What it is |
|---|---|
| [`vibe/INSTRUCTIONS.md`](vibe/INSTRUCTIONS.md) | **Canonical** tool-neutral instruction set — read this. |
| [`vibe/agents/`](vibe/agents/) | Role personas — `admin`, `designer`, `tl`, `developer`. Read the relevant `vibe/agents/<role>.md` before adopting that role. |
| [`vibe/commands/`](vibe/commands/) | Reusable command recipes (preview, section, step-analyze, diff, view, build, init-workspace). |
| [`vibe/templates/`](vibe/templates/) | Requirement / design-brief templates. |
| [`docs/agentic-workflow.md`](docs/agentic-workflow.md) | Full multi-role workflow specification. |

## How to onboard your agent

1. Load [`vibe/INSTRUCTIONS.md`](vibe/INSTRUCTIONS.md) into the agent's context
   (most hosts that read `AGENTS.md` can be pointed at it directly, or you can
   paste/import it via your host's instruction mechanism).
2. When you act as a named role, first read that role's persona file under
   [`vibe/agents/`](vibe/agents/) — do not infer it from memory.
3. Activate roles however your host supports it (subagents, slash commands, or an
   `@role` mention). The roles and rules are identical across hosts; only the
   *invocation mechanism* differs.

## Host-specific glue (ignore what isn't yours)

The canonical content above is provider-neutral. Each host wires it in through
its own thin pointer file plus any runtime scaffolding it needs:

| Host | Entry file | Notes |
|---|---|---|
| **Claude Code** | [`CLAUDE.md`](CLAUDE.md) | Imports `vibe/INSTRUCTIONS.md` and adds Claude-specific subagent invocation. Per-clone runtime aliases under `.claude/` are seeded by [`tools/init-claude-runtime.sh`](tools/init-claude-runtime.sh). **These are Claude-only — other hosts ignore `CLAUDE.md`, `.claude/`, and that script.** |
| **Any other host** | this `AGENTS.md` | Points at the same canonical `vibe/INSTRUCTIONS.md`. A host that prefers a native file (e.g. `.github/copilot-instructions.md`, `.cursor/rules/`) can add one that likewise imports `vibe/INSTRUCTIONS.md`; none ship yet. |

If you are *not* on Claude Code, you can disregard the entire `.claude/` tree,
`tools/init-claude-runtime.sh`, and any "subagent" / slash-command mechanics —
they are one host's implementation detail, not project requirements.
