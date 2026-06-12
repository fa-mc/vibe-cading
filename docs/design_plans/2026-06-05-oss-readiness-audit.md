# OSS Publication-Readiness Audit — `fa-mc/vibe-cading`

**Date:** 2026-06-05 · **Auditor:** Admin (spawned by PM) · **Scope:** read-only audit of tracked files (`git ls-files`, 185 files) ahead of flipping the repo PRIVATE → PUBLIC. No fixes applied.

## Verdict

**NOT-READY to flip public — 2 blockers.** The repository is structurally clean on the dimensions that usually sink an OSS launch (no secrets, no live tokens, license headers pass, CI green, `.gitignore` correct, no stray binaries, README/CONTRIBUTING links resolve, provider-neutrality of `vibe/` intact). The blockers are **private-business-strategy leakage in tracked TODO/CI files** — the supposedly-purged `vibe-cading-platform` SaaS plan is still named in plain text in `TODO.md` and re-described in `todo.md`'s cleanup note, and the private platform's MCP consumer is named in two CI/contributor files. These must be scrubbed before the flip; everything else is should-fix or nice-to-have. Additionally a **case-variant filename collision** (`TODO.md` vs `todo.md`) will break clones on macOS/Windows default filesystems and should be resolved as part of the same TODO consolidation.

## Findings (severity-ranked)

| # | Severity | Dimension | Finding | Evidence (file:line) | Suggested owner |
|---|---|---|---|---|---|
| 1 | **blocker** | Private-plugin/strategy leakage | `TODO.md` §"Transition to Open Core Engine" names the private commercial plan in plain text: *"Based on the new SaaS strategy, this repository will act as the public core engine for the `vibe-cading-platform`."* This is exactly the confidential business strategy that was purged from `docs/`, surviving in a tracked file that ships public. | `TODO.md:128-130` | admin |
| 2 | **blocker** | Private-plugin/strategy leakage | `todo.md` (the parking-lot file) re-describes the purged private internals it claims to have removed: names `docs/business-strategy.md` *(confidential commercial/SaaS plan)*, `docs/archive/mcp-integration-plan.md` *(private `vibe-cading-platform` SaaS internals — Docker sandbox, FastAPI SSE transport)*, and `docs/knowledge_base/mcp_architecture_rules.md` *(named private-repo boundaries)*. The cleanup note leaks the very internals it purged. Also leaks an off-clone backup path `/tmp/vibe-cading-prepurge-backup.git`. | `todo.md:17` | admin |
| 3 | should-fix | Private-plugin leakage | Contributor docs name the private platform's MCP consumer: *"Downstream LLM code-gen tooling (e.g. the platform's `query_engine_api` MCP) consumes it…"*. Reveals the existence/shape of the private platform to every public contributor. Reword generically (e.g. "downstream code-gen tooling"). | `CONTRIBUTING.md:173` | admin |
| 4 | should-fix | Private-plugin leakage | CI workflow comment names the private platform: *"The artifact is a tracked file… that the platform's MCP `query_engine_api` tool consumes."* Same leak as #3 in a tracked workflow. The same comment block (line 8) also points to `.agents/plans/engine-api-json.md`, a git-ignored path absent on a fresh clone (dangling pointer). | `.github/workflows/engine-api.yml:4-5,8` | admin |
| 5 | should-fix | Repo bloat / filename hygiene | Two case-variant TODO files are tracked as distinct blobs — `TODO.md` (release-blockers, 11 KB) and `todo.md` (session backlog, 7 KB). On case-insensitive filesystems (macOS/Windows default) they collide on checkout, corrupting the working tree for most contributors. Consolidate to one canonical filename. | `TODO.md`, `todo.md` (both tracked, differ only in case) | admin |
| 6 | should-fix | Repo bloat / stray artifacts | `TODO_ARCHIVE.md` is a historical completed-task archive (flagged historically) and its line 23 references *"the separate private platform worker"* — both bloat and a (mild) private-platform reference. Candidate for deletion or scrub during TODO consolidation. | `TODO_ARCHIVE.md:23` | admin |
| 7 | nice-to-have | Top-level OSS hygiene | No `SECURITY.md` and no `CODE_OF_CONDUCT.md`. Not strict blockers (LICENSE, README, CONTRIBUTING all present), but both are standard for a public repo: `SECURITY.md` gives a private vuln-disclosure channel, `CODE_OF_CONDUCT.md` is expected by GitHub's community-standards checker. Classify-only per brief; recommend adding before or shortly after the flip. | (absent) `.github/SECURITY.md`, `CODE_OF_CONDUCT.md` | admin |
| 8 | nice-to-have | Top-level OSS hygiene | No CI status badge in `README.md`. Already tracked in `todo.md:15` as a post-publication item ("add a CI status badge once first post-publication green-build lands"). Cosmetic. | `README.md:1-13` | developer |

## What was checked and is clean (negative space)

- **Private-plugin `core-agents` leakage** — zero matches for `core-agents` in any tracked file. The `marketplace`/`plugin` hits are benign (LICENSE-FAQ generic "third-party plugin/package", `vibe/INSTRUCTIONS.md` generic "plugin equivalent", README VS-Code-marketplace extension links).
- **Provider-agnosticism of `vibe/`** — every `Claude`/`CLAUDE.md`/`~/.claude/`/`init-claude-runtime.sh` reference inside `vibe/INSTRUCTIONS.md`, `vibe/agents/`, `vibe/commands/` is an *explicitly-labeled* host example ("e.g. `CLAUDE.md` for Claude Code", "for Claude Code: …") — compliant with the Provider-neutral rule. No unlabeled host-specific references in the neutral tree.
- **Personal / private info** — no personal email addresses (only `noreply`/`example.com` placeholders), no `marcus`/`madMarcus`/personal usernames, no `/home/<personal>`/`/Users/` absolute paths in tracked files. `signatures/version1/cla.json` contains only the public GitHub username `fa-mc` + numeric GitHub ID (expected owner, public data — not private). The owner `fa-mc` in repo URLs is expected.
- **Devcontainer portability** — `.devcontainer/devcontainer.json` uses `${localEnv:HOME}` interpolation and `remoteUser: "vscode"` (no hardcoded personal username/UID/path); the UID-1000 dual-IDE work is parameterized via build args. OSS-portable.
- **Secrets** — `.env` is git-ignored and not tracked (only `.env.example`, which ships placeholder `GH_TOKEN=""`). Zero matches for live token/key patterns (`ghp_`, `github_pat_`, `sk-…`, `AKIA…`, PEM private keys, `AIza…`) in tracked files.
- **License hygiene** — `tools/check_license_headers.py` → "All Python files have the AGPLv3 license header" (exit 0); covers `vibe_cading/`, `parts/` (3 py), `tools/`, `experiments/` (10 py). `tools/check_no_main_blocks.py` → OK (exit 0). LICENSE (AGPLv3) + LICENSE-FAQ.md present. `flake8` → exit 0.
- **Top-level OSS hygiene (links)** — all README internal links resolve; all CONTRIBUTING internal links resolve; AGENTS.md/CLAUDE.md links resolve; `docs/agentic-workflow.md`'s `../vibe/templates/_template_design.md` resolves correctly from `docs/` (the file exists at `vibe/templates/_template_design.md`).
- **Repo bloat / stray binaries** — no tracked `.stl`/`.step`/`.stp` or `output/`/`build/`/`dist/` files. Largest tracked files are all legitimate (`engine_api.json` 178 KB generated index, visual-contract SVGs under `.agents/plans/`, source/docs). `.gitignore` correctly excludes `tmp/`, `output/`, `.env`, `print_profiles_user.json`, build outputs, and the per-clone `.claude/` tree (except tracked `settings.json`), while intentionally tracking `.agents/plans/*.svg` visual contracts.
- **CI health** — three workflows (`ci.yml`, `cla.yml`, `engine-api.yml`). Latest `main` HEAD (`19812d3`) `ci` run = **success**; recent `ci` / `engine-api` / `CLA Assistant` runs all green (`gh run list --repo fa-mc/vibe-cading --branch main`).

## Recommended sequencing (for PM)

Blockers #1, #2 and should-fixes #3–#6 are all instruction/doc-graph edits owned by **admin** and can land in a single "OSS-strategy-scrub" PR: scrub the platform/SaaS strings from `TODO.md`/`CONTRIBUTING.md`/`engine-api.yml`, fold `todo.md` into `TODO.md` (resolving the case collision), and delete/scrub `TODO_ARCHIVE.md`. Note for the human: these TODO/strategy strings exist only in the *working tree* of currently-tracked files — a full git-history scrub of these specific files was out of audit scope and the human should decide whether history rewrite is warranted (the docs purge already rewrote history per `todo.md:17`; these TODO files were not part of that pass).

## Scrub implementation (2026-06-05)

**Spawned by:** PM (Admin persona). **Scope:** working-tree edits only — no git-history changes, no force-push (hard constraint honoured; the history rewrite remains a separate human-run step).

- **Branch:** `oss-strategy-scrub` (off `main`; confirmed no pre-existing PR via `gh pr list --head`).
- **Commit:** `bf43f6c` — *"docs: scrub private-strategy leakage + consolidate TODO files (OSS pre-flip)"* (Co-Authored-By footer present).
- **PR:** [#28](https://github.com/fa-mc/vibe-cading/pull/28) — OPEN, base `main`, head `oss-strategy-scrub`. As-shipped file list verified on GitHub: exactly the 5 changed files (3 modified, 2 deleted); the git-ignored `.agents/plans/` audit artifact correctly excluded from the diff.

### Findings fixed (how)

| # | File | Fix |
|---|------|-----|
| 1 | `TODO.md:128-130` | Removed the "Transition to Open Core Engine" stub entirely (header + the single leaky sentence naming the SaaS strategy + `vibe-cading-platform`). |
| 2 | `todo.md:17` | Reworded the docs-purge note to record the *fact* of the purge ("non-publishable internal docs — a confidential commercial plan and private downstream design notes — removed from working tree + history; off-clone pre-purge mirror retained by maintainer for one transition window") without naming `business-strategy.md` / `mcp-integration-plan.md` / `mcp_architecture_rules.md`, the SaaS internals, or the `/tmp/...prepurge-backup.git` path. Migrated into `TODO.md` as part of #5. |
| 3 | `CONTRIBUTING.md:173` | "Downstream LLM code-gen tooling (e.g. the platform's `query_engine_api` MCP)" → "Downstream LLM code-gen tooling" (no named private consumer). |
| 4 | `.github/workflows/engine-api.yml:4-5,8` | Reworded the platform-MCP comment generically; repointed the dangling git-ignored `.agents/plans/engine-api-json.md` pointer to tracked `CONTRIBUTING.md` §"Engine API Artifact" + `tools/engine_api/extractor.py`. |
| 5 | `TODO.md` vs `todo.md` | **Consolidation decision:** canonical = **`TODO.md`** (uppercase — matches the CLAUDE.md TODO direct-push carve-out reference). Migrated `todo.md`'s three still-relevant sections (Pre-OSS publication checklist, Deferred features, Parked refactors) into `TODO.md` under a new "Session backlog / parking lot" section with `###` sub-headings, sanitized per #2; `git rm`'d the lowercase `todo.md`. All genuine backlog content preserved; only leaky strings dropped. Resolves the case-insensitive-filesystem collision. |
| 6 | `TODO_ARCHIVE.md:23` | **Keep-or-delete decision: DELETED.** It is a self-contained flat list of completed `[x]` tasks (git history already preserves the completion record), has zero inbound tracked references, and carried the "separate private platform worker" reference on line 23. Deletion resolves both the bloat flag and the leak in one move — cleaner than scrubbing a no-forward-value archive. |

### Verification (run against staged blobs before commit)

Leak grep — `git grep --cached -nE 'vibe-cading-platform|SaaS strategy|query_engine_api|business-strategy|mcp-integration-plan|mcp_architecture_rules|prepurge-backup|private platform' -- ':!.agents/*'` → **no matches** (exit 1). A follow-up case-insensitive `platform` scan over all tracked files surfaced only benign hits (cross-platform / across-platforms / host-platform's-subagent-mechanism / host-platform-specific) — none reference the private platform.

Case-collision — `git ls-files | grep -iE '(^|/)todo'` → only `TODO.md`.

Lint gates — `flake8` exit 0; `tools/check_license_headers.py` "All Python files have the AGPLv3 license header"; `tools/check_no_main_blocks.py` OK. (Docs/CI-comment changes only; no `.py` touched.)

### CI status

On PR head `bf43f6c`: `engine-api` = **success**, `CLA Assistant` = **success**, `ci` = **in_progress** at time of return (confirmed via `gh run list --branch oss-strategy-scrub`; `gh pr checks` 403s per project memory). Merge remains the human's call after `ci` completes.
