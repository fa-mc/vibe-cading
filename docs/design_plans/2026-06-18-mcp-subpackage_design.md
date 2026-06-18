# Design: `vibe_cading.mcp` subpackage — engine's MCP (stdio) interface
<!-- Filename: 2026-06-18-mcp-subpackage_design.md  (tracked in git under docs/design_plans/) -->

## Meta
- **Requirements ref**: [docs/design_plans/2026-06-18-mcp-subpackage_req.md](2026-06-18-mcp-subpackage_req.md)
- **Requester role**: @admin (orchestrator, on behalf of RFC #41)
- **TL assessment backbone**: [docs/design_plans/2026-06-17-mcp-subpackage_rfc-tl-assessment.md](2026-06-17-mcp-subpackage_rfc-tl-assessment.md)
- **Date**: 2026-06-18
- **Dialog rounds**: 6 (Challenges A–F, all forcing substantive revision — see Design Dialog Log)
- **Domain integrity gate**: NO (tooling/infra; wraps already-validated contracts). No domain co-sign owed.

---

## Objective
Ship a `vibe_cading/mcp/` subpackage runnable as `python -m vibe_cading.mcp` that serves four deterministic engine tools (`list_engine_classes`, `query_engine_class`, `get_design_context`, `compile_model`) over MCP **stdio**, as a thin adapter layer over existing loaders, gated behind an optional `[mcp]` extra and a blocking two-layer import-isolation CI guard so library-only consumers never pay its dependency or import weight.

## Architecture / Approach

### Approach chosen

The MCP layer is a **thin adapter** over four already-validated, already-CI-fresh seams. It introduces **zero new domain logic** and **zero re-derivation** of param-parsing, `sys.path` handling, solid resolution, preview export, or AST walking. Its entire architectural job is (1) translate MCP tool calls into calls on existing functions, (2) translate their results/exceptions into the MCP wire shape, and (3) stay surgically isolated from the library import graph.

#### Module layout under `vibe_cading/mcp/` (resolves OQ4)

```
vibe_cading/mcp/
  __init__.py     # Package marker ONLY. Docstring + AGPL header. MUST NOT import
                  #   server/tools/context/the SDK (preserves isolation; importing
                  #   the package name stays mcp-SDK-free and CadQuery-free).
  __main__.py     # `python -m vibe_cading.mcp` entry. Owns the try/except ImportError
                  #   hint (R6) and the stdio-transport bootstrap. MAY import the mcp SDK.
  server.py       # Builds the MCP Server, registers the 4 tools, adapts SDK-free
                  #   handlers (tools.py) into registered MCP tools, maps results +
                  #   the structured error envelope. MAY import the mcp SDK.
  tools.py        # The 4 thin handler functions + their JSON-schema + result/error
                  #   builders. Pure adapters over model_loader / preview /
                  #   engine_api.json / context.py. MUST NOT import the mcp SDK
                  #   (keeps handlers unit-testable without the SDK — Challenge E).
  context.py      # get_design_context aggregation: live ToleranceProfile + curated
                  #   constant allowlist + doc pointers. MUST NOT import the mcp SDK.
  contract.py     # TOOL_CONTRACT_VERSION + the additive/breaking policy docstring (R8).
                  #   Tiny; MUST NOT import the mcp SDK. (See "Tool-contract versioning".)
```

**The `mcp` SDK isolation-guard carve-out set is exactly `{__main__.py, server.py}`.** Every other file in the package — and the package marker itself — is SDK-free. This makes Layer-A enforcement trivial (the guard forbids `import mcp` / `from mcp …` everywhere under `vibe_cading/**` and `parts/**` *except* the whole `vibe_cading/mcp/` subtree and `vibe_cading/tools/`; the *internal* SDK-free discipline of `tools.py`/`context.py`/`contract.py` is enforced by their unit tests importing them with `mcp` absent — see Challenge F's env matrix — not by the cross-package guard).

> Grounding: `vibe_cading/__init__.py:20-24` already "intentionally does NOT re-export anything from sub-packages", and `:35` only touches `importlib.metadata`. So `import vibe_cading` is already SDK-free and CadQuery-free; this layout *preserves* that property rather than creating it.

#### Reuse seams (R4 / R2 / R3) — re-deriving any of these is a review-blocking duplication finding

| Tool | Seam (exact symbol) | File:line grounded this session |
|------|--------------------|----------------------------------|
| `compile_model` (compile) | `tools.model_loader.instantiate(dotted, params)` + `tools.model_loader.parse_params(raw)` | `model_loader.py:186`, `:109` |
| `compile_model` (preview) | `tools.preview.export_previews(model_path, out_dir, params, views, quiet=True)` | `preview.py:222`, `quiet` semantics `:244-249`, returns `list[Path]` `:298` |
| `list_engine_classes` / `query_engine_class` | read committed `vibe_cading/engine_api.json` (`schema_version` + `classes[]`) | live shape confirmed: top keys `["schema_version","classes"]`, `schema_version="1.1"`, `classes` is a 70-element list |
| `get_design_context` (tolerance) | `vibe_cading.print_settings.get_profile(name)` → `ToleranceProfile` | `print_settings.py:611`; `ToleranceProfile` `:264-277`, `FitGrade` `:241-261` |

**The MUST-NOTs (R2/R4) restated as enforceable rules:**
- `list_engine_classes`/`query_engine_class` MUST NOT re-walk the AST at request time — they read the committed JSON. (`gen_engine_api.py --check` already keeps the JSON fresh in CI; the MCP tools ride that gate.)
- `compile_model` MUST NOT reimplement param-parsing, `sys.path` handling, or solid resolution — those are `model_loader`'s entire reason to exist (`model_loader.py:16-23` enumerates the five inline call sites it already de-duplicated; the MCP server is the sixth caller, not a re-implementer).
- `compile_model` MUST NOT import `cadquery` at MCP-package module-load — it inherits `model_loader`'s lazy-import property (`model_loader.py:73-79`: stdlib-only at import; CadQuery pulled in only at `instantiate()`). `tools.py` therefore imports `model_loader`/`preview` lazily *inside* the handler, never at module top, so importing `vibe_cading.mcp.tools` for a unit test does not drag CadQuery.

#### `get_design_context` design (R3 / OQ1)

A **versioned, explicitly-curated, doc-*pointer*-not-doc-*content* aggregate** with its own `schema_version` (independent of both `engine_api.json` and the tool-contract version). It never inlines doc prose, so it never needs a docs-freshness gate. Payload schema (the wire shape `context.py` returns):

```jsonc
{
  "schema_version": "1.0",            // get_design_context payload schema (own line; see "two version fields")
  "tolerance_profile": {              // (a) LIVE via print_settings.get_profile()
    "name": "fdm_standard",
    "free":  {"radial": 0.15, "axial": 0.10, "slot": 0.0},
    "slip":  {"radial": 0.05, "axial": 0.10, "slot": 0.10},
    "press": {"radial": 0.04, "axial": 0.10, "slot": 0.0}
  },
  "constants": {                       // (b) CURATED ALLOWLIST by name (NOT a reflection sweep)
    "STUD_PITCH": 8.0, "PLATE_HEIGHT": 3.2, "BRICK_HEIGHT": 9.6,
    "STUD_DIAMETER": 4.8, "STUD_HEIGHT": 1.8,
    "PIN_HOLE_DIAMETER": 4.8, "HOLE_SPACING": 8.0, "EDGE_TO_CENTRE": 4.0,
    "BEAM_THICKNESS": 7.8, "BEAM_WIDTH": 7.8, "BEAM_END_RADIUS": 3.9,
    "AXLE_TIP_TO_TIP": 4.78, "AXLE_LENGTH_PER_STUD": 8.0,
    "AXLE_HOLE_TIP_TO_TIP": 4.80, "AXLE_HOLE_ARM_WIDTH": 1.83,
    "BLOCK_PLAY": 0.2, "BLOCK_WALL": 1.5, "BLOCK_ROOF": 1.0, "CLUTCH_TUBE_OD": 6.51
  },
  "doc_pointers": [                    // (c) POINTERS (path + anchor), NOT prose
    {"topic": "Lego Technic dimensions", "path": "docs/lego-technic.md", "anchor": null},
    {"topic": "Tuning tolerances",       "path": "docs/lego-technic.md", "anchor": "#tuning-tolerances"},
    {"topic": "Print tolerances",        "path": "docs/print-tolerances.md", "anchor": null},
    {"topic": "Screw conventions",       "path": "docs/screws.md", "anchor": null}
  ]
}
```

**The curated constant allowlist** (the `CONTEXT_CONSTANTS` tuple lives in `context.py`) is the load-bearing subset I selected by opening `vibe_cading/lego/constants.py` this session — the grid/stud, pin-hole, beam, axle, axle-hole, and System-block nominals that a model author actually needs to place geometry on the 8 mm grid. **Deliberately excluded:** `CORNER_RADIUS` / `LEAD_IN` (internal cosmetic defaults), `AXLE_ARM_WIDTH` / `AXLE_ARM_PROTRUSION` (cross-profile *solid* internals rarely needed by a consumer authoring on the grid). The allowlist surfaces real-Lego **nominals**; it never surfaces printer-tuned fits (those come live through `tolerance_profile`, matching how `constants.py:37-43`, `:86-89`, `:106-109` route fits through the profile, not the constant).

**Anti-drift guard (resolves Challenge A — no reflection sweep):** a unit test (`tests/mcp/test_context.py`) asserts **every** name in `context.CONTEXT_CONSTANTS` still resolves as a module-level attribute of `vibe_cading.lego.constants` (`getattr(constants, name)` does not raise) *and* that each resolved value is a `float`. If a constant is renamed/removed in `constants.py`, the allowlist test goes red in the same PR — the curation cannot silently rot, and no brittle reflection-over-the-module sweep is needed. The reverse direction (a *new* constant added to `constants.py`) is intentionally NOT auto-surfaced: curation is a deliberate act, and the test failing on *removal* is the only direction that produces a *lying* context payload. Adding a constant to the allowlist is an **additive** `schema_version` event (see versioning).

#### Compile/preview tool (R4 / OQ2)

`compile_model` arg schema (full wire shape in Data & Interface Contracts):
- `class_path: str` (required) — dotted `module.ClassName`, passed verbatim to `model_loader.instantiate`.
- `params: object` (optional, default `{}`) — JSON object of constructor kwargs. **Encoding decision:** accept a native JSON object (`{"holes": 5}`), then normalize to `model_loader`'s `list["k=v"]` form via a tiny shim so we reuse `parse_params`' exact int→float→bool→str cast ladder (`model_loader.py:130-143`) rather than re-deriving casting. (A JSON object is the idiomatic MCP arg; the shim keeps the *cast contract* single-sourced.)
- `outputs: array<string>` (optional, default `["step"]`) — any of `"step"`, `"stl"`, `"svg"`. `svg` routes through `export_previews`; `step`/`stl` route through `cq.exporters.export` on the solid obtained via `model_loader.resolve_solid(instance)` (`model_loader.py:196`) — **not** a bare `instance.solid`, to honor the R4 *no-solid-resolution re-derivation* MUST-NOT (the only `cq.exporters` call we add, and only for the binary formats `export_previews` does not produce). **Recorded decision (Step-3.5 review round):** `compile_model` threads **no** `ToleranceProfile` — tolerance is whatever the model class constructor resolves on its own (via `get_profile`/`.env`); the MCP layer deliberately does not inject a profile, so this omission is intentional, not an oversight to re-litigate at Phase B.
- `views: array<string>` (optional, default `["iso_ne"]`, used only when `"svg" in outputs`) — forwarded verbatim to `export_previews(views=...)`, which already validates names and raises `ValueError` on unknown (`preview.py:260-265`).
- `return_inline: bool` (optional, default `false`) — opt-in inline SVG text (see Challenge B size guard).

**Result envelope (file-path default; resolves Challenge B):**
```jsonc
{
  "tool_contract_version": "1.0",
  "artifacts": [
    {"format": "step", "path": "/tmp/vibe_cading_mcp/<uuid>/Foo.step"},
    {"format": "svg",  "view": "iso_ne", "path": "/tmp/vibe_cading_mcp/<uuid>/Foo_iso_ne.svg",
     "inline": "<svg …>…</svg>"}   // "inline" present ONLY when return_inline=true AND under size cap
  ]
}
```

**Temp-file location + cleanup policy:** artifacts are written under `tempfile.mkdtemp(prefix="vibe_cading_mcp_")` (the OS temp root, never the repo tree — keeps the working copy clean per workspace-hygiene rules). **Cleanup is deliberately deferred to the OS temp reaper, NOT eager-deleted**, because the file-path return contract requires the file to still exist when the (local) client opens it — eager cleanup after returning the path would race the client and hand back a dangling path. The directory name is namespaced (`vibe_cading_mcp_*`) so it is greppable/sweepable. This is documented in the `compile_model` docstring with the why (path-return ⇒ file must outlive the call).

#### Error envelope (R9 / OQ5) — concrete mapping table

Every handler runs inside one `try/except` in `server.py` that converts a typed exception into an MCP tool error result (`isError: true` with a structured text content block) — **never** a transport-level crash / escaping traceback. The error content is a single JSON object: `{"error_code": <str>, "message": <str>, "detail": <str|null>}`.

**Serialization (resolves Step-3.5 review condition):** an MCP `CallToolResult` carries a `content` array of typed blocks plus an `isError` flag — **not** a bare dict. Both success and error results therefore cross the wire as a single text block wrapping the JSON: `content=[TextContent(type="text", text=json.dumps(payload))]`, with `isError=True` set on the error path. The dict shapes shown throughout this design (result envelopes and the error object above) are the JSON *inside* that one text block. This single serialization is owned by `server.py`'s adapter (the only place that touches SDK content types); `tools.py` handlers return plain dicts.

| Raised by | Exception | `error_code` | `message` shape | `detail` |
|-----------|-----------|--------------|-----------------|----------|
| `load_class` bad dotted path | `ValueError` (no `.`) | `bad_class_path` | "class_path must be 'module.ClassName', got …" | the offending string |
| `load_class` import fail | `ModuleNotFoundError` | `module_not_found` | "Could not import module for '<fqn>'" | `str(exc)` |
| `load_class` no such class | `AttributeError` | `class_not_found` | "Module '<mod>' has no class '<name>'" | the fqn |
| `parse_params` / param shim | `ValueError` (bad `k=v`) | `bad_params` | "Invalid params: …" | the offending entry |
| Constructor rejects kwargs | `TypeError` (unexpected/missing kwarg) | `bad_params` | "Constructor rejected params: …" | `str(exc)` |
| Constructor/geometry raises | `ValueError` from class body / `assert` | `model_error` | "Model raised: …" | `str(exc)` |
| CadQuery/OCCT boolean failure | any `Exception` from `instantiate`/export | `compile_failed` | "CadQuery failed during compile" | `type(exc).__name__: str(exc)` |
| Unknown view name | `ValueError` from `export_previews` | `bad_view` | "Unknown view(s): …" | the offending names |
| `query_engine_class` miss | (handled, not raised — see contract) | `class_not_found` | "No class matching '<key>'" | the key |

> `instantiate` "lets constructor exceptions propagate unchanged" (`model_loader.py:189-191`); the MCP layer is where they become structured errors. The `load_class` typed-exception trio (`ValueError`/`ModuleNotFoundError`/`AttributeError`) is grounded at `model_loader.py:166-182`. The broad `compile_failed` catch-all is last so a novel OCCT failure still returns a clean tool error rather than crashing the stdio loop.

#### Tool-contract versioning (R8 / OQ3) — resolves Challenge D

`TOOL_CONTRACT_VERSION = "1.0"` lives in `vibe_cading/mcp/contract.py` (single source). It is **echoed in every tool result** (`tool_contract_version` field) and exposed by a trivial reflective tool surface (it is part of `get_design_context`'s sibling — actually carried on each result envelope, so a client reads it from any call). It is **separate** from `engine_api.json`'s `schema_version` (which versions *class records*, not *tool signatures*).

**Additive-vs-breaking policy** (mirrors the engine_api additive discipline at `extractor.py:62-64`):
- **Additive ⇒ bump minor** (`1.0`→`1.1`): add a new optional arg with a default; add a new tool; add a new field to a result envelope; add a name to the constant allowlist. Existing clients keep working.
  - *Concrete additive example:* adding `return_inline: bool = false` to `compile_model` — old clients that never send it get the old file-path-only behaviour.
- **Breaking ⇒ bump major** (`1.0`→`2.0`): rename/remove a tool or arg; change an arg's type or required-ness; change a result field's name/type/meaning; change the `query_engine_class` lookup-key semantics.
  - *Concrete breaking example:* renaming `query_engine_class`'s `class_key` arg to `fqn` — a client pinned to `class_key` silently sends an unknown arg and breaks.

**Freshness test (OQ3):** a snapshot test (`tests/mcp/test_tool_contract_snapshot.py`) serializes the registered tool definitions (name + arg JSON-schema + result-shape marker) to a committed JSON fixture and byte-compares, exactly mirroring the `gen_engine_api.py --check` idiom — any signature drift fails CI unless the fixture and `TOOL_CONTRACT_VERSION` are updated in the same PR. This makes the version field *enforced*, not aspirational.

#### Import-isolation guard (R7) — resolves Challenge C

`vibe_cading/tools/check_mcp_import_isolation.py`, modeled directly on `check_no_main_blocks.py` (AST walker `find_violations(roots, exclude)` at `:60`, repo-root resolution `:89`, stdlib-only `:32`) and the `ocp_vscode` allowlist idiom (`ci.yml:62-73`).

**Layer A — static AST guard (primary, stdlib-only, pre-build).** Walk every `*.py` under `vibe_cading/` and `parts/`, *excluding* the whole `vibe_cading/mcp/` subtree and `vibe_cading/tools/`. Parse with `ast`; collect `ast.Import` / `ast.ImportFrom`; fail if any names `mcp` or a module under `vibe_cading.mcp`. AST (not raw grep) so the literal string `"vibe_cading.mcp"` inside a docstring does not false-positive — the exact rationale `check_no_main_blocks.py:32` already cites. Plus a **grep belt-and-braces twin** in `ci.yml` (`grep -rlE '(from|import) (mcp|vibe_cading\.mcp)' vibe_cading/ parts/`, subtract the `vibe_cading/mcp/` and `vibe_cading/tools/` allowlist), mirroring the existing two-step pattern at `ci.yml:47-61`.

**Layer B — live-import assertion (defense-in-depth, catches transitive/dynamic pollution AST cannot see).** In a **clean subprocess** (pristine `sys.modules`):
```
import vibe_cading
leaked = [m for m in sys.modules if m == "mcp" or m.startswith("vibe_cading.mcp")]
sys.exit(1 if leaked else 0)
```
This asserts the *actual property the invariant promises*: after `import vibe_cading`, neither `mcp` nor any `vibe_cading.mcp.*` is in `sys.modules`. It is the cheap, host-independent (pure import-graph) check the requirement's reproducibility constraint demands.

**Challenge-C decision — the class-module Layer-B variant does NOT run as a separate CI step.** The invariant we most care about is **top-level `import vibe_cading` staying `mcp`-free**, and that is cheap (top-level import only touches `importlib.metadata`, `__init__.py:35`). Importing a *representative class module* would pull CadQuery (heavy) for marginal added coverage, because **Layer A's static scan already covers every class module's *source* imports** — the only thing a class-module Layer-B run adds over Layer-A is *transitive* pollution through a class module, and the realistic transitive path (a shared helper that imports `mcp`) is itself a *direct* `import mcp` in some scanned file, which Layer A catches. So: **top-level Layer B (in the lint stage, no CadQuery) + Layer A's static class-module scan is sufficient.** We do not pay the CadQuery import for a class-module Layer-B step. (If a future regression ever proves a transitive leak through a class module that Layer A missed, add the class-module variant *after* Build smoke where CadQuery is already installed — noted as the escalation path, not shipped now.)

**CI wiring (resolves OQ6):**
| Check | CI stage | CadQuery needed? | `mcp` installed? |
|-------|----------|------------------|------------------|
| Layer A (AST) + grep twin | lint stage (alongside `check_no_main_blocks`, ~`ci.yml:47`) | no | no |
| Layer B (top-level `import vibe_cading`) | lint stage | no | **must be absent** (it asserts `mcp` absent) |
| Handler unit tests (non-compile) | existing Pytest step (`ci.yml:74`) | no | no (handlers are SDK-free) |
| `compile_model` handler tests | existing Pytest step (`ci.yml:74`) | **yes** (already installed via `requirements-ci.txt`) | no |
| stdio smoke test | dedicated step/job **after** `pip install -e ".[mcp]"` | yes | **yes** |
| Tool-contract snapshot test | smoke job (needs the SDK to introspect registered tools) | no | yes |

#### Packaging + UX (R5 / R6)

`pyproject.toml` — greenfield `[project.optional-dependencies]` table (none exists today; current `dependencies = ["cadquery"]` at `:36-38` is untouched):
```toml
[project.optional-dependencies]
mcp = ["mcp>=1,<2"]
```
Pin `>=1,<2` because `mcp` v2 is alpha/imminent — an unpinned bump must never break a clone mid-launch, and (the whole point of the extra) a transitive break in the `mcp`→`starlette`/`uvicorn`/`pydantic` tree must never break a plain `pip install vibe_cading`.

**README quickstart line** (added to "Dev Setup", README.md:50, near workspace-init): a one-liner —
> **AI interface (optional):** to drive the engine from an MCP client, install the extra and run the server: `pip install -e ".[mcp]"` then `python -m vibe_cading.mcp`.

**`__main__.py` missing-extra UX (R6):**
```python
try:
    from mcp.server import Server   # (exact import per SDK; the only SDK import path)
except ImportError:
    sys.stderr.write(
        "The MCP interface requires the optional 'mcp' extra.\n"
        "Install it with:  pip install -e \".[mcp]\"\n")
    sys.exit(1)
```
A missing extra prints **one actionable line naming `pip install -e ".[mcp]"`** and exits non-zero — never a raw traceback.

> **SDK-surface caveat (Step-3.5 review condition).** `mcp` is **not installed in this dev container** (confirmed), so the exact SDK symbols — the `from mcp.server import Server` import path shown above, the stdio-transport bootstrap, and the tool-registration API used in `server.py`/`__main__.py` — are pinned against the published `mcp>=1,<2` SDK docs, **not** import-grounded here. The **first Phase-A implementation act is `pip install -e ".[mcp]"` to probe the real SDK API**, then update the `__main__.py`/`server.py` snippets if the published surface differs. Recorded so the developer *verifies* rather than *trusts* the SDK call sites; the rest of the design (handlers, isolation, packaging, contracts) is fully import-grounded and unaffected.

#### AGPL posture (R10)

- Every non-empty new `.py` under `vibe_cading/mcp/` (and the new `vibe_cading/tools/check_mcp_import_isolation.py`) carries the AGPLv3 header verbatim — confirmed shape at `model_loader.py:1-14`, `constants.py:1-14`. `build.py`'s pre-build `check_license_headers.py` already enforces this (`ci.yml:79-80`); the new files fall under its scan. Empty `__init__.py` is exempt, but `vibe_cading/mcp/__init__.py` carries a docstring so it gets the header.
- **The design records:** the stdio transport is intentionally **not** an AGPL §13 network-interaction surface — stdin/stdout is not "interacting … through a computer network", there is no network listener (R1), and the server is single-tenant local-trust. So §13's remote-source-offer obligation is **not** engaged by this task.
- **Future-HTTP flag:** any future HTTP/SSE/WebSocket transport (which the bundled `uvicorn`/`starlette` in the `mcp` dependency tree make trivially reachable) **WOULD** engage §13 and require a Corresponding-Source offer mechanism to remote users. This is recorded so the next contributor does not add an HTTP transport without the licensing call. (Out of scope here — stdio only, per req.)

### Module depth (Deep-Modules Dual-Lens Rule)

Per `vibe/INSTRUCTIONS.md` §Code-Quality "Deep-Modules — Dual-Lens Rule" (re-read this session): each new module is evaluated on **(a) maintainer-locality** (do current internal callers benefit?) and **(b) contributor-locality** (would an external contributor adding a tool/family benefit?). An abstraction earns its keep if it passes *either* lens.

| Module | Behaviour concentrated | Caller leverage / locality | Verdict |
|--------|------------------------|----------------------------|---------|
| `__main__.py` | The stdio bootstrap + the missing-extra `try/except` hint; the single SDK-import entry. | (a) It is the **isolation firewall** — one of exactly two files the guard exempts, making Layer-A trivial. (b) **Cold-start orientation surface** — "where does `python -m vibe_cading.mcp` start?" — an explicit keep-even-if-thin category in the rule. | **Keep** (both lenses) |
| `server.py` | SDK `Server` construction, tool registration, the result/error-envelope adapter, the one `try/except` that produces `isError`. | (a) Concentrates *all* SDK-facing ceremony in one file so `tools.py` stays SDK-free and testable. (b) A contributor adding a tool registers it here against a documented adapter — they touch SDK ceremony in exactly one place. | **Keep** (both lenses) |
| `tools.py` | The 4 handler functions + arg-schema + result/error builders; pure adapters over the loaders. | (a) Handlers are **unit-testable without standing up an MCP session** (the §B4 testability win). (b) **Contributor-extension surface** — adding a tool = write one pure function against the documented loader API; no SDK ceremony to learn. | **Keep** (contributor-locality; the rule's explicit "keep even when current internal callers are few" category) |
| `context.py` | `get_design_context` aggregation: live profile + curated allowlist + doc pointers + the payload `schema_version`. | (a) The only module with non-trivial logic; concentrates the curation so the anti-drift test has one target. (b) A contributor extending the context surface edits one curated tuple + one schema bump, with a test that fails on drift. | **Keep** (both lenses) |
| `contract.py` | `TOOL_CONTRACT_VERSION` + the additive/breaking policy docstring. | (a) **Versioning seam** — an explicit keep-even-if-thin category. Single source for the version echoed on every result + the snapshot test. (b) The documented evolution policy onboards a contributor changing the tool surface. | **Keep** (versioning seam) |
| `check_mcp_import_isolation.py` | Layer A AST walk + Layer B subprocess assertion. | (a) **Security/invariant boundary** (the blocking isolation guard) — explicit keep category. (b) Mirrors the proven `check_no_main_blocks.py` shape a contributor already recognises. | **Keep** (invariant boundary) |

**Explicitly recorded — NO `BaseMcpTool` ABC / per-tool class hierarchy.** It **fails both lenses** for ~4 functions over stable loaders: (a) maintainer — there is no polymorphic dispatch the SDK's own registration doesn't already provide; the deletion test (inline a one-method ABC into 4 free functions) loses nothing. (b) contributor — an external contributor adding a tool benefits more from "write a function in `tools.py`, register it in `server.py`" than from implementing an abstract base. A `Protocol` for "an MCP tool" would be abstraction-for-its-own-sake. If it appears in implementation, it is a review-blocking over-engineering finding.

### Visual contract (CAD tasks)

**N/A — tooling/infra task, no visible geometry.** No model class, no `build.toml` change, no axis/hole/datum change. Per the §Visual-Contract scope carve-outs (instruction/config/tooling tasks are exempt), no SVG is owed or embedded.

### Alternatives rejected
- **`mcp` mandatory at v1** (the RFC's original D2 framing) — rejected; the "lightweight SDK" premise is factually wrong (`mcp` transitively drags a full ASGI stack: `starlette`/`uvicorn`/`sse-starlette`/`httpx`/`pydantic-settings`/`pyjwt`). Ratified as D2: optional `[mcp]` extra from day one.
- **Separate `vibe-cading-mcp` repo** — rejected (D1); strictly worse on coupling and clone-story; co-location rides the same `--check` freshness gate that already protects `engine_api.json`.
- **`get_design_context` returning curated doc *excerpts*** — rejected; an un-gated second copy of the docs with no freshness guard. Doc *pointers* (path+anchor) carry zero prose-drift liability.
- **Re-walking the AST at request time for introspection** — rejected (R2); the committed `engine_api.json` is the contract and is cheaper and already CI-fresh.
- **`BaseMcpTool` ABC** — rejected (see Module depth); fails both lenses for 4 functions.
- **Eager temp-file cleanup** — rejected; races the local client that the file-path return contract requires to open the file. Defer to the OS reaper with a namespaced prefix.

## Data & Interface Contracts

The public MCP wire contract clients pin to. `tool_contract_version` (from `contract.py`, `"1.0"`) is echoed on every result. All four tools return the structured error envelope from §Error-envelope on failure (`isError: true`, content = `{"error_code","message","detail"}`).

### `list_engine_classes`
- **Args** (all optional): `{"module_prefix": str?, "name_contains": str?}` — filters (resolves OQ7's list-filter question). `module_prefix` matches `fqn`/`module` by `str.startswith` (e.g. `"vibe_cading.mechanical"`); `name_contains` is a case-insensitive substring on `name`. Both absent ⇒ full index.
- **Result**:
```jsonc
{ "tool_contract_version": "1.0", "engine_api_schema_version": "1.1", "count": 70,
  "classes": [ {"fqn": "...", "name": "...", "module": "...", "doc_summary": "<first line of doc>"} ] }
```
Source: committed `engine_api.json` `classes[]` (fields `fqn`/`name`/`module`/`doc` confirmed live). Deterministic: same JSON ⇒ same output (R2 / NFC determinism).

### `query_engine_class`
- **Args**: `{"class_key": str (required), "match": "exact"|"short" = "exact"}`.
  - **Lookup key (resolves OQ7):** `class_key` matches against **`fqn` first (exact, unique)**. If `match="short"` OR the key contains no `.`, fall back to matching `name` (the short class name); if the short name is **ambiguous** (>1 class shares it) the tool returns an error envelope `error_code: ambiguous_class` listing the candidate `fqn`s — never silently picks one. **Exact, not fuzzy** (deterministic contract; fuzzy match is a non-goal — a client gets a precise miss it can correct, not a guessed wrong class).
- **Result**: the full class record from `engine_api.json` (verbatim `module`/`name`/`fqn`/`doc`/`constructors[]`/`result_accessor`), wrapped with `tool_contract_version` + `engine_api_schema_version`. Miss ⇒ `error_code: class_not_found`.

### `get_design_context`
- **Args**: `{"profile": str?}` — optional profile name forwarded to `get_profile(name)`; absent ⇒ the resolved default (`get_profile(None)`, which honours `.env` `PRINT_PROFILE`). An unknown name resolves to `fdm_standard` with the existing stderr warning (`print_settings.py:633-649`) — the payload's `tolerance_profile.name` then reads `"fdm_standard"`, not the bad name (so a typo is visible, per the existing contract).
- **Host-default note (Step-3.5 review condition):** the `tolerance_profile` values in the §get_design_context payload example are the **shipped-default `fdm_standard`**. On a *calibrated* host, `get_profile(None)` returns that host's profile (e.g. `bambu_p1s` via `.env` / `print_profiles_user.json`), so the live payload is correctly host-dependent **by design**. Consequently any test that *pins tolerance values* MUST force `PRINT_PROFILE=fdm_standard` before importing `print_settings` (precedent: `check_visual_contract_freshness.py:102`) — see Tests #4. This is the same host-calibration drift hazard the visual-contract freshness work hit; the fix is to env-neutralize the value-pinning test, never to byte-pin a host-dependent value.
- **Result**: the `get_design_context` payload (§get_design_context design) wrapped with `tool_contract_version`. Carries its own `schema_version` ("1.0").

### `compile_model`
- **Args** (§Compile/preview tool): `{"class_path": str (required), "params": object = {}, "outputs": ["step"] , "views": ["iso_ne"], "return_inline": false}`.
- **Result** (§result envelope): `{"tool_contract_version": "1.0", "artifacts": [{"format","path",("view"),("inline")}]}`. Errors per the mapping table.
- **Inline-fallback contract + size guard (Challenge B):** `inline` is present **only** when `return_inline=true` **and** `format=="svg"` **and** the SVG byte size ≤ **256 KiB** (`MAX_INLINE_SVG_BYTES`). Over the cap ⇒ `inline` omitted, `path` still returned, and a `note: "svg exceeded inline cap; path-only"` field added to that artifact. STEP/STL are **never** inlined (binary base64 bloats the JSON-RPC frame — opt-in only for SVG text). Default (`return_inline=false`) is path-only for all formats: the server runs on the user's own machine (RFC local-trust), so a local client opens the path losslessly.

## Implementation Plan
Ordered so isolation + packaging land **before/with** the server (the isolation guard must be green before the SDK-importing files exist in a way that could leak).

- [ ] **T1 — Packaging.** Add `[project.optional-dependencies]` `mcp = ["mcp>=1,<2"]` to `pyproject.toml` (do NOT touch `dependencies`). Add the README "Dev Setup" quickstart line. *(R5, R6-docs.)*
- [ ] **T2 — Isolation guard (ships before the server).** Write `vibe_cading/tools/check_mcp_import_isolation.py` (Layer A AST `find_violations` modeled on `check_no_main_blocks.py`; Layer B subprocess assertion). AGPL header. Wire both into `ci.yml` lint stage + grep twin. *(R7; OQ6.)* — verifiable immediately: it must pass on the current tree (no `vibe_cading/mcp/` yet ⇒ trivially green; Layer B already holds).
- [ ] **T3 — Package skeleton.** Create `vibe_cading/mcp/{__init__.py, contract.py}` — marker docstring + AGPL header; `contract.py` holds `TOOL_CONTRACT_VERSION = "1.0"` + the additive/breaking policy docstring. No SDK imports. *(R8.)* Re-run T2 guard — still green (these files are SDK-free).
- [ ] **T4 — `context.py`.** Implement `get_design_context` aggregation: `CONTEXT_CONSTANTS` tuple (the allowlist), live `get_profile()` → serialized `ToleranceProfile`/`FitGrade`, `DOC_POINTERS`, payload `schema_version`. SDK-free, lazy-imports nothing heavy. *(R3.)*
- [ ] **T5 — `tools.py`.** The 4 SDK-free handlers + arg-schema dicts + result/error builders. `model_loader`/`preview`/`json`-load are imported **lazily inside handlers** (preserve no-CadQuery-at-module-load). `compile_model` writes to `tempfile.mkdtemp(prefix="vibe_cading_mcp_")`, reuses `parse_params` via the object→`k=v` shim, routes svg→`export_previews(quiet=True)` and step/stl→`cq.exporters.export(model_loader.resolve_solid(instance), …)` (`resolve_solid` `:196` — **never** a bare `.solid`); threads **no** `ToleranceProfile`. *(R2, R3, R4, R9-shapes.)*
- [ ] **T6 — `server.py`.** **First verify the SDK surface live** (`pip install -e ".[mcp]"`, probe the real `mcp` API — see the SDK-surface caveat under Packaging+UX), then build the SDK `Server`, register the 4 tools (adapter wraps each `tools.py` handler — Challenge E seam), apply the one `try/except` → error envelope (serialize via `content=[TextContent(...)]` + `isError`). SDK import allowed here. *(R1, R8, R9.)*
- [ ] **T7 — `__main__.py`.** `try/except ImportError` missing-extra hint (R6); stdio-transport bootstrap → `server`. SDK import allowed here. *(R1, R6.)*
- [ ] **T8 — Handler unit tests** (`tests/mcp/test_tools.py`, `test_context.py`): each tool's handler called directly (no SDK, no subprocess); the allowlist anti-drift test; introspection determinism. Compile tests gated via `pytest.importorskip("cadquery")`; value-pinning context tests force `PRINT_PROFILE=fdm_standard` before importing `print_settings` (host-default note). **These tests run in the `mcp`-absent lint stage, and that is what *enforces* the SDK-free discipline of `tools.py`/`context.py`/`contract.py`:** a stray top-level `import mcp` in any of them fails test collection here. (The cross-package AST guard from T2 does **not** cover this direction — those files sit inside its carve-out — so the unit-test import is the load-bearing enforcement.) *(R11a; R3 anti-drift; Challenge A; Challenge E.)*
- [ ] **T9 — Isolation guard tests** (`tests/tools/test_check_mcp_import_isolation.py`): Layer A flags a planted violating fixture; Layer B subprocess assertion passes on the real tree. *(R7; R11c.)*
- [ ] **T10 — stdio smoke test** (`tests/mcp/test_stdio_smoke.py`, gated via `pytest.importorskip("mcp")`): spawn `python -m vibe_cading.mcp`, round-trip `initialize` + one `tools/call` (`list_engine_classes`), assert a well-formed response. *(R1, R11b.)*
- [ ] **T11 — Tool-contract snapshot test** (`tests/mcp/test_tool_contract_snapshot.py`, gated via `pytest.importorskip("mcp")` — needs the SDK to introspect registered tool defs): serialize registered tool defs, byte-compare to a committed fixture; `--update` regenerates. *(R8; OQ3.)*
- [ ] **T12 — CI wiring for the SDK jobs.** Add a step/job that `pip install -e ".[mcp]"` then runs the smoke + snapshot tests (after the existing CadQuery-bearing steps). Confirm Layer B still runs in the lint stage where `mcp` is absent. *(OQ6; R11; Challenge F.)*

## Tests
Two-tier strategy (R11): (a) direct handler unit tests (pure-Python, no SDK, no subprocess); (b) one stdio smoke test; plus both isolation layers and the contract snapshot. **Every R1–R11 appears in a "Maps to" cell below.** Rows needing CadQuery are marked **[CQ]** (run in the post-build Pytest/SDK stage where `cadquery` is installed). **No representative-scale geometry row is owed:** this task ships no model class, no `build.toml` entry, and no full-`build.py`/`boolean_diff` path (no geometry) — so the §4 Representative-Scale gate does not apply here; this absence is intentional and recorded for the reviewer. **Optional-dependency gating is explicit (Step-3.5 review condition):** SDK-gated rows (smoke #1, snapshot #12) use `pytest.importorskip("mcp")`; **[CQ]** rows (#6, #7) use `pytest.importorskip("cadquery")` — an unconditional `import` would hard-fail test *collection* in the no-`mcp` lint stage.

| # | Test description | Expected assertion | Maps to | File / location |
|---|------------------|--------------------|---------|-----------------|
| 1 | Spawn `python -m vibe_cading.mcp`, round-trip `initialize` + `tools/call list_engine_classes` over stdio | well-formed JSON-RPC response; no port opened; exit clean | **R1** | `tests/mcp/test_stdio_smoke.py` |
| 2 | `list_engine_classes` handler reads committed JSON; same JSON ⇒ same output; filters work | `count==len(classes)`; `module_prefix`/`name_contains` filter correctly; deterministic | **R2** | `tests/mcp/test_tools.py` |
| 3 | `query_engine_class` exact `fqn` hit; short-name fallback; ambiguous short-name ⇒ `ambiguous_class`; miss ⇒ `class_not_found` | record matches `engine_api.json`; ambiguity never silently resolved | **R2** (lookup-key OQ7) | `tests/mcp/test_tools.py` |
| 4 | `get_design_context` payload shape: live profile + curated constants + doc pointers; carries `schema_version` | **sets `PRINT_PROFILE=fdm_standard` before importing `print_settings`** (host-independent value-pinning, precedent `check_visual_contract_freshness.py:102`); profile fields then match `get_profile()`; `doc_pointers` are path/anchor only (no prose) | **R3** | `tests/mcp/test_context.py` |
| 5 | Anti-drift: every `CONTEXT_CONSTANTS` name resolves on `vibe_cading.lego.constants` and is a `float` | `getattr` never raises; all values `float` (Challenge A guard) | **R3** | `tests/mcp/test_context.py` |
| 6 | **[CQ]** `compile_model` step output: valid class+params ⇒ artifact with existing `.step` path under `vibe_cading_mcp_*` temp | file exists at returned path; path under OS temp, not repo | **R4** | `tests/mcp/test_tools.py` |
| 7 | **[CQ]** `compile_model` svg via `export_previews(quiet=True)`; `return_inline=true` under cap ⇒ `inline` present; over 256 KiB ⇒ omitted + `note` | reuses `export_previews` (no `cq.exporters` dup for svg); size guard honored | **R4** (Challenge B) | `tests/mcp/test_tools.py` |
| 8 | `pip install -e .` (no extra) resolve graph excludes `mcp`; `[project.optional-dependencies].mcp == ["mcp>=1,<2"]`; `dependencies` unchanged | TOML assertion; `mcp` not in base resolve set | **R5** | `tests/mcp/test_packaging.py` |
| 9 | `python -m vibe_cading.mcp` with `mcp` absent prints the one-line `pip install -e ".[mcp]"` hint, exits non-zero, no traceback | stderr contains the hint string; returncode != 0; no `Traceback` in output | **R6** | `tests/mcp/test_missing_extra.py` |
| 10 | Layer A: planted `from vibe_cading.mcp import x` in a temp fixture module ⇒ guard fails; clean tree ⇒ passes; grep twin agrees | `find_violations` returns the planted file; real tree green | **R7** | `tests/tools/test_check_mcp_import_isolation.py` |
| 11 | Layer B: subprocess `import vibe_cading` ⇒ no `mcp`/`vibe_cading.mcp.*` in `sys.modules` | `leaked == []`; host-independent (pure import-graph) | **R7** | `tests/tools/test_check_mcp_import_isolation.py` |
| 12 | Tool-contract snapshot: registered tool defs byte-match committed fixture; `TOOL_CONTRACT_VERSION` present in each result | snapshot equal; `--update` regenerates; drift fails | **R8** | `tests/mcp/test_tool_contract_snapshot.py` |
| 13 | Error envelope mapping: bad path→`bad_class_path`; bad module→`module_not_found`; bad class→`class_not_found`; bad params→`bad_params`; geometry raise→`model_error`/`compile_failed`; **no traceback escapes** | each exception → expected `error_code`; result is `isError:true`, never a transport crash | **R9** | `tests/mcp/test_errors.py` |
| 14 | AGPL header on every non-empty new `.py`; stdio≠§13 note + future-HTTP flag present in design/docstring | `check_license_headers.py` passes on new files; doc text present | **R10** | existing license-header CI step (`ci.yml:79`) + `tests/mcp/test_tools.py` (header assert) |
| 15 | Two-tier coverage exists: handler unit tests (no SDK) + one stdio smoke + both isolation layers; compile tests gated `[CQ]` | the suite contains all three tiers; compile tests skip when CadQuery absent | **R11** | `tests/mcp/` + `tests/tools/test_check_mcp_import_isolation.py` |

## Success Criteria
1. `python -m vibe_cading.mcp` (with `[mcp]` installed) serves stdio MCP; an `initialize` + `tools/call` round-trips; **no** port/listener opened; no API key required. *(R1)*
2. All four tools return their documented wire shapes; introspection reads `engine_api.json` (no request-time AST walk); same JSON ⇒ byte-identical introspection output. *(R2, R3)*
3. `compile_model` produces STEP/STL/SVG via `model_loader.instantiate` + `export_previews(quiet=True)` with **zero** re-derivation of param-parsing / `sys.path` / solid-resolution; result defaults to a file path under a namespaced OS-temp dir; inline SVG only under the 256 KiB cap. *(R4)*
4. `pip install -e .` (no extra) does **not** resolve `mcp`; `[mcp]` extra is `mcp>=1,<2`; README documents the install. *(R5)*
5. Missing-extra invocation prints a one-line actionable hint and exits non-zero with no traceback. *(R6)*
6. `check_mcp_import_isolation.py` is green in CI on both layers; Layer B proves `import vibe_cading` leaves `sys.modules` free of `mcp`/`vibe_cading.mcp.*`. *(R7)*
7. `TOOL_CONTRACT_VERSION` is echoed on every result and snapshot-tested; additive/breaking policy documented with one concrete example each. *(R8)*
8. The error-mapping table is implemented; no exception escapes as a transport crash. *(R9)*
9. Every non-empty new `.py` carries the AGPLv3 header; the stdio≠§13 note + future-HTTP flag are recorded. *(R10)*
10. The test suite contains all three tiers (handler unit / stdio smoke / isolation layers) and passes in CI; compile tests run in the CadQuery stage. *(R11)*

## Out of Scope
(Mirrors the requirements.)
- No LLM agent loop, asset/template library, billing, or provider API keys (belong in a consuming app).
- No HTTP/SSE/WebSocket/network transport — stdio only.
- No PyPI publish of the package or the extra in this task (clone-only audience).
- The consuming application's own design/integration (separate, on the consumer's side, gated on their AGPL clearance).
- No new CAD geometry, model classes, or `build.toml` entries.
- No `[mcp]`-gating of the SDK's own transport deps (upstream `mcp` doesn't gate them; out of our control).

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `get_design_context` curated allowlist rots when `constants.py` changes | Anti-drift unit test (test #5) asserts every allowlisted name resolves + is a `float`; failure on *removal* surfaces in the same PR. No reflection sweep. *(Challenge A)* |
| Client is sandboxed/containerized and can't read the returned file path | Default is local-trust file-path (RFC); `return_inline=true` opt-in for SVG text under a 256 KiB cap; STEP/STL never inlined. *(Challenge B)* |
| Two version fields (`engine_api.json.schema_version` vs `tool_contract_version`) confuse clients | Distinct field names on every result (`engine_api_schema_version` + `tool_contract_version`); independent bump rules; both documented with concrete additive/breaking examples. *(Challenge D)* |
| `tools.py` SDK-free goal collides with SDK registration wanting typed schemas | `server.py` owns the adapter: handlers expose plain `(args:dict)->dict` + a schema dict; the adapter binds SDK types around them. `tools.py` never imports `mcp`. *(Challenge E)* |
| `mcp` not installed in dev container / CI; smoke test needs it but Layer B needs it absent | Env matrix: lint stage (no `mcp`) runs Layer A + B; a dedicated `pip install -e ".[mcp]"` step runs smoke + snapshot. Layer B *requires* absence and runs only where absent. *(Challenge F)* |
| Class-module Layer-B variant would pull CadQuery for marginal coverage | Decided: top-level Layer B + Layer A static class-module scan is sufficient; class-module variant is an escalation path (post-build) only if a real transitive leak is ever proven. *(Challenge C)* |
| Temp artifacts accumulate under OS temp | Namespaced prefix `vibe_cading_mcp_*` (greppable/sweepable); cleanup deferred to OS reaper because path-return requires the file to outlive the call (eager delete races the client). |
| `mcp` v2 (alpha) lands a breaking change mid-launch | Pin `mcp>=1,<2`; the extra firewalls library-only consumers from any transitive break in the SDK tree. |
| Constructor raises an un-typed exception the table doesn't list | Broad `compile_failed` catch-all is last in `server.py`'s `try/except`, so a novel OCCT failure still returns a clean error envelope, never a stdio crash. |

---

## Design Dialog Log

### Round 1 — Module layout & reuse seams (OQ4, R2/R3/R4)
**TL proposal:**
> Five-file package (`__init__`/`__main__`/`server`/`tools`/`context`); SDK import confined to `__main__`+`server`; introspection reads committed `engine_api.json`; compile reuses `model_loader.instantiate`+`parse_params` and `preview.export_previews(quiet=True)`; `get_profile()` for context.
**Requester challenge / contribution:**
> Where does the tool-contract version live? It can't ride in `server.py` (SDK-coupled) if you want it snapshot-tested without the SDK.
**Resolution:**
> Added a sixth tiny file `contract.py` (SDK-free) holding `TOOL_CONTRACT_VERSION` + the policy docstring, so the version + its snapshot test are SDK-independent. Layout finalized; carve-out set = `{__main__, server}`.

### Round 2 — Challenge A (get_design_context drift)
**TL proposal:**
> `get_design_context` = curated constant allowlist + live profile + doc pointers.
**Requester challenge:**
> A curated allowlist rots when `constants.py` changes — without a reflection sweep, how do you stop it lying?
**Resolution:**
> Concrete guard landed: a unit test asserts **every** allowlisted name still resolves on `vibe_cading.lego.constants` and is a `float` (test #5). Removal/rename ⇒ red in the same PR. Reverse direction (new constant) is deliberately *not* auto-surfaced — curation is intentional; only *removal* produces a lying payload. Adding a name is an additive `schema_version` bump. No reflection sweep needed.

### Round 3 — Challenge B (compile transport assumption)
**TL proposal:**
> Default to file-path return (reuses `export_previews`' `Path` return; local-trust model).
**Requester challenge:**
> File-path assumes the client shares the filesystem; over stdio a client could be sandboxed/containerized. Defend the default and pin the inline fallback.
**Resolution:**
> Defended: RFC's explicit local-trust, single-tenant, runs-on-user's-machine model makes file-path the correct, lossless default. Pinned the fallback: `return_inline=true` inlines **SVG text only**, **only** under a **256 KiB** cap (`MAX_INLINE_SVG_BYTES`); over cap ⇒ path-only + a `note`. STEP/STL never inlined (base64 bloats JSON-RPC frames). Size guard is a hard contract, not advisory.

### Round 4 — Challenge C (Layer B cost/placement)
**TL proposal:**
> Two-layer guard; Layer B runs `import vibe_cading` in a clean subprocess.
**Requester challenge:**
> A class-module Layer-B variant pulls CadQuery (heavy). The invariant we most care about is top-level `import vibe_cading` staying `mcp`-free (cheap). Does the class-module variant run in CI, or is top-level Layer B + Layer A's static class-module scan enough?
**Resolution:**
> Decided **not** to run a class-module Layer-B step. Layer A already statically scans every class module's source imports; the only extra a class-module Layer-B adds is a transitive leak, whose realistic path is itself a direct `import mcp` Layer A catches. So top-level Layer B (lint stage, no CadQuery) + Layer A static scan is sufficient. Class-module variant is documented as a post-build escalation path *only if* a real transitive leak is ever proven — we don't pay the CadQuery import speculatively.

### Round 5 — Challenge D (two version fields)
**TL proposal:**
> Tool contract gets its own version, separate from `engine_api.json.schema_version`.
**Requester challenge:**
> Both will coexist. How does a client tell them apart, and what's the additive-vs-breaking rule — one concrete example of each.
**Resolution:**
> Distinct field names on every result: `engine_api_schema_version` (versions class records) and `tool_contract_version` (versions tool signatures), independent bump cadences. Additive ⇒ minor bump (concrete: add `return_inline=false` to `compile_model` — old clients unaffected). Breaking ⇒ major bump (concrete: rename `query_engine_class`'s `class_key`→`fqn` — pinned clients break). Snapshot test enforces the contract version.

### Round 6 — Challenge E (handler/SDK decoupling seam) & Challenge F (dev/CI env)
**TL proposal (E):**
> `tools.py` SDK-free for testability.
**Requester challenge (E):**
> SDK tool-registration wants typed signatures/schemas. Show the concrete seam — how does `server.py` register SDK tools without `tools.py` importing `mcp`?
**Resolution (E):**
> Concrete seam: each `tools.py` handler is a plain `def handler(args: dict) -> dict` paired with a plain `ARG_SCHEMA: dict` (JSON-schema as a Python dict, no SDK types). `server.py` iterates a registry of `(name, handler, schema)` and, for each, calls the SDK's tool-registration with the schema dict and a thin closure that (a) calls the handler, (b) wraps the return / exception in the MCP content+`isError` envelope. The SDK types live *only* in that closure in `server.py`; `tools.py` imports nothing from `mcp`. Unit tests call `handler(args)` directly.
**Requester challenge (F):**
> `mcp` is NOT installed in this dev container (confirmed). How are server + smoke test developed/run? Does CI install `.[mcp]` for the smoke job? Confirm Layer B runs *without* `mcp` installed (it asserts `mcp` ABSENT).
**Resolution (F):**
> Confirmed `mcp` absent in the container (`importlib.metadata.version('mcp')` raises) and `cadquery 2.7.0` present. Env matrix: **(i) lint stage** — no `mcp`, no CadQuery: runs Layer A + Layer B (Layer B *requires* `mcp` absent — it asserts absence — so this is exactly the right stage) + handler unit tests that import SDK-free modules. **(ii) existing Pytest + Build-smoke stage** — CadQuery present (`requirements-ci.txt`), no `mcp`: runs `[CQ]` compile-handler tests. **(iii) new SDK stage** — `pip install -e ".[mcp]"`: runs the stdio smoke + tool-contract snapshot (both need the SDK to introspect/round-trip). Local dev: a contributor installs `.[mcp]` once to develop `server.py`/`__main__.py`; the SDK-free `tools.py`/`context.py`/`contract.py` are developed and unit-tested with `mcp` absent (proving the decoupling holds). This is why the smoke/snapshot tests are SDK-gated (skip when `mcp` absent) — so the suite stays green in the no-`mcp` stages.

### Round 7 — Step 3.5 independent-review conditions folded in (2026-06-18)
Independent **TL** + **Developer** reviewers (fresh context) both returned **APPROVE-WITH-CONDITIONS**; all conditions were specification-completeness gaps (not redesigns) and have been applied to the brief above:
> 1. **SDK-free enforcement seam made explicit** (TL-C1) — T8 now states the handler unit tests run in the `mcp`-absent lint stage and that *this* (not the cross-package AST guard) enforces the SDK-free discipline of `tools.py`/`context.py`/`contract.py`.
> 2. **SDK-surface caveat** (TL-C2 + Dev-C3) — Packaging+UX records that the `mcp` SDK symbols are doc-pinned, not import-grounded (SDK absent here); first Phase-A act is `pip install -e ".[mcp]"` to verify; T6 leads with the live-verify step.
> 3. **`isError` ⇄ content-block serialization** (TL-C3) — Error-envelope section pins `content=[TextContent(type="text", text=json.dumps(payload))]` + `isError`, owned by `server.py`.
> 4. **`resolve_solid` routing + no-`ToleranceProfile` decision** (TL-C4 + Dev-C4) — compile § and T5 route STEP/STL through `model_loader.resolve_solid(instance)` (`:196`), never bare `.solid`; the no-profile omission is a recorded decision.
> 5. **Env-neutralized value-pinning test** (Dev-C1) — Tests #4 forces `PRINT_PROFILE=fdm_standard` before importing `print_settings`; `get_design_context` §Result carries the host-default note (the visual-contract host-calibration drift hazard).
> 6. **Optional-dependency skip mechanism** (Dev-C2) — Tests preamble + T8/T10/T11 specify `pytest.importorskip("mcp")` (smoke/snapshot) and `pytest.importorskip("cadquery")` (`[CQ]` rows).

Re-confirmation by fresh-context same-role reviewers recorded in the Independent Review sections below.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(N/A — domain integrity gate is NO)*
- [x] Requester sign-off  *(co-design dialog complete; all six challenges A–F resolved with substantive revisions)*
- [x] TL sign-off  *(architecturally-significant work; drafting TL self-signs the authoring gate — all seven Step-3 termination conditions met: every R1–R11 addressed; every OQ1–OQ7 resolved; Tests table maps every R1–R11; success criteria measurable; Module-depth done with the no-ABC record; non-blocking concerns cost-checked; domain gate NO ⇒ no domain co-sign owed)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
<!-- Do NOT touch — populated by the fresh-context independent reviewers in Step 3.5. -->
- [x] Independent TL  *(fresh-context `tl` subagent — APPROVE-WITH-CONDITIONS → all 4 conditions applied → re-confirmed APPROVE; see `## Independent TL Review` → `### Re-confirmation`)*
- [x] Independent Developer  *(fresh-context `developer` subagent — APPROVE-WITH-CONDITIONS → all 4 conditions applied → re-confirmed APPROVE; see `## Independent Developer Review` → `### Re-confirmation`)*
- [ ] Independent Researcher  *(N/A — domain integrity gate is NO)*

### Step 4 — Human design approval
- [x] **Human approved the design** — 2026-06-18, maintainer (`madMarcus` / @fa-mc), in-session. This approves the *design* (the "how"); the *RFC* (the "what / whether") was separately accepted by the platform/consumer on RFC #41. Implementation (Step 5) is gated on the maintainer's explicit go (the original task scope was "stop at the human approval gate; no implementation").

---

## Implementation Status
<!-- Populated by #developer at Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (T1–T12 — every `[ ]` below marked `[x]`)
- [x] Test suite executed — result: **44 new tests pass** (`tests/mcp/` + `tests/tools/test_check_mcp_import_isolation.py`); **full suite 429 passed, 2 xfailed, 0 failures** (`python3 -m pytest tests/`, with `cadquery` + `.[mcp]` installed). In the `mcp`-absent lint-stage simulation: **37 passed, 5 skipped** (the SDK-gated smoke/snapshot rows + the 3 `_dispatch` adapter rows skip via `pytest.importorskip("mcp")`).
- [x] No new linter / static-check errors — `flake8 .` clean; `check_license_headers.py`, `check_no_main_blocks.py`, `gen_engine_api.py --check`, and the new `check_mcp_import_isolation.py` (both layers) all exit 0.

### Task checklist (T1–T12)
- [x] **T1** — Packaging: `[project.optional-dependencies] mcp = ["mcp>=1,<2"]` added to `pyproject.toml` (`dependencies` untouched); README "Dev Setup" quickstart line added.
- [x] **T2** — Isolation guard `vibe_cading/tools/check_mcp_import_isolation.py` (Layer A AST `find_violations` modeled on `check_no_main_blocks.py`; Layer B clean-subprocess assertion). Wired into `ci.yml` lint stage + grep twin. Green on the current tree.
- [x] **T3** — Package skeleton: `vibe_cading/mcp/__init__.py` (marker docstring + header, imports nothing) + `contract.py` (`TOOL_CONTRACT_VERSION = "1.0"` + additive/breaking policy). SDK-free.
- [x] **T4** — `context.py`: `get_design_context` aggregation (`CONTEXT_CONSTANTS` allowlist, live `get_profile()` → serialized profile, `DOC_POINTERS`, payload `schema_version`). SDK-free, CadQuery-free.
- [x] **T5** — `tools.py`: 4 SDK-free handlers + arg-schema dicts + `_ToolError`. `model_loader`/`preview`/`cadquery` lazy-imported inside handlers. `compile_model` writes to `tempfile.mkdtemp(prefix="vibe_cading_mcp_")`, reuses `parse_params` via the object→`k=v` shim, svg→`export_previews(quiet=True)`, step/stl→`cq.exporters.export(model_loader.resolve_solid(instance), …)`, no `ToleranceProfile`.
- [x] **T6** — `server.py`: SDK surface verified live (see deviation D-SDK below), builds the low-level `mcp.server.Server`, registers the 4 tools via `@server.list_tools()`/`@server.call_tool()`, one `try/except` → `CallToolResult(content=[TextContent(text=json.dumps(...))], isError=…)`.
- [x] **T7** — `__main__.py`: `try/except ImportError` missing-extra hint (R6); stdio bootstrap (`mcp.server.stdio.stdio_server()` + `Server.run(…, create_initialization_options())`). No `__main__` guard (module body runs under `python -m`).
- [x] **T8** — Handler unit tests (`tests/mcp/test_tools.py`, `test_context.py`): handlers called directly; allowlist anti-drift; introspection determinism; AGPL-header assert. `[CQ]` rows `pytest.importorskip("cadquery")`; context value-pin forces `PRINT_PROFILE=fdm_standard` before importing `print_settings`.
- [x] **T9** — Isolation guard tests (`tests/tools/test_check_mcp_import_isolation.py`): Layer A flags planted violations (and does NOT false-positive on docstring mentions); Layer B passes on the real tree.
- [x] **T10** — stdio smoke test (`tests/mcp/test_stdio_smoke.py`, `importorskip("mcp")`): spawns `python -m vibe_cading.mcp`, round-trips `initialize` + `tools/call list_engine_classes` via the SDK client; also asserts a structured error round-trips with `isError`.
- [x] **T11** — Tool-contract snapshot (`tests/mcp/test_tool_contract_snapshot.py`, `importorskip("mcp")`): serializes registered tool defs → committed `tests/mcp/tool_contract_snapshot.json`; byte-compares; `UPDATE_MCP_CONTRACT_SNAPSHOT=1` regenerates (idempotent).
- [x] **T12** — CI wiring: new `ci.yml` step (last) `pip install -e ".[mcp]"` then runs the smoke + snapshot tests; Layer B remains in the lint stage where `mcp` is absent.

### Deviations from the design (each with rationale)

**D-ALLOWLIST — `get_design_context` constant allowlist ships 15 names, not the design's 19.**
The design's allowlist (and payload JSONC) lists four studded-System block nominals — `BLOCK_PLAY`, `BLOCK_WALL`, `BLOCK_ROOF`, `CLUTCH_TUBE_OD` — that **do not exist on this branch**. They were added by the `LegoBlock` generator commit `d25b76c` (`vibe_cading/lego/block.py` + 21 lines in `constants.py`), which is on the **unmerged sibling branch `feat/lego-block-generator`** and is *not* an ancestor of this branch's HEAD (`60bdf5e`). The design author grounded the allowlist against a tree that transiently included those constants. Per the design's own **anti-drift invariant** — the allowlist must contain only names that resolve, or the context payload *lies* (and test #5 goes red) — I ship the **15 names that resolve here** and omit the 4 absent ones. The design explicitly frames "adding a name to the allowlist is an additive `schema_version` bump (1.0→1.1)", so when `LegoBlock` lands on `main` a one-line follow-up adds the 4 names + bumps `CONTEXT_SCHEMA_VERSION`. The mechanism (curated tuple + anti-drift test asserting resolve+float) is **unchanged**; only the contents differ to match this tree. (Recorded in a `context.py` comment.) *Predicted cost if wrong: zero on this branch; one additive-bump follow-up PR once LegoBlock merges.*

**D-TOOLERROR — the handlers' exception is named `_ToolError` (underscore-prefixed), not `ToolError`.**
The `engine_api` AST extractor (`gen_engine_api.py` → `extractor.py`) walks **all of `vibe_cading/**`** and catalogs every *public* (`ClassDef` whose name lacks a leading `_`) class with a constructor — it has no per-subtree exclusion for `vibe_cading/mcp/`. A public `ToolError(Exception)` in `tools.py` was therefore picked up as a 70th "model class" (`vibe_cading.mcp.tools.ToolError` with a defaulted `.solid` accessor), failing `gen_engine_api.py --check`. The design did not anticipate the MCP package being *walked by* the extractor (it scoped only the MCP package *reading* `engine_api.json`). `ToolError` is genuinely package-internal — clients only ever see the JSON `{error_code, message, detail}` envelope, never the Python type — so underscore-prefixing it is the correct visibility and a purely local fix within `tools.py`'s boundary (no shared-contract change). This keeps `engine_api.json` a clean model-class catalog and undisturbed. *Predicted cost: zero — `--check` is green.*

> **↳ Escalation to TL/Admin (shared-contract follow-up, out of this task's scope):** the `_ToolError` rename fixes the *current* leak, but the root cause is latent — the engine_api extractor walking `vibe_cading/mcp/` will re-bite the moment any contributor adds a *public* class to the MCP package (a new `@dataclass`, a helper class in `context.py`, etc.). The architecturally-correct fix is to exclude the `vibe_cading/mcp/` subtree from the extractor's root walk (analogous to how `experiments/` is already excluded), which is a change to the shared `vibe_cading/tools/` engine_api CLI — TL territory, not a Developer unilateral edit. Flagged here for a follow-up.

**D-SDK — SDK-surface verification (the design's mandated first Phase-A act).**
`pip install -e ".[mcp]"` installed `mcp 1.28.0` (exactly the cited version; it transitively pulled `starlette`/`uvicorn`/`sse-starlette`/`pydantic-settings`/`pyjwt`/`httpx` — confirming D2's "optional extra" premise). I probed the live SDK before writing `server.py`/`__main__.py`. The design's doc-pinned snippets held: `from mcp.server import Server` is correct; the stdio bootstrap is `mcp.server.stdio.stdio_server()` (async ctx mgr → `(read, write)`) + `Server.run(read, write, server.create_initialization_options())` (exactly as the Independent-TL reviewer predicted in Condition 2). The one detail the design left as "tool-registration API" resolves to the low-level **decorator** API (`@server.list_tools()` returning `list[types.Tool]`, `@server.call_tool()` taking `(name, arguments)` and returning `types.CallToolResult`) — **not** a `register(name, handler, schema)` method. This is **fully consistent with the `server.py`/`tools.py` split** (Challenge E): `tools.py` handlers stay plain `(dict)->dict`, `server.py`'s closure adapts each into the decorator and owns the `CallToolResult`/`isError` serialization. **No architecturally-significant deviation — no escalation needed.** The `call_tool` decorator runs `jsonschema.validate(arguments, inputSchema)` *before* the handler, so a schema-`required` violation becomes an SDK-level error result (still `isError`, no crash) rather than my `bad_params` envelope; the documented error-mapping cases all route through my handlers as designed.

- **Developer note:** Every reuse seam was opened and import-grounded this session (`model_loader.instantiate`/`parse_params`/`resolve_solid` `:186`/`:109`/`:196`, `preview.export_previews(...quiet=True)` `:222`, `engine_api.json`, `print_settings.get_profile`/`ToleranceProfile`/`FitGrade`). The full compile path (param-shim → instantiate → `resolve_solid` → STEP/STL/SVG export under a `vibe_cading_mcp_*` temp dir) was validated end-to-end with a real class before writing the handler. The live `fdm_standard` profile resolves `axial=0.2` (not the design payload's illustrative `0.10`) — the value-pinning test compares against a freshly-resolved `get_profile("fdm_standard")` rather than literals, exactly the C1 host-calibration-drift fix. **The committed design docs (`60bdf5e`) were NOT re-committed.**

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes (fresh-context `tl` subagent, 2026-06-18 — opened every file under review; did not trust the developer summary):

  **Verdict: PASS.** The implementation is a faithful, architecturally-sound
  realization of the approved design. I independently re-ran the verification
  gates and opened all six package files, the isolation guard, the engine_api
  extractor, the CI/pyproject/README diffs, and all eight test files. The
  thin-adapter posture holds end-to-end: zero domain logic, zero re-derivation,
  surgical SDK isolation. **One non-blocking finding (TL-1), correctly deferred
  with a required tracking action.** Sign-off granted.

  **Gates re-run live this session (not taken on trust):**
  - `check_mcp_import_isolation.py` — Layer A **and** Layer B both green (rc=0).
  - `gen_engine_api.py --check` — green (rc=0); `engine_api.json` is a clean
    70-class catalog with **no** `vibe_cading.mcp.*` entry.
  - `pytest tests/mcp/ tests/tools/test_check_mcp_import_isolation.py` — **44
    passed**. `flake8` on all new files — clean.
  - `mcp 1.28.0` is installed in this container, so the SDK-gated rows (smoke,
    snapshot, `_dispatch` adapter) ran for real here, not skipped.

  **Design conformance (§1) — all confirmed by reading the files:**
  - 6-file package; the `mcp` SDK appears **only** in `__main__.py` (`:64,66`)
    and `server.py` (`:48-49`). `tools.py` / `context.py` / `contract.py` are
    SDK-free; SDK pulled lazily *inside* `compile_model` (`tools.py:406-408`),
    never at module top — Layer B proves `import vibe_cading` leaves
    `sys.modules` free of `mcp`/`vibe_cading.mcp.*`.
  - Introspection reads committed `engine_api.json` (`tools.py:104,114`); **no**
    request-time AST walk. `compile_model` reuses `parse_params` via the
    object→`k=v` shim (`:343-353,412`), `instantiate` (`:421`), and
    `resolve_solid` (`:455`) — **not** a bare `.solid` (R4 MUST-NOT honored);
    SVG routes through `export_previews(..., quiet=True)` (`:486`); the only new
    `cq.exporters` call is for STEP/STL binary formats (`:472`).
  - File-path default + 256 KiB inline-SVG cap (`MAX_INLINE_SVG_BYTES`,
    `:59`, applied `:510`); STEP/STL never inlined. Structured `isError`
    envelope owned solely by `server.py`'s adapter (`_dispatch` `:78-98`);
    handlers return plain dicts — no escaping traceback (the broad catch-all at
    `server.py:91` and `tools.py:473,492` is the last-resort `compile_failed`).
  - `TOOL_CONTRACT_VERSION` single-sourced in `contract.py:62`, echoed on every
    result, and snapshot-tested against the **live SDK-registered** tool defs
    (`test_tool_contract_snapshot.py:51-65` introspects `build_server()`, not a
    hand-list — genuine drift detection). AGPL header verbatim on all 6 new
    `vibe_cading/**` files + the new tool + all 8 test files.

  **Integration seams (§2):** the adapter seam genuinely keeps `tools.py`
  SDK-free — `server.py` binds `types.Tool`/`TextContent`/`CallToolResult`
  around the SDK-free `TOOLS` registry in one place (`:108-133`). CI wiring
  matches the design table: Layer A + Layer B + grep twin in the `mcp`-absent
  lint stage (`ci.yml` +`MCP import isolation` steps), SDK smoke/snapshot in a
  final step gated behind `pip install -e ".[mcp]"`. Tests, Success Criteria
  1–10, and Tests-table rows #1–#15 all exist and assert what they claim
  (error-mapping test exercises both the handler layer *and* the `_dispatch`
  envelope conversion incl. the "no traceback escapes" assertion; the context
  value-pinning test correctly forces `PRINT_PROFILE=fdm_standard` *before*
  importing `print_settings` and compares against a fresh `get_profile()`, not
  literals — the C1 host-drift fix is real).

  **Deviation adjudication (§4) — assessed independently:**
  - **D-ALLOWLIST — ACCEPTED, sound, nothing owed now.** Verified `BLOCK_PLAY`/
    `BLOCK_WALL`/`BLOCK_ROOF`/`CLUTCH_TUBE_OD` are absent on this branch (they
    live on the unmerged `feat/lego-block-generator`). The design's own
    anti-drift invariant *requires* shipping only names that resolve — shipping
    the 4 absent names would make test #5 red and the payload lie. The
    15-name tuple is the correct content; the mechanism (curated tuple +
    resolve+float test) is unchanged. The additive-`schema_version`-on-merge
    plan is exactly the policy `contract.py`/`context.py:65-72` already
    documents. The branch-isolation reasoning is correct. *Nothing owed on this
    branch.* Follow-up cost if forgotten: zero on this branch; one additive-bump
    PR once LegoBlock lands (already captured in the `context.py:65-72` comment).
  - **D-SDK — ACCEPTED, consistent, no hidden shallowness.** The low-level
    decorator registration form (`@server.list_tools()` / `@server.call_tool()`)
    is fully consistent with the `server.py`/`tools.py` split: handlers stay
    plain `(dict)->dict`, the decorator closure in `server.py:117-133` owns all
    SDK ceremony. The developer's discovery that the SDK runs
    `jsonschema.validate(arguments, inputSchema)` *before* the handler is a
    *strengthening*, not a gap — schema `required`/`additionalProperties:false`
    are genuinely SDK-enforced, and the handler-level `bad_params` checks are a
    belt-and-braces second layer. No escalation needed; concur.
  - **D-TOOLERROR — ruling below.**

  **TL-1 (non-blocking) — D-TOOLERROR extractor exclusion: DEFER to a tracked
  follow-up, NOT fix-now-inline. Underscore on this PR is sufficient.**
  I opened the extractor before ruling. Decisive correction to the escalation's
  framing: **the extractor has no subtree-exclusion mechanism.**
  `extract_classes(roots)` (`extractor.py:185`) walks `root.rglob("*.py")` and
  its *only* path filter is `__pycache__` (`:205`); class-level exclusions are
  by naming/base convention (leading `_` `:274`, ABC/Protocol bases `:287-289`,
  `@abstractmethod` `:296`, the `demo` classmethod `:410`). `experiments/` is
  **not** excluded by a subtree filter — it is excluded by *omission from the
  roots list* in `gen_engine_api.py:63-67` (which passes only `vibe_cading/` +
  `parts/`). `vibe_cading/mcp/` sits *inside* the `vibe_cading/` root that IS
  walked, so there is no "analogous to experiments/" one-liner to mirror — the
  correct fix must *introduce* an exclusion seam on the shared extractor (an
  `exclude=` param on `extract_classes`, or a narrow per-class guard, or a
  `*Protocol`-style leak-gate test). That is a shared `vibe_cading/tools/`
  engine_api CLI change with genuine design choices — it lands squarely in
  **two PR-follow-up carve-outs** (out-of-scope code touching files unrelated to
  the MCP package's subject **+** architectural shape) and therefore is
  correctly *deferred*, not forced inline into this PR.
  - **The `_ToolError` underscore is the correct immediate fix** and is
    sufficient for *this* PR: `gen_engine_api.py --check` is green and
    `engine_api.json` carries no MCP entry (both verified live). The underscore
    is also the right visibility on its own merits — clients only ever see the
    JSON `{error_code,message,detail}` envelope, never the Python type.
  - **Required tracking action (so the deferral is honest, not rot — Post-Fix
    Hardening / defense-in-depth):** add a `TODO.md` row for the latent
    extractor gap, and the follow-up MUST land a **durable regression guard** —
    a test asserting no `vibe_cading.mcp.*` fqn appears in `engine_api.json`,
    mirroring the existing `*Protocol`-leak gate the extractor docstring already
    references (`extractor.py:281`). Without that guard, the next public class in
    the MCP package silently re-bites. *(The TODO row is a backlog-tracking doc
    edit — per the TODO direct-push carve-out it may go straight to `main`; the
    extractor fix itself is a normal branch + PR.)*
  - **Predicted cost of the deferral:** bounded and low. The leak can only
    recur if a contributor adds a *public* (non-`_`, non-ABC/Protocol) class to
    `vibe_cading/mcp/` — none is planned. Worst case if it recurs *and* the
    guard is also absent: one red `gen_engine_api.py --check` in that future PR
    (caught in CI, never shipped) costing ~1 dev-cycle to underscore-rename or
    add the exclusion. With the regression-guard test in the follow-up, even
    that is caught by name at authoring time. This does not cross the
    blocking threshold (no consumer-visible defect, no unquantified-risk merge).

  **Workspace hygiene / strict-ops (§5) — clean.** Working tree clean
  (`git status` empty). Commits scoped: `473db82` = guard + extra + CI + guard
  tests (5 files); `032fa44` = package + tools + tests + the design's
  `## Implementation Status` fill-in (16 files). No `git add -A` sweep
  artifacts, no `tmp/` junk, no secrets. **Verified the design body was NOT
  re-committed** — the only `.md` change in `60bdf5e..HEAD` is the Phase-A
  `## Implementation Status` section replacing its placeholder template
  (`+33/-5`); the design through Step 4 sign-off is byte-untouched, exactly as
  the developer claimed.

### Domain Expert Review *(N/A — domain integrity gate is NO)*
- [ ] **Domain expert sign-off**
- Domain expert review notes:

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:

---

## Independent TL Review (fresh context, 2026-06-18)

**Verdict: APPROVE-WITH-CONDITIONS**

The design is unusually well-grounded: I opened every cited file and confirmed
each `file:line` / function-name / wire-shape claim physically holds (see
Verification log). The reuse-seam discipline (zero re-derivation of
param-parsing / `sys.path` / solid-resolution / AST-walking), the lazy-CadQuery
preservation, and the two-layer isolation guard modeled on the proven
`check_no_main_blocks.py` shape are architecturally sound. Every R1–R11 has a
design mechanism and a Tests-table "Maps to" row. The conditions below are
specification-completeness gaps a developer would otherwise have to *guess*
at — none require a redesign, all are local edits to the brief.

### Strengths (≤3)
1. **Reuse seams are exact and verified.** Every consume-don't-reimplement
   claim resolves to a real symbol at the cited line (`instantiate` `:186`,
   `parse_params` `:109`, `export_previews(...quiet=)` `:222`/`:298`,
   `get_profile` `:611`, `engine_api.json` `["schema_version","classes"]`
   with 70 classes). The "MCP server is the sixth caller, not a
   re-implementer" framing is the right structural posture and is true.
2. **Isolation guard asserts the *actual property*, not a proxy.** Layer B
   ("`import vibe_cading` leaves `sys.modules` free of `mcp`/`vibe_cading.mcp.*`")
   is the real runtime-graph invariant, is host-independent (pure import-graph,
   satisfies the reproducibility NFC), and is correctly placed in the
   `mcp`-absent lint stage. The Challenge-C decision to NOT pay a CadQuery
   import for a class-module Layer-B variant is correctly reasoned (Layer A
   already scans every class module's *source* imports; the only delta is a
   transitive leak whose realistic path is itself a direct `import mcp` Layer A
   catches).
3. **Module decomposition earns its keep on the Dual-Lens rule, and the
   no-`BaseMcpTool` record is correct.** A one-method ABC over 4 free functions
   fails both lenses; the explicit "review-blocking over-engineering finding if
   it appears" guard is exactly the right contributor-locality call for an
   OSS-bound codebase. `contract.py` (versioning seam) and
   `check_mcp_import_isolation.py` (invariant boundary) are legitimately-kept
   thin modules under the rule's named carve-outs.

### Conditions / required edits (numbered, each actionable)
1. **State the SDK import *direction* the isolation guard does NOT cover, and
   name the test that does.** The cross-package guard forbids importing
   `vibe_cading.mcp` from class modules; it does **not** forbid `tools.py` /
   `context.py` / `contract.py` from importing `mcp` (they live inside the
   carved-out `vibe_cading/mcp/` subtree). The design's testability claim
   ("handlers unit-testable without the SDK") rests entirely on the Challenge-F
   env matrix running handler unit tests in the **`mcp`-absent** lint stage, so
   a stray `import mcp` at module top of `tools.py` fails *test collection*
   there. That indirect enforcement is sound but must be stated as the
   load-bearing guarantee: add one sentence to the §Module-layout note and to
   T8 making explicit that "the SDK-free discipline of `tools.py`/`context.py`/
   `contract.py` is enforced by test collection failing in the no-`mcp` lint
   stage if any imports `mcp`" — otherwise a developer may assume the AST guard
   covers it (it does not) and put the unit tests only in the SDK stage, which
   would silently void the decoupling guarantee.
2. **Pin the exact stdio bootstrap symbol(s), or label them developer-owned.**
   The brief pins the missing-extra `try/except` import as
   `from mcp.server import Server` (R6 snippet), but R1's actual stdio
   transport bootstrap in `__main__.py` is left as "stdio-transport bootstrap →
   `server`" with no concrete SDK call. The `mcp` SDK's stdio entry
   (`mcp.server.stdio.stdio_server()` + `Server.run(...)` in 1.x) is a real
   API the developer cannot verify in-container (`mcp` is absent — confirmed in
   Challenge F). Either (a) name the expected SDK call sites with a "verify
   against the pinned `mcp>=1,<2` API at impl time" caveat, or (b) explicitly
   record that the `__main__.py`/`server.py` SDK bootstrap surface is
   Developer-owned-with-SDK-docs and out of the design's pin scope. As written
   it is ambiguous whether the developer may choose the bootstrap shape or must
   match an (unspecified) one. (Cost if left ambiguous: a round-trip when the
   developer's chosen bootstrap doesn't match the snapshot fixture in T11.)
3. **Resolve the `isError` envelope ⇄ MCP content-type contract.** The error
   table says the content is "a single JSON object
   `{"error_code","message","detail"}`" with `isError: true`. MCP tool errors
   carry a `content` array of typed blocks (typically `TextContent`); a raw
   JSON *object* is not itself a valid content block. The design must state the
   concrete shape the developer emits — e.g. `isError: true` +
   `content=[TextContent(type="text", text=json.dumps({...}))]` — so the error
   payload and the success-result payloads (which are *also* dicts wrapped in
   text content, per the four wire contracts) use **one** documented
   serialization. Right now success results are shown as bare JSONC objects and
   errors as a bare JSON object, but neither states how the dict becomes an MCP
   content block. One sentence in §Error-envelope + §Data-&-Interface-Contracts
   fixing the dict→content-block serialization removes the guess.
4. **`compile_model` STEP/STL export path needs the same zero-re-derivation
   rigor as the SVG path, including its tolerance-profile posture.** The design
   routes `svg` through `export_previews` (good, verified) but routes
   `step`/`stl` through "`cq.exporters.export` on the resolved `instance.solid`"
   — a *new* `cq.exporters` call. Two gaps: (a) it must resolve the solid via
   `model_loader.resolve_solid(instance)` (`:196`), not reach into
   `instance.solid` directly, to stay consistent with the "no solid-resolution
   re-derivation" MUST-NOT (R4) — `resolve_solid` is the seam and handles the
   missing-`.solid` case the bare attribute access would `AttributeError` on
   uncaught; (b) confirm whether STEP/STL export needs the active
   `ToleranceProfile` plumbed. For this task the class is constructed via
   `instantiate(class_path, params)` and carries its own tolerance defaults, so
   *no* profile is threaded into `compile_model` — that is defensible, but the
   brief should state it explicitly (one line: "compile_model does not accept a
   `profile` arg; tolerance is whatever the class's own constructor resolves —
   a client wanting a specific fit passes it via `params` if the class exposes
   it") so the omission is a recorded decision, not an oversight a reviewer
   re-litigates at Phase B.

### Open concerns (with predicted cost-of-failure)
- **(non-blocking) Tests-row 14 cites `ci.yml:79` as a standalone
  "license-header CI step"; it is not.** License headers are enforced by
  `check_license_headers.py` invoked *inside* `build.py` (`build.py:90`,
  subprocess) — `ci.yml:79-80` is the *comment* on the Build-smoke step
  explaining this. The mechanism is real and the new files fall under it;
  only the citation is imprecise. *Cost if left:* ~0 — a developer reading
  `build.py:90` finds the real invocation; worst case is a few minutes of
  "where is the standalone step?" confusion. Recommend fixing the citation to
  "`check_license_headers.py` via `build.py` (Build-smoke step, `ci.yml:76-82`)".
- **(non-blocking) The anti-drift test (#5) pins allowlist values as `float`,
  but does not pin the *values themselves*.** I confirmed all 19 names resolve
  as module-level floats today, matching the payload JSONC. The test as
  specified would still pass if a constant's *value* changed (e.g.
  `STUD_PITCH` 8.0→7.9) — it asserts type, not value. That is the design's
  stated intent (curation guards against *removal*, live values are
  intentionally live), so this is correct-as-designed, not a defect. *Cost if a
  contributor misreads it:* near-0; flagged only so the reviewer at Phase B
  does not mistake "values not pinned" for a test gap. No change required.
- **(non-blocking) `vibe_cading/tools/` is carved out of Layer A wholesale**, so
  a future *tool* file could import `vibe_cading.mcp` undetected. This is
  consistent with R7's literal scope (R7 protects class modules + `__init__.py`,
  not tools), and tools are CLI entry points not library surface, so it does not
  violate the runtime-graph NFC for library consumers. *Cost if a tool ever does
  import mcp:* low and self-correcting — Layer B would still catch it the moment
  that tool sits on the `import vibe_cading` path (it does not today). No change
  required; noted for completeness.

### Verification log (every code claim I opened and checked)
| Design claim | Cited loc | Held? |
|---|---|---|
| `model_loader.instantiate(dotted, params)` | `model_loader.py:186` | ✅ `:186` def instantiate |
| `model_loader.parse_params(raw)` | `:109` | ✅ `:109` def parse_params |
| param cast ladder int→float→bool→str | `:130-143` | ✅ exact ladder at `:130-143` |
| `load_class` typed-exception trio (ValueError/ModuleNotFoundError/AttributeError) | `:166-182` | ✅ ValueError `:166-169`, MNFE `:174-177`, AttributeError `:178-182` |
| `instantiate` lets constructor exceptions propagate unchanged | `:189-191` | ✅ docstring `:189-191` states it |
| model_loader stdlib-only at import; CadQuery only at `instantiate()` | `:73-79` | ✅ docstring "CadQuery deferral (R4)" `:72-79`; imports are stdlib-only (`importlib`, `sys`, `pathlib`, `typing`) |
| five inline call sites de-duplicated (MCP = 6th caller) | `:16-23` | ✅ enumerates build.py/preview/view/check_topology/check_polar_monotonicity |
| `resolve_solid` seam exists | (uncited; relevant to Condition 4) | ✅ `:196` def resolve_solid |
| `preview.export_previews(model_path, out_dir, params, views, quiet=)` → `list[Path]` | `preview.py:222`, returns `:298` | ✅ signature `:222`, `return written` `:298` |
| `quiet` semantics | `:244-249` | ✅ docstring `:244-249` |
| `export_previews` validates views, raises ValueError on unknown | `:260-265` | ✅ `:260-265` raises ValueError "Unknown view(s)" |
| `engine_api.json` top keys `["schema_version","classes"]`, schema 1.1, 70 classes | live shape | ✅ exactly `["schema_version","classes"]`, `1.1`, 70 |
| class record keys `module/name/fqn/doc/constructors/result_accessor` | live shape | ✅ exact |
| `print_settings.get_profile(name)` | `print_settings.py:611` | ✅ `:611` def get_profile |
| `ToleranceProfile` dataclass | `:264-277` | ✅ `:264-277` |
| `FitGrade` dataclass | `:241-261` | ✅ `:241-261` |
| unknown profile name → fdm_standard + stderr warning | `:633-649` | ✅ `:633-649` (label stays fdm_standard, typo visible) |
| `__init__.py` does NOT re-export sub-packages | `:20-24` | ✅ docstring `:20-23` ("intentionally does NOT re-export") |
| `__init__.py` only touches `importlib.metadata` | `:35` | ✅ `:35` `from importlib.metadata import version` |
| `check_no_main_blocks.find_violations(roots, exclude)` | `:60` | ✅ `:60` def find_violations |
| repo-root resolution | `:89` | ✅ `:89` `repo_root = ...parent.parent.parent` |
| stdlib-only + AST-not-regex rationale | `:32` | ✅ `:32` docstring "AST (not regex) so string literals … do not false-positive" |
| `ocp_vscode` allowlist idiom + grep two-step | `ci.yml:62-73`, `:47-61` | ✅ ocp_vscode step `:62-73`; main-block AST `:47-48` + grep twin `:49-61` |
| `__main__.py` w/o `if __name__==` guard does not trip check_no_main_blocks | (req claim) | ✅ confirmed: `_is_main_guard` only matches `if __name__=="__main__"` top-level `If` nodes (`:43-57`) |
| Pytest step exists | `ci.yml:74` | ✅ `:74-75` "Pytest (unit + smoke tests)" |
| license headers enforced in CI | `ci.yml:79-80` (design) | ⚠️ partial — enforced via `check_license_headers.py` inside `build.py:90`; `ci.yml:79-80` is the *comment*, not a standalone step (Condition/Open-concern noted) |
| AGPL header shape | `model_loader.py:1-14`, `constants.py:1-14` | ✅ identical 14-line AGPL header on both |
| `gen_engine_api.py --check` exists | (req/design) | ✅ `--check` arg `:97` |
| `extractor.py` additive-discipline / SCHEMA_VERSION | `:62-64` | ✅ `:62-64` `SCHEMA_VERSION="1.1"` + pinned-version comment |
| `demo` excluded from engine_api wire contract | (req claim) | ✅ `extractor.py:405-410` skips `child.name == "demo"` |
| `get_design_context` constant allowlist (19 names) resolve as module-level floats | constants.py | ✅ all 19 resolve, all `float`, values match payload JSONC exactly |
| excluded constants (CORNER_RADIUS/LEAD_IN/AXLE_ARM_WIDTH/AXLE_ARM_PROTRUSION) exist & are cosmetic/solid-internal | constants.py | ✅ all 4 exist (0.4/0.3/1.79/1.5); exclusion rationale holds |
| constants route fits through profile not constant | `:37-43`, `:86-89`, `:106-109` | ✅ pin-hole `:37-43`, axle-hole `:86-89`, clutch-tube `:106-109` all defer to ToleranceProfile |
| doc_pointer paths exist; `#tuning-tolerances` anchor resolves | docs/ | ✅ lego-technic.md / print-tolerances.md / screws.md all exist; `## Tuning Tolerances` at lego-technic.md:257 |
| `pyproject.toml` has exactly one runtime dep, no `[project.optional-dependencies]` | `:36-38` | ✅ `dependencies=["cadquery"]` `:36-38`; no optional-deps table (greenfield) |

**R1–R11 coverage check:** R1→Tests #1 (stdio smoke, no port); R2→#2/#3 (read JSON, no AST walk, determinism); R3→#4/#5 (payload shape + anti-drift); R4→#6/#7 (compile step/svg, temp dir, reuse export_previews); R5→#8 (packaging resolve-graph); R6→#9 (missing-extra hint); R7→#10/#11 (Layer A + Layer B); R8→#12 (contract snapshot); R9→#13 (error mapping, no traceback escape); R10→#14 (AGPL header + §13 note); R11→#15 (three-tier coverage). **All eleven map.** Each maps to a concrete file/location and an expected assertion. The "no Representative-Scale row owed" justification is correct (no model class, no `build.toml`, no full-build/boolean_diff path).

**Why APPROVE-WITH-CONDITIONS not APPROVE:** the four conditions are
implementation-ambiguity removals, not redesigns — a developer could currently
(1) void the SDK-decoupling guarantee by mis-placing unit tests, (2) guess the
stdio bootstrap shape and miss the snapshot fixture, (3) emit a malformed MCP
error content block, or (4) bypass the `resolve_solid` seam on the STEP/STL
path. All are one-to-three-sentence edits to the brief. None block the
architecture, which is sound.

### Re-confirmation (fresh context, 2026-06-18)

**Verdict: APPROVE**

Re-confirmation pass (not a fresh full review) of the four **TL** conditions
above. I opened each edited section of the design *body* (not the Round-7
summary) and confirmed every fix is real and in the location the condition
demanded; applying the conditions introduced no inconsistency with the rest of
the brief. Upgrading APPROVE-WITH-CONDITIONS → **APPROVE**.

> *Note on placement:* a sibling `### Re-confirmation (fresh context,
> 2026-06-18)` already exists under **§Independent Developer Review** (the
> Developer reviewer's pass on the Developer C1–C4). This subsection is the
> **TL** re-confirmation and is scoped to the TL conditions C1–C4; the two are
> distinguished by their parent `##` section, matching the parallel structure of
> the two review sections.

| TL Condition | Now addressed in (section cited) | ✓/✗ |
|---|---|---|
| **C1** — state the SDK-import direction the guard does NOT cover + name the test that does | §Module-layout note (internal SDK-free discipline of `tools.py`/`context.py`/`contract.py` "enforced by their unit tests importing them with `mcp` absent … not by the cross-package guard") **+** **T8** ("that is what *enforces* the SDK-free discipline … a stray top-level `import mcp` … fails test collection here … the unit-test import is the load-bearing enforcement") — both required locations | ✓ |
| **C2** — pin the stdio bootstrap symbols, or label them developer-owned | §Packaging+UX **SDK-surface caveat** (the `from mcp.server import Server` import path, the stdio-transport bootstrap, and the tool-registration API "pinned against the published `mcp>=1,<2` SDK docs, **not** import-grounded here"; first Phase-A act is `pip install -e ".[mcp]"` to probe, then update snippets if surface differs) **+** **T6** ("First verify the SDK surface live"). Ambiguity (developer chooses vs must match) resolved: doc-pinned + verify-at-impl | ✓ |
| **C3** — resolve the `isError` envelope ⇄ MCP content-type serialization | §Error-envelope **Serialization** paragraph (`content=[TextContent(type="text", text=json.dumps(payload))]` + `isError=True`; "the dict shapes shown throughout this design … are the JSON *inside* that one text block"; owned by `server.py`'s adapter, handlers return plain dicts) — covers both success and error envelopes with one documented serialization; consistent with §Data-&-Interface-Contracts and the Challenge-E seam | ✓ |
| **C4** — route STEP/STL through `resolve_solid` (not bare `.solid`) + record the no-`profile` decision | §Compile/preview tool (`step`/`stl` via `cq.exporters.export` on `model_loader.resolve_solid(instance)` `:196`, "**not** a bare `instance.solid`"; "**Recorded decision** … `compile_model` threads **no** `ToleranceProfile` … intentional, not an oversight to re-litigate at Phase B") **+** **T5** (same `resolve_solid` routing + no-`ToleranceProfile`). Consistent with R4 MUST-NOTs, Success Criterion 3, and the `compile_model` arg schema (no `profile` arg) | ✓ |

**Regression / consistency check:** no contradiction introduced. `resolve_solid`
routing aligns with the R4 MUST-NOTs and Success Criterion 3; the serialization
aligns with the Round-6 Challenge-E seam and its Known-Risks row; the
SDK-surface caveat aligns with Challenge F and its risk row; the
no-`ToleranceProfile` decision matches the `compile_model` arg schema (no
`profile` arg anywhere). The two original **non-blocking open concerns** (the
`ci.yml:79` license-header citation imprecision, and the "#5 pins type not
value" note) were *not* numbered conditions and remain as-is — correctly, since
both were explicitly "no change required / cost ~0"; they do not affect this
verdict.

---

## Independent Developer Review (fresh context, 2026-06-18)

**Verdict: APPROVE-WITH-CONDITIONS**

Reviewed from the implementer's chair: could I build this from the artifact
alone without guessing? Mostly yes — I opened `model_loader.py`, `preview.py`,
`print_settings.py`, `engine_api.json` (live), `constants.py`, `ci.yml`,
`pyproject.toml`, `check_no_main_blocks.py`, and `README.md`, and every reuse
seam, line citation, and wire-shape claim that *can* be checked in this
container holds. (An Independent TL Review already sits above; I reach the same
verdict but from the build-it lens, and I surface one finding it does not — the
profile-masking testability bug C1, which only shows up when you actually run
`get_profile(None)` on a calibrated host.) The conditions below are the spots
where a developer would otherwise have to guess at a value, a skip mechanism, or
an SDK call that is unverifiable here.

### Strengths (≤3)
1. **Reuse seams are real and line-exact.** `instantiate` (`model_loader.py:186`),
   `parse_params` (`:109`), the cast ladder (`:131-143`), the `load_class`
   typed-exception trio, "constructor exceptions propagate unchanged"
   (`:189-191`), and `export_previews(model_path, out_dir, params, views,
   quiet=True)` → `list[Path]` (`preview.py:222`/`:298`, `quiet` `:244-249`,
   unknown-view `ValueError` `:260-265`) all resolve verbatim, and the positional
   call order matches the real signature. The "sixth caller, not a
   re-implementer" posture is honest.
2. **Live wire-format verification, not doc-assumption.** I ran the producers:
   `engine_api.json` top keys are exactly `["classes","schema_version"]`,
   `schema_version="1.1"`, `classes` is a 70-element list, record keys are
   exactly the six the contract claims; and the container state matches
   Challenge F (`mcp` absent → `PackageNotFoundError`, `cadquery 2.7.0` present).
3. **Atomic, correctly-ordered plan.** T1–T12 each produce a concrete artifact
   with an R-mapping; the ordering (packaging + isolation guard before the
   SDK-importing files, T2 self-verifying green on the current tree) is exactly
   right, and every R1–R11 appears in a Tests-table "Maps to" cell.

### Conditions / required edits (numbered, each actionable)
1. **C1 — Env-neutralize the profile in any value-pinning context test (this is
   the finding the TL review does not have).** The §`get_design_context` payload
   example hardcodes `fdm_standard` leaves (`free.axial=0.10`, `slip.radial=0.05`,
   `slip.slot=0.10`), and Tests-row #4 asserts "profile fields match
   `get_profile()`". I ran `get_profile(None)` in this container: it returns
   `name="bambu_p1s"` with `free.axial=0.2`, `slip.radial=0.11`,
   `slip.slot=0.1125` — sourced from `.env` `PRINT_PROFILE="bambu_p1s"` +
   `print_profiles_user.json`. A test that byte-asserts the design's
   `fdm_standard` numbers therefore **fails on every calibrated contributor host
   and in any non-default env** (the exact class of failure the project memory
   and the 2026-06-01 visual-contract-freshness postmortem warn about). Fix:
   specify that the context test sets `os.environ["PRINT_PROFILE"] =
   "fdm_standard"` **before** importing `print_settings` (precedent:
   `check_visual_contract_freshness.py:102` does exactly this, before importing
   `preview`, for this identical reason), **or** that the test compares against a
   freshly-resolved `get_profile()` rather than literal leaf numbers. Also label
   the payload JSON example "shipped-default `fdm_standard`; live value reflects
   the resolved profile" so no implementer treats the example numbers as an
   invariant. (Anti-drift test #5 is profile-independent — no change.)
2. **C2 — Name the optional-dependency skip mechanism.** T8/T10/T11 and the
   `[CQ]` rows assume tests skip when `mcp`/`cadquery` is absent, but the repo has
   **no** existing `pytest.importorskip`/`skipif` usage and `pytest.ini`
   registers no markers (`testpaths = tests`, nothing else). State it: module-top
   `pytest.importorskip("mcp")` for the smoke (T10) and snapshot (T11) tests,
   `pytest.importorskip("cadquery")` (or `skipif`) for `[CQ]` rows #6/#7. Standard
   pytest, no new infra — but if left implicit, an unconditional `import mcp` at
   a test module top hard-fails *collection* in the no-`mcp` lint stage and turns
   the whole suite red there.
3. **C3 — First Phase-A act must verify the SDK surface against the live
   `mcp>=1,<2`, then update the brief's R6 snippet if it differs.** The
   missing-extra UX pins `from mcp.server import Server` and the stdio bootstrap
   is left as prose; neither is executable here (`mcp` confirmed absent). Per
   INSTRUCTIONS §4 Wire-Format Contract Verification, the developer must
   `pip install ".[mcp]"`, run a one-shot probe confirming the real import path,
   `Server` construction, the stdio-transport entry, and the tool-registration
   call shape, and write `server.py`/`__main__.py` against that — not against the
   placeholder. (Overlaps TL Condition 2; I keep it because it is the single
   highest-risk unverified surface and gates T6/T7/T10/T11.)
4. **C4 — Route the STEP/STL export through `resolve_solid`, and record the
   no-`profile`-arg decision.** `svg` correctly goes through `export_previews`;
   `step`/`stl` are described as "`cq.exporters.export` on `instance.solid`" — a
   new export call (the only one we add, uncited). To honor R4's "no
   solid-resolution re-derivation", resolve via
   `model_loader.resolve_solid(instance)` (`model_loader.py:196`), not a bare
   `instance.solid` attribute reach (which `AttributeError`s on a `.solid`-less
   class instead of giving the typed `ValueError`). Also state in one line that
   `compile_model` takes **no** `profile` arg — tolerance is whatever the class
   constructor resolves; a client wanting a specific fit passes it via `params`
   if the class exposes it — so the omission is a recorded decision, not an
   oversight re-litigated at Phase B. (Overlaps TL Condition 4; same fix.)

### Open concerns (non-blocking; predicted cost-of-failure)
- **O1 — `cq.exporters.export(shape, path, ExportTypes.STEP/STL)` is the one
  un-grounded call and needs a `.solid` vs `.val()` decision.** `export_previews`
  passes `instance.solid.val()` (a `cq.Shape`, `preview.py:270`); the design
  should say whether step/stl export passes the `Workplane` (`resolve_solid`
  return) or the `Shape` (`.val()`). *Cost if wrong:* low — CadQuery's STEP
  exporter accepts both, and `[CQ]` test #6 exercises the real path so a wrong
  enum/type fails in CI, not for an end user.
- **O2 — `__main__.py` with no `if __name__=="__main__":` guard is invisible to
  `check_no_main_blocks.py`.** Confirmed: that checker matches only the literal
  `If(__name__=="__main__")` AST node (`check_no_main_blocks.py:43-57`); a bare
  module body has none. *Cost:* zero — verified true; recorded so the implementer
  does not add a defensive guard out of habit and self-inflict a lint failure.
- **O3 — Tests-row #14 cites `ci.yml:79` as a standalone license-header step; it
  is the comment on the Build-smoke step.** Real enforcement is
  `check_license_headers.py` invoked inside `build.py`. *Cost:* ~0 — the new
  files fall under the scan regardless; only the citation is imprecise. (Same as
  TL open-concern 1.)

### Verification log (each claim I opened/ran and whether it held)
| # | Claim / signature | Cited loc | Held? |
|---|---|---|---|
| 1 | `instantiate(dotted, params)` | `model_loader.py:186` | ✅ `def instantiate(dotted, params=None)` at :186 |
| 2 | `parse_params(raw: list[str])` | `:109` | ✅ at :109 |
| 3 | cast ladder int→float→bool→str | `:130-143` | ✅ at :131-143 |
| 4 | `load_class` raises ValueError/ModuleNotFoundError/AttributeError | `:166-182` | ✅ ValueError :167, MNFE :175, AttributeError :179 |
| 5 | "constructor exceptions propagate unchanged" | `:189-191` | ✅ docstring :189-191 |
| 6 | `resolve_solid` seam exists (for C4) | `:196` (uncited in design) | ✅ `def resolve_solid(instance, *, missing="raise")` at :196 |
| 7 | stdlib-only at import; CadQuery only at `instantiate()` | `:73-79` | ✅ "CadQuery deferral" docstring; imports are `importlib`/`sys`/`pathlib`/`typing` only |
| 8 | `export_previews(model_path, out_dir, params, views, quiet=)` → `list[Path]` | `preview.py:222`,`:298` | ✅ signature :222; `return written` :298; positional order matches design's call |
| 9 | `quiet=True` suppresses `WROTE` | `:244-249` | ✅ docstring :244-249; `if not quiet: print` :295-296 |
| 10 | `export_previews` raises ValueError on unknown view | `:260-265` | ✅ at :260-265 |
| 11 | `get_profile(name=None)` | `print_settings.py:611` | ✅ at :611 |
| 12 | `ToleranceProfile`/`FitGrade` dataclass shapes | `:264-277`,`:241-261` | ✅ FitGrade(radial,axial,slot) :241-261; ToleranceProfile(name,free,slip,press) :264-277 |
| 13 | unknown profile → fdm_standard + stderr warning, label stays fdm_standard | `:633-649` | ✅ warning+fallback logic at :633-638 |
| 14 | **`get_profile(None)` yields the payload's `fdm_standard` values** | design payload JSONC | ❌ **FAILS on this host** — returns `bambu_p1s` (`free.axial=0.2`/`slip.radial=0.11`/`slip.slot=0.1125`) via `.env`+user file → **drives C1** |
| 15 | engine_api.json top keys + schema 1.1 + 70 classes | design reuse table | ✅ live: `["classes","schema_version"]`, `1.1`, len 70 |
| 16 | record fields fqn/name/module/doc/constructors/result_accessor | design `query_engine_class` result | ✅ exact six keys live |
| 17 | all 19 `CONTEXT_CONSTANTS` resolve + are `float`; 4 excluded names also exist | design allowlist | ✅ 19 found, all `: float`; excluded `CORNER_RADIUS`/`LEAD_IN`/`AXLE_ARM_WIDTH`/`AXLE_ARM_PROTRUSION` exist → exclusion deliberate, not masking typos |
| 18 | `check_no_main_blocks` shape (`find_violations` + exclude + repo-root) | design `:60`/`:89` | ✅ `find_violations(roots, exclude)` :60, repo-root :89, `exclude=[…/tools]` :97 |
| 19 | `ocp_vscode` allowlist grep idiom; main-block AST+grep twin | `ci.yml:62-73`/`:47-61` | ✅ ocp_vscode :62-73; check_no_main_blocks :48; grep twin :49-61; pytest :74-75 |
| 20 | `pyproject.toml`: one runtime dep, NO optional-deps table | design `:36-38` | ✅ `dependencies=["cadquery"]` :36-37; no `[project.optional-dependencies]` (greenfield) |
| 21 | README has a "Dev Setup" section for the quickstart line | design `README.md:50` | ✅ `## Dev Setup` at :50 |
| 22 | `mcp` absent / `cadquery` present (Challenge F) | design dialog F | ✅ `mcp`→`PackageNotFoundError`; `cadquery 2.7.0` |
| 23 | `__main__.py` (no guard) won't trip `check_no_main_blocks` | req line 47 | ✅ checker matches only literal `If(__name__=="__main__")` AST node (:43-57) |
| 24 | `from mcp.server import Server` + stdio/Server/registration API | design R6 snippet | ⚠ UNVERIFIABLE — `mcp` not installed; no SDK-facing line executed live → drives C3 |
| 25 | `cq.exporters.export` step/stl call | design compile path | ⚠ no line cited; SVG template at `preview.py:278-289` → O1 |
| 26 | optional-dep skip infra in repo | `pytest.ini`/`tests/` | ⚠ none exists (no `importorskip`/`skipif`, no markers) → drives C2 |
| 27 | Tests "Maps to" covers R1–R11; T1–T12 atomic/ordered | design Tests + Plan | ✅ R1(#1) R2(#2,#3) R3(#4,#5) R4(#6,#7) R5(#8) R6(#9) R7(#10,#11) R8(#12) R9(#13) R10(#14) R11(#15); plan ordering sound, T2 self-verifies |

### Re-confirmation (fresh context, 2026-06-18)

**Verdict: APPROVE**

Re-confirmation pass (not a fresh full review). All four conditions from the
Independent Developer Review above were applied to the design *body* in Round 7
and are now correctly and completely addressed; each fix is buildable as written
(not merely claimed). The two cheap code-grounding checks both hold live:
`model_loader.resolve_solid` is defined at `model_loader.py:196` (the seam C4
routes through), and `check_visual_contract_freshness.py:102` is the
`os.environ["PRINT_PROFILE"] = "fdm_standard"` line (the env-neutralization
precedent C1 cites). No applied condition contradicts another part of the plan
or makes any task non-buildable — C1's neutralization is scoped to value-pinning
tests and leaves the type-only anti-drift test #5 untouched; C3's "first Phase-A
act is `pip install -e \".[mcp]\"`" is consistent with the Challenge-F env matrix
and the T1-before-T6 ordering; C4's `resolve_solid` routing and no-`profile`
decision are consistent with R4 and §Out-of-Scope; C2's `pytest.importorskip`
gating adds no new infra and matches the CI-wiring table. Verdict upgrades to
APPROVE.

| Condition | Now addressed in | ✓/✗ |
|---|---|---|
| **C1** — env-neutralize profile in value-pinning context tests | Tests #4 ("sets `PRINT_PROFILE=fdm_standard` before importing `print_settings`", precedent `check_visual_contract_freshness.py:102`) **+** `get_design_context` §Result host-default note (payload is shipped-default `fdm_standard`; calibrated host is host-dependent by design; value-pinning tests MUST force the profile) | ✓ |
| **C2** — name the optional-dependency skip mechanism | Tests preamble (`pytest.importorskip("mcp")` for smoke #1/snapshot #12; `pytest.importorskip("cadquery")` for `[CQ]` #6/#7) **+** T8 (`importorskip("cadquery")`), T10 & T11 (`importorskip("mcp")`) | ✓ |
| **C3** — verify SDK surface live before T6/T7 | Packaging+UX SDK-surface caveat (symbols doc-pinned not import-grounded; first Phase-A act is `pip install -e ".[mcp]"` to probe the real API) **+** T6 ("First verify the SDK surface live … then build the SDK `Server`") | ✓ |
| **C4** — route STEP/STL through `model_loader.resolve_solid` + record no-`profile` decision | compile/preview tool § (`step`/`stl` via `cq.exporters.export` on `model_loader.resolve_solid(instance)` `:196`, never bare `.solid`; recorded "threads **no** `ToleranceProfile` … intentional, not an oversight to re-litigate at Phase B") **+** T5 (same `resolve_solid` routing + no-`ToleranceProfile`) | ✓ |

All four conditions satisfied; no regression found. Implementation may proceed.
