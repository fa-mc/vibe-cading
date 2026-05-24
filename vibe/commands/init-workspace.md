---
description: Initialize the local workspace (tmp/, .agents/plans/, print_profiles_user.json)
---

Perform the workspace initialization steps documented in `CLAUDE.md` under "Workspace Initialization":

1. Ensure the git-ignored directories `tmp/` and `.agents/plans/` exist (create them if missing).
2. If `print_profiles_user.json` does not yet exist, copy `print_profiles.json.example` to `print_profiles_user.json` so the user can override printer-specific tolerances locally without a dirty git history.
3. If `.env` does not yet exist, copy `.env.example` to `.env`.
4. Seed the per-clone `.claude/` runtime aliases by running:

   ```
   tools/init-claude-runtime.sh
   ```

   This regenerates `.claude/agents/<name>.md` and `.claude/commands/<name>.md`
   for every canonical entry under `vibe/agents/` and `vibe/commands/`. The
   `.claude/` tree is git-ignored (per `.gitignore`); the canonical content is
   tracked under `vibe/`. Re-run the script after editing any file under
   `vibe/agents/` or `vibe/commands/` so the runtime aliases stay in sync.
5. Report what changed (or "already initialized" for files that were already present).

Do **not** modify any tracked configuration files. Do **not** install pip packages — the dev container already provides every dependency.
