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

"""SG90 micro-servo reference body.

Coordinate system
-----------------
Origin is centred in X and in Y at the servo shaft axis (Y = 0).
Z = 0 is the bottom face of the servo body.

The body is oriented so its shaft axis sits at (X=0, Y=0); the mounting
tabs extend in ±Y beyond the narrow body walls.

All measurements are in mm, taken from the reference SG90.step file in this
directory.

Geometry summary
----------------
Main body
    22.6 mm wide (Y direction) × 12.6 mm deep (X) × 23.7 mm tall.
    The shaft output axis is at origin (0, 0).  The body is offset in Y:
    near face at Y = −6.1, far face at Y = +16.5.  Body centre is at
    Y = +5.2 from the shaft axis.

Mounting tabs
    Two flat tabs protrude ±Y beyond the body.
    Each tab: 4.9 mm protrusion × 12.6 mm wide (X) × 2.4 mm thick (Z).
    Tab underside at Z = 17 mm from the connector end (body bottom).
    Z breakdown: 17 (below tabs) + 2.4 (tabs) + 4.3 (above tabs) = 23.7 ✓
    Screw holes: Ø 2.1 mm (R 1.05), centred 2.6 mm from body outer Y face.

Shaft collar / boss
    Cylindrical boss: R = 6.3 mm, extends 4.2 mm above the body top,
    centred at (0, 0) — the output shaft axis.
    The shaft is NOT centred on the body: the body is asymmetric about
    the shaft axis.  The shaft is 6.1 mm from the near body face and
    16.5 mm from the far face (total body width 22.6 mm).

Secondary gear boss
    A second cylindrical boss (R = 2.5 mm, height = 3.9 mm) rises from the
    body top alongside the main collar.  Its axis is at (X=0, Y=+5.7) —
    offset 5.7 mm in +Y from the shaft axis.  It is partially embedded in
    the main collar and protrudes 1.9 mm (8.2 − 6.3) beyond the collar edge
    on the far (+Y) side.  This is the last-stage gear-shaft housing.

Shaft stub (above collar)
    R = 2.3 mm, extends 2.5 mm above the collar top.
    A central bore (R = 0.9 mm, depth = 6.4 mm) is cut from the collar base
    (Z = 23.7) upward to Z = 30.1 mm.  At the shaft tip the bore widens via
    a 45-degree countersink (R 0.9 → 1.2 mm over 0.3 mm), creating the
    visible top hole at Z = 30.4 mm.  The outer rim of the shaft tip is
    similarly chamfered (R 2.3 → 2.0 mm over 0.3 mm).

Connector end (near face, bottom)
    A chamfer cuts the bottom edge of the near face: the body narrows by
    3.0 mm over the bottom 2.0 mm of Z.  A small rectangular pocket
    (4.0 mm wide × 1.5 mm deep × 1.5 mm tall) is cut into the near face
    for the cable connector.

Corner bores (injection-mould draft)
    Four Ø 4.5 mm (R 2.25) cylindrical cuts at the four vertical body edges
    at the bottom.  Near-face pair: Z = 0.5–2.0 mm (centred at Y = ±6.3,
    Y_face = −6.1).  Far-face pair: Z = 0.0–1.0 mm (centred at X = ±6.3,
    Y_face = +16.5).

Total height = 23.7 + 4.2 + 2.5 = 30.4 mm.
"""

import cadquery as cq

from models.cq_utils import rounded_box, cylinder


class Sg90Servo:
    """Reference solid for the SG90 micro-servo body.

    Intended for assembly visualisation and clearance checking — not for
    printing.  The coordinate system matches the :class:`ServoCase` housing:
    shaft axis at (X=0, Y=0), Z=0 at the bottom of the servo.

    Parameters
    ----------
    body_width : float
        Width of the main body in Y (mm). Default 22.6.
    body_depth : float
        Depth of the main body in X (mm). Default 12.6.
    body_height : float
        Height of the main body (Z, bottom to top, excl. collar). Default 23.7.
    body_y_offset : float
        Offset of the body centre from the shaft axis in Y (mm).  The shaft
        is close to one face; the rest of the body extends in +Y. Default 5.2.
    tab_protrusion : float
        How far each tab extends beyond the body in ±Y (mm). Default 4.9.
    tab_depth : float
        Tab width in X (mm), matches body depth. Default 12.6.
    tab_thickness : float
        Thickness (Z height) of the mounting tabs (mm). Default 2.4.
    tab_z_bottom : float
        Z position of the tab underside (mm). Default 17.0.
    tab_hole_r : float
        Radius of the mounting screw holes in the tabs (mm). Default 1.05.
    tab_hole_y_offset : float
        Distance from the outer body face to the screw hole centre (mm).
        Default 2.6.
    collar_r : float
        Radius of the shaft boss / collar (mm). Default 6.3.
    collar_height : float
        Height of the collar above the body top (mm). Default 4.2.
    shaft_r : float
        Radius of the shaft stub above the collar (mm). Default 2.3.
    shaft_height : float
        Height of the shaft stub above the collar top (mm). Default 2.5.
    corner_r : float
        Outer corner fillet radius on the main body (mm). Default 0.2.
    """

    # ── Default dimensions (from SG90.step reference) ─────────────────────────
    BODY_WIDTH: float = 22.6      # Y span of main body
    BODY_DEPTH: float = 12.6      # X span of main body
    BODY_HEIGHT: float = 23.7     # Z from body bottom to body top (excl. collar)

    TAB_PROTRUSION: float = 4.9   # each tab extends this far in ±Y beyond body
    TAB_DEPTH: float = 12.6       # tab X width (matches body depth)
    TAB_THICKNESS: float = 2.4    # Z height of the tab plate
    TAB_Z_BOTTOM: float = 17.0    # Z of tab underside from connector end
    TAB_HOLE_R: float = 1.05      # screw bore radius (Ø 2.1 mm)
    TAB_HOLE_Y_OFFSET: float = 2.6   # from outer body Y face to hole centre

    BODY_Y_OFFSET: float = 5.2    # body centre offset from shaft axis in Y
                                      # shaft at Y=0; near face at −6.1, far at +16.5

    COLLAR_R: float = 6.3         # boss / collar radius
    COLLAR_HEIGHT: float = 4.2    # collar height above body top

    # ── Secondary gear boss (last-stage gear-shaft housing) ───────────────────
    _GEAR_BOSS_R: float = 2.5        # radius of secondary gear boss
    _GEAR_BOSS_Y: float = 5.7        # Y offset of its axis from shaft axis
    _GEAR_BOSS_HEIGHT: float = 3.9   # height above body top (same base as collar)

    SHAFT_R: float = 2.3          # shaft stub radius above collar
    SHAFT_HEIGHT: float = 2.5     # shaft stub height above collar top

    # ── Central shaft bore ───────────────────────────────────────────────────
    _SHAFT_BORE_R: float = 0.9      # central bore radius (Ø 1.8 mm)
    _SHAFT_BORE_DEPTH: float = 6.4  # bore depth from collar base (Z=body_height)

    # ── Shaft tip geometry (countersink + outer chamfer) ──────────────────────
    _SHAFT_BORE_COUNTERSINK_R: float = 1.2     # bore entry radius at shaft top (mm)
    _SHAFT_BORE_COUNTERSINK_DEPTH: float = 0.3 # axial depth of bore countersink (mm)
    _SHAFT_TIP_CHAMFER: float = 0.3            # 45-deg chamfer on outer top edge (mm)

    CORNER_R: float = 0.2         # body outer corner fillet radius

    # ── Corner-bore geometry (4 cylindrical draft cuts at body bottom corners) ─
    _CNRBORE_R: float = 2.25       # radius of each corner bore (Ø 4.5 mm)
    _CNRBORE_NEAR_Z: float = 0.5   # bottom Z of near-face corner bores
    _CNRBORE_NEAR_H: float = 1.5   # height of near-face corner bores
    _CNRBORE_FAR_Z: float = 0.0    # bottom Z of far-face corner bores
    _CNRBORE_FAR_H: float = 1.0    # height of far-face corner bores

    # ── Connector-end geometry (near face) ─ not exposed as constructor args ──
    _CHAMFER_HEIGHT: float = 2.0  # Z height of near-face bottom chamfer
    _CHAMFER_WIDTH: float = 3.0   # Y width removed from near face at Z = 0
    _POCKET_WIDTH: float = 4.0    # X width of connector pocket on near face
    _POCKET_Y_DEPTH: float = 1.5  # Y depth of pocket into near face
    _POCKET_HEIGHT: float = 1.5   # Z height of pocket
    _POCKET_Z: float = 1.0        # Z of pocket bottom

    def __init__(
        self,
        body_width: float = BODY_WIDTH,
        body_depth: float = BODY_DEPTH,
        body_height: float = BODY_HEIGHT,
        body_y_offset: float = BODY_Y_OFFSET,
        tab_protrusion: float = TAB_PROTRUSION,
        tab_depth: float = TAB_DEPTH,
        tab_thickness: float = TAB_THICKNESS,
        tab_z_bottom: float = TAB_Z_BOTTOM,
        tab_hole_r: float = TAB_HOLE_R,
        tab_hole_y_offset: float = TAB_HOLE_Y_OFFSET,
        collar_r: float = COLLAR_R,
        collar_height: float = COLLAR_HEIGHT,
        shaft_r: float = SHAFT_R,
        shaft_height: float = SHAFT_HEIGHT,
        corner_r: float = CORNER_R,
    ):
        self.body_width = body_width
        self.body_depth = body_depth
        self.body_height = body_height
        self.body_y_offset = body_y_offset
        self.tab_protrusion = tab_protrusion
        self.tab_depth = tab_depth
        self.tab_thickness = tab_thickness
        self.tab_z_bottom = tab_z_bottom
        self.tab_hole_r = tab_hole_r
        self.tab_hole_y_offset = tab_hole_y_offset
        self.collar_r = collar_r
        self.collar_height = collar_height
        self.shaft_r = shaft_r
        self.shaft_height = shaft_height
        self.corner_r = corner_r

        self._solid = self._build()

    # ── helpers ──────────────────────────────────────────────────────────────

    @property
    def _half_width(self) -> float:
        return self.body_width / 2       # 11.3 mm

    @property
    def _half_depth(self) -> float:
        return self.body_depth / 2       # 6.3 mm

    @property
    def _body_y_centre(self) -> float:
        """Y coordinate of the body centre (shaft is at Y=0)."""
        return self.body_y_offset        # +5.2 mm

    @property
    def total_height(self) -> float:
        """Total height including collar and shaft stub (mm)."""
        return self.body_height + self.collar_height + self.shaft_height

    # ── build pipeline ───────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._main_body()
        part = self._add_tabs(part)
        part = self._add_collar(part)
        part = self._add_gear_boss(part)
        part = self._add_shaft(part)
        part = self._cut_shaft_bore(part)
        part = self._cut_shaft_countersink(part)
        part = self._cut_connector_chamfer(part)
        part = self._cut_connector_pocket(part)
        part = self._cut_corner_bores(part)
        return part

    # ── 1. Main body ─────────────────────────────────────────────────────────

    def _main_body(self) -> cq.Workplane:
        """Rounded-corner box offset in Y so shaft axis is at Y=0."""
        return rounded_box(
            self.body_depth,        # X  (12.6 mm)
            self.body_width,        # Y  (22.6 mm)
            self.body_height,       # Z  (23.7 mm)
            self.corner_r,
            center=(0, self._body_y_centre, 0),
        )

    # ── 2. Mounting tabs ─────────────────────────────────────────────────────

    def _add_tabs(self, part: cq.Workplane) -> cq.Workplane:
        """Two flat rectangular tabs extending ±Y beyond the body."""
        tab_y_total = self.body_width + 2 * self.tab_protrusion   # 32.4 mm
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, self._body_y_centre, self.tab_z_bottom))
            .rect(self.tab_depth, tab_y_total)
            .extrude(self.tab_thickness)
        )
        part = part.union(tab)

        # Cut screw holes through both tabs.
        # Hole centres sit tab_hole_y_offset outside each body Y-face.
        body_y_min = self._body_y_centre - self._half_width   # near face
        body_y_max = self._body_y_centre + self._half_width   # far face
        hole_y_positions = [
            body_y_min - self.tab_hole_y_offset,
            body_y_max + self.tab_hole_y_offset,
        ]
        for y_centre in hole_y_positions:
            bore = cylinder(
                self.tab_hole_r,
                self.tab_thickness + 0.2,
                center=(0, y_centre, self.tab_z_bottom - 0.1),
            )
            part = part.cut(bore)

        return part

    # ── 3. Shaft collar / boss ────────────────────────────────────────────────

    def _add_collar(self, part: cq.Workplane) -> cq.Workplane:
        """Cylindrical boss centred at (0, 0), rising above the body top."""
        collar = cylinder(
            self.collar_r,
            self.collar_height,
            center=(0, 0, self.body_height),
        )
        return part.union(collar)

    # ── 4. Secondary gear boss ─────────────────────────────────────────────────

    def _add_gear_boss(self, part: cq.Workplane) -> cq.Workplane:
        """Cylindrical boss for the last-stage gear shaft, offset in +Y.

        Rises from the body top alongside the main collar.  Radius 2.5 mm,
        height 3.9 mm, axis at (X=0, Y=+5.7) — partially embedded in the
        R=6.3 collar and protruding 1.9 mm beyond it on the far side.
        """
        boss = cylinder(
            self._GEAR_BOSS_R,
            self._GEAR_BOSS_HEIGHT,
            center=(0, self._GEAR_BOSS_Y, self.body_height),
        )
        return part.union(boss)

    # ── 5. Shaft stub ────────────────────────────────────────────────────────

    def _add_shaft(self, part: cq.Workplane) -> cq.Workplane:
        """Thin shaft stub (spline profile approximated as cylinder) above collar.

        The outer top edge is chamfered (45°, 0.3 mm) to match the reference:
        the shaft tip outer radius tapers from R=2.3 to R=2.0 over 0.3 mm.
        """
        shaft = cylinder(
            self.shaft_r,
            self.shaft_height,
            center=(0, 0, self.body_height + self.collar_height),
        )
        shaft = shaft.faces(">Z").chamfer(self._SHAFT_TIP_CHAMFER)
        return part.union(shaft)

    # ── 6. Central shaft bore ─────────────────────────────────────────────────

    def _cut_shaft_bore(self, part: cq.Workplane) -> cq.Workplane:
        """Ø 1.8 mm central bore through the collar and shaft stub.

        Starts at the collar base (Z = body_height) and runs 6.4 mm deep,
        stopping 0.3 mm below the top of the shaft stub.
        """
        bore = cylinder(
            self._SHAFT_BORE_R,
            self._SHAFT_BORE_DEPTH + 0.1,   # oversize for clean cut
            center=(0, 0, self.body_height - 0.1),
        )
        return part.cut(bore)

    # ── 6b. Shaft bore countersink ──────────────────────────────────────────────

    def _cut_shaft_countersink(self, part: cq.Workplane) -> cq.Workplane:
        """Conical countersink at the top of the shaft bore.

        The bore entry at the shaft tip flares from R=0.9 mm (at
        Z = body_height + collar_height + shaft_height − 0.3) outward to
        R=1.2 mm at the shaft top face.  This creates the visible Ø 2.4 mm
        hole when the servo is viewed from above.
        """
        shaft_top_z = self.body_height + self.collar_height + self.shaft_height
        cs_start_z = shaft_top_z - self._SHAFT_BORE_COUNTERSINK_DEPTH  # Z=30.1
        # Overshoot by 0.1 mm in both height AND radius (preserving 45° slope)
        # so the interpolated radius at the actual shaft top (0.3 mm above
        # cs_start_z) is exactly _SHAFT_BORE_COUNTERSINK_R = 1.2 mm.
        _h = self._SHAFT_BORE_COUNTERSINK_DEPTH + 0.1
        _r2 = self._SHAFT_BORE_COUNTERSINK_R + 0.1
        countersink = cq.Workplane().add(
            cq.Solid.makeCone(
                self._SHAFT_BORE_R,  # R at bottom = 0.9
                _r2,                 # R at top = 1.3 (45° extended above shaft top)
                _h,                  # height = 0.4
                cq.Vector(0, 0, cs_start_z),
                cq.Vector(0, 0, 1),
            )
        )
        return part.cut(countersink)

    # ── 7. Connector chamfer ──────────────────────────────────────────────────

    def _cut_connector_chamfer(self, part: cq.Workplane) -> cq.Workplane:
        """Chamfer the bottom edge of the near face.

        The SG90 body narrows on the near (connector) side at the bottom:
        at Z = 0 the near face is 3.0 mm inward, linearly reaching its full
        position at Z = 2.0 mm.  This is modelled as a triangular-prism cut.
        """
        near_y = self._body_y_centre - self._half_width   # −6.1
        ch_w = self._CHAMFER_WIDTH                         # 3.0 mm in Y
        ch_h = self._CHAMFER_HEIGHT                        # 2.0 mm in Z
        half_d = self._half_depth + 0.5                    # oversize for clean cut
        chamfer = (
            cq.Workplane("YZ")
            .workplane(offset=-half_d)
            .moveTo(near_y, 0)
            .lineTo(near_y + ch_w, 0)
            .lineTo(near_y, ch_h)
            .close()
            .extrude(2 * half_d)
        )
        return part.cut(chamfer)

    # ── 8. Connector pocket ───────────────────────────────────────────────────

    def _cut_connector_pocket(self, part: cq.Workplane) -> cq.Workplane:
        """Small rectangular notch on the near face for the cable connector."""
        near_y = self._body_y_centre - self._half_width   # −6.1
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(
                0,
                near_y + self._POCKET_Y_DEPTH / 2,
                self._POCKET_Z,
            ))
            .rect(self._POCKET_WIDTH, self._POCKET_Y_DEPTH)
            .extrude(self._POCKET_HEIGHT)
        )
        return part.cut(pocket)

    # ── 9. Bottom corner bores ───────────────────────────────────────────────

    def _cut_corner_bores(self, part: cq.Workplane) -> cq.Workplane:
        """Four cylindrical draft cuts at the bottom corners of the body.

        Two near-face bores (Ø 4.5 mm) sit at Z = 0.5–2.0 mm, centred on the
        near body face (Y = −6.1) at X = ±half_depth.
        Two far-face bores (Ø 4.5 mm) sit at Z = 0.0–1.0 mm, centred on the
        far body face (Y = +16.5) at X = ±half_depth.
        """
        near_y = self._body_y_centre - self._half_width   # −6.1
        far_y  = self._body_y_centre + self._half_width   # +16.5
        for x_pos in (self._half_depth, -self._half_depth):
            near_bore = cylinder(
                self._CNRBORE_R,
                self._CNRBORE_NEAR_H + 0.1,
                center=(x_pos, near_y, self._CNRBORE_NEAR_Z),
            )
            part = part.cut(near_bore)
            far_bore = cylinder(
                self._CNRBORE_R,
                self._CNRBORE_FAR_H + 0.1,
                center=(x_pos, far_y, self._CNRBORE_FAR_Z - 0.1),
            )
            part = part.cut(far_bore)
        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

    def to_cutter(self, clearance: float = 0.2, extend_shaft_up: float = 5.0) -> cq.Workplane:
        """Return a simplified, oversized solid for cavity boolean cuts.
        
        Includes the main body, collar, gear boss, and shaft stub, expanded by `clearance`.
        The main body is extended infinitely downwards for through-cuts.
        """
        # Give the base body slightly more lateral clearance to avoid 
        # exact coincident/tangent faces with the collar at X = ±6.5,
        # and to ensure Y_min fully engulfs the collar overhang (-6.5).
        body_clearance = clearance + 0.3
        bw = self.body_width + 2 * body_clearance
        bd = self.body_depth + 2 * body_clearance
        bh = self.body_height + clearance  # Keep Z the same to preserve the shelf depth
        
        # We start the body way down (Z = -20) so it cleanly cuts open bottoms
        z_min = -20.0
        body_h = bh - z_min
        
        from models.cq_utils import rounded_box, cylinder
        # Base body
        part = rounded_box(
            bd, bw, body_h,
            corner_r=self.corner_r + body_clearance,
            center=(0, self._body_y_centre, z_min),
        )
        
        # Collar
        collar_h = self.collar_height + clearance + 0.1
        collar = cylinder(
            self.collar_r + clearance,
            collar_h,
            center=(0, 0, self.body_height - 0.1),
        )
        part = part.union(collar)
        
        # Gear boss
        # For the cutter, unify the gear boss height with the collar height.
        # Although physically 0.3mm shorter (3.9 vs 4.2), preserving this as a negative
        # cavity leaves an unprintable 0.3mm stair-step crescent on the ceiling of the mount.
        gear_boss = cylinder(
            self._GEAR_BOSS_R + clearance,
            collar_h,  # Override to match collar_h (eliminates micro-ceiling step)
            center=(0, self._GEAR_BOSS_Y, self.body_height - 0.1),
        )
        part = part.union(gear_boss)
        
        # Shaft Stub (extended upwards to guarantee union with arbitrary downward bores)
        shaft_h = self.shaft_height + clearance + 0.1 + extend_shaft_up
        shaft_stub = cylinder(
            self.shaft_r + clearance,
            shaft_h,
            center=(0, 0, self.body_height + self.collar_height - 0.1),
        )
        part = part.union(shaft_stub)
        
        return part
