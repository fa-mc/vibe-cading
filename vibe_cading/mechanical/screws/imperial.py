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

from typing import Literal

import cadquery as cq

IMPERIAL_SIZES = {
    "4-40": {"major_dia": 2.845, "socket_head_dia": 5.2, "socket_head_h": 2.8, "flat_head_dia": 5.7, "flat_head_h": 1.7, "pan_head_dia": 5.5, "pan_head_h": 2.0},
    "6-32": {"major_dia": 3.505, "socket_head_dia": 5.7, "socket_head_h": 3.5, "flat_head_dia": 7.1, "flat_head_h": 2.1, "pan_head_dia": 7.0, "pan_head_h": 2.5},
    "8-32": {"major_dia": 4.166, "socket_head_dia": 6.8, "socket_head_h": 4.1, "flat_head_dia": 8.5, "flat_head_h": 2.5, "pan_head_dia": 8.0, "pan_head_h": 3.0},
    "10-24": {"major_dia": 4.826, "socket_head_dia": 7.9, "socket_head_h": 4.8, "flat_head_dia": 9.8, "flat_head_h": 2.9, "pan_head_dia": 9.5, "pan_head_h": 3.4},
    "1/4-20": {"major_dia": 6.350, "socket_head_dia": 9.5, "socket_head_h": 6.3, "flat_head_dia": 13.0, "flat_head_h": 3.9, "pan_head_dia": 12.5, "pan_head_h": 4.4},
}

class ImperialMachineScrew:
    """Standard Unified Thread Standard (UTS) Imperial machine screws."""
    def __init__(
        self,
        length: float,
        major_diameter: float,
        head_diameter: float,
        head_height: float,
        head_type: Literal["socket", "flat", "pan"] = "socket",
        drive_type: Literal["hex", "phillips", "slotted", "torx"] = "hex",
        head_angle: float = 82.0
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.head_diameter = float(head_diameter)
        self.head_height = float(head_height)
        self.head_type = head_type.lower()
        self.drive_type = drive_type
        self.head_angle = float(head_angle)

    @classmethod
    def from_size(cls, size: Literal["4-40", "6-32", "8-32", "10-24", "1/4-20"], length: float, head_type: Literal["socket", "flat", "pan"] = "socket", drive_type: Literal["hex", "phillips", "slotted", "torx"] = "hex") -> "ImperialMachineScrew":
        size = size.lower()
        if size not in IMPERIAL_SIZES:
            raise ValueError(f"Unsupported imperial size: {size}. Available: {list(IMPERIAL_SIZES.keys())}")
        
        data = IMPERIAL_SIZES[size]
        head_type = head_type.lower()

        if head_type == "flat":
            head_dia = data["flat_head_dia"]
            head_h = data["flat_head_h"]
            head_angle = 82.0
        elif head_type == "socket":
            head_dia = data["socket_head_dia"]
            head_h = data["socket_head_h"]
            head_angle = 82.0
        elif head_type in ["pan", "button"]:
            head_dia = data["pan_head_dia"]
            head_h = data["pan_head_h"]
            head_angle = 82.0
        else:
            raise ValueError(f"Unsupported head type: {head_type}. Choose 'socket', 'flat', or 'pan'.")

        return cls(
            length=length,
            major_diameter=data["major_dia"],
            head_diameter=head_dia,
            head_height=head_h,
            head_type=head_type,
            drive_type=drive_type,
            head_angle=head_angle
        )

    @property
    def solid(self) -> cq.Workplane:
        if self.head_type == "flat":
            r1 = self.head_diameter / 2.0
            r2 = self.major_diameter / 2.0
            head = cq.Workplane("XY").circle(r1).workplane(offset=-self.head_height).circle(r2).loft()
        else:
            if self.head_type == "socket":
                head = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height)
            elif self.head_type in ["pan", "button"]:
                head_cyl = cq.Workplane("XY").circle(self.head_diameter / 2.0).extrude(self.head_height - 0.5)
                comp = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, self.head_height - 0.5))
                        .circle(self.head_diameter / 2.0).workplane(offset=0.5).circle(self.head_diameter / 3.0).loft())
                head = head_cyl.union(comp)

        shaft_z = -self.head_height if self.head_type == "flat" else 0.0
        shaft_len = self.length - self.head_height if self.head_type == "flat" else self.length
        shaft = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, shaft_z)).circle(self.major_diameter / 2.0).extrude(-shaft_len)

        return head.union(shaft)

    def to_cutter(self, profile=None, fit: str = "clearance") -> cq.Workplane:
        """Boolean-subtraction tool for the imperial machine screw.

        :param profile: Optional :class:`ToleranceProfile`.  Forwarded to
            the underlying :class:`CounterboreHole`.
        :param fit: ``"clearance"`` (free-pass), ``"tap"`` (tight,
            tapped), or ``"interference"`` (press fit).  Imperial sizes
            don't ship explicit clearance / tap drill data so we derive
            them from the major diameter with empirical per-side offsets
            (preserving the pre-Phase-5 ``+0.15`` / ``-0.15`` / ``-0.3``
            literals).
        """
        if fit == "clearance":
            shaft_dia = self.major_diameter + 0.30  # +0.15 per side
        elif fit == "tap":
            shaft_dia = self.major_diameter - 0.30  # -0.15 per side
        elif fit == "interference":
            shaft_dia = self.major_diameter - 0.60  # -0.30 per side
        else:
            raise ValueError(
                f"ImperialMachineScrew to_cutter fit must be 'clearance', "
                f"'tap', or 'interference', got {fit!r}"
            )

        from vibe_cading.mechanical.holes import CounterboreHole
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

