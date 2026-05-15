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

"""Composable bore types for parametric gears.

Each ``Bore`` subclass describes a hub-bore geometry that a gear consumes via
:meth:`Gear.bore_cutter`.  The bore is a *specification*, not a solid — it
exposes a single :meth:`profile_2d` method returning a closed CCW list of
``(x, y)`` points centred on the gear axis ``(0, 0)``.  Gear classes extrude
that profile through the face width (plus overcut) to form the through-bore
cutter.

The four bore shapes shipped with this module cover the common cases:

* :class:`RoundBore`  — circular hole, parameterised by diameter.
* :class:`HexBore`    — regular hexagon, parameterised by across-flats.
* :class:`DBore`      — D-shaped (round with one flat), parameterised by
  diameter and flat depth from the bore axis.
* :class:`KeyedBore`  — round with a single radial keyway, parameterised by
  bore diameter, key width, and key depth (radial extension beyond the bore
  radius).

Origin convention: all profiles are returned in the gear's local XY plane
with the bore centre at ``(0, 0)``.  Gears are extruded along +Z, so the
bore cutter follows the same extrusion direction.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod


class Bore(ABC):
    """Abstract base class for composable gear-bore specifications.

    A bore is a 2D profile centred at ``(0, 0)`` in the gear's local XY
    plane.  Subclasses only need to implement :meth:`profile_2d`; the gear
    itself owns the extrusion (face width plus overcut for clean booleans).
    """

    @abstractmethod
    def profile_2d(self, n_segments: int = 64) -> list[tuple[float, float]]:
        """Return a closed CCW 2D polyline describing the bore cross-section.

        Parameters
        ----------
        n_segments
            Number of segments approximating any curved portion of the
            profile.  Default 64 keeps tessellation tight for typical
            module-1 / module-2 gear bores; raise for very small / very
            large bores.
        """
        raise NotImplementedError


class RoundBore(Bore):
    """Plain circular bore through the gear hub."""

    def __init__(self, diameter: float) -> None:
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        self.diameter = float(diameter)

    def profile_2d(self, n_segments: int = 64) -> list[tuple[float, float]]:
        r = self.diameter / 2.0
        return [
            (r * math.cos(2.0 * math.pi * i / n_segments),
             r * math.sin(2.0 * math.pi * i / n_segments))
            for i in range(n_segments)
        ]


class HexBore(Bore):
    """Regular hexagonal bore, sized by across-flats."""

    def __init__(self, across_flats: float) -> None:
        if across_flats <= 0:
            raise ValueError(f"across_flats must be positive, got {across_flats}")
        self.across_flats = float(across_flats)

    def profile_2d(self, n_segments: int = 6) -> list[tuple[float, float]]:
        # A regular hexagon is parameterised by its circumradius, which is
        # ``across_flats / sqrt(3)`` for an across-flats measurement.  We
        # rotate by 30° so two flats lie parallel to the X axis (the usual
        # orientation for a hex driver).
        r = self.across_flats / math.sqrt(3.0)
        return [
            (r * math.cos(math.pi / 6.0 + 2.0 * math.pi * i / 6.0),
             r * math.sin(math.pi / 6.0 + 2.0 * math.pi * i / 6.0))
            for i in range(6)
        ]


class DBore(Bore):
    """Round bore with a single flat (D-profile).

    Parameters
    ----------
    diameter
        Bore diameter (mm).
    flat_offset
        Signed distance from the bore centre to the flat, measured along
        +Y.  Must satisfy ``0 < flat_offset < diameter / 2``.  The flat is
        oriented perpendicular to +Y by convention (matching the common
        servo-shaft D-cut orientation).
    """

    def __init__(self, diameter: float, flat_offset: float) -> None:
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        r = diameter / 2.0
        if not (0.0 < flat_offset < r):
            raise ValueError(
                f"flat_offset={flat_offset} must lie strictly between 0 and "
                f"r={r} for a valid D-profile"
            )
        self.diameter = float(diameter)
        self.flat_offset = float(flat_offset)

    def profile_2d(self, n_segments: int = 64) -> list[tuple[float, float]]:
        r = self.diameter / 2.0
        d = self.flat_offset
        # The flat chord intersects the circle at +Y = d.  Solve for the
        # x-intersections: x^2 + d^2 = r^2  →  x = ±sqrt(r^2 - d^2).
        x_chord = math.sqrt(r * r - d * d)
        # Sweep CCW from the right end of the chord (+x_chord, +d) all the
        # way around through -Y back to the left end of the chord
        # (-x_chord, +d), then close along the chord.
        a_start = math.atan2(d, x_chord)
        a_end = math.atan2(d, -x_chord)  # > a_start
        # We need to traverse the circle the LONG way around (avoiding the
        # chord), i.e. from a_start CCW down through -π/2 and up to a_end.
        # Easier: go a_start − 2π → a_end so the sweep is negative-going
        # CCW (i.e. we go clockwise from a_start to a_end, NOT through the
        # chord).  Equivalently, sample angles in [a_end − 2π, a_start]
        # ascending and reverse.
        sweep = (a_start + 2.0 * math.pi) - a_end  # positive sweep CCW
        pts: list[tuple[float, float]] = []
        for i in range(n_segments + 1):
            t = i / n_segments
            a = a_end + sweep * t
            pts.append((r * math.cos(a), r * math.sin(a)))
        # ``pts`` now starts at (-x_chord, +d), sweeps CCW around through
        # the bottom of the circle, and ends at (+x_chord, +d).  Closing
        # the polyline back to the start completes the D.
        return pts


class KeyedBore(Bore):
    """Round bore with a single radial keyway slot.

    The key is a rectangular notch extending radially outward (toward +Y by
    convention), parameterised by its width (tangential, along X) and its
    depth (radial extension *beyond* the bore radius).  A square-bottomed
    notch is used; a contributor can subclass and override
    :meth:`profile_2d` for radiused-bottom keyways.

    Parameters
    ----------
    diameter
        Bore diameter (mm).
    key_width
        Tangential width of the keyway (mm).  Must be less than the bore
        diameter.
    key_depth
        Radial depth of the keyway beyond the bore wall (mm).  Positive.
    """

    def __init__(self, diameter: float, key_width: float, key_depth: float) -> None:
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        if key_width <= 0 or key_width >= diameter:
            raise ValueError(
                f"key_width={key_width} must satisfy 0 < key_width < "
                f"diameter={diameter}"
            )
        if key_depth <= 0:
            raise ValueError(f"key_depth must be positive, got {key_depth}")
        self.diameter = float(diameter)
        self.key_width = float(key_width)
        self.key_depth = float(key_depth)

    def profile_2d(self, n_segments: int = 64) -> list[tuple[float, float]]:
        r = self.diameter / 2.0
        half_w = self.key_width / 2.0
        # Angle at which the bore circle is intersected by the key sides.
        # The key sides are at x = ±half_w; the bore circle at x = ±half_w
        # has y = sqrt(r^2 − half_w^2).
        y_at_key = math.sqrt(r * r - half_w * half_w)
        a_right = math.atan2(y_at_key, half_w)
        a_left = math.atan2(y_at_key, -half_w)  # > a_right
        # Sweep CCW from a_right − 2π (going the long way) up to a_left.
        # Equivalently: sample from a_left − 2π → a_right ascending then
        # close the keyway notch on top.
        sweep = (a_right + 2.0 * math.pi) - a_left
        pts: list[tuple[float, float]] = []
        for i in range(n_segments + 1):
            t = i / n_segments
            a = a_left + sweep * t
            pts.append((r * math.cos(a), r * math.sin(a)))
        # ``pts`` now ends at (half_w, y_at_key).  Trace the keyway:
        # right side up, top across, left side down — back to the start.
        top_y = r + self.key_depth
        pts.append((half_w, top_y))
        pts.append((-half_w, top_y))
        # The next implicit closing edge returns to pts[0] = (-half_w, y_at_key).
        return pts


__all__ = ["Bore", "RoundBore", "HexBore", "DBore", "KeyedBore"]
