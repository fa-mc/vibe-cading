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
"""
OCP CAD Viewer entry point for vibe-cading model classes.

Model class files must never import ``ocp_vscode`` or contain
``if __name__ == "__main__":`` viewer blocks.  Run this script instead to
push any model (or assembly) to the OCP CAD Viewer panel in VS Code.

Single-class usage
------------------
    python3 tools/view.py <module.path.ClassName> [--params key=value ...]

    python3 tools/view.py vibe_cading.rc.servo.sg90.Sg90Servo
    python3 tools/view.py vibe_cading.rc.servo.sg90.Sg90Servo --params body_width=23.0
    python3 tools/view.py vibe_cading.mechanical.bearings.Bearing \\
                          --params inner_diameter=8.0 outer_diameter=22.0 thickness=7.0

Multiple classes at once (shown side-by-side with automatic X offset)
----------------------------------------------------------------------
    python3 tools/view.py vibe_cading.rc.servo.sg90.Sg90Servo \\
                          vibe_cading.lego_adapters.servos.shaft_crown.ShaftCrown

Class-scoped demos
------------------
A class may opt into a richer demonstration by defining::

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        ...

Each returned tuple is ``(solid, name, color)`` — same shape as
``assemble()``.  Trigger via ``--demo``::

    python3 tools/view.py vibe_cading.mechanical.screws.metric.MetricMachineScrew --demo

``--params key=value`` is forwarded as ``**kwargs``; demos that don't read
parameters simply ignore them.  See ``vibe/INSTRUCTIONS.md`` § "OCP Viewer
— Dedicated Entry Point" for the convention contract.

Assembly modules
----------------
Assembly modules live alongside the models they compose and expose a single
top-level ``assemble()`` function that returns a list of
``(solid, name, color)`` tuples.  Pass ``--assembly`` instead of a class path:

    python3 tools/view.py --assembly vibe_cading.lego_adapters.servos.sg90.servo_mount

The module is imported and its ``assemble()`` function is called.  No class
instantiation is performed.

Arguments
---------
model [model ...]
    One or more dotted module.ClassName paths under the
    ``vibe_cading.`` or ``parts.`` packages.

--assembly
    Treat the sole positional argument as an assembly module path whose
    ``assemble()`` function returns ``[(solid, name, color), ...]``.

--params key=value ...
    Optional constructor keyword arguments forwarded to every class listed
    (all values auto-cast to int, float, or string in that order).

--reset
    Call ``reset_show()`` before displaying, clearing the viewer panel.  This
    is the default for single-class invocations; pass ``--no-reset`` to
    accumulate shapes across multiple calls.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent

# tools/model_loader.py owns sys.path management.  Add REPO_ROOT here so the
# ``from tools.model_loader import …`` line below resolves; the loader then
# inserts REPO_ROOT idempotently for downstream model imports.
sys.path.insert(0, str(REPO_ROOT))
from vibe_cading.tools.model_loader import (  # noqa: E402
    ensure_models_on_path,
    instantiate,
    load_class,
    parse_params,
    resolve_solid,
)

# ── Default display colours for multi-model side-by-side view ─────────────────
_PALETTE = [
    "royalblue",
    "gold",
    "tomato",
    "seagreen",
    "mediumpurple",
    "coral",
    "steelblue",
    "khaki",
]


def _export_step(solid, out_path: Path) -> None:
    """Write *solid* to a STEP file at *out_path*."""
    import cadquery as cq

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(solid.val() if hasattr(solid, "val") else solid, str(out_path))
    print(f"STEP     {out_path}")


def _prepare_shape(solid):
    """If a Workplane wraps a Compound shape, extract the shape so ocp_vscode can tessellate it."""
    import cadquery as cq
    if isinstance(solid, cq.Workplane):
        try:
            val = solid.val()
            if isinstance(val, cq.Compound):
                return val
        except Exception:
            pass
    return solid



def view_single(model_path: str, params: dict, reset: bool = True,
               export: Path | None = None) -> None:
    """Instantiate one model class and push it to the OCP viewer."""
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    instance = instantiate(model_path, params)
    # ``missing='instance'`` preserves the bare-``cq.Workplane`` fallback
    # documented in this tool's history.
    solid    = resolve_solid(instance, missing="instance")
    class_name = model_path.rsplit(".", 1)[-1]

    if export:
        _export_step(solid, export)

    if reset:
        reset_show()

    show(_prepare_shape(solid), names=[class_name])
    print(f"Showing  {class_name}")


def view_multiple(model_paths: list[str], params: dict, reset: bool = True,
                  export: Path | None = None) -> None:
    """Instantiate several model classes and show them side-by-side.

    Parts are separated by their combined bounding-box width plus a small gap
    so they never overlap in the viewer.
    """
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    solids: list      = []
    names:  list[str] = []
    colors: list[str] = []

    x_cursor = 0.0
    gap      = 5.0   # mm gap between adjacent parts

    for i, path in enumerate(model_paths):
        instance   = instantiate(path, params)
        solid      = resolve_solid(instance, missing="instance")
        class_name = path.rsplit(".", 1)[-1]

        # Compute bounding box to determine x-offset for the next part.
        bb    = solid.val().BoundingBox()
        width = bb.xmax - bb.xmin

        if x_cursor != 0.0:
            solid = solid.translate((x_cursor - bb.xmin, 0, 0))

        x_cursor += width + gap

        solids.append(solid)
        names.append(class_name)
        colors.append(_PALETTE[i % len(_PALETTE)])

    if export:
        # For multi-model exports, union all parts and write a single STEP.
        merged = solids[0]
        for s in solids[1:]:
            merged = merged.union(s)
        _export_step(merged, export)

    if reset:
        reset_show()

    prepared_solids = [_prepare_shape(s) for s in solids]
    show(*prepared_solids, names=names, colors=colors)
    print(f"Showing  {', '.join(names)}")


def view_demo(model_path: str, params: dict, reset: bool = True,
              export: Path | None = None) -> None:
    """Invoke ``<ClassName>.demo()`` and render the returned tuples.

    The class must define::

        @classmethod
        def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
            ...

    Each tuple is ``(solid, name, color)`` — the same shape consumed by
    :func:`view_assembly`.  ``--params key=value`` is forwarded as ``**kwargs``
    so demos that don't read parameters simply ignore the keyword arguments.

    Like :func:`view_assembly`, this function shares ``_export_step`` and
    ``_PALETTE`` with the rest of the module but keeps its dispatch path
    parallel — class-scoped demos and module-scoped assemblies have
    different ownership shapes (see design doc R-B / *Alternatives rejected
    #2*).
    """
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    cls = load_class(model_path)
    if not hasattr(cls, "demo"):
        raise AttributeError(
            f"{model_path} has no demo() classmethod. "
            "Run without --demo for a single-solid view, "
            "or add a `@classmethod def demo(cls, **kwargs)` to the class."
        )

    parts = cls.demo(**(params or {}))
    if not parts:
        raise ValueError(
            f"{model_path}.demo() returned no parts; expected "
            "list[tuple[Workplane, str, str]]."
        )

    solids = [p[0] for p in parts]
    names  = [p[1] for p in parts]
    colors = [p[2] for p in parts]

    if export:
        merged = solids[0]
        for s in solids[1:]:
            merged = merged.union(s)
        _export_step(merged, export)

    if reset:
        reset_show()

    prepared_solids = [_prepare_shape(s) for s in solids]
    show(*prepared_solids, names=names, colors=colors)
    print(f"Showing demo  {model_path}  ({len(parts)} parts)")


def view_assembly(module_path: str, reset: bool = True,
                  export: Path | None = None) -> None:
    """Call ``assemble()`` on an assembly module and display the result.

    The assembly module must expose::

        def assemble() -> list[tuple[cq.Workplane, str, str]]:
            ...

    Each tuple is ``(solid, name, color)``.

    Note: this path intentionally does NOT delegate to
    ``tools.model_loader``.  The loader's contract is single-class
    instantiation returning ``(instance, solid)``; assembly modules return
    a list of labelled tuples and have no class.  Promoting this to
    ``model_loader.load_assembly`` is reversible — see design risk R-E.
    """
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    ensure_models_on_path()
    module = importlib.import_module(module_path)
    if not hasattr(module, "assemble"):
        raise AttributeError(
            f"Assembly module '{module_path}' must define an "
            "`assemble()` function returning [(solid, name, color), ...]"
        )

    parts = module.assemble()

    solids = [p[0] for p in parts]
    names  = [p[1] for p in parts]
    colors = [p[2] for p in parts]

    if export:
        merged = solids[0]
        for s in solids[1:]:
            merged = merged.union(s)
        _export_step(merged, export)

    if reset:
        reset_show()

    prepared_solids = [_prepare_shape(s) for s in solids]
    show(*prepared_solids, names=names, colors=colors)
    print(f"Showing assembly  {module_path}  ({len(parts)} parts)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Push a CadQuery model class (or assembly) to the OCP CAD Viewer."
        ),
    )
    parser.add_argument(
        "models",
        nargs="*",
        metavar="module.path.ClassName",
        help=(
            "One or more dotted module.ClassName paths relative to models/.  "
            "E.g.  rc.servo.sg90.Sg90Servo"
        ),
    )
    parser.add_argument(
        "--assembly",
        metavar="module.path",
        help=(
            "Assembly module path.  The module must expose an assemble() "
            "function returning [(solid, name, color), ...]."
        ),
    )
    parser.add_argument(
        "--params",
        nargs="*",
        default=[],
        metavar="key=value",
        help="Constructor keyword arguments forwarded to every class listed.",
    )
    parser.add_argument(
        "--reset",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Clear the viewer before showing (default: on).  "
            "Use --no-reset to accumulate shapes across calls."
        ),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help=(
            "Invoke <ClassName>.demo(**params) on the single positional "
            "model and render the returned [(solid, name, color), ...] "
            "tuples.  Class must define a `@classmethod def demo(cls, "
            "**kwargs)`.  See vibe/INSTRUCTIONS.md."
        ),
    )
    parser.add_argument(
        "--export",
        metavar="PATH",
        default=None,
        help=(
            "Also write a STEP file to PATH (e.g. tmp/HexWheelHub.step).  "
            "For multi-part views the solids are unioned into one file."
        ),
    )

    args        = parser.parse_args()
    params      = parse_params(args.params or [])
    export_path = Path(args.export) if args.export else None

    if args.assembly:
        if args.models:
            parser.error("Cannot combine positional model paths with --assembly.")
        if args.demo:
            parser.error("--demo cannot be combined with --assembly.")
        view_assembly(args.assembly, reset=args.reset, export=export_path)
    elif args.demo:
        if len(args.models) != 1:
            parser.error("--demo requires exactly one positional model path.")
        view_demo(args.models[0], params, reset=args.reset, export=export_path)
    elif len(args.models) == 1:
        view_single(args.models[0], params, reset=args.reset, export=export_path)
    elif len(args.models) > 1:
        view_multiple(args.models, params, reset=args.reset, export=export_path)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
