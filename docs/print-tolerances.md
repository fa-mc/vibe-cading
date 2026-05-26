# Print Tolerances Reference

This document is the single reference for the project's print-tolerance taxonomy: the `FitGrade` × `{free, slip, press}` × `{radial, axial, slot}` matrix that every model class reads through [`get_profile()`](../vibe_cading/print_settings.py). It complements the [Print Tolerances & Calibration](../README.md#print-tolerances--calibration) section in the README — the README explains *what to do* (the calibration workflow), this doc explains *what each knob means and which models read it*.

All allowances are in millimeters. All values are read live from [`vibe_cading/print_settings.py`](../vibe_cading/print_settings.py) and pinned in [`tests/test_tolerance_profile.py`](../tests/test_tolerance_profile.py) T9b.

---

## 1. The Three Fit Grades: `free` / `slip` / `press`

The project models a hardware fit as one of three physical archetypes. Picking the right grade is the first decision a consumer makes; the numeric allowance is then resolved per machine via the active profile.

| Grade   | Physical semantics                                                                                                | `fdm_standard.radial` (mm) | Canonical example                                                                  |
|---------|-------------------------------------------------------------------------------------------------------------------|----------------------------|------------------------------------------------------------------------------------|
| `free`  | Loose, no-binding, passes straight through. The hole wall is *not* a working surface — the screw/peg floats.       | `0.15`                     | M3 clearance hole for a machine screw passing through a plate.                     |
| `slip`  | Snug; slides with mild friction. The hole walls *are* the contact surface — bearing seats, Lego axle sockets.      | `0.05`                     | Bearing inner-race shaft, Lego Technic cross axle slot.                            |
| `press` | Interference fit. The peg is **larger** than the nominal hole envelope so it must be hammered or firmly pressed in. | `0.04`                     | Bearing outer-race pocket, M3 hex-nut press-pocket (`MetricHexNut.to_cutter(fit="press")`). |

### Why the shipped values look the way they do

Read [`_FALLBACK_PROFILES["fdm_standard"]`](../vibe_cading/print_settings.py#L628) for the source-of-truth values:

- **`free` is three times looser than `slip`** (`0.15` vs `0.05`). A screw shank passing through a hole has all the headroom it wants — the walls are not load-bearing — so we err generously. A slip-fit bearing seat is dimensionally meaningful — the wall *is* the contact surface — so we err tight.
- **`press` is the tightest** (`0.04`). A press joint relies on interference; *adding* radial clearance defeats it. The shipped value is calibrated assuming a typical FDM `0.4 mm` nozzle's hole-shrink behavior, so the printed hole still binds. On a printer that prints holes oversize you may need `press.radial` slightly negative — calibrate with [`tools/calibrate.py press`](../tools/calibrate.py).

### Worked example (one consumer per grade)

| Grade   | Consumer call site                                       | Formula                                                       | M3 nominal | Printed diameter (`fdm_standard`) |
|---------|----------------------------------------------------------|---------------------------------------------------------------|------------|------------------------------------|
| `free`  | [`ClearanceHole.to_cutter`](../vibe_cading/mechanical/holes.py#L92) | `r = D/2 + profile.free.radial`                               | D = 3.2 mm | 3.20 + 2·0.15 = **3.50 mm**        |
| `slip`  | [`Bearing.shaft_cutter`](../vibe_cading/mechanical/bearings.py#L105) | `r = D_inner/2 + profile.slip.radial`                         | D = 5.0 mm | 5.00 + 2·0.05 = **5.10 mm**        |
| `press` | [`Bearing.outer_pocket`](../vibe_cading/mechanical/bearings.py#L81) | `r = D_outer/2 + profile.press.radial`                        | D = 10.0 mm | 10.00 + 2·0.04 = **10.08 mm**     |

(`+0.04` on a press pocket sounds like it *loosens* the joint — it does, by exactly enough that an OD-`10.00 mm` bearing presses into a `10.08 mm` printed hole rather than failing to insert at all. Recalibrate against your own printer with [`tools/calibrate.py press`](../tools/calibrate.py).)

---

## 2. The Three Allowances: `radial` / `axial` / `slot`

Each `FitGrade` carries three orthogonal numeric fields (see [`FitGrade`](../vibe_cading/print_settings.py#L259-L279)). They are independent because they map to physically distinct FDM failure modes — radial can't compensate for layer-line sag, and slot can't compensate for round-feature shrink. A consumer reads only the fields its geometry needs.

### 2.1 `radial` — half-extra-material on diameter

**What it modifies:** cross-section diameter of any round, polygonal, or width-defined feature. Half-extra-material per side: a `+0.15 mm` radial widens a hole's diameter by `0.30 mm` (or, equivalently, a shaft's diameter by `0.30 mm` when negative).

**Why it's a separate knob:** radial captures the dominant FDM error mode — wall-thickness shrink from extrusion-width overshoot on the perimeter pass. It's the knob most users actually calibrate.

**Shipped `fdm_standard` values:** `free=0.15`, `slip=0.05`, `press=0.04`.

**Consumers (sample — every `.to_cutter()` in the library reads this field):**

| Consumer                                                                                       | Grade   | Reference                                                                                        |
|------------------------------------------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------------|
| `ClearanceHole.to_cutter`                                                                      | `free`  | [`holes.py:92`](../vibe_cading/mechanical/holes.py#L92)                                          |
| `CounterboreHole.to_cutter` (shaft + head)                                                     | `free`  | [`holes.py:158`](../vibe_cading/mechanical/holes.py#L158), [`holes.py:165`](../vibe_cading/mechanical/holes.py#L165) |
| `CountersinkHole.to_cutter`                                                                    | `free`  | [`holes.py:210`](../vibe_cading/mechanical/holes.py#L210)                                        |
| `CaptiveNutPocket.to_cutter`                                                                   | `free`  | [`holes.py:269`](../vibe_cading/mechanical/holes.py#L269)                                        |
| `TaperedHole.to_cutter` (top + bottom radii)                                                   | `free`  | [`holes.py:318-319`](../vibe_cading/mechanical/holes.py#L318)                                    |
| `LipHole.to_cutter` (head + shaft)                                                             | `free`  | [`holes.py:361-362`](../vibe_cading/mechanical/holes.py#L361)                                    |
| `HexPocket.to_cutter`                                                                          | `free`  | [`holes.py:440`](../vibe_cading/mechanical/holes.py#L440)                                        |
| `MetricMachineScrew.to_cutter` (delegates to `CounterboreHole`)                                | `free`  | [`screws/metric.py:137-138`](../vibe_cading/mechanical/screws/metric.py#L137)                    |
| `MetricHexNut.to_cutter(fit="captive")`                                                        | `free`  | [`nuts/metric.py:106`](../vibe_cading/mechanical/nuts/metric.py#L106) (via `CaptiveNutPocket`)   |
| `MetricHexNut.to_cutter(fit="press")` (synthesises `prof.press` onto `effective.free`)         | `press` | [`nuts/metric.py:74`](../vibe_cading/mechanical/nuts/metric.py#L74)                              |
| `MetricSquareNut.to_cutter`                                                                    | `free`  | [`nuts/metric.py:214`](../vibe_cading/mechanical/nuts/metric.py#L214)                            |
| `TNut.to_cutter` (pocket + slot)                                                               | `free`  | [`nuts/tnut.py:75`](../vibe_cading/mechanical/nuts/tnut.py#L75), [`nuts/tnut.py:93`](../vibe_cading/mechanical/nuts/tnut.py#L93) |
| `Bearing.outer_pocket`                                                                         | `press` | [`bearings.py:81`](../vibe_cading/mechanical/bearings.py#L81)                                    |
| `Bearing.shaft_cutter`                                                                         | `slip`  | [`bearings.py:105`](../vibe_cading/mechanical/bearings.py#L105)                                  |
| `DiscMagnet.to_cutter`                                                                         | `slip`  | [`magnets.py:43`](../vibe_cading/mechanical/magnets.py#L43)                                      |
| `BarMagnet.to_cutter`                                                                          | `slip`  | [`magnets.py:115`](../vibe_cading/mechanical/magnets.py#L115)                                    |
| `Standoff.to_cutter`                                                                           | `free`  | [`standoffs.py:84`](../vibe_cading/mechanical/standoffs.py#L84)                                  |
| `PrintInPlaceHinge` (clearance + face gap)                                                     | `free`  | [`hinge.py:58-59`](../vibe_cading/mechanical/hinge.py#L58)                                       |
| `TechnicAxleHole` (`TIP_TO_TIP` cross envelope; chooses grade by `fit=` kwarg)                 | `slip`* | [`technic_axle_hole.py:114`](../vibe_cading/lego/cutters/technic_axle_hole.py#L114)              |
| `FreespinHexHub` (bearing pocket lateral inflation)                                            | `free`  | [`freespin_hex_hub.py:137`](../vibe_cading/rc/freespin_hex_hub.py#L137)                          |

\* `TechnicAxleHole` defaults to `slip` but accepts `fit="free"` / `fit="press"`; the grade selection happens at construction.

### 2.2 `axial` — extra material along the cut axis (typically Z)

**What it modifies:** depth of a counterbore, pocket, or recess along the cut axis. A `+0.20 mm` axial on a counterbore extends the head recess `0.20 mm` deeper so the head sits flush rather than proud.

**Why it's a separate knob:** radial alone can't compensate for layer-line sag. On an FDM printer the *bottom* of a downward-facing pocket sags slightly into the support, leaving the pocket shallower than designed. The fix is geometric (deepen the pocket), not radial. The two failure modes are independent — a printer that bores holes spot-on radially can still sag pockets axially.

**Shipped `fdm_standard` values:** `free=0.20`, `slip=0.20`, `press=0.20` (uniform across grades — the failure mode is layer-line behavior, not fit-grade).

**Consumers:**

| Consumer                                                                                       | Grade   | Reference                                                                                        |
|------------------------------------------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------------|
| `CounterboreHole.to_cutter` (head recess depth: `z_recess = -tol.free.axial`)                  | `free`  | [`holes.py:166`](../vibe_cading/mechanical/holes.py#L166)                                        |
| `MetricMachineScrew.to_cutter` (head recess; delegates to `CounterboreHole`)                   | `free`  | [`screws/metric.py:138`](../vibe_cading/mechanical/screws/metric.py#L138)                        |
| `MetricHexNut.to_cutter` (pocket depth inflation)                                              | `free`  | [`nuts/metric.py:130`](../vibe_cading/mechanical/nuts/metric.py#L130)                            |
| `MetricSquareNut.to_cutter`                                                                    | `free`  | [`nuts/metric.py:215`](../vibe_cading/mechanical/nuts/metric.py#L215)                            |
| `TNut.to_cutter` (depth inflation per side)                                                    | `free`  | [`nuts/tnut.py:76`](../vibe_cading/mechanical/nuts/tnut.py#L76), [`nuts/tnut.py:94`](../vibe_cading/mechanical/nuts/tnut.py#L94) |
| `Bearing.outer_pocket` (depth clearance)                                                       | `press` | [`bearings.py:82`](../vibe_cading/mechanical/bearings.py#L82)                                    |
| `DiscMagnet.to_cutter` (depth clearance)                                                       | `slip`  | [`magnets.py:44`](../vibe_cading/mechanical/magnets.py#L44)                                      |
| `BarMagnet.to_cutter` (Z clearance)                                                            | `slip`  | [`magnets.py:116`](../vibe_cading/mechanical/magnets.py#L116)                                    |
| `Standoff.to_cutter` (depth allowance)                                                         | `free`  | [`standoffs.py:85`](../vibe_cading/mechanical/standoffs.py#L85)                                  |
| `FreespinHexHub` (bearing pocket axial — `prof.free.axial + 0.5`)                              | `free`  | [`freespin_hex_hub.py:147`](../vibe_cading/rc/freespin_hex_hub.py#L147)                          |

Most through-hole consumers (`ClearanceHole`, `CountersinkHole`, etc.) do *not* read `axial` — they bake a fixed 100 mm overcut on both ends instead (see [`holes.py:36-38`](../vibe_cading/mechanical/holes.py#L36)).

### 2.3 `slot` — extra half-width applied **only** to narrow slots

**What it modifies:** an *additional* half-width on top of `radial`, applied **only** to narrow-slot widths (currently the arm width of a Lego Technic `+` cross axle hole).

**Why it's a separate knob:** a narrow `+` cross slot prints tighter on FDM than the round envelope of the same nominal — corner blowout from the perimeter tool path closes the slot more aggressively than it closes a circular hole. The two failure modes are physically distinct, so they need distinct knobs. See the [`FitGrade.slot` docstring](../vibe_cading/print_settings.py#L270-L279) for the rationale.

**Shipped `fdm_standard` values:** `free=0.0`, `slip=0.10`, `press=0.0`. Only the `slip.slot=0.10` is non-zero — the FDM conservative floor for slip-fit Lego axle holes. Resin and CNC profiles ship all-zero (no narrow-slot failure mode on those processes).

**Consumers (today: exactly one):**

| Consumer                                            | Field           | Reference                                                                            |
|-----------------------------------------------------|-----------------|--------------------------------------------------------------------------------------|
| `TechnicAxleHole.ARM_WIDTH` (the narrow `+` arms)   | `grade.slot`    | [`technic_axle_hole.py:120`](../vibe_cading/lego/cutters/technic_axle_hole.py#L120)  |

A new consumer that reads `slot` would be any cutter whose narrow-slot geometry experiences corner blowout — for example a future `TechnicAxleStub` or any custom narrow-`+` profile. Round-envelope features (everything else in the library today) leave `slot` at its `0.0` default and read only `radial` + `axial`.

---

## 3. Shipped Profile Reference

The three shipped profiles in [`_FALLBACK_PROFILES`](../vibe_cading/print_settings.py#L628-L646) resolve to the following 27 leaf-float values when passed through [`_profile_from_nested`](../vibe_cading/print_settings.py#L362) (i.e. the per-field defaults in [`_fitgrade_from_dict`](../vibe_cading/print_settings.py#L338) fill any missing leaf with `0.0`). These tuples are pinned in [`tests/test_tolerance_profile.py`](../tests/test_tolerance_profile.py) T9b — `test_shipped_profiles_pinned_tuples` — and a regression in any of the 27 values fails that test loudly.

| Profile          | `free.radial` | `free.axial` | `free.slot` | `slip.radial` | `slip.axial` | `slip.slot` | `press.radial` | `press.axial` | `press.slot` |
|------------------|---------------|--------------|-------------|---------------|--------------|-------------|----------------|---------------|--------------|
| `fdm_standard`   | 0.15          | 0.20         | 0.0         | 0.05          | 0.20         | **0.10**    | 0.04           | 0.20          | 0.0          |
| `resin_precise`  | 0.05          | 0.05         | 0.0         | 0.03          | 0.05         | 0.0         | 0.02           | 0.05          | 0.0          |
| `cnc`            | 0.02          | 0.0          | 0.0         | 0.01          | 0.0          | 0.0         | 0.0            | 0.0           | 0.0          |

**How to read the table:**

- `fdm_standard` is the safest default — loosest radials and largest axials, plus the conservative narrow-slot floor on `slip.slot`. It's also the hardcoded fallback when no profile name is configured (see [`get_default_profile_name`](../vibe_cading/print_settings.py#L225)).
- `resin_precise` is ~3× tighter radially and ~4× tighter axially than `fdm_standard` — resin parts shrink uniformly and don't sag.
- `cnc` is ~10× tighter than `fdm_standard` and the only profile that ships `press.radial=0.0` — on a machined part the nominal IS the final dimension.

---

## 4. Calibration: When to Tune vs Use Defaults

The project ships defaults forgiving enough that most users never tune — only the fussy fits earn a calibration cycle. The fewer the knobs a user must measure, the more reliably the system works out-of-the-box.

### v1 user-tunable knobs (calibration helper coverage)

[`tools/calibrate.py`](../tools/calibrate.py) walks the three radial knobs interactively:

| Knob          | Why it earns a calibration cycle                                                                            | Calibration command                       |
|---------------|-------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| `free.radial` | M3 clearance holes are the most common consumer — wrong here, every plate binds.                            | `python3 tools/calibrate.py free`         |
| `press.radial`| Press fits are unforgiving: too loose and the nut spins, too tight and the print cracks.                    | `python3 tools/calibrate.py press`        |
| `slip.radial` | Lego axle slip fit is the canonical "must feel right" interface — opt-in only.                              | `python3 tools/calibrate.py slip`         |

The helper prints the gauge, you measure the best-fitting variant, the tool back-solves the radial allowance via `radial = (D − N) / 2` against the live source-of-truth nominal, and atomically writes it to your `print_profiles_user.json` via per-knob field-level merge. See the README's [Print Tolerances & Calibration](../README.md#print-tolerances--calibration) section for the full workflow including non-interactive `--yes` flags.

### Default-floor-only knobs

- **`slip.slot = 0.10`** on `fdm_standard` — the conservative narrow-slot floor for FDM Lego axle holes. Per-printer calibration is *not* a v1 requirement: the floor is loose enough for nearly every consumer FDM machine. If your printer's corner blowout is unusual, override `slip.slot` in `print_profiles_user.json` (see §5 below).

### Out of scope for v1

- **`free.axial` / `slip.axial` / `press.axial`** — all shipped at `0.20` mm on `fdm_standard`. Layer-line sag is forgiving at this value; most users never tune. If your printer's first-layer settings cause binding under counterbore heads, override `axial` globally in your user file rather than per-grade.

---

## 5. User Override Patterns (the field-level merge contract)

User overrides in `print_profiles_user.json` recursively deep-merge onto the shipped defaults, **leaf-wins**. You override exactly the knob you measured; siblings inherit. See [`_deep_merge_profiles`](../vibe_cading/print_settings.py#L406) for the full semantics.

### Worked example: a fresh user-key entry

```jsonc
// print_profiles_user.json
{
  "bambu_p1s__pla_overture": {
    "slip": { "radial": 0.11 }
  }
}
```

Resolved `ToleranceProfile.slip` for `bambu_p1s__pla_overture`:

| Field         | Resolved value | Source                                                                                  |
|---------------|----------------|------------------------------------------------------------------------------------------|
| `slip.radial` | `0.11`         | User override.                                                                           |
| `slip.axial`  | `0.0`          | **`_fitgrade_from_dict` safety default** — NOT the shipped `fdm_standard.slip.axial=0.20`. |
| `slip.slot`   | `0.0`          | **`_fitgrade_from_dict` safety default** — NOT the shipped `fdm_standard.slip.slot=0.10`. |

### Critical: field-level merge inherits from the **matched parent key**, not the `fdm_standard` floor

The deep-merge walks per-top-level-key. A fresh `bambu_p1s__pla_overture` entry has *no* shipped sibling to inherit from — the merge takes the user dict verbatim, and the per-field defaults in [`_fitgrade_from_dict`](../vibe_cading/print_settings.py#L338) (where `default_slot=0.0`) fill in the missing leaves. The shipped `fdm_standard.slip.slot=0.10` floor does **not** carry over.

This is the **surface-not-seed** contract the calibration helper warns about. If you want the FDM narrow-slot floor in your custom profile, you must restate it explicitly:

```jsonc
// print_profiles_user.json — explicit floor copy
{
  "bambu_p1s__pla_overture": {
    "slip": { "radial": 0.11, "slot": 0.10 }
  }
}
```

If you instead override **inside** the shipped `fdm_standard` key — `{"fdm_standard": {"slip": {"radial": 0.11}}}` — the deep-merge **does** inherit siblings from the shipped grade, because there's a matched parent dict to recurse into. See the T9 fixture in [`tests/test_tolerance_profile.py:672`](../tests/test_tolerance_profile.py#L672) for the pinned tuple.

### User key convention

User-defined profile keys SHOULD follow the `<machine>__<material>[__<brand>]` lexical convention (double-underscore separator). The loader treats every top-level key as opaque, so the convention is purely documentary — but the convention keeps profile names collision-free against hyphenated machine names and shell-glob-safe. Examples:

- `bambu_p1s__pla_overture`
- `ender3__petg_polymaker`
- `prusa_mk4__pla`

The shipped keys (`fdm_standard`, `resin_precise`, `cnc`) are coarse-default categories and exempt from the convention.

### Null and type-mismatch are hard errors

A `null` leaf or a type-mismatched override (e.g. user puts a primitive where the shipped profile has a dict) raises `ValueError` with the JSON-pointer-style key path. Silent "reset to default via null" is too easy a foot-gun and `null` is not a tolerance-domain-valid value. See [`_deep_merge_profiles` branches (e) and (f)](../vibe_cading/print_settings.py#L460-L471).

### Unknown leaf keys silently pass through

A typo'd override (`{"slip": {"radail": 0.11}}`) is loaded into the merged dict but never read — `_fitgrade_from_dict` reads only the known field names `radial`, `axial`, `slot`. Your calibration is silently dropped. If a calibrated value doesn't seem to take effect, check your override for typos.

---

## 6. When to Add a New Consumer / New Knob

### Adding a new model class

Pick the grade based on the **intended fit physics**, not by which other consumer happens to read the same field:

- A through-hole the screw floats in → `free`.
- A bearing seat or peg-in-socket → `slip`.
- A press-in nut pocket or hammered insert → `press`.

Then pick the allowance dimension:

- Round / polygonal cross-section diameter → `radial`.
- Depth or floor along the cut axis → `axial`.
- Narrow `+` cross slot width (FDM-only failure mode) → `slot` (on top of `radial`).

Resolve the profile via the constructor pattern used elsewhere — accept a `profile: ToleranceProfile | str | None = None` argument and fall back to `get_profile()` lazily. See [`_resolve_profile`](../vibe_cading/mechanical/holes.py#L41) for the canonical pattern.

### When NOT to add a new field to `FitGrade`

Most new consumers reuse the existing three fields. Adding a brand-new `FitGrade` field (e.g. a hypothetical `bridge` for over-bridge sag) is a structural change that requires a design-flow consult, because:

- Every shipped profile in `_FALLBACK_PROFILES` needs a sensible value for the new field.
- The T9b snapshot test pins all 27 leaf-floats — a new field adds a column to every row.
- The user override-merge contract needs documenting for the new field.
- Calibration tooling needs a new walk command.

Before proposing a new field, check whether the physical failure mode is genuinely orthogonal to `radial` / `axial` / `slot` — `slot` was added because narrow-cross-slot corner blowout can't be modeled by widening `radial` alone. A field that adjusts the *same* physical surface as an existing one should reuse the existing knob.
