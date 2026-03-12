"""
SG90 servo case / housing – "loose fit" variant.

Reverse-engineered from ``servo+box_loose+fit.stp`` (CATIA V5, 2024-01-31).

The case is a 24 × 24 mm outer-shell box that wraps around an SG90 micro-servo
and presents LEGO-Technic-compatible mounting clusters on the top face.

Coordinate system
-----------------
* Origin is centred in X, with the box centre Y aligned to the servo shaft
  (Y = −5.6 mm is the shaft axis; the outer box spans Y = −17.6 to +6.4).
* Z = 0 is the bottom opening of the case.  The STEP file has its Z origin at
  18.8 mm above this; all dimensions here are expressed relative to Z = 0.

Geometry summary (all dimensions in mm)
----------------------------------------
Outer box
    24 × 24 mm in XY, vertical corner fillet R = 4 mm.
    Total height Z = 0 to Z = 21.2.

Servo cavity (open bottom)
    Inner pocket from Z = 0 up to the shelf at Z = 5.7.
    Width  X: ±6.9 mm  → 13.8 mm inside
    Depth  Y: −10.8 to +5.8 mm → 16.6 mm inside
    Rounded inner vertical corners R ≈ 0.9 mm.

Side-wall LEGO pin holes (3 per side, 8 mm pitch)
    Each hole is a round bore Ø 4.8 mm through a 1 mm deep × 5.05 mm tall
    rectangular recess cut into the outer X wall.
    The recess is 1 mm deep; the round bore continues 3 mm further (total 4 mm).
    Hole centres at Y = 2.4, −5.6, −13.6;  Z = 9.2 (mid-wall height).

Side-face M2 mounting screws (2 per side, X direction)
    Ø 3 mm bores at (X = ±9.5,  Y = −4.338 and −6.862),  Z = 6.7–11.7 mm.

Top plate with servo shaft opening
    8 mm solid plate (Z = 13.2 to 21.2) with a central Ø 9.6 mm shaft hole at
    (0, −5.6).

Snap-post clusters (4 clusters × 4 posts, 8 × 8 mm LEGO grid)
    Each cluster is centred at one of the four LEGO-pitch corner positions:
        (±8, 2.4)  and  (±8, −13.6)
    plus four clusters on the shaft-opening ring:
        (±8, −5.6)  and  (0, ±(2.4 / −13.6))
    Each cluster has 4 snap posts arranged on a 2 × 2 grid at ±1.737 mm.
    Post outer radius = 2.525 mm, inner bore R = 0.5 mm; stepped cap R = 3.05 mm
    at top and bottom (1 mm each), body R = 2.5 mm over the middle 6 mm.
    Posts rise from Z = 13.2 (top plate surface) to Z = 21.2 (top face).
"""

import cadquery as cq

from lego.constants import PIN_HOLE_DIAMETER, STUD_PITCH
from lego.cutters.technic_axle_hole import TechnicAxleHole
from lego.cutters.technic_pin_hole import TechnicPinHole
from cq_utils import (
    rounded_box,
    cylinder,
    countersunk_hole,
    orient_to_neg_x,
    orient_to_pos_x,
    cut_at_positions,
)


class ServoCase:
    """Parametric SG90 servo housing – "loose fit" variant.

    Designed to accept an SG90 (or equivalent) micro-servo body.  The top face
    carries four 2 × 2 snap-post clusters compatible with the LEGO Technic
    8 mm grid, allowing the case to be clipped into LEGO beams.

    Parameters
    ----------
    outer_size : float
        Square outer footprint (mm). Default 24.0.
    total_height : float
        Full height from open bottom to top face (mm). Default 21.2.
    corner_r : float
        Outer vertical corner fillet radius (mm). Default 4.0.
    cavity_depth : float
        Depth of the open-bottom servo cavity  (Z = 0 → shelf). Default 5.7.
    cavity_half_x : float
        Half-width of the servo cavity in X (mm). Default 6.9.
    cavity_front_y : float
        Inner front (−Y) wall of the cavity (mm). Default −10.8.
    cavity_back_y : float
        Inner back (+Y) wall of the cavity (mm). Default 5.8.
    cavity_corner_r : float
        Fillet radius on inner cavity vertical corners (mm). Default 0.9.
    servo_center_y : float
        Y position of the servo shaft axis (mm). Default −5.6.
    pin_hole_r : float
        Radius of the side-wall LEGO pin bores (mm). Default PIN_HOLE_DIAMETER/2.
    pin_hole_ys : tuple[float, ...]
        Y centres of the three side holes (mm). Default (2.4, −5.6, −13.6).
    pin_hole_z : float
        Z height of side hole centres (mm). Default 9.2.
    pin_recess_depth : float
        Depth of the outer flanged recess (mm). Default 1.0.
    screw_r : float
        Radius of side-face screw holes (mm). Default 1.5.
    screw_y_offsets : tuple[float, ...]
        Y offsets from servo_center_y for the two screw holes. Default (1.262, −1.262).
    screw_z_lo : float
        Lower Z of screw hole span (mm). Default 6.675.
    screw_z_hi : float
        Upper Z of screw hole span (mm). Default 11.725.
    shaft_hole_r : float
        Radius of the top-face servo shaft opening (mm). Default 4.8.
    top_plate_z : float
        Z where the top plate / snap posts begin (mm). Default 13.2.
    post_cluster_positions : tuple[tuple[float, float], ...]
        (x, y) centres of the four snap-post clusters. Default (±8, 2.4 / −13.6).
    post_outer_r : float
        Outer radius of each snap post (mm). Default 2.525.
    post_body_r : float
        Outer radius of the post body mid-section (mm). Default 2.5.
    post_cap_r : float
        Outer radius of the post step cap at top & bottom (mm). Default 3.05.
    post_cap_h : float
        Height of each step cap at top and bottom (mm). Default 1.0.
    post_bore_r : float
        Inner bore radius of each snap post (mm). Default 0.5.
    post_grid_offset : float
        ±XY offset of each post from the cluster centre (mm). Default 1.737.
    """

    # ── Default dimensions (reverse-engineered from STEP) ───────────────────
    OUTER_SIZE: float = 24.0
    TOTAL_HEIGHT: float = 21.2
    CORNER_R: float = 4.0

    CAVITY_DEPTH: float = 5.7
    CAVITY_HALF_X: float = 6.9
    CAVITY_FRONT_Y: float = -10.8
    CAVITY_BACK_Y: float = 5.8
    CAVITY_CORNER_R: float = 0.9

    SERVO_CENTER_Y: float = -5.6

    PIN_HOLE_R: float = PIN_HOLE_DIAMETER / 2   # 2.4 mm
    PIN_HOLE_YS: tuple = (2.4, -5.6, -13.6)     # 8 mm pitch
    PIN_HOLE_Z: float = 9.2
    PIN_RECESS_DEPTH: float = 1.0

    SCREW_R: float = 1.5
    SCREW_Y_OFFSETS: tuple = (1.262, -1.262)
    SCREW_Z_LO: float = 6.675    # 25.475 − 18.8
    SCREW_Z_HI: float = 11.725   # 30.525 − 18.8

    SHAFT_HOLE_R: float = 4.8
    # The shaft and boss bores are two offset cylinders (not one centred bore).
    # Both pairs are symmetric around servo_center_y.
    SHAFT_Y_OFFSET: float = 3.056   # ±offset of each of the two shaft bores
    BOSS_R: float = 5.8             # boss clearance bore radius
    BOSS_Y_OFFSET: float = 3.690    # ±offset of each of the two boss bores
    BOSS_Z_LO: float = 9.2          # boss clearance starts above cavity shelf
    SHAFT_Z_LO: float = 14.2        # shaft bore starts 1 mm into top plate

    # Bottom screw hole (visible from open cavity bottom)
    BOTTOM_SCREW_Y: float = -13.85  # Y centre of the countersunk screw hole
    BOTTOM_SCREW_R: float = 0.80    # bore radius
    BOTTOM_SCREW_CS_R: float = 1.43 # countersink entry radius at Z = 0
    BOTTOM_SCREW_CS_DEPTH: float = 0.50  # countersink depth
    BOTTOM_SCREW_DEPTH: float = 9.0  # total bore depth

    TOP_PLATE_Z: float = 13.2   # Z=32 in STEP (32 − 18.8)

    # Four 2×2 snap-post clusters at LEGO-pitch positions
    POST_CLUSTER_POSITIONS: tuple = (
        ( 8.0,   2.4),
        (-8.0,   2.4),
        ( 8.0, -13.6),
        (-8.0, -13.6),
    )
    POST_OUTER_R: float = 2.525   # = inner ring of snap fit
    POST_BODY_R: float = 2.5      # mid-section outer radius
    POST_CAP_R: float = 3.05      # step-cap outer radius (top & bottom 1 mm)
    POST_CAP_H: float = 1.0
    POST_BORE_R: float = 0.5      # M2 centre bore
    POST_GRID_OFFSET: float = 1.737  # ±XY offset within each 2×2 cluster

    def __init__(
        self,
        outer_size: float = OUTER_SIZE,
        total_height: float = TOTAL_HEIGHT,
        corner_r: float = CORNER_R,
        cavity_depth: float = CAVITY_DEPTH,
        cavity_half_x: float = CAVITY_HALF_X,
        cavity_front_y: float = CAVITY_FRONT_Y,
        cavity_back_y: float = CAVITY_BACK_Y,
        cavity_corner_r: float = CAVITY_CORNER_R,
        servo_center_y: float = SERVO_CENTER_Y,
        pin_hole_r: float = PIN_HOLE_R,
        pin_hole_ys: tuple = PIN_HOLE_YS,
        pin_hole_z: float = PIN_HOLE_Z,
        pin_recess_depth: float = PIN_RECESS_DEPTH,
        screw_r: float = SCREW_R,
        screw_y_offsets: tuple = SCREW_Y_OFFSETS,
        screw_z_lo: float = SCREW_Z_LO,
        screw_z_hi: float = SCREW_Z_HI,
        shaft_hole_r: float = SHAFT_HOLE_R,
        top_plate_z: float = TOP_PLATE_Z,
        post_cluster_positions: tuple = POST_CLUSTER_POSITIONS,
        post_outer_r: float = POST_OUTER_R,
        post_body_r: float = POST_BODY_R,
        post_cap_r: float = POST_CAP_R,
        post_cap_h: float = POST_CAP_H,
        post_bore_r: float = POST_BORE_R,
        post_grid_offset: float = POST_GRID_OFFSET,
    ):
        self.outer_size = outer_size
        self.total_height = total_height
        self.corner_r = corner_r
        self.cavity_depth = cavity_depth
        self.cavity_half_x = cavity_half_x
        self.cavity_front_y = cavity_front_y
        self.cavity_back_y = cavity_back_y
        self.cavity_corner_r = cavity_corner_r
        self.servo_center_y = servo_center_y
        self.pin_hole_r = pin_hole_r
        self.pin_hole_ys = pin_hole_ys
        self.pin_hole_z = pin_hole_z
        self.pin_recess_depth = pin_recess_depth
        self.screw_r = screw_r
        self.screw_y_offsets = screw_y_offsets
        self.screw_z_lo = screw_z_lo
        self.screw_z_hi = screw_z_hi
        self.shaft_hole_r = shaft_hole_r
        self.top_plate_z = top_plate_z
        self.post_cluster_positions = post_cluster_positions
        self.post_outer_r = post_outer_r
        self.post_body_r = post_body_r
        self.post_cap_r = post_cap_r
        self.post_cap_h = post_cap_h
        self.post_bore_r = post_bore_r
        self.post_grid_offset = post_grid_offset

        self._solid = self._build()

    # ── helpers ─────────────────────────────────────────────────────────────

    @property
    def _half(self) -> float:
        return self.outer_size / 2   # 12.0

    # ── build pipeline ───────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._outer_shell()
        part = self._cut_servo_cavity(part)
        part = self._cut_pin_holes(part)
        part = self._cut_side_screws(part)
        part = self._cut_bottom_screw(part)
        part = self._cut_top_holes(part)
        return part

    # ── 1. Outer shell ───────────────────────────────────────────────────────

    def _outer_shell(self) -> cq.Workplane:
        """Rounded-corner box: 24 × 24 mm, corner R = 4 mm, closed top."""
        return rounded_box(
            self.outer_size, self.outer_size, self.total_height,
            self.corner_r, center=(0, self.servo_center_y, 0),
        )

    # ── 2. Open-bottom servo cavity ──────────────────────────────────────────

    def _cut_servo_cavity(self, part: cq.Workplane) -> cq.Workplane:
        """Open-bottom pocket (Z = 0 → shelf at cavity_depth) for the servo body."""
        yf, yb = self.cavity_front_y, self.cavity_back_y
        cavity = rounded_box(
            2 * self.cavity_half_x, yb - yf, self.cavity_depth,
            self.cavity_corner_r, center=(0, (yf + yb) / 2, 0),
        )
        return part.cut(cavity)

    # ── 3. LEGO-style pin and axle holes through X side walls ───────────────

    def _cut_pin_holes(self, part: cq.Workplane) -> cq.Workplane:
        """Three standard Technic pin holes per X side, each 1 stud deep."""
        h = self._half   # 12.0
        hz = self.pin_hole_z
        cutter = TechnicPinHole.standard(depth=STUD_PITCH).solid
        positions = [(0, y) for y in self.pin_hole_ys]
        for x, y in positions:
            part = part.cut(orient_to_neg_x(cutter, -h, y, hz))
            part = part.cut(orient_to_pos_x(cutter,  h, y, hz))
        return part

    # ── 4. Side-face M2 mounting screw holes ─────────────────────────────────

    def _cut_side_screws(self, part: cq.Workplane) -> cq.Workplane:
        """Two Ø 3 mm through-bores per X wall for M2 self-tapping screws."""
        h = self._half
        z_mid = (self.screw_z_lo + self.screw_z_hi) / 2
        # Build a 2h-long cylinder along Z at origin, rotate to align with X,
        # then shift so it spans from x = −h to x = +h.
        cutter = (
            cylinder(self.screw_r, 2 * h)
            .rotate((0, 0, 0), (0, 1, 0), 90)   # +Z → +X  ⇒  bore now along X
            .translate((-h, 0, 0))               # centre on X axis
        )
        for y_off in self.screw_y_offsets:
            y_c = self.servo_center_y + y_off
            part = part.cut(cutter.translate((0, y_c, z_mid)))
        return part

    # ── 5. Shaft bore + boss clearance (two cylinders each, offset in Y) ──────

    def _cut_shaft_hole(self, part: cq.Workplane) -> cq.Workplane:
        """Cut shaft bore and boss clearance as two offset cylinders each.

        The SG90's circular boss sits off-centre relative to the case.
        Two R=5.8 boss-clearance bores start at the cavity shelf and rise
        to the top-plate; two R=4.8 shaft bores go through the top plate.
        All four cylinders are symmetric about servo_center_y.
        """
        cy = self.servo_center_y          # −5.6
        boss_ys = (
            cy + self.BOSS_Y_OFFSET,      # −1.91
            cy - self.BOSS_Y_OFFSET,      # −9.29
        )
        shaft_ys = (
            cy + self.SHAFT_Y_OFFSET,     # −2.54
            cy - self.SHAFT_Y_OFFSET,     # −8.66
        )

        # Boss clearance – from Z=9.2 (above cavity shelf) up to top plate
        boss_h = self.top_plate_z - self.BOSS_Z_LO   # 13.2 − 9.2 = 4.0
        for y in boss_ys:
            bore = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, y, self.BOSS_Z_LO))
                .circle(self.BOSS_R)
                .extrude(boss_h)
            )
            part = part.cut(bore)

        # Shaft bores – top plate only
        shaft_h = self.total_height - self.SHAFT_Z_LO  # 21.2 − 14.2 = 7.0
        for y in shaft_ys:
            bore = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, y, self.SHAFT_Z_LO))
                .circle(self.shaft_hole_r)
                .extrude(shaft_h)
            )
            part = part.cut(bore)

        return part

    # ── 5b. Bottom screw hole ─────────────────────────────────────────────────

    def _cut_bottom_screw(self, part: cq.Workplane) -> cq.Workplane:
        """Countersunk Ø 1.6 mm screw hole in the solid bottom face (≈ 46° head)."""
        cutter = countersunk_hole(
            bore_r=self.BOTTOM_SCREW_R,
            bore_depth=self.BOTTOM_SCREW_DEPTH,
            cs_r=self.BOTTOM_SCREW_CS_R,
            cs_depth=self.BOTTOM_SCREW_CS_DEPTH,
            center=(0, self.BOTTOM_SCREW_Y, 0),
        )
        return part.cut(cutter)

    # ── 6. Cut top plate Technic holes ───────────────────────────────────────

    def _cut_top_holes(self, part: cq.Workplane) -> cq.Workplane:
        """4 pin holes at LEGO-grid corners + 4 axle holes at mid-edges, top face."""
        z0 = self.top_plate_z
        depth = self.total_height - z0

        pin_cutter = TechnicPinHole.standard(depth=depth).solid
        axle_cutter = TechnicAxleHole(depth=depth).solid

        axle_positions = [
            (0.0,  2.4), (0.0, -13.6),
            (-8.0, -5.6), (8.0, -5.6),
        ]

        part = cut_at_positions(part, pin_cutter,  self.post_cluster_positions, z_offset=z0)
        part = cut_at_positions(part, axle_cutter, axle_positions,              z_offset=z0)
        return part

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show
    case = ServoCase()
    show(case.solid)
