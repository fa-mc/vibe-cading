"""
Standard heat-set threaded inserts for 3D printed parts.
Generates tapered voids for installing brass inserts with a soldering iron.

Supports generic dimensions or manufacturer-specific profiles (Ruthex, Voron).
"""

from __future__ import annotations

import cadquery as cq

class HeatSetInsert:
    """
    Generic tapered heat-set threaded insert.
    
    Generates the optimal tapered cutter void required to melt the insert
    cleanly into plastic. Tapered designs prevent plastic from extruding 
    over the top face during insertion.
    """
    
    def __init__(self, top_dia: float, bot_dia: float, depth: float):
        """
        Create a custom insert profile based on raw geometries.
        
        :param top_dia: Diameter of the void at the surface (mm).
        :param bot_dia: Diameter of the void at the bottom (mm) (usually slightly smaller for taper).
        :param depth: Total depth of the insert void (mm).
        """
        self.r_top = top_dia / 2.0
        self.r_bot = bot_dia / 2.0
        self.depth = depth

    def to_cutter(self, through_hole: bool = False, clearance_d: float = 3.2) -> cq.Workplane:
        """Generate a boolean cutter for the insert pocket.
        
        :param through_hole: If true, generates an infinitely deep clearance shaft below 
                             the insert so a screw can pass completely through.
        :param clearance_d:  The diameter of the optional through-hole (e.g., 3.2 for M3).
        """
        # Create the tapered loft for the insert
        pocket = (
            cq.Workplane("XY")
            .circle(self.r_top)
            .workplane(offset=-self.depth)
            .circle(self.r_bot)
            .loft()
        )
        
        if through_hole:
            # Add an arbitrarily deep cylinder below it for the screw shaft clearance
            shaft = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, -self.depth))
                .circle(clearance_d / 2.0)
                .extrude(-100.0) # Extend down broadly to pass through standard assemblies
            )
            pocket = pocket.union(shaft)
            
        return pocket

    # --- Standard Presets ---

    @classmethod
    def voron(cls, size: str = "M3") -> HeatSetInsert:
        """
        Standard insert void sizes specified by the Voron Design manual.
        Typical Voron insert for M3 is M3x5x4.
        """
        profiles = {
            "M3": {"top_dia": 4.4, "bot_dia": 4.0, "depth": 5.5},
            "M4": {"top_dia": 6.0, "bot_dia": 5.5, "depth": 8.1},
        }
        if size not in profiles:
            raise ValueError(f"Unknown Voron size '{size}'. Available: {list(profiles.keys())}")
        return cls(**profiles[size])

    @classmethod
    def ruthex(cls, size: str = "M3") -> HeatSetInsert:
        """
        Ruthex / CNC Kitchen geometry standard. 
        Slightly wider / longer than Voron specs.
        """
        profiles = {
            "M2": {"top_dia": 3.6, "bot_dia": 3.2, "depth": 4.0},
            "M2.5": {"top_dia": 4.1, "bot_dia": 3.6, "depth": 4.5},
            "M3": {"top_dia": 4.4, "bot_dia": 4.0, "depth": 6.0},      # Standards are 5.7mm long, 6.0 void depth
            "M3_short": {"top_dia": 4.4, "bot_dia": 4.0, "depth": 3.3},# 3.0mm long short variant
            "M4": {"top_dia": 6.1, "bot_dia": 5.6, "depth": 8.5},
            "M5": {"top_dia": 7.1, "bot_dia": 6.5, "depth": 10.0},
        }
        if size not in profiles:
            raise ValueError(f"Unknown Ruthex size '{size}'. Available: {list(profiles.keys())}")
        return cls(**profiles[size])


if __name__ == "__main__":
    from ocp_vscode import show

    # 1. Custom generic insert
    custom = HeatSetInsert(top_dia=4.5, bot_dia=4.0, depth=4.0)
    
    # 2. Manufacturer-specific presets
    voron_m3 = HeatSetInsert.voron("M3")
    ruthex_m4 = HeatSetInsert.ruthex("M4")
    
    show(
        custom.to_cutter().translate((-10, 0, 0)),
        voron_m3.to_cutter(through_hole=True, clearance_d=3.2).translate((0, 0, 0)),
        ruthex_m4.to_cutter().translate((15, 0, 0)),
        names=["Custom 4.5x4 Insert", "Voron M3 (Through-hole)", "Ruthex M4"]
    )