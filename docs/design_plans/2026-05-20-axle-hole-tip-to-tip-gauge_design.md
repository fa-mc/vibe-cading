# Design: Lego Axle-Hole Profiling — Separate Hole/Axle Constants + Round-Hole Tip-to-Tip Gauge

## Meta
- **Requirements ref**: Interactive request (this session) — see *Design Dialog Log*.
- **Requester role**: User (acting as Admin)
- **Date**: 2026-05-20
- **Dialog rounds**: 2

---

> ⚠️ **AMENDMENT 2 (2026-05-21)** — a post-calibration `@designer` + `@tl`
> review reversed the constant-role decision. **"Approach B", the original
> Implementation Plan, Tests, and Success Criteria below are SUPERSEDED.**
> Implement from **`## Amendment 2`** at the end of this brief.

## Objective

Decouple the Technic axle *hole* dimensions from the axle *solid* dimensions
into separate, env-overridable constants, and deliver a printable round-hole
gauge that isolates the effective **tip-to-tip** dimension for FDM calibration.

---

## Background — why this task exists

`TODO.md` carries an unfinished item: *"Revisit Technic axle hole clearance
tuning (concave radius sweep failed)."* The earlier attempt swept
`TechnicAxleHole.concave_radius` (the inner-corner fillet) and never found a
combination that fit a real Lego axle.

Root cause of that failure: a fillet on the concave corners cannot fix a
wrong **base dimension**. The axle hole is built from two parameters —
tip-to-tip (the bounding-cylinder diameter) and arm-width (the flat-slot
width). The concave-radius sweep tuned neither. Worse, the `+` cross hole has
four concave corners where FDM extrusion over-deposits ("corner blowout"),
choking the printed slot — so a cross-profile sweep mixes *three* unknowns
(tip-to-tip, arm-width, corner blowout) into one fit observation and cannot
isolate any of them.

**The fix is to isolate one variable at a time.** A *round* hole contacts a
Lego axle only at its four curved arm tips — each tip is an arc of radius
`tip_to_tip / 2`, so the axle's outer envelope *is* a circle of diameter
`tip_to_tip`. A round hole has no concave corners, so corner blowout cannot
confound it. The smallest round hole that accepts the axle therefore measures
the effective tip-to-tip directly. This brief delivers **Stage 1: tip-to-tip
via round holes**. Stage 2 (arm-width via a cross-profile gauge) is a
follow-up — see *Out of Scope*.

---

## Objective restated

Three structural changes plus one new part:

1. Two new env-overridable constants — `AXLE_HOLE_TIP_TO_TIP`,
   `AXLE_HOLE_ARM_WIDTH` — so the hole nominal is independent of the axle
   nominal.
2. `TechnicAxleHole` re-sourced from the new hole constants.
3. A new `AxleHoleGauge` model class — the round-hole tip-to-tip test fit.
4. `.env.example` + docs reconciliation (the docs already promise these
   variables; they do not yet exist).

---

## Architecture / Approach

### Approach chosen

#### A. New constants (`vibe_cading/lego/constants.py`)

Add, in the *Technic Axle* block:

```python
# ── Technic Axle Hole (cross profile, printer-tuned) ─────────────────────────
# Printer-tuned FINAL modelled dimensions of the cross axle *hole* — distinct
# from the AXLE_* values above, which describe the axle *solid*.  Calibrate
# with AxleHoleGauge (round-hole sweep) + the Stage-2 cross gauge and override
# in .env.  Defaults below reproduce the pre-decoupling cutter exactly
# (legacy AXLE_TIP_TO_TIP/ARM_WIDTH + fdm_standard slip clearance) so no
# dependent model changes until you run the calibration sweep.
AXLE_HOLE_TIP_TO_TIP: float = float(os.getenv("AXLE_HOLE_TIP_TO_TIP", "4.88"))
AXLE_HOLE_ARM_WIDTH:  float = float(os.getenv("AXLE_HOLE_ARM_WIDTH",  "1.89"))
```

The `os.getenv(...)` wrapper matches the existing `PIN_HOLE_PRINTED` pattern —
no new dependency, `.env` parsed by the existing `load_env_file()`.

#### B. `TechnicAxleHole` re-sourced — **constant-role decision (the "Designer advise" answer)**

`AXLE_HOLE_TIP_TO_TIP` / `AXLE_HOLE_ARM_WIDTH` are **printer-tuned final
modelled dimensions** — the same role `PIN_HOLE_PRINTED` already plays — and
they represent the **slip-fit** calibration (the natural fit by which a
sliding axle is judged by feel).

`TechnicAxleHole` builds its cross profile directly from these constants. The
`fit` grade is applied as a **delta from the slip baseline**, not as an
absolute clearance:

```python
grade = getattr(profile, fit)
delta = grade.radial - profile.slip.radial          # 0 when fit == "slip"
self.TIP_TO_TIP = AXLE_HOLE_TIP_TO_TIP + (2 * delta)
self.ARM_WIDTH  = AXLE_HOLE_ARM_WIDTH  + (2 * delta)
```

- `fit="slip"` (default) → delta 0 → **exactly the calibrated constant**. The
  number you measured on the gauge is the number that prints — zero surprise.
- `fit="press"` / `fit="free"` → shifts tighter / looser *relative to* the
  calibrated slip baseline, and scales correctly per profile.

**Why this and not "constant stays nominal, cutter keeps adding absolute
`+2·grade.radial`":** the round-hole sweep measures an *effective fit*, which
already bakes in the printer's hole-shrink, the material, and the desired
slide feel. There is no clean "nominal" hiding inside a fit observation, so
the constant must *be* the final printer-tuned dimension. If the cutter then
re-added an absolute profile clearance, a user who enters their measured
fitting diameter gets a hole ~0.10 mm too loose and would have to mentally
pre-subtract the clearance — the inverted-logic / double-negative anti-pattern
the Designer brief explicitly forbids. The delta form keeps the press/slip/free
feature alive (it has real use: a free fit lets the axle spin, a press fit
holds it) while making the default `slip` case land exactly on the value the
user calibrated.

#### C. New `AxleHoleGauge` model class

A compact flat block carrying a single row of round through-holes of swept
diameter, each engraved with its diameter on the top face. The user prints it,
inserts a real Lego axle, and reads off the smallest hole that accepts the
axle with a firm-but-free slip.

Suggested module: `vibe_cading/lego/axle_hole_gauge.py` (Lego-domain
calibration part). Final file placement is the Developer's call.

#### D. `.env.example` + docs reconciliation

`.env.example` gains `AXLE_HOLE_TIP_TO_TIP` / `AXLE_HOLE_ARM_WIDTH` (commented,
with calibration note). `docs/lego-technic.md` → *Tuning Tolerances* already
instructs users to "uncomment the `AXLE_HOLE_TIP_TO_TIP` and
`AXLE_HOLE_ARM_WIDTH` variables" — verify that section now matches reality.

### Visual contract (CAD task — new model class `AxleHoleGauge`)

![Design preview — iso_ne](2026-05-20-axle-hole-tip-to-tip-gauge_design_iso_ne.svg)

![Design preview — top](2026-05-20-axle-hole-tip-to-tip-gauge_design_top.svg)

Seven round through-holes in a single row along X, axes parallel to Z (the
build direction) — the default sweep is 4.70–5.00 mm in 0.05 mm increments.
The block lies flat on the print bed; the diameter labels (omitted from the
contract SVG — glyph outlines bloat it ~15×) occupy the −Y row. The contract
to verify at Phase B: holes are **round** (not cross), **through** (not
blind), in **one row**, with **vertical (Z) axes**.

### Alternatives rejected

- **Sweep the `+` cross profile directly (extend the failed approach).**
  Rejected — mixes tip-to-tip, arm-width, and corner blowout into one
  observation; cannot isolate any of them. This is the exact failure recorded
  in `TODO.md`.
- **Add an axle round-hole row to the existing `ToleranceGauge`.** Rejected
  by the user (Round 2) — couples the axle sweep range to the shared
  `offsets` tuple driving the screw/bearing/pin rows, and forces a full
  multi-feature reprint per iteration.
- **Keep `AXLE_HOLE_*` as nominal + have the cutter add absolute profile
  clearance.** Rejected — double-counts the print clearance; see *B* above.
- **Drop the `fit` parameter from `TechnicAxleHole` entirely** (the calibrated
  constant being the only fit). Simpler, but discards the genuine press/free
  use cases and is an API change beyond the selected scope. The delta form
  keeps the feature at near-zero cost.

---

## Data & Interface Contracts

**`AxleHoleGauge` public API**

```python
class AxleHoleGauge:
    """Printable round-hole gauge for calibrating the effective Technic
    axle-hole tip-to-tip diameter on a specific FDM printer / material.

    Origin (0, 0, 0): the block is plan-centred — its XY centroid sits at
    the origin — and its bottom face lies on the Z=0 print bed; the block
    extrudes up into +Z.  Hole axes are parallel to Z.
    """
    def __init__(
        self,
        diameters: Sequence[float] = (4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00),
        depth: float = 8.0,          # block thickness = hole depth = 1 stud
        hole_pitch: float = 9.0,     # cell width per hole (X)
        engrave_depth: float = 0.6,  # label engraving depth
    ): ...

    @property
    def solid(self) -> cq.Workplane: ...
```

**Invariants**
- One straight cylindrical through-hole per entry in `diameters`, axis ∥ Z,
  **no lead-in chamfer** — a chamfer would guide the axle and bias the
  "smallest hole that fits" judgment; the fit must be read off the full
  straight bore.
- Each hole engraved with its diameter (`f"{d:.2f}"`) on the top face. All
  label text unioned into one compound before a **single** `.cut()` (per the
  *Parameter Sweeps* text rule — avoids stalling the OCCT boolean kernel).
- Result is a single contiguous solid:
  `assert len(result.solids().vals()) == 1`.

**`TechnicAxleHole` — unchanged public signature.** `__init__(depth, fit,
profile, convex_radius, concave_radius)` is preserved; only the internal
dimension source (now `AXLE_HOLE_*`) and the clearance formula (now
slip-baseline delta) change. `.solid` / `.to_cutter()` unchanged.

---

## Implementation Plan

- [x] **T1** — Add `AXLE_HOLE_TIP_TO_TIP` (4.88) and `AXLE_HOLE_ARM_WIDTH`
  (1.89) to `vibe_cading/lego/constants.py` with `os.getenv` wrappers and the
  provenance/calibration block comment from *Approach A*.
- [x] **T2** — Update `TechnicAxleHole`: import the new `AXLE_HOLE_*`
  constants, replace the dimension source, change the clearance to the
  slip-baseline delta (`2 * (grade.radial - profile.slip.radial)`), and update
  the class docstring to state the constants are printer-tuned slip-fit
  dimensions.
- [x] **T3** — Implement `AxleHoleGauge` (new file: AGPLv3 header, strict type
  hints, origin docstring, no `__main__` / `ocp_vscode`). Single-instance
  `tools/view.py` is sufficient — do **not** add a `demo()` classmethod.
- [x] **T4** — Add commented `AXLE_HOLE_TIP_TO_TIP` / `AXLE_HOLE_ARM_WIDTH`
  entries to `.env.example` with a calibration note.
- [x] **T5** — Reconcile `docs/lego-technic.md` → *Tuning Tolerances*: confirm
  the referenced variables now exist and the steps are accurate. Do **not**
  edit the dimension *tables* (value reconciliation is out of scope).
- [x] **T6** — Validation: build `AxleHoleGauge`, run the single-solid assert,
  run `tools/preview.py`, regenerate the visual-contract SVGs from the
  implemented class and overwrite the two committed `.agents/plans/` SVGs.

---

## Tests

| # | Test description | Expected assertion | File / location |
|---|------------------|--------------------|-----------------|
| 1 | `AxleHoleGauge()` builds with defaults | `len(g.solid.solids().vals()) == 1` | `tests/` (new or existing lego test file) |
| 2 | Hole count matches sweep | gauge has one through-hole per `diameters` entry (verify via `hole_finder.py` or cylindrical-face count) | `tests/` |
| 3 | `TechnicAxleHole` default behaviour preserved | with `fdm_standard` + `fit="slip"`, cutter XY bounding box ≈ 4.88 × 4.88 mm (unchanged from pre-decoupling) | `tests/` |
| 4 | `fit` grade ordering | `fit="free"` cutter wider than `fit="slip"` wider than `fit="press"` (tip-to-tip monotonic) | `tests/` |
| 5 | Env override honoured | setting `AXLE_HOLE_TIP_TO_TIP` in the environment changes the constant / cutter size | `tests/` |
| 6 | Existing `TechnicAxleHole` consumers unaffected | gear_28t / servo-mount / shaft tests (if any) still pass | existing `tests/` |

Developer chooses concrete test-file placement; extend an existing lego test
module if one fits.

## Success Criteria

1. `AXLE_HOLE_TIP_TO_TIP` and `AXLE_HOLE_ARM_WIDTH` exist in `constants.py`,
   are env-overridable, and are the dimension source for `TechnicAxleHole`.
2. With default constants + `fdm_standard` + `fit="slip"`, the `TechnicAxleHole`
   cutter is dimensionally identical to the pre-change cutter (no dependent
   model — gear_28t, servo mounts, shafts, bearing sleeve — changes).
3. `AxleHoleGauge` builds a single contiguous solid with one labelled round
   through-hole per swept diameter.
4. `python3 tools/view.py vibe_cading.lego.axle_hole_gauge.AxleHoleGauge`
   renders; `tools/preview.py` SVGs match the visual contract (round / through
   / single row / Z axes).
5. `.env.example` and `docs/lego-technic.md` reference the real, existing
   variables.
6. No CI regressions — AGPLv3 header present, no `__main__` block, no
   `ocp_vscode` import, linters clean.

## Out of Scope

- Reconciling the conflicting dimension *values* in the repo (constants 4.78/1.79
  vs docs axle 4.75/1.78 vs docs hole 4.80/1.83) — only the *mechanism*
  (separate constants) is in scope; the user did not select value reconciliation.
- **Stage 2** — the cross-profile arm-width gauge. Follow-up once tip-to-tip is
  dialed in.
- Refactoring the duplicated cylinder∩cross construction shared by
  `TechnicAxleHole` and `TechnicAxle` into a `cq_utils` helper.
- Removing the dead `AXLE_ARM_PROTRUSION` constant.
- `TechnicAxle` (the axle *solid*) — unchanged; keeps using `AXLE_TIP_TO_TIP` /
  `AXLE_ARM_WIDTH`.
- Registering `AxleHoleGauge` in `build.toml` — requires explicit user approval
  and is presented separately (per the *build.toml* rule).

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Non-`fdm_standard` profiles: the hole tip-to-tip shifts ≤ 0.04 mm vs. the old absolute-clearance behaviour (delta-from-slip vs. absolute). | Documented here; resin/CNC users recalibrate via the gauge regardless, and the new model is dimensionally honest (the hole is a real dimension, not a profile-derived one). |
| Round-hole fit ≠ cross-hole fit — the round gauge isolates tip-to-tip only; arm-width and the short tip-arc / flat-junction interaction are still unknown. | Explicitly Stage 1; the Stage-2 cross-profile gauge validates the combined fit. Brief states the round hole measures tip-to-tip *only*. |
| A real axle in a round hole contacts at 4 tips only and can rotate/wobble. | Test procedure (below) instructs the user to judge by **axial slide feel**, not rotational play — wobble is expected, not a defect. |
| FDM print orientation affects hole shrink (vertical vs. horizontal bore). | Geometry prints flat with hole axes ∥ build-Z (most repeatable). Calibration assumption noted; documented as a Stage-1 constraint. |
| Engraved label text stalling the OCCT boolean kernel. | Union all label solids into one compound, then a single `.cut()` — the established `ToleranceGauge` pattern. |
| Sweep range misses the true value (the prior sweep's failure mode). | Default range 4.70–5.00 (0.05 mm step, 7 holes) brackets a nominal ~4.78 with margin both ways for FDM hole-shrink at finer resolution; the class is parametric, so a coarser or shifted pass is just a different `diameters=` tuple. |

### Test / calibration procedure (include in `AxleHoleGauge` docstring or a doc note)

1. Print `AxleHoleGauge` flat, holes vertical (axis ∥ build-Z), on the target
   printer + material, with the same slicer settings used for real parts.
2. Insert a real Lego Technic axle into each hole from the labelled face.
3. The smallest hole the axle enters with a firm-but-free slip — no slop, no
   force — gives the effective tip-to-tip. Judge by **axial slide feel**, not
   rotational wobble (wobble is inherent to a round hole and expected).
4. Set `AXLE_HOLE_TIP_TO_TIP=<that diameter>` in `.env`. After confirming
   across a couple of prints, promote it to the constant default.

---

## Design Dialog Log

### Round 1
**Designer findings:**
> Surveyed the current profiling: `TechnicAxleHole` and `TechnicAxle` both
> derive from a single pair of constants (`AXLE_TIP_TO_TIP=4.78`,
> `AXLE_ARM_WIDTH=1.79`); the docs reference `AXLE_HOLE_*` constants that do
> not exist; three conflicting dimension sets live in the repo;
> `AXLE_ARM_PROTRUSION` is dead; the cross construction is duplicated.

**Requester contribution:**
> Scope = **Separate hole/axle constants**. Trigger: *"I never finished this,
> the last sweep (a few weeks ago) did not find the right measurement that
> would fit."*

**Resolution:**
> Confirmed against `TODO.md` — the prior sweep tuned `concave_radius`, not the
> base dimensions. Scope the work to constant separation + finishing the
> calibration sweep. Value reconciliation explicitly excluded.

### Round 2
**Designer proposal:**
> (a) Package the gauge as a dedicated class or a `ToleranceGauge` row?
> (b) Once a fitting round hole is found, should `AXLE_HOLE_TIP_TO_TIP` be a
> final printer-tuned value or a nominal + profile clearance?

**Requester contribution:**
> (a) **Dedicated `AxleHoleGauge` class.** (b) *"Designer advise."* Plus the
> directional steer: *"find these variables separately. First use round holes
> to find tip to tip."*

**Resolution:**
> (a) Dedicated `AxleHoleGauge`. (b) Designer recommendation: **final
> printer-tuned value, calibrated at slip fit**, with the `fit` grade applied
> as a delta from the slip baseline (default `slip` → exact constant). See
> *Approach B* for the full rationale.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(N/A — domain integrity gate NO; dimensions sourced from existing repo constants, no new reference material interpreted)*
- [ ] Requester sign-off
- [x] Designer sign-off (drafting author)

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [ ] Independent TL
- [ ] Independent Developer
- [ ] Independent Researcher  *(N/A — domain integrity gate NO)*

---

## Implementation Status

**Amendment 2 re-implementation (2026-05-21)** — A1–A9 complete; the
constant-role reversal is shipped. Supersedes the T1–T6 status below.

- [x] All Amendment 2 tasks (A1–A9) completed.
- [x] Test suite executed — result: `178 passed, 2 xfailed` (full `tests/`
  suite, unchanged baseline count — no consumer regressions;
  `tests/test_axle_hole_gauge.py` 7/7 green).
- [x] No new linter / static-check errors (`flake8` clean on the four touched
  source/test files; `tools/check_no_main_blocks.py` OK; no `ocp_vscode`
  imports under `vibe_cading/` or `parts/`).
- Developer note (Amendment 2 pass):
  - **A1** — `AXLE_HOLE_TIP_TO_TIP = 4.80` / `AXLE_HOLE_ARM_WIDTH = 1.83` are
    now plain `float` constants (no `os.getenv`). Block comment rewritten:
    real-Lego nominal, tune the `ToleranceProfile` not the constant.
  - **A2** — `TechnicAxleHole` reverted to `nominal + 2*grade.radial`; the
    delta-from-slip mechanism removed; class docstring updated to state the
    constants are real nominals and clearance comes from the profile.
  - **A3** — `.env.example` `AXLE_HOLE_*` entries removed; replaced with a
    one-line note pointing to `machine_profiles_user.json` calibration.
  - **A4/A5** — `docs/lego-technic.md` *Tuning Tolerances* rewritten around
    `machine_profiles_user.json` (`slip.radial`) with the
    `radial = (D − 4.80) / 2` formula; `AxleHoleGauge` docstring step 4
    rewritten to yield a *profile* `slip.radial`, not a constant override.
  - **A6** — `README.md` gained a "## Print Tolerances & Calibration" section
    after "Lego Technic Reference" — brief, links out to
    `docs/lego-technic.md`.
  - **A7** — `TODO.md` line-13 axle-hole item ticked + annotated (Stage 1
    resolved by `AxleHoleGauge`); Stage-2 and calibration-helper items added.
  - **A8** — Test #5 (env override) replaced with a profile-override test
    (`slip.radial=0.10` → 5.00 × 5.00 mm cutter); test #3 updated to expect
    4.90 × 4.90 mm at `fdm_standard` slip.
  - **Verification** — `TechnicAxleHole` at `fdm_standard` + `fit="slip"`
    produces a **4.90 × 4.90 mm** cutter (4.80 + 2×0.05), not 4.88; arm-width
    1.93 mm. Fit ordering monotonic: press 4.88 < slip 4.90 < free 5.10. A
    `ToleranceProfile` with `slip.radial=0.10` moves the cutter to
    5.00 × 5.00 mm — profile-driven, as intended.
  - `AxleHoleGauge` geometry unchanged (Amendment 2 only touches its
    docstring) — contract SVGs deliberately NOT regenerated.
  - Parked follow-ups (PIN_HOLE_PRINTED migration; `fdm_standard` slip
    re-baseline) appended to `/memories/session/ideas.md`.
  - No commits made (per task instruction). No escalations.

---

### Original implementation status (Approach B — SUPERSEDED by Amendment 2)

**Amendment 2026-05-20** — `AxleHoleGauge.__init__` default `diameters`
refined from `(4.70, 4.80, 4.90, 5.00, 5.10, 5.20, 5.30)` to
`(4.70, 4.75, 4.80, 4.85, 4.90, 4.95, 5.00)` (still 7 holes; range tightened
to 4.70–5.00, increment halved to 0.05 mm). STEP re-exported, contract SVGs
regenerated, `tests/test_axle_hole_gauge.py` 7/7 green (tests read
`gauge.diameters` dynamically — no test edit needed).

- [x] All Implementation Plan tasks completed
- [x] Test suite executed — result: `178 passed, 2 xfailed` (full `tests/`
  suite; +7 new in `tests/test_axle_hole_gauge.py` covering design Tests 1-5;
  Test 6 — existing consumers unaffected — is the prior 171 passing unchanged).
- [x] No new linter / static-check errors (`flake8` clean on all touched
  source + test files; `tools/check_no_main_blocks.py` OK).
- Developer note:
  All six tasks complete; all Success Criteria met.
  - **T1/T2** — `AXLE_HOLE_TIP_TO_TIP=4.88` / `AXLE_HOLE_ARM_WIDTH=1.89` added
    to `constants.py` (env-overridable). `TechnicAxleHole` re-sourced from them
    with the slip-baseline delta `2 * (grade.radial - profile.slip.radial)`.
    Verified: `fit="slip"` cutter XY bbox = exactly 4.88 × 4.88 mm —
    dimensionally identical to the pre-decoupling cutter (`AXLE_TIP_TO_TIP
    4.78` + `fdm_standard` slip 0.05 → 4.88). Fit ordering confirmed
    monotonic: free 5.08 > slip 4.88 > press 4.86 mm. No dependent-model
    changes (full suite green).
  - **T3** — `AxleHoleGauge` implemented at
    `vibe_cading/lego/axle_hole_gauge.py` (AGPLv3 header, strict type hints,
    origin docstring, calibration procedure in docstring). No `__main__`
    block, no `ocp_vscode` import, no `demo()` classmethod. Builds a single
    contiguous solid (`assert` in `_build`); 7 round through-holes verified
    via CYLINDER-face introspection — single row, axes ∥ Z, uniform 9 mm
    pitch, full-depth Z span. Labels unioned into one compound before a
    single `.cut()`.
  - **T4/T5** — `.env.example` gained commented `AXLE_HOLE_*` entries with a
    calibration note; `docs/lego-technic.md` *Tuning Tolerances* steps
    confirmed accurate (variables now exist) plus an `AxleHoleGauge` pointer
    added. Dimension tables untouched (value reconciliation out of scope).
  - **T6** — `tools/preview.py` and `tools/view.py` both render
    `AxleHoleGauge` (view.py exits 0; the OCP-viewer port error is the
    headless environment, not a code defect). The two committed contract
    SVGs were regenerated text-free from the implemented class's layout
    (80541 / 60916 bytes — matching the original text-free sizes; preview
    SVGs *with* engraved glyphs are ~5× larger, hence the text-free render).
  - **build.toml** — `AxleHoleGauge` deliberately NOT registered; a proposed
    `[[build]]` block is presented to the user for explicit approval (per the
    build.toml rule) in the handoff message.
  - No escalations; no design ambiguities encountered.

---

## Post-Implementation Sign-Off

### TL Review
- [ ] **TL sign-off**
- TL review notes:

### Designer Review (output review — responsibility 7)
- [x] **Designer sign-off** — all acceptance criteria met. Independently verified:
  `TechnicAxleHole` slip cutter = 4.88 × 4.88 mm (dimensionally identical to
  pre-change); fit ordering monotonic (press 4.86 < slip 4.88 < free 5.08);
  `AxleHoleGauge` builds a single solid, 63 × 19.30 × 8.00 mm, 7 round
  through-holes (7 cylindrical faces), Z span 0..8 (bottom on bed). Visual
  contract satisfied: round / through / single row / Z axes.
  `tests/test_axle_hole_gauge.py` 7/7 pass. No findings.

### Domain Expert Review
- [ ] N/A — domain integrity gate NO

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:

---

## Amendment 2 (2026-05-21) — Constant role reversed: nominal + profile (option b)

**Status:** supersedes "Approach B" and the printer-tuned-constant model
throughout this brief. Origin: post-calibration design review — `@designer`
(domain) + `@tl` (architecture), 2026-05-21. User-approved.

### Why Approach B was reversed

Approach B made `AXLE_HOLE_TIP_TO_TIP` a *printer-tuned*, `os.getenv`-overridable
constant. The physical calibration (real axle 4.75 mm; modelled Ø5.00 round
hole = good slip fit, confirmed on 3 prints — passes 1, 2, control) plus the
user's OSS constraint — *downstream users must tune their `ToleranceProfile`,
never this constant* — showed Approach B to be wrong:

- It is the **lone consumer** in the library that bakes printer tuning into a
  constant. `Bearing`, `magnets`, `ClearanceHole` all use *nominal constant +
  profile clearance*. The axle hole must follow the live pattern.
- The printer-specific number's home is `machine_profiles_user.json`
  (gitignored, dict-merges over `machine_profiles.json`) — the project already
  has this channel. Approach B created a redundant second one (`.env`).
- `PIN_HOLE_PRINTED` was cited as precedent in Approach B; it is itself a
  pre-`ToleranceProfile` legacy wart, not the live pattern.

### Corrected design

- `AXLE_HOLE_TIP_TO_TIP = 4.80` — fixed real-world Lego nominal (cross
  axle-hole envelope; equals the `PIN_HOLE_DIAMETER` Technic-beam hole
  envelope; `docs/lego-technic.md`). Plain `float`, **no `os.getenv`**.
- `AXLE_HOLE_ARM_WIDTH = 1.83` — fixed nominal cross-slot flat width
  (`docs/lego-technic.md`). Plain `float`, no `os.getenv`. *(Best-sourced
  figure; the docs are internally muddled on arm width — 1.83 stands until
  Stage 2 yields calibration data.)*
- `TechnicAxleHole` — clearance reverts to the plain absolute form, matching
  `Bearing` / `magnets`:
  ```python
  grade = getattr(profile, fit)
  TIP_TO_TIP = AXLE_HOLE_TIP_TO_TIP + 2 * grade.radial
  ARM_WIDTH  = AXLE_HOLE_ARM_WIDTH  + 2 * grade.radial
  ```
  The delta-from-slip mechanism is **removed**.
- Printer calibration lives in the user's `machine_profiles_user.json`, e.g.
  `{"fdm_standard": {"slip": {"radial": 0.10, "axial": 0.20}}}`. The
  `AxleHoleGauge` now yields a *profile* value: `slip.radial = (D − 4.80) / 2`
  where `D` is the fitting modelled diameter.

### Blast radius (accepted)

All four `TechnicAxleHole` consumers use default `fit="slip"`. Under shipped
`fdm_standard` (slip 0.05): cutter tip-to-tip 4.88 → **4.90** (+0.02 mm),
arm-width 1.89 → **1.93** (+0.04 mm). Sub-layer-line, looser/safer, no
reprints. The original **Success Criterion 2 ("dimensionally identical to
pre-change") is retired** — see revised criteria.

### `fdm_standard` shipped default — left as-is

`fdm_standard.slip.radial = 0.05` yields a 4.90 mm hole — tighter than the
~5.00 the calibration found. Re-baselining a *shipped* profile on one
printer's prints is rejected (silently loosens every slip consumer for all
users). Shipped default stays; users calibrate their own profile. Whether
`fdm_standard` itself needs re-baselining is a separate, evidence-gated
follow-up (needs a second printer) — parked, not in scope.

### Stage 2 reframed

Under option (b) tip-to-tip and arm-width share one `profile.radial`;
arm-width is not independently tunable. FDM cross-slot corner blowout is a
*geometry* artifact → Stage 2 becomes "add an explicit corner-relief parameter
to `TechnicAxleHole`", not "make `AXLE_HOLE_ARM_WIDTH` tunable". Deferred;
re-scoped when a cross-profile gauge yields blowout data.

### Revised Implementation Plan (re-implementation pass — supersedes T1–T6)

- [x] **A1** — `constants.py`: `AXLE_HOLE_TIP_TO_TIP = 4.80`,
  `AXLE_HOLE_ARM_WIDTH = 1.83`, plain floats, **no `os.getenv`**; rewrite the
  block comment (real Lego nominal; tune the profile, not this constant).
- [x] **A2** — `TechnicAxleHole`: revert to `nominal + 2*grade.radial`; remove
  the delta-from-slip mechanism; update the class docstring (constants are
  real nominals, clearance comes from the profile).
- [x] **A3** — `.env.example`: remove the `AXLE_HOLE_TIP_TO_TIP` /
  `AXLE_HOLE_ARM_WIDTH` entries (no longer env-tunable).
- [x] **A4** — `docs/lego-technic.md` *Tuning Tolerances*: rewrite — calibrate
  by editing `machine_profiles_user.json` (`slip.radial`), not `.env`
  constants. Include the `radial = (D − 4.80) / 2` formula.
- [x] **A5** — `AxleHoleGauge` docstring calibration procedure: the result is
  a *profile* `slip.radial` value, not a constant override.
- [x] **A6** — `README.md`: add a "## Print Tolerances & Calibration" section
  (deliverable D-README below).
- [x] **A7** — `TODO.md`: deliverable D-TODO below.
- [x] **A8** — Tests: replace test #5 (env override) with a profile-override
  test (`slip.radial` change moves the cutter); update test #3 (cutter is
  4.90 × 4.90 at `fdm_standard` slip, not 4.88).
- [x] **A9** — Update brief Implementation Status.

### Revised Success Criteria (supersede the originals)

1. `AXLE_HOLE_TIP_TO_TIP` (4.80) and `AXLE_HOLE_ARM_WIDTH` (1.83) are plain
   fixed constants — no `os.getenv` — and the dimension source for
   `TechnicAxleHole`.
2. `TechnicAxleHole` uses `nominal + 2*grade.radial`; a `ToleranceProfile`
   with a different `slip.radial` changes the cutter (test-verified).
3. `AxleHoleGauge` builds a single contiguous solid, one labelled round
   through-hole per swept diameter. *(unchanged)*
4. `tools/view.py` / `tools/preview.py` render `AxleHoleGauge`; visual
   contract holds. *(unchanged)*
5. `.env.example`, `docs/lego-technic.md`, and `README.md` describe the
   *profile*-based calibration workflow; no doc references a removed env var.
6. No CI regressions — AGPLv3 headers, no `__main__`, no `ocp_vscode`, linters
   clean. *(unchanged)*

### New deliverables

**D-README** — `README.md`, new "## Print Tolerances & Calibration" section
near "Lego Technic Reference". One short paragraph: printed fits are
printer/material-dependent; the project ships `ToleranceProfile`s in
`machine_profiles.json`; users override per-machine in the gitignored
`machine_profiles_user.json` (and select via `VIBE_MACHINE_PROFILE`);
`AxleHoleGauge` + the procedure in `docs/lego-technic.md` calibrate the Lego
axle slip fit. Brief, link-out — do not duplicate the full procedure.

**D-TODO** — `TODO.md`:
- (a) Tick the existing line-13 item; annotate "Stage 1 (tip-to-tip) resolved
  by `AxleHoleGauge` — see `.agents/plans/2026-05-20-axle-hole-tip-to-tip-gauge`".
- (b) Add: "[ ] Stage 2 — cross-profile axle-hole validation + an explicit
  corner-relief parameter on `TechnicAxleHole` for FDM corner blowout."
- (c) Add: "[ ] Build a guided calibration helper (e.g. `tools/calibrate.py`)
  that walks the user through the `AxleHoleGauge` print + fit test and writes
  the resulting `slip.radial` into `machine_profiles_user.json` — replacing
  the manual print → feel-test → compute → hand-edit-JSON workflow."

### Parked follow-ups (not in scope — for `/memories/session/ideas.md`)

- Migrate `PIN_HOLE_PRINTED` → `PIN_HOLE_DIAMETER` (4.80) nominal + profile,
  same OSS argument as the axle hole.
- Re-baseline `fdm_standard.slip.radial` if a second printer corroborates
  ~0.10 (full all-slip-consumers blast-radius review required).

