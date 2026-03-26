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

Servo cavity (open bottom and far +Y face)
    Inner pocket from Z = 0 up to the shelf at Z = 5.7.
    Width  X: ±6.9 mm  → 13.8 mm inside
    Front wall at Y = −10.8 mm; back is open (breaks through the outer +Y wall).

Side-wall LEGO pin holes (3 per side, 8 mm pitch)
    Each hole is a round bore Ø 4.8 mm through a 1 mm deep × 5.05 mm tall
    rectangular recess cut into the outer X wall.
    The recess is 1 mm deep; the round bore continues 3 mm further (total 4 mm).
    Hole centres at Y = 2.4, −5.6, −13.6;  Z = 9.2 (mid-wall height).

Side-face M2 mounting screws (2 per side, X direction)
    Ø 3 mm bores at (X = ±9.5,  Y = −4.338 and −6.862),  Z = 6.7–11.7 mm.

Top plate with servo shaft opening
    8 mm solid plate (Z = 13.2 to 21.2) with a central stepped shaft clearance hole
    (R = 3.55 mm to 5.16 mm).

Top Face LEGO holes (Technic pin and axle grid)
    The top face (Z = 21.2) is perfectly flat, allowing the piece to be 3D printed
    UPSIDE-DOWN (face down on the bed) completely without supports. The cavity
    forms stable bridging layers naturally.
    It contains 4 standard Technic pin holes at the corner positions:
        (±8, 2.4)  and  (±8, −13.6)
    and 4 Technic axle holes around the shaft perimeter:
        (±8, −5.6)  and  (0, 2.4) and (0, −13.6)
    These holes cut downwards from Z = 21.2 down to Z = 13.2.
"""

import cadquery as cq

from models.lego.constants import PIN_HOLE_DIAMETER, STUD_PITCH
from models.lego.cutters.technic_axle_hole import TechnicAxleHole
from models.lego.cutters.technic_pin_hole import TechnicPinHole
from models.xlego.servos.shaft import Shaft
from models.rc.servo.sg90 import Sg90Servo
from models.cq_utils import (
    rounded_box,
    countersunk_hole,
    orient_to_neg_x,
    orient_to_pos_x,
    cut_at_positions,
    cylinder,
)


class ServoMountBase:
    """Parametric SG90 servo housing – Full mount main body.

    Designed to accept an SG90 micro-servo body and attaches to a Clamp piece
    to hold both tabs. The top face carries four 2 × 2 snap-post clusters.

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
    shaft_hole_r : float
        Radius of the top-face servo shaft opening (mm). Default 4.8.
    top_plate_z : float
        Z where the top plate / snap posts begin (mm). Default 13.2.
    top_pin_positions : tuple[tuple[float, float], ...]
        (x, y) centres of the four Technic pin holes on the top face. Default (±8, 2.4 / −13.6).
    """

    # ── Default dimensions (reverse-engineered from STEP) ───────────────────
    OUTER_SIZE: float = 24.0
    TOTAL_HEIGHT: float = 21.2
    CORNER_R: float = 4.0

    CAVITY_DEPTH: float = 4.5
    CAVITY_HALF_X: float = 6.5
    CAVITY_FRONT_Y: float = -11.9
    CAVITY_BACK_Y: float = 5.8
    CAVITY_CORNER_R: float = 0.9

    SERVO_CENTER_Y: float = -5.6

    PIN_HOLE_R: float = PIN_HOLE_DIAMETER / 2   # 2.4 mm
    PIN_HOLE_YS: tuple = (2.4, -13.6)     # 8 mm pitch
    PIN_HOLE_Z: float = 9.2
    PIN_RECESS_DEPTH: float = 1.0

    SHAFT_HOLE_R: float = 4.8
    # Clearances for single precision cuts
    COLLAR_R: float = 6.5           # main collar clearance
    GEAR_BOSS_R: float = 2.7        # secondary boss clearance
    GEAR_BOSS_Y_OFFSET: float = 5.7 # offset of secondary boss from shaft

    # Dovetail constants
    DOVETAIL_NECK_HW: float = 1.0
    DOVETAIL_TAIL_HW: float = 1.4

    # Bottom screw hole (visible from open cavity bottom)
    BOTTOM_SCREW_Y: float = -14.3  # Y centre of the countersunk screw hole
    BOTTOM_SCREW_R: float = 0.80    # bore radius
    BOTTOM_SCREW_CS_R: float = 1.43 # countersink entry radius at Z = 0
    BOTTOM_SCREW_CS_DEPTH: float = 0.50  # countersink depth
    BOTTOM_SCREW_DEPTH: float = 9.0  # total bore depth

    TOP_PLATE_Z: float = 13.2   # Z=32 in STEP (32 − 18.8)
    ARM_INNER_X: float = 6.8    # Inner X boundary of the clamp side-arms and wedge lock

    # Four Technic pin holes at LEGO-pitch positions
    TOP_PIN_POSITIONS: tuple = (
        ( 8.0,   2.4),
        (-8.0,   2.4),
        ( 8.0, -13.6),
        (-8.0, -13.6),
    )

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
        collar_r: float = COLLAR_R,
        gear_boss_r: float = GEAR_BOSS_R,
        gear_boss_y_offset: float = GEAR_BOSS_Y_OFFSET,
        pin_hole_r: float = PIN_HOLE_R,
        pin_hole_ys: tuple = PIN_HOLE_YS,
        pin_hole_z: float = PIN_HOLE_Z,
        pin_recess_depth: float = PIN_RECESS_DEPTH,
        shaft_hole_r: float = SHAFT_HOLE_R,
        top_plate_z: float = TOP_PLATE_Z,
        arm_inner_x: float = ARM_INNER_X,
        top_pin_positions: tuple = TOP_PIN_POSITIONS,
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
        self.collar_r = collar_r
        self.gear_boss_r = gear_boss_r
        self.gear_boss_y_offset = gear_boss_y_offset
        self.pin_hole_r = pin_hole_r
        self.pin_hole_ys = pin_hole_ys
        self.pin_hole_z = pin_hole_z
        self.pin_recess_depth = pin_recess_depth
        self.shaft_hole_r = shaft_hole_r
        self.top_plate_z = top_plate_z
        self.arm_inner_x = arm_inner_x
        self.top_pin_positions = top_pin_positions

        self._solid = self._build()

    # ── helpers ─────────────────────────────────────────────────────────────

    @property
    def _half(self) -> float:
        return self.outer_size / 2   # 12.0

    # ── build pipeline ───────────────────────────────────────────────────────

    def _build(self) -> cq.Workplane:
        part = self._outer_shell()
        part = self._cut_shaft_hole(part)
        part = self._cut_servo_cavity(part)
        part = self._cut_pin_holes(part)
        part = self._cut_bottom_screw(part)
        part = self._cut_top_holes(part)
        part = self._cut_clamp_lock(part)
        part = self._cut_back_corners(part)

        assert len(part.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return part

    # ── 1. Outer shell ───────────────────────────────────────────────────────

    def _outer_shell(self) -> cq.Workplane:
        """Box: 24 × 24 mm, closed top. Front (-Y) corners have R=4 mm, back (+Y) are flat."""
        # By leaving the back (+Y) corners sharp/flat, the clamp's sharp step perfectly aligns.
        box = cq.Workplane("XY").rect(self.outer_size, self.outer_size).extrude(self.total_height)

        # Only fillet the two front corners (y < 0 in local rect coordinates)
        def front_edges(e):
            return e.Center().y < 0

        box = box.edges("|Z").filter(front_edges).fillet(self.corner_r)
        return box.translate((0, self.servo_center_y, 0))

    # ── 2. Open-bottom servo cavity ──────────────────────────────────────────

    def _cut_servo_cavity(self, part: cq.Workplane) -> cq.Workplane:
        """Use the SG90 reference model to precisely cut the main cavity.

        This inherently cuts the correct footprint, offset, and collar/gear boss voids.
        """
        servo_ref = Sg90Servo()

        # The servo's tabs rest flush against Z=0 of this mount.
        # So we align servo's Z=0 to mount's Z: -(tabZ + tabThickness)
        z_shift = -(servo_ref.tab_z_bottom + servo_ref.tab_thickness)

        servo_cutter = (
            servo_ref.to_cutter(clearance=0.2)
            .translate((0, self.servo_center_y, z_shift))
        )
        return part.cut(servo_cutter)

    # ── 3. LEGO-style pin and axle holes through X side walls ───────────────

    def _cut_pin_holes(self, part: cq.Workplane) -> cq.Workplane:
        """Three standard Technic pin holes per X side, each 1 stud deep."""
        from models.cq_utils import cylinder
        from models.lego.cutters.technic_pin_hole import TECHNIC_PIN_CB_DIAMETER, TECHNIC_PIN_CB_DEPTH

        h = self._half   # 12.0
        hz = self.pin_hole_z

        # We build a custom cutter with an outside counterbore but NO inside counterbore.
        # The standard TechnicPinHole has counterbores on both ends, which would pierce
        # and scar the inner servo cavity walls because it intersects the collar space.
        base_bore = TechnicPinHole(depth=STUD_PITCH, counterbore_depth=0.0).solid
        cb_bottom = cylinder(TECHNIC_PIN_CB_DIAMETER / 2, TECHNIC_PIN_CB_DEPTH, center=(0, 0, 0))
        cutter = base_bore.union(cb_bottom)

        positions = [(0, y) for y in self.pin_hole_ys]
        for x, y in positions:
            part = part.cut(orient_to_neg_x(cutter, -h, y, hz))
            part = part.cut(orient_to_pos_x(cutter,  h, y, hz))
        return part

    # ── 4. Shaft bore + boss clearance ───────────────────────────────────────────

    def _cut_shaft_hole(self, part: cq.Workplane) -> cq.Workplane:
        """Cut clearance void for the servo saver spring + shaft."""
        cy = self.servo_center_y

        # The spring max compressed height reaches Z=20.5 absolute.
        # Spring radius is ~5.015. With 0.15 clearance -> 5.165.
        spring_r = Shaft.OUTER_R + 0.15

        # We start the cut down inside the servo cavity (Z=8.0) and push up to the 20.5mm ceiling.
        spring_clearance = cylinder(spring_r, 20.5 - 8.0, center=(0, cy, 8.0))
        part = part.cut(spring_clearance)

        # Ceiling clearance bore for the rigid shaft / lego axle
        # to poke out through the top (Z = 20.4 to Z = 21.3)
        # Shaft top core radius is 3.4. Clearance 0.15 -> 3.55.
        ceiling_clearance = cylinder(3.55, 21.3 - 20.4, center=(0, cy, 20.4))
        return part.cut(ceiling_clearance)

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
        from models.cq_utils import cylinder
        from models.lego.cutters.technic_pin_hole import TECHNIC_PIN_CB_DIAMETER

        z0 = self.top_plate_z
        depth = self.total_height - z0

        # We need an infinite cut to ensure cutters cleanly pierce Z=21.2 without coincident face artifacts
        axle_cutter = TechnicAxleHole(depth=depth + 1.0).solid

        base_pin = TechnicPinHole.standard(depth=depth).solid
        top_cb_overcut = cylinder(TECHNIC_PIN_CB_DIAMETER / 2, 2.0, center=(0, 0, depth))
        pin_cutter = base_pin.union(top_cb_overcut)

        axle_positions = [
            (0.0,  2.4), (0.0, -13.6),
            (-8.0, -5.6), (8.0, -5.6),
        ]

        part = cut_at_positions(part, pin_cutter,  self.top_pin_positions, z_offset=z0)
        part = cut_at_positions(part, axle_cutter, axle_positions,              z_offset=z0)
        return part

    # ── 7. Holes for the Clamp ───────────────────────────────────────────────

    def _cut_clamp_lock(self, part: cq.Workplane) -> cq.Workplane:
        """Cut a vertical dovetail socket for the clamp to slide into from the top.
        This provides a secure lateral interlock without Y-axis bridging overhead.
        Designed to be secured permanently with super glue.
        """
        center_x = (self.arm_inner_x + self._half) / 2.0

        from models.mechanical.joints import DovetailJoint

        joint = DovetailJoint(
            neck_width=self.DOVETAIL_NECK_HW * 2.0,
            tail_width=self.DOVETAIL_TAIL_HW * 2.0,
            depth=2.0,
            length=3.7,
            clearance=0.05
        )

        socket_cutter = joint.female(overlap=2.0)

        # Extrude vertically just enough to house the half-height (3.0mm) clamp pin (plus 0.2mm Z clearance)
        # This leaves the upper half of the base's locking face intact.
        socket_right = (
            socket_cutter
            .rotate((0,0,0), (0,0,1), 180)
            .translate((center_x, 6.4, -0.5))
        )
        socket_left = (
            socket_cutter
            .rotate((0,0,0), (0,0,1), 180)
            .translate((-center_x, 6.4, -0.5))
        )

        # Cut on both arms
        part = part.cut(socket_right)
        part = part.cut(socket_left)
        return part

    # ── 8. Round back corners below clamp arm ────────────────────────────────

    def _cut_back_corners(self, part: cq.Workplane) -> cq.Workplane:
        """Round the back (+Y) corners of the main body ONLY above the clamp arm (Z >= 6.0).
        This removes the sharp vertical edges perfectly flush with the 6mm thick arm.
        """
        r = self.corner_r
        cx = self._half - r
        cy = (self.servo_center_y + self._half) - r

        # Start at Z=6.0 (where the clamp arm ends) and cut upwards to the top face
        # We add 1.0 mm to the cut height to ensure an infinite cutter overcut past Z=21.2
        z_start = 6.0
        cut_h = (self.total_height - z_start) + 1.0

        # Build a negative fillet cutter tool using exact centers
        tool = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(r + 1.0, r + 1.0, centered=False)
            .extrude(cut_h)
        )
        cyl = (
            cq.Workplane("XY")
            .center(cx, cy)
            .circle(r)
            .extrude(cut_h)
        )

        # Determine the shape of the corner to remove, positioned at the correct Z
        corner_tool = tool.cut(cyl).translate((0, 0, z_start))

        # Cut right corner and mirror to the left
        part = part.cut(corner_tool)
        part = part.cut(corner_tool.mirror("YZ"))
        return part



    @property
    def solid(self) -> cq.Workplane:
        return self._solid


class ServoMountClamp:
    """Clamp arm for the full servo mount.

    This U-shaped bridge attaches to the cut step-notches of `ServoMountBase` (at Y=4.4),
    extends around the servo body, and provides a mounting pad for the second
    servo tab (located at Y=13.5 in Assembly coordinates) with a firm 6mm thick
    screwing block to resist spring-induced tilting.

    It is designed to be printed flat on its bottom face (Z=0).
    """

    def __init__(self, outer_x: float = 12.0, arm_inner_x: float = 6.8):
        self.outer_x = outer_x
        self.arm_inner_x = arm_inner_x
        self.neck_hw = ServoMountBase.DOVETAIL_NECK_HW
        self.tail_hw = ServoMountBase.DOVETAIL_TAIL_HW
        # Center the screw holes in the main clamp arm thickness
        self.hole_x = (self.outer_x + self.arm_inner_x) / 2.0
        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        # Base dimensions (in assembly coordinates):
        # We start the clamp deep inside the base's locking steps.
        # Apply a 0.05 mm Y-axis clearance gap for the primary planar mating face
        gap = 0.05

        w_out = self.outer_x
        w_in = self.arm_inner_x

        clamp_y_start = 6.4 + gap

        clamp_profile = (
            cq.Workplane("XY")
            .moveTo(-w_in, clamp_y_start)
            .lineTo(-w_out, clamp_y_start)
            .lineTo(-w_out, 16.8)
            .lineTo(w_out, 16.8)
            .lineTo(w_out, clamp_y_start)
            .lineTo(w_in, clamp_y_start)
            .lineTo(w_in, 11.1)
            .lineTo(-w_in, 11.1)
            .close()
            .extrude(6.0)
        )

        # Round the two outer back corners (near Y=16.8) to match the main base
        def select_back_edges(e):
            return e.Center().y > 16.0
        clamp = clamp_profile.edges("|Z").filter(select_back_edges).fillet(4.0)

        # Add the vertical dovetail pins
        from models.mechanical.joints import DovetailJoint

        center_x = self.hole_x
        pin_y_start = clamp_y_start
        pin_y_end = 4.4

        joint = DovetailJoint(
            neck_width=self.neck_hw * 2.0,
            tail_width=self.tail_hw * 2.0,
            depth=(pin_y_start - pin_y_end),
            length=3.0,
            clearance=0.0
        )

        pin_tool = joint.male(overlap=1.0)
        
        pin_right = (
            pin_tool
            .rotate((0,0,0), (0,0,1), 180)
            .translate((center_x, pin_y_start, 0))
        )
        pin_left = (
            pin_tool
            .rotate((0,0,0), (0,0,1), 180)
            .translate((-center_x, pin_y_start, 0))
        )

        clamp = clamp.union(pin_right)
        clamp = clamp.union(pin_left)

        # (Horizontal mounting screws removed in favor of glue + vertical dovetail)

        # Add the vertical screw hole for the servo tab.
        # The tab hole is at Y=13.5 (19.1 in servo coords - 5.6).
        # We need a countersunk hole matching the base: bore R=0.8
        tab_cutter = countersunk_hole(
            bore_r=0.8,
            bore_depth=6.0,
            cs_r=1.43,
            cs_depth=0.5,
            center=(0, 13.5, 0)
        )
        clamp = clamp.cut(tab_cutter)

        assert len(clamp.solids().vals()) == 1, "Expected single solid, got multiple pieces"
        return clamp

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


class ServoMountAssembly:
    """Pre-arranged print plate / assembly containing both base and clamp.

    Since the clamp and base are designed to sit flush on Z=0 and are spaced
    along the Y axis, they can be exported as a single compound STEP file
    for easy importing into slicers.
    """
    def __init__(self):
        self.base = ServoMountBase()
        self.clamp = ServoMountClamp(
            outer_x=self.base.outer_size / 2,
            arm_inner_x=self.base.arm_inner_x
        )
        self._solid = cq.Workplane("XY").add(self.base.solid).add(self.clamp.solid)

    @property
    def solid(self) -> cq.Workplane:
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show
    base = ServoMountBase()
    clamp = ServoMountClamp(outer_x=base.outer_size/2, arm_inner_x=base.arm_inner_x)
    show(base.solid, clamp.solid)
