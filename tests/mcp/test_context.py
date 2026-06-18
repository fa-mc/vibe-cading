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

"""Tests for ``vibe_cading.mcp.context.get_design_context`` (R3).

Two checks:

* **#4 — payload shape & value pinning.**  The ``tolerance_profile`` is
  **host-dependent by design** (``get_profile(None)`` returns the calibrated
  host profile, e.g. ``bambu_p1s``).  To pin *values* host-independently we force
  ``PRINT_PROFILE=fdm_standard`` **before importing ``print_settings``**
  (precedent: ``check_visual_contract_freshness.py``) and compare against a
  freshly-resolved ``get_profile("fdm_standard")`` — never against hardcoded
  literals, which would drift with the shipped default.
* **#5 — anti-drift.**  Every name in ``CONTEXT_CONSTANTS`` still resolves on
  ``vibe_cading.lego.constants`` and is a ``float``.  A removed/renamed constant
  goes red here in the same PR, so the curated allowlist cannot silently rot
  into a lying payload.  (Profile-independent — no env forcing needed.)
"""

from __future__ import annotations

import os

# --- value-pinning prerequisite: force the shipped default BEFORE print_settings
# is imported, so a calibrated host's .env PRINT_PROFILE cannot make a
# value-pinning assertion fail (the visual-contract host-calibration drift
# hazard).  This must run at import time, before the get_profile import below.
os.environ["PRINT_PROFILE"] = "fdm_standard"

from vibe_cading.lego import constants                      # noqa: E402
from vibe_cading.mcp.context import (                       # noqa: E402
    CONTEXT_CONSTANTS,
    CONTEXT_SCHEMA_VERSION,
    DOC_POINTERS,
    get_design_context,
)
from vibe_cading.print_settings import get_profile          # noqa: E402


# --------------------------------------------------------------------------
# Test #4 — payload shape + live profile (env-neutralized value pinning)
# --------------------------------------------------------------------------

def test_context_schema_version_is_additively_bumped():
    # Literal pin (not self-referential against the imported constant): surfacing
    # the studded-System block nominals is the additive 1.0 -> 1.1 bump the
    # context schema policy describes, so the bump is intentional-gated here.
    assert CONTEXT_SCHEMA_VERSION == "1.1"
    assert get_design_context()["schema_version"] == "1.1"


def test_context_payload_shape():
    ctx = get_design_context()
    assert ctx["schema_version"] == CONTEXT_SCHEMA_VERSION
    assert set(ctx.keys()) == {
        "schema_version",
        "tolerance_profile",
        "constants",
        "doc_pointers",
    }
    # tolerance profile carries the four-field bundle, each with three grades.
    tp = ctx["tolerance_profile"]
    assert set(tp.keys()) == {"name", "free", "slip", "press"}
    for grade in ("free", "slip", "press"):
        assert set(tp[grade].keys()) == {"radial", "axial", "slot"}


def test_context_tolerance_matches_live_profile():
    # We forced PRINT_PROFILE=fdm_standard at import time, so the default-resolved
    # profile is fdm_standard; compare against a fresh resolution rather than
    # literal numbers (the shipped default's values may evolve).
    ctx = get_design_context()
    tp = ctx["tolerance_profile"]
    assert tp["name"] == "fdm_standard"

    live = get_profile("fdm_standard")
    assert tp["free"] == {
        "radial": live.free.radial,
        "axial": live.free.axial,
        "slot": live.free.slot,
    }
    assert tp["slip"] == {
        "radial": live.slip.radial,
        "axial": live.slip.axial,
        "slot": live.slip.slot,
    }
    assert tp["press"] == {
        "radial": live.press.radial,
        "axial": live.press.axial,
        "slot": live.press.slot,
    }


def test_context_explicit_profile_arg():
    # An explicit profile name is forwarded to get_profile.
    ctx = get_design_context("fdm_standard")
    assert ctx["tolerance_profile"]["name"] == "fdm_standard"


def test_context_doc_pointers_are_pointers_not_prose():
    ctx = get_design_context()
    pointers = ctx["doc_pointers"]
    assert len(pointers) == len(DOC_POINTERS)
    for p in pointers:
        # path + anchor + topic only — never inlined doc prose.
        assert set(p.keys()) == {"topic", "path", "anchor"}
        assert p["path"].startswith("docs/")
        # anchor is either None or a fragment.
        assert p["anchor"] is None or p["anchor"].startswith("#")


def test_context_constants_values_are_live():
    # The curated values are read live from constants.py (not frozen copies).
    ctx = get_design_context()
    for name, value in ctx["constants"].items():
        assert value == getattr(constants, name)


def test_context_constants_include_block_nominals():
    # The studded-System block (LegoBlock) nominal set is surfaced (1.0 -> 1.1
    # additive bump): each name appears in the payload with its constants.py
    # value.  Gates the new surface so it cannot silently regress.
    ctx = get_design_context()
    block_nominals = ("BLOCK_PLAY", "BLOCK_WALL", "BLOCK_ROOF", "CLUTCH_TUBE_OD")
    for name in block_nominals:
        assert name in ctx["constants"], (
            f"block nominal {name!r} missing from get_design_context payload"
        )
        assert ctx["constants"][name] == getattr(constants, name)


# --------------------------------------------------------------------------
# Test #5 — anti-drift: every allowlisted name resolves and is a float
# --------------------------------------------------------------------------

def test_allowlist_anti_drift_every_name_resolves_as_float():
    assert len(CONTEXT_CONSTANTS) > 0
    for name in CONTEXT_CONSTANTS:
        assert hasattr(constants, name), (
            f"CONTEXT_CONSTANTS lists {name!r} but it no longer resolves on "
            "vibe_cading.lego.constants — the curated allowlist has rotted; "
            "remove it (breaking schema bump) or restore the constant."
        )
        value = getattr(constants, name)
        assert isinstance(value, float), (
            f"{name} resolved to {type(value).__name__}, expected float"
        )
