"""
Lego Technic dimension constants.

Single source of truth for all Lego Technic reference dimensions.
Update values here and they propagate to all models that import from this module.

All measurements are in millimetres (mm).
"""

# ── Grid & Stud Spacing ───────────────────────────────────────────────────────
STUD_PITCH: float = 8.0       # Centre-to-centre stud spacing (mm)
PLATE_HEIGHT: float = 3.2     # 1 plate height (mm)
BRICK_HEIGHT: float = 9.6     # 1 brick height = 3 plates (mm)
STUD_DIAMETER: float = 4.8    # Stud top diameter (mm)
STUD_HEIGHT: float = 1.8      # Stud height above top face (mm)

# ── Technic Pin Holes ─────────────────────────────────────────────────────────
PIN_HOLE_DIAMETER: float = 4.8    # Nominal round pin hole diameter (mm)
PIN_HOLE_PRINTED: float = 4.85    # Recommended diameter for FDM printed parts (mm)
HOLE_SPACING: float = 8.0         # Centre-to-centre hole spacing (mm)
EDGE_TO_CENTRE: float = 4.0       # Distance from part edge to hole centre (mm)

# ── Technic Axle (cross profile) ─────────────────────────────────────────────
AXLE_TIP_TO_TIP: float = 4.75    # Axle outer + tip-to-tip diameter (mm)
AXLE_ARM_WIDTH: float = 1.78     # Axle arm width / flat-to-flat (mm)
AXLE_ARM_PROTRUSION: float = 1.50  # Arm protrusion past flat face (mm)
AXLE_LENGTH_PER_STUD: float = 8.0  # Axle length per stud unit (mm)

# ── Technic Axle Hole (cross profile) ────────────────────────────────────────
AXLE_HOLE_TIP_TO_TIP: float = 4.9  # Axle hole cross tip-to-tip (mm)
AXLE_HOLE_ARM_WIDTH: float = 1.9   # Axle hole flat-to-flat (mm)

# ── Shared geometry defaults ──────────────────────────────────────────────────
DEFAULT_CORNER_RADIUS: float = 0.4   # Inner concave corner fillet radius (mm) — TechnicAxle
DEFAULT_LEAD_IN: float = 0.3        # End-face chamfer for easy sliding (mm)
