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
Standard metric nuts.
Includes Hex nuts (ISO 4032), Nyloc nuts (DIN 985), and Square nuts (DIN 562).
"""
from __future__ import annotations

from typing import Literal

import cadquery as cq

class MetricHexNut:
    """Standard Metric Hex Nut generator (ISO 4032 / DIN 934)."""
    DIMENSIONS = {
        "M2": {"thread_diameter": 2.0, "width_flats": 4.0, "thickness": 1.6},
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 2.0},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 2.4},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 3.2},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 4.7},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 5.2},
        "M8": {"thread_diameter": 8.0, "width_flats": 13.0, "thickness": 6.8},
    }

    def __init__(self, width_flats: float, thickness: float, thread_diameter: float = 0.0):
        self.width_flats = float(width_flats)
        self.thickness = float(thickness)
        self.thread_diameter = float(thread_diameter)
        self.radius = self.width_flats / 1.7320508075688772

    @classmethod
    def from_size(cls, size: Literal["M2", "M2.5", "M3", "M4", "M5", "M6", "M8"]) -> "MetricHexNut":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(width_flats=dims["width_flats"], thickness=dims["thickness"], thread_diameter=dims.get("thread_diameter", float(size[1:])))

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").polygon(6, self.radius * 2).extrude(self.thickness)
        if self.thread_diameter > 0.0:
            hole_cutter = cq.Workplane("XY").circle(self.thread_diameter / 2.0).extrude(self.thickness + 2.0)
            hole_cutter = hole_cutter.translate((0, 0, -1.0))
            base = base.cut(hole_cutter)
        return base

    def to_cutter(self, profile=None, fit: str = "captive") -> cq.Workplane:
        """Generate a pocket cutter for this nut.

        Parameters
        ----------
        profile:
            Active :class:`~vibe_cading.print_settings.ToleranceProfile`,
            or ``None`` to resolve via
            :func:`~vibe_cading.print_settings.get_profile`.
        fit:
            ``"captive"`` (default) sizes the pocket from
            ``profile.free.radial`` — loose enough for hand-insertion
            of the nut, suitable for a captive-nut slot or a hex
            recess where the screw passes through. Preserves bit-exact
            backwards-compatibility with every pre-``fit``-kwarg
            caller.

            ``"press"`` sizes the pocket from ``profile.press.radial``
            — an interference fit for hammer-/firm-press insertion of
            the nut, suitable for a self-retaining nut pocket with no
            mechanical capture.

        Notes
        -----
        First-call note: pre-calibration, ``fit="press"`` uses the
        shipped ``press.radial = 0.04`` (about 4× tighter per side
        than ``fit="captive"`` which uses the shipped
        ``free.radial = 0.15``). The first press print is likely to
        feel tight — run a quick test fit (or calibrate via
        ``python3 tools/calibrate.py press``) before relying on a
        press joint in a finished part.
        """
        from vibe_cading.print_settings import (
            ToleranceProfile,
            get_profile,
        )
        # Type-narrow: accept the same ``profile`` shapes that the
        # ``fit="captive"`` branch accepts (None or str profile name)
        # before the synthesis path dereferences ``prof.press``.
        # Without this, ``fit="press"`` + str profile name would
        # ``AttributeError`` at ``prof.press`` below — silent-until-trigger
        # for a future caller. See design Open Concern OC3 (2026-05-25).
        if profile is None or isinstance(profile, str):
            prof = get_profile(profile)
        else:
            prof = profile
        if fit == "captive":
            # Bit-exact backwards-compat: pass the resolved profile
            # straight through. ``CaptiveNutPocket`` reads
            # ``profile.free.radial`` / ``profile.free.axial``.
            effective = prof
        elif fit == "press":
            # Synthesise a per-call ``ToleranceProfile`` whose ``free``
            # slot carries the press allowances; ``CaptiveNutPocket``
            # is unchanged and continues to read ``free.radial``/
            # ``free.axial`` — but those now reflect ``prof.press``.
            # Option A from design brief §5: keeps the
            # ``CaptiveNutPocket`` wire contract byte-identical, only
            # this method's behaviour changes.
            effective = ToleranceProfile(
                name=f"{prof.name}__press_synth",
                free=prof.press,
                slip=prof.slip,
                press=prof.press,
            )
        else:
            raise ValueError(
                f"unknown fit {fit!r}; expected 'captive' or 'press'"
            )
        # ``CaptiveNutPocket`` reads ``profile.free.radial`` for the
        # pocket inflation; the matching axial allowance lives on the
        # same grade. Under ``fit="press"`` the synthesised profile
        # routes the press allowance through this same path.
        depth_allowance = effective.free.axial
        from vibe_cading.mechanical.holes import CaptiveNutPocket
        pocket = CaptiveNutPocket(
            self.width_flats,
            self.thickness + depth_allowance,
            effective,
        )
        # The pocket translates down by `-thickness` internally, so to
        # match the captive-pocket UP-from-XY convention we translate
        # up by its thickness so it sits at Z=0 and goes to +h.
        # ``CaptiveNutPocket`` is blind-class (no terminal/entry
        # overcut) — this consumer owns any host-body overcut.
        return pocket.to_cutter().translate(
            (0, 0, self.thickness + depth_allowance)
        )

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        r = self.radius + radial_allowance
        h = self.thickness + depth_allowance
        base = cq.Workplane("XY").polygon(6, r * 2).extrude(h)
        chan_width = self.width_flats + (radial_allowance * 2)
        channel = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                   .rect(chan_width, slot_length).extrude(h))
        return base.union(channel)

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """Show M3 hex / nyloc / square nuts side-by-side."""
        hex_nut = cls.from_size("M3")
        nyloc_nut = MetricNylocNut.from_size("M3")
        square_nut = MetricSquareNut.from_size("M3")
        return [
            (hex_nut.solid.translate((-10, 0, 0)),    "M3 Hex Nut",    "royalblue"),
            (nyloc_nut.solid.translate((0, 0, 0)),    "M3 Nyloc Nut",  "gold"),
            (square_nut.solid.translate((10, 0, 0)),  "M3 Square Nut", "tomato"),
        ]


class MetricNylocNut(MetricHexNut):
    """Standard Metric Nyloc Nut generator (DIN 985)."""
    DIMENSIONS = {
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 3.8},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 4.0},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 5.0},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 5.0},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 6.0},
        "M8": {"thread_diameter": 8.0, "width_flats": 13.0, "thickness": 8.0},
    }

    @classmethod
    def from_size(cls, size: Literal["M2.5", "M3", "M4", "M5", "M6", "M8"]) -> "MetricNylocNut":
        # Own override (not inherited) so the engine_api enum advertises the
        # Nyloc-specific size set — DIN 985 Nyloc has no "M2", unlike the
        # parent hex-nut DIMENSIONS.  Geometry is unchanged: delegate to the
        # parent factory, which reads ``cls.DIMENSIONS`` (here MetricNyloc's).
        return super().from_size(size)

class MetricSquareNut:
    """Standard Metric Square Nut generator (DIN 562)."""
    DIMENSIONS = {
        "M2": {"thread_diameter": 2.0, "width_flats": 4.0, "thickness": 1.2},
        "M2.5": {"thread_diameter": 2.5, "width_flats": 5.0, "thickness": 1.6},
        "M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 1.8},
        "M4": {"thread_diameter": 4.0, "width_flats": 7.0, "thickness": 2.2},
        "M5": {"thread_diameter": 5.0, "width_flats": 8.0, "thickness": 2.7},
        "M6": {"thread_diameter": 6.0, "width_flats": 10.0, "thickness": 3.2},
    }

    def __init__(self, width_flats: float, thickness: float, thread_diameter: float = 0.0):
        self.width_flats = float(width_flats)
        self.thickness = float(thickness)
        self.thread_diameter = float(thread_diameter)

    @classmethod
    def from_size(cls, size: Literal["M2", "M2.5", "M3", "M4", "M5", "M6"]) -> "MetricSquareNut":
        if size not in cls.DIMENSIONS:
            raise ValueError(f"Unknown nut size {size}. Supported: {list(cls.DIMENSIONS.keys())}")
        dims = cls.DIMENSIONS[size]
        return cls(width_flats=dims["width_flats"], thickness=dims["thickness"], thread_diameter=dims.get("thread_diameter", float(size[1:])))

    @property
    def solid(self) -> cq.Workplane:
        base = cq.Workplane("XY").rect(self.width_flats, self.width_flats).extrude(self.thickness)
        if self.thread_diameter > 0.0:
            hole_cutter = cq.Workplane("XY").circle(self.thread_diameter / 2.0).extrude(self.thickness + 2.0)
            hole_cutter = hole_cutter.translate((0, 0, -1.0))
            base = base.cut(hole_cutter)
        return base

    def to_cutter(self, profile = None) -> cq.Workplane:
        from vibe_cading.print_settings import get_profile
        prof = profile or get_profile()
        radial_allowance = prof.free.radial
        depth_allowance = prof.free.axial
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance
        return cq.Workplane("XY").rect(w, w).extrude(h)

    def to_captive_slot(self, slot_length: float, radial_allowance: float = 0.15, depth_allowance: float = 0.2) -> cq.Workplane:
        w = self.width_flats + (radial_allowance * 2)
        h = self.thickness + depth_allowance
        base = cq.Workplane("XY").rect(w, w).extrude(h)
        channel = (cq.Workplane("XY").transformed(offset=cq.Vector(0, -slot_length/2, 0))
                   .rect(w, slot_length).extrude(h))
        return base.union(channel)
