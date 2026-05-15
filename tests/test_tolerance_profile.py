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

"""Tolerance-profile schema + legacy-bridge regression tests.

Design reference: §Tests T5, §Success Criteria 8 in
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``.

The Phase 3 refactor restructured ``ToleranceProfile`` from a flat
``z_clearance``/``free_fit``/``slip_fit``/``press_fit`` shape into a
nested ``{free, slip, press}`` of ``FitGrade(radial, axial)`` slots.
A legacy-flat → nested bridge keeps old user-local
``machine_profiles_user.json`` files working transparently.

This module asserts:

1. The dataclass slot shape (``ToleranceProfile.free.radial``, etc.).
2. The legacy → nested migration is geometry-preserving (the old
   ``z_clearance`` value lands on every grade's ``.axial`` slot).
3. The default-name resolution path (``get_profile()`` with no args).
"""

from __future__ import annotations

from vibe_cading.print_settings import (
    FitGrade,
    ToleranceProfile,
    _is_legacy_flat_entry,
    _migrate_flat_to_nested,
    _profile_from_nested,
    get_default_profile_name,
    get_profile,
)


# --------------------------------------------------------------------------
# FitGrade — the radial/axial slot shape (Phase 3 §1)
# --------------------------------------------------------------------------

def test_fitgrade_required_radial():
    """A ``FitGrade`` carries a required ``radial`` and optional ``axial``."""
    grade = FitGrade(radial=0.15)
    assert grade.radial == 0.15
    assert grade.axial == 0.0  # default


def test_fitgrade_both_slots():
    """Both slots assignable explicitly."""
    grade = FitGrade(radial=0.15, axial=0.20)
    assert grade.radial == 0.15
    assert grade.axial == 0.20


# --------------------------------------------------------------------------
# ToleranceProfile — nested ``free`` / ``slip`` / ``press`` access (Phase 3 §2)
# --------------------------------------------------------------------------

def test_tolerance_profile_nested_access():
    """The four-field shape: name + three ``FitGrade`` slots."""
    prof = ToleranceProfile(
        name="example",
        free=FitGrade(radial=0.15, axial=0.20),
        slip=FitGrade(radial=0.05, axial=0.10),
        press=FitGrade(radial=-0.04, axial=0.05),
    )
    # Nested access pattern that every cutter callsite uses.
    assert prof.free.radial == 0.15
    assert prof.free.axial == 0.20
    assert prof.slip.radial == 0.05
    assert prof.slip.axial == 0.10
    assert prof.press.radial == -0.04
    assert prof.press.axial == 0.05


def test_profile_from_nested_dict():
    """``_profile_from_nested`` builds a ``ToleranceProfile`` from a nested dict."""
    prof = _profile_from_nested(
        "fdm_test",
        {
            "free": {"radial": 0.15, "axial": 0.20},
            "slip": {"radial": 0.05, "axial": 0.20},
            "press": {"radial": -0.04, "axial": 0.20},
        },
    )
    assert prof.name == "fdm_test"
    assert prof.free.radial == 0.15
    assert prof.slip.radial == 0.05
    assert prof.press.radial == -0.04
    # All three carry the matching axial value
    assert prof.free.axial == 0.20
    assert prof.slip.axial == 0.20
    assert prof.press.axial == 0.20


# --------------------------------------------------------------------------
# Legacy flat → nested bridge (Phase 3 §3 — back-compat)
# --------------------------------------------------------------------------

def test_legacy_flat_detection():
    """``_is_legacy_flat_entry`` distinguishes flat from nested dicts."""
    legacy_flat = {
        "z_clearance": 0.20,
        "free_fit": 0.15,
        "slip_fit": 0.05,
        "press_fit": 0.04,
    }
    nested = {
        "free": {"radial": 0.15, "axial": 0.20},
        "slip": {"radial": 0.05, "axial": 0.20},
        "press": {"radial": 0.04, "axial": 0.20},
    }
    partial_flat = {"z_clearance": 0.20}
    not_a_dict = "string"

    assert _is_legacy_flat_entry(legacy_flat) is True
    assert _is_legacy_flat_entry(nested) is False
    assert _is_legacy_flat_entry(partial_flat) is True
    assert _is_legacy_flat_entry(not_a_dict) is False
    assert _is_legacy_flat_entry({}) is False


def test_legacy_flat_to_nested_migration():
    """The bridge maps ``z_clearance`` onto every grade's ``axial`` slot.

    Geometry-preserving invariant — every historical callsite that paired
    ``prof.<fit>`` with ``prof.z_clearance`` continues to read the same
    numerical values post-migration via ``prof.<fit>.axial``.
    """
    legacy = {
        "z_clearance": 0.20,
        "free_fit": 0.15,
        "slip_fit": 0.05,
        "press_fit": 0.04,
    }
    nested = _migrate_flat_to_nested(legacy)

    assert nested["free"]["radial"] == 0.15
    assert nested["slip"]["radial"] == 0.05
    assert nested["press"]["radial"] == 0.04

    # The single z_clearance replicates onto every grade
    assert nested["free"]["axial"] == 0.20
    assert nested["slip"]["axial"] == 0.20
    assert nested["press"]["axial"] == 0.20


def test_legacy_flat_to_nested_defaults_when_partial():
    """The bridge supplies sensible defaults when a field is missing."""
    legacy_partial = {"z_clearance": 0.10}
    nested = _migrate_flat_to_nested(legacy_partial)

    # Defaults pulled from the bridge function's literals (0.15/0.05/0.04).
    assert nested["free"]["radial"] == 0.15
    assert nested["slip"]["radial"] == 0.05
    assert nested["press"]["radial"] == 0.04

    # z_clearance flows through to all axial slots
    assert nested["free"]["axial"] == 0.10
    assert nested["slip"]["axial"] == 0.10
    assert nested["press"]["axial"] == 0.10


def test_legacy_bridge_then_build_profile():
    """End-to-end: legacy-flat → nested → ``ToleranceProfile`` is consistent."""
    legacy = {
        "z_clearance": 0.20,
        "free_fit": 0.15,
        "slip_fit": 0.05,
        "press_fit": 0.04,
    }
    assert _is_legacy_flat_entry(legacy) is True
    nested = _migrate_flat_to_nested(legacy)
    prof = _profile_from_nested("bridge_test", nested)

    assert prof.free.radial == 0.15
    assert prof.free.axial == 0.20
    assert prof.slip.radial == 0.05
    assert prof.slip.axial == 0.20
    assert prof.press.radial == 0.04
    assert prof.press.axial == 0.20


# --------------------------------------------------------------------------
# Default resolver — ``get_profile()`` with no args (Phase 3 §4)
# --------------------------------------------------------------------------

def test_get_profile_returns_tolerance_profile():
    """``get_profile()`` with no name returns a fully-shaped profile."""
    prof = get_profile()
    assert isinstance(prof, ToleranceProfile)
    assert isinstance(prof.free, FitGrade)
    assert isinstance(prof.slip, FitGrade)
    assert isinstance(prof.press, FitGrade)


def test_get_profile_named_fdm_standard():
    """``fdm_standard`` is the tracked default and always resolves."""
    prof = get_profile("fdm_standard")
    assert isinstance(prof, ToleranceProfile)
    assert prof.name == "fdm_standard"
    # Sanity bounds — fdm_standard has positive radial allowances.
    assert prof.free.radial > 0.0
    assert prof.free.axial >= 0.0


def test_get_profile_unknown_falls_back_to_hardcoded():
    """Unknown names still return a valid ``ToleranceProfile`` (hardcoded fallback)."""
    prof = get_profile("some_unknown_profile_name_xyz")
    assert isinstance(prof, ToleranceProfile)
    # The hardcoded fallback labels the profile with the requested name
    assert prof.name == "some_unknown_profile_name_xyz"


def test_get_default_profile_name_env_var():
    """The default-name resolver returns a non-empty string."""
    name = get_default_profile_name()
    assert isinstance(name, str)
    assert name  # non-empty
