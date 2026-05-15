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
Topological validation tool for CadQuery models and STEP files.
Detects disconnected geometric bodies (floating artifacts, un-merged unions).
"""

import sys
import os
import argparse
import cadquery as cq

# tools/model_loader.py owns sys.path management.  Add REPO_ROOT here so the
# ``from tools.model_loader import …`` resolves; the loader then inserts
# REPO_ROOT + MODELS_DIR idempotently for the model imports below.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.model_loader import instantiate, parse_params  # noqa: E402


def load_target(target: str, kwargs: dict) -> cq.Workplane:
    if target.lower().endswith(('.step', '.stp')):
        return cq.importers.importStep(target)

    parts = target.split(".")
    if len(parts) < 2:
        print("Error: Target must be a .step file or a python module path (e.g. vibe_cading.lego.gears.Gear)", file=sys.stderr)
        sys.exit(1)

    class_name = parts[-1]

    try:
        instance = instantiate(target, kwargs)
    except ModuleNotFoundError as e:
        print(f"Error loading module {'.'.join(parts[:-1])}: {e}", file=sys.stderr)
        sys.exit(1)
    except AttributeError:
        print(f"Error: Class {class_name} not found in {'.'.join(parts[:-1])}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error instantiating {target}: {e}", file=sys.stderr)
        raise e

    if hasattr(instance, "solid"):
        return instance.solid
    elif isinstance(instance, cq.Workplane):
        return instance
    else:
        print(f"Error: Instance of {class_name} has no '.solid' property and is not a Workplane.", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    parser = argparse.ArgumentParser(description="Check CAD topology for disconnected floating bodies.")
    parser.add_argument("target", help="Module path (vibe_cading.pkg.Class) or .step file")
    parser.add_argument("--params", nargs="*", help="key=value constructor args for python classes", default=[])
    parser.add_argument("--export", action="store_true", help="Export floating bodies to tmp/ as STEP files if found")
    parser.add_argument("--ignore", type=int, default=0, help="Allow exactly N disconnected bodies if intentional (default: 0)")
    
    args = parser.parse_args()

    # Parse kwargs.  ``tools.model_loader.parse_params`` skips entries with
    # no ``=`` by raising; preserve the legacy "skip silently" behavior here
    # by filtering before delegating, since the legacy parser used
    # ``continue`` on missing ``=``.
    kwargs = parse_params([p for p in args.params if "=" in p])

    # ``tools.model_loader.instantiate`` calls ``ensure_models_on_path``
    # internally, so no explicit sys.path mutation is needed here.

    print(f"Loading '{args.target}'...")
    workplane = load_target(args.target, kwargs)
    
    solids = workplane.solids().vals()
    num_solids = len(solids)
    
    if num_solids == 0:
        print("ERROR: Result contains no solids at all (empty geometry).")
        sys.exit(1)
        
    expected_solids = args.ignore + 1
    
    if num_solids > expected_solids:
        print(f"\n[FAIL] Topological Error: Found {num_solids} disconnected solid bodies (expected {expected_solids}).")
        print("This typically indicates floating artifacts, failed boolean cuts, or un-merged outer components.")
        print("\nBreakdown by Volume:")
        
        # Sort by volume descending
        sorted_solids = sorted(enumerate(solids, 1), key=lambda x: x[1].Volume(), reverse=True)
        
        for idx, solid in sorted_solids:
            vol = solid.Volume()
            print(f"  Solid {idx}: {vol:10.2f} mm³")
            if args.export:
                out_path = f"tmp/topology_error_{args.target.split('.')[-1]}_body_{idx}.step"
                cq.exporters.export(cq.Workplane(solid), out_path)
                print(f"    -> Exported: {out_path}")
        sys.exit(1)
    else:
        print(f"\n[PASS] Topology is contiguous. Found {num_solids} solid(s).")
        sys.exit(0)

if __name__ == "__main__":
    main()
