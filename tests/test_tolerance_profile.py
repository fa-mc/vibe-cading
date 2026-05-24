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

Design reference: §Tests T1–T22 + §Success Criteria 1–9 in
``.agents/plans/2026-05-23-print-profile-foundation_design.md`` (current
foundation refactor); earlier history in
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``.

The Phase 3 refactor restructured ``ToleranceProfile`` from a flat
``z_clearance``/``free_fit``/``slip_fit``/``press_fit`` shape into a
nested ``{free, slip, press}`` of ``FitGrade(radial, axial)`` slots.
A legacy-flat → nested bridge keeps old user-local
``machine_profiles_user.json`` / ``print_profiles_user.json`` files
working transparently.  The 2026-05-23 refactor adds field-level
deep-merge semantics (a user can override one leaf without restating
its siblings), file/env-var rename to ``print_profiles*`` /
``VIBE_PRINT_PROFILE``, and a single deprecation window honouring the
legacy names.

This module asserts:

1. The dataclass slot shape (``ToleranceProfile.free.radial``, etc.).
2. The legacy → nested migration is geometry-preserving.
3. The default-name resolution path (``get_profile()`` with no args).
4. The 2026-05-23 ``_deep_merge_profiles`` algorithm — branch
   semantics, type-mismatch + null hard-rejection, unrecognized leaf
   keys pass through without shifting downstream tolerances.
5. The deprecation-warning emitter — one stderr line + one
   ``DeprecationWarning`` per (process, key).
6. The shipped-profile backward-compat snapshot — the three shipped
   profiles resolve to their pinned 10-tuples bit-identically under
   the new loader.
"""

from __future__ import annotations

import importlib
import json
import warnings

import pytest

import vibe_cading.print_settings as print_settings_module
from vibe_cading.print_settings import (
    FitGrade,
    ToleranceProfile,
    _deep_merge_profiles,
    _emit_deprecation_once,
    _is_legacy_flat_entry,
    _migrate_flat_to_nested,
    _profile_from_nested,
    get_default_profile_name,
    get_profile,
)


def _reset_deprecation_state() -> None:
    """Clear the module-level ``_emitted_deprecations`` set between tests.

    Each test that exercises deprecation emission must start from a
    clean slate; the set is module-level state.
    """
    print_settings_module._emitted_deprecations.clear()


@pytest.fixture(autouse=False)
def reset_deprecations():
    """Fixture-style reset wrapper for tests that opt in."""
    _reset_deprecation_state()
    yield
    _reset_deprecation_state()


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
# FitGrade.slot — narrow-slot allowance (Stage 2b §T1)
# --------------------------------------------------------------------------

def test_fitgrade_slot_defaults_zero():
    """``slot`` is the optional third allowance — defaults to 0.0.

    Stage 2b Test #1: a ``FitGrade`` built without ``slot`` reports
    ``slot == 0.0`` (no narrow-slot widening), keeping every pre-Stage-2b
    ``FitGrade(...)`` call site unaffected.
    """
    grade = FitGrade(radial=0.05, axial=0.20)
    assert grade.slot == 0.0


def test_fitgrade_slot_assignable():
    """``slot`` is assignable explicitly alongside ``radial`` / ``axial``."""
    grade = FitGrade(radial=0.05, axial=0.20, slot=0.10)
    assert grade.radial == 0.05
    assert grade.axial == 0.20
    assert grade.slot == 0.10


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


def test_profile_from_nested_dict_omitting_slot_defaults_zero():
    """A nested entry without a ``slot`` key loads ``slot == 0.0``.

    Stage 2b Test #2: ``_fitgrade_from_dict`` defaults the optional
    ``slot`` key to 0.0 — a pre-Stage-2b nested profile (no ``slot``
    anywhere) keeps pre-Stage-2b narrow-slot behaviour.
    """
    prof = _profile_from_nested(
        "no_slot",
        {
            "free": {"radial": 0.15, "axial": 0.20},
            "slip": {"radial": 0.05, "axial": 0.20},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    )
    assert prof.free.slot == 0.0
    assert prof.slip.slot == 0.0
    assert prof.press.slot == 0.0


def test_profile_from_nested_dict_reads_slot():
    """An explicit per-grade ``slot`` key is read into ``FitGrade.slot``."""
    prof = _profile_from_nested(
        "with_slot",
        {
            "free": {"radial": 0.15, "axial": 0.20},
            "slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    )
    assert prof.slip.slot == 0.10
    # Grades omitting the key still default to 0.0.
    assert prof.free.slot == 0.0
    assert prof.press.slot == 0.0


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


def test_legacy_flat_migration_yields_zero_slot():
    """A legacy-flat profile migrates with ``slot == 0.0`` on every grade.

    Stage 2b Test #3: the legacy flat schema has no narrow-slot concept,
    so ``_migrate_flat_to_nested`` emits no ``slot`` key and the loader
    defaults it to 0.0 — a stale legacy-flat ``print_profiles_user.json``
    (or the legacy-named ``machine_profiles_user.json`` still in the
    deprecation window) keeps pre-Stage-2b narrow-slot behaviour,
    intentionally diverging from the shipped nested ``fdm_standard``
    (``slip.slot = 0.10``).
    """
    legacy = {
        "z_clearance": 0.20,
        "free_fit": 0.15,
        "slip_fit": 0.11,
        "press_fit": 0.04,
    }
    nested = _migrate_flat_to_nested(legacy)
    prof = _profile_from_nested("legacy_bambu", nested)
    assert prof.free.slot == 0.0
    assert prof.slip.slot == 0.0
    assert prof.press.slot == 0.0


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


def test_get_profile_unknown_falls_back_to_hardcoded(capsys):
    """Unknown names emit a stderr warning and return ``fdm_standard``.

    Updated 2026-05-23 (Test T13 / Q2 resolution): the substring-classification
    heuristic was dropped — unknown profile names no longer silently propagate
    as the resolved profile's label.  Instead, ``get_profile`` emits a stderr
    warning and returns a profile labelled ``"fdm_standard"`` (the coarse-default
    fallback).  This surfaces calibration mistakes (typos in ``VIBE_PRINT_PROFILE``,
    missing profile entries) that the old silent-pass-through hid.
    """
    prof = get_profile("some_unknown_profile_name_xyz")
    assert isinstance(prof, ToleranceProfile)
    # New behaviour: the resolved profile is labelled "fdm_standard", NOT the
    # unknown requested name — so a downstream calibration mistake is visible.
    assert prof.name == "fdm_standard"

    captured = capsys.readouterr()
    assert "some_unknown_profile_name_xyz" in captured.err
    assert "fdm_standard" in captured.err


def test_get_profile_unknown_warning_emitted_once_per_process(capsys):
    """Follow-up 3: unknown-profile-name warning fires exactly once per process per name.

    Before the follow-up, ``get_profile()``'s unknown-profile-name warning
    was an unconditional ``print(..., file=sys.stderr)`` — fine for one-shot
    CLI use but spammy in a build loop that resolves the same unknown name
    once per model class.  The follow-up factors out a generic ``_emit_once``
    helper that handles the once-per-process guard for any warning category,
    and routes the unknown-profile-name warning through it under the
    ``UserWarning`` category with a ``WARNING:`` stderr prefix.

    This test verifies:
      1. The first ``get_profile("nonexistent_profile_xyz")`` call emits the
         ``WARNING: unknown print profile 'nonexistent_profile_xyz'`` line.
      2. A second call with the same unknown name does NOT re-emit it.
      3. Both calls return a profile labelled ``fdm_standard`` — the unknown
         name is NOT silently propagated.
    """
    # Reset the module-level once-per-process guard so this test's emission
    # is not suppressed by a prior unrelated test that used the same key.
    print_settings_module._emitted_warnings.clear()

    prof_first = get_profile("nonexistent_profile_xyz")
    prof_second = get_profile("nonexistent_profile_xyz")

    # Both calls return the coarse-default fallback labelled "fdm_standard"
    # — the unknown name is NOT silently propagated as the resolved label.
    assert isinstance(prof_first, ToleranceProfile)
    assert isinstance(prof_second, ToleranceProfile)
    assert prof_first.name == "fdm_standard"
    assert prof_second.name == "fdm_standard"

    # Exactly one WARNING line in stderr across the two calls — the guard
    # suppresses the second emission.
    captured = capsys.readouterr()
    assert captured.err.count(
        "WARNING: unknown print profile 'nonexistent_profile_xyz'"
    ) == 1


def test_get_default_profile_name_env_var():
    """The default-name resolver returns a non-empty string."""
    name = get_default_profile_name()
    assert isinstance(name, str)
    assert name  # non-empty


# --------------------------------------------------------------------------
# T1–T5: _deep_merge_profiles algorithm (Data Contract §1)
# --------------------------------------------------------------------------

def test_deep_merge_leaf_wins():
    """T1 (FR8): user overrides ``slip.radial`` only; siblings inherit from base.

    Worked example from Data Contract §1: base ``slip = {radial: 0.05,
    axial: 0.20, slot: 0.10}``; user override carries only ``radial =
    0.11``; the merged dict carries ``radial = 0.11`` (user wins) and
    ``axial = 0.20`` + ``slot = 0.10`` (inherited from base via branch (a)).
    """
    base = {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}
    override = {"fdm_standard": {"slip": {"radial": 0.11}}}
    merged = _deep_merge_profiles(base, override)
    assert merged == {
        "fdm_standard": {"slip": {"radial": 0.11, "axial": 0.20, "slot": 0.10}}
    }


def test_deep_merge_disjoint_keys():
    """T2 (FR8, FR9): user defines a profile that base does not; both top-level keys survive.

    Branch (b): key absent from base, present in override → override value
    copied through verbatim.  Branch (a) on the other top-level key keeps
    the base entry unchanged.
    """
    base = {
        "fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}},
        "resin_precise": {"slip": {"radial": 0.03, "axial": 0.05}},
    }
    override = {"bambu_p1s__pla_overture": {"slip": {"radial": 0.11}}}
    merged = _deep_merge_profiles(base, override)
    assert set(merged.keys()) == {"fdm_standard", "resin_precise", "bambu_p1s__pla_overture"}
    assert merged["resin_precise"] == {"slip": {"radial": 0.03, "axial": 0.05}}
    assert merged["bambu_p1s__pla_overture"] == {"slip": {"radial": 0.11}}


def test_deep_merge_type_mismatch_raises():
    """T3 (FR8, FR11, Domain integrity): primitive-vs-dict mismatch raises.

    Branch (e): the user puts a primitive where the base has a dict —
    silent shape coercion downstream is exactly the silent-tolerance-shift
    the domain-integrity gate guards against.  The merge must raise
    ``ValueError`` naming the JSON-pointer-style key path.
    """
    base = {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20}}}
    override = {"fdm_standard": {"slip": 0.11}}  # primitive where dict expected
    with pytest.raises(ValueError) as exc_info:
        _deep_merge_profiles(base, override)
    msg = str(exc_info.value)
    # Key path should be present (JSON-pointer-style with `/` separator).
    assert "fdm_standard/slip" in msg
    assert "type mismatch" in msg


def test_deep_merge_null_leaf_raises():
    """T4 (FR11, Q3): a null leaf override raises ``ValueError``.

    Branch (f): silent "reset to default via null" is too easy a foot-gun;
    ``null`` is not a tolerance-domain-valid value.  The merge must raise
    ``ValueError`` naming the JSON-pointer-style key path and the word
    "null".
    """
    base = {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}
    override = {"fdm_standard": {"slip": {"slot": None}}}
    with pytest.raises(ValueError) as exc_info:
        _deep_merge_profiles(base, override)
    msg = str(exc_info.value)
    assert "fdm_standard/slip/slot" in msg
    assert "null" in msg


def test_deep_merge_typo_does_not_shift_tolerance():
    """T5 (FR8, Domain integrity): a typo'd override leaf does not shift the resolved value.

    Data Contract §1's deliberate trade-off: unrecognized leaf keys are
    silently accepted into the merged dict but never read by any consumer
    (``_fitgrade_from_dict`` reads only ``radial`` / ``axial`` / ``slot``).
    A typo'd ``radail`` therefore loads but does NOT shift the resolved
    ``slip.radial`` value — the failure mode is *visible in test output*
    (the typo is preserved in the merged dict but ignored downstream),
    not a silent tolerance shift.
    """
    base = {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}
    override = {"fdm_standard": {"slip": {"radail": 0.11}}}  # typo!
    merged = _deep_merge_profiles(base, override)
    # The typo lands in the merged dict — visible in test output.
    assert merged["fdm_standard"]["slip"]["radail"] == 0.11
    # But the resolved profile's slip.radial still equals the BASE value.
    prof = _profile_from_nested("fdm_standard", merged["fdm_standard"])
    assert prof.slip.radial == 0.05  # unchanged by typo — base value wins
    assert prof.slip.axial == 0.20  # untouched
    assert prof.slip.slot == 0.10  # untouched


def test_deep_merge_does_not_mutate_inputs():
    """Sanity check: ``_deep_merge_profiles`` returns a NEW dict.

    Invariant in Data Contract §1: base and override are unmodified.
    """
    base = {"fdm_standard": {"slip": {"radial": 0.05}}}
    override = {"fdm_standard": {"slip": {"radial": 0.11}}}
    base_snapshot = json.dumps(base, sort_keys=True)
    override_snapshot = json.dumps(override, sort_keys=True)
    _deep_merge_profiles(base, override)
    assert json.dumps(base, sort_keys=True) == base_snapshot
    assert json.dumps(override, sort_keys=True) == override_snapshot


def test_deep_merge_null_leaf_in_override_only_subtree_raises():
    """Follow-up 1: a null leaf nested inside an override-only sub-tree raises.

    Before the follow-up, ``_deep_merge_profiles`` Pass 2 (the branch (b)
    loop over override-only keys) only checked ``override_v is None`` at
    the immediate level of the override-only sub-tree.  A user override
    that introduces a brand-new top-level profile key with a nested null
    leaf — e.g. ``{"new_profile": {"slip": {"radial": null}}}`` — bypassed
    the §1 branch (f) rejection because ``new_profile``'s value is a dict
    (passes the top-level ``is None`` check) and the function did not
    recurse into override-only dict values.

    The follow-up adds ``_validate_no_null_leaves`` which recursively
    walks any override-only dict value, raising ``ValueError`` on the
    first ``None`` leaf using the same JSON-pointer-style key-path
    message format as branch (f).
    """
    with pytest.raises(
        ValueError,
        match=r"null tolerance at new_profile/slip/radial is not a valid override",
    ):
        _deep_merge_profiles({}, {"new_profile": {"slip": {"radial": None}}})


# --------------------------------------------------------------------------
# T6–T8: file-resolution chain (Data Contract §4)
# --------------------------------------------------------------------------

def _import_print_settings_against(tmp_path, monkeypatch):
    """Re-import ``print_settings`` with its repo-root re-pointed at ``tmp_path``.

    The loader resolves files relative to ``_REPO_ROOT`` (= ``Path(__file__).parent.parent``).
    To exercise the file-resolution chain without touching real repo files,
    monkeypatch ``_REPO_ROOT`` on the freshly-imported module and reset
    the deprecation set.
    """
    importlib.reload(print_settings_module)
    monkeypatch.setattr(print_settings_module, "_REPO_ROOT", tmp_path)
    print_settings_module._emitted_deprecations.clear()
    return print_settings_module


def test_loader_prefers_new_shipped_filename(tmp_path, monkeypatch, capsys):
    """T6 (FR1, FR12): ``print_profiles.json`` present → loaded with no deprecation warning."""
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    (tmp_path / "print_profiles.json").write_text(json.dumps({
        "fdm_standard": {
            "free":  {"radial": 0.15, "axial": 0.20},
            "slip":  {"radial": 0.05, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    }))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        profiles = mod._load_json_profiles()
    assert "fdm_standard" in profiles
    captured = capsys.readouterr()
    assert "DEPRECATION" not in captured.err
    assert not any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_loader_legacy_shipped_emits_deprecation(tmp_path, monkeypatch, capsys):
    """T7 (FR12, FR13, Q1): only ``machine_profiles.json`` present → loaded with one deprecation."""
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    (tmp_path / "machine_profiles.json").write_text(json.dumps({
        "fdm_standard": {
            "free":  {"radial": 0.15, "axial": 0.20},
            "slip":  {"radial": 0.05, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    }))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        profiles = mod._load_json_profiles()
    assert "fdm_standard" in profiles
    captured = capsys.readouterr()
    # Exactly one stderr DEPRECATION line, one DeprecationWarning.
    assert captured.err.count("DEPRECATION") == 1
    assert "machine_profiles.json" in captured.err
    assert "print_profiles.json" in captured.err
    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) == 1
    assert "OSS publication release" in str(deprecation_warnings[0].message)


def test_loader_both_shipped_prefers_new(tmp_path, monkeypatch, capsys):
    """T8 (FR12, FR13): both shipped files present → new wins, deprecation warns of ignored legacy."""
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    new_data = {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}
    legacy_data = {"fdm_standard": {"slip": {"radial": 999.0, "axial": 0.0, "slot": 0.0}}}
    (tmp_path / "print_profiles.json").write_text(json.dumps(new_data))
    (tmp_path / "machine_profiles.json").write_text(json.dumps(legacy_data))
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        profiles = mod._load_json_profiles()
    # New file's value wins.
    assert profiles["fdm_standard"]["slip"]["radial"] == 0.05
    captured = capsys.readouterr()
    assert "IGNORING" in captured.err
    assert "machine_profiles.json" in captured.err


# --------------------------------------------------------------------------
# T9 + T9b: backward-compat snapshot (Data Contract §8)
# --------------------------------------------------------------------------

def test_backward_compat_snapshot(tmp_path, monkeypatch):
    """T9 (FR9, NFC backward-compat floor, Domain integrity).

    Snapshot the resolved 10-tuple for the maintainer's actual current
    user-file shape — a full-grade override of a new top-level profile
    key (``bambu_p1s``).  Under the new loader the merge is branch-(b):
    the new top-level key flows through verbatim because the base does
    not carry it.  The resolved tuple must equal the pinned snapshot
    bit-identically (the floor the §8 invariant claims).
    """
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    # Shipped: today's print_profiles.json content (verbatim).
    (tmp_path / "print_profiles.json").write_text(json.dumps({
        "fdm_standard": {
            "free":  {"radial": 0.15, "axial": 0.20, "slot": 0.00},
            "slip":  {"radial": 0.05, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20, "slot": 0.00},
        },
        "resin_precise": {
            "free":  {"radial": 0.05, "axial": 0.05},
            "slip":  {"radial": 0.03, "axial": 0.05},
            "press": {"radial": 0.02, "axial": 0.05},
        },
        "cnc": {
            "free":  {"radial": 0.02, "axial": 0.00},
            "slip":  {"radial": 0.01, "axial": 0.00},
            "press": {"radial": 0.00, "axial": 0.00},
        },
    }))
    # User: today's maintainer machine_profiles_user.json content (verbatim).
    (tmp_path / "print_profiles_user.json").write_text(json.dumps({
        "bambu_p1s": {
            "free":  {"radial": 0.15, "axial": 0.20},
            "slip":  {"radial": 0.11, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    }))
    prof = mod.get_profile("bambu_p1s")
    resolved = (
        prof.name,
        prof.free.radial, prof.free.axial, prof.free.slot,
        prof.slip.radial, prof.slip.axial, prof.slip.slot,
        prof.press.radial, prof.press.axial, prof.press.slot,
    )
    # Pinned snapshot — the maintainer's bambu_p1s profile resolved under
    # the new loader.  Branch (b) of the merge takes the user dict verbatim;
    # _fitgrade_from_dict defaults free.slot and press.slot to 0.0.
    assert resolved == ("bambu_p1s", 0.15, 0.20, 0.0, 0.11, 0.20, 0.10, 0.04, 0.20, 0.0)


def test_shipped_profiles_pinned_tuples(tmp_path, monkeypatch):
    """T9b (FR9, NFC backward-compat floor, Domain integrity).

    Snapshot the new loader's resolution of each shipped profile name in
    ``_FALLBACK_PROFILES``.  The pinned tuples below are transcribed
    verbatim from the design's Data Contract §8 table.  A regression
    (e.g. accidentally zeroing ``fdm_standard.slip.slot``, dropping a
    profile, or mis-routing the deep-merge) will fail at least one of
    these 27 leaf-float equalities loudly.

    These values are derived from ``_FALLBACK_PROFILES`` data passed
    through ``_profile_from_nested``'s per-field defaults — so
    ``free.slot`` and ``press.slot`` resolve to ``0.0`` (no explicit
    ``slot`` key in the JSON entry; ``_fitgrade_from_dict.default_slot
    = 0.0``), and ``slip.slot`` resolves to ``0.10`` only for
    ``fdm_standard`` (explicit in the entry) and ``0.0`` for
    ``resin_precise`` / ``cnc``.
    """
    # Exercise the loader against an empty repo root so no JSON files exist
    # — get_profile() must then hit the hardcoded _FALLBACK_PROFILES path
    # via _fallback_profile().  This is the disaster-recovery floor.
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    expected = {
        "fdm_standard":  ("fdm_standard",  0.15, 0.20, 0.0,  0.05, 0.20, 0.10, 0.04, 0.20, 0.0),
        "resin_precise": ("resin_precise", 0.05, 0.05, 0.0,  0.03, 0.05, 0.0,  0.02, 0.05, 0.0),
        "cnc":           ("cnc",           0.02, 0.0,  0.0,  0.01, 0.0,  0.0,  0.0,  0.0,  0.0),
    }
    for name, expected_tuple in expected.items():
        prof = mod.get_profile(name)
        resolved = (
            prof.name,
            prof.free.radial, prof.free.axial, prof.free.slot,
            prof.slip.radial, prof.slip.axial, prof.slip.slot,
            prof.press.radial, prof.press.axial, prof.press.slot,
        )
        assert resolved == expected_tuple, (
            f"shipped profile {name!r} resolved to {resolved}, "
            f"expected {expected_tuple}"
        )


# --------------------------------------------------------------------------
# T10–T12: env-var resolution chain (Data Contract §3)
# --------------------------------------------------------------------------

def test_env_new_var_wins(monkeypatch, capsys, reset_deprecations):
    """T10 (FR2): ``VIBE_PRINT_PROFILE`` set → wins; no deprecation warning."""
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "my_custom_profile")
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        name = get_default_profile_name()
    assert name == "my_custom_profile"
    captured = capsys.readouterr()
    assert "DEPRECATION" not in captured.err
    assert not any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_env_legacy_var_with_warning(monkeypatch, capsys, reset_deprecations):
    """T11 (FR12, FR13, Q1): only ``VIBE_MACHINE_PROFILE`` set → returned with deprecation."""
    monkeypatch.delenv("VIBE_PRINT_PROFILE", raising=False)
    monkeypatch.setenv("VIBE_MACHINE_PROFILE", "my_legacy_value")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        name = get_default_profile_name()
    assert name == "my_legacy_value"
    captured = capsys.readouterr()
    assert captured.err.count("DEPRECATION") == 1
    assert "VIBE_MACHINE_PROFILE" in captured.err
    assert "VIBE_PRINT_PROFILE" in captured.err
    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) == 1
    assert "OSS publication release" in str(deprecation_warnings[0].message)


def test_env_neither_returns_default(monkeypatch, capsys, reset_deprecations):
    """T12 (FR12): neither env var set → ``"fdm_standard"``."""
    monkeypatch.delenv("VIBE_PRINT_PROFILE", raising=False)
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    name = get_default_profile_name()
    assert name == "fdm_standard"
    captured = capsys.readouterr()
    assert "DEPRECATION" not in captured.err


# --------------------------------------------------------------------------
# T14: deprecation-emitter idempotence (Data Contract §5)
# --------------------------------------------------------------------------

def test_deprecation_emitted_once_per_key(capsys, reset_deprecations):
    """T14 (FR13, Q1): same key emitted twice → exactly one stderr line + one warning.

    Different keys emit independently.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _emit_deprecation_once("test_key_1", "first message about key 1")
        _emit_deprecation_once("test_key_1", "duplicate message about key 1")
        _emit_deprecation_once("test_key_1", "another duplicate about key 1")
        _emit_deprecation_once("test_key_2", "first message about key 2")

    captured = capsys.readouterr()
    # key_1 emits once, key_2 emits once — total two DEPRECATION lines.
    assert captured.err.count("DEPRECATION") == 2
    # First (and only) emission per key — duplicates discarded.
    assert captured.err.count("first message about key 1") == 1
    assert captured.err.count("duplicate message about key 1") == 0
    assert captured.err.count("first message about key 2") == 1

    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) == 2


# --------------------------------------------------------------------------
# T15 + T16: legacy-flat ↔ nested migration in the merge pipeline (Data Contract §2)
# --------------------------------------------------------------------------

def test_legacy_flat_user_merges_with_nested_shipped(tmp_path, monkeypatch):
    """T15 (FR10): legacy-flat user file migrates before merging onto nested shipped.

    Per Data Contract §2 the ordering invariant is: migrate each side
    *first*, then deep-merge.  A legacy-flat user entry has no ``slot``
    concept; after migration its grade dicts carry no ``slot`` key, so
    the deep-merge inherits ``slot`` from the shipped nested side via
    branch (a).
    """
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    (tmp_path / "print_profiles.json").write_text(json.dumps({
        "fdm_standard": {
            "free":  {"radial": 0.15, "axial": 0.20},
            "slip":  {"radial": 0.05, "axial": 0.20, "slot": 0.10},
            "press": {"radial": 0.04, "axial": 0.20},
        },
    }))
    # User in legacy-flat shape — migrates to nested with z_clearance → axial
    # on every grade, no slot key on any grade.
    (tmp_path / "print_profiles_user.json").write_text(json.dumps({
        "fdm_standard": {
            "z_clearance": 0.25,
            "free_fit":    0.15,
            "slip_fit":    0.11,
            "press_fit":   0.04,
        },
    }))
    prof = mod.get_profile("fdm_standard")
    # User-side values land on the resolved profile.
    assert prof.slip.radial == 0.11
    assert prof.slip.axial == 0.25
    # User had no slot key — inherits 0.10 from shipped via the deep-merge
    # branch (a).  This is the *strictly better* behaviour Data Contract §3
    # of the Domain Expert review calls out.
    assert prof.slip.slot == 0.10


def test_nested_user_override_inherits_from_legacy_flat_shipped(tmp_path, monkeypatch):
    """T16 (FR8, FR10): nested user override merges onto a legacy-flat shipped entry.

    If a hypothetical contributor ships a legacy-flat shipped file, a
    nested user override should still deep-merge correctly: shipped
    migrates to nested first, then user override's leaf wins, siblings
    inherited from the migrated shipped dict.
    """
    mod = _import_print_settings_against(tmp_path, monkeypatch)
    # Shipped in legacy-flat shape.
    (tmp_path / "print_profiles.json").write_text(json.dumps({
        "fdm_standard": {
            "z_clearance": 0.20,
            "free_fit":    0.15,
            "slip_fit":    0.05,
            "press_fit":   0.04,
        },
    }))
    # User in nested shape — override one leaf only.
    (tmp_path / "print_profiles_user.json").write_text(json.dumps({
        "fdm_standard": {"slip": {"radial": 0.11}},
    }))
    prof = mod.get_profile("fdm_standard")
    # User leaf wins on radial; shipped-migrated axial inherits.
    assert prof.slip.radial == 0.11
    assert prof.slip.axial == 0.20  # from shipped z_clearance → axial migration
    # No slot anywhere — defaults to 0.0.
    assert prof.slip.slot == 0.0


# --------------------------------------------------------------------------
# T17: module docstring covers the new contracts (FR4, FR15)
# --------------------------------------------------------------------------

def test_module_docstring_documents_new_contracts():
    """T17 (FR4, FR15): module docstring names every Q1–Q6-resolved contract.

    The docstring is the in-code source of truth for the loader contract;
    a refactor that drops one of these references silently breaks the
    contributor's primary onboarding surface.
    """
    doc = print_settings_module.__doc__
    assert doc is not None
    # Q4 — canonical env var name.
    assert "VIBE_PRINT_PROFILE" in doc
    # Q4 — canonical file name.
    assert "print_profiles.json" in doc
    # Q4 — key convention with `__` separator (search both quoted and unquoted).
    assert "<machine>__<material>" in doc
    # Q1 — field-level deep merge documented.
    assert "deep-merge" in doc.lower() or "deep merge" in doc.lower()
    # Q3 — null rejection rule.
    assert "null" in doc.lower()
    # Q6 — cutover criterion.
    assert "OSS publication release" in doc


# --------------------------------------------------------------------------
# T18: smoke — a profile-consuming model class loads (FR3, NFC loader-runtime)
# --------------------------------------------------------------------------

def test_axle_hole_gauge_loads_under_new_loader():
    """T18 (FR3): a profile-consuming model class constructs without error.

    Smoke test that the end-to-end loader+consumer path survives the
    refactor — ``AxleHoleGauge`` consumes ``slip.radial`` via the active
    profile, and a broken loader would surface as an import or
    construction error.
    """
    from vibe_cading.lego.axle_hole_gauge import AxleHoleGauge

    gauge = AxleHoleGauge()
    # Construct should succeed without raising; the resolved profile's
    # slip.radial must be positive (any of the shipped profiles satisfy this).
    assert gauge is not None
    prof = get_profile()
    assert prof.slip.radial > 0.0
