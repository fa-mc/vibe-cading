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

"""``get_design_context`` aggregation (R3).

A **versioned, explicitly-curated, doc-pointer-not-doc-content** aggregate of:

* **(a) the live ``ToleranceProfile``** via ``print_settings.get_profile()`` —
  the active printer fit allowances, resolved fresh per call.
* **(b) a curated allowlist of real-Lego *nominal* constants by name** — NOT a
  reflection sweep over ``constants.py``.  Curation is a deliberate act; an
  anti-drift unit test (``tests/mcp/test_context.py``) asserts every name here
  still resolves on ``vibe_cading.lego.constants`` and is a ``float``, so the
  curation cannot silently rot into a *lying* payload.
* **(c) doc *pointers* (path + anchor)** — never inlined doc prose, so this
  aggregate never needs a docs-freshness gate and never becomes a second,
  un-gated copy of the docs.

SDK-free: this module never imports the ``mcp`` SDK (the isolation discipline is
enforced by this module's unit test importing it with ``mcp`` absent).  It also
imports no CadQuery — both ``vibe_cading.lego.constants`` and
``vibe_cading.print_settings`` are stdlib-only at import.
"""

from __future__ import annotations

from typing import Any

from vibe_cading.lego import constants
from vibe_cading.print_settings import ToleranceProfile, get_profile

# get_design_context payload schema version.  Independent of both
# engine_api.json's schema_version and contract.TOOL_CONTRACT_VERSION (see the
# "two version fields" discussion in the design).  Adding a name to
# CONTEXT_CONSTANTS or a pointer to DOC_POINTERS is an *additive* bump
# (1.0 -> 1.1); removing/renaming a field is a *breaking* bump (1.0 -> 2.0).
CONTEXT_SCHEMA_VERSION = "1.1"

# The curated allowlist: the load-bearing real-Lego *nominal* subset a model
# author actually needs to place geometry on the 8 mm stud grid.  These are
# surfaced by name (not swept) and resolved live from constants.py at call
# time, so a value tweak in constants.py flows through without a code change
# here while a *removal* is caught by the anti-drift test.
#
# Surfaced: the grid/stud, pin-hole, beam, axle, and axle-hole nominals.
# Deliberately EXCLUDED: CORNER_RADIUS / LEAD_IN (internal cosmetic defaults)
# and AXLE_ARM_WIDTH / AXLE_ARM_PROTRUSION (cross-profile *solid* internals
# rarely needed by a consumer authoring on the grid).  The allowlist surfaces
# real-Lego nominals only; it never surfaces printer-tuned fits — those come
# live through ``tolerance_profile`` (matching how constants.py routes fits
# through the profile, not the constant).
#
# Studded-System block nominals (BLOCK_PLAY / BLOCK_WALL / BLOCK_ROOF /
# CLUTCH_TUBE_OD) land with the LegoBlock generator, now merged to main, so they
# resolve on constants.py and are surfaced below.  They are the real-Lego /
# FDM-design nominals a System-block author needs (footprint shrink, wall and
# roof thicknesses, underside clutch-tube Ø); the fussy clutch-tube *bore* fit is
# deliberately NOT a constant — LegoBlock sizes it live from the active
# ToleranceProfile, so it flows through ``tolerance_profile`` like every other
# printer-tuned fit, never the allowlist.  Surfacing this complete block nominal
# set is the additive CONTEXT_SCHEMA_VERSION bump (1.0 -> 1.1) the policy above
# describes.
CONTEXT_CONSTANTS: tuple[str, ...] = (
    # Grid & stud
    "STUD_PITCH", "PLATE_HEIGHT", "BRICK_HEIGHT", "STUD_DIAMETER", "STUD_HEIGHT",
    # Technic pin holes
    "PIN_HOLE_DIAMETER", "HOLE_SPACING", "EDGE_TO_CENTRE",
    # Technic beam (liftarm) cross-section
    "BEAM_THICKNESS", "BEAM_WIDTH", "BEAM_END_RADIUS",
    # Technic axle (solid)
    "AXLE_TIP_TO_TIP", "AXLE_LENGTH_PER_STUD",
    # Technic axle hole (cross profile, real-Lego nominal)
    "AXLE_HOLE_TIP_TO_TIP", "AXLE_HOLE_ARM_WIDTH",
    # Studded-System block (LegoBlock)
    "BLOCK_PLAY", "BLOCK_WALL", "BLOCK_ROOF", "CLUTCH_TUBE_OD",
)

# Doc *pointers* — path + optional in-page anchor.  NOT prose: the consumer
# opens these against its own checkout.  Carries zero prose-drift liability.
DOC_POINTERS: tuple[dict[str, Any], ...] = (
    {"topic": "Lego Technic dimensions", "path": "docs/lego-technic.md", "anchor": None},
    {"topic": "Tuning tolerances", "path": "docs/lego-technic.md", "anchor": "#tuning-tolerances"},
    {"topic": "Print tolerances", "path": "docs/print-tolerances.md", "anchor": None},
    {"topic": "Screw conventions", "path": "docs/screws.md", "anchor": None},
)


def _serialize_profile(profile: ToleranceProfile) -> dict[str, Any]:
    """Serialize a :class:`ToleranceProfile` to the payload wire shape.

    Each fit grade (``free`` / ``slip`` / ``press``) carries its three
    orthogonal allowances (``radial`` / ``axial`` / ``slot``).
    """
    def grade(g: Any) -> dict[str, float]:
        return {"radial": g.radial, "axial": g.axial, "slot": g.slot}

    return {
        "name": profile.name,
        "free": grade(profile.free),
        "slip": grade(profile.slip),
        "press": grade(profile.press),
    }


def get_design_context(profile: str | None = None) -> dict[str, Any]:
    """Aggregate the live design context payload.

    Parameters
    ----------
    profile:
        Optional profile name forwarded to ``print_settings.get_profile``.
        Absent ⇒ the resolved default (``get_profile(None)``, which honours the
        ``.env`` ``PRINT_PROFILE`` / ``print_profiles_user.json`` calibration).
        An unknown name resolves to ``fdm_standard`` (with the existing stderr
        warning), so the returned ``tolerance_profile.name`` reflects the
        *resolved* profile, making a typo visible.

    Returns
    -------
    dict
        The payload described in the design's ``get_design_context`` section:
        ``schema_version`` + live ``tolerance_profile`` + curated ``constants``
        + ``doc_pointers``.  The ``constants`` values are read live from
        ``vibe_cading.lego.constants`` — so the payload is correct as the
        nominals evolve, while the anti-drift test guards against a *removed*
        name producing a lying payload.

    Note
    ----
    ``tolerance_profile`` is **host-dependent by design**: on a calibrated host
    ``get_profile(None)`` returns that host's profile (e.g. ``bambu_p1s``), not
    the shipped ``fdm_standard``.  A test that pins specific tolerance *values*
    must force ``PRINT_PROFILE=fdm_standard`` before importing ``print_settings``
    (see ``tests/mcp/test_context.py``).
    """
    resolved = get_profile(profile)
    constants_payload = {
        name: getattr(constants, name) for name in CONTEXT_CONSTANTS
    }
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "tolerance_profile": _serialize_profile(resolved),
        "constants": constants_payload,
        "doc_pointers": [dict(p) for p in DOC_POINTERS],
    }
