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

"""Curve generators for the slipper-gear R&D experiment.

These helpers were previously exposed from ``vibe_cading.cq_utils`` but
their only callers live inside this experiment package.  Per the
design Round 6.1 single-adapter audit (`.agents/plans/2026-05-13-pre-oss-models-structure_design.md`),
moving them here removes the speculative seams from the OSS library
surface — `cq_utils.py` now exposes only primitives with multiple,
generic-purpose callers.

If the slipper-gear experiment is later salvaged into a shipped
library component, the relevant helper(s) can be promoted back to
`vibe_cading.cq_utils` at that time.
"""

from __future__ import annotations

import math

import cadquery as cq


def tapered_arm_profile(
    r_start: float,
    r_end: float,
    width_start: float,
    width_end: float,
    sweep_angle: float,
    angle_start: float = 0.0,
    n_points: int = 50,
    r_start_draw: float | None = None,
    b_out: float | None = None,
) -> list[tuple[float, float]]:
    cap_r = width_end / 2.0
    tip_center_r = r_end - cap_r
    angular_overshoot_rad = cap_r / tip_center_r
    effective_sweep = max(0.01, sweep_angle - angular_overshoot_rad)

    a_in = r_start
    a_out = r_start + width_start
    if b_out is None:
        b_out = (r_end - a_out) / sweep_angle
    # For a tapered arm, we infer b_in so the tip matches width_end
    # r_end_in = r_end - width_end. Since r_end_in = a_in + b_in * sweep_angle:
    b_in = (r_end - width_end - a_in) / sweep_angle

    if r_start_draw is not None and b_in != 0:
        t_draw_start = (r_start_draw - a_in) / b_in
        # Prevent going to negative radius
        t_min_in = (0.1 - a_in) / b_in if b_in > 0 else -10.0
        t_min_out = (0.1 - a_out) / b_out if b_out > 0 else -10.0
        t_draw_start = max(t_draw_start, t_min_in, t_min_out)
        t_draw_start = min(t_draw_start, effective_sweep)
    else:
        t_draw_start = 0.0

    pts = []

    # Inner curve
    for i in range(n_points + 1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_in + b_in * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))

    # Semicircular Cap
    actual_r_out = a_out + b_out * effective_sweep
    actual_r_in = a_in + b_in * effective_sweep
    cap_center_r = (actual_r_out + actual_r_in) / 2.0
    cap_r_actual = (actual_r_out - actual_r_in) / 2.0
    cap_angle = angle_start + effective_sweep
    cx = cap_center_r * math.cos(cap_angle)
    cy = cap_center_r * math.sin(cap_angle)

    cap_steps = 10
    for i in range(1, cap_steps):
        frac = i / cap_steps
        ang = cap_angle + math.pi - math.pi * frac
        pts.append((cx + cap_r_actual * math.cos(ang), cy + cap_r_actual * math.sin(ang)))

    # Outer curve
    for i in range(n_points, -1, -1):
        frac = i / n_points
        t = t_draw_start + (effective_sweep - t_draw_start) * frac
        r = a_out + b_out * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))

    return pts


def archimedean_spiral_arc(
    r_start: float,
    r_end: float,
    sweep_angle: float,
    angle_start: float = 0.0,
    n_points: int = 50,
    r_start_draw: float | None = None,
) -> list[tuple[float, float]]:
    b = (r_end - r_start) / sweep_angle

    if r_start_draw is not None and b != 0:
        t_start = (r_start_draw - r_start) / b
    else:
        t_start = 0.0

    pts = []
    for i in range(n_points + 1):
        frac = i / n_points
        t = t_start + (sweep_angle - t_start) * frac
        r = r_start + b * t
        th = angle_start + t
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts


def fillet_z_edges(wp: cq.Workplane, r_min: float, r_max: float, radius: float = 0.8) -> cq.Workplane:
    """Safely apply a fillet to all Z-aligned edges whose radial centroid falls between r_min and r_max"""
    z_edges = wp.edges("|Z")

    def match_edge(e) -> bool:
        c = e.Center()
        dist = math.hypot(c.x, c.y)
        return r_min <= dist <= r_max

    try:
        matched = [e for e in z_edges.vals() if match_edge(e)]
        if matched:
            return wp.objects(matched).fillet(radius)
    except Exception:
        pass

    return wp
