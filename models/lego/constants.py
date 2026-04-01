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
Lego Technic dimension constants.

Single source of truth for all Lego Technic reference dimensions.
Update values here and they propagate to all models that import from this module.

All measurements are in millimetres (mm).
"""

import os
from pathlib import Path

# Parse local .env file if it exists (simple fallback without external dependencies)
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Grid & Stud Spacing ───────────────────────────────────────────────────────
STUD_PITCH: float = 8.0       # Centre-to-centre stud spacing (mm)
PLATE_HEIGHT: float = 3.2     # 1 plate height (mm)
BRICK_HEIGHT: float = 9.6     # 1 brick height = 3 plates (mm)
STUD_DIAMETER: float = 4.8    # Stud top diameter (mm)
STUD_HEIGHT: float = 1.8      # Stud height above top face (mm)

# ── Technic Pin Holes ─────────────────────────────────────────────────────────
PIN_HOLE_DIAMETER: float = 4.8    # Nominal round pin hole diameter (mm)
PIN_HOLE_PRINTED: float = float(os.getenv("PIN_HOLE_PRINTED", "4.85"))  # Recommended diameter for FDM printed parts (mm)
HOLE_SPACING: float = 8.0         # Centre-to-centre hole spacing (mm)
EDGE_TO_CENTRE: float = 4.0       # Distance from part edge to hole centre (mm)

# ── Technic Axle (cross profile) ─────────────────────────────────────────────
AXLE_TIP_TO_TIP: float = 4.75    # Axle outer + tip-to-tip diameter (mm)
AXLE_ARM_WIDTH: float = 1.78     # Axle arm width / flat-to-flat (mm)
AXLE_ARM_PROTRUSION: float = 1.50  # Arm protrusion past flat face (mm)
AXLE_LENGTH_PER_STUD: float = 8.0  # Axle length per stud unit (mm)

# ── Technic Axle Hole (cross profile) ────────────────────────────────────────
AXLE_HOLE_TIP_TO_TIP: float = float(os.getenv("AXLE_HOLE_TIP_TO_TIP", "4.82"))  # Axle hole cross tip-to-tip (mm)
AXLE_HOLE_ARM_WIDTH: float = float(os.getenv("AXLE_HOLE_ARM_WIDTH", "1.64"))   # Axle hole flat-to-flat (mm)

# ── Shared geometry defaults ──────────────────────────────────────────────────
DEFAULT_CORNER_RADIUS: float = float(os.getenv("DEFAULT_CORNER_RADIUS", "0.4")) # Inner concave corner fillet radius (mm) — TechnicAxle
DEFAULT_LEAD_IN: float = float(os.getenv("DEFAULT_LEAD_IN", "0.3"))             # End-face chamfer for easy sliding (mm)
