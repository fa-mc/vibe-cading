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

"""
Shared model-class loader for vibe-cading CLI tools.

This module concentrates the duplicated dotted-path → class → instance →
``.solid`` resolution logic, the ``--params key=value`` parser, and the
``sys.path`` insertion that ``build.py``, ``tools/preview.py``,
``tools/view.py``, ``tools/check_topology.py``, and
``tools/check_polar_monotonicity.py`` previously each carried inline.

Public API
----------

- ``ensure_models_on_path()`` — idempotently insert REPO_ROOT and MODELS_DIR
  at ``sys.path[0]``.  See *sys.path contract* below for why both are
  required.
- ``parse_params(raw)`` — parse ``['k=v', ...]`` to a kwargs dict, casting
  values in the order int → float → bool (``'true'`` / ``'false'``,
  case-insensitive) → str.
- ``load_class(dotted)`` — resolve ``'module.path.ClassName'`` to a class
  object.
- ``instantiate(dotted, params)`` — load the class and call ``cls(**params)``,
  returning the instance.
- ``resolve_solid(instance, missing=...)`` — return ``instance.solid`` or
  fall back per the ``missing=`` policy.
- ``load_solid(dotted, params, missing=...)`` — convenience composite of
  ``instantiate`` + ``resolve_solid``; returns ``(instance, solid)``.

sys.path contract
-----------------

``ensure_models_on_path()`` inserts a single path — the repo root — on
``sys.path`` so that fully-qualified dotted paths resolve.  After the
Phase 1 rename (`.agents/plans/2026-05-13-pre-oss-models-structure_design.md`)
every ``[[build]] model = …`` entry in ``build.toml`` is fully namespaced
(``vibe_cading.*``, ``parts.*``, or ``experiments.*``) — bare imports like
``technic_ball_bearing.axle_sleeve.AxleSleeve`` are no longer used and the
old ``MODELS_DIR`` insertion would only act as a shadow-import hazard.

``--params`` cast order
-----------------------

The parser tries each cast in this order, returning the first one that
succeeds, except that the bool branch matches only the literal
case-insensitive strings ``'true'`` / ``'false'``:

1. ``int`` — ``'1'``, ``'-7'`` → ``int``
2. ``float`` — ``'2.5'``, ``'1e3'`` → ``float``
3. ``bool`` — ``'true'`` / ``'TRUE'`` → ``True``; ``'false'`` / ``'False'``
   → ``False``.  Anything else falls through.
4. ``str`` — fallback.

``check_topology.py`` previously had a ``true`` / ``false`` bool branch in
its inline parser; preserving it here means the loader's contract is a
strict superset of the prior per-tool parsers (``view.py`` and
``preview.py`` cast int → float → str, both subsumed).

CadQuery deferral (R4)
----------------------

This module imports only the standard library at module-load time.
CadQuery is pulled in transitively only when ``instantiate()`` actually
imports a model module.  A future caller that wants metadata only can use
``load_class()`` without ``instantiate()`` and avoid the CadQuery import
cost entirely.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_models_on_path() -> None:
    """Insert ``REPO_ROOT`` at ``sys.path[0]`` if not already present.

    Idempotent: calling repeatedly has no effect once the path is on
    ``sys.path``.  Comparison is on the resolved string form so a duplicate
    insertion via a different relative spelling is still detected.

    Only the repo root is inserted — the post-Phase-1 ``build.toml`` exclusively
    uses fully-qualified namespaces (``vibe_cading.*``, ``parts.*``,
    ``experiments.*``), all of which resolve from the repo root alone.  No
    bare-import ``models/`` shadow needs to be on the path.
    """
    repo_str = str(REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def parse_params(raw: list[str]) -> dict[str, Any]:
    """Parse ``['k=v', 'k2=v2']`` into ``{'k': v, 'k2': v2}``.

    Each value is auto-cast in the order int → float → bool → str.  See the
    module docstring for the exact bool-branch contract (``'true'`` /
    ``'false'`` only, case-insensitive).

    Raises
    ------
    ValueError
        If any entry is missing the ``=`` separator.
    """
    result: dict[str, Any] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(
                f"--params entries must be key=value, got: {item!r}"
            )
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        # int → float → bool ('true'/'false', case-insensitive) → str
        try:
            cast: Any = int(v)
        except ValueError:
            try:
                cast = float(v)
            except ValueError:
                low = v.lower()
                if low == "true":
                    cast = True
                elif low == "false":
                    cast = False
                else:
                    cast = v
        result[k] = cast
    return result


def load_class(dotted: str) -> type:
    """Resolve ``'module.path.ClassName'`` to a class object.

    Performs the dual-path ``sys.path`` insertion before importing so the
    target module resolves regardless of the caller's cwd.

    Raises
    ------
    ValueError
        If *dotted* contains no ``'.'`` (cannot be split into
        module + class).
    ModuleNotFoundError
        If the module portion cannot be imported.  The exception message
        embeds *dotted* so failures are self-diagnosing.
    AttributeError
        If the module imports successfully but does not expose the named
        class.  The exception message embeds *dotted*.
    """
    if "." not in dotted:
        raise ValueError(
            f"load_class() expects a 'module.ClassName' path, got: {dotted!r}"
        )
    ensure_models_on_path()
    module_path, class_name = dotted.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"Could not import module for {dotted!r}: {exc}"
        ) from exc
    if not hasattr(module, class_name):
        raise AttributeError(
            f"Module {module_path!r} has no attribute {class_name!r} "
            f"(while resolving {dotted!r})"
        )
    return getattr(module, class_name)


def instantiate(dotted: str, params: dict[str, Any] | None = None) -> Any:
    """Load the class at *dotted* and call ``cls(**(params or {}))``.

    Returns the constructed instance.  Constructor exceptions propagate
    unchanged so callers preserve their existing failure semantics.
    """
    cls = load_class(dotted)
    return cls(**(params or {}))


def resolve_solid(instance: Any, *, missing: str = "raise") -> Any:
    """Return ``instance.solid`` if present; otherwise fall back per *missing*.

    Parameters
    ----------
    instance:
        The object returned by ``instantiate``.
    missing:
        Policy for instances that lack a ``.solid`` attribute:

        - ``'raise'`` *(default)* — raise ``ValueError``.  Matches the
          strict-by-default behavior of ``build.py`` and
          ``check_polar_monotonicity.py``.
        - ``'instance'`` — return *instance* unchanged.  Semantic name:
          *"return the loaded object as-is; let the caller decide what to
          do with a non-Solid result"*.  Used by ``view.py`` (bare
          ``cq.Workplane`` fallback) and ``check_topology.py`` (which
          performs its own ``isinstance(instance, cq.Workplane)`` check
          on the returned value).
        - ``'none'`` — return ``None``.  Caller decides downstream.
    """
    if hasattr(instance, "solid"):
        return instance.solid
    if missing == "raise":
        raise ValueError(
            f"Instance of {type(instance).__name__!r} has no '.solid' attribute"
        )
    if missing == "instance":
        return instance
    if missing == "none":
        return None
    raise ValueError(
        f"resolve_solid: unknown missing policy {missing!r} "
        "(expected 'raise', 'instance', or 'none')"
    )


def load_solid(
    dotted: str,
    params: dict[str, Any] | None = None,
    *,
    missing: str = "raise",
) -> tuple[Any, Any]:
    """Convenience: ``instantiate(...)`` + ``resolve_solid(...)``.

    Returns
    -------
    tuple[Any, Any]
        ``(instance, solid_or_fallback)``.  The first element is always
        the constructed instance; the second is whatever ``resolve_solid``
        returns under the selected *missing* policy.
    """
    instance = instantiate(dotted, params)
    solid = resolve_solid(instance, missing=missing)
    return instance, solid
