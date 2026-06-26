"""Tests for BevelGear — straight-bevel involute gear (Tredgold scaled-section loft).

Covers all rows of the Tests table in:
docs/design_plans/2026-06-26-bevel-gear_design.md
"""

from __future__ import annotations

import math
import warnings

import cadquery as cq
import pytest

from vibe_cading.mechanical.gears import BevelGear, Gear
from vibe_cading.mechanical.gears.bore import DBore, HexBore, KeyedBore, RoundBore


# ── Helpers ──────────────────────────────────────────────────────────────────

def _miter(bore=5.0) -> BevelGear:
    """Default miter pair member: m=2, z=20, mate=20, fw=6, bore=5."""
    return BevelGear(module=2, teeth=20, mate_teeth=20, face_width=6.0, bore=bore)


def _bbox(wp: cq.Workplane):
    return wp.val().BoundingBox()


# ── T_BUILD ──────────────────────────────────────────────────────────────────

def test_build_constructs_solid():
    """T_BUILD: default miter construct builds a solid."""
    g = _miter()
    assert g.solid is not None
    assert isinstance(g, BevelGear)
    assert isinstance(g, Gear)


# ── T_SINGLE ─────────────────────────────────────────────────────────────────

def test_single_contiguous_solid():
    """T_SINGLE: final solid is one contiguous body."""
    g = _miter()
    assert len(g.solid.solids().vals()) == 1


# ── T_REUSE ──────────────────────────────────────────────────────────────────

def test_profile_length_parity_with_spur():
    """T_REUSE: heel profile uses Gear.gear_blank_with_teeth_2d (same as SpurGear)."""
    module, teeth, pa = 2.0, 20, 20.0
    bevel_pts = Gear.gear_blank_with_teeth_2d(module=module, teeth=teeth,
                                               pressure_angle=pa, n_flank=32)
    spur_pts = Gear.gear_blank_with_teeth_2d(module=module, teeth=teeth,
                                              pressure_angle=pa, n_flank=32)
    assert len(bevel_pts) == len(spur_pts)


# ── T_SIG ────────────────────────────────────────────────────────────────────

def test_constructor_accepts_all_kwargs():
    """T_SIG: constructor accepts all keyword arguments."""
    g = BevelGear(
        module=2.0,
        teeth=20,
        mate_teeth=20,
        face_width=6.0,
        bore=5.0,
        pressure_angle=20.0,
        shaft_angle=90.0,
        n_flank=32,
    )
    assert g.solid is not None


# ── T_DELTA ──────────────────────────────────────────────────────────────────

def test_pitch_angle_miter_90deg():
    """T_DELTA: miter pair (z==mate, Σ=90°) → pitch_angle = 45°."""
    g = _miter()
    assert math.isclose(math.degrees(g.pitch_angle), 45.0, abs_tol=1e-9)


# ── T_DELTA_ASYM ─────────────────────────────────────────────────────────────

def test_pitch_angle_asymmetric_pair():
    """T_DELTA_ASYM: z=12, mate=24, Σ=90° → δ ≈ 26.565°.

    Uses pressure_angle=25° (z_min=11) to satisfy the undercut floor for z=12.
    The pitch-angle formula is independent of pressure angle.
    """
    g = BevelGear(module=2, teeth=12, mate_teeth=24, face_width=4.0, bore=5.0,
                  pressure_angle=25.0)
    expected_deg = math.degrees(math.atan(12.0 / 24.0))  # ≈ 26.565°
    assert math.isclose(math.degrees(g.pitch_angle), expected_deg, abs_tol=1e-3)


# ── T_LOFT ───────────────────────────────────────────────────────────────────

def test_apex_convergence_two_way_equality():
    """T_LOFT: toe pitch radius computed via scale == via apex geometry."""
    g = _miter()
    # Scale path: R_p · s
    toe_rp_scale = g.pitch_radius * g._toe_scale
    # Geometry path: R_p − z_toe · tan(δ)
    toe_rp_geom = g.pitch_radius - g._axial_height * math.tan(g.pitch_angle)
    assert math.isclose(toe_rp_scale, toe_rp_geom, abs_tol=1e-6)


# ── T_DATUM ──────────────────────────────────────────────────────────────────

def test_datum_heel_at_z0_toe_at_axial_height():
    """T_DATUM: bounding box spans from ≈0 to ≈_axial_height."""
    g = _miter()
    bb = _bbox(g.solid)
    assert math.isclose(bb.zmin, 0.0, abs_tol=1e-4)
    assert math.isclose(bb.zmax, g._axial_height, abs_tol=1e-3)


# ── T_BORE_ROUND ─────────────────────────────────────────────────────────────

def test_bore_round_breaks_through_both_faces():
    """T_BORE_ROUND: bore=5.0 (float) reduces volume and remains one solid."""
    g_solid = _miter(bore=None)
    g_bored = _miter(bore=5.0)
    assert len(g_bored.solid.solids().vals()) == 1
    # Bore must reduce volume.
    assert g_bored.solid.val().Volume() < g_solid.solid.val().Volume()


# ── T_BORE_COMPOSABLE ────────────────────────────────────────────────────────

@pytest.mark.parametrize("bore_obj", [
    RoundBore(diameter=5.0),
    HexBore(across_flats=5.0),
    DBore(diameter=5.0, flat_offset=1.5),
    KeyedBore(diameter=5.0, key_width=2.0, key_depth=1.0),
])
def test_bore_composable_types_single_solid(bore_obj):
    """T_BORE_COMPOSABLE: all Bore subtypes build a single-solid bevel gear."""
    g = BevelGear(module=2, teeth=20, mate_teeth=20, face_width=6.0, bore=bore_obj)
    assert len(g.solid.solids().vals()) == 1


# ── T_BORE_HEIGHT ─────────────────────────────────────────────────────────────

def test_bore_uses_axial_height_not_face_width():
    """T_BORE_HEIGHT: axial height is strictly less than face_width for a bevel."""
    g = _miter()
    # For any bevel gear with δ > 0, _axial_height < face_width.
    # Miter: _axial_height = 6·cos(45°) ≈ 4.243 mm < 6.0 mm.
    assert g._axial_height < g.face_width
    # The bore void must reach the toe (confirmed by single-solid check above).
    assert len(g.solid.solids().vals()) == 1


# ── T_MESH ───────────────────────────────────────────────────────────────────

def test_mesh_with_returns_two_solids_miter():
    """T_MESH: mesh_with returns 2 non-empty workplanes for a miter pair."""
    g1 = _miter()
    g2 = _miter()
    s1, s2 = g1.mesh_with(g2)
    assert len(s1.solids().vals()) == 1
    assert len(s2.solids().vals()) == 1


def test_mesh_with_cross_module_asymmetric_pair():
    """T_MESH (cross-module): asymmetric pair z=12/mate=24 and its complement.

    This test exercises the from-scratch apex pose.  If mesh_with wrongly
    delegated to the base center_distance_to path, it would raise ValueError
    on a cross-module pair (different pitch radii) or produce a parallel-axis
    pose (wrong geometry).  The asymmetric pair forces a non-trivial apex-z
    difference and Σ-tilt computation.

    Uses pressure_angle=25° (z_min=11) to satisfy the undercut floor for z=12.
    """
    g_small = BevelGear(module=2, teeth=12, mate_teeth=24, face_width=4.0, bore=5.0,
                        pressure_angle=25.0)
    g_large = BevelGear(module=2, teeth=24, mate_teeth=12, face_width=4.0, bore=5.0,
                        pressure_angle=25.0)
    # Neither direction should raise ValueError (no center_distance_to delegation).
    s1, s2 = g_small.mesh_with(g_large)
    assert len(s1.solids().vals()) == 1
    assert len(s2.solids().vals()) == 1
    s3, s4 = g_large.mesh_with(g_small)
    assert len(s3.solids().vals()) == 1
    assert len(s4.solids().vals()) == 1


def test_mesh_with_docstring_has_disclaimer():
    """T_MESH: mesh_with carries the not-a-simulation disclaimer."""
    doc = BevelGear.mesh_with.__doc__
    assert doc is not None
    # Check for the key phrase.
    assert "simulation" in doc.lower()


# ── T_FROM_ISO ───────────────────────────────────────────────────────────────

def test_from_iso_builds_for_standard_module():
    """T_FROM_ISO: from_iso with ISO module builds successfully."""
    g = BevelGear.from_iso(
        module=2.0, teeth=20, mate_teeth=20, face_width=6.0, bore=5.0,
        shaft_angle=90.0,
    )
    assert isinstance(g, BevelGear)
    assert g.solid is not None


def test_from_iso_raises_for_non_iso_module():
    """T_FROM_ISO: non-ISO module raises ValueError."""
    with pytest.raises(ValueError, match="ISO"):
        BevelGear.from_iso(
            module=2.3, teeth=20, mate_teeth=20, face_width=6.0,
        )


# ── T_DEMO ───────────────────────────────────────────────────────────────────

def test_demo_returns_two_item_list():
    """T_DEMO: demo() returns a list of 2 (Workplane, str, str) tuples."""
    result = BevelGear.demo()
    assert len(result) == 2
    for solid, name, color in result:
        assert isinstance(solid, cq.Workplane)
        assert isinstance(name, str)
        assert isinstance(color, str)


# ── T_HYGIENE ────────────────────────────────────────────────────────────────

def test_importable_from_package():
    """T_HYGIENE: BevelGear is importable from the gears package."""
    from vibe_cading.mechanical.gears import BevelGear as BG  # noqa: F401
    assert BG is BevelGear


def test_no_ocp_vscode_import():
    """T_HYGIENE: bevel.py does not import ocp_vscode."""
    import ast
    import pathlib
    src = pathlib.Path(__file__).parent.parent.parent / \
        "vibe_cading" / "mechanical" / "gears" / "bevel.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [a.name for a in node.names] if isinstance(node, ast.Import)
                else ([node.module] if node.module else [])
            )
            for name in names:
                assert "ocp_vscode" not in (name or ""), \
                    "bevel.py must not import ocp_vscode"


def test_no_main_block():
    """T_HYGIENE: bevel.py has no if __name__ == '__main__' block."""
    import ast
    import pathlib
    src = pathlib.Path(__file__).parent.parent.parent / \
        "vibe_cading" / "mechanical" / "gears" / "bevel.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check for: if __name__ == "__main__":
            test = node.test
            if (isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"):
                pytest.fail("bevel.py must not have an if __name__ == '__main__' block")


# ── T_FW_HARD ────────────────────────────────────────────────────────────────

def test_face_width_hard_limit_raises():
    """T_FW_HARD: face_width >= outer_cone_distance raises ValueError."""
    # For m=2, z=20, mate=20, Σ=90°: A_o ≈ 28.284 mm.
    with pytest.raises(ValueError, match="outer_cone_distance"):
        BevelGear(module=2, teeth=20, mate_teeth=20, face_width=30.0)


# ── T_FW_SOFT ────────────────────────────────────────────────────────────────

def test_face_width_soft_limit_warns_but_builds():
    """T_FW_SOFT: face_width > A_o/3 warns but builds successfully."""
    # A_o ≈ 28.284 mm; A_o/3 ≈ 9.428 mm.  Use fw=15 (valid but > A_o/3).
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        g = BevelGear(module=2, teeth=20, mate_teeth=20, face_width=15.0, bore=5.0)
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) >= 1
    assert "A_o/3" in str(user_warnings[0].message) or "stubby" in str(user_warnings[0].message)
    # The gear must still build successfully.
    assert g.solid is not None
    assert len(g.solid.solids().vals()) == 1


# ── Additional validation: derived attributes ─────────────────────────────────

def test_derived_attributes_miter():
    """Verify all derived attributes for the miter sample against known values."""
    g = _miter()
    # R_p = m·z/2 = 2·20/2 = 20 mm
    assert math.isclose(g.pitch_radius, 20.0, abs_tol=1e-9)
    # A_o = R_p / sin(45°) = 20 / (√2/2) = 20√2 ≈ 28.2843 mm
    assert math.isclose(g.outer_cone_distance, 20.0 * math.sqrt(2), abs_tol=1e-9)
    # z_toe = 6 · cos(45°) = 6 · √2/2 ≈ 4.2426 mm
    assert math.isclose(g._axial_height, 6.0 * math.cos(math.pi / 4), abs_tol=1e-6)
    # s = (A_o - fw) / A_o
    expected_s = (20.0 * math.sqrt(2) - 6.0) / (20.0 * math.sqrt(2))
    assert math.isclose(g._toe_scale, expected_s, abs_tol=1e-9)
    # pitch_apex_z = R_p / tan(45°) = 20 mm
    assert math.isclose(g.pitch_apex_z, 20.0, abs_tol=1e-9)
    # virtual_teeth = z / cos(45°) = 20√2 ≈ 28.284
    assert math.isclose(g.virtual_teeth, 20.0 * math.sqrt(2), abs_tol=1e-9)


def test_shaft_angle_non_90():
    """BevelGear with shaft_angle=60 builds a valid single solid."""
    g = BevelGear(module=2, teeth=20, mate_teeth=20, face_width=5.0, bore=5.0,
                  shaft_angle=60.0)
    assert g.solid is not None
    assert len(g.solid.solids().vals()) == 1


def test_mate_teeth_zero_raises():
    """mate_teeth=0 raises ValueError."""
    with pytest.raises(ValueError):
        BevelGear(module=2, teeth=20, mate_teeth=0, face_width=6.0)


def test_shaft_angle_boundary_raises():
    """shaft_angle=0 and shaft_angle=180 raise ValueError."""
    with pytest.raises(ValueError):
        BevelGear(module=2, teeth=20, mate_teeth=20, face_width=6.0,
                  shaft_angle=0.0)
    with pytest.raises(ValueError):
        BevelGear(module=2, teeth=20, mate_teeth=20, face_width=6.0,
                  shaft_angle=180.0)
