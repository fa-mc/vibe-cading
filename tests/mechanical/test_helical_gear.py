"""Tests for HelicalGear — double-helix geometry and crossed-axis meshing.

Covers the ``double_helix`` constructor flag (herringbone geometry) and the
crossed-helical posing layer (``crossed_mesh_with`` /
``crossed_center_distance_to``) per the design Tests table in
``docs/design_plans/2026-06-26-crossed-helical-mesh_design.md``.
"""

from __future__ import annotations

import math

import pytest

from vibe_cading.mechanical.gears.helical import HelicalGear
from vibe_cading.mechanical.gears.spur import SpurGear


def _bbox(workplane):
    return workplane.val().BoundingBox()


# ── double_helix geometry ────────────────────────────────────────────────────
def test_double_helix_is_single_solid_full_face_width():
    """Herringbone gear is one contiguous solid spanning the full face width."""
    g = HelicalGear(module=1.5, teeth=18, face_width=12.0, helix_angle=30,
                    double_helix=True)
    assert len(g.solid.solids().vals()) == 1
    bb = _bbox(g.solid)
    assert math.isclose(bb.zmin, 0.0, abs_tol=1e-6)
    assert math.isclose(bb.zmax, 12.0, abs_tol=1e-6)


def test_double_helix_bore_cuts_through():
    """A bore reduces volume and the result stays a single solid."""
    solid_hub = HelicalGear(module=1.5, teeth=18, face_width=12.0,
                            helix_angle=30, double_helix=True)
    bored = HelicalGear(module=1.5, teeth=18, face_width=12.0, helix_angle=30,
                        bore=5, double_helix=True)
    assert len(bored.solid.solids().vals()) == 1
    assert bored.solid.val().Volume() < solid_hub.solid.val().Volume()


def test_single_helix_unchanged_by_double_helix_default():
    """Default double_helix=False still produces a single-helix solid."""
    g = HelicalGear(module=1.5, teeth=18, face_width=12.0, helix_angle=30)
    assert g.double_helix is False
    assert len(g.solid.solids().vals()) == 1


# ── crossed-axis meshing ─────────────────────────────────────────────────────
def _crossed_pair(b1=45, b2=45, **kw):
    a = HelicalGear(module=2, teeth=20, face_width=12, helix_angle=b1)
    b = HelicalGear(module=2, teeth=20, face_width=12, helix_angle=b2)
    return a, b


def test_crossed_mesh_returns_two_single_solids():
    a, b = _crossed_pair()
    s_self, s_other = a.crossed_mesh_with(b)
    assert len(s_self.solids().vals()) == 1
    assert len(s_other.solids().vals()) == 1


def test_crossed_mesh_90deg_pose():
    """Σ=90° (45°+45°): other's axis swings to −Y, X/Z centred on cd."""
    a, b = _crossed_pair(45, 45)
    cd = a.crossed_center_distance_to(b)
    _, other = a.crossed_mesh_with(b)
    bb = _bbox(other)
    assert bb.ymax <= 1e-6 and bb.ymin < -1.0          # axis swung to −Y
    assert math.isclose((bb.xmin + bb.xmax) / 2, cd, abs_tol=1e-6)
    assert math.isclose((bb.zmin + bb.zmax) / 2, 0.0, abs_tol=1e-6)


def test_crossed_center_distance_handles_unequal_helix():
    """Different helix angles → different transverse modules; the crossed
    distance works where the parallel one (rightly) refuses."""
    a, b = _crossed_pair(60, 30)            # same normal module, different β
    assert math.isclose(a.crossed_center_distance_to(b),
                        a.pitch_radius + b.pitch_radius, abs_tol=1e-9)
    assert a.pitch_radius != b.pitch_radius
    with pytest.raises(ValueError):
        a.center_distance_to(b)             # parallel: transverse modules differ


@pytest.mark.parametrize("b1,b2,expected", [
    (45, 45, 90.0),     # same hand → |β1|+|β2|
    (60, 30, 90.0),
    (45, -45, 0.0),     # opposite hand → ||β1|−|β2||
    (60, -30, 30.0),
])
def test_derived_shaft_angle_hand_detection(b1, b2, expected):
    a, b = _crossed_pair(b1, b2)
    assert math.isclose(a._derived_shaft_angle(b), expected)


def test_shaft_angle_override_changes_pose():
    a, b = _crossed_pair(45, 45)           # derived Σ = 90
    _, derived = a.crossed_mesh_with(b)
    _, forced = a.crossed_mesh_with(b, shaft_angle=60)
    bd, bf = _bbox(derived), _bbox(forced)
    assert (bd.ymin, bd.ymax) != (bf.ymin, bf.ymax)


def test_crossed_mesh_rejects_non_helical():
    a, _ = _crossed_pair()
    spur = SpurGear(module=2, teeth=20, face_width=12)
    with pytest.raises(TypeError):
        a.crossed_mesh_with(spur)
    assert not hasattr(spur, "crossed_mesh_with")


def test_crossed_mesh_rejects_module_and_pa_mismatch():
    a, _ = _crossed_pair()
    wrong_module = HelicalGear(module=3, teeth=20, face_width=12, helix_angle=45)
    with pytest.raises(ValueError):
        a.crossed_mesh_with(wrong_module)
    wrong_pa = HelicalGear(module=2, teeth=20, face_width=12, helix_angle=45,
                           pressure_angle=25)
    with pytest.raises(ValueError):
        a.crossed_mesh_with(wrong_pa)


def test_parallel_mesh_with_unaffected():
    """Backward-compat: the base parallel mesh path is intact for spur gears."""
    a = SpurGear(module=2, teeth=20, face_width=8)
    b = SpurGear(module=2, teeth=20, face_width=8)
    pa, pb = a.mesh_with(b)
    assert len(pa.solids().vals()) == 1 and len(pb.solids().vals()) == 1
    cd = a.center_distance_to(b)
    bb = _bbox(pb)
    assert abs((bb.xmin + bb.xmax) / 2 - cd) < 1.0
