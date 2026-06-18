# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# vibe-cading is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""The four SDK-free MCP tool handlers + their JSON-schemas (R2/R3/R4/R9).

Each handler is a plain ``def handler(args: dict) -> dict`` paired with a plain
``*_SCHEMA`` JSON-schema dict (no ``mcp`` SDK types).  ``server.py`` iterates the
``TOOLS`` registry and wraps each handler in a thin closure that binds the SDK
content/``isError`` envelope around the plain-dict return / raised exception.
The SDK types live *only* in ``server.py``'s closure — this module imports
nothing from ``mcp``, so the handlers are unit-testable without standing up an
MCP session.

The discipline that this module (and ``context.py`` / ``contract.py``) stays
SDK-free is **enforced by the unit tests importing it with ``mcp`` absent** (the
no-``mcp`` lint stage): a stray top-level ``import mcp`` here would fail test
*collection* there.  The cross-package AST guard does NOT cover this direction —
this subtree is inside its carve-out.

Lazy-import discipline (R4)
---------------------------
``model_loader`` / ``preview`` / ``cadquery`` are imported **lazily inside the
handlers that need them**, never at module top, so importing
``vibe_cading.mcp.tools`` for a unit test does not drag CadQuery.  ``json`` /
``tempfile`` / ``pathlib`` are stdlib and import-cheap, so they sit at module
top.

Errors
------
Handlers raise :class:`_ToolError` (carrying ``error_code`` / ``message`` /
``detail``) for the *documented* error cases; ``server.py`` converts both
``_ToolError`` and any unexpected exception into the structured MCP error
envelope.  Handlers return plain ``dict`` payloads on success.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from vibe_cading.mcp.contract import TOOL_CONTRACT_VERSION

# SVG text may be returned inline only under this byte cap; STEP/STL are never
# inlined (binary base64 bloats the JSON-RPC frame).  256 KiB.
MAX_INLINE_SVG_BYTES = 256 * 1024

# Namespaced temp-dir prefix so compile artifacts are greppable/sweepable and
# never touch the repo tree.  Cleanup is deferred to the OS temp reaper, NOT
# eager-deleted: the file-path return contract requires the file to still exist
# when the (local) client opens it, so eager cleanup would race the client and
# hand back a dangling path.
_TEMP_PREFIX = "vibe_cading_mcp_"


class _ToolError(Exception):
    """A handled, structured tool error (becomes ``isError`` in ``server.py``).

    Carries the wire fields of the error envelope: ``error_code`` (a stable
    machine token), ``message`` (human-readable), and optional ``detail``.

    Underscore-prefixed (package-internal): clients never see this Python type —
    ``server.py`` converts it into the JSON ``{error_code, message, detail}``
    wire envelope before anything crosses the transport.  The ``_`` also keeps
    the ``engine_api`` AST extractor (which catalogs every *public* class under
    ``vibe_cading/**``) from mis-cataloging this infra exception as a model
    class.
    """

    def __init__(self, error_code: str, message: str, detail: str | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.detail = detail

    def to_payload(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


# --------------------------------------------------------------------------
# engine_api.json access (R2) — read the committed contract, never AST-walk.
# --------------------------------------------------------------------------

# engine_api.json lives next to the vibe_cading package root
# (vibe_cading/engine_api.json).  This module is vibe_cading/mcp/tools.py, so
# the package root is the parent of this file's parent.
_ENGINE_API_PATH = Path(__file__).resolve().parent.parent / "engine_api.json"


def _load_engine_api() -> dict[str, Any]:
    """Read and parse the committed ``engine_api.json`` (R2).

    Deterministic: same file ⇒ same dict.  Never re-walks the AST — the JSON is
    kept fresh by ``gen_engine_api.py --check`` in CI; the MCP tools ride that
    gate.
    """
    with _ENGINE_API_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _class_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Project a full class record down to the index summary fields."""
    doc = record.get("doc") or ""
    first_line = doc.strip().splitlines()[0] if doc.strip() else ""
    return {
        "fqn": record.get("fqn"),
        "name": record.get("name"),
        "module": record.get("module"),
        "doc_summary": first_line,
    }


# --------------------------------------------------------------------------
# Tool 1: list_engine_classes (R2)
# --------------------------------------------------------------------------

LIST_ENGINE_CLASSES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "module_prefix": {
            "type": "string",
            "description": (
                "Filter to classes whose fqn or module starts with this prefix "
                "(e.g. 'vibe_cading.mechanical')."
            ),
        },
        "name_contains": {
            "type": "string",
            "description": (
                "Filter to classes whose short name contains this substring "
                "(case-insensitive)."
            ),
        },
    },
    "additionalProperties": False,
}


def list_engine_classes(args: dict[str, Any]) -> dict[str, Any]:
    """Return the class index from the committed ``engine_api.json`` (R2).

    Optional filters ``module_prefix`` (startswith on fqn/module) and
    ``name_contains`` (case-insensitive substring on the short name).  Both
    absent ⇒ the full index.  Deterministic: same JSON ⇒ same output.
    """
    api = _load_engine_api()
    classes = api.get("classes", [])

    module_prefix = args.get("module_prefix")
    name_contains = args.get("name_contains")

    if module_prefix:
        classes = [
            c
            for c in classes
            if str(c.get("fqn", "")).startswith(module_prefix)
            or str(c.get("module", "")).startswith(module_prefix)
        ]
    if name_contains:
        needle = name_contains.lower()
        classes = [c for c in classes if needle in str(c.get("name", "")).lower()]

    summaries = [_class_summary(c) for c in classes]
    return {
        "tool_contract_version": TOOL_CONTRACT_VERSION,
        "engine_api_schema_version": api.get("schema_version"),
        "count": len(summaries),
        "classes": summaries,
    }


# --------------------------------------------------------------------------
# Tool 2: query_engine_class (R2)
# --------------------------------------------------------------------------

QUERY_ENGINE_CLASS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "class_key": {
            "type": "string",
            "description": (
                "The class to look up.  Matched against fqn first (exact); if "
                "match='short' or the key has no '.', falls back to the short "
                "class name."
            ),
        },
        "match": {
            "type": "string",
            "enum": ["exact", "short"],
            "default": "exact",
            "description": (
                "'exact' matches fqn (with short-name fallback when the key has "
                "no dot); 'short' forces short-name matching."
            ),
        },
    },
    "required": ["class_key"],
    "additionalProperties": False,
}


def query_engine_class(args: dict[str, Any]) -> dict[str, Any]:
    """Return the full class record for ``class_key`` (R2).

    Lookup is **exact, not fuzzy**.  ``class_key`` matches ``fqn`` first.  If
    ``match='short'`` OR the key contains no ``.``, it falls back to matching the
    short ``name``; an *ambiguous* short name (>1 class shares it) returns an
    ``ambiguous_class`` error listing the candidate fqns rather than silently
    picking one.  A miss returns ``class_not_found``.
    """
    class_key = args.get("class_key")
    if not class_key:
        raise _ToolError(
            "bad_params",
            "query_engine_class requires a non-empty 'class_key'",
            repr(class_key),
        )
    match = args.get("match", "exact")

    api = _load_engine_api()
    classes = api.get("classes", [])

    def _wrap(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool_contract_version": TOOL_CONTRACT_VERSION,
            "engine_api_schema_version": api.get("schema_version"),
            "class": record,
        }

    # fqn-exact path (default, unless caller forces short matching)
    if match != "short":
        for c in classes:
            if c.get("fqn") == class_key:
                return _wrap(c)

    # short-name fallback: forced by match='short', or when the key has no dot,
    # or when no fqn matched above.
    short_matches = [c for c in classes if c.get("name") == class_key]
    if len(short_matches) == 1:
        return _wrap(short_matches[0])
    if len(short_matches) > 1:
        candidates = sorted(str(c.get("fqn")) for c in short_matches)
        raise _ToolError(
            "ambiguous_class",
            f"Short name '{class_key}' is ambiguous ({len(candidates)} classes)",
            ", ".join(candidates),
        )

    raise _ToolError(
        "class_not_found",
        f"No class matching '{class_key}'",
        class_key,
    )


# --------------------------------------------------------------------------
# Tool 3: get_design_context (R3)
# --------------------------------------------------------------------------

GET_DESIGN_CONTEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "profile": {
            "type": "string",
            "description": (
                "Optional tolerance-profile name (e.g. 'fdm_standard'); absent "
                "⇒ the resolved default (honours .env PRINT_PROFILE)."
            ),
        },
    },
    "additionalProperties": False,
}


def get_design_context(args: dict[str, Any]) -> dict[str, Any]:
    """Return the curated design-context aggregate (R3).

    Live tolerance profile + curated constant allowlist + doc pointers, wrapped
    with ``tool_contract_version``.  Delegates to ``context.get_design_context``
    (the aggregation logic + the curated allowlist live there; this handler is a
    thin adapter that adds the contract-version envelope).
    """
    # Lazy import keeps the handler module SDK-free *and* defers even the
    # constants/print_settings import until a context call actually happens.
    from vibe_cading.mcp.context import get_design_context as _aggregate

    payload = _aggregate(args.get("profile"))
    return {"tool_contract_version": TOOL_CONTRACT_VERSION, **payload}


# --------------------------------------------------------------------------
# Tool 4: compile_model (R4)
# --------------------------------------------------------------------------

COMPILE_MODEL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "class_path": {
            "type": "string",
            "description": "Dotted 'module.ClassName' path of the model to compile.",
        },
        "params": {
            "type": "object",
            "description": "Constructor kwargs as a JSON object (e.g. {\"length_in_studs\": 5}).",
        },
        "outputs": {
            "type": "array",
            "items": {"type": "string", "enum": ["step", "stl", "svg"]},
            "description": "Artifact formats to produce. Defaults to [\"step\"].",
        },
        "views": {
            "type": "array",
            "items": {"type": "string"},
            "description": "View names for svg output (used only when 'svg' in outputs). Defaults to [\"iso_ne\"].",
        },
        "return_inline": {
            "type": "boolean",
            "description": "Opt-in inline SVG text (svg only, under a 256 KiB cap). Defaults to false.",
        },
    },
    "required": ["class_path"],
    "additionalProperties": False,
}


def _params_object_to_kv(params: dict[str, Any]) -> list[str]:
    """Normalize a JSON params object to ``model_loader.parse_params``' k=v form.

    Encoding decision (design OQ2): the MCP arg is the idiomatic native JSON
    object (``{"length_in_studs": 5}``), but we route it through
    ``parse_params`` so the exact int→float→bool→str cast ladder is
    single-sourced in ``model_loader`` rather than re-derived here.  Each value
    is stringified; ``parse_params`` then re-casts it through the canonical
    ladder.
    """
    return [f"{k}={v}" for k, v in params.items()]


def compile_model(args: dict[str, Any]) -> dict[str, Any]:
    """Compile a model on the local machine, returning artifact file paths (R4).

    Reuses ``model_loader.instantiate`` / ``parse_params`` and
    ``preview.export_previews(quiet=True)``; re-derives **no** param-parsing,
    ``sys.path`` handling, or solid resolution.  STEP/STL are exported via
    ``cq.exporters.export`` on ``model_loader.resolve_solid(instance)`` — the
    one ``cq.exporters`` call this layer adds, and only for the binary formats
    ``export_previews`` does not produce; SVG always routes through
    ``export_previews``.

    Tolerance posture: ``compile_model`` threads **no** ``ToleranceProfile``.
    Tolerance is whatever the model class constructor resolves on its own (via
    ``get_profile`` / ``.env``); a client wanting a specific fit passes it via
    ``params`` if the class exposes it.  This omission is intentional.

    Artifacts are written under ``tempfile.mkdtemp(prefix="vibe_cading_mcp_")``
    (the OS temp root, never the repo tree).  Cleanup is deferred to the OS temp
    reaper because the file-path return contract requires the file to outlive
    the call (eager delete would race the local client opening the path).
    """
    class_path = args.get("class_path")
    if not class_path:
        raise _ToolError(
            "bad_params",
            "compile_model requires a non-empty 'class_path'",
            repr(class_path),
        )

    params_obj = args.get("params") or {}
    if not isinstance(params_obj, dict):
        raise _ToolError(
            "bad_params",
            "compile_model 'params' must be a JSON object",
            repr(params_obj),
        )
    outputs = args.get("outputs") or ["step"]
    views = args.get("views") or ["iso_ne"]
    return_inline = bool(args.get("return_inline", False))

    unknown_formats = [o for o in outputs if o not in ("step", "stl", "svg")]
    if unknown_formats:
        raise _ToolError(
            "bad_params",
            f"Unknown output format(s): {unknown_formats}",
            "valid formats: step, stl, svg",
        )

    # Lazy imports — keep tools.py import SDK-free AND CadQuery-free at module
    # load; CadQuery is pulled in here, only when a compile actually runs.
    import cadquery as cq

    from vibe_cading.tools import model_loader, preview

    # ---- param-parsing (reuse parse_params' cast ladder; no re-derivation) ---
    try:
        params = model_loader.parse_params(_params_object_to_kv(params_obj))
    except ValueError as exc:
        raise _ToolError("bad_params", f"Invalid params: {exc}", str(exc)) from exc

    out_dir = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    artifacts: list[dict[str, Any]] = []

    # ---- instantiate (let model_loader own dotted-path resolution) ----------
    try:
        instance = model_loader.instantiate(class_path, params)
    except ValueError as exc:
        # load_class raises ValueError for a path with no '.'
        raise _ToolError(
            "bad_class_path",
            "class_path must be 'module.ClassName'",
            class_path,
        ) from exc
    except ModuleNotFoundError as exc:
        raise _ToolError(
            "module_not_found",
            f"Could not import module for {class_path!r}",
            str(exc),
        ) from exc
    except AttributeError as exc:
        raise _ToolError(
            "class_not_found",
            f"Module has no such class for {class_path!r}",
            str(exc),
        ) from exc
    except TypeError as exc:
        # constructor rejected the kwargs (unexpected / missing)
        raise _ToolError(
            "bad_params",
            f"Constructor rejected params: {exc}",
            str(exc),
        ) from exc

    class_name = class_path.rsplit(".", 1)[-1]

    # ---- STEP / STL via resolve_solid (NOT a bare .solid; R4 MUST-NOT) -------
    binary_formats = [o for o in outputs if o in ("step", "stl")]
    if binary_formats:
        try:
            solid = model_loader.resolve_solid(instance)
        except ValueError as exc:
            # instance has no .solid attribute
            raise _ToolError(
                "model_error",
                f"Model raised while resolving solid: {exc}",
                str(exc),
            ) from exc

        export_map = {
            "step": cq.exporters.ExportTypes.STEP,
            "stl": cq.exporters.ExportTypes.STL,
        }
        suffix_map = {"step": "step", "stl": "stl"}
        for fmt in binary_formats:
            path = out_dir / f"{class_name}.{suffix_map[fmt]}"
            try:
                cq.exporters.export(solid, str(path), export_map[fmt])
            except Exception as exc:  # noqa: BLE001 — broad catch-all is intentional
                # Any OCCT/CadQuery export failure becomes a clean tool error,
                # never a stdio crash.
                raise _ToolError(
                    "compile_failed",
                    "CadQuery failed during compile",
                    f"{type(exc).__name__}: {exc}",
                ) from exc
            artifacts.append({"format": fmt, "path": str(path)})

    # ---- SVG via export_previews(quiet=True) (reuse; no cq.exporters dup) ----
    if "svg" in outputs:
        try:
            written = preview.export_previews(
                class_path, out_dir, params, views, quiet=True
            )
        except ValueError as exc:
            # export_previews raises ValueError on an unknown view name.
            raise _ToolError("bad_view", f"Unknown view(s): {exc}", str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — broad catch-all is intentional
            raise _ToolError(
                "compile_failed",
                "CadQuery failed during compile",
                f"{type(exc).__name__}: {exc}",
            ) from exc

        # export_previews writes "<ClassName>_<view>.svg"; recover the view from
        # the filename so the artifact carries the right "view" field.
        for svg_path in written:
            view = svg_path.stem[len(class_name) + 1:]  # strip "<ClassName>_"
            artifact: dict[str, Any] = {
                "format": "svg",
                "view": view,
                "path": str(svg_path),
            }
            if return_inline:
                size = svg_path.stat().st_size
                if size <= MAX_INLINE_SVG_BYTES:
                    artifact["inline"] = svg_path.read_text(encoding="utf-8")
                else:
                    artifact["note"] = "svg exceeded inline cap; path-only"
            artifacts.append(artifact)

    return {
        "tool_contract_version": TOOL_CONTRACT_VERSION,
        "artifacts": artifacts,
    }


# --------------------------------------------------------------------------
# Tool registry — consumed by server.py to register the SDK tools.
# Each entry: (name, handler, schema, one-line description).
# --------------------------------------------------------------------------

# Type alias for a handler: plain dict in, plain dict out (SDK-free).
ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]

TOOLS: tuple[tuple[str, ToolHandler, dict[str, Any], str], ...] = (
    (
        "list_engine_classes",
        list_engine_classes,
        LIST_ENGINE_CLASSES_SCHEMA,
        "List the engine's model classes (from the committed engine_api.json), "
        "with optional module-prefix / name-substring filters.",
    ),
    (
        "query_engine_class",
        query_engine_class,
        QUERY_ENGINE_CLASS_SCHEMA,
        "Return the full record (constructors, doc, result accessor) for one "
        "engine class by fqn or short name.",
    ),
    (
        "get_design_context",
        get_design_context,
        GET_DESIGN_CONTEXT_SCHEMA,
        "Return the live tolerance profile, curated Lego/Technic nominal "
        "constants, and documentation pointers.",
    ),
    (
        "compile_model",
        compile_model,
        COMPILE_MODEL_SCHEMA,
        "Compile a model class locally to STEP/STL/SVG artifact files (and "
        "optional inline SVG text).",
    ),
)
