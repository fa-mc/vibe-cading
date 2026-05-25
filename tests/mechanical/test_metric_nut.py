"""Tests for the ``MetricHexNut.to_cutter(fit=...)`` Option-A refactor.

Covers design-Tests-table rows 24 (press fit reads ``press.radial``)
and 25 (default ``fit='captive'`` preserves backwards-compatibility).
"""

from __future__ import annotations

import pytest

from vibe_cading.mechanical.nuts.metric import MetricHexNut
from vibe_cading.print_settings import FitGrade, ToleranceProfile


def _xy_bbox(workplane):
    bb = workplane.val().BoundingBox()
    return bb.xlen, bb.ylen


# ── T24 — fit='press' reads press.radial, not free.radial ────────────────────
def test_to_cutter_press_fit_reads_press_radial():
    """Press fit consumes ``press.radial`` via the Option-A synthesised
    per-call ``ToleranceProfile``.

    Construct a profile whose ``press.radial`` is large and whose
    ``free.radial`` is zero; the produced cutter must reflect the
    PRESS allowance.
    """
    profile = ToleranceProfile(
        name="test_press_only",
        free=FitGrade(radial=0.0, axial=0.0),
        slip=FitGrade(radial=0.0, axial=0.0),
        press=FitGrade(radial=1.0, axial=0.0),
    )
    nut = MetricHexNut.from_size("M3")  # WAF 5.5
    cutter = nut.to_cutter(profile=profile, fit="press")
    xlen, _ = _xy_bbox(cutter)
    # Pocket WAF = 5.5 + 2 * 1.0 = 7.5 mm. CadQuery's polygon(6,
    # diameter) is circumscribed-diameter; the x-extent equals
    # 7.5 / cos(30°).
    import math
    expected = 7.5 / math.cos(math.radians(30))
    assert xlen == pytest.approx(expected, abs=1e-4)


# ── T25 — default fit='captive' preserves backwards-compat ───────────────────
def test_to_cutter_default_captive_backcompat():
    """Default call (no ``fit`` kwarg) reads ``free.radial`` as before."""
    profile = ToleranceProfile(
        name="test_captive_default",
        free=FitGrade(radial=0.1, axial=0.0),
        slip=FitGrade(radial=0.0, axial=0.0),
        press=FitGrade(radial=1.0, axial=0.0),
    )
    nut = MetricHexNut.from_size("M3")
    # No fit kwarg: behave as if pre-refactor.
    cutter_default = nut.to_cutter(profile=profile)
    cutter_explicit_captive = nut.to_cutter(
        profile=profile, fit="captive"
    )
    x_default, _ = _xy_bbox(cutter_default)
    x_captive, _ = _xy_bbox(cutter_explicit_captive)
    # Both must agree, and reflect FREE allowance (0.1), NOT press (1.0).
    assert x_default == pytest.approx(x_captive, abs=1e-6)
    import math
    expected = (5.5 + 2 * 0.1) / math.cos(math.radians(30))
    assert x_default == pytest.approx(expected, abs=1e-4)


def test_to_cutter_unknown_fit_raises():
    nut = MetricHexNut.from_size("M3")
    with pytest.raises(ValueError, match="unknown fit"):
        nut.to_cutter(fit="bogus")


# ── OC3 (follow-up) — fit='press' accepts a str profile name ─────────────────
def test_to_cutter_press_fit_accepts_str_profile_name():
    """Phase-C Domain-Expert OC3: ``fit="press"`` previously dereferenced
    ``prof.press`` directly, which would ``AttributeError`` if a future
    caller passed ``profile=<str name>`` (zero current callers do this,
    but the failure mode is silent-until-trigger). The type-narrow
    inside ``to_cutter`` resolves a ``str``/``None`` profile via
    ``get_profile(profile)`` first, matching the shapes the
    ``fit="captive"`` branch already accepts.
    """
    nut = MetricHexNut.from_size("M3")
    # Must not raise. The shipped ``fdm_standard`` profile carries a
    # press grade with valid radial/axial values, so the synthesised
    # per-call ToleranceProfile is well-formed and the cutter
    # construction completes.
    cutter = nut.to_cutter(profile="fdm_standard", fit="press")
    bb = cutter.val().BoundingBox()
    # Sanity: produced geometry is non-degenerate.
    assert bb.xlen > 0
    assert bb.ylen > 0
    assert bb.zlen > 0
