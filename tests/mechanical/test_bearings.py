"""Tests for the ``Bearing.blind_pocket_dims`` / ``Bearing.mr85`` consolidation
refactor (TODO.md: "Consolidate blind bearing-pocket sizing").

Covers the shared formula's own correctness plus a regression guard proving
FreespinHexHub and HexHubNut still compute identical pocket dimensions after
delegating to it, rather than their own hand-rolled formulas.
"""

from __future__ import annotations

import pytest

from vibe_cading.mechanical.bearings import MR85_ID, MR85_OD, MR85_W, Bearing
from vibe_cading.print_settings import FitGrade, ToleranceProfile, get_profile
from vibe_cading.rc.freespin_hex_hub import FreespinHexHub
from vibe_cading.rc.hex_hub_bearing.hex_hub_nut import HexHubNut


def test_mr85_preset_matches_shared_constants() -> None:
    brg = Bearing.mr85()
    assert brg.inner_diameter == pytest.approx(MR85_ID)
    assert brg.outer_diameter == pytest.approx(MR85_OD)
    assert brg.thickness == pytest.approx(MR85_W)


def test_blind_pocket_dims_formula() -> None:
    prof = ToleranceProfile(
        name="test",
        free=FitGrade(radial=0.20, axial=0.10),
        slip=FitGrade(radial=0.0, axial=0.0),
        press=FitGrade(radial=0.0, axial=0.0),
    )
    diameter, depth = Bearing.blind_pocket_dims(
        8.0, 2.5, profile=prof, fit="free", proud_margin=0.5
    )
    assert diameter == pytest.approx(8.0 + 2.0 * 0.20)
    assert depth == pytest.approx(2.5 + 0.10 + 0.5)


def test_blind_pocket_dims_zero_proud_margin() -> None:
    """proud_margin=0.0 drops the flat assembly-headroom addition entirely --
    depth is then just thickness + the fit grade's own axial allowance."""
    prof = ToleranceProfile(
        name="test",
        free=FitGrade(radial=0.0, axial=0.15),
        slip=FitGrade(radial=0.0, axial=0.0),
        press=FitGrade(radial=0.0, axial=0.0),
    )
    _, depth = Bearing.blind_pocket_dims(8.0, 2.5, profile=prof, proud_margin=0.0)
    assert depth == pytest.approx(2.5 + 0.15)


def test_blind_pocket_dims_rejects_unknown_fit() -> None:
    with pytest.raises(ValueError, match="unknown fit"):
        Bearing.blind_pocket_dims(8.0, 2.5, fit="bogus")


def test_blind_pocket_dims_default_fit_and_proud_margin() -> None:
    """Pins the *default* argument values themselves -- every other test in
    this file either overrides `fit`/`proud_margin` explicitly, or (below)
    compares a consumer against a call using the same defaults, neither of
    which can fail if the defaults drift (e.g. `proud_margin: float = 0.5`
    silently changed to `1.0`). This is the one check whose failure would
    directly mean "the defaults changed," independent of any consumer."""
    prof = ToleranceProfile(
        name="test",
        free=FitGrade(radial=0.20, axial=0.10),
        slip=FitGrade(radial=0.0, axial=0.0),
        press=FitGrade(radial=0.0, axial=0.0),
    )
    diameter, depth = Bearing.blind_pocket_dims(8.0, 2.5, profile=prof)
    assert diameter == pytest.approx(8.0 + 2.0 * 0.20)  # default fit="free"
    assert depth == pytest.approx(2.5 + 0.10 + 0.5)      # default proud_margin=0.5


# ── Regression guard: refactor must not change either consumer's output.
#
# Deliberately does NOT call Bearing.blind_pocket_dims() at all -- computing
# "expected" via the same shared call the consumer now delegates to would
# only prove the delegation is wired correctly, not that the *value* matches
# what the pre-refactor hand-rolled formula produced (a drift in
# blind_pocket_dims' own defaults would move both sides of such a comparison
# together and the test would stay green). Instead, each expected value is
# computed here from the original inline formula
# (`bearing_od/width + free.radial/axial + 0.5`), reading the ambient
# default profile's grade values directly -- independent of
# blind_pocket_dims' own implementation or defaults.
#
# (A custom ToleranceProfile can't be injected here instead: both classes'
# `profile` constructor param is `str | None`, passed straight through to
# `get_profile(name)`, which only resolves string profile names.)

def test_freespin_hex_hub_pocket_dims_match_shared_formula() -> None:
    prof = get_profile()
    hub = FreespinHexHub(bearing_od=9.0, bearing_width=3.0)
    assert hub._pocket_dia == pytest.approx(9.0 + 2.0 * prof.free.radial)
    assert hub._pocket_depth == pytest.approx(3.0 + prof.free.axial + 0.5)


def test_hex_hub_nut_pocket_dims_match_shared_formula() -> None:
    prof = get_profile()
    nut = HexHubNut(bearing_od=9.0, bearing_width=2.0)
    assert nut._pocket_dia == pytest.approx(9.0 + 2.0 * prof.free.radial)
    assert nut._pocket_depth == pytest.approx(2.0 + prof.free.axial + 0.5)
