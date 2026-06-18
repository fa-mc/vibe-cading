# Requirements: `vibe_cading.mcp` subpackage — engine's MCP (stdio) interface
<!-- Filename: 2026-06-18-mcp-subpackage_req.md  (tracked in git under docs/design_plans/) -->

## Meta
- **Initiator role**: @admin (orchestrator), on behalf of RFC #41
- **Date**: 2026-06-18
- **Domain integrity gate**: NO — tooling/infra task. It wraps existing, already-validated contracts (`engine_api.json`, `print_profiles.json`, `lego/constants.py`); it defines no new CAD geometry or domain data/model contract. (A Designer sanity-check of the `get_design_context` curation is welcome but is not a gate.)

---

## Problem Statement
The engine is the parametric-CAD generation library but has no native AI interface. RFC #41 proposes an MCP server, co-located in this repo as `vibe_cading/mcp/`, exposing the engine's deterministic introspection tools (plus a local compile/preview) over MCP **stdio**, so any MCP client (Claude Desktop, Cursor, arbitrary clients) can drive the engine directly at its public debut. Co-location keeps the tool surface byte-synchronized with class signatures the same way `engine_api.json` already is — a separate repo would skew the moment a signature changes.

## User Story / Motivation
As an MCP-client user (or an AI agent acting through one), I need a keyless, local, deterministic interface to query the engine's class catalog, fetch design context, and compile/preview a model on my own machine, so that I can drive parametric CAD generation without learning the codebase internals — and as a maintainer, I need that interface to never leak its dependency or import weight onto library-only consumers.

## Decisions already locked (RFC #41 — maintainer + consumer accepted)
Ratified on the GitHub issue (see Human Confirmation Checkpoint for links):
- **D1 — Placement:** accept co-location as the `vibe_cading.mcp` subpackage. Separate-repo fallback is dead unless the launch window genuinely can't absorb in-repo work.
- **D2 — Dependency:** `mcp` is an **optional `[mcp]` extra from day one** (NOT mandatory at v1), pinned `mcp>=1,<2`. *(Correction to the RFC's "lightweight SDK" premise: `mcp` 1.28.0's core `requires_dist` carries a full ASGI stack — `starlette`, `uvicorn`, `sse-starlette`, `python-multipart`, `httpx`, `pyjwt[crypto]`, `pydantic-settings` — ungated, so a stdio-only consumer still resolves it. Verified twice against live PyPI.)*
- **D3 — Build engine-side**, with a two-layer import-isolation CI guard as a **blocking** deliverable.

## Functional Requirements
<!-- Numbered, unambiguous, testable. MUST / MUST NOT. -->
1. **R1 — Runnable stdio server.** The repo MUST ship a `vibe_cading/mcp/` subpackage runnable as `python -m vibe_cading.mcp`, serving MCP over **stdio** (JSON-RPC on stdin/stdout). It MUST NOT open a network listener, port, or HTTP endpoint, and MUST require no API keys.
2. **R2 — Deterministic introspection tools.** The server MUST expose `list_engine_classes` (class index) and `query_engine_class` (per-class record), reading the **committed `vibe_cading/engine_api.json`**. It MUST NOT re-walk the AST at request time.
3. **R3 — `get_design_context` as a doc-pointer aggregate.** The server MUST expose `get_design_context` as a **versioned** aggregate of: (a) the resolved `ToleranceProfile` via `print_settings.get_profile()` (live), (b) a **curated allowlist** of constants *by name* (not a reflection sweep), and (c) doc **pointers** (path + anchor) — NOT inlined doc prose. It MUST NOT become a second, un-gated copy of the docs.
4. **R4 — Local compile/preview tool.** The server MUST expose a compile/preview tool that runs CadQuery on the user's own machine, routed through `tools/model_loader` (`instantiate` / `parse_params`) and `tools/preview.export_previews(..., quiet=True)`. It MUST NOT reimplement param-parsing, `sys.path` handling, or solid-resolution. Its result MUST default to a **file path**; an opt-in inline-SVG-text mode MAY be offered.
5. **R5 — `mcp` is an optional extra.** `pyproject.toml` MUST declare `mcp` under `[project.optional-dependencies]` as an `mcp` extra pinned `mcp>=1,<2`, and MUST NOT add `mcp` to the mandatory `dependencies`. The README quickstart MUST document `pip install -e ".[mcp]"` as the install for the AI interface.
6. **R6 — Graceful missing-extra UX.** `python -m vibe_cading.mcp` MUST detect a missing `mcp` import (`try/except ImportError`) and print a one-line actionable hint naming `pip install -e ".[mcp]"`, exiting non-zero — never a raw traceback.
7. **R7 — Import-isolation invariant (blocking).** `vibe_cading/mcp/` MUST NOT be imported by `vibe_cading/__init__.py` or any class module under `vibe_cading/**` or `parts/**`. A new `vibe_cading/tools/check_mcp_import_isolation.py` MUST enforce it in CI with **two layers**: (A) a static AST guard (no `vibe_cading.mcp` import in any class module; carve out `vibe_cading/mcp/` itself and `vibe_cading/tools/`), with a grep belt-and-braces twin; and (B) a live assertion that, in a clean subprocess, `import vibe_cading` leaves neither `mcp` nor any `vibe_cading.mcp.*` in `sys.modules`.
8. **R8 — Versioned tool contract.** The MCP tool contract (tool names, argument schemas, result shapes) MUST carry its own version field, separate from `engine_api.json`'s `schema_version`, with a documented additive-vs-breaking evolution policy.
9. **R9 — Structured error semantics.** The MCP layer MUST translate `model_loader`'s typed exceptions (`ModuleNotFoundError` / `AttributeError` / `ValueError`) and constructor/CadQuery failures into structured MCP tool errors (`isError` content). A Python traceback MUST NOT escape as a transport-level crash.
10. **R10 — Licensing & AGPL posture.** Every non-empty new `.py` under `vibe_cading/mcp/` MUST carry the AGPLv3 header. The design MUST document that the stdio transport is intentionally **not** an AGPL §13 network-interaction surface (no network listener), and flag that any future HTTP/SSE transport WOULD engage §13.

## Non-Functional Constraints
- **Resolve-graph isolation:** a plain `pip install vibe_cading` (or `pip install -e .` without the extra) MUST NOT resolve `mcp` or its ASGI stack. This is the core reason D2 landed as an extra.
- **Runtime-graph isolation:** enforced by R7. Importing the library surface or any class module MUST NOT import `mcp`.
- **Determinism:** introspection reads (R2) MUST be deterministic — same `engine_api.json` → same output.
- **No asserted wall-time/build-time budget** at any entry point in this task (so no Entry-Point Full-Execution Probe is owed). If a later change asserts one (e.g. a `--help` runtime budget), ground it per INSTRUCTIONS.md §4.
- **Reproducibility:** the import-isolation Layer B check MUST be host-independent (pure import-graph assertion; no fonts/OCCT/glyph dependence).

## Known Domain Constraints
- `engine_api.json` is the contract artifact; `gen_engine_api.py --check` keeps it fresh in CI. Introspection tools read it; they do not regenerate it.
- `tools/model_loader.py` is **stdlib-only at import**; CadQuery is pulled in only at `instantiate()` time. The compile path MUST preserve this lazy-import property (don't import cadquery at module load of the MCP package).
- Existing CI structural-guard idiom to mirror: `tools/check_no_main_blocks.py` (AST walker + exclude list) + its grep twin + the `ocp_vscode` import allowlist in `.github/workflows/ci.yml`.
- A `__main__.py` does not use an `if __name__ == "__main__":` guard, so it does not trip `check_no_main_blocks.py` — confirmed in the TL assessment.
- `pyproject.toml` currently has exactly one runtime dependency (`cadquery`) and **no** `[project.optional-dependencies]` table — adding the extra is greenfield.

## Out of Scope
- No LLM agent loop, asset/template library, billing, or provider API keys — those belong in a consuming application, not the open engine.
- No HTTP/SSE/WebSocket/network transport. stdio only.
- No PyPI publish of the package or the extra in this task (clone-only audience now; PyPI is the later "extract extra was already done" moment).
- The consuming application's own design / integration (separate, on the consumer's side, gated on their AGPL firewall clearance — explicitly non-blocking to this brief per the consumer).
- No new CAD geometry, model classes, or `build.toml` entries.
- No `[mcp]`-gating of the SDK's own transport deps (upstream `mcp` doesn't gate them; out of our control).

## Open Questions
<!-- Resolved in the TL-requester design dialog (Step 3) before sign-off. -->
- [ ] OQ1 — `get_design_context` payload schema: exact field shape, the curated constant **allowlist** contents, and which doc paths/anchors are surfaced (R3).
- [ ] OQ2 — Compile/preview tool arg schema (dotted class path, params encoding, view selection) and result envelope (path default vs opt-in inline); temp-file location + cleanup policy (R4).
- [ ] OQ3 — Where the tool-contract version lives and whether it gets a snapshot/freshness test (R8).
- [ ] OQ4 — Final module layout (`__init__` / `__main__` / `server` / `tools` / `context`) and exactly which files may import the `mcp` SDK (the isolation-guard carve-out set) (R1, R7).
- [ ] OQ5 — Error-envelope mapping table: which exception → which MCP error code + message shape (R9).
- [ ] OQ6 — CI wiring: which job runs Layer A (lint, stdlib-only) vs Layer B (which `import vibe_cading` variant runs pre-build; class-module variant post-build where CadQuery is installed); where the compile-handler tests run (R7, R11).
- [ ] OQ7 — `query_engine_class` lookup key: fqn vs short name, fuzzy/exact match, and any list-filter params for `list_engine_classes` (R2).

## Testing requirement (feeds the design Tests table)
- **R11 — Two-tier test strategy.** The design MUST specify: (a) direct handler unit tests (pure-Python, no SDK, no subprocess) covering each tool; (b) one stdio **smoke test** that spawns `python -m vibe_cading.mcp` and round-trips an `initialize` + one `tools/call`; (c) the import-isolation guard tests (Layer A + Layer B). The compile-handler tests need CadQuery and run in the post-build CI stage.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human — **ratified on RFC #41** by the maintainer + consumer:
  - Recommendation posted: https://github.com/fa-mc/vibe-cading/issues/41#issuecomment-4735882670
  - Acceptance ("Accept — including the Decision 2 modification … Go ahead and draft the design brief.", filed against engine SHA `8201564`): RFC #41 comment dated 2026-06-18.
<!-- The GitHub acceptance is the human confirmation for this requirements set; the design brief (Steps 3–3.5) proceeds, stopping at the Step 4 human approval gate before any implementation. -->
