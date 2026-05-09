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

"""Shared STEP-analysis primitives for the ``tools/`` CLIs.

This module concentrates the small surface (`vec3`, `face_area`,
`load_step`) that was duplicated across seven STEP-analysis CLIs in
``tools/``.  It is intentionally placed at flat ``tools/step_primitives.py``
(NOT inside ``tools/engine_api/``): this module imports CadQuery and OCP
directly, while ``tools/engine_api/extractor.py`` is required to be
CadQuery-agnostic per ``.agents/plans/engine-api-json.md`` §1.  Physical
separation makes that invariant enforceable by inspection
(``grep -r "cadquery|from OCP" tools/engine_api/`` returns zero matches).

Public API
----------
``LoadedStep``
    NamedTuple of ``(wp, shape, occ_compound)`` returned by ``load_step``.
``StepLoadError``
    Raised on missing / empty STEP files.  Subclass of ``OSError`` so that
    consumers' broad ``except OSError:`` blocks catch it cleanly.
``load_step(path)``
    Imports a STEP file via ``cq.importers.importStep`` and returns a
    ``LoadedStep``.
``vec3(gp_obj)``
    Converts ``gp_Pnt`` / ``gp_Dir`` / ``gp_Vec`` to ``{x, y, z}`` rounded
    to 4 decimals.
``face_area(occ_face)``
    Surface area via ``BRepGProp.SurfaceProperties_s`` — un-rounded; callers
    apply their own rounding precision to keep historical JSON output stable.

This module imports only ``cadquery``, ``OCP.*``, and stdlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import cadquery as cq
import OCP.BRepGProp as bgp
import OCP.GProp as gprop


class StepLoadError(OSError):
    """Raised by :func:`load_step` on missing / empty STEP files.

    Subclass of :class:`OSError` (not :class:`RuntimeError`) so that
    consumers' broad ``except OSError:`` blocks catch this error cleanly —
    :class:`FileNotFoundError` is itself an :class:`OSError` subclass, so
    this places STEP-load failures in the standard I/O-error hierarchy
    where consumer file-handling code already catches.
    """


class LoadedStep(NamedTuple):
    """Triple returned by :func:`load_step` so each consumer reaches its
    preferred handle without re-deriving.

    Fields
    ------
    wp : cq.Workplane
        For tools that traverse via ``.faces().vals()`` or ``.solids().vals()``
        (CadQuery-style).
    shape : cq.Shape
        For tools that need ``.BoundingBox()`` or ``.wrapped`` directly
        (e.g. ``boolean_diff``).
    occ_compound : Any
        ``shape.wrapped`` — the underlying OCP top-level shape.  Expected
        runtime type is ``OCP.TopoDS.TopoDS_Compound``, but may also be
        ``TopoDS_Shape`` depending on STEP content; typed ``Any`` to match
        runtime variability without defeating IDE / mypy analysis.
        Consumed by tools that pass to ``TopExp_Explorer`` / ``BRepGProp``.
    """

    wp: cq.Workplane
    shape: cq.Shape
    occ_compound: Any


def load_step(path: str | Path) -> LoadedStep:
    """Load a STEP file and return a :class:`LoadedStep` triple.

    Parameters
    ----------
    path : str or Path
        Filesystem path to the ``.step`` / ``.stp`` file.

    Returns
    -------
    LoadedStep
        ``(wp, shape, occ_compound)`` — see :class:`LoadedStep` for field
        semantics.

    Raises
    ------
    StepLoadError
        If *path* does not exist, or if ``cq.importers.importStep``
        returns an empty / shape-less workplane (e.g. for a zero-byte
        ``.step`` file).  The message includes the offending path so CLI
        ``main()`` blocks can surface it to stderr and ``sys.exit(1)``.
    """
    p = Path(path)
    if not p.exists():
        raise StepLoadError(f"STEP file not found: {p}")

    try:
        wp = cq.importers.importStep(str(p))
    except Exception as exc:  # pragma: no cover — wrap any underlying load error
        raise StepLoadError(f"Failed to load STEP file {p}: {exc}") from exc

    shape = wp.val()
    if shape is None:
        raise StepLoadError(
            f"STEP file {p} loaded but contains no shape (empty / unreadable)"
        )

    occ_compound = shape.wrapped
    if occ_compound is None:
        raise StepLoadError(
            f"STEP file {p} loaded but underlying OCC shape is None"
        )

    return LoadedStep(wp=wp, shape=shape, occ_compound=occ_compound)


def vec3(gp_obj) -> dict:
    """Convert an OCP ``gp_Pnt`` / ``gp_Dir`` / ``gp_Vec`` to ``{x, y, z}``.

    Each component is rounded to 4 decimals.  The 4-decimal precision
    matches the historical contract of the seven CLI tools and is a hard
    constraint — changing it would alter their ``--json`` output.
    """
    return {
        "x": round(gp_obj.X(), 4),
        "y": round(gp_obj.Y(), 4),
        "z": round(gp_obj.Z(), 4),
    }


def face_area(occ_face) -> float:
    """Surface area of an OCC face.

    Returned **un-rounded**: callers round to whichever precision their
    historical JSON output dictates (e.g. ``face_catalog.py`` rounds to 4
    at the call-site; ``hole_finder.py`` rounds the *summed* area at the
    call-site).  Rounding here would force a single global precision and
    risk a one-byte JSON regression in any consumer that rounds
    differently.
    """
    props = gprop.GProp_GProps()
    bgp.BRepGProp.SurfaceProperties_s(occ_face, props)
    return props.Mass()
