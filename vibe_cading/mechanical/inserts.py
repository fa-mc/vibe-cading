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
Standard heat-set threaded inserts for 3D printed parts.
Generates tapered voids for installing brass inserts with a soldering iron.

Supports generic dimensions or manufacturer-specific profiles (Ruthex, Voron).
"""

from __future__ import annotations

import cadquery as cq

from vibe_cading.print_settings import ToleranceProfile


class HeatSetInsert:
    """Generic tapered heat-set threaded insert.

    Generates the optimal tapered cutter void required to melt the
    insert cleanly into plastic.  Tapered designs prevent plastic from
    extruding over the top face during insertion.

    Through-vs-blind: the tapered pocket is fundamentally **blind**
    (defined floor at ``-depth``).  When ``through_hole=True`` an
    arbitrarily deep clearance shaft (100 mm) is appended below the
    pocket so a screw can pass completely through.
    """

    # Class-level overcut for the optional through-hole clearance shaft —
    # 100 mm guarantees clearance through any reasonable host body.
    _THROUGH_SHAFT_LENGTH: float = 100.0

    def __init__(
        self,
        top_diameter: float,
        bot_diameter: float,
        depth: float,
        through_hole: bool = False,
        clearance_diameter: float = 3.2,
    ):
        """Create a custom insert profile based on raw geometries.

        :param top_diameter: Diameter of the void at the surface (mm).
        :param bot_diameter: Diameter of the void at the bottom (mm) — usually
            slightly smaller for taper.
        :param depth: Total depth of the insert void (mm).
        :param through_hole: When True, ``to_cutter`` appends a deep
            clearance shaft beneath the insert pocket so a screw can
            pass through the host body.  Migrated from a ``to_cutter``
            kwarg to a constructor argument per Phase 4 so the
            ``CutterProtocol`` call-time signature stays uniform.
        :param clearance_diameter: Diameter of the optional through-hole shaft
            (mm) — e.g. 3.2 for an M3 clearance hole.  Ignored when
            ``through_hole`` is False.
        """
        self.r_top = top_diameter / 2.0
        self.r_bot = bot_diameter / 2.0
        self.depth = depth
        self.through_hole = through_hole
        self.clearance_diameter = clearance_diameter

    def to_cutter(self, profile: ToleranceProfile | None = None) -> cq.Workplane:
        """Generate a boolean cutter for the insert pocket.

        :param profile: Currently unused — insert dimensions are
            constructor-driven (top_diameter / bot_diameter / depth).  The
            argument is accepted to satisfy ``CutterProtocol``.
        """
        # Tapered loft for the insert
        pocket = (
            cq.Workplane("XY")
            .circle(self.r_top)
            .workplane(offset=-self.depth)
            .circle(self.r_bot)
            .loft()
        )

        if self.through_hole:
            # Add an arbitrarily deep cylinder below it for the screw shaft clearance
            shaft = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, -self.depth))
                .circle(self.clearance_diameter / 2.0)
                .extrude(-self._THROUGH_SHAFT_LENGTH)
            )
            pocket = pocket.union(shaft)

        return pocket

    # --- Standard Presets ---

    @classmethod
    def voron(cls, size: str = "M3", through_hole: bool = False, clearance_diameter: float = 3.2) -> HeatSetInsert:
        """Standard insert void sizes specified by the Voron Design manual.

        Typical Voron insert for M3 is M3x5x4.
        """
        profiles = {
            "M3": {"top_diameter": 4.4, "bot_diameter": 4.0, "depth": 5.5},
            "M4": {"top_diameter": 6.0, "bot_diameter": 5.5, "depth": 8.1},
        }
        if size not in profiles:
            raise ValueError(f"Unknown Voron size '{size}'. Available: {list(profiles.keys())}")
        return cls(through_hole=through_hole, clearance_diameter=clearance_diameter, **profiles[size])

    @classmethod
    def ruthex(cls, size: str = "M3", through_hole: bool = False, clearance_diameter: float = 3.2) -> HeatSetInsert:
        """Ruthex / CNC Kitchen geometry standard.

        Slightly wider / longer than Voron specs.
        """
        profiles = {
            "M2": {"top_diameter": 3.6, "bot_diameter": 3.2, "depth": 4.0},
            "M2.5": {"top_diameter": 4.1, "bot_diameter": 3.6, "depth": 4.5},
            "M3": {"top_diameter": 4.4, "bot_diameter": 4.0, "depth": 6.0},       # Standards are 5.7 mm long, 6.0 void depth
            "M3_short": {"top_diameter": 4.4, "bot_diameter": 4.0, "depth": 3.3}, # 3.0 mm long short variant
            "M4": {"top_diameter": 6.1, "bot_diameter": 5.6, "depth": 8.5},
            "M5": {"top_diameter": 7.1, "bot_diameter": 6.5, "depth": 10.0},
        }
        if size not in profiles:
            raise ValueError(f"Unknown Ruthex size '{size}'. Available: {list(profiles.keys())}")
        return cls(through_hole=through_hole, clearance_diameter=clearance_diameter, **profiles[size])

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show a generic insert next to Voron M3 and Ruthex M4 cutters."""
        # 1. Custom generic insert (blind)
        custom = cls(top_diameter=4.5, bot_diameter=4.0, depth=4.0)

        # 2. Manufacturer-specific presets — Voron M3 with through-hole
        voron_m3 = cls.voron("M3", through_hole=True, clearance_diameter=3.2)
        ruthex_m4 = cls.ruthex("M4")

        return [
            (custom.to_cutter().translate((-10, 0, 0)),
             "Custom 4.5x4 Insert", "royalblue"),
            (voron_m3.to_cutter().translate((0, 0, 0)),
             "Voron M3 (Through-hole)", "gold"),
            (ruthex_m4.to_cutter().translate((15, 0, 0)),
             "Ruthex M4", "tomato"),
        ]
