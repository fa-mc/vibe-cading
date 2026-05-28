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

"""TechnicPinHole — profile-aware bore-diameter regression net.

Pins the post-2026-05-26 refactor contract: the round pin-hole bore
follows ``profile.<fit>.radial`` (default ``fit="slip"``), mirroring
``TechnicAxleHole``'s shape.  The 27-leaf-float T9b snapshot in
``tests/test_tolerance_profile.py`` pins the ``_FALLBACK_PROFILES``
data; *this* test file pins the consumer plumbing — independent
regression surfaces, deliberately.

A regression that flips the default ``fit`` (e.g. ``"slip"`` →
``"press"``) silently tightens every printed pin hole library-wide;
the per-grade matrix in :func:`test_pin_hole_consumes_slip_radial`
fails loudly when that happens.
"""

import math

import pytest

from vibe_cading.lego.constants import PIN_HOLE_DIAMETER
from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole
from vibe_cading.print_settings import get_profile


# ── Pinned per-profile bore-diameter matrix (load-bearing snapshot) ──────────
#
# These three values are the contract a default-``fit`` regression would
# violate.  Pre-computed against live ``_FALLBACK_PROFILES.<profile>.slip.radial``:
#
#   fdm_standard.slip.radial = 0.05  →  4.80 + 2 * 0.05 = 4.90 mm
#   resin_precise.slip.radial = 0.03 →  4.80 + 2 * 0.03 = 4.86 mm
#   cnc.slip.radial = 0.01           →  4.80 + 2 * 0.01 = 4.82 mm
#
# A default ``fit="free"`` regression would resolve to 5.10/4.90/4.84 on
# fdm_standard/resin_precise/cnc; a ``fit="press"`` regression resolves
# to 4.88/4.84/4.80.  Either fails this matrix loudly.
_PINNED_SLIP_BORE: dict[str, float] = {
    "fdm_standard":  4.90,
    "resin_precise": 4.86,
    "cnc":           4.82,
}


# ── 1. Per-profile bore snapshot (FR1, FR3) ──────────────────────────────────


@pytest.mark.parametrize("profile_name", list(_PINNED_SLIP_BORE.keys()))
def test_pin_hole_consumes_slip_radial(profile_name: str) -> None:
    """Default-path bore = PIN_HOLE_DIAMETER + 2 * profile.slip.radial.

    Pins the per-shipped-profile matrix and acts as the default-fit
    regression net: a flip from ``"slip"`` to any other grade fails this
    test on every profile.
    """
    profile = get_profile(profile_name)
    expected = PIN_HOLE_DIAMETER + 2 * profile.slip.radial
    cutter = TechnicPinHole(depth=8.0, profile=profile)

    assert math.isclose(cutter.diameter, expected, abs_tol=1e-9), (
        f"{profile_name}: expected default-fit bore {expected:.4f} mm, "
        f"got {cutter.diameter:.4f} mm"
    )
    # Defense-in-depth: also assert the pinned snapshot value.  If
    # _FALLBACK_PROFILES drifts, T9b in tests/test_tolerance_profile.py
    # fires first; this assertion catches the rare case where T9b is
    # also updated but the consumer formula regresses simultaneously.
    assert math.isclose(cutter.diameter, _PINNED_SLIP_BORE[profile_name], abs_tol=1e-9), (
        f"{profile_name}: pinned-bore snapshot mismatch — "
        f"expected {_PINNED_SLIP_BORE[profile_name]:.4f} mm, got {cutter.diameter:.4f} mm"
    )


# ── 2. fit= grade selector (FR2) ─────────────────────────────────────────────


@pytest.mark.parametrize("fit", ["free", "slip", "press"])
def test_pin_hole_fit_grade_selector(fit: str) -> None:
    """fit= kwarg selects the FitGrade off the resolved profile."""
    profile = get_profile("fdm_standard")
    expected = PIN_HOLE_DIAMETER + 2 * getattr(profile, fit).radial
    cutter = TechnicPinHole(depth=8.0, fit=fit, profile=profile)

    assert math.isclose(cutter.diameter, expected, abs_tol=1e-9), (
        f"fit={fit!r}: expected bore {expected:.4f} mm, "
        f"got {cutter.diameter:.4f} mm"
    )


# ── 3. Explicit diameter= bypasses profile widening (FR6 / Q1) ───────────────


def test_pin_hole_explicit_diameter_bypasses_profile() -> None:
    """An explicit ``diameter=`` value wins as-is — no profile widening.

    This is the load-bearing contract for ``tolerance_gauge.py``: the
    gauge pre-computes the exact bore it wants per column, and a silent
    re-widening would break the gauge's documentary purpose.
    """
    cutter = TechnicPinHole(depth=8.0, diameter=5.0, profile=get_profile("fdm_standard"))
    assert cutter.diameter == 5.0, (
        f"Explicit diameter=5.0 must win as-is; got {cutter.diameter}"
    )


# ── 4. .standard() forwards fit + profile kwargs (FR5) ───────────────────────


def test_pin_hole_standard_forwards_profile() -> None:
    """``TechnicPinHole.standard(depth, profile=...)`` flows profile through.

    Without this forwarding, a caller asking for the standard pin hole on
    a non-default profile would have to duplicate every ``.standard()``
    default just to pass ``profile=``.
    """
    cutter = TechnicPinHole.standard(depth=8.0, profile="resin_precise")
    expected = PIN_HOLE_DIAMETER + 2 * get_profile("resin_precise").slip.radial
    assert math.isclose(cutter.diameter, expected, abs_tol=1e-9), (
        f".standard() must forward profile=; expected {expected:.4f} mm, "
        f"got {cutter.diameter:.4f} mm"
    )
    # Same value as the pinned snapshot row for resin_precise.
    assert math.isclose(cutter.diameter, _PINNED_SLIP_BORE["resin_precise"], abs_tol=1e-9)
