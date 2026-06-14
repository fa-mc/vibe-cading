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

#!/usr/bin/env python3
"""Generic multi-knob print-tolerance calibration helper.

Walks a contributor through calibrating the most-consumed print-tolerance
knobs against printable mechanical gauges (M3 clearance hole, M3 nut
press-fit pocket, opt-in Lego axle hole), and writes the calibrated
values into the active ``<machine>__<material>[__<brand>]`` entry of
``print_profiles_user.json`` via per-knob field-level merged atomic
writes — so every downstream ``get_profile()`` consumer inherits the
calibrated values on the next call with zero source edits.

Sanctioned in-tree consumer of two underscored helpers from
``vibe_cading.print_settings`` (``_is_legacy_flat_entry`` and
``_migrate_flat_to_nested``) — see design brief Architecture
*Alternatives rejected R1*. The legacy-flat → nested migration is run
**per-target-entry on write** so the user file's untouched profiles
remain JSON-semantically identical.

Subcommand layout
-----------------
::

    python3 tools/calibrate.py                  # sequence: free, press
    python3 tools/calibrate.py all              # explicit sequence
    python3 tools/calibrate.py free             # only free.radial
    python3 tools/calibrate.py press            # only press.radial
    python3 tools/calibrate.py slip             # opt-in slip.radial
    python3 tools/calibrate.py free --diameter 3.30 --yes \\
        --profile bambu_p1s__pla_overture

CadQuery is **lazy-imported** — running ``--help`` does NOT trigger
the CadQuery import cascade, keeping the help path under the runtime
budget (design Success Criterion 3).
"""

from __future__ import annotations

import argparse
import copy
import errno
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

# IMPORTANT: only stdlib imports + ``vibe_cading.print_settings`` may
# appear at module load time — the help path runs without any CadQuery
# or gauge import. Gauge classes and ``METRIC_SIZES`` / ``MetricHexNut``
# / ``AXLE_HOLE_TIP_TO_TIP`` are imported lazily inside
# ``_load_knob_runtime``.

# Self-bootstrap sys.path so the script runs as a fresh subprocess from
# any cwd (mirrors build.py:24). Required when invoked via
# ``python tools/calibrate.py …`` without PYTHONPATH set — most notably
# by tests/tools/test_calibrate.py which subprocess.runs the --help path.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vibe_cading.print_settings import (
    _is_legacy_flat_entry,
    _migrate_flat_to_nested,
    get_default_profile_name,
)


_USER_FILE = _REPO_ROOT / "print_profiles_user.json"

# Profile names that may freely receive calibrations even with ``--yes``
# and no ``--profile``. These are hardcoded shipped fallback names and
# cannot be "typo'd into existence".
_SHIPPED_PROFILE_NAMES: frozenset[str] = frozenset(
    {"fdm_standard", "resin_precise", "cnc"}
)

# Hardcoded representative consumer lists per knob. The full inventory
# lives in the design brief §2; here we name 3-4 prominent ones each so
# the user sees what they just dialled in. Auto-discovery (AST/grep) is
# out of scope per design Out of Scope.
_CONSUMERS: dict[str, tuple[str, ...]] = {
    "free": (
        "MetricMachineScrew.to_cutter (shaft clearance)",
        "ClearanceHole, CounterboreHole, CountersinkHole, HexHole, Bore "
        "(every vibe_cading/mechanical/holes.py class)",
        "Standoff.to_cutter, Hinge.to_cutter",
        "FreespinHexHub.bearing_seat_diameter",
    ),
    "press": (
        "Bearing.outer_pocket (vibe_cading/mechanical/bearings.py)",
        "MetricHexNut.to_cutter(fit='press') "
        "(vibe_cading/mechanical/nuts/metric.py)",
        "(every future press-fit pocket consumer)",
    ),
    "slip": (
        "TechnicAxleHole (vibe_cading/lego/cutters/technic_axle_hole.py)",
        "Magnet.to_cutter (vibe_cading/mechanical/magnets.py)",
        "Bearing.shaft_cutter (vibe_cading/mechanical/bearings.py)",
    ),
}


# --------------------------------------------------------------------------
# Knob runtime — gauges + nominals (lazy-loaded)
# --------------------------------------------------------------------------

class _KnobRuntime:
    """Bundle of (gauge instance, nominal, grade, field) for a knob.

    Constructed lazily inside ``_load_knob_runtime`` so the ``--help``
    code path never touches CadQuery or the gauge modules.
    """

    def __init__(
        self,
        knob: str,
        gauge: Any,
        nominal: float,
        valid: tuple[float, ...],
        grade: str,
        field: str,
        gauge_fqn: str,
    ) -> None:
        self.knob = knob
        self.gauge = gauge
        self.nominal = nominal
        self.valid = valid
        self.grade = grade
        self.field = field
        self.gauge_fqn = gauge_fqn


def _load_knob_runtime(knob: str) -> _KnobRuntime:
    """Resolve the gauge + nominal for a knob. Lazy CadQuery import."""
    if knob == "free":
        # Lazy imports — these trigger the CadQuery cascade.
        from vibe_cading.mechanical.calibration.m3_clearance_gauge import (
            MThreeClearanceGauge,
        )
        from vibe_cading.mechanical.screws.metric import METRIC_SIZES
        gauge = MThreeClearanceGauge()
        return _KnobRuntime(
            knob="free",
            gauge=gauge,
            nominal=float(METRIC_SIZES["M3"]["clearance"]),
            valid=gauge.diameters,
            grade="free",
            field="radial",
            gauge_fqn=(
                "vibe_cading.mechanical.calibration."
                "m3_clearance_gauge.MThreeClearanceGauge"
            ),
        )
    if knob == "press":
        from vibe_cading.mechanical.calibration.m3_nut_pocket_gauge import (
            MThreeNutPocketGauge,
        )
        from vibe_cading.mechanical.nuts.metric import MetricHexNut
        gauge = MThreeNutPocketGauge()
        return _KnobRuntime(
            knob="press",
            gauge=gauge,
            nominal=float(MetricHexNut.DIMENSIONS["M3"]["width_flats"]),
            valid=gauge.widths,
            grade="press",
            field="radial",
            gauge_fqn=(
                "vibe_cading.mechanical.calibration."
                "m3_nut_pocket_gauge.MThreeNutPocketGauge"
            ),
        )
    if knob == "slip":
        from vibe_cading.lego.axle_hole_gauge import AxleHoleGauge
        from vibe_cading.lego.constants import AXLE_HOLE_TIP_TO_TIP
        gauge = AxleHoleGauge()
        return _KnobRuntime(
            knob="slip",
            gauge=gauge,
            nominal=float(AXLE_HOLE_TIP_TO_TIP),
            valid=gauge.diameters,
            grade="slip",
            field="radial",
            gauge_fqn=(
                "vibe_cading.lego.axle_hole_gauge.AxleHoleGauge"
            ),
        )
    raise ValueError(f"unknown knob {knob!r}")


# --------------------------------------------------------------------------
# Calibration formula (uniform across knobs — see design §1)
# --------------------------------------------------------------------------

def _compute_radial(diameter: float, nominal: float) -> float:
    """``radial = (D - N) / 2`` — see design brief §1 calibration table.

    Rounded to 4 decimal places so the value persisted to
    ``print_profiles_user.json`` is readable (the sweep tuples
    themselves are quantised to 0.01 mm, so the calibrated value has
    at most 3 significant decimal digits of physical meaning; 4dp
    leaves a digit of headroom and dodges the binary-float artefact
    ``0.05 → 0.04999999999999982`` that ``(D - N) / 2`` produces).
    """
    return round((float(diameter) - float(nominal)) / 2.0, 4)


# --------------------------------------------------------------------------
# Data assembly layer (T6)
# --------------------------------------------------------------------------

def _read_user_profiles_raw(path: Path = _USER_FILE) -> dict:
    """Return the raw user-profile dict. ``{}`` if the file is missing.

    A JSON parse error is fatal (FR23) — surface the error and the
    file path on stderr, leave the file untouched, and let ``main``
    return non-zero.
    """
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"ERROR: failed to parse {path}: {e}\n"
            f"The file is left untouched. Fix the JSON syntax manually "
            f"and re-run."
        )


def _resolve_target_entry(
    raw: dict, name: str
) -> tuple[dict, bool]:
    """Return ``(entry, was_legacy_flat)`` for the target profile name.

    Missing entry → ``({}, False)``. A legacy-flat entry is returned
    as-is; the caller invokes ``_migrate_if_legacy_flat`` before
    setting the calibrated leaf.
    """
    if name not in raw:
        return ({}, False)
    entry = raw[name]
    if not isinstance(entry, dict):
        # Defensive: a non-dict at the profile slot is malformed; treat
        # as missing rather than corrupting it further.
        return ({}, False)
    return (entry, _is_legacy_flat_entry(entry))


def _migrate_if_legacy_flat(entry: dict) -> dict:
    """Thin wrapper around ``_migrate_flat_to_nested``.

    Returns the nested-schema equivalent. No-op if already nested.
    """
    if _is_legacy_flat_entry(entry):
        return _migrate_flat_to_nested(entry)
    return entry


def _build_after_entry(
    entry: dict, grade: str, field: str, value: float
) -> dict:
    """Deep-copy ``entry`` and set ``entry[grade][field] = value``.

    Sibling fields are preserved verbatim. The nested grade dict is
    created if absent.
    """
    out = copy.deepcopy(entry) if entry else {}
    if grade not in out or not isinstance(out.get(grade), dict):
        out[grade] = {}
    out[grade][field] = float(value)
    return out


# --------------------------------------------------------------------------
# Atomic-write layer (T8)
# --------------------------------------------------------------------------

# Pinned canonical serialisation form — see design §3 normalisation
# contract. Any handwritten formatting in the user's
# ``print_profiles_user.json`` WILL be normalised to this form on the
# first calibrate.py write; JSON-semantic content is preserved.
_JSON_INDENT = 2
_JSON_SORT_KEYS = True


def _serialise_canonical(data: dict) -> str:
    """Canonical JSON serialisation pinned by the §3 contract."""
    return json.dumps(
        data, indent=_JSON_INDENT, sort_keys=_JSON_SORT_KEYS
    ) + "\n"


def _cleanup_tempfiles(path: Path, knob: str) -> None:
    """Best-effort sweep of stale ``<path>.tmp.*.<knob>`` files.

    Runs after a successful write and on cleanup paths. Silent on
    failure — never mask the original exception.
    """
    pattern = f"{path}.tmp.*.{knob}"
    for stale in glob.glob(pattern):
        try:
            os.remove(stale)
        except OSError:
            pass


def _atomic_write_json(path: Path, data: dict, knob: str) -> None:
    """Atomic write: tempfile → fsync → ``os.replace`` → cleanup.

    Tempfile name includes ``<pid>.<knob>`` so a parallel calibration
    session writing the same file does not race into a half-written
    file. ``os.replace`` is atomic on POSIX.
    """
    payload = _serialise_canonical(data)
    pid = os.getpid()
    tmp_path = Path(f"{path}.tmp.{pid}.{knob}")
    try:
        # Open in text mode; explicit encoding avoids surprises on
        # exotic system locales.
        fd = os.open(
            str(tmp_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            # If write/fsync fails, the file descriptor is already
            # consumed by fdopen and closed by its context manager.
            raise
        # Atomic rename. Failure here means the tempfile may still
        # exist; the except branch cleans it up.
        os.replace(str(tmp_path), str(path))
    except BaseException:
        # Best-effort cleanup; preserve the original exception.
        try:
            if tmp_path.exists():
                os.remove(str(tmp_path))
        except OSError as cleanup_err:
            if cleanup_err.errno != errno.ENOENT:
                pass
        raise
    finally:
        _cleanup_tempfiles(path, knob)


# --------------------------------------------------------------------------
# Interaction layer (T7)
# --------------------------------------------------------------------------

def _prompt_diameter(
    valid: tuple[float, ...], gauge_name: str
) -> float:
    """Prompt for the best-fitting gauge variant. Validates strictly.

    Per design Q3 + FR11 — only values in the live gauge sweep tuple
    are accepted. A custom diameter must be supplied via a v2 escape
    hatch (out of scope).
    """
    choices = ", ".join(f"{d:.2f}" for d in valid)
    while True:
        prompt = (
            f"Best-fitting {gauge_name} variant (mm) "
            f"[valid: {choices}]: "
        )
        try:
            raw = input(prompt).strip()
        except EOFError:
            raise SystemExit(
                "ERROR: no input provided (stdin closed). "
                "Re-run with --diameter <value> for non-interactive use."
            )
        if not raw:
            print(
                "Please enter one of the valid variants.",
                file=sys.stderr,
            )
            continue
        try:
            value = float(raw)
        except ValueError:
            print(
                f"'{raw}' is not a number. "
                f"Valid choices: {choices}",
                file=sys.stderr,
            )
            continue
        if not _value_in_valid(value, valid):
            print(
                f"{value:.2f} is not a valid choice. "
                f"Valid choices: {choices}",
                file=sys.stderr,
            )
            continue
        return value


def _value_in_valid(value: float, valid: tuple[float, ...]) -> bool:
    """True if ``value`` matches any sweep entry within float tolerance."""
    return any(abs(value - v) <= 1e-6 for v in valid)


def _prompt_profile_name_confirmation(name: str) -> str:
    """Confirm a fresh non-shipped profile name. Default-Enter accepts.

    The user may re-type to fix a typo. See design §4 step 3 / FR20.
    """
    print(
        f"The profile name '{name}' does not yet exist in "
        f"print_profiles_user.json and does not match any shipped "
        f"fallback."
    )
    print(
        "It will be CREATED. Recommended convention: "
        "<machine>__<material>[__<brand>]."
    )
    try:
        raw = input(f"Confirm key name [{name}]: ").strip()
    except EOFError:
        # Non-interactive run; default-accept.
        return name
    return raw or name


def _prompt_confirm() -> bool:
    """Plain y/N; default N. Per design §6."""
    try:
        raw = input("Apply this change? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return raw in ("y", "yes")


def _format_value(v: float) -> str:
    """Three-decimal pretty-format used in the change preview."""
    return f"{v:.3f}"


def _render_preview(
    *,
    user_file: Path,
    user_file_exists: bool,
    profile_name: str,
    profile_existed: bool,
    profile_source: str,
    grade: str,
    field: str,
    before_value: float | None,
    before_inherited_from: str | None,
    after_value: float,
    diameter: float,
    nominal: float,
    nominal_source: str,
    was_legacy_flat: bool,
    knob: str,
) -> str:
    """Render the change preview block. See design §6 wire format."""
    file_qualifier = " (will be CREATED)" if not user_file_exists else ""
    profile_qualifier = (
        " (will be CREATED)" if not profile_existed else ""
    )
    lines = [
        "Calibration target",
        f"  File:    {user_file.name}{file_qualifier}",
        f"  Profile: {profile_name}{profile_qualifier}",
        f"                                                  "
        f"(resolved from {profile_source})",
        f"  Grade:   {grade}",
        f"  Field:   {field}",
        "",
        "Change",
    ]
    if before_value is None:
        # Fresh leaf — show the safety-default value for clarity.
        lines.append(
            f"  Before:  {grade}.{field} = (unset; would resolve via "
            f"_fitgrade_from_dict safety defaults)"
        )
    else:
        inherited_qualifier = (
            f" (inherited from {before_inherited_from})"
            if before_inherited_from
            else ""
        )
        lines.append(
            f"  Before:  {grade}.{field} = "
            f"{_format_value(before_value)} mm{inherited_qualifier}"
        )
    lines.extend([
        f"  After:   {grade}.{field} = "
        f"{_format_value(after_value)} mm",
        "",
        "Derivation",
        f"  Best-fitting gauge variant D = "
        f"{diameter:.3f} mm         (your input)",
        f"  Nominal N                    = "
        f"{nominal:.3f} mm         ({nominal_source})",
        f"  {grade}.{field} = (D − N) / 2 = "
        f"{_format_value(after_value)} mm",
        "",
        "Migration",
    ])
    if was_legacy_flat:
        lines.extend([
            "  Will migrate the existing legacy-flat entry to the nested",
            "  schema before applying the calibration",
            "  (z_clearance → axial on every grade).",
        ])
    else:
        lines.append("  (none — profile is in nested schema)")
    lines.extend([
        "",
        f"Downstream consumers that will inherit "
        f"{grade}.{field} = {_format_value(after_value)} mm:",
    ])
    for consumer in _CONSUMERS[knob]:
        lines.append(f"  - {consumer}")
    lines.extend([
        "",
        "Other grades and fields are preserved verbatim.",
        "",
    ])
    return "\n".join(lines)


def _render_success(
    *,
    profile_name: str,
    grade: str,
    field: str,
    after_value: float,
    knob: str,
    fresh_profile_with_slip_only: bool,
    fresh_profile_without_slot: bool,
    next_knob: str | None,
) -> str:
    """Render the post-write success block. See design Q8 resolution."""
    lines = [
        "",
        f"WROTE {profile_name}.{grade}.{field} = "
        f"{_format_value(after_value)} mm to "
        f"{_USER_FILE.name}",
        "",
        f"Downstream consumers now resolve "
        f"{grade}.{field} = {_format_value(after_value)} mm:",
    ]
    for consumer in _CONSUMERS[knob]:
        lines.append(f"  - {consumer}")

    # Stage-2b slip.slot floor surface (NOT seed) — see design §4
    # and the Independent Domain Expert C1 condition. Only fires for
    # fresh profiles whose calibrated grade is ``slip`` and which
    # carry no ``slot`` value yet.
    if knob == "slip" and fresh_profile_without_slot:
        lines.extend([
            "",
            "Note: this fresh profile has no `slip.slot` value, so it "
            "will resolve to 0.0",
            "(NOT the shipped fdm_standard floor of 0.10 mm). If you "
            "want the conservative",
            "narrow-slot floor, add `\"slot\": 0.10` under \"slip\" in "
            "print_profiles_user.json,",
            "or copy the value from print_profiles.json:fdm_standard.",
        ])
    elif knob in ("free", "press") and fresh_profile_with_slip_only:
        # ``fresh_profile_with_slip_only`` is a misnomer for this
        # branch — we re-use it as the generic "fresh profile, other
        # knobs uncalibrated" signal. Surfaces the same gap for
        # uncalibrated siblings.
        lines.extend([
            "",
            "Note: uncalibrated knobs in this profile will use "
            "`_fitgrade_from_dict`'s safety",
            "defaults (0.0 across the board), NOT the shipped "
            "fdm_standard values. Calibrate the",
            "remaining knobs by running this tool again, or copy "
            "specific fields from",
            "print_profiles.json:fdm_standard.",
        ])

    if next_knob:
        lines.extend([
            "",
            f"Next in sequence: {next_knob}. Print the corresponding "
            f"gauge and re-run.",
        ])
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Per-knob orchestration
# --------------------------------------------------------------------------

def _resolve_active_profile_name(
    args: argparse.Namespace,
) -> tuple[str, str]:
    """Return ``(name, source_label)`` for stdout messages."""
    if args.profile:
        return (args.profile, "--profile flag")
    env_value = os.getenv("PRINT_PROFILE")
    if env_value:
        return (env_value, "PRINT_PROFILE env var")
    return (get_default_profile_name(), "hardcoded default")


def _knob_was_uncalibrated(
    entry: dict, grade: str, field: str
) -> bool:
    """True if the (grade, field) leaf is absent in the pre-write entry."""
    grade_dict = entry.get(grade, {}) if isinstance(entry, dict) else {}
    return field not in grade_dict


def _entry_has_grade_field(entry: dict, grade: str, field: str) -> bool:
    """True if ``entry[grade][field]`` exists and is set."""
    grade_dict = entry.get(grade, {}) if isinstance(entry, dict) else {}
    return isinstance(grade_dict, dict) and field in grade_dict


def _run_one_knob(
    knob: str,
    args: argparse.Namespace,
    profile_name: str,
    profile_source: str,
    next_knob: str | None,
) -> int:
    """Run the T6 → T7 → T8 cycle for a single knob.

    Returns 0 on successful write, 0 also on user abort (default-N),
    non-zero on error. Re-reads the raw user file from disk per
    invocation so a concurrent edit between knobs is picked up rather
    than silently clobbered.
    """
    rt = _load_knob_runtime(knob)

    # 1. Diameter input.
    if args.diameter is not None:
        diameter = float(args.diameter)
        if not _value_in_valid(diameter, rt.valid):
            choices = ", ".join(f"{d:.2f}" for d in rt.valid)
            print(
                f"ERROR: --diameter {diameter:.2f} is not a valid "
                f"choice for the {knob} gauge. "
                f"Valid choices: {choices}",
                file=sys.stderr,
            )
            return 2
    else:
        diameter = _prompt_diameter(rt.valid, rt.gauge_fqn.rsplit(".", 1)[-1])

    # 2. Compute calibrated value.
    after_value = _compute_radial(diameter, rt.nominal)

    # 3. Read raw user file, locate target entry.
    raw = _read_user_profiles_raw(_USER_FILE)
    user_file_existed = _USER_FILE.exists()
    target_entry, was_legacy_flat = _resolve_target_entry(
        raw, profile_name
    )
    profile_existed = profile_name in raw

    # 4. Compute the after-entry on a deep-copy.
    pre_entry = _migrate_if_legacy_flat(target_entry)
    after_entry = _build_after_entry(
        pre_entry, rt.grade, rt.field, after_value
    )

    # 5. Determine the "before" value for the preview.
    before_value: float | None = None
    before_inherited_from: str | None = None
    if _entry_has_grade_field(pre_entry, rt.grade, rt.field):
        before_value = float(pre_entry[rt.grade][rt.field])
    elif profile_name == "fdm_standard":
        # Surface the shipped value if we have it cheaply.
        before_inherited_from = "print_profiles.json:fdm_standard"
    # else: fresh profile, no inherited value — preview shows "unset".

    # 6. Render and confirm.
    nominal_source = {
        "free": "vibe_cading/mechanical/screws/metric.py:23",
        "press": "vibe_cading/mechanical/nuts/metric.py:28",
        "slip": "vibe_cading/lego/constants.py:91",
    }[knob]

    # First-write profile-name confirmation (FR20 / §4 step 3).
    # Skipped when: (a) --yes AND --profile explicit; OR (b) --yes AND
    # the resolved name is in the shipped fallback set.
    if (
        not profile_existed
        and profile_name not in _SHIPPED_PROFILE_NAMES
        and not args.yes
        and not args.profile
    ):
        confirmed_name = _prompt_profile_name_confirmation(profile_name)
        if confirmed_name != profile_name:
            profile_name = confirmed_name
            # Re-resolve the target entry against the corrected name.
            target_entry, was_legacy_flat = _resolve_target_entry(
                raw, profile_name
            )
            profile_existed = profile_name in raw
            pre_entry = _migrate_if_legacy_flat(target_entry)
            after_entry = _build_after_entry(
                pre_entry, rt.grade, rt.field, after_value
            )

    preview = _render_preview(
        user_file=_USER_FILE,
        user_file_exists=user_file_existed,
        profile_name=profile_name,
        profile_existed=profile_existed,
        profile_source=profile_source,
        grade=rt.grade,
        field=rt.field,
        before_value=before_value,
        before_inherited_from=before_inherited_from,
        after_value=after_value,
        diameter=diameter,
        nominal=rt.nominal,
        nominal_source=nominal_source,
        was_legacy_flat=was_legacy_flat,
        knob=knob,
    )
    print(preview)

    if args.yes:
        confirmed = True
    else:
        confirmed = _prompt_confirm()
    if not confirmed:
        print("Aborted; no changes written.")
        return 0

    # 7. Atomic write.
    new_raw = copy.deepcopy(raw)
    new_raw[profile_name] = after_entry
    _atomic_write_json(_USER_FILE, new_raw, knob)

    # 8. Success block.
    fresh_profile = not profile_existed
    fresh_without_slot = (
        knob == "slip"
        and fresh_profile
        and "slot" not in after_entry.get("slip", {})
    )
    # Surface the "uncalibrated knobs use 0.0 defaults" gap for fresh
    # profiles that just calibrated free or press.
    fresh_other_uncalibrated = fresh_profile and knob in ("free", "press")

    success = _render_success(
        profile_name=profile_name,
        grade=rt.grade,
        field=rt.field,
        after_value=after_value,
        knob=knob,
        fresh_profile_with_slip_only=fresh_other_uncalibrated,
        fresh_profile_without_slot=fresh_without_slot,
        next_knob=next_knob,
    )
    print(success)
    return 0


# --------------------------------------------------------------------------
# CLI layer (T9 + T10)
# --------------------------------------------------------------------------

_DESCRIPTION = """\
Walk through calibrating the most-consumed print-tolerance knobs
against printable mechanical gauges and write the calibrated values
into print_profiles_user.json.

Knobs and their default gauges:
  free.radial   → MThreeClearanceGauge (M3 clearance hole, nominal 3.2 mm)
                  consumers: MetricMachineScrew.to_cutter, every
                  vibe_cading/mechanical/holes.py class, Standoff/Hinge,
                  FreespinHexHub.bearing_seat_diameter
  press.radial  → MThreeNutPocketGauge (M3 nut WAF, nominal 5.5 mm)
                  consumers: Bearing.outer_pocket,
                  MetricHexNut.to_cutter(fit='press')
  slip.radial   → AxleHoleGauge (Lego axle, nominal 4.80 mm) — opt-in
                  consumers: TechnicAxleHole, Magnet.to_cutter,
                  Bearing.shaft_cutter

Prerequisite: print the relevant gauge first. Generate a preview SVG
with:
  python3 tools/preview.py \\
      vibe_cading.mechanical.calibration.m3_clearance_gauge.MThreeClearanceGauge \\
      --views iso_ne
(swap the class for MThreeNutPocketGauge / AxleHoleGauge as needed).

Writes the calibrated values into print_profiles_user.json under the
active profile name (resolved via --profile, PRINT_PROFILE, or
the hardcoded 'fdm_standard' default). Each calibrated value is
field-level deep-merged onto the shipped defaults at get_profile()
time — your override file stays a diff from shipped, never a full
snapshot.

Atomicity: each knob's confirmation triggers an independent atomic
write (tempfile → fsync → os.replace). A multi-knob 'all' run is a
sequence of per-knob atomic writes; Ctrl-C between knobs leaves
earlier writes persisted.

Normalisation: print_profiles_user.json is re-serialised on every
write via json.dumps(..., indent=2, sort_keys=True), so any
handwritten indentation or key ordering will be normalised on first
calibration. JSON-semantic content of untouched profiles is
preserved.

Examples:
  python3 tools/calibrate.py
  python3 tools/calibrate.py free --diameter 3.30 --yes \\
      --profile bambu_p1s__pla_overture
  python3 tools/calibrate.py press
  python3 tools/calibrate.py slip
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tools/calibrate.py",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "knob",
        nargs="?",
        default="all",
        choices=("all", "free", "press", "slip"),
        help="Knob to calibrate. Default 'all' runs free then press in "
             "sequence (slip is opt-in and only runs when named).",
    )
    parser.add_argument(
        "--diameter",
        type=float,
        default=None,
        help="Best-fitting gauge variant in mm. If omitted, the tool "
             "prompts interactively.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Override the active profile name (else uses "
             "PRINT_PROFILE env var or 'fdm_standard').",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the y/N confirmation. For fresh non-shipped profile "
             "names, also requires --profile (so an env-var typo "
             "cannot silently create a stray entry).",
    )
    parser.add_argument(
        "--gauge",
        type=str,
        default=None,
        help="(v2 placeholder) Select an opt-in alternate gauge for a "
             "knob. v1 has only one valid value per knob, defaulting "
             "to it — this flag exists to keep the CLI surface stable "
             "for v2 additions (e.g. bearing-pocket for press).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.gauge is not None:
        # v1: only the per-knob default gauge is valid. Accept the
        # flag for forward-compat surface stability, but reject any
        # value the v1 helper cannot route.
        print(
            f"WARNING: --gauge {args.gauge!r} is a v2 placeholder; "
            f"v1 routes every knob to its single default gauge "
            f"(MThreeClearanceGauge for free, MThreeNutPocketGauge "
            f"for press, AxleHoleGauge for slip).",
            file=sys.stderr,
        )

    profile_name, profile_source = _resolve_active_profile_name(args)

    # FR17 — print resolved profile name BEFORE any prompt or write.
    print(
        f"Profile: {profile_name}  "
        f"(resolved from {profile_source})"
    )
    print(f"File:    {_USER_FILE}")
    print()

    if args.knob == "all":
        knobs = ["free", "press"]
    else:
        knobs = [args.knob]

    # Snapshot fresh-profile state BEFORE the session loop runs so a
    # mid-session write (which creates the entry on disk) doesn't mask
    # the fact that the profile was freshly created by THIS session.
    # Used by the end-of-session slot-gap surfacing below.
    pre_session_raw = _read_user_profiles_raw(_USER_FILE)
    profile_was_fresh_at_session_start = (
        profile_name not in pre_session_raw
    )

    # FR20 hard guard — non-interactive (`--yes`) creation of a fresh
    # non-shipped profile MUST be explicitly confirmed via `--profile`.
    # Without this, an env-var typo
    # (e.g. ``PRINT_PROFILE=bumbu_p1s__pla`` instead of
    # ``bambu_p1s__pla``) would silently materialise a stray entry on
    # the next ``--yes`` run. The interactive path (no ``--yes``)
    # already prompts for confirmation inside ``_run_one_knob``; this
    # guard closes the matching ``--yes`` hole that the ``--yes`` flag's
    # own help text already advertises. Fires ONCE at the top of
    # ``main()`` so it short-circuits before any per-knob prompting.
    if (
        args.yes
        and not args.profile
        and profile_was_fresh_at_session_start
        and profile_name not in _SHIPPED_PROFILE_NAMES
    ):
        print(
            f"ERROR: --yes was passed but the resolved profile "
            f"'{profile_name}' does not yet exist in "
            f"print_profiles_user.json and is not a shipped fallback.\n"
            f"To create a new profile entry non-interactively, also "
            f"pass:\n"
            f"    --profile {profile_name}\n"
            f"This guard prevents silent stray entries from an env-var "
            f"typo.\n"
            f"(Resolved from: {profile_source}.)",
            file=sys.stderr,
        )
        return 2

    for i, knob in enumerate(knobs):
        next_knob = knobs[i + 1] if i + 1 < len(knobs) else None
        rc = _run_one_knob(
            knob, args, profile_name, profile_source, next_knob
        )
        if rc != 0:
            return rc

    # End-of-session Stage-2b surface for the slot-gap. Fires when:
    #   1. ``slip`` was NOT part of the session's knob sequence
    #      (i.e. ``all`` or single-knob ``free``/``press``), AND
    #   2. The profile name was freshly created by this session, AND
    #   3. The post-write entry has no ``slip.slot`` value.
    # Surfaces the same Stage-2b contract as the per-knob slip warning
    # so a contributor running ``calibrate.py all`` against a fresh
    # ``<machine>__<material>__<brand>`` profile is told that
    # ``slip.slot`` will resolve to 0.0 (NOT the shipped fdm_standard
    # floor of 0.10). See design Open Concern OC2 (2026-05-25).
    if (
        "slip" not in knobs
        and profile_was_fresh_at_session_start
    ):
        post_session_raw = _read_user_profiles_raw(_USER_FILE)
        post_entry = post_session_raw.get(profile_name, {})
        post_slip = (
            post_entry.get("slip", {})
            if isinstance(post_entry, dict)
            else {}
        )
        if (
            isinstance(post_slip, dict)
            and "slot" not in post_slip
        ):
            print(
                "Note: this session created a fresh profile without "
                "calibrating `slip`, so"
            )
            print(
                "`slip.slot` will resolve to 0.0 (NOT the shipped "
                "fdm_standard floor of 0.10 mm)."
            )
            print(
                "If you want the conservative narrow-slot floor for "
                "downstream TechnicAxleHole"
            )
            print(
                "consumers, run `python3 tools/calibrate.py slip "
                "--gauge axle`, or add"
            )
            print(
                "`\"slot\": 0.10` under \"slip\" in "
                "print_profiles_user.json (copy the value from"
            )
            print("print_profiles.json:fdm_standard).")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
