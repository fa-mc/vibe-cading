---
description: Initialize the local workspace (tmp/, .agents/plans/, machine_profiles_user.json)
---

Perform the workspace initialization steps documented in `CLAUDE.md` under "Workspace Initialization":

1. Ensure the git-ignored directories `tmp/` and `.agents/plans/` exist (create them if missing).
2. If `machine_profiles_user.json` does not yet exist, copy `machine_profiles.json.example` to `machine_profiles_user.json` so the user can override printer-specific tolerances locally without a dirty git history.
3. If `.env` does not yet exist, copy `.env.example` to `.env`.
4. Report what changed (or "already initialized" for files that were already present).

Do **not** modify any tracked configuration files. Do **not** install pip packages — the dev container already provides every dependency.
