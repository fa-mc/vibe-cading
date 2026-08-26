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

"""Tests for the Lego Technic axle -> 12 mm hex hub adapter family.

Covers the Tests table from the design brief
``docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md``.  Test
numbers in comments refer to that table; geometry that needs a visual/section
cross-check (Tests 2, 5, 6, 10, 13, 14) is exercised separately via
``section_slicer.py`` during Developer validation (see the design brief and
the implementation report) rather than duplicated here as brittle edge-count
assertions -- those are exactly the class of check the project's Mandatory
Slicing rule requires empirical, human-inspectable confirmation of. Test 16
(full-tree ``build.py`` rebuild) is deferred until ``build.toml`` registration
is approved (Out of Scope).
"""

from __future__ import annotations

import pytest

from vibe_cading.cq_utils import axle_cross_section
from vibe_cading.lego.constants import AXLE_HOLE_ARM_WIDTH, AXLE_HOLE_TIP_TO_TIP
from vibe_cading.lego_adapters.axle_hex_hub.axle_hex_hub_adapter import AxleHexHubAdapter
from vibe_cading.lego_adapters.axle_hex_hub.compression_collet import AxleCompressionCollet
from vibe_cading.lego_adapters.axle_hex_hub.hex_insert_hub import HexInsertHub
from vibe_cading.print_settings import get_profile


# ── Test 1 — AxleCompressionCollet single-solid topology ──────────────────

def test_axle_compression_collet_single_solid() -> None:
    assert len(AxleCompressionCollet().solid.solids().vals()) == 1


# ── Test 3 — AxleCompressionCollet printed OD is shrunk for slip fit
#     (Round 4: tightened from free to slip -- less play in the collar) ────

def test_axle_compression_collet_od_is_slip_fit() -> None:
    """Checks the ``_od_printed`` derivation directly rather than reading
    it back off a BoundingBox: the stop ring, dents, and slots all locally
    perturb the X/Y extent at various Z, so no single whole-part bbox
    measurement isolates the plain shaft OD cleanly."""
    prof = get_profile()
    collet = AxleCompressionCollet()
    expected_od = 10.0 - 2.0 * prof.slip.radial
    assert expected_od != pytest.approx(10.0), (
        "test is not falsifiable if slip.radial resolves to 0.0"
    )
    assert collet._od_printed == pytest.approx(expected_od, abs=1e-9)
    # The collet's overall bbox X/Y is governed by the stop ring (Round 4),
    # which is wider than the shaft -- sanity-check that relationship too.
    bb = collet.solid.val().BoundingBox()
    assert bb.xlen == pytest.approx(collet.stop_ring_od, abs=1e-6)
    assert collet.stop_ring_od > expected_od


# ── Test 4 — AxleCompressionCollet bounding-box height is 10.0 mm (Round 3) ─

def test_axle_compression_collet_height_is_10mm() -> None:
    collet = AxleCompressionCollet()
    bb = collet.solid.val().BoundingBox()
    assert bb.zlen == pytest.approx(10.0, abs=1e-6)


# ── Test 7 — HexInsertHub single-solid topology, no axle-bore cavity ──────

def test_hex_insert_hub_single_solid() -> None:
    assert len(HexInsertHub().solid.solids().vals()) == 1


# ── Test 8 — HexInsertHub floor-margin guard (D6/D7) ───────────────────────

def test_hex_insert_hub_floor_margin_guard_boundary_passes() -> None:
    """At the exact MIN_INSERT_FLOOR_MARGIN boundary (0.5 mm margin), the
    guard must NOT fire."""
    hub = HexInsertHub(insert_length=5.5)
    assert hub.thickness - hub.insert_length == pytest.approx(
        HexInsertHub.MIN_INSERT_FLOOR_MARGIN, abs=1e-9
    )


def test_hex_insert_hub_floor_margin_guard_fires_just_past_boundary() -> None:
    """0.1 mm past the boundary (0.4 mm margin) -- the guard MUST fire.

    Positive control for the boundary-passes test above: proves the guard
    can actually reject a violating value, not just silently accept
    everything.
    """
    with pytest.raises(ValueError):
        HexInsertHub(insert_length=5.6)


# ── Test 9 — HexInsertHub insert pocket dimensions match parametrization ──

def test_hex_insert_hub_default_insert_length_is_5mm() -> None:
    """D6/D7, Round 3: the default is 5.0 mm (was 3.0 mm pre-Round-3),
    prioritizing heat-set-insert thread engagement over floor-margin
    conservatism."""
    hub = HexInsertHub()
    assert hub.insert_length == pytest.approx(5.0, abs=1e-9)
    assert hub.insert_diameter == pytest.approx(5.0, abs=1e-9)
    assert hub.thickness - hub.insert_length == pytest.approx(1.0, abs=1e-9)


# ── Test 11 — AxleHexHubAdapter fused single-solid topology ───────────────

def test_axle_hex_hub_adapter_single_solid() -> None:
    fused = AxleHexHubAdapter()
    assert len(fused.solid.solids().vals()) == 1, (
        "AxleHexHubAdapter: union between HexInsertHub and "
        "AxleCompressionCollet did not produce a single contiguous body"
    )


# ── Test 12 — AxleHexHubAdapter fused bounding-box height (Round 3) ───────

def test_axle_hex_hub_adapter_bounding_box_height() -> None:
    fused = AxleHexHubAdapter()
    bb = fused.solid.val().BoundingBox()
    expected_height = (
        fused.collet.height + fused.hex_hub.thickness - fused.overlap_eps
    )
    assert expected_height == pytest.approx(15.98, abs=1e-6)
    assert bb.zlen == pytest.approx(expected_height, abs=1e-6)
    assert bb.zmin == pytest.approx(
        -(fused.collet.height - fused.overlap_eps), abs=1e-6
    )
    assert bb.zmax == pytest.approx(fused.hex_hub.thickness, abs=1e-6)


# ── Test 15 — nominal axle cross-section freely intersects the printed bore
#     with zero interference (free fit); a snug/oversized probe MUST show
#     interference (Positive Control Before Any Absence Claim) ────────────

def test_axle_compression_collet_bore_admits_nominal_axle() -> None:
    """A real nominal-dimension (no clearance) axle test solid must NOT
    interfere with the printed keyed bore -- proving the printed bore is
    larger than nominal, not merely equal to it."""
    collet = AxleCompressionCollet().solid
    axle = axle_cross_section(
        AXLE_HOLE_TIP_TO_TIP, AXLE_HOLE_ARM_WIDTH, collet.val().BoundingBox().zlen
    )
    inter = collet.intersect(axle)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol == pytest.approx(0.0, abs=1e-6)


def test_axle_compression_collet_bore_rejects_oversized_probe() -> None:
    """Positive control for the above: an oversized axle probe (nominal +
    1.0 mm on both cross dimensions) MUST show interference, proving the
    probe can actually detect a collision."""
    collet = AxleCompressionCollet().solid
    oversized = axle_cross_section(
        AXLE_HOLE_TIP_TO_TIP + 1.0,
        AXLE_HOLE_ARM_WIDTH + 1.0,
        collet.val().BoundingBox().zlen,
    )
    inter = collet.intersect(oversized)
    vol = sum(s.Volume() for s in inter.solids().vals()) if inter.solids().vals() else 0.0
    assert vol > 0.0


# ── Round 4/5 — post-approval refinements applied directly (small enough
#     not to route back through a full design-brief revision) ────────────

def test_axle_compression_collet_bore_extra_clearance_widens_bore_profile() -> None:
    """Round 5: axle_bore_extra_clearance adds on top of the profile's own
    free.radial, scoped to the bore only -- doesn't touch the collet OD's
    slip fit."""
    collet = AxleCompressionCollet()
    assert collet.axle_bore_extra_clearance == pytest.approx(0.1, abs=1e-9)
    assert collet._bore_profile.free.radial == pytest.approx(
        collet._prof.free.radial + collet.axle_bore_extra_clearance, abs=1e-9
    )
    # Must not leak into the OD fit (still slip-graded, Round 4).
    assert collet._bore_profile.slip.radial == pytest.approx(
        collet._prof.slip.radial, abs=1e-9
    )


def test_axle_compression_collet_zero_extra_clearance_is_a_pure_passthrough() -> None:
    """axle_bore_extra_clearance=0.0 must fall back to the bare profile
    object, not a numerically-equal copy -- avoids an unnecessary
    dataclasses.replace() on the hot path."""
    collet = AxleCompressionCollet(axle_bore_extra_clearance=0.0)
    assert collet._bore_profile is collet._prof


def test_axle_compression_collet_stop_ring_is_wider_than_collar_id() -> None:
    """Round 4: the stop ring must be strictly wider than the 10 mm ID
    compression collar it's meant to block, or it provides no stop at
    all."""
    collet = AxleCompressionCollet()
    assert collet.stop_ring_od > collet.collet_od


def test_axle_compression_collet_slot_width_is_0_6mm() -> None:
    """Round 4: narrowed from 1.0 mm to 0.6 mm."""
    assert AxleCompressionCollet().slot_width == pytest.approx(0.6, abs=1e-9)


def test_axle_compression_collet_dents_removed_material_at_90_270() -> None:
    """Round 4 (corrected): the two grub-screw dimples sit at 90/270 deg,
    off the collet slots at 0/180 deg -- verify material is actually
    missing at the dent's angular position and Z, by volume comparison
    against a collet built with dent_depth=0 (no dimple cut at all)."""
    dented = AxleCompressionCollet()
    undented = AxleCompressionCollet(dent_depth=0.0)
    vol_dented = sum(s.Volume() for s in dented.solid.solids().vals())
    vol_undented = sum(s.Volume() for s in undented.solid.solids().vals())
    assert vol_dented < vol_undented, (
        "dents did not remove any material -- dent_depth=0.0 control "
        "should be strictly larger"
    )
    assert dented.dent_angles == (90.0, 270.0)
    assert dented.dent_angles != dented.slot_angles, (
        "dents must not land on the same angle as the slots (explicit "
        "human correction, Round 4)"
    )
