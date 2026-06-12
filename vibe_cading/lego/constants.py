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

from vibe_cading._env import load_env_file

# Seed environment from REPO_ROOT/.env if present (shared parser; see vibe_cading._env).
load_env_file()

# ── Grid & Stud Spacing ───────────────────────────────────────────────────────
STUD_PITCH: float = 8.0       # Centre-to-centre stud spacing (mm)
PLATE_HEIGHT: float = 3.2     # 1 plate height (mm)
BRICK_HEIGHT: float = 9.6     # 1 brick height = 3 plates (mm)
STUD_DIAMETER: float = 4.8    # Stud top diameter (mm)
STUD_HEIGHT: float = 1.8      # Stud height above top face (mm)

# ── Technic Pin Holes ─────────────────────────────────────────────────────────
# PIN_HOLE_DIAMETER (4.8 mm) is the fixed real-Lego nominal envelope — no
# printer clearance baked in.  TechnicPinHole sources its printed bore from
# the active ToleranceProfile (slip.radial by default) — see
# vibe_cading/lego/cutters/technic_pin_hole.py and docs/print-tolerances.md
# §2.1.  To tune the printed pin fit, calibrate slip.radial in
# print_profiles_user.json via ``python3 tools/calibrate.py slip``.
PIN_HOLE_DIAMETER: float = 4.8    # Nominal round pin hole diameter (mm)
HOLE_SPACING: float = 8.0         # Centre-to-centre hole spacing (mm)
EDGE_TO_CENTRE: float = 4.0       # Distance from part edge to hole centre (mm)

# ── Technic Lift Arm (Beam) ──────────────────────────────────────────────────
# NOTE: BEAM_END_RADIUS (3.9 mm) and EDGE_TO_CENTRE (4.0 mm) are deliberately
# offset by 0.1 mm — they describe *different* geometric quantities:
#   * EDGE_TO_CENTRE = 4.0 = STUD_PITCH/2 is the stud-grid quantization of the
#     first/last hole centre from the body edge; nominal Lego liftarm length
#     formula L = n × 8 mm and hole-pitch = 8 mm both hold exactly under this.
#   * BEAM_END_RADIUS = 3.9 = BEAM_WIDTH/2 is the physical radius of the
#     hemicircular end-cap, sourced from Cailliau's measured cross-section
#     (7.8 × 7.8 thick-liftarm).  Centring an r=3.9 end-cap on the first hole
#     (X=4) would put the body's outermost X at 0.1, contradicting the
#     n × 8 mm total-length convention (FR11 bb claim).
# Resolution (option iii per PM brief): place the end-cap *centres* at
# X = BEAM_END_RADIUS = 3.9 (not on the hole at X = 4.0), preserving FR11's
# body bb X ∈ [0, length_mm] and the 8 mm stud-grid pitch — at the cost of a
# 0.1 mm offset between hole centre and end-cap centre on the outermost
# holes.  Real-liftarm Cailliau geometry has the end-cap centred on the hole
# (which would shrink total length by 0.2 mm); the project trades that 0.2 mm
# real-liftarm fidelity for length_mm = n × 8 mm conformance to the
# n-stud naming convention.  See docs/lego-technic.md lines 219–221 (which
# state "end-cap centred on outermost hole") for the contrasting view; the
# 1M-beam doc entry "total length = 8.0 mm" is internally inconsistent with
# centring r=3.9 on the hole (which would yield 7.8 mm).  This project picks
# the 8.0 mm total length and lives with the 0.1 mm offset.
BEAM_THICKNESS: float = 7.8       # Beam height along Z (mm) — Cailliau 7.4–7.8; project picks 7.8 (theoretical 8.0 less ~0.2 relief)
BEAM_WIDTH: float = 7.8           # Beam width along Y (mm) — square cross-section per Cailliau (7.8 × 7.8)
BEAM_END_RADIUS: float = 3.9      # Hemicircular end-cap radius (mm) — = BEAM_WIDTH / 2; end-cap *centres* sit at X = BEAM_END_RADIUS, NOT on the outermost hole (see block-header NOTE for the EDGE_TO_CENTRE 0.1 mm offset rationale)

# ── Technic Axle (cross profile) ─────────────────────────────────────────────
AXLE_TIP_TO_TIP: float = 4.78    # Based on reference drawing
AXLE_ARM_WIDTH: float = 1.79     # Based on reference drawing
AXLE_ARM_PROTRUSION: float = 1.50  # Arm protrusion past flat face (mm)
AXLE_LENGTH_PER_STUD: float = 8.0  # Axle length per stud unit (mm)

# ── Technic Axle Hole (cross profile, real-Lego nominal) ─────────────────────
# Fixed real-world Lego nominal dimensions of the cross axle *hole* — distinct
# from the AXLE_* values above, which describe the axle *solid*.  These are
# plain constants (NOT env-overridable): they are the geometric nominal, not a
# printer-tuned value.  Printer / material clearance is NOT baked in here —
# TechnicAxleHole adds it from the active ToleranceProfile (nominal +
# 2*grade.radial).  To tune a printed fit, calibrate your ToleranceProfile in
# print_profiles_user.json (slip.radial), NOT these constants — see
# docs/lego-technic.md > Tuning Tolerances and AxleHoleGauge.
#   * TIP_TO_TIP 4.80 — cross axle-hole bounding-cylinder envelope; equals the
#     PIN_HOLE_DIAMETER Technic-beam hole envelope (docs/lego-technic.md).
#   * ARM_WIDTH 1.83 — nominal cross-slot flat width (docs/lego-technic.md;
#     best-sourced figure — stands until Stage-2 calibration data exists).
AXLE_HOLE_TIP_TO_TIP: float = 4.80
AXLE_HOLE_ARM_WIDTH:  float = 1.83

# ── Shared geometry defaults ──────────────────────────────────────────────────
CORNER_RADIUS: float = 0.4                                      # Inner concave corner fillet radius (mm) — TechnicAxle
LEAD_IN: float = 0.3                                            # End-face chamfer for easy sliding (mm)
