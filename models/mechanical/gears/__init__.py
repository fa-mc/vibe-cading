"""Gears package.

Contains parametric gear generators.
"""

from .base import Gear
from .spur import SpurGear
from .helical import HelicalGear
from .rack import RackGear

__all__ = [
    "Gear",
    "SpurGear",
    "HelicalGear",
    "RackGear",
]
