---
description: Initialize the local workspace (tmp/, .agents/plans/, print_profiles_user.json)
---

Perform the workspace initialization steps documented in `vibe/INSTRUCTIONS.md` under "Workspace Initialization":

1. Ensure the git-ignored directories `tmp/` and `.agents/plans/` exist (create them if missing).
2. If `print_profiles_user.json` does not yet exist, copy `print_profiles.json.example` to `print_profiles_user.json` so the user can override printer-specific tolerances locally without a dirty git history.
3. If `.env` does not yet exist, copy `.env.example` to `.env`.
4. If your agent host requires a runtime-alias scaffolder to surface the
   canonical personas/commands under `vibe/`, run it now. This step is
   host-specific — see your host instruction file for the exact command.
   *(For Claude Code: `tools/init-claude-runtime.sh`, documented in `CLAUDE.md`;
   re-run it after editing any file under `vibe/agents/` or `vibe/commands/`.)*
5. Report what changed (or "already initialized" for files that were already present).

Do **not** modify any tracked configuration files. Do **not** install pip packages — the dev container already provides every dependency.
