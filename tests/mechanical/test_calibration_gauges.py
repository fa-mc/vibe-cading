"""Geometry tests for the new calibration gauge classes.

Covers design-Tests-table rows 22 (``MThreeClearanceGauge``) and 23
(``MThreeNutPocketGauge``) — both gauges build a single contiguous
solid and expose the live source-of-truth nominal in their swept tuple.
"""

from __future__ import annotations

import pytest

from vibe_cading.mechanical.calibration.m3_clearance_gauge import (
    MThreeClearanceGauge,
)
from vibe_cading.mechanical.calibration.m3_nut_pocket_gauge import (
    MThreeNutPocketGauge,
)


# ── T22 — MThreeClearanceGauge geometry ──────────────────────────────────────
def test_m3_clearance_gauge_single_solid():
    gauge = MThreeClearanceGauge()
    assert len(gauge.solid.solids().vals()) == 1


def test_m3_clearance_gauge_exposes_diameters():
    gauge = MThreeClearanceGauge()
    # Live source-of-truth nominal MUST appear in the swept tuple.
    assert 3.2 in gauge.diameters
    # Tuple is read-only public surface.
    assert isinstance(gauge.diameters, tuple)


def test_m3_clearance_gauge_rejects_empty_sweep():
    with pytest.raises(ValueError):
        MThreeClearanceGauge(diameters=())


def test_m3_clearance_gauge_rejects_off_nominal_sweep():
    """A sweep that omits the live M3 clearance nominal is a misconfig."""
    with pytest.raises(ValueError, match="nominal"):
        MThreeClearanceGauge(diameters=(2.50, 2.60, 2.70))


# ── T23 — MThreeNutPocketGauge geometry ──────────────────────────────────────
def test_m3_nut_pocket_gauge_single_solid():
    gauge = MThreeNutPocketGauge()
    assert len(gauge.solid.solids().vals()) == 1


def test_m3_nut_pocket_gauge_exposes_widths():
    gauge = MThreeNutPocketGauge()
    assert 5.5 in gauge.widths
    assert isinstance(gauge.widths, tuple)


def test_m3_nut_pocket_gauge_rejects_empty_sweep():
    with pytest.raises(ValueError):
        MThreeNutPocketGauge(widths=())


def test_m3_nut_pocket_gauge_rejects_off_nominal_sweep():
    with pytest.raises(ValueError, match="nominal"):
        MThreeNutPocketGauge(widths=(3.0, 3.5, 4.0))
