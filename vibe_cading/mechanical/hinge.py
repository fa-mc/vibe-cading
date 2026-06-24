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

import cadquery as cq
from vibe_cading.print_settings import ToleranceProfile

class PrintInPlaceHinge:
    """
    Parametric Print-in-Place Hinge.

    The origin (0,0,0) is located precisely at the center of the hinge axis.
    The hinge is split along the X-axis:
      - Leaf A extends towards +X.
      - Leaf B extends towards -X.

    The hinge pivots on the Y-axis. The mating mechanism relies on
    45-degree conical pins and sockets to allow FDM printing.

    When ``screw_holes=True`` (default), 2 countersunk M3 flat-head screw
    holes are cut into each leaf (4 total) using the ``MetricMachineScrew``
    cutter, tolerance-profile-driven.  Set ``screw_holes=False`` to suppress
    all holes (e.g. when embedding the hinge into an assembly that uses a
    different fastening method).

    Screw-hole positions are computed parametrically from ``leaf_length`` and
    ``width`` so they remain valid across different hinge sizes:
      - X: ``leaf_length * 0.65`` from the hinge axis (one column per leaf).
      - Y: ``± width * 0.25`` (symmetric about Y=0).
    For default 20 mm leaf and 30 mm width this gives X=13.0, Y=±7.5.

    The countersink opens on the **plate top face** (Z = plate top, the face
    facing the hinge knuckle side).  The screw is inserted from that side so
    its head recesses flush with the plate and the shank exits the bottom face
    to engage the mounting substrate.
    """

    def __init__(
        self,
        width: float = 30.0,
        leaf_a_length: float = 20.0,
        leaf_b_length: float = 20.0,
        leaf_a_width: float = None,
        leaf_b_width: float = None,
        thickness: float = 4.0,
        knuckle_diameter: float = 10.0,
        knuckle_count: int = 3,
        angle: float = 0.0,
        screw_holes: bool = True,
        profile: ToleranceProfile = None
    ):
        if profile is None:
            from vibe_cading.print_settings import get_profile
            profile = get_profile("fdm_standard")

        self.width = width
        self.leaf_a_length = leaf_a_length
        self.leaf_b_length = leaf_b_length
        self.leaf_a_width = leaf_a_width if leaf_a_width is not None else width
        self.leaf_b_width = leaf_b_width if leaf_b_width is not None else width
        self.thickness = thickness
        self.knuckle_diameter = knuckle_diameter
        self.knuckle_count = max(2, knuckle_count)
        self.angle = angle
        self.screw_holes = screw_holes
        self._profile = profile
        self.clearance = profile.free.radial
        self.face_gap = profile.free.radial
        
        # Calculate knuckle segments
        self.total_gaps = (self.knuckle_count - 1) * self.face_gap
        self.knuckle_width = (self.width - self.total_gaps) / self.knuckle_count
        
        # Conical pin parameters
        self.cone_height = min((self.knuckle_width / 2.0) - 0.5, (self.knuckle_diameter / 2.0) - 1.0)
        self.cone_height = max(1.0, self.cone_height)
        self.cone_base_radius = self.cone_height
        
        # Pre-compute alternating knuckle gap positions
        self._gaps_list = []
        start_y = -self.width / 2.0
        for i in range(self.knuckle_count):
            end_y = start_y + self.knuckle_width
            if i < self.knuckle_count - 1:
                y_gap = end_y + self.face_gap / 2.0
                self._gaps_list.append((i, i+1, y_gap))
            start_y = end_y + self.face_gap

        # Build the two leaves
        self.leaf_a = self._build_leaf_a()
        self.leaf_b = self._build_leaf_b()
        
        # Apply user rotation to Leaf B relative to Leaf A
        if self.angle != 0.0:
            self.leaf_b = self.leaf_b.rotate((0, 0, 0), (0, 1, 0), self.angle)

    def _compute_screw_hole_centers(
        self, leaf_length: float
    ) -> list[tuple[float, float]]:
        """Return 2 (X, Y) hole-center pairs for one leaf (leaf_a coords, +X).

        Positions are computed parametrically so they scale with leaf geometry:
          - X = leaf_length * 0.65  (single column, verified clear of knuckle zone)
          - Y = ± width * 0.25     (symmetric about Y=0)

        For the default 20 mm leaf and 30 mm width: X=13.0, Y=±7.5.

        Margins are asserted at construction time:
          - inner margin (hole edge to knuckle clearance zone) >= 0.5 mm
          - outer margin (hole edge to leaf tip)               >= 0.5 mm
          - Y-edge margin (hole edge to leaf side)             >= 0.5 mm

        Raises ``ValueError`` if any margin is violated (e.g. very short or
        narrow leaf combined with a large knuckle_diameter).
        """
        # Resolve the M3 flat-head cutter head radius (with profile tolerance).
        # M3 flat_head_dia = 5.5 mm nominal (METRIC_SIZES["M3"]["flat_head_dia"]).
        # CounterboreHole inflates the head by free.radial on each side, so:
        #   head_r_with_tol = (5.5 + free.radial * 2) / 2
        head_r = (5.5 + self._profile.free.radial * 2) / 2.0
        # The knuckle clearance zone half-width on X (same formula as _build_leaf_a):
        clearance_x_half = (self.knuckle_diameter + self.face_gap * 4) / 2.0

        hole_x = leaf_length * 0.65
        hole_y = self.width * 0.25

        # Margin validation
        inner_margin = hole_x - head_r - clearance_x_half
        if inner_margin < 0.5:
            raise ValueError(
                f"Screw hole inner margin {inner_margin:.2f} mm < 0.5 mm "
                f"(hole_x={hole_x:.2f}, head_r={head_r:.2f}, "
                f"clearance_zone_half={clearance_x_half:.2f}).  "
                f"Increase leaf_length or decrease knuckle_diameter."
            )
        outer_margin = leaf_length - hole_x - head_r
        if outer_margin < 0.5:
            raise ValueError(
                f"Screw hole outer margin {outer_margin:.2f} mm < 0.5 mm "
                f"(leaf_length={leaf_length:.2f}, hole_x={hole_x:.2f}, "
                f"head_r={head_r:.2f}).  Increase leaf_length."
            )
        y_edge_margin = self.width / 2.0 - hole_y - head_r
        if y_edge_margin < 0.5:
            raise ValueError(
                f"Screw hole Y-edge margin {y_edge_margin:.2f} mm < 0.5 mm "
                f"(width={self.width:.2f}, hole_y={hole_y:.2f}, "
                f"head_r={head_r:.2f}).  Increase width."
            )

        return [(hole_x, hole_y), (hole_x, -hole_y)]

    def _apply_screw_holes(
        self,
        leaf: cq.Workplane,
        centers: list[tuple[float, float]],
    ) -> cq.Workplane:
        """Cut countersunk M3 flat-head cutter holes into ``leaf`` at ``centers``.

        The cutter origin is placed at the plate top face:
          plate_top_z = thickness / 2 + (thickness - knuckle_diameter) / 2

        For defaults (thickness=4, knuckle_diameter=10):
          plate_top_z = 2 + (4-10)/2 = 2 - 3 = -1.0.
        This is derived from instance attributes — never hardcoded.

        ``centers`` contains (X, Y) pairs already in leaf coordinate space
        (positive X for leaf_a, negative X for leaf_b).
        """
        from vibe_cading.mechanical.screws.metric import MetricMachineScrew
        # Plate top face Z in hinge coordinate space.
        # The box is centered on the XY plane so it spans ±thickness/2 in Z.
        # It is then translated by (thickness - knuckle_diameter) / 2.
        # Plate top face Z = +thickness/2 + translate_z
        #                  = thickness/2 + (thickness - knuckle_diameter) / 2
        # For defaults: 2 + (4-10)/2 = 2 + (-3) = -1.
        plate_top_z = self.thickness / 2 + (self.thickness - self.knuckle_diameter) / 2
        # Sanity: plate_top_z should be <= 0 for typical params (knuckle > thickness).
        # The cutter opens upward from this face toward -Z (INTO the plate),
        # which aligns with CounterboreHole convention (cutter projects -Z).
        cutter = (
            MetricMachineScrew
            .from_size("M3", length=10.0, head_type="flat")
            .to_cutter(profile=self._profile)
        )
        for (hx, hy) in centers:
            leaf = leaf.cut(cutter.translate((hx, hy, plate_top_z)))
        return leaf

    def _get_knuckle_ranges(self, target_parity: int):
        ranges = []
        start_y = -self.width / 2.0
        for i in range(self.knuckle_count):
            end_y = start_y + self.knuckle_width
            if i % 2 == target_parity:
                ranges.append((start_y, end_y, i))
            start_y = end_y + self.face_gap
        return ranges

    def _build_pin(self, y_gap: float, dir_y: int) -> cq.Workplane:
        """ dir_y is 1 for +Y, -1 for -Y. """
        pin_h = self.cone_height - self.clearance
        pin_r = self.cone_base_radius - self.clearance
        
        pin = (
            cq.Workplane("XZ")
            .circle(pin_r)
            .workplane(offset=pin_h)
            .circle(0.01)
            .loft(combine=True)
            # Extrude backwards to join with main body
            .union(cq.Workplane("XZ").circle(pin_r).extrude(-self.face_gap))
        )
        if dir_y == -1:
            pin = pin.rotate((0,0,0), (1,0,0), 180)
            
        return pin.translate((0, y_gap, 0))

    def _build_socket(self, y_gap: float, dir_y: int) -> cq.Workplane:
        """ dir_y is 1 for +Y, -1 for -Y. """
        soc_h = self.cone_height
        soc_r = self.cone_base_radius
        
        soc = (
            cq.Workplane("XZ")
            .circle(soc_r)
            .workplane(offset=soc_h + 0.1) # tiny overcut at tip
            .circle(0.01)
            .loft(combine=True)
            # Extrude backwards past face level to ensure breaking the outer face
            .union(cq.Workplane("XZ").circle(soc_r).extrude(-self.face_gap))
        )
        if dir_y == -1:
            soc = soc.rotate((0,0,0), (1,0,0), 180)
            
        return soc.translate((0, y_gap, 0))

    def _build_leaf_a(self) -> cq.Workplane:
        """Leaf A (+X). Knuckles with even indices (0, 2, 4...)"""
        plate = (
            cq.Workplane("XY")
            .center(self.leaf_a_length / 2, 0)
            .box(self.leaf_a_length, self.leaf_a_width, self.thickness)
        )
        plate = plate.translate((0, 0, (self.thickness - self.knuckle_diameter) / 2))
        
        # Carve rectangular spaces where B's knuckles rotate
        b_ranges = self._get_knuckle_ranges(1)
        clearance_x = self.knuckle_diameter + self.face_gap * 4
        
        for (y_min, y_max, idx) in b_ranges:
            kw = y_max - y_min
            y_mid = (y_min + y_max) / 2
            clearance_box = (
                cq.Workplane("XY")
                .box(clearance_x, kw + self.face_gap * 2, self.knuckle_diameter * 2)
                .translate((0, y_mid, 0))
            )
            plate = plate.cut(clearance_box)

        # Build knuckles
        knuckles_solid = cq.Workplane("XZ")
        a_ranges = self._get_knuckle_ranges(0)
        for (y_min, y_max, idx) in a_ranges:
            y_mid = (y_min + y_max) / 2
            kw = y_max - y_min
            knuckle = cq.Workplane("XZ").cylinder(kw, self.knuckle_diameter / 2).translate((0, y_mid, 0))
            knuckles_solid = knuckles_solid.union(knuckle)
            
        # Attach male pins (which only ever exist on A leaf knuckles)
        for (left_idx, right_idx, y_gap) in self._gaps_list:
            if left_idx % 2 == 0:
                knuckles_solid = knuckles_solid.union(self._build_pin(y_gap, 1))
            elif right_idx % 2 == 0:
                knuckles_solid = knuckles_solid.union(self._build_pin(y_gap, -1))

        leaf = plate.union(knuckles_solid)

        if self.screw_holes:
            # Centers computed in leaf_a (+X) coordinate space.
            centers = self._compute_screw_hole_centers(self.leaf_a_length)
            leaf = self._apply_screw_holes(leaf, centers)
            assert len(leaf.solids().vals()) == 1, (
                "leaf_a screw holes produced floating fragments"
            )

        return leaf

    def _build_leaf_b(self) -> cq.Workplane:
        """Leaf B (-X). Knuckles with odd indices (1, 3, 5...)"""
        plate = (
            cq.Workplane("XY")
            .center(-self.leaf_b_length / 2, 0)
            .box(self.leaf_b_length, self.leaf_b_width, self.thickness)
        )
        plate = plate.translate((0, 0, (self.thickness - self.knuckle_diameter) / 2))
        
        # Carve rectangular spaces where A's knuckles rotate
        a_ranges = self._get_knuckle_ranges(0)
        clearance_x = self.knuckle_diameter + self.face_gap * 4
        
        for (y_min, y_max, idx) in a_ranges:
            kw = y_max - y_min
            y_mid = (y_min + y_max) / 2
            clearance_box = (
                cq.Workplane("XY")
                .box(clearance_x, kw + self.face_gap * 2, self.knuckle_diameter * 2)
                .translate((0, y_mid, 0))
            )
            plate = plate.cut(clearance_box)

        # Build knuckles
        knuckles_solid = cq.Workplane("XZ")
        b_ranges = self._get_knuckle_ranges(1)
        for (y_min, y_max, idx) in b_ranges:
            y_mid = (y_min + y_max) / 2
            kw = y_max - y_min
            knuckle = cq.Workplane("XZ").cylinder(kw, self.knuckle_diameter / 2).translate((0, y_mid, 0))
            knuckles_solid = knuckles_solid.union(knuckle)
            
        # Cut female cavities (which only ever exist on B leaf knuckles)
        for (left_idx, right_idx, y_gap) in self._gaps_list:
            if left_idx % 2 == 0:
                knuckles_solid = knuckles_solid.cut(self._build_socket(y_gap, 1))
            elif right_idx % 2 == 0:
                knuckles_solid = knuckles_solid.cut(self._build_socket(y_gap, -1))

        leaf = plate.union(knuckles_solid)

        if self.screw_holes:
            # Centers for leaf_b: same Y offsets, but X is negated (−X direction).
            centers_a = self._compute_screw_hole_centers(self.leaf_b_length)
            centers = [(-hx, hy) for (hx, hy) in centers_a]
            leaf = self._apply_screw_holes(leaf, centers)
            assert len(leaf.solids().vals()) == 1, (
                "leaf_b screw holes produced floating fragments"
            )

        return leaf

    @property
    def solid(self) -> cq.Workplane:
        """Returns the fully assembled static geometry of the hinge.

        The two leaves are composed via ``cq.Assembly().toCompound()`` and
        then wrapped in a ``cq.Workplane`` so the return type matches the
        project-wide ``.solid -> cq.Workplane`` convention every other
        shipped model class honors.  Without the wrap, downstream tooling
        that assumes a Workplane selector chain (e.g.
        ``tools/check_topology.py`` calling ``.solids().vals()``) crashes
        with ``AttributeError: 'Compound' object has no attribute …``.
        """
        comp = cq.Assembly()
        comp.add(self.leaf_a, name="leaf_a")
        comp.add(self.leaf_b, name="leaf_b")
        return cq.Workplane(obj=comp.toCompound())

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a 5-knuckle, 30°-open print-in-place hinge."""
        hinge = cls(
            width=40,
            knuckle_count=5,
            leaf_a_width=20,
            leaf_b_width=60,
            leaf_a_length=25,
            leaf_b_length=25,
            angle=30,
        )
        return [(hinge.solid, "PrintInPlaceHinge", "lightsteelblue")]
