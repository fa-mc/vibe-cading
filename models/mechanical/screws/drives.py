# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import math
from abc import ABC, abstractmethod
import cadquery as cq

class FastenerDrive(ABC):
    """
    Abstract base class for all fastener drive geometry cutters.
    Each standard drive type implements specific sizes (e.g., PH1, M3 Hex)
    so users don't need to guess geometric parameters.
    """
    @property
    @abstractmethod
    def cutter(self) -> cq.Workplane:
        """
        Returns a solid cutter starting slightly above Z=0 (overcut)
        and extending to the required depth.
        """
        pass

class HexDrive(FastenerDrive):
    """
    Standard hexagon socket drive (e.g., for Allen bolts).
    """
    def __init__(self, across_flats: float, depth: float):
        self.across_flats = across_flats
        self.depth = depth

    @property
    def cutter(self) -> cq.Workplane:
        # Circumscribed diameter for CadQuery's polygon: diameter = 2 * r = across_flats / cos(30 deg)
        diameter = self.across_flats / math.cos(math.radians(30))
        return (
            cq.Workplane("XY")
            .workplane(offset=0.1) # Add a small 0.1mm Z overcut
            .polygon(6, diameter)
            .extrude(-(self.depth + 0.1))
        )

class SlottedDrive(FastenerDrive):
    """
    Standard flat-head slotted drive.
    """
    def __init__(self, length: float, width: float, depth: float):
        self.length = length
        self.width = width
        self.depth = depth

    @property
    def cutter(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .workplane(offset=0.1)
            .rect(self.length + 0.2, self.width) # +0.2 length for slight X overcut
            .extrude(-(self.depth + 0.1))
        )

class PhillipsDrive(FastenerDrive):
    """
    Realistic cross-shaped Phillips drive based on standardized PH profiles.
    Constructed by unioning tapered rectangles and a central cone for a correct pocket.
    """
    
    # ISO Phillips standard approximations (diameter, width, depth)
    PH_SIZES = {
        "PH00": (2.0, 0.6, 1.0),
        "PH0":  (3.0, 0.8, 1.5),
        "PH1":  (4.5, 1.2, 2.5),
        "PH2":  (6.0, 1.5, 3.5),
        "PH3":  (8.0, 2.0, 5.0)
    }

    def __init__(self, diameter: float, width: float, depth: float):
        self.diameter = diameter
        self.width = width
        self.depth = depth

    @classmethod
    def from_size(cls, size: str) -> "PhillipsDrive":
        """Instantiate a Phillips drive cutter based on industry standard (e.g., 'PH1', 'PH2')."""
        size = size.upper()
        if size not in cls.PH_SIZES:
            raise ValueError(f"Unknown Phillips size: {size}. Available sizes: {list(cls.PH_SIZES.keys())}")
        d, w, h = cls.PH_SIZES[size]
        return cls(diameter=d, width=w, depth=h)

    @property
    def cutter(self) -> cq.Workplane:
        # A robust Phillips cutter: tapered rectangles + central support.
        # This prevents CadQuery from struggling with intersecting tapered 2D wires.
        depth_val = -(self.depth + 0.1)
        w = cq.Workplane("XY", origin=(0, 0, 0.1))
        
        # We use a 20 degree taper (close to ISO 53 degrees total included angle)
        t_ang = 20
        arm1 = w.rect(self.diameter, self.width).extrude(depth_val, taper=t_ang)
        arm2 = w.rect(self.width, self.diameter).extrude(depth_val, taper=t_ang)
        
        # Intersecting center to prevent collapse artifacts at the very bottom
        center = w.circle(self.width * 0.8).extrude(depth_val, taper=t_ang)
        
        return arm1.union(arm2).union(center)

