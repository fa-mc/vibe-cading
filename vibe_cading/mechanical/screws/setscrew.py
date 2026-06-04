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

SET_SCREW_SIZES = {
    "M2": {"major": 2.0, "tap": 1.6, "clearance": 2.2},
    "M2.5": {"major": 2.5, "tap": 2.1, "clearance": 2.7},
    "M3": {"major": 3.0, "tap": 2.5, "clearance": 3.2},
    "M4": {"major": 4.0, "tap": 3.3, "clearance": 4.3},
    "M5": {"major": 5.0, "tap": 4.2, "clearance": 5.3},
}

class SetScrew:
    """
    Headless grub screws / set screws typically used for trapping shafts or locking gears.
    """
    def __init__(
        self,
        length: float,
        major_diameter: float,
        clearance_diameter: float,
        tap_diameter: float,
        drive_type: Literal["hex", "slotted", "torx"] = "hex"
    ):
        self.length = float(length)
        self.major_diameter = float(major_diameter)
        self.clearance_diameter = float(clearance_diameter)
        self.tap_diameter = float(tap_diameter)
        self.drive_type = drive_type

    @classmethod
    def from_size(cls, size: Literal["M2", "M2.5", "M3", "M4", "M5"], length: float, drive_type: Literal["hex", "slotted", "torx"] = "hex") -> "SetScrew":
        size = size.upper()
        if size not in SET_SCREW_SIZES:
            raise ValueError(f"Unsupported grub screw size: {size}. Available: {list(SET_SCREW_SIZES.keys())}")
        data = SET_SCREW_SIZES[size]
        return cls(
            length=length,
            major_diameter=data["major"],
            clearance_diameter=data["clearance"],
            tap_diameter=data["tap"],
            drive_type=drive_type
        )

    @property
    def solid(self) -> cq.Workplane:
        return cq.Workplane("XY").circle(self.major_diameter / 2).extrude(-self.length)

    def to_cutter(self, profile=None, fit: str = "clearance") -> cq.Workplane:
        """Boolean-subtraction tool for trapping the headless set screw.

        :param profile: Optional :class:`ToleranceProfile`.  Forwarded to
            the underlying :class:`ClearanceHole`, which reads
            ``profile.free.radial`` for the bore inflation.
        :param fit: ``"clearance"`` (loose) or ``"tap"`` (tight, threaded
            into plastic) — selects the bore from the constructor data.
            ``SetScrew`` has no head, so ``"interference"`` is not
            supported (raises ``ValueError``).
        """
        if fit == "tap":
            shaft_dia = self.tap_diameter
        elif fit == "clearance":
            shaft_dia = self.clearance_diameter
        else:
            raise ValueError(
                f"SetScrew to_cutter fit must be 'tap' or 'clearance', got {fit!r}"
            )

        from vibe_cading.mechanical.holes import ClearanceHole

        # Resolve ``None`` to the env-configured default exactly once;
        # the hole class otherwise yields ``AttributeError`` on the
        # underlying ``profile.free.radial`` lookup when nothing is
        # plumbed.  This mirrors the pre-Phase-5 ``get_profile()``
        # fallback the old ``custom_prof`` bridge used.
        from vibe_cading.print_settings import get_profile
        prof = profile if profile is not None else get_profile()
        hole = ClearanceHole(
            diameter=shaft_dia,
            depth=self.length,
            profile=prof,
        )
        return hole.to_cutter()

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show an M3 grub screw beside its tap cutter."""
        grub = cls.from_size("M3", 4)
        return [
            (grub.solid.translate((-5, 0, 0)),               "M3 Grub",    "royalblue"),
            (grub.to_cutter(fit="tap").translate((5, 0, 0)), "Tap Cutter", "gold"),
        ]
