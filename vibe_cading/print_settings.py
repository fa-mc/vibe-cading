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

"""Manufacturing tolerance profiles for printed / machined parts.

The public surface is the two dataclasses ``FitGrade`` and
``ToleranceProfile``, plus the ``get_profile()`` resolver.  A profile
carries three fit grades — ``free``, ``slip``, ``press`` — each of which
is a ``FitGrade(radial, axial)`` pair.

* ``radial`` is the half-extra material added (or removed, when
  negative) on diameter — i.e. add ``radial`` mm to a hole radius for a
  through-hole clearance, or subtract ``radial`` mm for a press-fit
  shaft.
* ``axial`` is the extra material added along the cut axis (typical Z
  direction) — i.e. extend a counterbore floor by ``axial`` mm so the
  fastener head clears its recess.

The split is FDM-aware: print-direction asymmetry means radial and
axial tolerances can diverge — large axial clearance for layer-line
sag, small radial clearance for tight fits.  Resin / CNC profiles
typically use small or zero axial values.

Resolution order at runtime:

1. ``machine_profiles.json``   — repository defaults (tracked).
2. ``machine_profiles_user.json`` — user-local overrides (gitignored;
   dict-merged on top of the defaults).
3. ``VIBE_MACHINE_PROFILE`` env var picks which named profile resolves
   when ``get_profile()`` is called without an explicit name.
4. Hardcoded fallback inside :func:`get_profile` if both JSON files are
   missing or fail to parse.

Both JSON files use a nested schema::

    {
      "fdm_standard": {
        "free":  {"radial": 0.15, "axial": 0.20},
        "slip":  {"radial": 0.05, "axial": 0.20},
        "press": {"radial": -0.04, "axial": 0.20}
      }
    }

For backwards compatibility, the loader also accepts the legacy flat
schema (``z_clearance`` / ``press_fit`` / ``slip_fit`` / ``free_fit``)
and migrates it in-memory by mapping ``z_clearance`` onto every grade's
``.axial`` value.  This bridge is provided so a stale local
``machine_profiles_user.json`` continues to load; the tracked
``machine_profiles.json`` is migrated to the nested schema in Phase 3.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass

from vibe_cading._env import load_env_file

# Seed environment from REPO_ROOT/.env if present (shared parser; see vibe_cading._env).
load_env_file()


def get_default_profile_name() -> str:
    """
    Returns the globally configured machine profile name.
    Defaults to 'fdm_standard' as it's the safest (loosest) tolerance fallback.
    """
    return os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")


@dataclass
class FitGrade:
    """One radial/axial allowance pair for a single fit grade.

    ``radial`` is half-extra-material on diameter (mm); positive widens
    a hole, negative shrinks a peg.  ``axial`` is the along-axis
    allowance (mm); positive deepens a counterbore floor or pocket.
    """
    radial: float
    axial: float = 0.0


@dataclass
class ToleranceProfile:
    """A named bundle of three fit grades, one per fit kind.

    The four mandatory fields (``name``, ``free``, ``slip``, ``press``)
    cover every call site in the library: cutters pick whichever grade
    their fit demands.  ``ClearanceHole`` consumes ``profile.free``;
    ``Bearing.outer_pocket`` consumes ``profile.press``;
    ``Bearing.shaft_cutter`` consumes ``profile.slip``; etc.
    """
    name: str
    free: FitGrade
    slip: FitGrade
    press: FitGrade


# --------------------------------------------------------------------------
# Schema bridging (legacy flat → new nested)
# --------------------------------------------------------------------------

def _is_legacy_flat_entry(entry: dict) -> bool:
    """Heuristic — a dict that has any flat key but no nested ``free``."""
    if not isinstance(entry, dict):
        return False
    if "free" in entry and isinstance(entry["free"], dict):
        return False
    return any(k in entry for k in ("z_clearance", "free_fit", "slip_fit", "press_fit"))


def _migrate_flat_to_nested(entry: dict) -> dict:
    """Convert a legacy flat entry into the new nested schema in-place-safe.

    The old single ``z_clearance`` value is replicated onto every grade's
    ``axial`` slot.  This is the geometry-preserving mapping: every
    historical call site that paired ``prof.<radial>`` with
    ``prof.z_clearance`` continues to pair the same numerical values
    after migration, because each grade's ``.axial`` now carries the
    same value the old single ``z_clearance`` carried.
    """
    z = float(entry.get("z_clearance", 0.0))
    return {
        "free": {
            "radial": float(entry.get("free_fit", 0.15)),
            "axial": z,
        },
        "slip": {
            "radial": float(entry.get("slip_fit", 0.05)),
            "axial": z,
        },
        "press": {
            "radial": float(entry.get("press_fit", 0.04)),
            "axial": z,
        },
    }


def _fitgrade_from_dict(data: dict, *, default_radial: float, default_axial: float = 0.0) -> FitGrade:
    """Build a ``FitGrade`` from a dict, falling back to defaults per field."""
    if not isinstance(data, dict):
        return FitGrade(radial=default_radial, axial=default_axial)
    return FitGrade(
        radial=float(data.get("radial", default_radial)),
        axial=float(data.get("axial", default_axial)),
    )


def _profile_from_nested(name: str, data: dict) -> ToleranceProfile:
    """Build a ``ToleranceProfile`` from a nested-schema dict."""
    return ToleranceProfile(
        name=name,
        free=_fitgrade_from_dict(data.get("free", {}), default_radial=0.15, default_axial=0.20),
        slip=_fitgrade_from_dict(data.get("slip", {}), default_radial=0.05, default_axial=0.0),
        press=_fitgrade_from_dict(data.get("press", {}), default_radial=0.04, default_axial=0.0),
    )


# --------------------------------------------------------------------------
# JSON loading
# --------------------------------------------------------------------------

def _load_json_profiles() -> dict:
    """Load profiles from ``machine_profiles.json`` (defaults) and
    ``machine_profiles_user.json`` (user overrides — gitignored).

    Returns a dict keyed by profile name; each value is a nested-schema
    dict (``{"free": {...}, "slip": {...}, "press": {...}}``).  Legacy
    flat entries are migrated transparently on load.
    """
    profiles: dict = {}

    # 1. Load repository defaults
    repo_file = Path(__file__).parent.parent / "machine_profiles.json"
    if repo_file.exists():
        try:
            with open(repo_file, "r") as f:
                raw = json.load(f)
            for k, v in raw.items():
                profiles[k] = _migrate_flat_to_nested(v) if _is_legacy_flat_entry(v) else v
        except Exception as e:
            print(f"Warning: Could not parse machine_profiles.json - {e}")

    # 2. Load user overrides (takes precedence; dict-merged grade-level).
    user_file = Path(__file__).parent.parent / "machine_profiles_user.json"
    if user_file.exists():
        try:
            with open(user_file, "r") as f:
                user_profiles = json.load(f)
            for k, v in user_profiles.items():
                migrated = _migrate_flat_to_nested(v) if _is_legacy_flat_entry(v) else v
                if k in profiles and isinstance(profiles[k], dict) and isinstance(migrated, dict):
                    # Shallow merge at the grade level — user can override a
                    # single grade without restating the others.
                    merged = dict(profiles[k])
                    for grade_key, grade_val in migrated.items():
                        merged[grade_key] = grade_val
                    profiles[k] = merged
                else:
                    profiles[k] = migrated
        except Exception as e:
            print(f"Warning: Could not parse machine_profiles_user.json - {e}")

    return profiles


# --------------------------------------------------------------------------
# Hardcoded safety fallback (used only when both JSON files are unreadable)
# --------------------------------------------------------------------------

_FALLBACK_PROFILES: dict[str, dict] = {
    "fdm_standard": {
        "free":  {"radial": 0.15, "axial": 0.20},
        "slip":  {"radial": 0.05, "axial": 0.20},
        "press": {"radial": 0.04, "axial": 0.20},
    },
    "resin_precise": {
        "free":  {"radial": 0.05, "axial": 0.05},
        "slip":  {"radial": 0.03, "axial": 0.05},
        "press": {"radial": 0.02, "axial": 0.05},
    },
    "cnc": {
        "free":  {"radial": 0.02, "axial": 0.0},
        "slip":  {"radial": 0.01, "axial": 0.0},
        "press": {"radial": 0.0,  "axial": 0.0},
    },
}


def _fallback_profile(name: str) -> ToleranceProfile:
    name_lower = name.lower()
    if "resin" in name_lower:
        data = _FALLBACK_PROFILES["resin_precise"]
    elif "cnc" in name_lower or "machined" in name_lower:
        data = _FALLBACK_PROFILES["cnc"]
    else:
        data = _FALLBACK_PROFILES["fdm_standard"]
    return _profile_from_nested(name, data)


def get_profile(name: str | None = None) -> ToleranceProfile:
    """Load a specific manufacturing tolerance profile.

    Resolution: the JSON files first, then hardcoded fallback.
    """
    name = name or get_default_profile_name()
    profiles = _load_json_profiles()

    if name in profiles:
        return _profile_from_nested(name, profiles[name])

    # Hardcoded safety fallback if JSON is entirely broken or the name
    # is unknown.
    return _fallback_profile(name)
