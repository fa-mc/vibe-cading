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

    python3 tools/view.py rc.servo.sg90.Sg90Servo
    python3 tools/view.py rc.servo.sg90.Sg90Servo --params body_width=23.0
    python3 tools/view.py technic_ball_bearing.axle_sleeve.AxleSleeve \\
                          --params bearing_id=8.0 length=3.0

Multiple classes at once (shown side-by-side with automatic X offset)
----------------------------------------------------------------------
    python3 tools/view.py rc.servo.sg90.Sg90Servo \\
                          xlego.servos.shaft_crown.ShaftCrown

Assembly modules
----------------
Assembly modules live alongside the models they compose and expose a single
top-level ``assemble()`` function that returns a list of
``(solid, name, color)`` tuples.  Pass ``--assembly`` instead of a class path:

    python3 tools/view.py --assembly xlego.servos.shaft_saver_assembly

The module is imported and its ``assemble()`` function is called.  No class
instantiation is performed.

Arguments
---------
model [model ...]
    One or more dotted module.ClassName paths relative to ``models/``.

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

REPO_ROOT  = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"

# Make all model packages importable exactly as build.py does.
sys.path.insert(0, str(MODELS_DIR))

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


def _parse_params(raw: list[str]) -> dict[str, float | int | str]:
    result: dict[str, float | int | str] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"--params entries must be key=value, got: {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        try:
            result[k] = int(v)
        except ValueError:
            try:
                result[k] = float(v)
            except ValueError:
                result[k] = v
    return result


def _load_class(dotted: str):
    """Import and return the class at a dotted ``module.ClassName`` path."""
    module_str, class_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_str)
    return getattr(module, class_name)


def _solid_from_instance(instance):
    """Return the CadQuery solid for a model instance.

    Tries ``.solid`` first (the standard vibe-cading API), then falls back
    to returning the instance itself (for bare ``cq.Workplane`` factories).
    """
    if hasattr(instance, "solid"):
        return instance.solid
    return instance


def _export_step(solid, out_path: Path) -> None:
    """Write *solid* to a STEP file at *out_path*."""
    import cadquery as cq

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(solid.val() if hasattr(solid, "val") else solid, str(out_path))
    print(f"STEP     {out_path}")


def view_single(model_path: str, params: dict, reset: bool = True,
               export: Path | None = None) -> None:
    """Instantiate one model class and push it to the OCP viewer."""
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    cls      = _load_class(model_path)
    instance = cls(**params)
    solid    = _solid_from_instance(instance)
    class_name = model_path.rsplit(".", 1)[-1]

    if export:
        _export_step(solid, export)

    if reset:
        reset_show()

    show(solid, names=[class_name])
    print(f"Showing  {class_name}")


def view_multiple(model_paths: list[str], params: dict, reset: bool = True,
                  export: Path | None = None) -> None:
    """Instantiate several model classes and show them side-by-side.

    Parts are separated by their combined bounding-box width plus a small gap
    so they never overlap in the viewer.
    """
    import cadquery as cq
    from ocp_vscode import show, reset_show  # noqa: PLC0415

    solids: list      = []
    names:  list[str] = []
    colors: list[str] = []

    x_cursor = 0.0
    gap      = 5.0   # mm gap between adjacent parts

    for i, path in enumerate(model_paths):
        cls        = _load_class(path)
        instance   = cls(**params)
        solid      = _solid_from_instance(instance)
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
        import cadquery as cq
        merged = solids[0]
        for s in solids[1:]:
            merged = merged.union(s)
        _export_step(merged, export)

    if reset:
        reset_show()

    show(*solids, names=names, colors=colors)
    print(f"Showing  {', '.join(names)}")


def view_assembly(module_path: str, reset: bool = True,
                  export: Path | None = None) -> None:
    """Call ``assemble()`` on an assembly module and display the result.

    The assembly module must expose::

        def assemble() -> list[tuple[cq.Workplane, str, str]]:
            ...

    Each tuple is ``(solid, name, color)``.
    """
    from ocp_vscode import show, reset_show  # noqa: PLC0415

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
        import cadquery as cq
        merged = solids[0]
        for s in solids[1:]:
            merged = merged.union(s)
        _export_step(merged, export)

    if reset:
        reset_show()

    show(*solids, names=names, colors=colors)
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
        "--export",
        metavar="PATH",
        default=None,
        help=(
            "Also write a STEP file to PATH (e.g. tmp/HexWheelHub.step).  "
            "For multi-part views the solids are unioned into one file."
        ),
    )

    args        = parser.parse_args()
    params      = _parse_params(args.params or [])
    export_path = Path(args.export) if args.export else None

    if args.assembly:
        if args.models:
            parser.error("Cannot combine positional model paths with --assembly.")
        view_assembly(args.assembly, reset=args.reset, export=export_path)
    elif len(args.models) == 1:
        view_single(args.models[0], params, reset=args.reset, export=export_path)
    elif len(args.models) > 1:
        view_multiple(args.models, params, reset=args.reset, export=export_path)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
