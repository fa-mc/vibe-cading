"""Gears package.

Contains parametric gear generators.
"""

from .base import Gear
from .spur import SpurGear

__all__ = [
    "Gear",
    "SpurGear",
]
