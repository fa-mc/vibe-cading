"""Shared constants and helpers for the sinusoidal servo-saver cam.

This module owns the spring dimensions (AX31009 kit), cam geometry
constants, and the ``cut_sinusoidal_cam`` BSpline-prism cutter used by
both ShaftCrown and ShaftBody.
"""

from __future__ import annotations

import math

import cadquery as cq


# ── Spring constants ──────────────────────────────────────────────────────────
# Source: Axial AXIC3009 (a.k.a. AX31009) servo-saver spring.
# Ships in the Axial EXO, Yeti, SCX10 II, and Wraith servo-saver kits.

SPRING_OD: float          = 10.03   # spring outer diameter (mm)
SPRING_ID: float          = 6.9     # spring inner diameter (mm)
SPRING_FREE_HEIGHT: float = 6.0     # spring free (unloaded) height (mm)
SPRING_PRELOAD: float     = 0.5     # assembly pre-compression (mm)
SPRING_GAP: float         = SPRING_FREE_HEIGHT - SPRING_PRELOAD  # 5.5 mm assembled gap


# ── Cam constants ─────────────────────────────────────────────────────────────

CAM_LIFT: float    = 2.5    # sinusoid peak-to-trough height (mm)
CAM_R_INNER: float = 3.5    # inner radius of the annular ramp (mm)
CAM_R_OUTER: float = 5.0    # outer radius of the annular ramp (mm)
CAM_STEPS: int     = 72     # wedge count for ramp approximation (5° each)


# ── Sinusoidal cam helper ─────────────────────────────────────────────────────

def cut_sinusoidal_cam(
    part: cq.Workplane,
    face_z: float,
    r_inner: float,
    r_outer: float,
    cam_lift: float,
    steps: int = 72,
    phase: float = 0.0,
    cut_upward: bool = True,
    profile: str = "sinusoidal",
) -> cq.Workplane:
    """Carve a two-peak sinusoidal annular ramp into *part*.

    The ramp surface height at angle θ is::

        Z(θ) = face_z − (cam_lift / 2) · (1 + cos(2θ + phase))

    ``phase = 0``
        Deepest cut at 0° / 180°; zero at 90° / 270°.
        Leaves material **peaks** at 90° / 270°.
        → use for **both** ShaftCrown (top face) and ShaftBody (bottom face).

    ``cut_upward = True``  (default)
        Removes material **above** the sinusoidal surface.
        → use for ShaftCrown: carves ramp down from the top.

    ``cut_upward = False``
        Removes material **below** the sinusoidal surface.
        → use for ShaftBody: carves valleys up from the bottom.

    Algorithm
    ---------
    A BSpline surface is fit through a 2-D grid of (r, θ) → (x, y, z)
    points using ``cq.Face.makeSplineApprox``.  The surface is then
    extruded into a solid prism via ``BRepPrimAPI_MakePrism`` and
    boolean-cut from the part.  This yields a mathematically smooth (C2)
    cam surface with a single boolean operation — no stair-stepping or
    chord-vs-arc artefacts.

    Parameters
    ----------
    part : cq.Workplane
        The target solid to cut.
    face_z : float
        Z height of the flat reference face (top of cylinder for crown,
        top of cam base for body).
    r_inner, r_outer : float
        Inner and outer radii of the annular cam zone.
    cam_lift : float
        Peak-to-trough sinusoidal amplitude.
    steps : int
        Number of angular segments for the BSpline point grid
        (n_theta = steps + 1).  Default 72.
    phase : float
        Phase offset in radians added to the cosine term.
    cut_upward : bool
        If True, remove material above the surface (crown ramp).
        If False, remove material below the surface (body valleys).
    profile : str
        "sinusoidal" (default) or "v-shape" (sharp peaks/troughs triangle wave).
    """
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec

    overcut = 0.3   # extend BSpline past cylinder walls (mm)
    n_r = 5         # radial point rows (sufficient for flat annular zone)
    n_theta = steps + 1  # angular columns (closed: first == last)

    r_ext_inner = r_inner - overcut
    r_ext_outer = r_outer + overcut

    # Build 2-D point grid for the sinusoidal surface
    pts: list[list[cq.Vector]] = []
    for i_r in range(n_r):
        row: list[cq.Vector] = []
        r = r_ext_inner + (r_ext_outer - r_ext_inner) * i_r / (n_r - 1)
        for i_theta in range(n_theta):
            theta = 2.0 * math.pi * i_theta / (n_theta - 1)
            x = 2.0 * theta + phase
            if profile == "v-shape" or profile == "v-shape-fourier":
                # Fourier series approximation of a triangle wave (first 3 terms)
                # Gives straight steep sides but smooth C2 transitions at peaks/troughs
                # preventing OCCT BSpline overshoots/ringing and Z-fighting artifacts.
                val = math.cos(x) + (1.0/9.0)*math.cos(3*x) + (1.0/25.0)*math.cos(5*x)
                peak = 1.15111
                val = val / peak
                # shift to [0, 1] and scale by cam_lift
                depth = (cam_lift / 2.0) * (1.0 + val)
            elif profile == "linear-smoothed":
                # A piecewise kinematic profile with a straight slope and C1
                # continuous quadratic blends at bounds, eliminating any BSpline ringing
                # while giving flat, true conical faces for standard lock-in torques.
                cycle = ((theta + phase / 2.0) % math.pi) / (math.pi / 2.0)
                t = cycle if cycle <= 1.0 else 2.0 - cycle
                b = 0.1  # 10% of travel (approx 9 degrees) blended at top and bottom
                if t < b:
                    A = 1.0 / (2.0 * b * (1.0 - b))
                    f = 1.0 - A * t**2
                elif t > 1.0 - b:
                    A = 1.0 / (2.0 * b * (1.0 - b))
                    f = A * (1.0 - t)**2
                else:
                    f = 0.5 - (t - 0.5) / (1.0 - b)
                depth = cam_lift * f
            else: # sinusoidal
                depth = (cam_lift / 2.0) * (1.0 + math.cos(x))
            z = face_z - depth
            row.append(cq.Vector(
                r * math.cos(theta),
                r * math.sin(theta),
                z,
            ))
        pts.append(row)

    sin_face = cq.Face.makeSplineApprox(pts, tol=0.001)

    # Extrude the BSpline face into a solid prism (the boolean cutter).
    # Direction: +Z removes material above the surface (crown),
    #            −Z removes material below the surface (body valleys).
    extrude_h = cam_lift + 1.0  # extend well past the body
    direction = gp_Vec(0, 0, extrude_h if cut_upward else -extrude_h)
    prism = BRepPrimAPI_MakePrism(sin_face.wrapped, direction)
    prism.Build()
    if not prism.IsDone():
        raise RuntimeError("BRepPrimAPI_MakePrism failed for sinusoidal cam cutter")

    cutter = cq.Solid(prism.Shape())
    return part.cut(cq.Workplane("XY").add(cutter))
