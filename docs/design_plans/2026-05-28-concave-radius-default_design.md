# Design: TechnicAxleHole default concave radius — 0.6 → 0.3
<!-- Filename: 2026-05-28-concave-radius-default_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-28-concave-radius-default_req.md`
- **Requester role**: @designer (Admin-relayed; human-confirmed 2026-05-28)
- **Date**: 2026-05-28
- **Dialog rounds**: 3

---

## Objective
Lower `TechnicAxleHole.DEFAULT_CONCAVE_RADIUS` from `0.6` to `0.3` mm,
document the new evidence on the constant and in the kwarg docstring,
annotate the existing `TODO.md` Stage-2c history, and update
`docs/lego-technic.md` — without changing the constructor signature,
the fit envelope, or any profile-level field.

## Architecture / Approach

### Approach chosen

This is a **single kwarg-default bump** plus minimal-surface
documentation reconciliation. Mechanics:

1. **One-line constant edit** in
   `vibe_cading/lego/cutters/technic_axle_hole.py` — flip
   `DEFAULT_CONCAVE_RADIUS: float = 0.6` to `0.3`, with an
   adjacent comment carrying the provenance line.
2. **In-class docstring patch** — the `concave_radius` parameter
   docstring (currently lines 78–80) gains a sentence stating the
   new default and citing the validating evidence.
3. **Class-level docstring patch** — a single short paragraph noting
   that `0.3` is best-current-evidence on one calibrated FDM stack
   (`bambu_p1s + PLA`), not universal, and pointing at the
   `concave_radius=` kwarg as the per-printer override path.
4. **New test file** `tests/test_technic_axle_hole.py` with
   (a) the FR-5 equality assertion and
   (b) a small parametrize smoke that exercises 4 representative
   radii (`0.0`, `0.1`, `0.3`, `0.5`, `0.8`) asserting
   `len(cutter.solids().vals()) == 1` — single-solid guard against a
   future maintainer accidentally setting a radius that produces
   unbuildable edges.
5. **`TODO.md` Stage-2c inline annotation** — the existing
   `"concave_radius 0.6 fillet corner is acceptable; no corner_relief
   parameter needed"` line gets a trailing inline parenthetical
   `"(Followed up 2026-05-28: default lowered to 0.3 mm on
   bambu_p1s + slip.slot 0.1125 — see
   .agents/plans/2026-05-28-concave-radius-default_design.md.)"`.
   Stage-2c text otherwise untouched.
6. **`docs/lego-technic.md` §"Concave-corner blowout — verified
   adequate" reconciliation** — change `(default 0.6 mm)` →
   `(default 0.3 mm)`; preserve the 2026-05-22 confirmation as
   history; append a 2026-05-28 follow-up sentence noting that
   subsequent calibration on `bambu_p1s` (`slip.slot = 0.1125`,
   `slip.radial = 0.11`) showed `0.3` prints clean and is now the
   shipped default.
7. **`docs/print-tolerances.md` §6.1 ("When NOT to add a new field
   to `FitGrade`") gains a final paragraph** capturing the
   geometric-kwarg-vs-profile-field distinction this task
   crystallised. One paragraph, in-place — no new section.

**Cross-model propagation mechanism.** Every `TechnicAxleHole`
consumer that does NOT pass `concave_radius=` explicitly picks up
the new default at next construction — there is no global state,
no cached compiled geometry, no plumbing. Six consumers were
enumerated in the req's NFC-2 section
(`lego_adapters/technic_axle_to_bearing_sleeve.py`, two
`lego_adapters/servos/shaft*.py` files, two
`lego_adapters/servos/sg90/servo_mount*.py` files, and
`lego/gears/gear_28t.py`). None pass `concave_radius=`; all will
get slightly sharper inner-valley corners. Fit envelope is
unaffected — owned by `slip.radial + slip.slot`, both unchanged.
`AxleCrossHoleGauge` is unaffected (replaces the fillet with
dog-bone relief; never reads `DEFAULT_CONCAVE_RADIUS`).

### Visual contract (CAD tasks)

**N/A — scope carve-out.** This is a refactor-class change to a
single kwarg-default constant. The visible geometry change is a
0.3 mm reduction in inner-valley fillet radius on the
`TechnicAxleHole` cross profile; no axis convention, hole pattern,
mating-face datum, or orientation is altered. Per
`vibe/INSTRUCTIONS.md` → "Visual Contract Deliverable" carve-outs:
*"Optional for: refactors, internal API changes, additive-only
changes that don't alter visual outcome, instruction / config /
tooling tasks."* A new SVG would mostly reproduce existing
`TechnicAxleHole` preview output with a barely-perceptible inner
fillet difference — adding it does not catch the failure modes the
rule exists to catch. Skipping is the correct call.

### Alternatives rejected
- **Promoting `concave_radius` to a `FitGrade` field** — explicitly
  rejected in req §"Out of Scope" and `Open Questions Q1` framing;
  violates the "fewer calibration knobs" anchor; the concave fillet
  does not participate in the fit envelope, so it does not belong in
  the profile.
- **`os.getenv("VIBE_AXLE_CONCAVE_RADIUS")` override** — the
  constructor kwarg `concave_radius=` already IS the override path;
  adding env-var plumbing duplicates a public API.
- **Single equality-only test (no smoke parametrize)** — see Dialog
  Round 1. The equality assertion alone does not protect a future
  maintainer from accidentally setting a radius that produces
  unbuildable edges. Smoke at 4 values is ~50 lines, runs in <2 s,
  cheap insurance.
- **Folding the regression assertion into
  `tests/test_technic_pin_hole_profile.py`** — see Dialog Round 3.
  Wrong class, wrong file name, wrong scope; the per-class test
  convention (`test_technic_pin_hole_profile.py`,
  `test_axle_cross_hole_gauge.py`) calls for a new
  `test_technic_axle_hole.py`.
- **Rewriting Stage-2c TODO history** — explicitly forbidden by
  req §"Out of Scope". Inline parenthetical is the house style
  (see TODO.md line 30 "Re-scoped 2026-05-23").

## Data & Interface Contracts

**N/A** — domain integrity gate is NO. Pure geometric kwarg-default
bump; no schema, no field, no protocol, no wire format touched.

**Informational note (not a contract):** The kwarg-default mechanism
works as follows. The default expression in
`def __init__(..., concave_radius: float = DEFAULT_CONCAVE_RADIUS)`
is evaluated once at class-definition time and bound to the
class-level constant `DEFAULT_CONCAVE_RADIUS = 0.3`. Every
constructor call that omits `concave_radius` uses that bound value.
Existing call sites that pass `concave_radius=0.6` (none in-tree as
of 2026-05-28; verify with grep — see T1) remain bit-for-bit
unaffected. No mutable default, no late-binding gotcha.

## Implementation Plan

- [x] **T1** — Grep the workspace for any caller passing
  `concave_radius=` explicitly: `grep -rn "concave_radius=" vibe_cading/ parts/ tools/ tests/ tmp/`.
  Expected result: zero matches in production code paths.
  If any production-code match is found, surface to TL — design
  may need a deviation note. (Probe scripts under `tmp/` are
  informational only.)
- [x] **T2** — Edit
  `vibe_cading/lego/cutters/technic_axle_hole.py`:
  - Line 85: change `DEFAULT_CONCAVE_RADIUS: float = 0.6` to
    `DEFAULT_CONCAVE_RADIUS: float = 0.3` with comment
    `# 0.3 validated 2026-05-28 on bambu_p1s + PLA (slip.slot=0.1125, slip.radial=0.11); was 0.6 pre-2026-05-28 — see tmp/print_concave_sweep_2.py.`
  - Update the `concave_radius:` docstring entry (currently
    lines 78–80) to state the new default and cite the evidence.
  - Add a one-paragraph class-docstring note (after the existing
    "To tune a printed fit…" paragraph at line 46) explaining that
    `0.3` is best-current-evidence on one calibrated FDM stack;
    other printers may override via `concave_radius=`.
- [x] **T3** — Create `tests/test_technic_axle_hole.py` with the
  AGPLv3 header, importing
  `from vibe_cading.lego.cutters.technic_axle_hole import TechnicAxleHole`.
  Two test functions:
  - `test_default_concave_radius_pinned_at_0_3()` — asserts
    `TechnicAxleHole.DEFAULT_CONCAVE_RADIUS == 0.3` AND
    `TechnicAxleHole(depth=8.0).concave_radius == 0.3` (catches
    both constant drift and a constructor-binding regression).
  - `test_axle_hole_builds_single_solid_across_radii(radius)` —
    `pytest.parametrize` over `[0.0, 0.1, 0.3, 0.5, 0.8]`,
    asserting `len(TechnicAxleHole(depth=8.0, concave_radius=radius).to_cutter().solids().vals()) == 1`.
- [x] **T4** — Annotate `TODO.md` Stage-2c entry (line ~27): append
  the inline parenthetical `(Followed up 2026-05-28: default
  lowered to 0.3 mm on bambu_p1s + slip.slot 0.1125 — see
  .agents/plans/2026-05-28-concave-radius-default_design.md.)` to
  the end of the "concave_radius 0.6 fillet corner is acceptable"
  sentence. Do NOT rewrite Stage-2c text.
- [x] **T5** — Update `docs/lego-technic.md` §"Concave-corner
  blowout — verified adequate" (lines 321–333):
  - Line 327: change `(default 0.6 mm)` to `(default 0.3 mm)`.
  - Append a short follow-up sentence after the existing 2026-05-22
    history: `"Follow-up 2026-05-28 on the same printer at a
    re-calibrated slip.slot (0.1125): a 2-variant in-script sweep
    (tmp/print_concave_sweep_2.py) showed 0.30 prints clean while
    0.35 does not, so the shipped default is now 0.3 mm. The
    original 0.6 mm value was acceptable at the prior calibration
    point but consumed more slot wall than needed; 0.3 mm is the
    best-current-evidence point at the calibrated slot."`
- [x] **T6** — Update `docs/print-tolerances.md` §6.1 ("When NOT
  to add a new field to `FitGrade`"): append a one-paragraph note
  on the geometric-kwarg-default vs profile-knob distinction —
  approximately: *"A related anti-pattern: do not promote a
  geometric default (a corner fillet radius, a chamfer size, an
  internal rib width) to a `FitGrade` field just because one
  printer wants a different value. If the parameter does not
  participate in the fit envelope (i.e. it does not enter a
  clearance computation against a mating Lego or hardware
  dimension), it belongs as a per-class constructor kwarg with a
  shipped default — like `TechnicAxleHole.concave_radius`. See
  the 2026-05-28 design dialog
  (.agents/plans/2026-05-28-concave-radius-default_design.md) for
  the worked example."*
- [x] **T7** — Run the new test file: `python3 -m pytest tests/test_technic_axle_hole.py -v` — expect 6 passes (1 + 5 parametrize). Run the existing suite for collateral check: `python3 -m pytest tests/ -q`.
- [x] **T8** — Run `python3 tools/preview.py vibe_cading.lego.cutters.technic_axle_hole.TechnicAxleHole --views top iso_ne` and verify the inner-valley corners are visibly sharper (~half the prior fillet radius) — informational check, not a gate.

## Tests

| # | Test description | Expected assertion | File / location | FR coverage |
|---|------------------|--------------------|-----------------|-------------|
| 1 | Default constant pinned at 0.3 (catches constant drift) | `TechnicAxleHole.DEFAULT_CONCAVE_RADIUS == 0.3` | `tests/test_technic_axle_hole.py::test_default_concave_radius_pinned_at_0_3` | FR-1, FR-5 |
| 2 | Constructor default bound to constant (catches signature-default regression) | `TechnicAxleHole(depth=8.0).concave_radius == 0.3` | `tests/test_technic_axle_hole.py::test_default_concave_radius_pinned_at_0_3` | FR-5 |
| 3 | Builds single contiguous solid at 5 radii spanning realistic range | `len(TechnicAxleHole(depth=8.0, concave_radius=r).to_cutter().solids().vals()) == 1` for `r ∈ {0.0, 0.1, 0.3, 0.5, 0.8}` | `tests/test_technic_axle_hole.py::test_axle_hole_builds_single_solid_across_radii` | smoke (defense-in-depth on FR-1, FR-4) |
| 4 | Docstring states new default + cites evidence | Manual reviewer check at TL post-impl review | `vibe_cading/lego/cutters/technic_axle_hole.py` class docstring + `concave_radius:` entry | FR-2, FR-3 |
| 5 | TODO.md Stage-2c annotated, history preserved | Manual reviewer check — inline parenthetical present, Stage-2c text unchanged | `TODO.md` Stage-2c entry (lines 24–29) | FR-6 |
| 6 | `docs/lego-technic.md` §concave-corner narrative reconciled | Manual reviewer check — `(default 0.3 mm)` + 2026-05-28 follow-up paragraph present | `docs/lego-technic.md` lines 321–333 | FR-7 |
| 7 | Full existing test suite passes (no collateral regression) | All previously-passing tests still pass; in particular `tests/test_technic_pin_hole_profile.py` T9b snapshot unchanged | `tests/` | NFC backward-compat |

## Success Criteria
1. `TechnicAxleHole.DEFAULT_CONCAVE_RADIUS == 0.3` (FR-1, T1).
2. `tests/test_technic_axle_hole.py` exists and all 6 test cases (1 equality + 5 parametrize) pass under `pytest -v` (FR-5, T7).
3. `python3 -m pytest tests/` exits zero on the modified tree (no collateral regression in the existing 12 test files).
4. The `concave_radius` kwarg docstring entry in `technic_axle_hole.py` cites the 2026-05-28 / `bambu_p1s + PLA` evidence (FR-2).
5. Class-level docstring carries the "best-current-evidence on one calibrated FDM stack" caveat and points at `concave_radius=` as the per-printer override (FR-3).
6. `TODO.md` Stage-2c entry retains its original text verbatim, with a 2026-05-28 inline parenthetical appended (FR-6).
7. `docs/lego-technic.md` §"Concave-corner blowout — verified adequate" shows `(default 0.3 mm)` and a reconciled narrative (2026-05-22 history preserved, 2026-05-28 follow-up appended) (FR-7).
8. `docs/print-tolerances.md` §6.1 gains the geometric-kwarg-vs-profile-field paragraph (Q4 resolution).
9. `tools/preview.py vibe_cading.lego.cutters.technic_axle_hole.TechnicAxleHole` succeeds and produces visibly sharper inner corners (informational — not a gate).

## Out of Scope
Mirrored from req with no expansion:
- No `FitGrade.corner_radius` field promotion.
- No `os.getenv` override for `concave_radius`.
- No change to `AXLE_HOLE_TIP_TO_TIP`, `AXLE_HOLE_ARM_WIDTH`,
  `slip.radial`, `slip.slot`, or any `_FALLBACK_PROFILES` value.
- No change to `AxleCrossHoleGauge`.
- No `tools/calibrate.py` extension.
- No new public API.
- No rewrite of Stage-2c history.

## Known Risks & Mitigations

| Risk | Predicted cost if it fires | Mitigation |
|------|----------------------------|-----------|
| A consumer down-tree relies on the 0.6 mm geometric profile in a way that breaks at 0.3 mm (e.g. a tightly-toleranced cosmetic clearance, a thin wall newly exposed by the sharper corner). | One re-print + a one-line `concave_radius=0.6` override at the consumer site; no released asset affected. | T1 grep enumerates current callers (expected zero). NFC-2 in the req walked all 6 consumers and confirmed none participates in fit-envelope dimensioning. |
| OCCT fails to build the fillet at one of the parametrize values (e.g. `0.0` boundary, `0.8` near edge length). | One test-suite red flag during T7; trivial fix (drop the offending value or adjust to a buildable one). | The 5 chosen values were picked to span the realistic-use range; `0.0` is the documented skip-path; `0.8` < `AXLE_HOLE_ARM_WIDTH/2` so geometrically buildable. If T7 fails on `0.0` or `0.8`, narrow the parametrize set rather than expand. |
| A future maintainer "rolls back" the default to 0.6 thinking the 2026-05-22 Stage-2c entry is current. | Re-discovery cycle ~30 min from a confused contributor; possible mis-tuned-default print. | Belt-and-braces: (a) constant-comment provenance line (visible to grep `0.3`), (b) updated kwarg docstring (visible to IDE hover), (c) annotated TODO Stage-2c (visible to anyone walking the calibration history), (d) reconciled `docs/lego-technic.md` paragraph, (e) regression test that fails if the default flips. |
| The smoke parametrize test (5 values × constructor + fillet) measurably slows the suite. | <2 s estimated based on existing `TechnicAxleHole` build times in `tests/test_axle_cross_hole_gauge.py`; tolerable. If it pushes test-suite wall-clock noticeably, trim to 3 values (`0.1`, `0.3`, `0.5`). | Run T7 and measure; trim only if measured cost exceeds ~5 s. |

---

## Design Dialog Log

### Round 1 — Test depth (Q3 resolution)

**TL proposal:**
> Ship FR-5 equality assertion alone. The req mandates only the
> equality; designer's Q3-(a) "smoke parametrize at multiple radii"
> is OPTIONAL. Keep the new test file minimal — single assertion,
> single function, no parametrize ceremony. Smoke can be added in a
> follow-up if a future regression surfaces.

**Requester challenge / contribution:**
> The equality assertion catches the *value* drift but not the
> *buildability* class of regression. A future maintainer who
> needs a sharper or more rounded corner for a derived class could
> set a radius that produces OCCT-unbuildable edges (e.g.
> `concave_radius` ≥ `ARM_WIDTH/2 = 0.915 mm` (per
> `vibe_cading/lego/constants.py:102`, `AXLE_HOLE_ARM_WIDTH = 1.83`)
> would over-round the inner valley into self-intersection — note
> the `0.8` smoke ceiling therefore sits only `0.115 mm` below
> this bound, not the wider margin the original draft implied;
> Risk row 2's "drop offending value if T7 fails" recovery still
> covers it). Such a regression would
> NOT trip the equality test — it would trip whatever downstream
> `_build()` call exercises the new default, with no clear pointer
> back to this constant. The marginal cost is ~30 lines and
> sub-2-second runtime; the marginal protection is "if you change
> this default, the test file independently proves the new value
> is buildable, AND proves four other points along the realistic
> usage range still work."

**Resolution:**
> Adopt Q3-(a) smoke parametrize at `[0.0, 0.1, 0.3, 0.5, 0.8]` —
> spans the skip-fillet boundary (0.0), the sweep low-water-mark
> (0.1), the new default (0.3), the prior shipped default (0.5
> as a proxy for 0.6 to stay clear of the upper buildability
> envelope), and a higher-radius point (0.8). Skip Q3-(b) —
> default-vs-explicit equivalence is logically implied by the
> equality assertion in test #1 and adds no independent coverage.
> Updates Tests table rows #1–#3.

### Round 2 — Citation locus (Q1 resolution)

**TL proposal:**
> Adopt designer's recommendation (d): one-line comment on the
> constant + updated kwarg docstring. Walking the contributor's
> grep flow:
>
> - A contributor changing the default greps `DEFAULT_CONCAVE_RADIUS`
>   → lands on line 85 → adjacent comment immediately shows
>   "0.3 validated 2026-05-28 on bambu_p1s; was 0.6 pre-2026-05-28
>   — see tmp/print_concave_sweep_2.py" — they understand the
>   provenance without leaving the file.
> - A user reading IDE hover on `concave_radius=` parameter →
>   gets the updated docstring line citing the same evidence.
> - A maintainer auditing calibration history → grep
>   `concave_radius` in `docs/` or `TODO.md` → lands on the
>   `docs/lego-technic.md` reconciled paragraph or the TODO
>   inline annotation.
>
> Three locations all carry the date + machine + slot context; no
> location is the single source of truth, but each is sufficient
> for its audience.

**Requester challenge / contribution:**
> Concern: three locations risk drift on future re-calibration
> (one gets updated, others stale). Counter-argument: the test
> assertion is the *machine-readable* source of truth — if the
> default flips, test #1 fails and the contributor MUST touch the
> constant + comment in the same commit. The docstring and
> `docs/lego-technic.md` paragraph are not enforced, but the
> annual `bump-review` / `post-change-review` flow would surface
> stale citations. Accept the recommendation; flag the drift risk
> as a Known Risk row (last row in the table).

**Resolution:**
> Adopt (d). Provenance lives in: (1) in-code comment on the
> constant, (2) updated `concave_radius:` kwarg docstring,
> (3) class-level docstring caveat, (4) `TODO.md` Stage-2c
> inline annotation, (5) `docs/lego-technic.md` §concave-corner
> reconciled paragraph. The test is the enforcement point;
> documentation locations are the contributor-discoverability
> layer. Drift risk captured in Known Risks (row 3).

### Round 3 — Test file placement (Q5) + Q2 (TODO annotation form) + Q4 (print-tolerances cross-ref)

**TL proposal:**
> Resolve the three remaining open questions in one round:
>
> - **Q5 (test file placement):** grep `tests/test_technic*`
>   returns `tests/test_technic_pin_hole_profile.py` and
>   `tests/test_technic_beam.py`. No `test_technic_axle_hole.py`.
>   Per-class convention is unambiguous — create
>   `tests/test_technic_axle_hole.py`. Do NOT fold into the
>   pin-hole file (wrong class, wrong scope; T9b snapshot pins
>   pin-hole bore values, not axle-hole corner geometry; mixing
>   surfaces would dilute the focused "pin hole bore consumer
>   contract" purpose of that file).
>
> - **Q2 (TODO annotation form):** Inline parenthetical with a
>   `Followed up YYYY-MM-DD:` prefix. Matches TODO.md line 30
>   "Re-scoped 2026-05-23" house style. No new bullet, no
>   footnote.
>
> - **Q4 (print-tolerances §6 cross-ref):** Add the
>   geometric-kwarg-vs-profile-field paragraph to §6.1 ("When NOT
>   to add a new field to `FitGrade`") as a one-paragraph
>   in-place addition. Do NOT split into a follow-up doc task —
>   the rule was crystallised by *this* design dialog, the
>   evidence is *this* design artifact; deferring loses the
>   coupling. One-paragraph addition is in-scope (test depth: 0
>   new tests; surface: 1 doc paragraph). Worth flagging: this
>   adds a 7th implementation task (T6) and a 6th success
>   criterion (#8) — accept the marginal scope.

**Requester challenge / contribution:**
> Q5 and Q2 land cleanly. Q4 — push back on a subtle point: the
> §6.1 paragraph as drafted in the proposal mentions
> "TechnicAxleHole.concave_radius" by name as the worked example.
> That couples §6.1 to a specific class; if `TechnicAxleHole` is
> ever renamed or refactored, the doc reference goes stale.
> Counter-argument: the same coupling already exists throughout
> §6 (mentions of `TechnicPinHole`, `MetricMachineScrew`); the
> doc's pattern is to name concrete examples. Accept the coupling
> as house-consistent. No revision.

**Resolution:**
> All three Open Questions resolved.
>
> - **Q2** → inline parenthetical, `Followed up YYYY-MM-DD:` prefix.
> - **Q4** → one-paragraph addition to `docs/print-tolerances.md` §6.1 (in-scope, T6).
> - **Q5** → new `tests/test_technic_axle_hole.py` (per-class convention).
>
> Decision on the *additional architectural question* raised in
> the TL spawn brief (snapshot resolved arm/tip dimensions in the
> new test file?): **NO**. T9b in
> `tests/test_tolerance_profile.py` pins `_FALLBACK_PROFILES`
> and `tests/test_technic_pin_hole_profile.py` pins the pin-hole
> consumer formula. A parallel `(tip, arm)` snapshot in
> `test_technic_axle_hole.py` would duplicate the *profile-side*
> coverage (T9b) without adding independent regression surface
> for *this* task's change (the concave radius default). If a
> future change touches `AXLE_HOLE_TIP_TO_TIP` /
> `AXLE_HOLE_ARM_WIDTH` / `cq_utils.axle_cross_section`, that's
> a separate design and would carry its own snapshot in a
> separate test function. Keep the new file scoped to
> concave-radius behaviour.

### Round 4 — Condition application (2026-05-28)

**Context:** Step 3.5 fresh-context independent reviewers returned
APPROVE-WITH-CONDITIONS (Independent TL) and APPROVE-WITH-COMMENT
(Independent Developer). Drafting TL applied two surgical fixes
inline before re-spawning Step 3.5.

**C1 — Consumer inventory correction (Independent TL, blocking).**
Re-ran `grep -rn "TechnicAxleHole(" vibe_cading/ --include="*.py"`:
6 production call sites + 1 docstring example
(`technic_axle_hole.py:56`). Production set:
`lego_adapters/servos/shaft.py:96`,
`lego_adapters/servos/shaft_body.py:218`,
`lego_adapters/technic_axle_to_bearing_sleeve.py:90`,
`lego_adapters/servos/sg90/servo_mount.py:411`,
`lego_adapters/servos/sg90/servo_mount_half.py:374`,
`lego/gears/gear_28t.py:50`. `vibe_cading/mechanical/tolerance_gauge.py`
has ZERO `TechnicAxleHole` references — the original cite was
wrong. Count of 6 stands; membership corrected in both
req §NFC-2 (Backward compatibility / geometry) and design
§"Cross-model propagation mechanism". Load-bearing conclusion
(no consumer passes `concave_radius=`; fit envelope unaffected)
re-verified and survives.

**C2 — Dialog Round 1 math correction (both reviewers,
non-blocking).** Confirmed `AXLE_HOLE_ARM_WIDTH = 1.83` at
`vibe_cading/lego/constants.py:102` → `ARM_WIDTH/2 = 0.915 mm`,
not the `≈ 1.125 mm` the original Round 1 draft cited. Replaced
in-place inside the Round 1 Requester-challenge block;
clarified that the `0.8` upper smoke bound has only `0.115 mm`
headroom (not `~0.325 mm`). Risk row 2's "drop offending value
if T7 fails" recovery remains valid — no deliverable text
changes.

**Scope discipline:** ONLY C1 + C2 applied. No new discoveries,
no scope expansion. Reviewer sections (Independent TL,
Independent Developer) left untouched — they re-render on
re-spawn. Author sign-off state unchanged.

---

## Module-depth ledger

| Module / class | Action | Depth (lens a + lens b) |
|----------------|--------|-------------------------|
| N/A — no new module, no new class | — | One-line constant edit + a new test file containing two test functions in a single module. No abstraction added or removed; depth analysis does not apply. |

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(required if domain integrity gate is YES; skip if NO)*  — **N/A** (gate is NO)
- [x] Requester sign-off  *(Designer-relayed; req human-approved 2026-05-28)*
- [x] TL sign-off

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE (2026-05-28, re-confirmed after applying C1 + C2; see `## Independent TL Review` below)
- [x] Independent Developer  *(always required)* — APPROVE (2026-05-28, re-confirmed after `ARM_WIDTH/2` math correction; see `## Independent Developer Review` below)
- [ ] Independent Researcher  *(required if domain integrity gate is YES; skip if NO)*  — **N/A** (gate is NO)

---

## Implementation Status
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: **291 passed, 2 xfailed, 0 failed** (full `pytest tests/ -v`, 121.5 s wall-clock); new `tests/test_technic_axle_hole.py` contributes 6 passes (1 equality + 5 parametrize smoke); regression-critical files (`tests/test_tolerance_profile.py`, `tests/test_technic_pin_hole_profile.py`, `tests/test_technic_beam.py`) are byte-identical to `main` (zero git-diff stat) — T9b 27-leaf profile snapshot and pin-hole bore consumer contract both unchanged.
- [x] No new linter / static-check errors — `flake8 vibe_cading/lego/cutters/technic_axle_hole.py tests/test_technic_axle_hole.py` clean; `tools/check_license_headers.py`, `tools/check_no_main_blocks.py` pass; `tools/check_topology.py vibe_cading.lego.cutters.technic_axle_hole.TechnicAxleHole --params depth=8.0` returns `[PASS] Topology is contiguous. Found 1 solid(s)`.
- Developer note: T1 grep confirmed zero `concave_radius=` callers in production code (none of the 6 downstream consumers passes the kwarg explicitly — they all pick up the new `0.3` default at next construction). `engine_api.json` diff is minimal and additive: 1 line changed, only the `TechnicAxleHole` docstring updated (extractor surfaces docstrings but not literal kwarg-default values, so the constant flip itself does not propagate to the wire format). FR-5 enforcement verified live: `TechnicAxleHole(depth=8.0).concave_radius == 0.3`. T8 preview SVGs regenerated to `tmp/preview/TechnicAxleHole_{top,iso_ne}.svg` — inner-valley corners visibly sharper than the prior 0.6 mm fillet, as expected.

---

## Independent Developer Review (fresh context, 2026-05-28)

**Verdict:** APPROVE — implementable as written; prior numeric note on the smoke-test upper bound has been addressed inline.

**Strengths:**
1. T1–T8 are atomic with clear deliverables; line-number citations all match (`technic_axle_hole.py:85` constant, TODO.md:24–29 Stage-2c, `docs/lego-technic.md:321–333`, `docs/print-tolerances.md` §6 / `### When NOT to add a new field to FitGrade` at L244).
2. Five-value parametrize is well-chosen at the `0.0` skip boundary: code at L137 (`if self.concave_radius > 0`) skips the fillet entirely at `0.0`, so the build path is exercised cleanly.
3. Risk row 2 already names the OCCT-buildability failure mode for boundary values and prescribes the trim-not-expand recovery — Developer can act without escalating if T7 reds at an endpoint.

**Open concerns (non-blocking):**
- Dialog Round 1 (L256-258) states `ARM_WIDTH/2 ≈ 1.125 mm`. Actual `AXLE_HOLE_ARM_WIDTH = 1.83 mm` (`vibe_cading/lego/constants.py:102`), so `ARM_WIDTH/2 = 0.915 mm`. The `0.8` upper smoke-test value therefore has only `0.115 mm` headroom (not `~0.325 mm`). Still likely buildable; if T7 reds on `0.8`, the design-prescribed recovery (drop the offending value) applies — but Developer should be aware the upper-bound margin is roughly 3× tighter than the design framed it.

**Conditions:** None blocking. The numeric discrepancy in Round 1's stated bound does not change any deliverable text; the test recovery path is already in Risk row 2.

**Verification log:**
- Read `technic_axle_hole.py` L1-150: constant at L85 = `0.6` (matches); docstring at L75-81 (matches); `if self.concave_radius > 0` guard at L137 (confirms `0.0` is a clean skip path).
- Read `TODO.md` L20-34: Stage-2c entry at L24-29 with the exact `concave_radius 0.6 fillet corner is acceptable` text the design targets; Re-scoped 2026-05-23 house-style precedent at L30.
- Read `docs/lego-technic.md` L318-333: `(default 0.6 mm)` at L327-328 (matches design's edit target); 2026-05-22 confirmation narrative present.
- Listed `tests/`: no `test_technic_axle_hole.py` collision; per-class convention holds.
- `docs/print-tolerances.md`: `## 6.` at L226, `### When NOT to add a new field to FitGrade` at L244 (the design's §6.1 informal label).
- `vibe_cading/lego/constants.py:101-102`: `AXLE_HOLE_TIP_TO_TIP=4.80`, `AXLE_HOLE_ARM_WIDTH=1.83` → drives the `0.915 mm` correction above.

**Re-confirmed 2026-05-28:** ARM_WIDTH/2 math correction applied (1.125 → 0.915 mm); verdict upgraded to APPROVE.

---

## Independent TL Review (fresh context, 2026-05-28)

**Verdict:** APPROVE

**Strengths:**
1. Scope is genuinely surgical — one constant edit + one new test file + three doc reconciliations; anti-scope (`FitGrade`, `_FALLBACK_PROFILES`, `AxleCrossHoleGauge`, `slip.radial`, `slip.slot`, `axle_cross_section`) is respected throughout. T6 adds a *doc* paragraph about `FitGrade` placement — it does not touch the `FitGrade` code surface.
2. Provenance is multi-locus (constant comment, kwarg docstring, class docstring, `TODO.md` annotation, `docs/lego-technic.md` paragraph) and the enforcement point (the equality test) is correctly identified as the machine-readable source of truth, with the drift risk captured in Known Risks row 3.
3. Q3 dialog (smoke parametrize) earns its keep — the upper-bound buildability argument is real and the equality assertion alone would not catch it. (Independent Developer reviewer's note that the upper-bound margin is `0.115 mm` not `0.325 mm` strengthens, not weakens, the value of having the smoke test.)

**Conditions (must address before Step-5 Phase A kickoff):**

1. **Consumer inventory is factually wrong.** Design §"Cross-model propagation mechanism" (lines 67–69) and req §NFC-2 enumerate the 6 consumers as `tolerance_gauge.py`, `technic_axle_to_bearing_sleeve.py`, two `shaft*.py`, two `servo_mount*.py`. Verified live: `grep -rn "TechnicAxleHole(" vibe_cading/` returns 7 hits — 1 docstring example (`technic_axle_hole.py:56`) plus **6 production call sites**, but `tolerance_gauge.py` is **NOT** one of them. `grep "TechnicAxleHole\|concave_radius" vibe_cading/mechanical/tolerance_gauge.py` returns empty. The actual 6th consumer is `vibe_cading/lego/gears/gear_28t.py:50` (`TechnicAxleHole(depth=self.face_width + 1.0).solid.translate(...)`) — also does not pass `concave_radius=`, so the load-bearing conclusion (no consumer passes `concave_radius=`; fit envelope unaffected) survives. But the enumerated names must be fixed in BOTH the req NFC-2 paragraph AND the design §"Cross-model propagation mechanism" so a downstream maintainer audit grep does not chase a non-existent `tolerance_gauge.py` consumer. Predicted cost if not fixed: ~15 min of a future contributor's time chasing a phantom citation, possibly compounded if they assume the rest of the inventory is similarly unreliable. Mechanical fix: replace `tolerance_gauge.py` with `vibe_cading/lego/gears/gear_28t.py` in both files.

**Open concerns (non-blocking, with predicted cost):**

- **FR-4 (constructor signature unchanged) has no explicit Tests-table row.** Predicted cost if it fires: silent signature regression slips past CI; downstream `shaft.py` / `servo_mount.py` callers (positional+kwarg form) break at next refactor. Cost: one print + one revert commit. Mitigation: trivial — T3's `TechnicAxleHole(depth=8.0).concave_radius == 0.3` exercises the no-kwarg construction path and would fail loudly on a signature change. Acceptable to leave implicit; flagging for completeness.
- **T8 (preview check) is informational-only.** Predicted cost: if a Phase-A developer accidentally lands a no-op edit (e.g. patches the docstring but not the constant), test #1 catches it — so the cost is bounded to "wasted preview run, no escaped defect". Acceptable.
- **Dialog Round 1's stated `ARM_WIDTH/2 ≈ 1.125 mm` is numerically wrong** (per the Independent Developer Review verification log — actual `AXLE_HOLE_ARM_WIDTH = 1.83 mm` ⇒ `ARM_WIDTH/2 = 0.915 mm`). Predicted cost: if T7 reds on the `0.8` smoke value, the design-prescribed recovery (trim the offending value) already applies; no escaped defect. Worth annotating in the dialog log if a fix touch is going in for Condition 1 anyway, but does not change any deliverable.

**Verification log:**
- Read `vibe_cading/lego/cutters/technic_axle_hole.py` lines 40–149 — confirmed `DEFAULT_CONCAVE_RADIUS: float = 0.6` at line 85, docstring `concave_radius:` entry at lines 78–80, class-docstring "To tune a printed fit" paragraph at line 46. All design path:line citations match live source.
- Read `TODO.md` lines 20–34 — confirmed Stage-2c entry at lines 24–29 with the verbatim text "concave_radius 0.6 fillet corner is acceptable; no corner_relief parameter needed". TODO line 30 "Re-scoped 2026-05-23" inline parenthetical pattern confirms the house style cited in Q2.
- Read `docs/lego-technic.md` lines 315–333 — confirmed §"Concave-corner blowout — verified adequate" at lines 321–333; the parenthetical `(default 0.6 mm)` is at line 327–328 (matches design's `Line 327` claim within wrap rounding).
- `grep -rn "TechnicAxleHole(" vibe_cading/` — 7 hits, 6 production call sites + 1 docstring example. Production set: `shaft.py:96`, `shaft_body.py:218`, `technic_axle_to_bearing_sleeve.py:90`, `servo_mount_half.py:374`, `servo_mount.py:411`, `gear_28t.py:50`. Count matches design (6); membership diverges → Condition 1.
- `grep "concave_radius" vibe_cading/ parts/ tools/ tests/` — only in-class definitions and the docstring; zero production call sites pass `concave_radius=` explicitly, confirming the design's T1 expected-result and the load-bearing "none passes the kwarg" assertion.
- Scope grep on design — `_FALLBACK_PROFILES` (1 mention, "Out of Scope"), `FitGrade` (5 mentions, all as N/A or rejected-alternative or docs-paragraph-about-it), `AxleCrossHoleGauge` (1 mention, "unaffected"), `axle_cross_section` (1 mention, "separate design"). Anti-scope respected.
- Open Questions Q1–Q5 — all resolved across Dialog Rounds 1 (Q3), 2 (Q1), 3 (Q2, Q4, Q5). ✓
- Module-depth ledger present with N/A + reasoning (no new module, no new class). ✓
- "Data & Interface Contracts" section is N/A as expected (domain integrity gate is NO); only an informational note about default-binding mechanics, not a contract. ✓

**Re-confirmed 2026-05-28:** conditions C1 + C2 applied; verdict upgraded to APPROVE.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- **Verdict:** PASS — implementation matches the signed design contract bit-for-bit; all FRs verified live; regression baselines hold; scope is surgical and inside the Touchpoint inventory.
- **Conditions:** None.
- **Open concerns (with predicted cost):**
  - `tools/check_topology.py` emits a `VIBE_MACHINE_PROFILE is deprecated` notice on every invocation in this session — pre-existing on `origin/main`, NOT introduced by this PR. Predicted cost if unaddressed before OSS release: contributors confused by deprecation noise in their first-run gate output; ~5 min of head-scratching per new contributor. Out of scope for this PR; track separately if not already on the OSS-prep list.
- **Verification log:**
  - **Touchpoint inventory:** `git status --short` shows exactly 5 modified + 1 untracked: `TODO.md`, `docs/lego-technic.md`, `docs/print-tolerances.md`, `engine_api.json`, `vibe_cading/lego/cutters/technic_axle_hole.py`, `tests/test_technic_axle_hole.py` (new). Matches design Touchpoint inventory; no scope creep.
  - **FR1 (constant flip):** `technic_axle_hole.py:104` shows `DEFAULT_CONCAVE_RADIUS: float = 0.3` with the 3-line provenance comment above (lines 99-103) citing `2026-05-28 on bambu_p1s + PLA (slip.slot=0.1125, slip.radial=0.11)` and `tmp/print_concave_sweep_2.py`. PASS.
  - **FR2 (kwarg docstring evidence cite):** lines 87-94 contain the date, machine, material, slip values, and sweep-script reference. PASS.
  - **FR3 (class docstring caveat + override path):** lines 52-59 of class docstring carry "best-current-evidence on one calibrated FDM stack" caveat and point at the `concave_radius=` constructor kwarg. PASS.
  - **FR4 (signature byte-identical):** `git diff vibe_cading/lego/cutters/technic_axle_hole.py` shows no change to the `def __init__(...)` block; only the `DEFAULT_CONCAVE_RADIUS` value (and adjacent comment) changed. Signature line is byte-identical. PASS.
  - **FR5 (regression test):** `tests/test_technic_axle_hole.py::test_default_concave_radius_pinned_at_0_3` asserts both `TechnicAxleHole.DEFAULT_CONCAVE_RADIUS == 0.3` and `TechnicAxleHole(depth=8.0).concave_radius == 0.3`. PASS.
  - **FR6 (TODO annotation):** `TODO.md` lines 24-29 retain Stage-2c text verbatim; lines 30-32 add inline parenthetical `(Followed up 2026-05-28: ...)` with the design-artifact link. PASS — house style matches Re-scoped 2026-05-23 precedent.
  - **FR7 (docs/lego-technic.md):** line 328 reads `(default 0.3 mm)`; lines 335-340 append the 2026-05-28 narrative referencing `tmp/print_concave_sweep_2.py` and the calibration context. 2026-05-22 history preserved. PASS.
  - **Q1 five-location citation:** verified all 5 — constant comment (FR1), kwarg docstring (FR2), class docstring (FR3), TODO annotation (FR6), lego-technic.md (FR7). PASS.
  - **Q3 test depth:** `pytest.parametrize` covers exactly `[0.0, 0.1, 0.3, 0.5, 0.8]` (test_technic_axle_hole.py:54). PASS.
  - **Q4 print-tolerances.md §6.1:** line 255 contains the one-paragraph geometric-kwarg-vs-profile-field rule with the `2026-05-28 design dialog` reference. PASS.
  - **Q5 test file location:** new file `tests/test_technic_axle_hole.py` (not folded into pin-hole). PASS.
  - **Test gate:** `python3 -m pytest tests/ -q` → `291 passed, 2 xfailed, 12 warnings in 142.63s`. Matches Developer claim. PASS.
  - **Snapshot guards:** `git diff origin/main -- tests/test_technic_pin_hole_profile.py tests/test_technic_beam.py` returns empty — both files byte-identical (T9b 27-leaf snapshot intact). PASS.
  - **Consumer smoke:** `python3 tools/check_topology.py vibe_cading.lego.gears.gear_28t.LegoGear28T` → `[PASS] Topology is contiguous. Found 1 solid(s)`. Production consumer builds cleanly with the new default. PASS.
  - **Consumer imports:** all 4 module families enumerated in design §"Cross-model propagation mechanism" (servos/shaft\*, technic_axle_to_bearing_sleeve, servos/sg90/servo_mount\*, gears/gear_28t) import without error. PASS.
  - **Engine API diff:** `git diff engine_api.json` shows exactly one `doc` field updated for `TechnicAxleHole` — additive docstring text only; no kwarg-default surfacing (matches design prediction in Implementation Status). PASS.
  - **Strict-ops gates:** `flake8 vibe_cading/lego/cutters/technic_axle_hole.py tests/test_technic_axle_hole.py` clean; `check_license_headers.py` → `All Python files have the AGPLv3 license header.`; `check_no_main_blocks.py` → `OK`; `check_topology.py ...TechnicAxleHole --params depth=8.0` → `[PASS]`. PASS.
  - **AGPLv3 header on new test file:** `tests/test_technic_axle_hole.py:1-14` carries the standard 14-line header. PASS.
  - **Implementation Plan completion:** T1-T8 all `[x]`; spot-checked T2 (constant + comment), T3 (test file content + parametrize values), T4 (TODO annotation), T5 (lego-technic.md edit + append), T7 (291 passed). Five-of-five spot-checks back T1-T8 with live evidence. PASS.

### Domain Expert Review *(required if domain integrity gate is YES; skip if NO)*
- N/A (gate is NO)

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:
