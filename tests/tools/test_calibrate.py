"""Tests for ``tools/calibrate.py``.

Covers the design's 28-row Tests table for the helper itself (test
rows 1–21 and 26; gauge geometry rows 22–23 in
``tests/mechanical/test_calibration_gauges.py``; refactor rows 24–25
in ``tests/test_metric_nut.py``; license/third-party rows 27–28 are
covered by ``tools/check_license_headers.py`` and the
no-third-party-imports check at the bottom of this file).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CALIBRATE_SCRIPT = _REPO_ROOT / "tools" / "calibrate.py"


def _load_calibrate(monkeypatch):
    """Load ``tools/calibrate.py`` fresh, pointing at a tempfile.

    ``monkeypatch`` is a pytest fixture used to swap the module-level
    ``_USER_FILE`` constant for a per-test tempfile path AFTER load.
    """
    spec = importlib.util.spec_from_file_location(
        "_calibrate_under_test", str(_CALIBRATE_SCRIPT)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def calibrate(tmp_path, monkeypatch):
    """Return the freshly-loaded ``calibrate`` module bound to a tempfile.

    The module's ``_USER_FILE`` constant is monkey-patched to point at
    ``<tmp_path>/print_profiles_user.json`` so tests cannot collide
    with the real user file in the repo root.
    """
    mod = _load_calibrate(monkeypatch)
    user_file = tmp_path / "print_profiles_user.json"
    monkeypatch.setattr(mod, "_USER_FILE", user_file)
    return mod


# ── T1 — --help completes without importing CadQuery ─────────────────────────
def test_help_no_cadquery_import():
    """Test row 1: ``--help`` must not trigger CadQuery import cascade.

    Runs the CLI as a subprocess with ``-X importtime`` and asserts
    that no line in stderr names ``cadquery``.
    """
    result = subprocess.run(
        [sys.executable, "-X", "importtime", str(_CALIBRATE_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--help exited non-zero: stdout={result.stdout}, "
        f"stderr={result.stderr}"
    )
    # importtime trace goes to stderr; help text to stdout.
    cadquery_lines = [
        line for line in result.stderr.splitlines()
        if "cadquery" in line.lower()
    ]
    assert cadquery_lines == [], (
        "--help triggered CadQuery import:\n"
        + "\n".join(cadquery_lines[:5])
    )


# ── T2 — --help lists every calibratable knob with gauges + consumers ────────
def test_help_lists_knobs():
    """Test row 2: help text mentions all v1 knobs, gauges, and a hint."""
    result = subprocess.run(
        [sys.executable, str(_CALIBRATE_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0
    for token in (
        "free.radial", "press.radial", "slip.radial",
        "MThreeClearanceGauge", "MThreeNutPocketGauge", "AxleHoleGauge",
        "print_profiles_user.json",
    ):
        assert token in result.stdout, (
            f"--help missing token '{token}'"
        )


# ── T3 — Creates user file with single calibrated leaf ───────────────────────
def test_creates_user_file(calibrate):
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "testprofile",
    ])
    assert rc == 0
    assert calibrate._USER_FILE.exists()
    with open(calibrate._USER_FILE, "r") as f:
        data = json.load(f)
    # (3.30 - 3.20) / 2 = 0.05
    assert data == {"testprofile": {"free": {"radial": 0.05}}}


# ── T4 — Calibration formula correctness ─────────────────────────────────────
def test_formula(calibrate):
    assert calibrate._compute_radial(3.30, 3.20) == pytest.approx(0.05)
    assert calibrate._compute_radial(3.50, 3.20) == pytest.approx(0.15)
    assert calibrate._compute_radial(3.10, 3.20) == pytest.approx(-0.05)


# ── T5 — Nominal reads live from source-of-truth constants ───────────────────
def test_nominal_live_source(calibrate):
    """Helper resolves nominals live from the metric.py / nuts.py / lego.

    Asserts that ``_load_knob_runtime('free')`` returns the live
    ``METRIC_SIZES["M3"]["clearance"]`` value rather than a stale
    hardcoded one. Live-source-of-truth is FR11.
    """
    from vibe_cading.mechanical.screws.metric import METRIC_SIZES
    from vibe_cading.mechanical.nuts.metric import MetricHexNut
    from vibe_cading.lego.constants import AXLE_HOLE_TIP_TO_TIP

    free_rt = calibrate._load_knob_runtime("free")
    press_rt = calibrate._load_knob_runtime("press")
    slip_rt = calibrate._load_knob_runtime("slip")

    assert free_rt.nominal == pytest.approx(
        float(METRIC_SIZES["M3"]["clearance"])
    )
    assert press_rt.nominal == pytest.approx(
        float(MetricHexNut.DIMENSIONS["M3"]["width_flats"])
    )
    assert slip_rt.nominal == pytest.approx(float(AXLE_HOLE_TIP_TO_TIP))


# ── T6 — Field-level merge preserves siblings ────────────────────────────────
def test_field_level_merge_preserves_siblings(calibrate):
    # Pre-existing user file.
    pre = {
        "fdm_standard": {
            "slip": {"radial": 0.10},
            "press": {"axial": 0.15},
        }
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    rc = calibrate.main([
        "free", "--diameter", "3.50", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0

    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    # (3.50 - 3.20) / 2 = 0.15
    assert post == {
        "fdm_standard": {
            "slip": {"radial": 0.10},
            "press": {"axial": 0.15},
            "free": {"radial": 0.15},
        }
    }


# ── T7 — Other profile entries byte-identical (JSON-semantic) ────────────────
def test_other_profiles_untouched(calibrate):
    pre = {
        "fdm_standard": {"slip": {"radial": 0.10}},
        "bambu_p1s__pla": {"free": {"radial": 0.18}},
        "ender3__petg": {"press": {"radial": 0.05}},
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    def _hash_entries(file_path, names):
        with open(file_path, "r") as f:
            data = json.load(f)
        out = {}
        for n in names:
            out[n] = hashlib.sha256(
                json.dumps(data.get(n, {}), sort_keys=True).encode()
            ).hexdigest()
        return out

    pre_hashes = _hash_entries(
        calibrate._USER_FILE, ["bambu_p1s__pla", "ender3__petg"]
    )

    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0

    post_hashes = _hash_entries(
        calibrate._USER_FILE, ["bambu_p1s__pla", "ender3__petg"]
    )
    assert pre_hashes == post_hashes


# ── T8 — Legacy-flat → nested migration on write ─────────────────────────────
def test_legacy_flat_migrate_on_write(calibrate):
    pre = {
        "fdm_standard": {
            "z_clearance": 0.20,
            "free_fit": 0.15,
            "slip_fit": 0.05,
            "press_fit": 0.04,
        }
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    rc = calibrate.main([
        "free", "--diameter", "3.50", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0

    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    # z_clearance → axial on every grade; calibrated free.radial wins.
    entry = post["fdm_standard"]
    assert entry["free"]["radial"] == pytest.approx(0.15)
    assert entry["free"]["axial"] == pytest.approx(0.20)
    assert entry["slip"]["axial"] == pytest.approx(0.20)
    assert entry["press"]["axial"] == pytest.approx(0.20)
    for legacy_key in (
        "z_clearance", "free_fit", "slip_fit", "press_fit"
    ):
        assert legacy_key not in entry, (
            f"legacy key {legacy_key!r} survived migration"
        )


# ── T9 — Legacy-flat migration scoped to target only ─────────────────────────
def test_legacy_flat_migrate_scoped_to_target(calibrate):
    pre = {
        "fdm_standard": {
            "z_clearance": 0.20,
            "free_fit": 0.15,
            "slip_fit": 0.05,
            "press_fit": 0.04,
        },
        "bambu_p1s__pla": {"free": {"radial": 0.18}},
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    pre_hash = hashlib.sha256(
        json.dumps(
            pre["bambu_p1s__pla"], sort_keys=True
        ).encode()
    ).hexdigest()

    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0

    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    post_hash = hashlib.sha256(
        json.dumps(
            post["bambu_p1s__pla"], sort_keys=True
        ).encode()
    ).hexdigest()
    assert pre_hash == post_hash


# ── T10 — Atomic write: crash injection between tempfile and os.replace ──────
def test_atomic_write_crash_injection(calibrate, monkeypatch):
    pre = {"fdm_standard": {"free": {"radial": 0.10}}}
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)
    pre_mtime = calibrate._USER_FILE.stat().st_mtime
    pre_content = calibrate._USER_FILE.read_text()

    def fake_replace(src, dst):
        raise OSError("simulated crash between tempfile and replace")

    monkeypatch.setattr(os, "replace", fake_replace)

    with pytest.raises(OSError, match="simulated crash"):
        calibrate._atomic_write_json(
            calibrate._USER_FILE,
            {"fdm_standard": {"free": {"radial": 0.99}}},
            "free",
        )

    # Original file untouched.
    assert calibrate._USER_FILE.read_text() == pre_content
    # Confirm mtime (may be same — content-equality is the stronger
    # guarantee). No tempfile leak.
    leaked = list(calibrate._USER_FILE.parent.glob(
        f"{calibrate._USER_FILE.name}.tmp.*"
    ))
    assert leaked == [], f"tempfile leak: {leaked!r}"
    _ = pre_mtime  # silence unused-var lint


# ── T11 — y/N default-N exits without write ──────────────────────────────────
def test_default_no_aborts(calibrate, monkeypatch, capsys):
    # No pre-existing file.
    inputs = iter([""])  # default-enter == N
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

    rc = calibrate.main([
        "free", "--diameter", "3.30", "--profile", "fdm_standard",
    ])
    assert rc == 0
    assert not calibrate._USER_FILE.exists()


# ── T12 — Per-knob atomic in sequence mode (interrupt after first write) ─────
def test_per_knob_atomic_in_sequence(calibrate, monkeypatch):
    """First knob is fully persisted before the second knob starts.

    Simulate KeyboardInterrupt during the second knob's prompt; assert
    the first knob's leaf is on disk.
    """
    # Use --yes for the first knob; interrupt the second knob's
    # --diameter prompt.
    # The all-mode loop calls _prompt_diameter for press because we
    # only supply --diameter for one knob via CLI. Approach: monkeypatch
    # _prompt_diameter to return 3.30 for free, raise KeyboardInterrupt
    # for press.
    call_count = {"n": 0}

    def fake_prompt_diameter(valid, gauge_name):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return 3.30  # free.radial = 0.05
        raise KeyboardInterrupt

    monkeypatch.setattr(
        calibrate, "_prompt_diameter", fake_prompt_diameter
    )

    with pytest.raises(KeyboardInterrupt):
        calibrate.main([
            "all", "--yes", "--profile", "fdm_standard",
        ])

    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    assert post["fdm_standard"]["free"]["radial"] == pytest.approx(0.05)
    assert "press" not in post["fdm_standard"]


# ── T13 — Per-knob independence (press without free) ─────────────────────────
def test_per_knob_independent(calibrate):
    rc = calibrate.main([
        "press", "--diameter", "5.60", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0
    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    # (5.60 - 5.50) / 2 = 0.05
    assert post == {"fdm_standard": {"press": {"radial": 0.05}}}


# ── T14 — Cross-model propagation through get_profile ────────────────────────
def test_propagation_to_get_profile(calibrate, monkeypatch):
    """Calibrating writes to a file get_profile reads back.

    Monkey-patches print_settings to use the per-test user file
    instead of the real repo-root file.
    """
    rc = calibrate.main([
        "free", "--diameter", "3.50", "--yes",
        "--profile", "testpropagation",
    ])
    assert rc == 0

    # Redirect print_settings to the same tempfile.
    from vibe_cading import print_settings as ps
    monkeypatch.setattr(
        ps, "_resolve_user_file", lambda: calibrate._USER_FILE
    )
    # Bust the module-level cache for emitted warnings so a re-resolve
    # doesn't get confused by prior test runs.
    ps._emitted_warnings.discard("unknown_profile_testpropagation")

    prof = ps.get_profile("testpropagation")
    assert prof.free.radial == pytest.approx(0.15)


# ── T15 — Profile-name confirmation prompt (interactive) ─────────────────────
def test_profile_name_confirmation(calibrate, monkeypatch):
    """Fresh non-shipped profile name triggers a confirm prompt.

    Default-Enter accepts the resolved name verbatim. The user may
    re-type to fix a typo.
    """
    # First scenario: default-Enter accepts the typo.
    inputs = iter(["", "y"])  # accept name as-is, then confirm write
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    rc = calibrate.main([
        "free", "--diameter", "3.30",
        "--profile", None or "bambo_p1s__pla",
    ])
    # NOTE: --profile is set so the confirmation prompt does NOT fire
    # for this case per the §4 step 3 contract. To force the prompt,
    # we drop --profile.
    assert rc == 0

    # Second scenario: omit --profile entirely; confirm prompt fires.
    # Reset the user file.
    calibrate._USER_FILE.unlink(missing_ok=True)
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "bambo_p1s__pla")
    inputs2 = iter(["bambu_p1s__pla", "y"])  # corrects the typo
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs2))
    rc = calibrate.main(["free", "--diameter", "3.30"])
    assert rc == 0
    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    assert "bambu_p1s__pla" in post
    assert "bambo_p1s__pla" not in post


# ── T16 — Profile-name confirmation skipped on --yes + --profile ─────────────
def test_profile_name_confirm_skipped_on_yes(calibrate, monkeypatch):
    """No prompt when --yes and --profile are both set."""
    # Sentinel: input() should NEVER be called.
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("input() should not be called")
        ),
    )
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "neverseenbefore_profile",
    ])
    assert rc == 0
    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    assert "neverseenbefore_profile" in post


# ── T17 — --diameter validates against gauge sweep ───────────────────────────
def test_diameter_validates_against_sweep(calibrate, capsys):
    rc = calibrate.main([
        "free", "--diameter", "9.99", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc != 0
    captured = capsys.readouterr()
    # Error names valid choices.
    assert "Valid choices:" in captured.err
    assert "3.20" in captured.err  # nominal must appear


# ── T18 — Active-profile resolution via VIBE_PRINT_PROFILE ───────────────────
def test_active_profile_resolution(calibrate, monkeypatch, capsys):
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "myprinter__pla")
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    # Seed the profile so the env-resolved name is NOT fresh; otherwise
    # the FR20 --yes-without-explicit-confirm guard would (correctly)
    # block this run. The intent of this test is to verify env-var
    # resolution, not the fresh-profile guard.
    with open(calibrate._USER_FILE, "w") as f:
        json.dump({"myprinter__pla": {}}, f)
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        # NO --profile — should resolve from env.
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Profile: myprinter__pla" in captured.out


# ── T19 — --profile flag overrides env ───────────────────────────────────────
def test_profile_flag_overrides_env(calibrate, monkeypatch, capsys):
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "from_env")
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "from_flag",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Profile: from_flag" in captured.out
    assert "from_env" not in captured.out.split("Profile:")[1].split("\n")[0]


# ── T20 — Resolved profile name printed BEFORE any prompt or write ───────────
def test_profile_printed_before_prompts(calibrate, capsys):
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # Find positions; "Profile:" must come before "Calibration target".
    profile_idx = out.index("Profile:")
    target_idx = out.index("Calibration target")
    assert profile_idx < target_idx


# ── T21 — Corrupt user JSON file → abort with clear error ────────────────────
def test_corrupt_user_file_aborts(calibrate, capsys):
    calibrate._USER_FILE.write_text("{not valid json")
    pre_content = calibrate._USER_FILE.read_text()
    with pytest.raises(SystemExit) as exc:
        calibrate.main([
            "free", "--diameter", "3.30", "--yes",
            "--profile", "fdm_standard",
        ])
    assert exc.value.code != 0
    # File untouched.
    assert calibrate._USER_FILE.read_text() == pre_content


# ── T26 — Success block names at least 3 downstream consumers ────────────────
def test_success_block_lists_consumers(calibrate, capsys):
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "fdm_standard",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # Crude: there must be at least 3 "  - " bullet lines in the
    # success block (one per named consumer).
    success_section = out.split("WROTE")[-1]
    bullets = [
        ln for ln in success_section.splitlines() if ln.startswith("  - ")
    ]
    assert len(bullets) >= 3


# ── OC1 (follow-up) — slip-mode success block emits slip.slot→0.0 warning ────
def test_slip_fresh_profile_emits_slot_warning(calibrate, capsys):
    """Phase-C Domain-Expert OC1: load-bearing Stage-2b surface-not-seed.

    Calibrating ``slip`` against a freshly-created profile must surface
    the ``slip.slot → 0.0`` gap in the success block (the resolved
    value is NOT the shipped ``fdm_standard.slip.slot = 0.10`` floor —
    field-level merge inherits from the matched parent key only).
    A future refactor of ``_render_success`` that silently drops this
    note would otherwise go unnoticed (T26 only counts bullet lines).
    """
    rc = calibrate.main([
        "slip", "--diameter", "4.80", "--yes",
        "--profile", "freshly_created_slip_only",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # The post-write success block must mention slip.slot AND its
    # resolved 0.0 value, AND why the field-level merge does NOT
    # inherit the 0.10 floor from fdm_standard.
    success_section = out.split("WROTE")[-1]
    assert "slip.slot" in success_section, (
        "success block missing literal 'slip.slot' reference"
    )
    assert "0.0" in success_section, (
        "success block missing '0.0' resolved value"
    )
    assert "fdm_standard" in success_section, (
        "success block missing reference to the unmerged fdm_standard floor"
    )


def test_slip_existing_profile_does_not_emit_slot_warning(
    calibrate, capsys
):
    """Negative half of OC1: the slot-gap warning must NOT fire when
    calibrating ``slip`` against an existing profile that already
    carries a ``slip.slot`` value.
    """
    pre = {
        "preexisting_profile": {
            "slip": {"radial": 0.05, "slot": 0.10},
        }
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    rc = calibrate.main([
        "slip", "--diameter", "4.80", "--yes",
        "--profile", "preexisting_profile",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    success_section = out.split("WROTE")[-1]
    # The literal `slip.slot` token must not appear in the success
    # block when the profile is not fresh — confirms the warning is
    # gated on fresh-profile-creation, not unconditional.
    assert "slip.slot" not in success_section, (
        "slot-gap warning fired on an existing-profile slip calibration"
    )


# ── OC2 (follow-up) — all-mode + fresh profile emits slot-gap warning ────────
def test_all_mode_fresh_profile_emits_slot_warning(
    calibrate, monkeypatch, capsys
):
    """Phase-C Domain-Expert OC2: ``calibrate.py all`` runs free+press
    only. Against a fresh ``<machine>__<material>__<brand>`` profile,
    the resulting entry carries no ``slip.slot`` — every downstream
    ``TechnicAxleHole`` consumer on that profile would silently
    resolve ``slot=0.0`` (not the shipped 0.10 floor). The end-of-
    session surfacing must call this out.

    Drives the two-knob loop via the interactive prompt so each knob
    receives a sweep-valid diameter from its OWN gauge tuple (the
    ``--diameter`` flag applies to every knob, but each knob's nominal
    differs — 3.20 mm for free, 5.50 mm for press).
    """
    diameters = iter([3.30, 5.60])  # free gauge value, press gauge value

    def fake_prompt_diameter(valid, gauge_name):
        return next(diameters)

    monkeypatch.setattr(
        calibrate, "_prompt_diameter", fake_prompt_diameter
    )

    rc = calibrate.main([
        "all", "--yes",
        "--profile", "fresh_all_mode_profile",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # The end-of-session block must surface slip.slot=0.0 and name
    # fdm_standard as the unmerged floor. It is NOT inside any single
    # knob's `WROTE ...` success block — it's printed after the loop.
    assert "slip.slot" in out, (
        "end-of-session slot-gap warning missing 'slip.slot' literal"
    )
    assert "0.0" in out, (
        "end-of-session slot-gap warning missing '0.0' resolved value"
    )
    assert "fdm_standard" in out, (
        "end-of-session slot-gap warning missing fdm_standard reference"
    )


def test_all_mode_existing_profile_does_not_emit_slot_warning(
    calibrate, monkeypatch, capsys
):
    """Negative half of OC2: ``calibrate.py all`` against an EXISTING
    profile must NOT emit the end-of-session slot-gap warning,
    regardless of whether that profile carries a ``slip.slot``. The
    surfacing is gated on fresh-profile-creation by this session, so a
    contributor re-running ``all`` against their dialled-in profile
    sees no unsolicited noise.
    """
    pre = {
        "preexisting_all_profile": {
            "free": {"radial": 0.10},
            "press": {"radial": 0.04},
            # Deliberately no `slip` entry — even so, the warning must
            # NOT fire because the profile was not freshly created by
            # this session.
        }
    }
    with open(calibrate._USER_FILE, "w") as f:
        json.dump(pre, f)

    diameters = iter([3.30, 5.60])

    def fake_prompt_diameter(valid, gauge_name):
        return next(diameters)

    monkeypatch.setattr(
        calibrate, "_prompt_diameter", fake_prompt_diameter
    )

    rc = calibrate.main([
        "all", "--yes",
        "--profile", "preexisting_all_profile",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # Strip every per-knob `WROTE` success block (those may carry the
    # generic "uncalibrated knobs" note) and inspect what's left for
    # the end-of-session emission.
    # The end-of-session block specifically opens with
    # "Note: this session created a fresh profile" — assert that
    # phrase is absent.
    assert "this session created a fresh profile" not in out, (
        "end-of-session slot-gap warning fired against an EXISTING profile"
    )


# ── FR20-tighten — --yes without --profile on a fresh non-shipped name ──────
def test_yes_fresh_env_profile_blocked_without_explicit_profile(
    calibrate, monkeypatch, capsys
):
    """An env-var typo cannot silently create a stray profile entry.

    Scenario: ``VIBE_PRINT_PROFILE=bumbu_p1s__test_typo`` (note the
    "bumbu" typo for "bambu"), invoked with ``--yes`` and no
    ``--profile``. The resolved name is fresh (no user file yet) and
    not in ``_SHIPPED_PROFILE_NAMES``, so the FR20 guard MUST fire,
    name the typo'd profile in stderr, suggest the corrective
    ``--profile`` flag, and exit non-zero BEFORE any write.
    """
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "bumbu_p1s__test_typo")
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    # Sentinel: input() should NEVER be called (--yes bypasses prompts,
    # the guard fires before any per-knob prompting).
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("input() should not be called")
        ),
    )
    assert not calibrate._USER_FILE.exists()

    rc = calibrate.main(["free", "--diameter", "3.30", "--yes"])

    assert rc != 0, "guard must exit non-zero on fresh-env-profile + --yes"
    captured = capsys.readouterr()
    assert "ERROR:" in captured.err
    assert "bumbu_p1s__test_typo" in captured.err
    assert "--profile bumbu_p1s__test_typo" in captured.err
    # Guard fires before any write — user file must not have been
    # created (or, if pre-existing, must remain empty / unchanged).
    assert not calibrate._USER_FILE.exists(), (
        "guard fired but a stray user file was still created"
    )


def test_yes_with_explicit_profile_creates_fresh_entry(
    calibrate, monkeypatch
):
    """The guard does NOT over-trigger when --profile is explicit.

    Negative control for the FR20 tighten: same env-var typo would
    fire, but the user explicitly confirms creation via
    ``--profile <name>`` so the run proceeds normally.
    """
    monkeypatch.setenv("VIBE_PRINT_PROFILE", "bumbu_p1s__test_typo")
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("input() should not be called")
        ),
    )
    rc = calibrate.main([
        "free", "--diameter", "3.30", "--yes",
        "--profile", "bambu_p1s__pla_real",
    ])
    assert rc == 0
    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    assert "bambu_p1s__pla_real" in post


def test_yes_resolves_to_shipped_default_proceeds(
    calibrate, monkeypatch
):
    """Shipped fallback names are exempt from the FR20 tighten guard.

    No env var, no ``--profile`` → ``_resolve_active_profile_name``
    falls through to the hardcoded ``fdm_standard`` shipped default.
    Even though that name is fresh (no user file yet), it IS in
    ``_SHIPPED_PROFILE_NAMES`` so the guard exempts it.
    """
    monkeypatch.delenv("VIBE_PRINT_PROFILE", raising=False)
    monkeypatch.delenv("VIBE_MACHINE_PROFILE", raising=False)
    monkeypatch.setattr(
        "builtins.input",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("input() should not be called")
        ),
    )
    rc = calibrate.main(["free", "--diameter", "3.30", "--yes"])
    assert rc == 0
    with open(calibrate._USER_FILE, "r") as f:
        post = json.load(f)
    assert "fdm_standard" in post


# ── T28 — No third-party imports in helper or new gauges ─────────────────────
def test_no_third_party_imports():
    """Helper + new gauges must only import stdlib + vibe_cading + cadquery.

    Implemented as an AST-based positive allowlist (T28 design rationale
    in Independent-Developer-review O1: the regex form was POSIX-invalid).
    """
    import ast

    targets = [
        _REPO_ROOT / "tools" / "calibrate.py",
        _REPO_ROOT / "vibe_cading" / "mechanical" / "calibration"
        / "__init__.py",
        _REPO_ROOT / "vibe_cading" / "mechanical" / "calibration"
        / "m3_clearance_gauge.py",
        _REPO_ROOT / "vibe_cading" / "mechanical" / "calibration"
        / "m3_nut_pocket_gauge.py",
    ]
    allowed_stdlib = {
        "argparse", "copy", "errno", "glob", "json", "os", "sys",
        "tempfile", "pathlib", "warnings", "math", "typing", "__future__",
    }
    allowed_internal_prefixes = ("vibe_cading", "cadquery", "cq")

    for path in targets:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert (
                        top in allowed_stdlib
                        or top.startswith(allowed_internal_prefixes)
                    ), f"{path}: disallowed import {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top = node.module.split(".")[0]
                assert (
                    top in allowed_stdlib
                    or top.startswith(allowed_internal_prefixes)
                ), f"{path}: disallowed import from {node.module}"
