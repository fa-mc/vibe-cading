# MCP interface — `vibe-cading-engine`

Vibe-cading ships an optional **MCP (Model Context Protocol) server** that exposes
the CAD engine to an LLM client (Claude Code, Claude Desktop, Cursor, or any MCP
client). It lets a model **introspect** the engine's model classes, read the
**live design context** (tolerance profile + Lego/Technic nominals + doc
pointers), and **compile** a model class to STEP/STL/SVG on your machine — all
over a local stdio transport.

This page is the canonical, user-facing reference. The implementation lives under
[`../vibe_cading/mcp/`](../vibe_cading/mcp/); the design rationale is in the
[RFC #41 design plan](design_plans/2026-06-18-mcp-subpackage_design.md).

| | |
|---|---|
| **Server name** | `vibe-cading-engine` |
| **Tool-contract version** | `1.0` |
| **Transport** | MCP **stdio** (JSON-RPC on stdin/stdout) — no network listener, no port, no API key |
| **Trust model** | single-tenant, local-trust (the client and server run on the same machine) |
| **Launch** | `python3 -m vibe_cading.mcp` |
| **Install** | `pip install -e ".[mcp]"` (optional extra — see below) |

---

## Install

The `mcp` SDK is an **opt-in extra**. A plain `pip install vibe_cading` (or
`pip install -e .`) does **not** pull it in, so library-only consumers never pay
its dependency weight (the SDK drags `starlette` / `uvicorn` / `pydantic`).

```bash
pip install -e ".[mcp]"
```

If you launch the server without the extra installed, it prints one actionable
line and exits non-zero — never a traceback:

```
The MCP interface requires the optional 'mcp' extra.
Install it with:  pip install -e ".[mcp]"
```

> In the dev container, the system `python3` is the right interpreter — run the
> `pip install -e ".[mcp]"` once inside the container.

---

## Launch

```bash
python3 -m vibe_cading.mcp
```

This serves the four engine tools over stdio and blocks until the client
disconnects. There is nothing to configure on the server side — no port, no
config file, no credentials.

---

## Connect a client

An MCP client launches the server as a subprocess and speaks JSON-RPC over its
stdio. Point the client's `command` at an interpreter where the `[mcp]` extra is
installed, with the repo importable on `sys.path` (the editable install handles
this). If the client runs from a different working directory, set `cwd` to your
clone.

### Generic MCP client

```json
{
  "mcpServers": {
    "vibe-cading-engine": {
      "command": "python3",
      "args": ["-m", "vibe_cading.mcp"],
      "cwd": "/path/to/vibe-cading"
    }
  }
}
```

### Claude Code

```bash
claude mcp add vibe-cading-engine -- python3 -m vibe_cading.mcp
```

Or commit a project-scoped [`.mcp.json`](https://docs.claude.com/en/docs/claude-code/mcp)
at the repo root with the `mcpServers` block above so collaborators inherit it.

### Claude Desktop

Add the `mcpServers` block above to `claude_desktop_config.json` (macOS:
`~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`), then
restart the app. Use an absolute interpreter path (e.g. the venv/conda `python`
that has the `[mcp]` extra) plus `cwd` if the engine is not importable from the
default Python.

---

## Tools

The server registers four tools. Every result is a single JSON object (see
[Response & error envelope](#response--error-envelope)); every result echoes
`tool_contract_version` so a client can detect a surface change.

### 1. `list_engine_classes`

List the engine's model classes from the committed
[`engine_api.json`](design_plans/engine-api-json.md) (deterministic — it reads
the committed contract, it does **not** re-walk the AST).

**Arguments** (all optional):

| Arg | Type | Effect |
|---|---|---|
| `module_prefix` | string | Keep classes whose `fqn` or `module` starts with this prefix (e.g. `vibe_cading.mechanical`). |
| `name_contains` | string | Keep classes whose short name contains this substring (case-insensitive). |

**Result:**

```json
{
  "tool_contract_version": "1.0",
  "engine_api_schema_version": "<from engine_api.json>",
  "count": 2,
  "classes": [
    {
      "fqn": "vibe_cading.mechanical.screws.metric.MetricMachineScrew",
      "name": "MetricMachineScrew",
      "module": "vibe_cading.mechanical.screws.metric",
      "doc_summary": "<first line of the class docstring>"
    }
  ]
}
```

### 2. `query_engine_class`

Return the **full** class record (fqn, name, module, doc, constructors, result
accessor — the schema documented in
[`engine-api-json.md`](design_plans/engine-api-json.md)) for one class.

**Arguments:**

| Arg | Type | Effect |
|---|---|---|
| `class_key` | string **(required)** | The class to look up. Matched against `fqn` first; falls back to the short name when the key has no `.` (or when `match="short"`). |
| `match` | `"exact"` \| `"short"` | Default `"exact"`. `"short"` forces short-name matching. |

Lookup is **exact, never fuzzy.** A short name shared by more than one class
returns an `ambiguous_class` error listing the candidate fqns rather than
silently picking one; a miss returns `class_not_found`.

**Result:**

```json
{
  "tool_contract_version": "1.0",
  "engine_api_schema_version": "<from engine_api.json>",
  "class": { "fqn": "...", "name": "...", "doc": "...", "constructors": [], "...": "..." }
}
```

### 3. `get_design_context`

Return a **curated, versioned** aggregate a model author needs to place geometry
on the 8 mm stud grid: the **live tolerance profile**, a **curated allowlist of
real-Lego nominal constants** (read live from
[`vibe_cading/lego/constants.py`](../vibe_cading/lego/constants.py)), and **doc
pointers** (path + anchor — never inlined prose).

**Arguments** (optional):

| Arg | Type | Effect |
|---|---|---|
| `profile` | string | Tolerance-profile name (e.g. `fdm_standard`). Absent ⇒ the resolved default, which honours `.env` `PRINT_PROFILE` / `print_profiles_user.json`. An unknown name resolves to `fdm_standard`; the returned `tolerance_profile.name` reflects the *resolved* profile so a typo is visible. |

**Result:**

```json
{
  "tool_contract_version": "1.0",
  "schema_version": "1.1",
  "tolerance_profile": {
    "name": "fdm_standard",
    "free":  { "radial": 0.0, "axial": 0.0, "slot": 0.0 },
    "slip":  { "radial": 0.0, "axial": 0.0, "slot": 0.0 },
    "press": { "radial": 0.0, "axial": 0.0, "slot": 0.0 }
  },
  "constants": { "STUD_PITCH": 8.0, "BEAM_THICKNESS": 7.2, "...": 0.0 },
  "doc_pointers": [
    { "topic": "Lego Technic dimensions", "path": "docs/lego-technic.md", "anchor": null }
  ]
}
```

> **`tolerance_profile` is host-dependent by design.** On a calibrated host,
> `get_design_context` with no `profile` returns *that host's* profile (e.g.
> `bambu_p1s`), not the shipped `fdm_standard`. Pass `profile` explicitly for a
> reproducible answer. The `constants` block, by contrast, is host-independent
> (real-Lego nominals).

The curated constant set covers the grid/stud, Technic pin-hole, beam, axle,
axle-hole, and Studded-System block nominals. It is an explicit allowlist (not a
reflection sweep) guarded by an anti-drift test, so the payload can never quietly
rot into a lie.

### 4. `compile_model`

Compile a model class **on the local machine** and return artifact **file
paths** (the client opens them off the local filesystem).

**Arguments:**

| Arg | Type | Effect |
|---|---|---|
| `class_path` | string **(required)** | Dotted `module.ClassName` of the model to compile. |
| `params` | object | Constructor kwargs as a JSON object, e.g. `{"length_in_studs": 5}`. Cast through the same ladder as the CLI (`int → float → bool → str`). |
| `outputs` | array of `"step"` \| `"stl"` \| `"svg"` | Formats to produce. Default `["step"]`. |
| `views` | array of string | View names for `svg` output (e.g. `iso_ne`, `top`, `front`). Default `["iso_ne"]`. Only used when `svg` is in `outputs`. |
| `return_inline` | boolean | Opt-in inline SVG text in the result (SVG only, under a 256 KiB cap). Default `false`. STEP/STL are **never** inlined. |

**Result:**

```json
{
  "tool_contract_version": "1.0",
  "artifacts": [
    { "format": "step", "path": "/tmp/vibe_cading_mcp_ab12cd/MetricMachineScrew.step" },
    { "format": "svg", "view": "iso_ne", "path": "/tmp/vibe_cading_mcp_ab12cd/MetricMachineScrew_iso_ne.svg" }
  ]
}
```

With `return_inline: true`, an SVG artifact under the 256 KiB cap also carries an
`"inline"` field with the SVG text; one over the cap carries
`"note": "svg exceeded inline cap; path-only"` and is path-only.

> **Notes.**
> - Artifacts are written under a `vibe_cading_mcp_*` directory in the OS temp
>   root (never the repo tree). Cleanup is left to the OS temp reaper so the
>   returned path is still valid when the client opens it.
> - `compile_model` threads **no** tolerance profile — the model class resolves
>   its own tolerance (via `get_profile` / `.env`). To compile at a specific fit,
>   pass it through `params` if the class exposes such a parameter.

---

## Response & error envelope

Every tool returns an MCP `CallToolResult` whose `content` is a **single text
block** holding `json.dumps(payload)`. The `isError` flag distinguishes the two
shapes:

- **Success** — `isError: false`; the text is the tool's result object (the
  shapes shown above).
- **Error** — `isError: true`; the text is a structured envelope:

  ```json
  { "error_code": "class_not_found", "message": "No class matching 'Foo'", "detail": "Foo" }
  ```

A Python traceback **never** escapes as a transport crash — every failure, even a
novel OCCT one, is converted to this envelope.

| `error_code` | Raised when |
|---|---|
| `bad_params` | A required argument is missing, or an argument has the wrong type / an unknown output format. |
| `bad_class_path` | `compile_model` `class_path` is not a dotted `module.ClassName`. |
| `module_not_found` | `compile_model` could not import the named module. |
| `class_not_found` | The class / attribute does not exist (also a `query_engine_class` miss). |
| `ambiguous_class` | `query_engine_class` short name matches more than one class (`detail` lists the fqns). |
| `model_error` | The model raised while resolving its solid (e.g. no `.solid`). |
| `bad_view` | `compile_model` got an unknown SVG view name. |
| `compile_failed` | CadQuery/OCCT failed during export (also the last-resort catch-all for any unexpected exception). |
| `unknown_tool` | The client called a tool name the server does not register. |

---

## Versioning

The server carries three independent version fields so a client can detect
exactly what changed:

| Field | Versions | Appears on |
|---|---|---|
| `tool_contract_version` (`1.0`) | The **tool surface** — names, argument schemas, result shapes. | Every result. |
| `engine_api_schema_version` | The **class-record schema** that introspection reads. | `list_engine_classes`, `query_engine_class`. |
| `schema_version` (`1.1`) | The **`get_design_context` payload** shape. | `get_design_context`. |

Each follows the same additive-vs-breaking discipline: an **additive** change
(new optional arg with a default, new tool, new result field, new constant in the
allowlist) bumps the **minor**; a **breaking** change (rename/remove a tool or
arg, change a type or required-ness, change a field's meaning) bumps the
**major**. See [`contract.py`](../vibe_cading/mcp/contract.py) for the policy.

---

## Design & licensing notes

- **Deterministic introspection.** `list_engine_classes` / `query_engine_class`
  read the committed `engine_api.json`, kept fresh by CI's `gen_engine_api.py
  --check` gate — they never re-walk the AST, so the same commit always yields
  the same answer.
- **Import isolation.** The `mcp` SDK is confined to two files
  (`__main__.py`, `server.py`); the tool/context/contract modules are SDK-free
  and CadQuery-free at import. A CI guard
  ([`check_mcp_import_isolation.py`](../vibe_cading/tools/check_mcp_import_isolation.py))
  enforces this so a plain `import vibe_cading` never drags the SDK.
- **AGPL §13.** The stdio transport is intentionally **not** an AGPL §13
  network-interaction surface (no network listener, single-tenant local trust).
  Adding any HTTP/SSE/WebSocket transport *would* engage §13 and require a
  Corresponding-Source offer to remote users — do not add one without that
  licensing call.

**Further reading:** [requirements](design_plans/2026-06-18-mcp-subpackage_req.md)
· [design](design_plans/2026-06-18-mcp-subpackage_design.md)
· [TL architectural assessment](design_plans/2026-06-17-mcp-subpackage_rfc-tl-assessment.md)
· [`engine_api.json` contract](design_plans/engine-api-json.md)
