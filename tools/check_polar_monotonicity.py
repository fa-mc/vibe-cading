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

import sys
import math
from pathlib import Path

# tools/model_loader.py owns sys.path management.  Add REPO_ROOT here so the
# ``from tools.model_loader import …`` resolves; ``load_class`` then inserts
# REPO_ROOT + MODELS_DIR idempotently for the model imports below.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.model_loader import load_class  # noqa: E402


def analyze_profile(pts, tolerance=-0.01):
    print(f"Analyzing {len(pts)} points...")
    prev_th = None
    backward_count = 0
    for i, p in enumerate(pts):
        th = math.degrees(math.atan2(p[1], p[0]))
        # Unwrap negative values for smooth transition
        while prev_th is not None and th - prev_th < -180:
            th += 360
        while prev_th is not None and th - prev_th > 180:
            th -= 360

        if prev_th is not None:
            dth = th - prev_th
            if dth < tolerance:
                print(f"❌ BACKWARD LOOP DETECTED: index {i}, th: {prev_th:.2f}° -> {th:.2f}° (Δ={dth:.2f}°, r={math.hypot(p[0], p[1]):.2f})")
                backward_count += 1
        prev_th = th
    
    if backward_count == 0:
        print("✅ SUCCESS: Profile is strictly monotonic in polar angle (no backward hooks).")
    else:
        print(f"❌ FAILURE: {backward_count} backward sequence(s) found. This will create jagged geometric hooks.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_polar_monotonicity.py models.module.ClassName._method")
        sys.exit(1)
        
    target = sys.argv[1]
    # Tool target shape: module.path.ClassName.method (one trailing rsplit
    # for the method name; the rest is a normal dotted ``module.ClassName``
    # path that the loader resolves).
    class_dotted, method_name = target.rsplit(".", 1)

    try:
        cls = load_class(class_dotted)
        obj = cls()
        pts = getattr(obj, method_name)()
        analyze_profile(pts)
    except Exception as e:
        print(f"Error loading {target}: {e}")
        sys.exit(1)
