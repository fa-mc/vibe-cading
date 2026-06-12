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
is a ``FitGrade(radial, axial, slot)`` triple.

* ``radial`` is the half-extra material added (or removed, when
  negative) on diameter — i.e. add ``radial`` mm to a hole radius for a
  through-hole clearance, or subtract ``radial`` mm for a press-fit
  shaft.  Applies to all features.
* ``axial`` is the extra material added along the cut axis (typical Z
  direction) — i.e. extend a counterbore floor by ``axial`` mm so the
  fastener head clears its recess.
* ``slot`` is an *additional* half-extra-material applied **only** to
  narrow-slot widths, on top of ``radial`` — a narrow ``+`` cross slot
  prints tighter on FDM than the round envelope, so it needs its own
  allowance.  Defaults to ``0.0``; read only by narrow-slot consumers
  such as ``TechnicAxleHole``.

The split is FDM-aware: print-direction asymmetry means radial and
axial tolerances can diverge — large axial clearance for layer-line
sag, small radial clearance for tight fits.  Resin / CNC profiles
typically use small or zero axial values.

Resolution order at runtime
---------------------------

1. ``print_profiles.json``   — repository defaults (tracked).
2. ``print_profiles_user.json`` — user-local overrides (gitignored;
   recursively field-level deep-merged onto the defaults — see
   *Field-level deep-merge* below).
3. ``PRINT_PROFILE`` env var picks which named profile resolves
   when ``get_profile()`` is called without an explicit name.
4. Hardcoded fallback inside :func:`get_profile` if both JSON files are
   missing or fail to parse.

User key convention
-------------------

User-defined profile keys are recommended (not enforced) to follow the
``<machine>__<material>[__<brand>]`` lexical convention, using
``__`` (double underscore) as the separator — shell-glob-safe and
collision-free against hyphenated machine names.  Examples::

    "bambu_p1s__pla_overture": { ... }
    "ender3__petg_polymaker": { ... }
    "prusa_mk4__pla":          { ... }

The convention is purely documentary — the loader treats every
top-level key as an opaque profile name and does not decompose it.
The shipped fallback keys (``fdm_standard``, ``resin_precise``,
``cnc``) remain the coarse-default categories and are exempt from the
convention.

Field-level deep-merge
----------------------

User overrides merge recursively onto the shipped defaults, leaf-wins.
This means a user can override exactly one numeric field without
restating the rest of a fit grade::

    # print_profiles.json (shipped)
    {"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}

    # print_profiles_user.json (user override — calibrate one knob)
    {"fdm_standard": {"slip": {"radial": 0.11}}}

    # Resolved ToleranceProfile.slip:
    #   radial = 0.11   ← user override
    #   axial  = 0.20   ← inherited from shipped
    #   slot   = 0.10   ← inherited from shipped

A ``null`` (JSON null / Python ``None``) at any leaf override raises
``ValueError`` — silent "reset to default" via ``null`` is too easy a
foot-gun, and ``null`` is not a tolerance-domain-valid value.  A
type-mismatch (e.g. user puts a primitive where the shipped profile
has a dict) likewise raises ``ValueError`` with the JSON-pointer-style
key path, preventing silent shape coercion downstream.

Legacy flat → nested schema
---------------------------

For backwards compatibility, the loader also accepts the legacy flat
schema (``z_clearance`` / ``press_fit`` / ``slip_fit`` / ``free_fit``)
and migrates it in-memory by mapping ``z_clearance`` onto every grade's
``.axial`` value.  Migration runs on each side (shipped + user)
**independently before** the field-level deep merge — see
:func:`_load_json_profiles`.  The legacy flat schema has no
narrow-slot concept, so a migrated profile gets ``slot = 0.0`` on
every grade — pre-Stage-2b narrow-slot behaviour, which intentionally
diverges from the shipped nested ``fdm_standard`` (``slip.slot =
0.10``).  A user file in *combined* shape (legacy-flat sibling keys
alongside a nested ``free`` dict) is detected as nested by
:func:`_is_legacy_flat_entry` and the flat-style siblings (``z_clearance``,
``slip_fit``, …) are silently ignored — in practice a hand-edited user
file does not produce this combination.
"""

import json
import os
import sys
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from vibe_cading._env import load_env_file

# Seed environment from REPO_ROOT/.env if present (shared parser; see vibe_cading._env).
load_env_file()


# --------------------------------------------------------------------------
# Warning emitter (deprecation + general user-warning, once-per-process)
# --------------------------------------------------------------------------

# Module-level state — guards against repeat emissions across the many
# get_profile() calls in a single process.  Each entry is a stable key
# string identifying *what* was warned about (e.g.
# "shipped_file_legacy_only", "unknown_profile_foo"); the *first* call
# with a given key emits both a stderr line and a ``warnings.warn`` of
# the requested category, subsequent calls with the same key are no-ops.
#
# Renamed from ``_emitted_deprecations`` when the once-per-process
# guard was generalised to cover the unknown-profile-name ``UserWarning``
# in addition to the original ``DeprecationWarning`` cases — the guarding
# mechanism is category-agnostic, only the message prefix and warning
# category differ per call site.
_emitted_warnings: set[str] = set()

# Backwards-compatibility alias for any external test code that imported
# the pre-refactor name.  The set object is the same — both names point
# at the single source of truth above.
_emitted_deprecations = _emitted_warnings


def _emit_once(
    key: str,
    message: str,
    *,
    category: type[Warning] = DeprecationWarning,
    prefix: str = "DEPRECATION",
    stacklevel: int = 3,
) -> None:
    """Emit a warning of ``category`` exactly once per process per ``key``.

    Mechanism: ``warnings.warn`` for programmatic filtering + a
    one-shot stderr mirror so the user sees the warning even with
    default CPython warning filters (which suppress
    ``DeprecationWarning`` by default in many contexts, and may
    suppress ``UserWarning`` depending on environment).

    Belt-and-suspenders: the stderr mirror guarantees visibility; the
    ``warnings.warn`` call lets test suites and tooling capture
    programmatically.  Both are gated by the same idempotence set so
    a noisy hot-path call (every ``get_profile()`` invocation) emits
    at most one of each kind per (process, key).

    ``stacklevel=N`` attributes the warning to the N-th frame up from
    ``warnings.warn``; default ``3`` = caller-of-caller of
    :func:`_emit_once` (i.e. the function that called the thin
    wrapper, which called this).  Pass a higher value when the chain
    has additional intermediate frames so tooling that filters
    warnings by source location attributes the warning to the
    user-visible public surface instead of an internal helper.
    """
    if key in _emitted_warnings:
        return
    _emitted_warnings.add(key)
    print(f"{prefix}: {message}", file=sys.stderr)
    warnings.warn(message, category, stacklevel=stacklevel)


def _emit_deprecation_once(key: str, message: str, *, stacklevel: int = 3) -> None:
    """Emit a deprecation warning exactly once per process per ``key``.

    Thin wrapper around :func:`_emit_once` preserving the prior name and
    signature; defaults to ``DeprecationWarning`` + ``"DEPRECATION"``
    stderr prefix.  See :func:`_emit_once` for the frame-counting
    semantics of ``stacklevel`` — default ``3`` attributes the warning to
    the caller-of-caller of ``_emit_deprecation_once`` (e.g. the
    user-visible public function that called the resolver that called
    this).
    """
    _emit_once(
        key,
        message,
        category=DeprecationWarning,
        prefix="DEPRECATION",
        stacklevel=stacklevel,
    )


# --------------------------------------------------------------------------
# Env-var resolution
# --------------------------------------------------------------------------

def get_default_profile_name() -> str:
    """Return the globally configured print-profile name.

    Resolution chain (first match wins):

    1. ``PRINT_PROFILE`` — canonical env var.
    2. ``"fdm_standard"`` — hardcoded coarse default (loosest /
       safest profile).
    """
    name = os.getenv("PRINT_PROFILE")
    if name:
        return name

    # No env var set — hardcoded coarse default.
    return "fdm_standard"


@dataclass
class FitGrade:
    """The three orthogonal manufacturing allowances for a single fit grade.

    All three are independent — a feature applies whichever ones its
    geometry calls for:

    * ``radial`` — half-extra-material on diameter (mm), applied to **all**
      features; positive widens a hole, negative shrinks a peg.
    * ``axial`` — the along-axis allowance (mm); positive deepens a
      counterbore floor or pocket.
    * ``slot`` — an *additional* half-extra-material (mm) applied **only**
      to narrow-slot widths, **on top of** ``radial``.  It exists because a
      narrow ``+`` cross slot prints tighter on FDM than the round envelope
      of the same nominal — the two need physically distinct clearances.
      Defaults to ``0.0`` (no narrow-slot widening); only narrow-slot
      consumers such as :class:`TechnicAxleHole` read it.
    """
    radial: float
    axial: float = 0.0
    slot: float = 0.0   # extra half-width for narrow-slot FDM tightening


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


def _fitgrade_from_dict(
    data: dict,
    *,
    default_radial: float,
    default_axial: float = 0.0,
    default_slot: float = 0.0,
) -> FitGrade:
    """Build a ``FitGrade`` from a dict, falling back to defaults per field.

    ``default_slot`` stays ``0.0`` — an omitted ``slot`` key always loads
    as ``0.0``.  The shipped non-zero ``slot`` (0.10 on ``fdm_standard``)
    lives in the JSON *data*, not this dataclass-load default, so a
    legacy-flat profile (which never carries a ``slot`` key) migrates to
    ``slot = 0.0`` and keeps pre-Stage-2b narrow-slot behaviour.
    """
    if not isinstance(data, dict):
        return FitGrade(radial=default_radial, axial=default_axial, slot=default_slot)
    return FitGrade(
        radial=float(data.get("radial", default_radial)),
        axial=float(data.get("axial", default_axial)),
        slot=float(data.get("slot", default_slot)),
    )


def _profile_from_nested(name: str, data: dict) -> ToleranceProfile:
    """Build a ``ToleranceProfile`` from a nested-schema dict."""
    return ToleranceProfile(
        name=name,
        free=_fitgrade_from_dict(
            data.get("free", {}), default_radial=0.15, default_axial=0.20, default_slot=0.0,
        ),
        slip=_fitgrade_from_dict(
            data.get("slip", {}), default_radial=0.05, default_axial=0.0, default_slot=0.0,
        ),
        press=_fitgrade_from_dict(
            data.get("press", {}), default_radial=0.04, default_axial=0.0, default_slot=0.0,
        ),
    )


# --------------------------------------------------------------------------
# Field-level deep merge (recursive, leaf-wins)
# --------------------------------------------------------------------------

def _validate_no_null_leaves(d: dict, _path: tuple[str, ...]) -> None:
    """Recursively assert that no leaf in ``d`` is ``None``.

    Used by :func:`_deep_merge_profiles` Pass 2 (branch (b) — override-only
    sub-trees) to extend branch (f)'s null-rejection rule into nested
    override-only dicts.  Without this walk, a user override that introduces
    a brand-new top-level profile key whose nested leaf is ``None`` (e.g.
    ``{"new_profile": {"slip": {"radial": null}}}``) would bypass the
    top-level None check — Pass 2's existing guard only fires on the
    immediate override value, not on nested children.

    Raises ``ValueError`` using the same JSON-pointer-style key-path
    message format as branch (f) in :func:`_deep_merge_profiles`.
    """
    for k, v in d.items():
        path_k = _path + (k,)
        if v is None:
            raise ValueError(
                f"null tolerance at {'/'.join(path_k)} is not a valid override"
            )
        if isinstance(v, dict):
            _validate_no_null_leaves(v, path_k)


def _deep_merge_profiles(
    base: dict, override: dict, *, _path: tuple[str, ...] = ()
) -> dict:
    """Recursive leaf-wins merge of ``override`` onto ``base``.

    Invariants:
      - Both inputs are dicts; output is a NEW dict (base and override
        unmodified).
      - At each key, the recursion rule is:
          (a) key absent from override → ``base[k]`` copied through unchanged
          (b) key absent from base → ``override[k]`` copied through verbatim;
              if ``override[k]`` is a dict, its nested leaves are
              recursively validated against branch (f) (no ``None`` leaves
              anywhere in the override-only sub-tree) via
              :func:`_validate_no_null_leaves`
          (c) both present, both dict → recurse with ``_path + (k,)``
          (d) both present, both NON-dict → ``override[k]`` wins (leaf override)
          (e) both present, MIXED → ``ValueError`` naming the key path
              (this rules out the silent shape-coercion failure mode the
              domain-integrity gate guards against)
          (f) override leaf is ``None`` → ``ValueError`` naming the key path
              (silent "reset to default via null" is too easy a foot-gun;
              ``null`` is not a tolerance-domain-valid value)
      - Sequences (lists, tuples) are treated as LEAVES — override wins
        wholesale.  (No element-wise merge; tolerance JSON never carries
        lists, but defining the rule explicitly prevents future surprise.)
      - Unrecognized leaf keys silently pass through; ``_fitgrade_from_dict``
        reads only known field names (``radial``, ``axial``, ``slot``) so
        a typo'd override (``radail``) is loaded into the merged dict but
        never read by any consumer.  See design brief §1 for the trade-off
        rationale and Test T5 for the failure-mode-visibility check.
    """
    # unrecognized keys silently accepted; see design brief §1
    out: dict = {}

    # Pass 1: every key from base.
    for k, base_v in base.items():
        path_k = _path + (k,)
        if k not in override:
            # branch (a) — key absent from override
            out[k] = base_v
            continue

        override_v = override[k]

        # branch (f) — null leaf is a hard error regardless of base type
        if override_v is None:
            raise ValueError(
                f"null tolerance at {'/'.join(path_k)} is not a valid override"
            )

        base_is_dict = isinstance(base_v, dict)
        override_is_dict = isinstance(override_v, dict)

        if base_is_dict and override_is_dict:
            # branch (c) — recurse
            out[k] = _deep_merge_profiles(base_v, override_v, _path=path_k)
        elif not base_is_dict and not override_is_dict:
            # branch (d) — both leaves; override wins
            out[k] = override_v
        else:
            # branch (e) — type mismatch
            raise ValueError(
                f"type mismatch at {'/'.join(path_k)}: "
                f"base is {type(base_v).__name__}, override is {type(override_v).__name__}"
            )

    # Pass 2: keys only in override (branch (b)).
    for k, override_v in override.items():
        if k in base:
            continue
        path_k = _path + (k,)
        # branch (f) also applies to override-only leaves at the top of any
        # nested level; a user override that introduces a NEW leaf with
        # explicit null is still incoherent and should be rejected.
        if override_v is None:
            raise ValueError(
                f"null tolerance at {'/'.join(path_k)} is not a valid override"
            )
        # branch (f) extension: if the override-only value is itself a dict,
        # recursively reject any None leaf nested inside it.  Without this
        # walk, a brand-new top-level profile key with a nested null leaf
        # (e.g. {"new_profile": {"slip": {"radial": null}}}) would slip past
        # the top-level None check above — Pass 2 does NOT recurse into
        # override-only dict values for merging, so the validation must be
        # an explicit standalone walk.
        if isinstance(override_v, dict):
            _validate_no_null_leaves(override_v, path_k)
        out[k] = override_v

    return out


# --------------------------------------------------------------------------
# JSON loading
# --------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent


def _resolve_shipped_file() -> Path | Any | None:
    """Resolve the shipped-defaults file path, or ``None`` if absent."""
    try:
        from importlib.resources import files
        resource = files("vibe_cading").joinpath("print_profiles.json")
        if resource.is_file():
            return resource
    except (ImportError, Exception):
        pass
    path = _REPO_ROOT / "vibe_cading" / "print_profiles.json"
    return path if path.exists() else None


def _resolve_user_file() -> Path | Any | None:
    """Resolve the user-override file path, or ``None`` if absent."""
    import os
    # 1. Env Var override
    env_path = os.getenv("VIBE_PRINT_PROFILES_USER_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    # 2. Current working directory
    cwd_path = Path.cwd() / "print_profiles_user.json"
    if cwd_path.exists():
        return cwd_path
    # 3. Fallback to repo root
    path = _REPO_ROOT / "print_profiles_user.json"
    return path if path.exists() else None


def _normalise_raw_profiles(raw: dict) -> dict:
    """Run legacy-flat → nested migration on every top-level entry.

    Returns a new dict; the input is not modified.  Migration runs
    *per side* (shipped + user) *before* :func:`_deep_merge_profiles`
    so the merge always sees structurally compatible dict shapes — see
    design brief §2.
    """
    return {
        k: (_migrate_flat_to_nested(v) if _is_legacy_flat_entry(v) else v)
        for k, v in raw.items()
    }


def _load_json_profiles() -> dict:
    """Load profiles from the shipped + user JSON files.

    Returns a dict keyed by profile name; each value is a nested-schema
    dict (``{"free": {...}, "slip": {...}, "press": {...}}``).  Legacy
    flat entries are migrated transparently on load.  User overrides are
    merged onto the shipped defaults via :func:`_deep_merge_profiles`
    (field-level recursive leaf-wins) — a user override of a single leaf
    inherits its sibling fields from the shipped grade.
    """
    shipped_norm: dict = {}
    user_norm: dict = {}

    # 1. Load shipped defaults.
    shipped_file = _resolve_shipped_file()
    if shipped_file is not None:
        try:
            with shipped_file.open("r") as f:
                shipped_raw = json.load(f)
            shipped_norm = _normalise_raw_profiles(shipped_raw)
        except Exception as e:
            print(f"Warning: Could not parse {shipped_file.name} - {e}")

    # 2. Load user overrides.
    user_file = _resolve_user_file()
    if user_file is not None:
        try:
            with user_file.open("r") as f:
                user_raw = json.load(f)
            user_norm = _normalise_raw_profiles(user_raw)
        except Exception as e:
            print(f"Warning: Could not parse {user_file.name} - {e}")

    # 3. Field-level deep merge — user overrides win at every leaf.
    return _deep_merge_profiles(shipped_norm, user_norm)


# --------------------------------------------------------------------------
# Hardcoded safety fallback (used only when both JSON files are unreadable)
# --------------------------------------------------------------------------

_FALLBACK_PROFILES: dict[str, dict] = {
    "fdm_standard": {
        "free":  {"radial": 0.15, "axial": 0.20},
        # ``slip.slot`` mirrors the shipped print_profiles.json — the
        # conservative narrow-slot floor for FDM cross axle holes.
        "slip":  {"radial": 0.05, "axial": 0.20, "slot": 0.10},
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
    """Resolve a coarse-default fallback ``ToleranceProfile`` by name.

    Looks up ``name`` in :data:`_FALLBACK_PROFILES`; if unknown, returns
    the ``fdm_standard`` defaults (loosest / safest).  Substring-based
    heuristic classification (e.g. "anything containing 'resin' resolves
    to resin_precise") was dropped per Q2 — the new ``<machine>__<material>``
    user-key convention makes substring matching accidental.  Callers
    that hit the unknown path should rely on the warning emitted by
    :func:`get_profile`.
    """
    data = _FALLBACK_PROFILES.get(name, _FALLBACK_PROFILES["fdm_standard"])
    return _profile_from_nested(name, data)


def get_profile(name: str | None = None) -> ToleranceProfile:
    """Load a specific manufacturing tolerance profile.

    Resolution: the JSON files first, then hardcoded fallback.  If
    ``name`` is not a known profile (neither in the JSON files nor in
    the hardcoded fallback set), a stderr warning is emitted naming the
    unknown name and the active fallback (``fdm_standard``), and the
    returned profile carries ``name == "fdm_standard"`` — i.e. the
    requested name is NOT silently propagated as the resolved profile's
    label, so downstream calibration mistakes are visible.
    """
    name = name or get_default_profile_name()
    profiles = _load_json_profiles()

    if name in profiles:
        return _profile_from_nested(name, profiles[name])

    if name in _FALLBACK_PROFILES:
        # Hardcoded safety fallback if JSON is entirely broken but the
        # name is one of the known coarse defaults.
        return _fallback_profile(name)

    # Unknown name — emit a warning and resolve to fdm_standard.  The
    # returned profile is labelled "fdm_standard", NOT the unknown name,
    # so a calibration mistake (typo in PRINT_PROFILE, missing
    # profile entry, etc.) does not silently mask itself.  Routed through
    # ``_emit_once`` so a build loop that repeatedly resolves the same
    # unknown name (e.g. once per model class) does not spam stderr —
    # one warning per (process, unknown-name) is sufficient signal.
    _emit_once(
        f"unknown_profile_{name}",
        f"unknown print profile '{name}'; falling back to 'fdm_standard'. "
        f"Add a '{name}' entry to print_profiles_user.json or pick a shipped "
        f"profile name (fdm_standard, resin_precise, cnc).",
        category=UserWarning,
        prefix="WARNING",
        stacklevel=2,  # attribute to ``get_profile`` — the public surface
    )
    return _fallback_profile("fdm_standard")
