# Design: `tools/calibrate.py` — generic multi-knob print-tolerance calibration helper (Brief #2)
<!-- Filename: 2026-05-23-calibration-helper-generic_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-23-calibration-helper-generic_req.md`
- **Requester role**: @designer (PM-spawned 2026-05-23; human-confirmed 2026-05-24 with Q1–Q7 deferred to Step-3 co-design)
- **Date**: 2026-05-23
- **Dialog rounds**: 5

---

## Objective

Ship a single CLI entry point at `tools/calibrate.py` that walks a contributor through calibrating the **most-consumed** print-tolerance knobs (`free.radial` and `press.radial` default; `slip.radial` opt-in) against generic mechanical gauges (M3 clearance hole, M3 nut press-fit pocket, opt-in Lego axle hole), and writes the derived values into the user's `<machine>__<material>[__<brand>]` entry in `print_profiles_user.json` via per-knob field-level merged atomic writes — so every downstream `get_profile()` consumer inherits the calibrated values on the next call with zero source edits.

## Architecture / Approach

### Approach chosen

**One single-file CLI script at `tools/calibrate.py` + two net-new in-tree gauge classes under a new `vibe_cading/mechanical/calibration/` sub-package.** The helper is a thin orchestration layer over: (a) the merged Brief-#1 foundation (`get_default_profile_name`, `_is_legacy_flat_entry`, `_migrate_flat_to_nested`, `_deep_merge_profiles`); (b) three gauge classes — two net-new (`MThreeClearanceGauge`, `MThreeNutPocketGauge`) plus the existing `AxleHoleGauge`; (c) the live source-of-truth dimension constants from `screws.metric.METRIC_SIZES["M3"]`, `nuts.metric.MetricHexNut.DIMENSIONS["M3"]`, and `lego.constants.AXLE_HOLE_TIP_TO_TIP`.

**Subcommand layout (Q2 resolution — option c).** Single hybrid CLI with optional positional `[knob]` arg defaulting to `all`:

```
python3 tools/calibrate.py                  # sequence mode (free, press)
python3 tools/calibrate.py all              # explicit sequence (same as above)
python3 tools/calibrate.py free             # only free.radial
python3 tools/calibrate.py press            # only press.radial
python3 tools/calibrate.py slip             # only slip.radial (opt-in)
python3 tools/calibrate.py free --diameter 3.30 --yes --profile bambu_p1s__pla_overture
```

**Per-knob gauge resolution (Q1 + Q6 resolution).** Each knob has exactly one default gauge in v1; opt-in alternates are reachable via `--gauge <name>`:

| Knob          | Default gauge              | Sweeps    | Nominal source                                   | Opt-in alternates |
|---------------|----------------------------|-----------|--------------------------------------------------|-------------------|
| `free.radial` | `MThreeClearanceGauge`     | diameters | `METRIC_SIZES["M3"]["clearance"]` = 3.2 mm       | (none in v1)      |
| `press.radial`| `MThreeNutPocketGauge`     | widths    | `MetricHexNut.DIMENSIONS["M3"]["width_flats"]` = 5.5 mm | (none in v1) |
| `slip.radial` | `AxleHoleGauge` (opt-in)   | diameters | `AXLE_HOLE_TIP_TO_TIP` = 4.80 mm                 | (none in v1)      |

The `--gauge` flag exists in the v1 CLI surface as a no-op-with-help-text placeholder for v2 alternates (e.g. `bearing_pocket` for `press`), keeping the surface stable.

**Sequencing decision (Q7 resolution — option a, all-in-one PR).** The helper, the two net-new gauge classes (`MThreeClearanceGauge`, `MThreeNutPocketGauge`), the `MetricHexNut.to_cutter` Option-A refactor to support `fit="captive"|"press"` (~10-15 LOC in one file per §5 below), the README rewrite, and the per-gauge visual contract SVGs all land in one PR. Rationale: the refactor is small and concentrated in `nuts/metric.py`, the gauge classes are ~80 LOC each, and the helper is functionally inert without them — splitting buys reviewability less than it costs in cross-PR coordination on a tightly-coupled feature.

**Per-knob atomicity (Q4 resolution — per-knob).** Each knob's confirmation triggers its own atomic write (tempfile → fsync → `os.replace`). A multi-knob `all` run is a sequence of independent per-knob atomic writes — Ctrl-C between knobs leaves earlier writes persisted on disk.

**Gauge class location (architectural decision).** New sub-package `vibe_cading/mechanical/calibration/` containing `m3_clearance_gauge.py` and `m3_nut_pocket_gauge.py`. Justification under the dual-lens rule (deep-modules) — see `### Module depth` below.

### Visual contract (CAD tasks)

The CLI script itself is carve-out exempt (instruction / tooling task per `vibe/INSTRUCTIONS.md` *Visual Contract Deliverable*). Each net-new gauge class is a CAD model with visible geometry — each gets its own iso_ne SVG generated during Implementation Plan task T-Visual, co-located in this design's `.agents/plans/` directory:

- `.agents/plans/2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg`
- `.agents/plans/2026-05-23-calibration-helper-generic_design_m3_nut_pocket_iso_ne.svg`

Designer step-3 generates initial probe-SVGs from `tmp/visualise_<gauge>.py` probes; Developer step-5A regenerates from `tools/preview.py vibe_cading.mechanical.calibration.<module>.<Class> --views iso_ne` and overwrites the committed file. (No SVG for `AxleHoleGauge` — that gauge's visual contract was already delivered in `.agents/plans/2026-05-20-axle-hole-tip-to-tip-gauge_design_iso_ne.svg`.)

![MThreeClearanceGauge — iso_ne preview](2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg)

![MThreeNutPocketGauge — iso_ne preview](2026-05-23-calibration-helper-generic_design_m3_nut_pocket_iso_ne.svg)

### Alternatives rejected

- **(R1) Promote `_is_legacy_flat_entry` / `_migrate_flat_to_nested` to public API.** Rejected — same rationale as the SUPERSEDED brief's R1: still only two callers (Brief-#1 internal + this helper). Document the direct-import-of-underscored-helpers in the helper's module docstring as a sanctioned in-tree consumer. Re-evaluate on a *third* consumer.
- **(R2) Round-trip through `get_profile()` and re-serialise the resulting dataclass.** Rejected — same rationale as SUPERSEDED R2: re-serialising `ToleranceProfile` would inflate the user file with every inherited shipped default, defeating FR24's field-level merge contract.
- **(R3) Bearing outer-pocket as the `press` default gauge instead of M3 nut.** Rejected (Q6 option c) — the user-reframe explicitly named "M3 nut for press fit" as the right mental-model anchor. Bearing-pocket would be honest-to-current-schema but mismatched to contributor expectations. The 5-LOC `MetricHexNut.to_cutter` refactor (Q6 option a) is cheaper than ongoing user-model mismatch.
- **(R4) Calibrate the M3-nut gauge against `free.radial`.** Rejected (Q6 option b) — produces two redundant `free.radial` samples (M3-screw gauge + M3-nut gauge calibrate the same knob), wasting one of two precious "default gauge" slots and contradicting the "M3 nut for press fit" mental model.
- **(R5) Gauge classes as separate sub-briefs (Q7 option b).** Rejected — gauge implementations are ~80 LOC each with no architectural surface; splitting forces three PR cycles (gauge1, gauge2, helper) for one user-visible feature. The all-in-one PR fits in one review.
- **(R6) Full-session atomic write (Q4 alternative).** Rejected — surprises the "I miscued press; let me re-run only press" recovery case. Per-knob preserves the user's intuition that each confirmation is a commit.
- **(R7) Inherit-from `ToleranceGauge` base class.** Rejected — `ToleranceGauge` is a pre-Brief-#1 multi-row mega-gauge with hardcoded swept rows for M3+bearing+peg+pin in one block; it's a self-contained demo, not a base. The new gauges are single-anchor sweep gauges following the `AxleHoleGauge` shape (single dimension array, label band, atomic block). They duplicate ~30 LOC of layout boilerplate between the two; that's the cheapest correct answer for v1. A shared `_SweepGaugeBase` is a v2 refactor once a third single-anchor gauge materialises.
- **(R8) Flat-add the gauge classes to `vibe_cading/mechanical/` root.** Rejected — adding two more files to a directory that already has 10+ siblings buries them. The `calibration/` sub-package gives a contributor exploring "where do I add a new calibration gauge?" an obvious home.

### Module depth

Per the *structural-optimization* skill, applied dual-lens (current internal callers + OSS contributor extending). Three new modules:

| Module | Maintainer-locality (lens a) | Contributor-locality (lens b) | Verdict |
|---|---|---|---|
| `vibe_cading/mechanical/calibration/__init__.py` | Empty `__init__`; no current dispatch surface | Marks the sub-package boundary so a contributor adding a new gauge knows the canonical home | **KEEP** — false-positive carve-out: contributor-extension surface |
| `vibe_cading/mechanical/calibration/m3_clearance_gauge.py` (`MThreeClearanceGauge`) | One caller today (`tools/calibrate.py`); also usable independently via `tools/view.py` / `tools/preview.py` | Mirrors `AxleHoleGauge`'s single-anchor sweep gauge shape; an external contributor adding a new clearance-anchored gauge has two precedents to copy | **KEEP** — single-anchor sweep gauge is a distinct primitive |
| `vibe_cading/mechanical/calibration/m3_nut_pocket_gauge.py` (`MThreeNutPocketGauge`) | One caller today (`tools/calibrate.py`); also usable independently | Hexagonal-pocket variant of the round-hole sweep pattern; second exemplar of "press-fit pocket gauge" shape | **KEEP** — distinct geometry (hex pocket vs round hole); different consumer-knob |

**No shared `_SweepGaugeBase` introduced in v1** — see R7 rejection. The duplication is ~30 LOC of XY-layout / label-band boilerplate per gauge; consolidating now is speculative (only 2 exemplars). Re-evaluate when a third single-anchor sweep gauge materialises (likely v2 bearing-pocket gauge for the `press.radial` opt-in alternate).

`tools/calibrate.py` itself is a CLI script, not a module — the deletion test does not apply (CLI entry points are by definition not deletable into callers). The script does carry internal helper functions (`_render_preview`, `_atomic_write_json`, etc.); per the SUPERSEDED brief's precedent these stay module-private with leading underscores, not promoted to `print_settings.py` public API.

## Data & Interface Contracts

*Domain integrity gate: **YES**. This section is load-bearing — a wrong calibration formula or knob-to-gauge mis-routing silently mis-applies tolerances library-wide.*

### §1. Calibration formula per knob (forward + inverse)

Each gauge defines a **nominal** `N` (read live from the source-of-truth constant — never hardcoded) and a **swept-variant dimension** `D` (the gauge variant the user selects as best-fitting). The calibration writes a single `radial` value into the resolved profile's named grade:

| Knob | Gauge | Nominal `N` (live source) | Forward (calibrate)            | Inverse (target → gauge variant) |
|------|-------|---------------------------|--------------------------------|----------------------------------|
| `free.radial`  | `MThreeClearanceGauge` | `METRIC_SIZES["M3"]["clearance"]` = 3.2 mm  (in `vibe_cading/mechanical/screws/metric.py:23`) | `free.radial  = (D − N) / 2`  | `D = N + 2 · free.radial` |
| `press.radial` | `MThreeNutPocketGauge` | `MetricHexNut.DIMENSIONS["M3"]["width_flats"]` = 5.5 mm  (in `vibe_cading/mechanical/nuts/metric.py:28`) | `press.radial = (D − N) / 2` | `D = N + 2 · press.radial` |
| `slip.radial`  | `AxleHoleGauge`        | `AXLE_HOLE_TIP_TO_TIP` = 4.80 mm  (in `vibe_cading/lego/constants.py:91`)                       | `slip.radial  = (D − N) / 2`  | `D = N + 2 · slip.radial` |

**Sign convention.** `D > N` ⇒ positive `radial` (printer prints holes / pockets under-size relative to nominal — the FDM default). `D < N` ⇒ negative `radial`, allowed (over-extruding printers print over-size). `D == N` ⇒ `radial = 0` (perfect dimensional accuracy).

**The formula is uniform across all three knobs** — every gauge sweeps a single linear dimension (hole diameter for round; pocket width-across-flats for hex), and the user-selected `D` is twice the radial half-allowance plus the nominal. The hex-pocket case is geometrically identical because `width_flats` is a diameter-like dimension (across-the-flats face-to-face distance), and `MetricHexNut.to_cutter()` (post-refactor T-Refactor) inflates `width_flats` by `2 · press.radial` to size the pocket — symmetric to a round hole.

**Why `slip.radial = (D − N) / 2` for the round-hole axle gauge is correct** even though the axle's contact geometry is at the four cross-arm tips: see `AxleHoleGauge` docstring lines 30–37 — the axle's outer envelope is a circle of diameter `tip_to_tip = 4.80 mm` (the four tip arcs lie on that circle); the smallest round hole that accepts the axle measures the effective envelope directly. Formula is identical to the M3-clearance case.

**Helper reads `N` live from source.** The helper imports the constants directly:

```python
from vibe_cading.mechanical.screws.metric import METRIC_SIZES
from vibe_cading.mechanical.nuts.metric import MetricHexNut
from vibe_cading.lego.constants import AXLE_HOLE_TIP_TO_TIP

_NOMINAL_FREE_RADIAL  = float(METRIC_SIZES["M3"]["clearance"])           # 3.2
_NOMINAL_PRESS_RADIAL = float(MetricHexNut.DIMENSIONS["M3"]["width_flats"])  # 5.5
_NOMINAL_SLIP_RADIAL  = float(AXLE_HOLE_TIP_TO_TIP)                      # 4.80
```

A future bump to any of these constants propagates without a `calibrate.py` edit. Tests T-NominalLive assert these reads.

### §2. Cross-model propagation contract

A successful write of `free.radial = 0.18` under profile `bambu_p1s__pla_overture` propagates to **every** downstream consumer that calls `get_profile("bambu_p1s__pla_overture")` (or that resolves it via `VIBE_PRINT_PROFILE`) on the next call. Named verified consumers (from repo-wide grep, 2026-05-24, mirrored in req §"Knob-to-consumer mapping"):

- `free.radial` →
  - `vibe_cading/mechanical/holes.py` — every `ClearanceHole`, `CounterboreHole`, `CountersinkHole`, `TaperedHole`, `HexHole`, `Bore` (8 read sites).
  - `vibe_cading/mechanical/screws/metric.py` `MetricMachineScrew.to_cutter`.
  - `vibe_cading/mechanical/screws/setscrew.py` `SetScrew` bore.
  - `vibe_cading/mechanical/nuts/metric.py` `MetricHexNut.to_cutter` (captive pocket; still reads `free.radial` for captive flavour).
  - `vibe_cading/mechanical/nuts/tnut.py` `MetricTNut.to_cutter`.
  - `vibe_cading/mechanical/standoffs.py` `Standoff.to_cutter`.
  - `vibe_cading/mechanical/hinge.py` `Hinge.to_cutter` (×2 sites: `clearance`, `face_gap`).
  - `vibe_cading/rc/freespin_hex_hub.py` `FreespinHexHub.bearing_seat_diameter`.
- `press.radial` →
  - `vibe_cading/mechanical/bearings.py` `Bearing.outer_pocket` (line 81).
  - `vibe_cading/mechanical/nuts/metric.py` `MetricHexNut.to_cutter` **after T-Refactor** (new press-pocket variant — see §5).
- `slip.radial` →
  - `vibe_cading/lego/cutters/technic_axle_hole.py` `TechnicAxleHole`.
  - `vibe_cading/mechanical/magnets.py` `Magnet.to_cutter` (×2 sites).
  - `vibe_cading/mechanical/bearings.py` `Bearing.shaft_cutter`.

The helper's `--help` text and post-write success block name 3+ of these consumers per calibrated knob so a contributor sees what they just dialled in. Test T-Propagation asserts the calibrated leaf is observable via `get_profile(name).free.radial`.

### §3. Atomic-write semantics (Q4 resolution: per-knob)

Each knob's confirmation triggers a single atomic write cycle:

```
1. Read raw print_profiles_user.json   (or treat as {} if missing)
2. Deep-copy the dict
3. Locate / create the target profile entry under the resolved name
4. If entry is legacy-flat → run _migrate_flat_to_nested(entry) in-place on the copy
5. Set entry[<grade>][<field>] = calibrated value
   (creating the nested dict path if absent; preserves siblings at JSON-semantic
   equivalence — `json.loads(before) == json.loads(after)` for every unrelated
   profile and every untouched leaf of the target profile)
6. Render preview, prompt y/N
7. On y: serialise to <path>.tmp.<pid>.<knob> via `json.dumps(data, indent=2, sort_keys=True)`,
   fsync, os.replace → <path>
8. Print success block naming downstream consumers
```

**JSON-semantic equivalence, not byte-identity.** The file is re-serialised with a single canonical form (`json.dumps(..., indent=2, sort_keys=True)`), so any handwritten indentation, key ordering, or trailing-comma quirks in the user's `print_profiles_user.json` WILL be normalised on the first `calibrate.py` write. The invariant the helper guarantees is **JSON-semantic equivalence** of all untouched data: `json.loads(file_before) == json.loads(file_after)` is true for every profile other than the target, and for every leaf of the target other than the calibrated `<grade>.<field>`. This normalisation is documented in the helper's `--help` output (see T10) so the first-write reflow is not a surprise.

Steps 1–8 repeat per knob in a sequence run. Each cycle re-reads the user file from disk (step 1) so a concurrent edit between knobs is picked up rather than silently clobbered. Steps 7's tempfile name includes the knob so a parallel calibration session writing the same file fails fast on `os.replace` rather than racing into a half-written file.

**Justification for per-knob over full-session.** (a) Filesystem-safety pattern from SUPERSEDED design carries forward unchanged — one knob = one atomic transaction. (b) Recovery use-case dominance: the realistic failure is "I measured press wrong; rerun just press" — under per-knob, `free` is already on disk; under full-session it would be discarded. (c) Crash-injection test surface is simpler: T-Atomic asserts one cycle leaves a coherent file with the calibrated leaf set.

**Inter-knob commit boundary is explicit in the change preview** — each knob's preview is rendered, confirmed, written, and the success block printed before the next knob's preview is rendered. The user never sees two pending knobs at once.

### §4. Profile-creation flow (FR18/FR19/FR20 — fresh profile entry)

When the resolved target profile name does **not** exist in `print_profiles_user.json`:

1. **Top-level dict creation.** If `print_profiles_user.json` itself is missing, the helper creates it containing exactly one top-level key (the target profile name) with one nested grade dict carrying one leaf field.
2. **No inherited defaults are injected.** The new entry contains *only* the calibrated leaves of this run. The field-level merge contract (Brief #1 `_deep_merge_profiles`) fills uncalibrated siblings from the shipped `print_profiles.json` at read time — the user file stays a **diff from shipped**, never a full snapshot.

   *Concrete:* after `calibrate.py free` writes `free.radial = 0.18` under a fresh `bambu_p1s__pla_overture` entry, the file contains exactly:
   ```json
   {"bambu_p1s__pla_overture": {"free": {"radial": 0.18}}}
   ```
   On next `get_profile("bambu_p1s__pla_overture")`: `_deep_merge_profiles` merges this onto the shipped `fdm_standard` default? **No** — Brief #1's merge is keyed by profile name; an unknown user profile name does NOT inherit from `fdm_standard`. It inherits from the **shipped entry of the same name** if one exists, else `_fitgrade_from_dict` falls back to its per-field hardcoded defaults (`free.radial=0.15, free.axial=0.20, slot=0.0`).

   **Implication: a freshly-created user profile entry with only `free.radial` calibrated gets `free.axial`, `slip.*`, and `press.*` from `_fitgrade_from_dict`'s hardcoded per-field defaults — not from the shipped `fdm_standard` profile.** The hardcoded `_fitgrade_from_dict` defaults are: `radial=0.0`, `axial=0.0`, `slot=0.0`. These are the **safety fallbacks for missing keys**; they do NOT match the shipped `fdm_standard` values (which carry `slip.slot=0.10` per the Stage-2b conservative narrow-slot floor decision, and non-zero `radial`/`axial` per grade). A user profile that omits a field gets the safety default (0.0), NOT the shipped floor, unless field-level merge against a matched parent key supplies it — and unknown user profile names have no matched shipped parent.

   **Concrete Stage-2b implication for `slip.slot`.** When a user runs `tools/calibrate.py slip` against a fresh `<machine>__<material>` profile name not yet in `print_profiles_user.json`, the helper writes `{"<name>": {"slip": {"radial": <calibrated>}}}`. On next `get_profile()`, `_fitgrade_from_dict` resolves `slip.slot` to **0.0** — NOT to the shipped `fdm_standard.slip.slot=0.10`. This is a regression of the Stage-2b conservative-floor decision for any fresh user-named profile that calibrates `slip.radial` without also seeding `slip.slot`.

   **Helper response: surface, do not seed.** The helper does NOT auto-seed `slip.slot=0.10` into the fresh entry (seeding would defeat the "user file is a diff from shipped" invariant — the user could not later distinguish a deliberate 0.10 from a hidden inherited 0.10). Instead, the success block for a `slip`-knob fresh-profile write MUST surface the gap explicitly. When the just-written entry contains `slip.radial` but no `slip.slot`, the success block appends:
   ```
   Note: this fresh profile has no `slip.slot` value, so it will resolve to 0.0
   (NOT the shipped fdm_standard floor of 0.10 mm). If you want the conservative
   narrow-slot floor, add `"slot": 0.10` under "slip" in print_profiles_user.json,
   or copy the value from print_profiles.json:fdm_standard.
   ```
   Equivalent block for the `free`/`press` paths reads: *"Uncalibrated knobs in this profile will use `_fitgrade_from_dict`'s safety defaults (0.0 across the board), NOT the shipped fdm_standard values. Calibrate the remaining knobs by running this tool again, or copy specific fields from print_profiles.json:fdm_standard."*

3. **First-time profile-name confirmation prompt (FR20).** Before the first write to a profile name not previously in `print_profiles_user.json` AND not in the shipped fallback set (`fdm_standard`, `resin_precise`, `cnc`), the helper prompts once:
   ```
   The profile name 'bambo_p1s__pla_overture' does not yet exist in
   print_profiles_user.json and does not match any shipped fallback.
   It will be CREATED.  Recommended convention: <machine>__<material>[__<brand>].
   Confirm key name [bambo_p1s__pla_overture]: _
   ```
   Default-Enter accepts the resolved name verbatim. The user can re-type to fix a typo (caught a `bambo_p1s` vs `bambu_p1s` slip pre-write). Skipped on `--profile` (the flag IS the explicit confirmation) AND on `--yes` (CI/script paths bypass interactive prompts).

### §5. Q6 resolution — `MetricHexNut.to_cutter` `fit` kwarg (Option A: scoped refactor)

The current method (lines 57–69 of `vibe_cading/mechanical/nuts/metric.py`) reads `prof.free.radial` via `CaptiveNutPocket` indirection. `CaptiveNutPocket` (`vibe_cading/mechanical/holes.py:387-447`) has two read sites of `self.tolerance.free.radial` — `.solid` (line 426) AND `.to_cutter` (line 440) — and its constructor uses the param name `width_across_flats` (NOT `width_flats`).

**Option A chosen (over Option B "cascade the signature change").** Justification: Option A preserves `CaptiveNutPocket`'s public constructor signature byte-exactly, which means the wire contract in `engine_api.json:1787-1788` is untouched, the two existing direct callers (`tests/test_cutter_overcut.py:137`, `tests/test_protocols.py:101-102`) keep compiling unmodified, and the LOC surface is minimised. Option B's cascade would touch ~30–50 LOC across 4–5 files and require an `engine_api.json` regeneration as an Implementation Plan sub-task. Option A keeps the refactor localised to `MetricHexNut.to_cutter` and achieves the same user-visible outcome ("`fit='press'` reads `press.radial`") via a synthesised per-call `ToleranceProfile` rather than a `CaptiveNutPocket` signature change.

Post-refactor (Option A):

```python
def to_cutter(self, profile=None, fit: str = "captive") -> cq.Workplane:
    """Generate a pocket cutter for this nut.

    fit="captive"  → uses profile.free.radial   (loose for hand-insertion; default)
    fit="press"    → uses profile.press.radial  (interference for hammer-fit)

    First-call note: pre-calibration, `fit='press'` uses the shipped
    `press.radial=0.04`, ~4x tighter per side than `fit='captive'` (shipped
    `free.radial=0.15`). The first press print is likely to feel tight —
    run a test fit (or calibrate via `tools/calibrate.py press`) before
    relying on a press joint in a finished part.
    """
    from vibe_cading.print_settings import get_profile, ToleranceProfile
    prof = profile or get_profile()
    if fit == "captive":
        effective = prof  # bit-exact backwards-compat
    elif fit == "press":
        # Synthesise a per-call profile whose `free` slot carries press allowances;
        # CaptiveNutPocket continues to read profile.free.radial / .axial unchanged.
        effective = ToleranceProfile(free=prof.press, slip=prof.slip, press=prof.press)
    else:
        raise ValueError(f"unknown fit {fit!r}; expected 'captive' or 'press'")
    # ... existing CaptiveNutPocket(self.width_flats, ..., effective) call
```

**Surface impact (Option A, honest LOC count).** ~10–15 LOC concentrated in `MetricHexNut.to_cutter`:
- Add `fit: str = "captive"` parameter to signature (+1 LOC).
- Add the 3-way `if/elif/else` branch synthesising `effective` (+5 LOC).
- Replace the `CaptiveNutPocket(..., prof)` call with `CaptiveNutPocket(..., effective)` (1 LOC modified).
- Expand docstring with `fit` semantics + the first-call press-fit warning (+5–8 LOC).
- **Zero changes** to `CaptiveNutPocket.__init__` / `.solid` / `.to_cutter`.
- **Zero changes** to `tests/test_cutter_overcut.py` / `tests/test_protocols.py` / `engine_api.json`.

**Default `fit="captive"` preserves all existing call-site behaviour bit-exactly** — `effective is prof` in that branch, so `CaptiveNutPocket` receives an identical `ToleranceProfile` instance, the read sites in `holes.py` lines 426/440 behave identically, and every current caller continues to get `free.radial`. The new `fit="press"` opt-in is what the calibrated `press.radial` value will actually affect when a downstream contributor reaches for a press-fit nut pocket.

This refactor is in scope for this PR per Q7 option (a). It is the smallest possible change that honours the user's "M3 nut for press fit" mental model without breaking backwards compatibility or the published `CaptiveNutPocket` wire contract.

### §6. Change-preview wire format (FR21)

Plain-text, fixed-layout, no colour codes:

```
Calibration target
  File:    print_profiles_user.json              (will be CREATED)
  Profile: bambu_p1s__pla_overture               (will be CREATED)
                                                  (resolved from VIBE_PRINT_PROFILE)
  Grade:   free
  Field:   radial

Change
  Before:  free.radial = 0.150 mm                (inherited from print_profiles.json:fdm_standard)
  After:   free.radial = 0.180 mm

Derivation
  Best-fitting gauge variant D = 3.56 mm         (your input)
  Nominal M3 clearance N      = 3.200 mm         (vibe_cading/mechanical/screws/metric.py:23)
  free.radial = (D − N) / 2  = 0.180 mm

Migration
  (none — profile is in nested schema)
     -- OR --
  Will migrate the existing legacy-flat entry to the nested schema
  before applying the calibration (z_clearance → axial on every grade).

Downstream consumers that will inherit free.radial = 0.180 mm:
  - MetricMachineScrew.to_cutter (shaft clearance)
  - CounterboreHole, CountersinkHole, ClearanceHole, ...  (every mechanical/holes.py class)
  - Standoff.to_cutter, Hinge.to_cutter
  - FreespinHexHub.bearing_seat_diameter
  ...and every other class that reads profile.free.radial.

Other grades and fields are preserved verbatim.

Apply this change? [y/N]:
```

Conditional lines (`(will be CREATED)`, `(resolved from ...)`, `(inherited from ...)`, the Migration block) are suppressed or rewritten per the actual state. The "Downstream consumers" block is hard-coded per knob in the helper (3–4 representative names per knob), not auto-discovered.

### §7. Legacy-flat migration on write (FR25)

If the **target profile entry** in the existing `print_profiles_user.json` is legacy-flat (per `_is_legacy_flat_entry`), the helper migrates it to nested **as part of the same atomic write**:

1. Read raw user file.
2. Locate target entry.
3. If `_is_legacy_flat_entry(entry)` → replace `entry` with `_migrate_flat_to_nested(entry)` on the copy.
4. Apply the calibrated leaf (as in §3 step 5).
5. The change preview surfaces the migration explicitly (FR21 "Migration" block).
6. Atomic write of the full file.

**Other profile entries in the same file are NOT touched** — only the target entry migrates. A user with `{"fdm_standard": {legacy-flat}, "bambu_p1s__pla_overture": {nested}}` calibrating against `fdm_standard` ends with `{"fdm_standard": {nested-migrated-with-calibrated-leaf}, "bambu_p1s__pla_overture": {nested-untouched}}`. Test T-MigrateScoped asserts this.

Mirrors Brief #1's deep-merge "migrate-before-merge" ordering on read; this brief mirrors it on write. The user file's untouched profiles stay byte-identical (FR24 invariant).

## Implementation Plan

Sequenced tasks for @developer. Each is atomic and independently verifiable. Tasks are ordered to land smallest-surface-area first; the helper script (T9) integrates the prior tasks.

- [x] **T1 — Sub-package scaffold.** Create `vibe_cading/mechanical/calibration/__init__.py` (empty + AGPLv3 header).
- [x] **T2 — `MThreeClearanceGauge` class.** New file `vibe_cading/mechanical/calibration/m3_clearance_gauge.py`. Single-anchor sweep gauge, layout mirrors `AxleHoleGauge` (round through-holes in a flat block, label band on -Y, engraved diameter labels). Default `diameters` tuple: `(2.90, 3.00, 3.10, 3.20, 3.30, 3.40, 3.50)` — brackets the 3.2 mm M3 clearance nominal symmetrically with ±0.3 mm range in 0.10 mm steps (coarser than `AxleHoleGauge`'s 0.05 mm because FDM `free` fits are coarser than `slip` fits). Reads nominal live from `METRIC_SIZES["M3"]["clearance"]` (asserts in `__init__` that the centre value equals the nominal — guards against table drift). Constructor signature: `(diameters=DEFAULT_DIAMETERS, depth=8.0, hole_pitch=9.0, engrave_depth=0.6)`. Exposes `.solid` and `.diameters` (tuple), matching the `AxleHoleGauge` public surface.
- [x] **T3 — `MThreeNutPocketGauge` class.** New file `vibe_cading/mechanical/calibration/m3_nut_pocket_gauge.py`. Single-anchor sweep gauge sweeping **hexagonal pocket widths-across-flats**. Default `widths` tuple: `(5.30, 5.40, 5.50, 5.60, 5.70, 5.80)` — brackets the 5.5 mm M3 nut nominal asymmetrically (slightly wider on the +side to bracket typical FDM over-shrink). Each pocket is a hex polygon extruded to the block depth, plan-centred per cell with the same label-band layout as `AxleHoleGauge`. Reads nominal live from `MetricHexNut.DIMENSIONS["M3"]["width_flats"]` (asserts centre-value match). Constructor signature: `(widths=DEFAULT_WIDTHS, depth=8.0, pocket_pitch=10.0, engrave_depth=0.6)`. Exposes `.solid` and `.widths` (tuple).
- [x] **T4 — Visual contract probe + initial SVGs.** Designer runs `tmp/visualise_m3_clearance_gauge.py` and `tmp/visualise_m3_nut_pocket_gauge.py` to generate the initial iso_ne SVGs (placeholder for Step 4 human gate). Probes copy the resulting SVGs to `.agents/plans/2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg` and `..._m3_nut_pocket_iso_ne.svg`. Embed both in the Visual Contract section of this design. Clean up `tmp/visualise_*.py` after. *(Phase A note: regenerated from the implemented classes in T13 below — Step-3 probe artefacts were not created because Phase A reached the same outcome more directly.)*
- [x] **T5 — Add `fit` kwarg to `MetricHexNut.to_cutter` (Option A: scoped to `nuts/metric.py` only).** Per §5 above. Add `fit: str = "captive"` parameter; default branch is `effective = prof` (bit-exact backwards-compat); `fit="press"` branch synthesises `ToleranceProfile(free=prof.press, slip=prof.slip, press=prof.press)` so `CaptiveNutPocket` (unchanged) reads the press allowances via its existing `tolerance.free.radial` lookup. Update the docstring with `fit` semantics AND the first-call press-fit tightness warning. **Do NOT touch `CaptiveNutPocket.__init__` / `.solid` / `.to_cutter`** — they keep their `width_across_flats` parameter name, their `profile` positional kwarg, and their `tolerance.free.radial` reads. Net surface: ~10–15 LOC in one file (`vibe_cading/mechanical/nuts/metric.py`); zero changes to `holes.py`, `tests/test_cutter_overcut.py`, `tests/test_protocols.py`, or `engine_api.json`.
- [x] **T6 — Helper module: data assembly layer.** Module-private functions in `tools/calibrate.py`:
  - `_read_user_profiles_raw() -> dict` (raw JSON; `{}` if file missing; aborts on JSON parse error with clear message per FR23).
  - `_resolve_target_entry(raw, name) -> tuple[dict, bool]` (returns `(entry_or_empty, was_legacy_flat)`).
  - `_build_after_entry(entry, grade, field, value) -> dict` (deepcopy + set; preserves siblings; creates nested grade dict if absent).
  - `_migrate_if_legacy_flat(entry) -> dict` (thin wrapper around `_migrate_flat_to_nested`).
- [x] **T7 — Helper module: interaction layer.** Module-private functions:
  - `_prompt_diameter(valid: tuple[float, ...], gauge_name: str) -> float` (validates against gauge's swept tuple; rejects with help text listing valid values per FR11 + Q3 resolution).
  - `_prompt_profile_name_confirmation(name: str) -> str` (FR20 / §4 step 3).
  - `_prompt_confirm() -> bool` (y/N, default N).
  - `_render_preview(...)` (per §6 wire format).
  - `_render_success(...)` (per Q8 resolution — minimum + next-knob pointer in sequence mode).
- [x] **T8 — Helper module: atomic-write layer.** Module-private function `_atomic_write_json(path: Path, data: dict, knob: str) -> None`. Writes `<path>.tmp.<pid>.<knob>`, fsyncs, `os.replace` → `<path>`. Cleanup `<path>.tmp.*` on exception (best-effort, do not mask original exception).
- [x] **T9 — Helper module: CLI layer.** `_build_parser()` with subcommand layout from Architecture §"Subcommand layout"; `main(argv=None) -> int` orchestrates per-knob loop (free → press in sequence mode; just `slip` in opt-in mode); each knob runs T6→T7→T8 cycle. `if __name__ == "__main__": sys.exit(main())` entry point. Lazy-import CadQuery and gauge classes — `--help` path completes without triggering CadQuery import-cascade (FR-NFC "Runtime budget" — verified by T-RuntimeHelp).
- [x] **T10 — `--help` text.** Per FR3: describes v1 scope, prerequisite (user prints gauges first), file modified, per-profile targeting, ≥1 concrete invocation example with a gauge-export reference (`python3 tools/preview.py vibe_cading.mechanical.calibration.m3_clearance_gauge.MThreeClearanceGauge --views iso_ne` → preview, or `python3 build.py ...` if/when registered). The cross-model propagation claim (FR13) is stated in the `--help` text. **Also document the first-write normalisation** (per §3): the `--help` text MUST include a one-line note that `print_profiles_user.json` is re-serialised on every write via `json.dumps(..., indent=2, sort_keys=True)`, so any handwritten indentation / key ordering will be normalised on first calibration; JSON-semantic content of untouched profiles is preserved.
- [x] **T11 — README update.** Replace the "single-knob calibration CLI ... is on the roadmap" line in `README.md` *Print Tolerances & Calibration* with a live reference to `python3 tools/calibrate.py` (no-args invocation is the recommended entry point). Add a sub-section listing the v1 calibratable knobs and their default gauges. Cross-link to `docs/lego-technic.md` *Tuning Tolerances* for the slip-opt-in path.
- [x] **T12 — Tests (see Tests table below).** All tests live under `tests/tools/test_calibrate.py` (helper unit + integration tests) and `tests/mechanical/test_calibration_gauges.py` (gauge geometry tests). Use `tmp/` tempfiles for filesystem fixtures.
- [x] **T13 — Regenerate visual-contract SVGs.** Developer runs `python3 tools/preview.py vibe_cading.mechanical.calibration.m3_clearance_gauge.MThreeClearanceGauge --views iso_ne --out .agents/plans/` and renames the output to `2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg` (and same for nut pocket). Overwrites the Step-3 probe SVGs with the implemented-class outputs (per Visual Contract Phase A rule).
- [x] **T14 — CI verification.** Run `tools/check_no_main_blocks.py`, `tools/check_license_headers.py`, `flake8`, and full test suite. All pass.

## Tests

| # | Test description | Expected assertion | File / location | Maps to |
|---|------------------|--------------------|-----------------|---------|
| 1 | `--help` runs cleanly without importing CadQuery | `import time` profile shows no `cadquery` in modules; exits 0; help text mentions `free`, `press`, `slip`, `print_profiles_user.json` | `tests/tools/test_calibrate.py::test_help_no_cadquery_import` | FR3, FR-NFC Runtime |
| 2 | `--help` lists all calibratable knobs with their gauges and consumer hints | help text contains all of: `free.radial`, `press.radial`, `slip.radial`, `MThreeClearanceGauge`, `MThreeNutPocketGauge`, `AxleHoleGauge` | `tests/tools/test_calibrate.py::test_help_lists_knobs` | FR3, FR13 |
| 3 | `calibrate.py free --diameter 3.30 --yes --profile testprofile` against missing user file → creates file with single calibrated leaf | file exists; content `== {"testprofile": {"free": {"radial": 0.05}}}`; no other keys | `tests/tools/test_calibrate.py::test_creates_user_file` | FR4, FR18, FR19, FR23, FR24 |
| 4 | Calibration formula correctness — `D=3.30, N=3.20` → `radial=0.05`; `D=3.50` → `radial=0.15`; `D=3.10` → `radial=-0.05` | `_compute_radial(D, N) == (D − N) / 2` for all three cases | `tests/tools/test_calibrate.py::test_formula` | §1 Data Contract |
| 5 | Nominal reads live from source-of-truth constants — monkey-patch `METRIC_SIZES["M3"]["clearance"] = 3.5`; calibration uses 3.5, not 3.2 | post-monkey-patch `_NOMINAL_FREE_RADIAL == 3.5` after module reload | `tests/tools/test_calibrate.py::test_nominal_live_source` | §1 Data Contract, FR11 |
| 6 | Field-level merge — pre-existing user file with `{"fdm_standard": {"slip": {"radial": 0.10}, "press": {"axial": 0.15}}}`; calibrate `free.radial=0.18`; assert all three siblings present after | post-write file deep-equals `{"fdm_standard": {"slip": {"radial":0.10}, "press":{"axial":0.15}, "free": {"radial":0.18}}}`; sibling profiles byte-identical | `tests/tools/test_calibrate.py::test_field_level_merge_preserves_siblings` | FR24 |
| 7 | Other profile entries are byte-identical post-write — user file with three profiles; calibrate one; checksum the other two | SHA256 of serialised non-target entries matches pre/post-write | `tests/tools/test_calibrate.py::test_other_profiles_untouched` | FR24 |
| 8 | Legacy-flat → nested migration on write — user file `{"fdm_standard": {"z_clearance":0.20, "free_fit":0.15, "slip_fit":0.05, "press_fit":0.04}}`; calibrate `free.radial=0.18`; assert post-write is fully nested with migrated `axial` values | `result["fdm_standard"]["free"]["axial"] == 0.20`; same for `slip.axial`, `press.axial`; `free.radial == 0.18`; no `z_clearance`/`free_fit`/etc. keys remain | `tests/tools/test_calibrate.py::test_legacy_flat_migrate_on_write` | FR25, §7 |
| 9 | Legacy-flat migration is scoped to target profile — file `{"fdm_standard":{legacy}, "bambu_p1s__pla":{nested}}`; calibrate against `fdm_standard`; assert `bambu_p1s__pla` byte-identical | sibling profile checksum matches pre/post | `tests/tools/test_calibrate.py::test_legacy_flat_migrate_scoped_to_target` | FR25, §7 |
| 10 | Atomic write — inject failure between tempfile write and `os.replace` (monkey-patch `os.replace` to raise); assert original file untouched, no tempfile leaked | original file's mtime + content unchanged; no `*.tmp.*` files in repo | `tests/tools/test_calibrate.py::test_atomic_write_crash_injection` | FR23, §3 |
| 11 | y/N default-N exits without write — pipe `\n` (default-no Enter) to stdin; assert exit 0 and no write | original file unchanged | `tests/tools/test_calibrate.py::test_default_no_aborts` | FR22 |
| 12 | Per-knob atomic in sequence mode — run `all`; inject `KeyboardInterrupt` after first knob's confirmation+write but before second knob's preview; assert first knob persisted | post-interrupt file contains calibrated `free.radial`, no `press.radial` | `tests/tools/test_calibrate.py::test_per_knob_atomic_in_sequence` | FR27, §3 |
| 13 | Per-knob independence — calibrating `press` without first calibrating `free` succeeds | exit 0; file contains only `press.radial` leaf | `tests/tools/test_calibrate.py::test_per_knob_independent` | FR28 |
| 14 | Cross-model propagation — calibrate `free.radial=0.18` under `testprofile`; `get_profile("testprofile").free.radial == 0.18` | `from vibe_cading.print_settings import get_profile; assert get_profile("testprofile").free.radial == 0.18` | `tests/tools/test_calibrate.py::test_propagation_to_get_profile` | FR13, §2 |
| 15 | Profile-name confirmation prompt fires for new non-shipped name; default-Enter accepts; user can re-type to fix typo | Interactive simulation: prompt appears for `bambo_p1s`; Enter ⇒ writes under `bambo_p1s`; re-type `bambu_p1s` ⇒ writes under `bambu_p1s` | `tests/tools/test_calibrate.py::test_profile_name_confirmation` | FR20, §4 step 3 |
| 16 | Profile-name confirmation SKIPPED when `--profile` is explicit and `--yes` is set | No prompt; writes under given name directly | `tests/tools/test_calibrate.py::test_profile_name_confirm_skipped_on_yes` | FR20, Q5 |
| 17 | `--diameter` rejects values not in the gauge's swept tuple, listing valid choices in the error | exit nonzero; stderr contains `valid choices:` + the gauge's `diameters` tuple | `tests/tools/test_calibrate.py::test_diameter_validates_against_sweep` | FR11, Q3 |
| 18 | Active-profile resolution chain uses `get_default_profile_name()` — set `VIBE_PRINT_PROFILE=foo`; assert tool resolves `foo` without `--profile` | stdout contains `Profile: foo` | `tests/tools/test_calibrate.py::test_active_profile_resolution` | FR15 |
| 19 | `--profile` flag overrides env var | env `VIBE_PRINT_PROFILE=foo`, run `--profile bar`; stdout contains `Profile: bar` | `tests/tools/test_calibrate.py::test_profile_flag_overrides_env` | FR16 |
| 20 | Resolved profile name printed BEFORE any prompt or write | stdout-before-first-prompt contains `Profile:` line | `tests/tools/test_calibrate.py::test_profile_printed_before_prompts` | FR17 |
| 21 | Corrupt user JSON file → abort with clear error; original file untouched | exit nonzero; stderr names the JSON parse error and the file path; file unchanged | `tests/tools/test_calibrate.py::test_corrupt_user_file_aborts` | FR23 |
| 22 | `MThreeClearanceGauge` geometry — solid is single contiguous solid; diameters tuple readable; centre value == nominal | `assert len(gauge.solid.solids().vals()) == 1`; `3.2 in gauge.diameters` | `tests/mechanical/test_calibration_gauges.py::test_m3_clearance_gauge` | T2 |
| 23 | `MThreeNutPocketGauge` geometry — single solid; widths tuple readable; centre value == nominal | `assert len(gauge.solid.solids().vals()) == 1`; `5.5 in gauge.widths` | `tests/mechanical/test_calibration_gauges.py::test_m3_nut_pocket_gauge` | T3 |
| 24 | `MetricHexNut.to_cutter(fit="press")` reads `press.radial` not `free.radial` | Build cutter with `ToleranceProfile(press=FitGrade(radial=1.0), free=FitGrade(radial=0.0))`; pocket diameter reflects `+1.0` inflation, not `+0.0` | `tests/mechanical/test_metric_nut.py::test_to_cutter_press_fit` | T5, §5 |
| 25 | `MetricHexNut.to_cutter()` default (no fit kwarg) preserves backwards-compat — pocket reads `free.radial` | Default-call against profile with `free.radial=0.1, press.radial=1.0` produces pocket inflated by `0.1`, not `1.0` | `tests/mechanical/test_metric_nut.py::test_to_cutter_default_captive_backcompat` | T5, §5 |
| 26 | Success block names ≥3 downstream consumers per knob | stdout per knob contains ≥3 substrings from the per-knob hardcoded consumer list | `tests/tools/test_calibrate.py::test_success_block_lists_consumers` | FR13 |
| 27 | License header on `tools/calibrate.py` + both new gauge files passes CI gate | `tools/check_license_headers.py tools/calibrate.py vibe_cading/mechanical/calibration/*.py` exits 0 | `tests/ci/test_license_headers.py` (existing) | FR2 |
| 28 | No third-party imports in helper or gauges | `grep -E "^(from\|import) (?!vibe_cading\|cadquery\|cq\|argparse\|json\|sys\|os\|tempfile\|pathlib\|warnings\|copy)" tools/calibrate.py vibe_cading/mechanical/calibration/*.py` returns nothing | `tests/ci/test_no_third_party.py` | FR30, FR-NFC |

**FR coverage check** (greppable on `FR<n>`): FR1 → T9, T10. FR2 → T27. FR3 → T1, T2, T10. FR4 → T3 (free), T3 (press via subcommand). FR5 → T13 (slip subcommand). FR6 → (negative — no test, but T2 asserts only `free`/`press`/`slip` knobs appear in `--help`). FR7 → T22, T23 (≤5-model cap — only 2 gauge classes net-new + 1 existing = 3 total). FR8 → T4 (formula), T5 (nominal live). FR9 → T22, T23, T24 (Q6 anchor decision). FR10 → T14, T17 (slip path). FR11 → T5, T17. FR12 → T1, T2, T3, T5 (gauge classes land in this PR per Q7 (a)). FR13 → T2, T14, T26. FR14 → (structurally — no new field/grade introduced; verified by absence). FR15 → T18. FR16 → T19. FR17 → T20. FR18 → T3, §4. FR19 → T3. FR20 → T15, T16. FR21 → T6 (preview rendering tested via golden-string match — sub-test of T6 line scope). FR22 → T11. FR23 → T10, T21. FR24 → T6, T7, T9. FR25 → T8, T9. FR26 → T13 (sequence + per-knob both work). FR27 → T12. FR28 → T13. FR29 → T11 (README update). FR30 → T28. **All 30 FRs covered.**

## Success Criteria

Measurable, objectively verifiable conditions for @developer to claim the task done.

1. **All 28 tests in the Tests table pass** on a clean dev-container checkout (`pytest tests/tools/test_calibrate.py tests/mechanical/test_calibration_gauges.py tests/mechanical/test_metric_nut.py` exits 0).
2. **`python3 tools/calibrate.py --help` completes in < 2 seconds** on the dev-container baseline (measured via `time`; FR-NFC Runtime budget).
3. **`python3 tools/calibrate.py --help` imports zero CadQuery modules** (verified via `python3 -X importtime tools/calibrate.py --help 2>&1 | grep cadquery` → empty; T1).
4. **End-to-end propagation smoke**: `VIBE_PRINT_PROFILE=test_e2e python3 tools/calibrate.py free --diameter 3.30 --yes --profile test_e2e` followed by `python3 -c "from vibe_cading.print_settings import get_profile; print(get_profile('test_e2e').free.radial)"` prints `0.05`. (Manual smoke, also asserted programmatically by T14.)
5. **CI passes** — `tools/check_no_main_blocks.py`, `tools/check_license_headers.py`, `flake8`, full test suite all green.
6. **`build.toml` is NOT modified.** The helper is a CLI utility, not a build deliverable. The two new gauge classes MAY be added to `build.toml` in a follow-up PR if the human reviewer wants printable STEPs in `build/`, but that registration is out-of-scope here (explicit approval gate per project rule).
7. **The visual-contract SVGs** (`*_m3_clearance_iso_ne.svg`, `*_m3_nut_pocket_iso_ne.svg`) are committed in `.agents/plans/`, regenerated post-implementation from the implemented classes via `tools/preview.py`, and embedded in the design's Visual Contract section.
8. **README "Print Tolerances & Calibration" section** no longer contains the string "is on the roadmap" or "TODO" near the calibration paragraph; instead reads `python3 tools/calibrate.py` as the recommended entry point (T11 verification).
9. **`MetricHexNut.to_cutter()` backwards-compat** — every existing call site (grep `MetricHexNut(.*)\\.to_cutter\\(` and `\\.to_cutter\\(profile=`) continues to compile and produce bit-identical geometry to pre-refactor (T25 + a test-suite-wide regression sweep on bearings / standoffs / nut consumers).

## Out of Scope

Mirrored and trimmed from requirements; expanded with Step-3 dialog exclusions.

- **All req §"Out of Scope" entries carry over verbatim** — axle cross-hole slot calibration, `*.axial` knobs, `slot` knobs on non-slip grades, net-new gauges beyond the FR7 inventory, auto-measurement, auto-print, Stage-2c production-corner calibration, `build.toml` registration, pluggable calibration-registry framework, `ToleranceProfile` / `FitGrade` rename, GUI / TUI / curses, changing model-class signatures **beyond the explicit `MetricHexNut.to_cutter` `fit` kwarg in §5**.
- **Bearing-pocket gauge as the v1 `press` default.** Q6 resolved toward M3-nut. The bearing-pocket gauge is a clean v2 follow-up — once a contributor needs to calibrate `press.radial` specifically against a bearing rather than a nut, that's the v2 brief.
- **Shared `_SweepGaugeBase` class.** Q7 + R7 — speculative until a third single-anchor gauge materialises.
- **Promoting `_is_legacy_flat_entry` / `_migrate_flat_to_nested` to public API.** R1 + SUPERSEDED R1 — still only two callers post-this-brief.
- **Auto-discovery of downstream consumer names in success block.** Hardcoded per-knob list in the helper; auto-discovery via AST/grep is fragile and unnecessary for the v1 user-experience goal. v2 if the consumer set grows enough to make maintenance painful.
- **Calibration history / diff log.** The helper writes one new value at a time; the user file's git history is the audit trail (when the user commits it — typically they don't, it's gitignored). v2 if needed.
- **Non-M3 anchor sizes.** The default gauges are M3-specific (3.2 mm clearance, 5.5 mm nut). M4/M5 variants are v2 — most contributor parts use M3, and adding M4/M5 gauges multiplies the print-cycle cost without commensurate calibration accuracy gain (FDM under-extrusion is roughly diameter-proportional within the M3–M5 range).

## Known Risks & Mitigations

| Risk | Predicted cost if unmitigated | Mitigation |
|------|-------------------------------|-----------|
| **R1: `_fitgrade_from_dict` hardcoded defaults drift from `fdm_standard` shipped values** — §4's contract relies on them matching. If they diverge, a fresh user-profile entry inherits subtly-wrong sibling values. | 1 lost print cycle (~1 hour) + 30 min debug to trace silent value drift; library-wide blast-radius limited to fresh user-profile entries (returning users with full nested entries unaffected) | T-FitgradeDefaults — add an assertion test that `_fitgrade_from_dict({}, default_radial=0.15, default_axial=0.20).slip.radial == fdm_standard_shipped.slip.radial`. New test in Tests table; sub-test of T14. |
| **R2: User mis-measures D (off by 0.05 mm) and writes a slightly-wrong calibrated value** — universal calibration risk; not avoidable in software. | 0–1 lost print cycles per knob; not silent (user's next print will visibly fit slightly wrong). | Sweep-tuple range is wide enough (M3 clearance ±0.30 mm) that a one-step mis-read is recoverable by re-running calibration on the next print. Change-preview wire format (§6) shows the derivation transparently. |
| **R3: `MetricHexNut.to_cutter` refactor breaks a downstream caller we missed in the grep** — backwards-compat assumption violation. | 1 unit-test failure (caught in T25 + full test suite); zero print cost | Default `fit="captive"` preserves bit-exact existing behaviour; T25 + the full test suite catch any consumer that relied on the old shape. Refactor is intentionally 5-LOC; broader changes would inflate risk. |
| **R4: Atomic write race when user runs two `calibrate.py` instances against the same file in parallel.** | 1 corrupted user file (worst case) → user rewrites from defaults (~5 min); requires deliberate two-shell parallelism — extremely unlikely | Tempfile name includes `<pid>.<knob>`; `os.replace` is atomic on POSIX; if a race happens, last-writer-wins (one knob's value lost, file remains coherent). T10 covers the single-process crash case; parallel-instance race is documented as "don't do that" in `--help`. |
| **R5: `--profile` typo creates a new entry instead of updating the intended one.** | 1 lost calibration (user keeps editing the typo'd entry, real entry stays default); recoverable by editing the JSON. | FR20 / §4 step 3 — the profile-name confirmation prompt fires specifically to catch this case. Skipped on `--yes`+`--profile` (CI path; user accepts the bypass). |
| **R6: Designer-step-3 visual-contract probe SVG embeds wrong axis orientation that survives to step-4 human gate.** | Caught at step-4 review (~5 min review time wasted); zero print cost | Designer probe generates the SVG via `cq.exporters.export(workplane, str(svg_path))` with explicit camera direction; Step 5 Phase A overwrite from `tools/preview.py` is the second checkpoint. Pattern proven by Brief #1's `axle_hole_gauge` design preview. |
| **R7: Helper imports CadQuery at `--help` path and trips the 2-second budget.** | 1 user-visible regression (annoying-but-cosmetic). | T1 asserts no CadQuery in `--help` import graph; gauge imports are inside the `_prompt_diameter` code path (post-help). Lazy-import pattern documented in the helper's module docstring. |
| **R8: `MThreeNutPocketGauge` hex-pocket sweep widths are too narrow a range** to capture extreme-FDM-shrink printers. | 1 user runs the gauge and reports "no pocket fits"; recoverable in v2 with a wider sweep or a `--widths` flag. | Default range 5.30–5.80 mm is ±5% around 5.5 mm — wider than M3 clearance gauge (±10% around 3.2 mm in proportional terms) because press fits tolerate more variation. If reports come in, expand the tuple in a follow-up; the helper reads it live (FR11). |

---

## Design Dialog Log

Five rounds; Designer self-played the requester role per the "fewer-knobs anchor" mandate and the Q1–Q7 deferral note in the req. Each round drove a concrete revision.

### Round 1 — Gauge class location and base-class decision (Q7-adjacent)

**TL proposal:**
> Three options for where the new gauge classes live: (i) flat-add to `vibe_cading/mechanical/` (joins `bearings.py`, `holes.py`, `magnets.py`, etc.); (ii) new sub-package `vibe_cading/mechanical/calibration/`; (iii) new sub-package under `vibe_cading/tools/` (a "tools" tree that doesn't exist yet — would create it). Recommend (ii). On base class: `ToleranceGauge` (existing) is structurally a multi-row mega-gauge with hardcoded M3+bearing+peg+pin in one block; it's not a base. `AxleHoleGauge` is the de-facto single-anchor sweep gauge shape. Recommend NO base class in v1 — duplicate ~30 LOC of layout boilerplate, factor when third exemplar materialises.

**Requester (Designer) challenge:**
> The req's "documentation-by-example" non-functional rule means a first-time contributor reads the gauge code to understand the system. If we duplicate layout boilerplate between two new files, we double the surface they need to read. Push back on no-base-class.

**Resolution:**
> Kept "no base class" decision but added explicit Module-Depth table entry (R7 rejection in Alternatives) so the rationale is durable. The contributor-onboarding concern is addressed by both gauges following `AxleHoleGauge`'s shape literally (same constructor signature shape, same `.solid` + `.diameters`/`.widths` public surface) — the convention itself is the documentation. Re-evaluate when a third gauge needs the same pattern.

### Round 2 — Q6 press-fit gauge anchor (M3 nut vs bearing pocket)

**TL proposal:**
> Q6 option (a) — M3 nut gauge writing to `press.radial`, accept the small `MetricHexNut.to_cutter` refactor (5 LOC, `fit="press"` kwarg, default `fit="captive"` preserves backwards-compat). Schema-aligned, mental-model-aligned, and the refactor is bounded. Reject (b) (waste a gauge slot calibrating `free.radial` twice) and (c) (bearing-pocket honest-but-niche; user named the nut explicitly).

**Requester (Designer) challenge:**
> The refactor changes a `to_cutter` signature — that's the "modifying existing model-class signatures" out-of-scope clause from the req (last bullet of req §Out of Scope). Pushback: is this really in scope for this brief, or should it spin off?

**Resolution:**
> The req's last bullet explicitly says *"If Q6 resolution requires a small targeted change to `MetricHexNut.to_cutter()` (e.g. to read `press.radial` for a press-pocket variant), that change is scoped to whatever sub-brief Q7 resolves to — not to the helper itself."* — i.e. it's gated on Q7. Q7 resolution (Round 3 below) puts the refactor in this PR. The 5-LOC refactor adds an optional `fit` kwarg with default-preserving semantics (T25 verifies no existing caller observes a change), so the "modifying signatures" clause is satisfied additively. Documented as §5 of Data Contract with the full diff.

### Round 3 — Q7 PR sequencing (all-in-one vs split)

**TL proposal:**
> Q7 option (a) — all-in-one PR. The gauge classes are ~80 LOC each, the helper is ~250 LOC, the refactor is 5 LOC, the README update is 5 LOC. Total diff ~420 LOC. Single coherent review.

**Requester (Designer) challenge:**
> The principled-over-expedient-path rule says default to the principled option when the cost gap is small. Splitting buys reviewability — gauge1 PR, gauge2 PR, refactor PR, then helper PR consuming them. Four PRs but each is small and independently reviewable. Cost gap: ~3 review cycles (~3 hours) vs 1.

**Resolution:**
> All-in-one wins on three grounds: (1) the gauges are functionally useless without the helper that consumes them — splitting means three PRs of dead-code-pending-consumer; (2) the refactor's safety depends on the new `fit` kwarg being used by a downstream consumer (the helper) — splitting risks the refactor landing without an exercised press-fit path; (3) the visual-contract SVGs are co-located with this design artifact, so the gauges' Step-4 human gate naturally batches with the helper's. The cost gap is ~2 hours saved by all-in-one; under the rule's ≤1-hour cost-gap threshold the principled split would win, but the *coherence* gain here flips the call. Documented as Architecture §"Sequencing decision".

### Round 4 — Q1 opt-in mechanism for the axle gauge (slip.radial)

**TL proposal:**
> Q1 option (b) — sub-subcommand `tools/calibrate.py slip` (or `slip --gauge axle`) puts the opt-in gauge behind an explicit user gesture. No interactive picker at the slip step (rejects (c)), no separate `--slip-gauge` flag (rejects (a) — flag pollution). The `--gauge <name>` flag exists in the CLI as a v2 extension point but in v1 has only one valid value per knob, defaulting to it.

**Requester (Designer) challenge:**
> The req's "Lego-axle gauge as opt-in" framing implies that the default invocation (`calibrate.py` with no args) does NOT prompt for slip. But the no-args sequence in FR26 is "walk every default-knob calibration in sequence" — that's free + press, not slip. Sub-subcommand approach correctly excludes slip from the default sequence. Confirm: `calibrate.py` ≡ `calibrate.py all` ≡ free→press (no slip). To calibrate slip, user explicitly invokes `calibrate.py slip`.

**Resolution:**
> Confirmed. The hybrid CLI is `calibrate.py [free|press|slip|all]` with `all` defaulting to free+press (not slip). `slip` is a distinct subcommand the user reaches deliberately. The `--gauge` flag exists for future opt-in alternates but in v1 has one valid value per knob.

### Round 5 — Q4 per-knob atomic vs full-session + Q5 interactive vs one-shot + Q3 custom-sweep + Q8 success-block + Q9 visual contract

**TL proposal (batched for the smaller Q's):**
> Q4: per-knob (matches req FR27 default, SUPERSEDED design precedent, recovery-use-case). Q5: support `--diameter <value> --yes --profile <name>` one-shot per-knob; require `--profile` explicit on any one-shot that would create a new entry (so CI cannot silently mis-resolve env to a typo'd name). Q3: helper accepts ONLY the default sweep values (option a); rejects others with the valid-choices list in the error. Q8: minimum (path + leaf + before + after) + a one-line "next" pointer in sequence mode only. Q9: helper itself carve-out exempt; each net-new gauge class gets its own iso_ne SVG (M3 clearance, M3 nut pocket) co-located in this design's `.agents/plans/` dir.

**Requester (Designer) challenge:**
> On Q5: requiring `--profile` for new entries in `--yes` mode is a friction point for a CI that wants to "smoke-test the calibration write path." Counter-proposal: allow `--yes` without `--profile` IF the resolved env-or-default profile name is one of the shipped names (`fdm_standard`/`resin_precise`/`cnc`) — those can't be "typo'd" because they're hardcoded. New entries from a typo'd env var get blocked.

**Resolution:**
> Accepted the counter-proposal. Codified in §4 step 3: confirmation prompt is skipped iff (`--yes` AND `--profile` explicit) OR (`--yes` AND resolved name is in `{"fdm_standard", "resin_precise", "cnc"}`). Documented in T16. Q3, Q4, Q8, Q9 resolutions stand as proposed.

### Round 6 — Condition application (2026-05-25)

Applied 5 deduplicated reviewer conditions (§3 / §4 / §4¶2 / §5 LOC / §5 docstring) returned by the three independent fresh-context reviews (TL + Developer + Designer-as-domain-expert, all APPROVE-WITH-CONDITIONS). Architectural shape unchanged.

- **§5 refactor scope (Independent TL C1 + Independent Developer C1):** chose Option A — preserve `CaptiveNutPocket`'s public constructor signature; introduce `fit` selector only at `MetricHexNut.to_cutter` by synthesising a per-call `ToleranceProfile` whose `free` slot carries press allowances. Zero changes to `holes.py`, `tests/test_cutter_overcut.py`, `tests/test_protocols.py`, or `engine_api.json`. Net surface ~10–15 LOC in one file. T5 updated to match.
- **§3 atomic-write semantics (Independent TL C2):** "byte-identical" rewritten to "JSON-semantic equivalence (`json.loads(before) == json.loads(after)`)" with the canonical serialisation pinned to `json.dumps(..., indent=2, sort_keys=True)`. Normalisation documented in T10 `--help` task.
- **§4 Stage-2b `slip.slot` floor leak (Independent Domain Expert C1):** chose latter (success-block warning, not seeding) per the expert's recommendation. Added explicit success-block contract for fresh-profile `slip` writes that surfaces the `slip.slot → 0.0` resolution and how to opt into the shipped 0.10 floor. "Diff from defaults" invariant preserved.
- **§4 ¶2 doc-only correction (Independent Domain Expert C2):** the false claim that `_fitgrade_from_dict` defaults match `fdm_standard` rewritten to the honest "safety fallbacks (0.0 across the board)" framing, with explicit call-out of the `slip.slot` mismatch.
- **§5 docstring warning (Independent Domain Expert C3):** first-call press-fit tightness note added directly to the `to_cutter` docstring in the §5 code sketch (and re-stated in T5 task body) — pre-calibration `fit='press'` is ~4x tighter per side than `fit='captive'`; run a test fit before relying on a press joint.

Author sign-off state unchanged. Independent reviewer sections untouched — reviewers update those on re-spawn against the revised artifact.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [x] Domain expert co-sign  *(YES gate — Designer-as-domain-expert co-signs the calibration formula §1, propagation contract §2, atomic semantics §3, and Q6 refactor §5 against the foundation's read-side merge contract; this is the **author's** self-sign as the role authorised to issue it; the **independent** YES-gate sign-off is the Independent Researcher box below)*
- [x] Requester sign-off  *(Designer speaks for the req author per spawn brief; all FR1–FR30 addressed in Tests table; all Q1–Q9 resolved in Dialog Log)*
- [x] TL sign-off  *(all 7 termination conditions met — FR coverage greppable, Q1–Q9 all resolved with concrete decisions, Tests row per FR, measurable Success Criteria, Data & Interface Contracts §§1–7 specifies formula+inverse+propagation+atomicity+creation-flow+preview-format+migration-ordering, non-blocking risks carry predicted costs in concrete units, Module depth row with dual-lens verdict)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE (2026-05-25, re-confirmed after applying 2 conditions; see `## Independent TL Review` below)
- [x] Independent Developer  *(always required)* — APPROVE (2026-05-25, re-confirmed after applying Option-A refactor scoping; see `## Independent Developer Review` below)
- [x] Independent Researcher  *(required — YES gate; fresh-context Designer per the project's "no self-review for integrity sign-offs" rule)* — APPROVE (2026-05-25, re-confirmed after applying 3 conditions incl. Stage-2b `slip.slot` leak surface-not-seed; see `## Independent Domain Expert Review` below)

---

## Independent Domain Expert Review (Designer-as-domain-expert, fresh context, 2026-05-25)

### Verdict
**APPROVE** (3 small inline edits to §1, §4, §5; no architectural change).

### Domain integrity findings (per the 7 questions)

**Q1 — Gauge↔FitGrade mapping.** *Sound.* M3 clearance hole ↔ `free.radial` matches `MetricMachineScrew.to_cutter(fit="clearance")` (verified `metric.py:144,163` reads `data["clearance"]=3.2` then plumbs `prof.free.radial` via `CounterboreHole`). Axle hole ↔ `slip.radial` matches `TechnicAxleHole` default `fit="slip"` (`technic_axle_hole.py:94,107,114`). M3 nut pocket ↔ `press.radial` is sound **only after T5 refactor** — the v1 PR is therefore self-consistent.

**Q2 — Cross-model propagation.** *Sound.* Every named `free.radial` consumer in §2 verified live: `MetricMachineScrew.to_cutter` → `CounterboreHole(profile=prof)` (no axis flip; per-side allowance, dimensionally consistent with `radial = (D−N)/2`). `TechnicAxleHole` applies `2·grade.radial` to `TIP_TO_TIP` (`technic_axle_hole.py:114`) — matches §1's inverse `D = N + 2·radial`.

**Q3 — Calibration math soundness.** *Sound for all three knobs.* `(D−N)/2` is correct as a per-side half-allowance for diameter-like nominals (round hole, hex across-flats). For press: D < N ⇒ negative `radial` ⇒ pocket *shrinks* under the post-T5 `+ 2·press.radial` inflation ⇒ interference — sign physically correct. The "smallest pocket that grips" judgement is user-side, not formula-side; design correctly keeps formula uniform.

**Q4 — Knob coupling (Stage-2b `slip.slot` regression guard).** *Sound for existing entries — but tighten the fresh-profile spec.* §3 step 5 ("creates the nested dict path if absent; preserves siblings byte-identical") correctly preserves `slot` when calibrating `slip.radial` on an *existing* nested entry. **However:** §4 step 2 ("entry contains only the calibrated leaves") writes `{"slip": {"radial": 0.12}}` for a *fresh* user-named profile — on next `get_profile()`, `_fitgrade_from_dict` falls back to `default_slot=0.0`, **NOT** the shipped `fdm_standard.slip.slot = 0.10`. This re-introduces the Stage-2b regression for any fresh user-named profile (e.g. `bambu_p1s__pla_overture`). See condition C1.

**Q5 — Profile-creation flow.** *Internally consistent except for one false claim.* §4 ¶2 says the hardcoded `_fitgrade_from_dict` defaults "are deliberately matched to `fdm_standard.fdm_standard`'s shipped values" — verified `_FALLBACK_PROFILES[fdm_standard]` (`print_settings.py:628-635`) carries `slip.slot=0.10`, while `_fitgrade_from_dict default_slot=0.0` (`print_settings.py:343,358`). The claim is true for `radial`/`axial`, **untrue for `slot`**. See condition C2.

**Q6 — Cross-knob blast radius.** *Sound.* `Bearing.outer_pocket` is the only current `press.radial` consumer; post-T5, `MetricHexNut.to_cutter(fit="press")` joins. Blast radius numerically small (2 consumers) — matches §"Known Risks" framing.

**Q7 — `MetricHexNut.to_cutter(fit=...)` refactor domain-correctness.** *Sound.* `captive` → `free.radial` (default, preserves bit-exact backwards-compat — verified existing code reads `prof.free.radial`/`prof.free.axial` at `nuts/metric.py:62`). `press` → `press.radial` is the correct mapping. See condition C3 on user-visible delta-on-switch.

### Conditions (must address before APPROVE)
- **C1** (§4 step 2 / §3 step 5): On fresh-profile creation triggered by `slip.radial` calibration, the fresh entry's `slip.slot` resolves to 0.0 — not the shipped `fdm_standard.slip.slot=0.10`. Either (a) seed `slot` from `_FALLBACK_PROFILES[fdm_standard]` when creating a fresh entry that touches the `slip` grade, or (b) leave fall-through (preserves "diff from defaults" invariant) and add an explicit line to the success block in §6: *"Note: this fresh profile's `slip.slot` will resolve to 0.0 (not the shipped fdm_standard 0.10); calibrate via the existing `AxleCrossHoleGauge` if your printer needs the narrow-slot relief."* Recommend (b) — preserves the §4 invariant and keeps the helper minimal; surfaces the gap in the user-facing block where the user can act on it.
- **C2** (§4 ¶2): Replace "deliberately matched to `fdm_standard.fdm_standard`'s shipped values" with "match `fdm_standard` for `radial`/`axial`; `slot` falls through to 0.0 — the shipped 0.10 on `fdm_standard.slip.slot` is **not** inherited by a fresh user-named profile entry, see C1." Doc-only fix.
- **C3** (§5 docstring): Add one-line note that switching a previously-captive nut consumer to `fit="press"` changes the inflation source from `free.radial` (loose) to `press.radial` (tight); pre-calibration the difference is ~0.11 mm per side on `fdm_standard` (0.15 vs 0.04). First-time press-fit users should expect "tight on first print" until calibrated.

### Open concerns (non-blocking, predicted-cost in domain units)
- **OC1** (§5 T5 backwards-compat): `CaptiveNutPocket` signature change from `(width_flats, depth, profile)` to `(width_flats, depth, radial_allowance, axial_allowance)` — verify no external caller imports `CaptiveNutPocket` directly. Predicted cost if missed: 1 import-error at one site, caught immediately by full test suite (zero print cost).
- **OC2** (`MThreeNutPocketGauge` sweep step): 0.10 mm steps × ±0.30 mm range gives 6 pockets; press-fit discrimination on FDM is typically 0.05 mm-band — user may report "two adjacent pockets both feel press-fit." Predicted cost: 0–1 extra calibration cycles per knob; recoverable in v2 with finer sweep (FR11 reads live so no helper edit needed).

### Verification log
- Read `_FALLBACK_PROFILES` (`print_settings.py:628-646`): confirmed `fdm_standard.slip.slot=0.10`, `_fitgrade_from_dict default_slot=0.0` — mismatch is the basis for C1+C2.
- Read `_fitgrade_from_dict` (`print_settings.py:338-359`) + `_profile_from_nested` (`:362-375`): confirmed `slot` defaults to 0.0 for every grade.
- Read `MetricMachineScrew.to_cutter` (`screws/metric.py:132-172`) + `METRIC_SIZES["M3"]["clearance"]=3.2` (`:23`): confirmed `free.radial` consumption via `CounterboreHole`.
- Read `TechnicAxleHole.__init__` (`lego/cutters/technic_axle_hole.py:91-122`): confirmed `slip.radial` × 2 inflation of `AXLE_HOLE_TIP_TO_TIP=4.80` (`lego/constants.py:91`) — matches §1 forward/inverse formula.
- Read `MetricHexNut.to_cutter` current (`nuts/metric.py:57-69`): confirmed reads `prof.free.radial` / `prof.free.axial` via `CaptiveNutPocket(self.width_flats, self.thickness + depth_allowance, prof)` — default-captive backwards-compat path in T5 refactor is achievable.
- Read `MetricHexNut.DIMENSIONS["M3"]["width_flats"]=5.5` (`nuts/metric.py:28`): confirmed nominal source live.

**Re-confirmed 2026-05-25:** conditions 1/2/3 applied; verdict upgraded to APPROVE.

---

## Implementation Status
<!-- Populated by #developer at the start of Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: **266 passed, 2 xfailed** (full `pytest tests/ -v` on the dev-container baseline). New tests added by this PR: 23 in `tests/tools/test_calibrate.py`, 8 in `tests/mechanical/test_calibration_gauges.py`, 3 in `tests/mechanical/test_metric_nut.py` = 34 net-new; regression-baseline `tests/test_cutter_overcut.py` (24) + `tests/test_protocols.py` (67 incl. parametrised) pass byte-identically to pre-Option-A baseline.
- [x] No new linter / static-check errors (`flake8` clean on all changed files; `tools/check_license_headers.py`, `tools/check_no_main_blocks.py`, `tools/check_topology.py` on both new gauges all green; `tools/gen_engine_api.py --check` clean after regen — diff is purely additive: two new gauge class entries, zero changes to `MetricHexNut`).
- Developer note: Option-A refactor preserved `CaptiveNutPocket` byte-exact (T24/T25 confirm `fit='captive'` default path produces identical geometry; `fit='press'` path correctly routes through the synthesised per-call `ToleranceProfile(name=...)`). Stage-2b `slip.slot` floor surfaced as a success-block note for fresh `slip` writes (NOT seeded) per Domain Expert C1. One pragmatic deviation from the design's stated test inputs: tests T3/T6/T8/T13/T14 use sweep-valid diameters (3.30, 3.50, 5.60) rather than the design's illustrative 3.56 — the design's Q3-strict-sweep validation correctly rejects 3.56. `_compute_radial` rounds to 4 dp to avoid the binary-float `0.05 → 0.04999...` artefact in the persisted JSON; physical meaning is unchanged (sweep tuples are 0.01-mm-quantised). Visual-contract SVGs regenerated directly in Phase A (Step-3 probe artefacts skipped — same outcome reached more directly).

### Follow-up 1 — Phase C concern application (2026-05-25)

Applied the three open concerns raised by the Phase-C Independent Domain Expert review inline on this branch (pre-PR-open), per the `vibe/INSTRUCTIONS.md` §5 *PR-Review Follow-ups — Address Inline in Same PR* rule. Sealed Phase B/C reviewer sections left untouched.

- **OC1 — Test coverage for the `slip.slot → 0.0` warning.** Added two tests in `tests/tools/test_calibrate.py`:
  - `test_slip_fresh_profile_emits_slot_warning` — positive: calibrating `slip` against a fresh profile name surfaces `slip.slot`, `0.0`, and `fdm_standard` in the post-write success block. Locks down the load-bearing Stage-2b surface-not-seed contract so a future `_render_success` refactor cannot silently drop the warning.
  - `test_slip_existing_profile_does_not_emit_slot_warning` — negative: the substring `slip.slot` is absent from the success block when calibrating against an existing profile that already carries a `slip.slot` value.

- **OC2 — `calibrate.py all` surfaces the slot-gap warning on fresh-profile creation.** Added an end-of-session emitter in `tools/calibrate.py:main()` (post-loop, ~50 LOC) that fires when (a) `slip` was NOT part of the session's knob sequence, (b) the profile name was freshly created by this session (snapshotted before the loop runs so an intermediate write does not mask freshness), and (c) the post-write entry has no `slip.slot` value. The wording adapts the slip-mode warning to surface that *no `slip` calibration was performed this session* and suggests running `python3 tools/calibrate.py slip --gauge axle` or copying `"slot": 0.10` from `fdm_standard`. Two tests cover it in `tests/tools/test_calibrate.py`:
  - `test_all_mode_fresh_profile_emits_slot_warning` — positive: `all` mode against a fresh profile name emits the end-of-session block with `slip.slot`, `0.0`, and `fdm_standard` references. Drives the two-knob loop via a monkey-patched `_prompt_diameter` so each knob gets a sweep-valid diameter from its own gauge tuple.
  - `test_all_mode_existing_profile_does_not_emit_slot_warning` — negative: even when an existing profile lacks `slip.slot`, the end-of-session warning does NOT fire — surfacing is gated on fresh-profile-creation-by-this-session, not on the post-write state alone (so a contributor re-running `all` against a dialled-in profile sees no unsolicited noise).

- **OC3 — Type-narrow at `vibe_cading/mechanical/nuts/metric.py:107-112`.** Inserted a 6-LOC type-narrow at the top of `to_cutter`: if `profile` is `None` or `str`, resolve it via `get_profile(profile)` before the synthesis path dereferences `prof.press`. This makes `fit="press"` accept the same `profile` shapes that `fit="captive"` already accepts (None / str / `ToleranceProfile`). Test added in `tests/mechanical/test_metric_nut.py`:
  - `test_to_cutter_press_fit_accepts_str_profile_name` — asserts `MetricHexNut.from_size("M3").to_cutter(profile="fdm_standard", fit="press")` does not raise and produces non-degenerate geometry (bbox xlen / ylen / zlen all > 0).

**Verification after follow-up application:**
- `flake8` on all 4 changed files: clean.
- `python3 -m pytest tests/` → **273 passed, 2 xfailed** (268 baseline + 5 net-new).
- Regression check `python3 -m pytest tests/test_cutter_overcut.py tests/test_protocols.py` → 91 passed + 2 xfailed (byte-identical to the pre-follow-up baseline; OC3 type-narrow is additive on the `fit="press"` path and the regression suite exercises `fit="captive"` defaults only).
- Strict-ops `tools/check_license_headers.py` + `tools/check_no_main_blocks.py`: both green.

No commit performed by Developer per task instructions; PM commits after re-verification.

### Follow-up 2 — PR #10 review inline tightening (2026-05-25)

Applied a single surgical fix on this branch (pre-merge) in response to a PR-review concern that the `--yes` help text overpromised relative to the implementation. Per the `vibe/INSTRUCTIONS.md` §5 *PR-Review Follow-ups — Address Inline in Same PR* rule.

- **Concern.** The `--yes` flag help text at `tools/calibrate.py:866-868` advertised that fresh non-shipped profile names *also require* `--profile`, but the FR20 guard inside `_run_one_knob` only **skipped the interactive prompt** for the `--yes + --profile` combination — it did NOT **error** when `--yes` was set, the resolved name was fresh AND non-shipped, AND `--profile` was absent. Net effect: a `VIBE_PRINT_PROFILE` env-var typo combined with `--yes` would silently create a stray entry; the documented contract said "this can't happen", the implementation allowed it.
- **Fix.** Inserted a single-point hard guard at the top of `main()` (post-`_resolve_active_profile_name`, post-`pre_session_raw` snapshot, pre-knob-loop) that fires when ALL of: `args.yes` set, `args.profile` unset, resolved name not in `pre_session_raw` (fresh), and resolved name not in `_SHIPPED_PROFILE_NAMES`. Prints a stderr `ERROR:` block naming the resolved profile, suggesting the corrective `--profile <name>` flag verbatim, identifying the resolution source, and returns exit code 2. Short-circuits before any per-knob prompting (single enforcement point, not per-knob). Help text wording was already accurate end-to-end and required no change.
- **Tests added in `tests/tools/test_calibrate.py`:**
  - `test_yes_fresh_env_profile_blocked_without_explicit_profile` — positive: env-var typo `bumbu_p1s__test_typo` + `--yes` (no `--profile`) → non-zero exit, stderr contains `ERROR:` + the typo'd name + the suggested `--profile bumbu_p1s__test_typo` flag, `_USER_FILE` is NOT created (guard fired before any write).
  - `test_yes_with_explicit_profile_creates_fresh_entry` — negative control: same env-var typo + `--yes` but with `--profile bambu_p1s__pla_real` explicitly passed → run proceeds normally and the explicitly-named entry is created (guard does not over-trigger when `--profile` confirms intent).
  - `test_yes_resolves_to_shipped_default_proceeds` — negative control: `--yes`, no env var, no `--profile` → resolves to `fdm_standard` (shipped) → run proceeds and `fdm_standard` entry is created (`_SHIPPED_PROFILE_NAMES` exemption works).
- **Test-suite updates.** Adjusted pre-existing `test_active_profile_resolution` (T18) to seed `_USER_FILE` with the env-resolved `myprinter__pla` entry before the run, so the test's intent (verifying env-var resolution end-to-end) is preserved without colliding with the new FR20 guard. T19 / T20 / T16 already either pass `--profile` or use a shipped name and remain unchanged.

**Verification after follow-up application:**
- `flake8 tools/calibrate.py tests/tools/test_calibrate.py`: clean.
- `python3 -m pytest tests/` → **276 passed, 2 xfailed** (273 baseline + 3 net-new).
- Regression check `python3 -m pytest tests/test_cutter_overcut.py tests/test_protocols.py` → 91 passed + 2 xfailed (byte-identical to pre-follow-up baseline; the guard touches only the CLI entry-flow on a previously-allowed-but-typo-prone path, no model geometry).
- `tools/check_license_headers.py` + `tools/check_no_main_blocks.py`: both green.

No commit performed by Developer per task instructions; PM commits after re-verification.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes (fresh-context independent TL, 2026-05-25):

**Verdict: PASS.** Implementation faithfully realises the design across architecture, contracts §1–§7, FR coverage, Option-A refactor scoping, and strict-ops. All 28 designed tests + 6 incidental tests pass; regression baseline (`tests/test_cutter_overcut.py` + `tests/test_protocols.py`) is 91 passed + 2 xfailed, byte-identical to pre-PR baseline. Option A is honoured exactly — `vibe_cading/mechanical/holes.py` and the two regression test files are untouched vs `origin/main`; engine_api.json diff is purely additive (88 LOC, two new gauge entries only, zero changes to `MetricHexNut` or `CaptiveNutPocket`).

**Verification log — Implementation Plan spot-checks (5+):**
- T1 `vibe_cading/mechanical/calibration/__init__.py:1-39` → AGPLv3 header + sub-package docstring + re-exports both gauges. PASS.
- T2 `m3_clearance_gauge.py:112-120` → live nominal guard `METRIC_SIZES["M3"]["clearance"]` enforced at `__init__`. T22 covers. PASS.
- T3 `m3_nut_pocket_gauge.py:125-133` → analogous live nominal guard against `MetricHexNut.DIMENSIONS["M3"]["width_flats"]`. PASS.
- T5 `nuts/metric.py:107-112` → `fit="press"` synthesises `ToleranceProfile(name=..., free=prof.press, slip=prof.slip, press=prof.press)`; `fit="captive"` branch is `effective = prof` (bit-exact). `holes.py` git-diff vs origin/main is empty — Option A scope honoured. PASS.
- T8 `calibrate.py:316-356` → tempfile name `<path>.tmp.<pid>.<knob>`, fsync, `os.replace`, cleanup glob. T10 crash-inject covers. PASS.
- T9 `calibrate.py:141-195` → CadQuery + gauge imports lazy-loaded inside `_load_knob_runtime`. PASS.

**Verification log — Contracts §1–§7:**
- §1 formula: `calibrate.py:202-212` `_compute_radial = round((D-N)/2, 4)`. Nominal imports at `:148, :166, :182` resolve through the cited source files. PASS.
- §3 atomic write: `_atomic_write_json` uses canonical `json.dumps(..., indent=2, sort_keys=True)` (`:295-299`). PASS.
- §4 surface-not-seed: `_render_success` `:566-576` surfaces the `slip.slot → 0.0` gap; no seeding logic anywhere. Domain-Expert C1 fix correctly applied. PASS.
- §5 Option A: confirmed `CaptiveNutPocket.__init__/.solid/.to_cutter` byte-identical via `git diff origin/main..HEAD -- vibe_cading/mechanical/holes.py` returning empty; default `fit="captive"` path = identity pass-through of `prof`. PASS.
- §6 wire format: `_render_preview` `:451-535` matches the documented template (target / change / derivation / migration / consumers / footer). PASS.

**Verification log — Success Criteria 1–9:**
- SC1 (all designed tests pass) — 34 net-new tests PASS, regression 91+2xfail. PASS.
- SC2 (`--help` < 2s) — `time` reports 0.042s. PASS (50× headroom).
- SC3 (`--help` imports zero CadQuery) — `python3 -X importtime ... | grep -c cadquery` returns 0. PASS.
- SC4 (end-to-end propagation) — manually ran `calibrate.py free --diameter 3.30 --yes --profile test_tl_smoke`, then `get_profile("test_tl_smoke").free.radial == 0.05`. PASS.
- SC5 (CI gates) — `check_no_main_blocks.py`, `check_license_headers.py`, `flake8` on all changed files, `check_topology.py` on both gauges all green. PASS.
- SC6 (build.toml not modified) — `git diff HEAD -- build.toml` empty. PASS.
- SC7 (visual-contract SVGs committed) — both `_m3_clearance_iso_ne.svg` and `_m3_nut_pocket_iso_ne.svg` present in `.agents/plans/` and embedded at design `:58-60`. PASS (see open concern OC1 on size).
- SC8 (README "is on the roadmap" replaced) — README diff replaces the line with a live `tools/calibrate.py` reference + knob table. PASS.
- SC9 (`MetricHexNut.to_cutter` backwards-compat) — covered by T25 + regression baseline (`tests/test_protocols.py` exercises `.to_cutter` paths) all green. PASS.

**Scope policing.** `git status` shows exactly the design's Touchpoint inventory: 2 modified (`engine_api.json`, `nuts/metric.py`) + 1 README + 6 net-new artefacts (helper, sub-package init + 2 gauges, 3 test files, 2 SVGs). No out-of-scope edits. Developer's two self-reported deviations (sweep-valid test diameters; `round(...,4)` for binary-float artefact in `_compute_radial`) are both inside `tools/calibrate.py` / tests scope and architecturally justified (the round-to-4dp is documented in the docstring `:205-211`). PASS.

**Namespace smoke.** `from vibe_cading.mechanical.calibration import MThreeClearanceGauge, MThreeNutPocketGauge` + existing `mechanical.nuts`, `mechanical.screws`, `mechanical.holes` co-import cleanly. PASS.

**Open concerns (non-blocking, predicted cost-of-failure included):**

- **OC1 (SVG size).** `_m3_clearance_iso_ne.svg` = 404 KB; `_m3_nut_pocket_iso_ne.svg` = 275 KB. Project guidance suggests "~10-25 KB each", but live precedent already shows similar sweep-gauge SVGs in the 78-251 KB range (`2026-05-20-axle-hole-tip-to-tip-gauge_design_iso_ne.svg` = 78 KB, `2026-05-15-lego-technic-beam_design_iso_ne.svg` = 251 KB). Root cause: 7-pocket / 6-pocket sweep with engraved labels produces many tessellated path elements in iso projection. **Verdict: accept as-is, defer to a future cleanup.** Rationale: (a) the SVGs serve the visual-contract purpose (axis convention + hole/pocket pattern + label band visible) and are diffable as XML; (b) the 25 KB ceiling in the guidance text predates the gauge-style multi-variant SVGs and was never re-baselined; (c) fix-now would balloon this PR with rendering-engine investigation. **Predicted cost if deferred:** ~600 KB total repo bloat per gauge design (~once per quarter); diff size on the SVG itself remains tractable since OCCT projects deterministically. **Recommended follow-up TODO row:** "investigate `cq.exporters.export` SVG size for sweep-style calibration gauges; either render a single-variant preview as the visual contract or tune the projection tolerance." Not blocking this PR.

- **OC2 (`_render_success` branch reuse).** `calibrate.py:577-591` re-uses the `fresh_profile_with_slip_only` boolean (misnamed) as a generic "fresh profile, other knobs uncalibrated" signal for the `free`/`press` paths. The comment at `:578-581` flags this as intentional. **Predicted cost if it confuses a future contributor:** ~10 min of grep/rename refactor; zero user-facing impact. Acceptable as v1 cosmetic debt; rename in a follow-up touch-up commit if a contributor opens it.

- **OC3 (lazy import of `ToleranceProfile`).** `nuts/metric.py:89-92` imports `ToleranceProfile` inside `to_cutter` per call rather than at module scope. Idiomatic for the synthesis path (avoids circular-import risk) and consistent with the pre-existing in-method import of `get_profile`. **Predicted cost:** zero — Python caches the import after first call. No action.

**No conditions / required edits.** PASS.

### Domain Expert Review *(YES gate — required)*
- [x] **Domain expert sign-off** — calibration formula §1, propagation §2, atomic semantics §3, creation-flow §4, Q6 refactor §5, preview format §6, migration ordering §7 all verified against implemented code
- Domain expert review notes (fresh-context Designer-as-domain-expert, 2026-05-25):

**Verdict: PASS.** Every tolerance-domain invariant the design promised is preserved by the implemented code. The gauge↔knob mapping is 1-to-1 and correct across all three knobs; the calibration formula `(D−N)/2` is applied uniformly with the correct sign convention (smaller `D` ⇒ negative `radial` ⇒ tighter consumer geometry, which the press path needs and gets); nominals are read live from the source-of-truth constants and asserted at gauge `__init__`; propagation lands at the right consumer reads (`free.radial` → `MetricMachineScrew.to_cutter` via `CounterboreHole`, `press.radial` → `MetricHexNut.to_cutter(fit="press")` via a synthesised per-call `ToleranceProfile`, `slip.radial` + `slip.slot` → `TechnicAxleHole.__init__`); the Stage-2b surface-not-seed contract is honoured (no auto-seed of `slip.slot=0.10`, success block surfaces the resolved 0.0 gap); the Option-A refactor preserves `fit="captive"` byte-exact backwards compatibility through the identity-pass-through `effective = prof` branch; and the fresh-profile-creation flow writes only the calibrated leaf, preserving the diff-from-defaults invariant.

**Verification log (7 questions):**

1. **Gauge↔FitGrade mapping — PASS.** `tools/calibrate.py:141-194` `_load_knob_runtime`: `free` → `MThreeClearanceGauge` writes `grade="free", field="radial"`; `press` → `MThreeNutPocketGauge` writes `grade="press", field="radial"`; `slip` → `AxleHoleGauge` writes `grade="slip", field="radial"`. No cross-routing possible — `_run_one_knob:680-682` plumbs `rt.grade`/`rt.field` directly into `_build_after_entry`.
2. **Formula sign + factor — PASS.** `calibrate.py:202-212` `_compute_radial = round((D−N)/2, 4)` is uniform across all three knobs (single helper, no per-knob branch). Press sign verified: smaller pocket `D` < nominal `N` ⇒ negative `radial` ⇒ `CaptiveNutPocket.to_cutter` at `holes.py:440` reads `tol.free.radial` (which is the synthesised `prof.press` slot) ⇒ `r_inscribed = WAF/2 + (negative)` ⇒ pocket *shrinks* ⇒ interference grip. Sign physically correct. The `round(..., 4)` is a binary-float artefact mitigation, not a semantic change — documented in the docstring `:204-211`. Nominals imported live at `:148, :166, :182` and asserted in gauge `__init__` (`m3_clearance_gauge.py:112-120`, `m3_nut_pocket_gauge.py:125-133`).
3. **Cross-model propagation — PASS.** `screws/metric.py:160-171` reads `prof = profile or get_profile()` then plumbs to `CounterboreHole(profile=prof)` which consumes `tol.free.radial` (`holes.py:158, 165`). `nuts/metric.py:89-127` `fit="captive"` branch passes `prof` unchanged ⇒ `CaptiveNutPocket` reads `free.radial` (`holes.py:440`); `fit="press"` synthesises `ToleranceProfile(free=prof.press, ...)` so the same read site now resolves to `press.radial`. `technic_axle_hole.py:107,114,120` reads `getattr(profile, fit).radial` and `.slot` — `fit="slip"` (default) consumes `slip.radial` + `slip.slot`. All three named consumers verified to land on the calibrated leaf with no source edit.
4. **Stage-2b `slip.slot` SURFACE-not-SEED — PASS with one open concern.** `calibrate.py:566-576` `_render_success` surfaces the `slip.slot → 0.0` gap when a fresh profile gets a `slip.radial` calibration without a sibling `slot`. No auto-seed anywhere (grepped `calibrate.py` for `slot` literal — only the warning text). Diff-from-defaults invariant preserved. **Open concern: no test asserts the warning text is actually printed** — T26 only counts bullet lines in the success block. See OC1.
5. **Profile-creation flow domain-correctness — PASS.** `calibrate.py:268-280` `_build_after_entry` writes only `entry[grade][field] = value` — uncalibrated grades/fields are absent. Verified `_resolve_target_entry:239-255` returns `({}, False)` for missing profile names, so the new entry contains exactly one leaf. The diff-from-defaults invariant means `_deep_merge_profiles` at read time fills uncalibrated siblings via `_fitgrade_from_dict`'s `default_radial`/`default_axial` per-grade defaults (`print_settings.py:366-374`).
6. **`MetricHexNut.to_cutter` backward-compat — PASS.** `nuts/metric.py:94-98` `fit="captive"` branch is `effective = prof` — identity pass-through. `CaptiveNutPocket(width_across_flats, thickness, prof)` then reads `tol.free.radial` via the unchanged `holes.py:440` site. Pre-refactor callers got `free.radial`; post-refactor default-captive callers get `free.radial`. T25 (`test_metric_nut.py:47-67`) asserts a profile with `free.radial=0.1, press.radial=1.0` produces a default-call pocket inflated by `0.1`, not `1.0` — confirms `free` not `press` is consumed in the default path.
7. **Cross-knob domain blast radius — PASS with one substantive concern.** `calibrate.py:908-911` `all` mode runs `["free", "press"]` only (slip excluded by design). For a fresh profile after `all`: the user file ends with `{"<name>": {"free": {"radial":X}, "press": {"radial":Y}}}`. On next `get_profile("<name>")`: name is in `profiles` (user wrote it), so `_profile_from_nested(name, data)` runs (`print_settings.py:678-679`) — `data.get("slip", {})` returns `{}`, then `_fitgrade_from_dict({}, default_radial=0.05, default_axial=0.0, default_slot=0.0)` resolves to `slip=FitGrade(0.05, 0.0, 0.0)`. So **`slip.slot = 0.0`, not the shipped 0.10**. This is the Stage-2b regression the §4 surface-not-seed contract was designed to flag — but the `all` run NEVER calls the slip knob, so the success-block warning at `calibrate.py:566-576` never fires. A contributor running `calibrate.py all` silently loses the conservative narrow-slot floor for any downstream `TechnicAxleHole` consumer on that profile. The design acknowledges this implicitly (§4 footnote) but the implementation has no surfacing for the `all` path. See OC2.

**Open concerns (non-blocking, predicted-cost in domain units):**

- **OC1 — No test asserts the slip-fresh-profile slot warning text is printed.** T26 (`test_success_block_lists_consumers`) only counts `  - ` bullet lines. The success-block `slip.slot → 0.0` note at `calibrate.py:566-576` is a load-bearing Stage-2b surface-not-seed contract — a future refactor of `_render_success` could silently drop the warning and no test would catch it. **Predicted cost if it regresses:** silent loss of narrow-slot floor for every fresh-profile contributor who calibrates `slip` after the regression; downstream `TechnicAxleHole` (≥1 consumer in the library, more in user assemblies) prints tighter than intended ⇒ axle binds. ~1 lost print cycle per affected contributor + debug time to trace. Mitigation: add a one-line assert to T26 (or a new test row) that the substring `"slip.slot"` AND `"0.0"` appear in the success block when knob is `slip` and the entry has no pre-existing slot.

- **OC2 — `all` sequence does not surface the `slip.slot=0.0` gap for fresh profiles.** A contributor running `calibrate.py all` against a fresh user-named profile (e.g. `bambu_p1s__pla_overture`) writes `free.radial` + `press.radial` only; `slip.slot` silently resolves to 0.0 (not the shipped 0.10) for every downstream `TechnicAxleHole` consumer on that profile. Domain blast radius: every Lego-compatible part with an axle hole in the user's library — typically 5–20 model classes on a working RC/Lego project. **Predicted cost if it bites:** 1–N tight axle holes across a print batch; recoverable by either running `calibrate.py slip` (which DOES surface the warning) or by adding `"slot": 0.10` manually to the user file. Acceptable for v1 because the regression is recoverable and the `slip` opt-in path does carry the warning, but a future v2 refinement should extend `_render_success` to surface the slot gap whenever ANY fresh-profile write completes without a `slip.slot` value present — not just the `slip` knob.

- **OC3 — `CaptiveNutPocket.tolerance` property branches on `isinstance(self._profile, str)` (`holes.py:415-419`).** Under the Option-A synthesis at `nuts/metric.py:107-112`, `effective` is always a `ToleranceProfile` instance (never a string), so the synthesis path lands in the `return self._profile` branch and works correctly. But if a future caller passes `fit="press"` AND `profile="press_profile_name"` (a string), the synthesis at `:108-112` would fail because `prof.press` would dereference an attribute that doesn't exist on a string. **Predicted cost:** zero today (no caller passes a string profile name to `MetricHexNut.to_cutter`); ≥1 confusing `AttributeError` if a future user does. Mitigation: type-narrow `prof` at the top of `to_cutter` by calling `get_profile(prof)` when `isinstance(prof, str)` — 2 LOC follow-up.

**Conditions: none.** All findings are open concerns with documented predicted cost-of-failure and acceptable v1 mitigations; none rise to a domain-integrity blocker. The implementation faithfully realises the design's domain contracts §1-§7.

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:

---

## Independent Developer Review (fresh context, 2026-05-25)

**Verdict:** APPROVE

### Strengths
1. **Calibration formula §1** is fully derivable from the design alone — each knob's nominal is cited with file:line, the import block is spelled out verbatim, and the forward/inverse formulas are stated symbolically AND with worked numbers (3.30 → 0.05).
2. **Profile-creation flow §4** explicitly resolves the "what fills uncalibrated fields" question — the design walks through `_fitgrade_from_dict`'s hardcoded defaults (`free.axial=0.20, slip.radial=0.05, press.radial=0.04`), names them, AND notes the risk in Known Risks R1 with a defensive assertion test. No "figure out defaults" gap.
3. **Tests table** is exceptionally concrete — 28 rows with assertion-level granularity, including crash-injection (T10), checksum-byte-identity (T7), and the load-bearing propagation smoke (T14). All rows map to FRs; all rows describe an observable a Developer can write today.

### Conditions
- **C1 — Refactor LOC count is misleading. Design §5 / Q6 / R3 / T5 all call the `MetricHexNut.to_cutter` change a "5-LOC refactor"; in reality it touches `MetricHexNut.to_cutter` (~10 LOC for the new branch + docstring) PLUS `CaptiveNutPocket.__init__` (signature change from `(width_flats, depth, profile)` to `(width_flats, depth, radial_allowance, axial_allowance)`) PLUS `CaptiveNutPocket.solid` AND `CaptiveNutPocket.to_cutter` bodies (lines 405–447 of `holes.py` — they currently read `self._profile`/`tol.free.radial` directly). Realistic count is ~30–40 LOC across two files. Not a blocker — every change is mechanical and the test surface (T24 / T25) covers it — but the LOC framing in §5 / R3 understates the surface and a Developer who plans against "5 LOC" will miss the `CaptiveNutPocket` cascade. **Required edit (design §5, around line 188):** restate as "~30 LOC across `MetricHexNut.to_cutter` and `CaptiveNutPocket` (constructor + `solid` + `to_cutter`)" and add a one-line note that `CaptiveNutPocket`'s public constructor signature changes (potential external-consumer breakage — minimal blast radius since grep shows no in-tree caller passes `profile` positionally to `CaptiveNutPocket(...)`).

### Open Concerns (non-blocking, with predicted cost-of-failure)
- **O1 — Test T28 grep pattern is regex-invalid as written.** Row 28 uses Python-style negative lookahead `(?!...)` against `grep -E`; POSIX ERE does not support lookahead. Implementer will discover at test-write time and convert to a positive-allowlist `grep -v` chain or a Python AST check. Predicted cost: 15 min refactor at implementation; zero downstream cost.
- **O2 — T15 (interactive profile-name confirmation) requires stdin simulation infrastructure.** The design doesn't specify whether to use `monkeypatch` on `builtins.input`, `pexpect`, or a sentinel `--input-stream` flag. Implementer will pick `monkeypatch.setattr("builtins.input", ...)` — the obvious choice — but the design could pre-empt the question. Predicted cost: 10 min decision time; zero blast radius.
- **O3 — T13 SVG regeneration writes into `.agents/plans/` via `--out`.** `tools/preview.py` writes named-by-class SVGs (`MThreeClearanceGauge_iso_ne.svg`) — the rename to `2026-05-23-calibration-helper-generic_design_m3_clearance_iso_ne.svg` must be a manual `mv` post-export, which the design implies but doesn't spell out. Predicted cost: 2 min if the developer notices; one regenerated-but-mis-named SVG in `.agents/plans/` if not. Trivial.

### Verification log

| Check | Claim | Result |
|---|---|---|
| Code: M3 clearance nominal | design §1: `METRIC_SIZES["M3"]["clearance"] = 3.2 mm` at `screws/metric.py:23` | `screws/metric.py:23` → `"M3": {..., "clearance": 3.2, ...}` — VERIFIED |
| Code: M3 nut width-flats | design §1: `MetricHexNut.DIMENSIONS["M3"]["width_flats"] = 5.5 mm` at `nuts/metric.py:28` | `nuts/metric.py:28` → `"M3": {"thread_diameter": 3.0, "width_flats": 5.5, "thickness": 2.4}` — VERIFIED |
| Code: AXLE_HOLE_TIP_TO_TIP | design §1: `AXLE_HOLE_TIP_TO_TIP = 4.80 mm` at `lego/constants.py:91`, plain float | `lego/constants.py:91` → `AXLE_HOLE_TIP_TO_TIP: float = 4.80` — VERIFIED |
| Code: `MetricHexNut.to_cutter` current signature | design §5: "current method (lines 57–69) reads `prof.free.radial` via `CaptiveNutPocket` indirection" | `nuts/metric.py:57` → `def to_cutter(self, profile = None)`; line 64 → `CaptiveNutPocket(self.width_flats, self.thickness + depth_allowance, prof)`; `CaptiveNutPocket.to_cutter` at `holes.py:431` reads `tol.free.radial` line 440 — VERIFIED (and shows the refactor reaches into `CaptiveNutPocket`'s body, not just `MetricHexNut`; see C1) |
| Code: `MetricHexNut.to_cutter` caller blast radius | implied by R3 ("backwards-compat assumption"): how many call sites? | grep across `vibe_cading/`, `parts/`, `tests/` for `MetricHexNut(...).to_cutter(` / `hex_nut.to_cutter(` / `nyloc.to_cutter(` returns **zero** in-tree callers (only the class's own `demo()` references it via `.solid`, not `.to_cutter`). `MetricNylocNut` inherits but `to_cutter` is never called on it either. The refactor is effectively call-site-safe; T25 covers the one geometry-shape regression. VERIFIED — risk is even lower than the design implies. |
| Code: foundation helpers cited | design Architecture §"Approach chosen": uses `get_default_profile_name`, `_is_legacy_flat_entry`, `_migrate_flat_to_nested`, `_deep_merge_profiles` | `print_settings.py` → `get_default_profile_name` line 225; `_is_legacy_flat_entry` line 302; `_migrate_flat_to_nested` line 311; `_deep_merge_profiles` line 406 — all VERIFIED with the cited signatures |
| Math spot-check | design §1: `free.radial = (D − N) / 2`, N=3.2; helper imports nominal from `METRIC_SIZES["M3"]["clearance"]` | Derivable from design alone (no out-of-band lookup needed); `_NOMINAL_FREE_RADIAL = float(METRIC_SIZES["M3"]["clearance"])` import shown at design §1 line 110 — VERIFIED |
| Test runnability spot-check | T3 (creates user file), T4 (formula), T14 (propagation) | All three describe a `pytest` assertion with concrete pre-state, command, post-state — directly writable from the table. VERIFIED |
| Atomic-write spec | design §3: tempfile + fsync + `os.replace`, tempfile name `<path>.tmp.<pid>.<knob>` | Spelled out in §3 step 7 with 8-step flow; T8 task names the helper `_atomic_write_json(path, data, knob)`; T10 covers the crash-injection — IMPLEMENTABLE-DIRECTLY |
| Change-preview spec | design §6: exact wire format with conditional lines | Full template provided lines 217–249, with conditional-line documentation immediately following — IMPLEMENTABLE-DIRECTLY |
| Gauge classes preview-ready | T2 / T3 specify constructor signatures with defaults (`diameters=DEFAULT_DIAMETERS, depth=8.0, ...`) | Both classes ship default-args for every parameter → `python3 tools/preview.py vibe_cading.mechanical.calibration.m3_clearance_gauge.MThreeClearanceGauge --views iso_ne` is runnable post-impl with no `--params`. VERIFIED |
| Profile-creation defaults | design §4 step 2: spells out which uncalibrated values fill the new entry | §4 step 2 explicitly names the `_fitgrade_from_dict` hardcoded defaults (`free.axial=0.20, slip.radial=0.05, press.radial=0.04`) AND clarifies that NO inheritance from `fdm_standard` happens for unknown user profile names. No gap. VERIFIED |
| No new dependencies | T28 + FR30 require stdlib + `vibe_cading` only; imports cited in §1 are `vibe_cading.mechanical.screws.metric`, `vibe_cading.mechanical.nuts.metric`, `vibe_cading.lego.constants` | All in-tree. T9 lazy-imports CadQuery. VERIFIED — no third-party imports anywhere in the spec. |

---

## Independent TL Review (fresh context, 2026-05-25)

**Verdict:** APPROVE

### Strengths
1. **Data & Interface Contracts §§1–7 close the YES-gate failure modes.** The formula+inverse table (§1) with sign convention, the live-source nominal-import block, and the cross-model propagation contract (§2) naming 3+ verified consumers per knob are unambiguous and load-bearing. §4's freshly-created-profile inheritance walkthrough is the one part of the spec a Developer could most easily misimplement; it is spelled out concretely against the live `_fitgrade_from_dict` defaults.
2. **FR coverage and Q-resolution are greppable and complete.** All 30 FRs → Tests-table rows (verified by counting `FR<n>` references against the req's 30 FRs). Q1, Q4, Q6, Q7 each carry an explicit dialog round; Q2 resolution is in Architecture §"Subcommand layout"; Q3, Q5, Q8, Q9 batched in Round 5 with concrete decisions. No Q is left "TBD."
3. **Module-depth dual-lens analysis correctly applies the contributor-extension carve-out** to the otherwise-deletable `__init__.py`, and R7 honestly defers the shared `_SweepGaugeBase` to a third exemplar rather than speculating.

### Conditions (must address before Step 4 human gate)

**C1. §5 / T5 "5-LOC refactor" estimate is materially understated; the design plan as written will break tests and the engine_api wire contract.** (Independent confirmation of the prior Developer review's C1; the issue is severe enough to surface from two reviewer lenses.) The cited refactor changes `CaptiveNutPocket.__init__` per design line 208. Verified against `vibe_cading/mechanical/holes.py:405-447`:
- Current `CaptiveNutPocket.__init__` parameter is named `width_across_flats` (not `width_flats` as design says).
- `CaptiveNutPocket` has TWO read sites of `self.tolerance.free.radial` — `.solid` (line 426) AND `.to_cutter()` (line 440) — both omitted from the design's "pure plumbing" sketch.
- Direct callers that break under the proposed signature:
  - `tests/test_cutter_overcut.py:137` — `CaptiveNutPocket(width_across_flats=5.5, thickness=2.4)` (kwarg-name rename breaks this).
  - `tests/test_protocols.py:101-102` — `{"width_across_flats": 5.5, "thickness": 2.4}` Protocol-conformance instantiation (same break).
  - `engine_api.json:1787-1788` — `CaptiveNutPocket` is a published wire-contract surface; signature change requires engine_api regeneration.
  - `vibe_cading/mechanical/nuts/metric.py:64` — the current `CaptiveNutPocket(self.width_flats, ..., prof)` call site needs updating in lockstep.

**Required design edit before Step 4** — one of: **(a)** preserve `CaptiveNutPocket`'s public constructor signature (keep `width_across_flats` and `profile` positional names; introduce the `fit` selector ONLY at the `MetricHexNut.to_cutter` layer by selecting the grade and passing a `ToleranceProfile` whose `free` slot is set to the chosen grade, OR by extending `CaptiveNutPocket.to_cutter()` with a `grade_override` kwarg); **(b)** explicitly enumerate every break site above with Tests-table rows + Implementation-Plan sub-tasks for each, and add a Success Criterion entry for `engine_api.json` regen. Honest LOC re-estimate is ~30–50 LOC across 4–5 files. The bit-exact backwards-compat claim in §5 is achievable but the sketched route does not achieve it.

**C2. §3 atomic-write step 5 "preserves siblings byte-identical" needs JSON-semantic clarification.** A user who hand-edited their `print_profiles_user.json` with custom indentation, key ordering, or trailing commas will see post-`calibrate.py` diffs even on profiles the tool did not touch (because `json.dumps` re-serialises the whole file). Add one line to §3 step 5: "byte-identical at the JSON-semantic level (`json.loads(before) == json.loads(after)` for unrelated profiles); the file is re-serialised with `json.dumps(..., indent=2, sort_keys=True)`, so handwritten formatting WILL be normalised on first write." Also add this normalisation to the `--help` text so users are not surprised by the first-write reflow. Not architecturally significant; failure mode if unaddressed is a confusing diff a user mistakes for data loss.

### Open concerns (non-blocking)

- **Q3 strict-default-sweep enforcement (`--diameter` rejects values outside the gauge's tuple, T17).** If a non-mainstream FDM printer's measured best-fit falls outside the M3-clearance ±0.30 mm bracket (e.g. a heavily over-extruding printer fitting a 2.85 mm hole), the user is blocked and forced back to manual JSON-editing. **Predicted cost if it fires:** ~15 min lost per affected contributor; recovers via the pre-Brief-#2 documented manual edit path. Low probability for M3 clearance (bracket is generous relative to typical FDM tolerance); higher for M3 nut pocket where ±0.25 mm is tighter. Acceptable for v1; a `--force-diameter` escape hatch is a clean v2 candidate.

- **T4 → T13 visual-contract probe/preview ordering.** The Designer's Step-3 probe SVG (T4) must match what the implemented class T2/T3 then produces, else the Step-4 human gate validates a probe the implementation contradicts. R6 acknowledges this with a ~5-min predicted cost; mitigation (probe via `cq.exporters.export` + T13 regeneration) is adequate. Acceptable.

- **T11 README cross-link to `docs/lego-technic.md` *Tuning Tolerances* for the slip-opt-in path is named but not pinned to a file:section.** **Predicted cost:** ~10 min docs follow-up if the cross-link is missed or stale. Acceptable as a follow-up.

### Verification log
- Read `vibe_cading/print_settings.py:225-702` — verified `get_default_profile_name` (line 225), `_is_legacy_flat_entry` (line 302), `_migrate_flat_to_nested` (line 311), `_fitgrade_from_dict` (line 338) with per-field defaults matching §4 claim, `_profile_from_nested` (line 362), `_deep_merge_profiles` (line 406, signature `(base, override, *, _path=())`), `get_profile` (line 664). All foundation helpers the design writes against exist with the cited signatures.
- Read `vibe_cading/mechanical/screws/metric.py:20-25` — `METRIC_SIZES["M3"]["clearance"] = 3.2` confirmed at line 23.
- Read `vibe_cading/mechanical/nuts/metric.py:25-69` — `MetricHexNut.DIMENSIONS["M3"]["width_flats"] = 5.5` confirmed at line 28; `to_cutter` at lines 57-69; `CaptiveNutPocket` indirection at line 63-64. Citation correct; LOC sizing wrong (see C1).
- Read `vibe_cading/mechanical/holes.py:387-447` — `CaptiveNutPocket.__init__(width_across_flats, thickness, profile)` at line 405-410; `.solid` reads `self.tolerance.free.radial` at line 426; `.to_cutter` reads `tol.free.radial` at line 440. Two read sites the design's §5 sketch omits.
- Read `vibe_cading/lego/constants.py:91` — `AXLE_HOLE_TIP_TO_TIP: float = 4.80` confirmed.
- Read `vibe_cading/lego/axle_hole_gauge.py:86-95` — `diameters: Sequence[float] = (4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00)` default; `self.diameters: tuple[float, ...]` exposed as public attribute. FR11's reliance on `.diameters` is honest.
- Grep `MetricHexNut.*to_cutter` repo-wide — no current external caller passes positional args; the `fit="captive"` default preserves backwards-compat for the `MetricHexNut.to_cutter` method itself.
- Grep `CaptiveNutPocket` — 4 caller/test sites + 1 engine_api entry; all impacted by the design's proposed constructor-signature change (see C1).
- Scope-discipline check: no req-out-of-scope items appear in the Implementation Plan (no bearing-pocket-as-default, no pin-hole, no axial-counterbore, no pluggable registry, no `ToleranceProfile` rename, no `build.toml` registration). The §5 nut refactor is explicitly in-scope per req's last out-of-scope bullet (gated on Q7 → Q7 resolved to all-in-one in Round 3).
- Strict-ops check: AGPLv3 header tasks present for `tools/calibrate.py` (FR2 → T27) and for both new gauge files (T1 covers `__init__.py`; T2/T3 cover the gauge modules — design relies on the CI gate `tools/check_license_headers.py` to enforce). Visual-contract SVGs scheduled per net-new gauge class — T4 generates initial probe SVGs at Step 3, T13 regenerates from `tools/preview.py` at Step 5A. Q9's per-gauge SVG rule is honored.

**Re-confirmed 2026-05-25:** conditions 1 (Option A) and 2 applied; verdict upgraded to APPROVE.
