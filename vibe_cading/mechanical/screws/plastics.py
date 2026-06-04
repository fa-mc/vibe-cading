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
from typing import Literal

import cadquery as cq

PLASTIC_SCREW_SIZES = {
    "M2": {"major_dia": 2.0, "core_dia": 1.2, "pilot_dia": 1.6, "pan_head_dia": 4.0, "pan_head_h": 1.6, "flat_head_dia": 3.8, "flat_head_h": 1.2},
    "M2.5": {"major_dia": 2.5, "core_dia": 1.5, "pilot_dia": 2.0, "pan_head_dia": 5.0, "pan_head_h": 2.1, "flat_head_dia": 4.7, "flat_head_h": 1.5},
    "M3": {"major_dia": 3.0, "core_dia": 1.8, "pilot_dia": 2.4, "pan_head_dia": 6.0, "pan_head_h": 2.4, "flat_head_dia": 5.5, "flat_head_h": 1.65},
    "M4": {"major_dia": 4.0, "core_dia": 2.3, "pilot_dia": 3.2, "pan_head_dia": 8.0, "pan_head_h": 3.1, "flat_head_dia": 8.4, "flat_head_h": 2.7},
    "M5": {"major_dia": 5.0, "core_dia": 2.8, "pilot_dia": 4.0, "pan_head_dia": 10.0, "pan_head_h": 3.8, "flat_head_dia": 9.3, "flat_head_h": 2.7},
}

class PlasticsScrew:
    """
    Self-tapping / thread-forming screws designed for plastics (e.g. PT screws).
    """
    def __init__(
        self,
        length: float,
        major_diameter: float,
        core_diameter: float,
        pilot_diameter: float,
        head_diameter: float,
        head_height: float,
        head_type: Literal["pan", "flat"] = "pan",
        drive_type: Literal["phillips", "hex", "slotted", "torx"] = "phillips",
        head_angle: float = 90.0,
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.core_diameter = float(core_diameter)
        self.pilot_diameter = float(pilot_diameter)
        self.head_diameter = float(head_diameter)
        self.head_height = float(head_height)
        self.head_type = head_type.lower()
        self.drive_type = drive_type
        self.head_angle = float(head_angle)

    @classmethod
    def from_size(cls, size: Literal["M2", "M2.5", "M3", "M4", "M5"], length: float, head_type: Literal["pan", "flat"] = "pan", drive_type: Literal["phillips", "hex", "slotted", "torx"] = "phillips") -> "PlasticsScrew":
        size = size.upper()
        if size not in PLASTIC_SCREW_SIZES:
            raise ValueError(f"Unsupported plastic screw size: {size}. Available: {list(PLASTIC_SCREW_SIZES.keys())}")
        
        data = PLASTIC_SCREW_SIZES[size]
        head_type = head_type.lower()

        if head_type == "flat":
            head_dia = data["flat_head_dia"]
            head_h = data["flat_head_h"]
            head_angle = 90.0
        elif head_type == "pan":
            head_dia = data["pan_head_dia"]
            head_h = data["pan_head_h"]
            head_angle = 0.0
        else:
            raise ValueError(f"Unsupported head type: {head_type}. Choose 'flat' or 'pan'.")

        return cls(
            length=length,
            major_diameter=data["major_dia"],
            core_diameter=data["core_dia"],
            pilot_diameter=data["pilot_dia"],
            head_diameter=head_dia,
            head_height=head_h,
            head_type=head_type,
            drive_type=drive_type,
            head_angle=head_angle
        )

    @property
    def solid(self) -> cq.Workplane:
        shaft = cq.Workplane("XY").circle(self.major_diameter / 2).extrude(-self.length)
        core = cq.Workplane("XY").circle(self.core_diameter / 2).extrude(-self.length)
        
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            r2 = self.major_diameter / 2.0
            angle_rad = math.radians(self.head_angle / 2.0)
            physical_cone_height = (r1 - r2) / math.tan(angle_rad)
            head = cq.Workplane("XY", origin=(0,0,-physical_cone_height)).circle(r2).workplane(offset=physical_cone_height).circle(r1).loft()
            return core.union(shaft.edges("<Z").fillet(0.2)).union(head)
        else:
            head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            try:
                head = head.edges(">Z").fillet(self.head_height * 0.4)
            except:
                pass
            return core.union(shaft.edges("<Z").fillet(0.2)).union(head)

    def to_cutter(self, profile=None, fit: str = "tap") -> cq.Workplane:
        """Boolean-subtraction tool for self-tapping plastics screws.

        :param profile: Optional :class:`ToleranceProfile`.  Forwarded to
            the underlying :class:`CounterboreHole`.
        :param fit: ``"tap"`` (pilot-bore for thread-forming) or
            ``"clearance"`` (free-pass for the major shank).  Defaults to
            ``"tap"`` since the dominant use-case for plastics screws is
            thread-forming into a pilot hole.
        """
        if fit == "tap":
            shaft_dia = self.pilot_diameter
        elif fit == "clearance":
            # Add the historical ``+0.1`` per-side fudge on top of the
            # major diameter so plastics-clearance bores end up slightly
            # looser than tap; the profile then adds ``free.radial`` on
            # top inside ``CounterboreHole``.
            shaft_dia = self.major_diameter + 0.2
        else:
            raise ValueError(
                f"PlasticsScrew to_cutter fit must be 'tap' or 'clearance', got {fit!r}"
            )

        from vibe_cading.mechanical.holes import CounterboreHole
        # Resolve ``None`` to the env-configured default; preserves the
        # pre-Phase-5 ``profile or get_profile()`` fallback so callers
        # (notably the ``demo()`` classmethod and external scripts) can
        # invoke ``to_cutter()`` without explicitly plumbing a profile.
        from vibe_cading.print_settings import get_profile
        prof = profile if profile is not None else get_profile()

        hole = CounterboreHole(
            shaft_diameter=shaft_dia,
            shaft_depth=self.length,
            head_diameter=self.head_diameter,
            head_depth=self.head_height,
            head_type="cylinder" if self.head_type != "flat" else "cone",
            head_angle=self.head_angle if self.head_type == "flat" else 90.0,
            profile=prof,
        )
        return hole.to_cutter()

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show M3-10 pan/flat plastics screws each with their tap cutter."""
        screw1 = cls.from_size("M3", 10, head_type="pan")
        screw2 = cls.from_size("M3", 10, head_type="flat")

        return [
            (screw1.solid.translate((-5, 0, 0)),                  "M3 Pan",      "royalblue"),
            (screw1.to_cutter(fit="tap").translate((-5, 10, 0)),  "Pan Cutter",  "gold"),
            (screw2.solid.translate(( 5, 0, 0)),                  "M3 Flat",     "tomato"),
            (screw2.to_cutter(fit="tap").translate(( 5, 10, 0)),  "Flat Cutter", "seagreen"),
        ]
