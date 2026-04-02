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

import math
import cadquery as cq
from models.print_settings import ToleranceProfile, get_profile

class ClearanceHole:
    """
    A simple cylindrical through-hole or blind-hole.
    Origin lies exactly at the Z=0 plane (opening).
    """

    def __init__(
        self,
        diameter: float,
        depth: float,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.diameter = diameter
        self.depth = depth
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    @property
    def solid(self) -> cq.Workplane:
        """Returns the positive hole geometry."""
        r = (self.diameter / 2.0) + self.tolerance.radial_clearance
        return cq.Workplane("XY", origin=(0, 0, -self.depth)).circle(r).extrude(self.depth)

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        """
        Tool for boolean subtraction.
        Z extrudes from `-(depth + overcut)` all the way up through the Z=0 boundary `+ overcut`.
        """
        r = (self.diameter / 2.0) + self.tolerance.radial_clearance
        return cq.Workplane("XY", origin=(0, 0, -(self.depth + overcut))).circle(r).extrude(self.depth + 2 * overcut)

class CounterboreHole:
    """
    A composite hole containing a shaft and a head recess (counterbore/countersink).
    Origin lies at the Z=0 mating surface of the part being bolted down.
    The primary use is for boolean subtraction to make room for fasteners.
    """

    def __init__(
        self,
        shaft_diameter: float,
        shaft_depth: float,
        head_diameter: float,
        head_depth: float,
        head_type: str = "cylinder",
        head_angle: float = 90.0,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.shaft_diameter = shaft_diameter
        self.shaft_depth = shaft_depth
        self.head_diameter = head_diameter
        self.head_depth = head_depth
        self.head_type = head_type
        self.head_angle = head_angle
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    @property
    def solid(self) -> cq.Workplane:
        """Positive representation of the hole, anchored at Z=0."""
        shaft_r = (self.shaft_diameter / 2.0) + self.tolerance.radial_clearance
        shaft = cq.Workplane("XY", origin=(0, 0, -self.shaft_depth)).circle(shaft_r).extrude(self.shaft_depth)

        head_r = (self.head_diameter / 2.0) + max(0.0, self.tolerance.screw_radial_allowance)
        z_recess = -self.tolerance.screw_head_recess

        if self.head_type == "cone":
            angle_rad = math.radians(self.head_angle / 2.0)
            cone_h = (head_r - shaft_r) / math.tan(angle_rad)
            head = (cq.Workplane("XY", origin=(0, 0, z_recess - cone_h))
                    .circle(shaft_r).workplane(offset=cone_h).circle(head_r).loft())
        else:
            head = cq.Workplane("XY", origin=(0, 0, z_recess)).circle(head_r).extrude(self.head_depth)

        return shaft.union(head)

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        """Boolean subtraction tool with infinite overhang for clean cuts."""
        shaft_r = (self.shaft_diameter / 2.0) + self.tolerance.radial_clearance
        shaft = cq.Workplane("XY", origin=(0, 0, -(self.shaft_depth + overcut))).circle(shaft_r).extrude(self.shaft_depth + overcut + 1)

        head_r = (self.head_diameter / 2.0) + max(0.0, self.tolerance.screw_radial_allowance)
        z_recess = -self.tolerance.screw_head_recess

        if self.head_type == "cone":
            angle_rad = math.radians(self.head_angle / 2.0)
            cone_h = (head_r - shaft_r) / math.tan(angle_rad)
            cone = (cq.Workplane("XY", origin=(0, 0, z_recess - cone_h))
                    .circle(shaft_r).workplane(offset=cone_h).circle(head_r).loft())
            head_overcut = cq.Workplane("XY", origin=(0, 0, z_recess)).circle(head_r).extrude(overcut)
            head = cone.union(head_overcut)
        else:
            head = cq.Workplane("XY", origin=(0, 0, z_recess)).circle(head_r).extrude(max(self.head_depth, 0.0) + overcut)

        return shaft.union(head)


class TeardropHole:
    """
    A teardrop-shaped through hole (avoids overhangs when 3D printed horizontally).
    """

    def __init__(
        self,
        diameter: float,
        depth: float,
        angle: float = 45.0,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.diameter = diameter
        self.depth = depth
        self.angle = angle
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    def _get_teardrop_wire(self) -> cq.Workplane:
        """Generates the 2D footprint."""
        r = (self.diameter / 2.0) + self.tolerance.radial_clearance
        # A simple teardrop polygon combined with an arc
        # We'll just trace half the circle into a point
        return cq.Workplane("XY").polyline([
            (r * math.cos(math.radians(135)), r * math.sin(math.radians(135))),
            (0, r / math.cos(math.radians(45))),
            (r * math.cos(math.radians(45)), r * math.sin(math.radians(45)))
        ]).close().union(cq.Workplane("XY").circle(r))

    @property
    def solid(self) -> cq.Workplane:
        return self._get_teardrop_wire().extrude(self.depth).translate((0, 0, -self.depth))

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        return self._get_teardrop_wire().extrude(self.depth + 2 * overcut).translate((0, 0, -(self.depth + overcut)))


class SlottedHole:
    """
    An oblong (pill-shaped) slotted hole, typically used for adjustable mounting.
    The slot is centered at the origin, extending along the X-axis.
    `length` is the total length of the slot tip-to-tip.
    """

    def __init__(
        self,
        diameter: float,
        length: float,
        depth: float,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.diameter = diameter
        self.length = length
        self.depth = depth
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    @property
    def solid(self) -> cq.Workplane:
        r = (self.diameter / 2.0) + self.tolerance.radial_clearance
        # CadQuery slot2D takes overall length and diameter
        l = max(self.length, self.diameter) # Prevent invalid slots where length < diameter
        return cq.Workplane("XY", origin=(0, 0, -self.depth)).slot2D(l, r * 2).extrude(self.depth)

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        r = (self.diameter / 2.0) + self.tolerance.radial_clearance
        l = max(self.length, self.diameter)
        return cq.Workplane("XY", origin=(0, 0, -(self.depth + overcut))).slot2D(l, r * 2).extrude(self.depth + 2 * overcut)


class TaperedHole:
    """
    A hole with a draft/taper angle (conical frustum), typically used for 
    Heat-Set Threaded Inserts to allow them to self-align and displace plastic.
    The larger opening is at Z=0, tapering inward as it goes down to `-depth`.
    """

    def __init__(
        self,
        top_diameter: float,
        bottom_diameter: float,
        depth: float,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.top_diameter = top_diameter
        self.bottom_diameter = bottom_diameter
        self.depth = depth
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    @property
    def solid(self) -> cq.Workplane:
        top_r = (self.top_diameter / 2.0) + self.tolerance.radial_clearance
        bot_r = (self.bottom_diameter / 2.0) + self.tolerance.radial_clearance
        return (cq.Workplane("XY", origin=(0, 0, -self.depth))
                .circle(bot_r).workplane(offset=self.depth).circle(top_r).loft())

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        # For the cutter, we must extend the top and bottom cones straight out
        # rather than just lofting the overcuts, to avoid unintended scaling
        top_r = (self.top_diameter / 2.0) + self.tolerance.radial_clearance
        bot_r = (self.bottom_diameter / 2.0) + self.tolerance.radial_clearance
        
        main_cone = (cq.Workplane("XY", origin=(0, 0, -self.depth))
                     .circle(bot_r).workplane(offset=self.depth).circle(top_r).loft())
        
        top_overcut = cq.Workplane("XY", origin=(0, 0, 0)).circle(top_r).extrude(overcut)
        bot_overcut = cq.Workplane("XY", origin=(0, 0, -self.depth - overcut)).circle(bot_r).extrude(overcut)
        
        return main_cone.union(top_overcut).union(bot_overcut)

class Keyhole:
    """
    A keyhole slot typically used for wall mounting.
    Includes a larger insertion hole for the screw head, and a narrower slot for the shaft.
    The main insertion hole is at the origin, and the slot tracks along the +X axis by `length`.
    """

    def __init__(
        self,
        head_diameter: float,
        shaft_diameter: float,
        length: float,
        depth: float,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.head_diameter = head_diameter
        self.shaft_diameter = shaft_diameter
        self.length = length
        self.depth = depth
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    def _get_keyhole_wire(self) -> cq.Workplane:
        head_r = (self.head_diameter / 2.0) + self.tolerance.radial_clearance
        shaft_r = (self.shaft_diameter / 2.0) + self.tolerance.radial_clearance
        
        # Base circular entry for the head
        entry = cq.Workplane("XY").circle(head_r)
        
        # Linear slot for the main shaft (starting from origin going to length)
        # slot2D centers the slot. We want it offset so it goes from X=0 to X=length.
        # Length of slot = self.length, but slot2D takes total tip-to-tip length.
        # We place it at X = length / 2 to span from 0 to length
        slot = cq.Workplane("XY", origin=(self.length / 2.0, 0, 0)).slot2D(self.length + shaft_r * 2, shaft_r * 2)
        
        return entry.union(slot)

    @property
    def solid(self) -> cq.Workplane:
        return self._get_keyhole_wire().extrude(self.depth).translate((0, 0, -self.depth))

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        return self._get_keyhole_wire().extrude(self.depth + 2 * overcut).translate((0, 0, -(self.depth + overcut)))


class CaptiveNutPocket:
    """
    A hexagonal pocket designed to securely trap a standard nut, preventing it from spinning.
    The pocket is centered at the origin, with the hex flats aligned to the axes.
    `width_across_flats` is the standard flat-to-flat span of the nut.
    """

    def __init__(
        self,
        width_across_flats: float,
        thickness: float,
        profile: ToleranceProfile | str = "fdm_standard"
    ):
        self.width_across_flats = width_across_flats
        self.thickness = thickness
        self._profile = profile

    @property
    def tolerance(self) -> ToleranceProfile:
        if isinstance(self._profile, str):
            return get_profile(self._profile)
        return self._profile

    @property
    def solid(self) -> cq.Workplane:
        # In CadQuery, polygon(6, diameter) defines a circumscribed circle diameter.
        # Width Across Flats (WAF) = Inscribed Circle Diameter
        # circumscribed diameter = WAF / cos(30 degrees)
        r_inscribed = (self.width_across_flats / 2.0) + self.tolerance.radial_clearance
        r_circumscribed = r_inscribed / math.cos(math.radians(30))
        
        return cq.Workplane("XY", origin=(0, 0, -self.thickness)).polygon(6, r_circumscribed * 2).extrude(self.thickness)

    def to_cutter(self, overcut: float = 100.0) -> cq.Workplane:
        r_inscribed = (self.width_across_flats / 2.0) + self.tolerance.radial_clearance
        r_circumscribed = r_inscribed / math.cos(math.radians(30))
        
        # A trapped nut usually only cuts down into the object (not infinitely out the back), 
        # but to allow boolean subtraction from a surface Z=0 we give it a top overcut.
        return cq.Workplane("XY", origin=(0, 0, -(self.thickness + overcut))).polygon(6, r_circumscribed * 2).extrude(self.thickness + overcut * 2)

