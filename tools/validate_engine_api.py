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

#!/usr/bin/env python3
"""Validate ``engine_api.json`` against the schema invariants in §5 of
``.agents/plans/engine-api-json.md``.

Pure stdlib — no ``jsonschema`` dependency. Imports the pinned
``SCHEMA_VERSION`` constant from the extractor so version bumps are
mechanically forced to land in lockstep with the generator.

Returns 0 on success, 1 on any structural failure. ``result_accessor =
null`` triggers a stderr warning listing the offending FQNs but does
*not* fail the run; per brief §2 step 4 those are maintenance issues to
audit, not blockers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Same sys.path shim as ``gen_engine_api.py`` so direct invocation works.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.engine_api.extractor import SCHEMA_VERSION  # noqa: E402

_VALID_KINDS = {"init", "classmethod", "factory"}
# Allowed values for a param's ``units`` field. ``None`` means "no unit
# inferred"; any string must be one of the canonical short codes below.
# Constrained defensively to catch typos in the extractor's inference
# table (e.g. a stray ``"mmm"`` would otherwise pass schema validation).
_VALID_UNIT_STRINGS = {"mm", "deg"}


def _fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def _validate_param(
    param: object, *, ctor_label: str, errors: list[str]
) -> None:
    if not isinstance(param, dict):
        _fail(errors, f"{ctor_label}: param entry is not a dict")
        return
    for key, expected_type in (("name", str), ("type", str), ("required", bool)):
        if key not in param:
            _fail(errors, f"{ctor_label}: param missing required key '{key}'")
            continue
        if not isinstance(param[key], expected_type):
            _fail(
                errors,
                f"{ctor_label}: param '{key}' has wrong type "
                f"(expected {expected_type.__name__})",
            )
    name = param.get("name", "<unknown>")
    if "units" not in param:
        _fail(errors, f"{ctor_label}.{name}: missing 'units' key")
    else:
        units = param["units"]
        if units is not None and not isinstance(units, str):
            _fail(errors, f"{ctor_label}.{name}: 'units' must be string or null")
        elif isinstance(units, str) and units not in _VALID_UNIT_STRINGS:
            _fail(
                errors,
                f"{ctor_label}.{name}: 'units' must be one of "
                f"{sorted(_VALID_UNIT_STRINGS)} or null (got {units!r})",
            )

    required = param.get("required")
    has_default_key = "default" in param
    if required is True and has_default_key:
        _fail(
            errors,
            f"{ctor_label}.{name}: 'default' must be absent when required is true",
        )
    if required is False and not has_default_key:
        _fail(
            errors,
            f"{ctor_label}.{name}: 'default' must be present when required is false",
        )

    _validate_allowed_values(param, ctor_label=ctor_label, name=name, errors=errors)


def _strip_one_quote_layer(default: str) -> str:
    """Strip one layer of source-literal quoting from an ``ast.unparse`` default.

    ``ast.unparse`` of a string default produces a quoted source literal —
    e.g. ``"slip"`` round-trips as the 6-char string ``"'slip'"``.  The
    ``allowed_values`` members are bare strings (``"slip"``), so the
    membership check must strip exactly one matching pair of surrounding
    quotes (``'…'`` or ``"…"``) before comparing.  A default that is not a
    quoted string literal (e.g. ``None``, a number) is returned unchanged.
    """
    if len(default) >= 2 and default[0] == default[-1] and default[0] in ("'", '"'):
        return default[1:-1]
    return default


def _validate_allowed_values(
    param: dict, *, ctor_label: str, name: str, errors: list[str]
) -> None:
    """Schema 1.1 assertions for ``allowed_values`` / ``value_doc`` (R7/R8).

    R7a — ``allowed_values`` (when non-null) is a non-empty list.
    R7b — every ``allowed_values`` entry is a string (the 1.1 in-scope set).
    R8a — when both ``default`` and ``allowed_values`` are present, the
          quote-stripped default is a member of ``allowed_values``
          (a ``None``/null default is exempt).
    R8b — ``value_doc`` keys are a subset of ``allowed_values``.
    R8c — ``value_doc`` MUST be null when ``allowed_values`` is null.
    """
    label = f"{ctor_label}.{name}"
    allowed = param.get("allowed_values", "<missing>")
    value_doc = param.get("value_doc", "<missing>")

    if allowed == "<missing>":
        _fail(errors, f"{label}: missing 'allowed_values' key (schema 1.1)")
        allowed = None
    if value_doc == "<missing>":
        _fail(errors, f"{label}: missing 'value_doc' key (schema 1.1)")
        value_doc = None

    if allowed is not None:
        # R7a — non-empty list.
        if not isinstance(allowed, list):
            _fail(errors, f"{label}: 'allowed_values' must be a list or null")
            return
        if not allowed:
            _fail(
                errors,
                f"{label}: 'allowed_values' must be non-empty when present "
                "(use null for free-form params)",
            )
            return
        # R7b — every entry is a string.
        if not all(isinstance(v, str) for v in allowed):
            _fail(
                errors,
                f"{label}: every 'allowed_values' entry must be a string "
                "(1.1 in-scope set)",
            )
        # R8a — quote-stripped default ∈ allowed_values (None/null exempt).
        default = param.get("default")
        if isinstance(default, str):
            stripped = _strip_one_quote_layer(default)
            if stripped != "None" and stripped not in allowed:
                _fail(
                    errors,
                    f"{label}: default {default!r} (stripped {stripped!r}) "
                    f"not in allowed_values {allowed}",
                )
        # R8b — value_doc keys ⊆ allowed_values.
        if isinstance(value_doc, dict):
            stray = [k for k in value_doc if k not in allowed]
            if stray:
                _fail(
                    errors,
                    f"{label}: value_doc keys {sorted(stray)} not in "
                    f"allowed_values {allowed}",
                )
        elif value_doc is not None:
            _fail(errors, f"{label}: 'value_doc' must be a dict or null")
    else:
        # R8c — value_doc must be null when allowed_values is null.
        if value_doc is not None:
            _fail(
                errors,
                f"{label}: 'value_doc' must be null when 'allowed_values' "
                "is null",
            )


def _validate_constructor(
    ctor: object, *, class_fqn: str, errors: list[str]
) -> None:
    if not isinstance(ctor, dict):
        _fail(errors, f"{class_fqn}: constructor entry is not a dict")
        return
    kind = ctor.get("kind")
    if not isinstance(kind, str) or kind not in _VALID_KINDS:
        _fail(
            errors,
            f"{class_fqn}: constructor 'kind' must be one of {sorted(_VALID_KINDS)} "
            f"(got {kind!r})",
        )
    name = ctor.get("name")
    if not isinstance(name, str) or not name:
        _fail(errors, f"{class_fqn}: constructor 'name' must be non-empty string")
    params = ctor.get("params")
    if not isinstance(params, list):
        _fail(errors, f"{class_fqn}.{name}: 'params' must be a list")
        return
    for param in params:
        _validate_param(param, ctor_label=f"{class_fqn}.{name}", errors=errors)


def _validate_class(record: object, *, errors: list[str]) -> str | None:
    """Validate a single class record. Returns its FQN when present."""
    if not isinstance(record, dict):
        _fail(errors, "class entry is not a dict")
        return None
    module = record.get("module")
    name = record.get("name")
    fqn = record.get("fqn")
    for key, value in (("module", module), ("name", name), ("fqn", fqn)):
        if not isinstance(value, str) or not value:
            _fail(errors, f"class {fqn!r}: '{key}' must be non-empty string")
    if isinstance(module, str) and isinstance(name, str) and isinstance(fqn, str):
        if fqn != f"{module}.{name}":
            _fail(
                errors,
                f"class {fqn}: fqn must equal '{module}.{name}'",
            )
    constructors = record.get("constructors")
    if not isinstance(constructors, list) or not constructors:
        _fail(errors, f"class {fqn}: 'constructors' must be a non-empty list")
    else:
        for ctor in constructors:
            _validate_constructor(
                ctor, class_fqn=fqn if isinstance(fqn, str) else "<unknown>",
                errors=errors,
            )
    accessor = record.get("result_accessor", "<missing>")
    if accessor == "<missing>":
        _fail(errors, f"class {fqn}: missing 'result_accessor' key")
    elif accessor is None:
        # Warning — handled by the caller (needs the FQN list to print
        # one consolidated message). No failure.
        pass
    elif not isinstance(accessor, str) or not accessor.startswith("."):
        _fail(
            errors,
            f"class {fqn}: 'result_accessor' must be null or a string "
            f"starting with '.' (got {accessor!r})",
        )
    return fqn if isinstance(fqn, str) else None


def validate(payload: object) -> tuple[list[str], list[str]]:
    """Run schema checks. Returns (errors, null_accessor_fqns)."""
    errors: list[str] = []
    null_accessors: list[str] = []

    if not isinstance(payload, dict):
        _fail(errors, "top-level JSON must be an object")
        return errors, null_accessors

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        _fail(errors, "'schema_version' must be a non-empty string")
    elif schema_version != SCHEMA_VERSION:
        _fail(
            errors,
            f"'schema_version' mismatch: expected {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}. Bump the extractor's SCHEMA_VERSION "
            "in lockstep when updating the schema.",
        )

    classes = payload.get("classes")
    if not isinstance(classes, list):
        _fail(errors, "'classes' must be a list")
        return errors, null_accessors
    if not classes:
        _fail(errors, "'classes' is empty — extractor produced no records")

    seen: dict[str, int] = {}
    for record in classes:
        fqn = _validate_class(record, errors=errors)
        if fqn is None:
            continue
        seen[fqn] = seen.get(fqn, 0) + 1
        if isinstance(record, dict) and record.get("result_accessor") is None:
            null_accessors.append(fqn)

    duplicates = sorted(fqn for fqn, count in seen.items() if count > 1)
    for fqn in duplicates:
        _fail(errors, f"duplicate fqn: {fqn}")

    return errors, null_accessors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate engine_api.json against schema invariants.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=_REPO_ROOT / "engine_api.json",
        help="Path to engine_api.json (default: <repo>/engine_api.json).",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"engine_api.json not found at {args.path}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"engine_api.json is not valid JSON: {exc}", file=sys.stderr)
        return 1

    errors, null_accessors = validate(payload)

    if null_accessors:
        print(
            "warning: classes with null result_accessor (audit recommended): "
            + ", ".join(sorted(null_accessors)),
            file=sys.stderr,
        )

    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    n_classes = len(payload.get("classes", []))
    print(
        f"engine_api.json OK — schema_version={SCHEMA_VERSION}, {n_classes} classes",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
