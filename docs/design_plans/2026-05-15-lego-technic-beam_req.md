# Requirements: First-party `LegoTechnicBeam` class
<!-- Filename: 2026-05-15-lego-technic-beam_req.md  (tracked in git under .agents/plans/) -->

## Meta
- **Initiator role**: @designer (Discovery complete; encoding locked-in resolutions)
- **Date**: 2026-05-15
- **Domain integrity gate**: NO

> Rationale for NO: this task adds one new first-party model class
> (`LegoTechnicBeam`) under `vibe_cading/lego/` that consumes the existing
> `TechnicPinHole.standard().to_cutter()` cutter surface, plus three new
> nominal-geometry constants in `vibe_cading/lego/constants.py`. It does
> not alter any data contract, class hierarchy, tolerance-profile schema,
> cutter protocol, `build.toml` shape, or coordinate convention. The new
> constants are reference-geometry floats that mirror the existing pattern
> at lines 32–49 of `constants.py` (e.g. `STUD_PITCH`, `AXLE_TIP_TO_TIP`)
> — they widen the dimension table by three rows, they do not change the
> table's shape.

---

## Problem Statement

A first-party `LegoTechnicBeam` class does not exist in `vibe_cading/lego/`.
Today the only Lego primitives shipped are `TechnicAxle`,
`TechnicAxleHole`, `TechnicAxleToBearingSleeve`, plus the
`vibe_cading/lego/cutters/` family (notably `TechnicPinHole`). The README
Models table and the `vibe_cading/lego/` package both lack the single most
recognizable Lego Technic primitive — the studless liftarm beam.

This gap is felt acutely downstream: FR13 of
[`.agents/plans/2026-05-15-examples-directory_req.md`](2026-05-15-examples-directory_req.md)
currently mandates that `examples/lego_technic_beam.py` build its beam from
`vibe_cading/lego/constants.py` primitives + raw CadQuery, **explicitly
because no `LegoTechnicBeam` class exists**. That example becomes a
five-line `LegoTechnicBeam(length_in_studs=5).solid` invocation the moment
this class lands, materially improving the first-time OSS reader's signal
from the constants-and-raw-primitives composition to a real first-party
class. This task closes the gap before the examples task resumes from its
human-gate pause.

## User Story / Motivation

As an **OSS contributor or RC-Lego adapter author** consuming
`vibe_cading.lego`, I need **a first-party `LegoTechnicBeam` class that
produces a stud-grid-aligned studless liftarm body with uniform Technic
pin holes**, so that **I can compose Technic beams into larger assemblies
(adapters, brackets, jigs) without re-deriving the beam geometry or
re-implementing the pin-hole pattern from `constants.py` every time**.

Secondary motivation: this class **unblocks FR13 of
[`2026-05-15-examples-directory_req.md`](2026-05-15-examples-directory_req.md)**.
When `examples/` resumes from its human-gate pause, the `lego_technic_beam.py`
example will be updated to import and instantiate this class directly; the
FR13 wording itself ("MUST build its beam by composing constants ... with
raw CadQuery primitives") will be revised at that time to reflect the new
first-party surface.

## Functional Requirements

<!-- Numbered, unambiguous, testable. Use "MUST" or "MUST NOT" language. -->

1. **File target.** A new file **MUST** be created at
   `vibe_cading/lego/technic_beam.py`, sibling to `technic_axle.py`. It
   **MUST** carry the AGPLv3 header (identical wording to
   `technic_axle.py`'s header). It **MUST NOT** contain an
   `if __name__ == "__main__":` block (CI rule from
   `tools/check_no_main_blocks.py` applies to `vibe_cading/**`).

2. **Class name and shape.** The file **MUST** define one public class
   `LegoTechnicBeam` representing a **studless (liftarm-style)** Technic
   beam. Studded beams are explicitly out of scope (see Out of Scope).
   The class **MUST** follow the project's `vibe_cading/lego/technic_axle.py`
   precedent (single class, `_build()` private helper,
   `.solid` property, demo classmethod where applicable).

3. **Primary constructor parameter.** The class **MUST** accept a
   positional / keyword parameter `length_in_studs: int` (positive
   integer ≥ 1). Beam length in millimetres **MUST** equal
   `length_in_studs * STUD_PITCH` (i.e. `length_in_studs * 8.0`). The
   constructor **MUST** raise `ValueError` (or equivalent typed error)
   if `length_in_studs < 1`.

4. **Classmethod factory mirror.** *(Adjusted from spawn brief during
   verification.)* The class **MUST NOT** ship a `from_studs(cls, n)`
   classmethod. The current `vibe_cading/lego/technic_axle.py` precedent
   uses a bare constructor parameter (`TechnicAxle(studs=N)`) with no
   classmethod factory — see `technic_axle.py:55`. To mirror that
   precedent exactly, `LegoTechnicBeam(length_in_studs=N)` is the sole
   entry point. A `from_studs` classmethod can be added in a future
   ergonomic pass alongside an equivalent `TechnicAxle.from_studs(...)`,
   under a single "lego factory ergonomics" task — not piecewise here.
   *(See Meta-note in the discrepancy log below.)*

5. **Cross-section and axis convention.** The beam body **MUST** have a
   **square cross-section** of `BEAM_WIDTH × BEAM_THICKNESS` (i.e.
   7.8 × 7.8 mm), per the corrected
   [`docs/lego-technic.md`](../../docs/lego-technic.md) Lift Arms section.
   The axis convention **MUST** match the doc:
   - Beam length runs along **X** (extent = `length_in_studs * 8.0` mm).
   - Beam width runs along **Y** (extent = `BEAM_WIDTH` = 7.8 mm).
   - Beam height runs along **Z** (extent = `BEAM_THICKNESS` = 7.8 mm).
   - Pin holes **MUST** be parallel to **Z** (the orientation a real
     Lego liftarm has when laid flat on a table — wide face up, holes
     vertical), entering through the **top face (Z = BEAM_THICKNESS)
     and the bottom face (Z = 0)**. Both faces are pierced; both carry
     the symmetric counterbore.
   - The cutter's bore axis **MUST** be aligned with **Z** in the final
     placement (not Y).

   *Superseded — 2026-05-16 original wording:*
   > ~~Pin holes **MUST** be parallel to **Y** (axis perpendicular to
   > length, entering through the side face — real-liftarm-faithful).~~

   - *Correction trail:* the 2026-05-17 update inverts the bore-axis
     direction from Y to Z. The original "parallel to Y" wording was
     human-approved on 2026-05-16 against `docs/lego-technic.md`'s
     then-current "short transverse axis" framing; that framing
     under-constrained direction for **square cross-section** beams
     (Y and Z are geometrically equivalent). User Phase-D feedback
     against the OCP CAD viewer demo identified that the convention
     should instead follow the orientation-when-laid-flat: a real Lego
     liftarm rests on its bottom face with holes vertical. The doc was
     corrected in the same pass; this FR is the requirements-side
     mirror. The hole-axis correction trail matters — do not silently
     rewrite the prior wording.
   - **MUST NOT:** rotate the cutter to redirect its bore axis to **Y**
     (this was the previous wording — invert it). The cutter's native
     bore axis is +Z; the corrected mechanic leaves the cutter
     un-rotated and translates it to pierce vertically.

6. **End geometry.** Both ends of the beam **MUST** be hemicircular caps
   of radius `BEAM_END_RADIUS = 3.9 mm` (= ½ × `BEAM_WIDTH`). The body
   **MUST** be constructed via a single 2D sketch (rectangle + two
   end-circles, unioned in `Workplane.sketch()`), extruded once along
   Z. Multi-step 3D boolean union of three separate prisms is
   **NOT** acceptable — see the "2D Sketching over 3D Booleans" rule in
   [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md).

7. **Hole pattern.** The beam **MUST** carry one Technic pin hole at
   every stud centre along its length (uniform pattern; no per-position
   variant in v1). For `length_in_studs = N`, there are exactly **N**
   pin holes. Hole centres along X **MUST** lie at
   `x_i = STUD_PITCH * i + STUD_PITCH/2` for `i = 0 .. N-1` — i.e. the
   first hole is at X = 4 mm (one stud half-pitch from X = 0), the last
   hole is at X = `length_mm - 4 mm`. This matches the 1M beam case
   (single beam, length 8 mm, hole centred at X = 4 mm) cited in
   [`docs/lego-technic.md`](../../docs/lego-technic.md) line 141.

8. **Hole composition.** Each hole **MUST** be cut by consuming
   `TechnicPinHole.standard(depth=...).to_cutter()` from
   `vibe_cading/lego/cutters/technic_pin_hole.py`. The cutter is
   instantiated once and re-used (translated + rotated) for every hole
   position. The cutter's `_ENTRY_OVERCUT = 0.01` mm already provides
   the entry-face clearance; the cutter as built is **blind** (terminal
   face exactly at `depth`), so for a beam the cutter must be extended
   past the opposite side face — strategy locked in FR8a below. The
   resulting hole **MUST** be fully through and both side-face entries
   **MUST** carry a counterbore (see FR8a for why this is automatic).
   Repurposing the blind cutter as a through-cutter at
   `depth = BEAM_WIDTH + 2 · _ENTRY_OVERCUT` produces the symmetric
   two-end counterbore that the real liftarm has — see
   `technic_pin_hole.py:99–110`. No second cutter call is required.

8a. **Through-hole cutter strategy.** The cutter **MUST** be
    instantiated once with
    `depth = BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT` (i.e. the
    full beam width plus an entry-overcut on the terminal side), then
    after the 90°-about-X rotation (FR9) translated along **−Y** by
    `BEAM_WIDTH / 2 + TechnicPinHole._ENTRY_OVERCUT` so that the
    near-face overcut sits at one side face and the (now-extended)
    terminal face sits past the opposite side face. The alternative
    *two-mirrored-instance* strategy **MUST NOT** be used in v1 — the
    single-cutter form is the canonical surface, and the symmetric
    counterbore comes for free (see FR8 final sentence). Verified
    against `vibe_cading/lego/cutters/technic_pin_hole.py:99–110`:
    `cb_bottom` (entry-side, starts at `z = -overcut`) and `cb_top`
    (terminal-side, stops at `z = depth`) are both unconditionally
    unioned into the bore when `counterbore_depth > 0`, so the
    symmetric two-end counterbore is a property of `standard()`'s
    default geometry, not of the beam's assembly logic.

9. **Hole axis rotation.** Because `TechnicPinHole` is built with its
   bore axis along **+Z** with its near face at Z=0 (the entry overcut
   starts at Z = -0.01 per `technic_pin_hole.py:96–97`), each cutter
   instance **MUST** be rotated 90° about the **X axis** so its bore axis
   becomes parallel to **Y** before being translated to the per-hole
   X position. The
   rotation **MUST** be applied via `Workplane.rotate(...)` or
   equivalent CadQuery transform; no axis remap by sketch-plane swap
   is acceptable (the cutter's geometry is anchored to its build
   plane and a transform is the correct surface).

10. **Lead-in chamfer.** Each pin hole **MUST** carry a 0.3 mm × 45°
    lead-in chamfer on **both** entry faces (both Y-facing side faces).
    The chamfer **MUST** use the existing
    `DEFAULT_LEAD_IN` constant from `vibe_cading/lego/constants.py:53`
    (env-var-overridable via `os.getenv("DEFAULT_LEAD_IN", "0.3")`).
    Rationale: layer-line ringing at sharp hole entries on FDM-printed
    beams increases pin insertion force unpredictably; the chamfer is
    a printability concession, not a cosmetic one. The chamfer **MUST**
    be applied after the bore cut, not baked into the cutter (the cutter
    is a project-wide reusable surface and is not the right place to
    bake beam-specific lead-ins).

11. **Zero datum.** The beam's geometric placement **MUST** follow the
    "Absolute Zero-Datum Consistency" rule in
    [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md):
    - **Bottom face of the beam** (the Z-minimum face) sits at
      **`z = 0`**; the body extrudes into **+Z** to
      `z = BEAM_THICKNESS = 7.8 mm`.
    - **First hole centre** sits at **X = 4 mm** (= `STUD_PITCH/2`);
      the beam's X = 0 plane coincides with the X-minimum tangent of
      the first end-cap. The beam therefore occupies
      `X ∈ [0, length_mm]`. *(This origin choice mirrors
      `technic_axle.py`'s convention: the cross-axle body extrudes
      from `(0, 0, 0)` along +Z; the X = 0 / Y = 0 datum is the body's
      geometric reference, not the centroid. The class docstring
      MUST document this explicitly per project rule.)*
    - Beam is **symmetric about Y = 0**: the body's Y extent is
      `[-BEAM_WIDTH/2, +BEAM_WIDTH/2]`. Pin-hole centres lie on the
      Y = 0 plane.

12. **`.solid` property only — no `.to_cutter()`, no `.female()`.** The
    class **MUST** expose a single `.solid: cq.Workplane` read-only
    property returning the finished beam body. It **MUST NOT** define a
    `.to_cutter()` method, a `.female(...)` method, a `male()` method,
    or any other cutter surface — beams are **unioned into assemblies,
    not subtracted from host material**. This matches the
    `vibe_cading/lego/technic_axle.py` precedent (solid-only,
    `.solid` exposed at line 124; no cutter method). Verified.

13. **`demo()` classmethod.** The class **MUST** define a
    `@classmethod demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]`
    method conforming to the `tools/view.py --demo` contract in
    [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md) (signature
    contract — "demo MUST be a `@classmethod` with the exact signature
    ..."). The demo **MUST** display three instances side-by-side:
    `LegoTechnicBeam(length_in_studs=3)`,
    `LegoTechnicBeam(length_in_studs=5)`, and
    `LegoTechnicBeam(length_in_studs=9)`, with each beam translated
    along **Y** by a clearance margin (e.g. ±12 mm) so the three bodies
    do not overlap. Returned tuple shape: `(solid, name, colour)` per
    the contract; suggested colours and names follow the existing
    project pattern (e.g. `"royalblue"`, `"gold"`, `"tan"`).

14. **New constants — `vibe_cading/lego/constants.py`.** Three new
    nominal-geometry constants **MUST** be added to
    `vibe_cading/lego/constants.py`, in a new section block
    (e.g. `# ── Technic Lift Arm (Beam) ──`) inserted between the
    existing Pin Holes block (lines 39–43) and the Axle block
    (lines 45–49):
    - `BEAM_THICKNESS: float = 7.8` — Height of beam along Z axis;
      Cailliau-measured value 7.4–7.8 mm, project picks 7.8 mm
      (theoretical nominal 8.0 mm less ~0.2 mm relief). Comment **MUST**
      cite Cailliau in the inline `#` annotation.
    - `BEAM_WIDTH: float = 7.8` — Short transverse axis (Y); thick
      liftarms are square in cross-section (7.8 × 7.8 mm) per Cailliau.
      Comment **MUST** note "square cross-section per Cailliau".
    - `BEAM_END_RADIUS: float = 3.9` — Hemicircular end-cap radius =
      ½ × `BEAM_WIDTH`. Comment **MUST** state the derivation
      (`= BEAM_WIDTH / 2`).
    Style **MUST** match the existing pattern in `constants.py`: plain
    `float` literals (no `os.getenv` wrapper) because these are nominal
    reference dimensions, not print-tolerance-tunable values. The
    existing precedent for the bare-float style is `STUD_PITCH`,
    `PLATE_HEIGHT`, `AXLE_TIP_TO_TIP`, etc. Print-tolerance values
    (`PIN_HOLE_PRINTED`, `DEFAULT_LEAD_IN`, `DEFAULT_CORNER_RADIUS`)
    use `os.getenv`; beam nominal geometry does not.

15. **`technic_beam.py` imports the new constants.** The new file
    **MUST** import `BEAM_THICKNESS`, `BEAM_WIDTH`, `BEAM_END_RADIUS`,
    `STUD_PITCH`, and `DEFAULT_LEAD_IN` from
    `vibe_cading.lego.constants`, plus `TechnicPinHole` from
    `vibe_cading.lego.cutters.technic_pin_hole`. The class **MUST NOT**
    hardcode `7.8`, `3.9`, `8.0`, or `0.3` as numeric literals anywhere
    in the body — every dimension flows from the constants module per
    the "No Overly Specific Hardcoding" rule in
    [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md).

16. **Topological assertion.** The `_build()` method (or the `.solid`
    property's first read) **MUST** end with a programmatic assertion
    that the produced geometry is a **single contiguous solid**:
    `assert len(result.solids().vals()) == 1, "Expected single
    solid, got {n}"`. This is mandated by the "Topological Validation
    (Floating Bodies)" entry in
    [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md). Without this
    guard, a stuck through-hole misalignment could leave a thin wafer
    or split solid undetected.

17. **`TechnicPinHole.standard()` defaults — DO NOT MODIFY.** This task
    **MUST NOT** modify `TechnicPinHole.standard()`'s default
    counterbore parameters (`TECHNIC_PIN_CB_DIAMETER = 6.2`,
    `TECHNIC_PIN_CB_DEPTH = 1.0`) at
    `vibe_cading/lego/cutters/technic_pin_hole.py:22–24`. Those values
    are intentionally the **loose / FDM-friendly edge** of Cailliau's
    6.0–6.2 / 0.8–1.0 mm tolerance band (see
    [`docs/lego-technic.md`](../../docs/lego-technic.md) lines 152–160).
    Beam holes inherit the loose-edge counterbore by design.

## Non-Functional Constraints

- **Construction style.** Single-extrude 2D sketch for the body
  (FR6); no multi-prism 3D boolean union for the cap geometry.
  Per-hole boolean cuts via `host.cut(cutter)` are acceptable and
  unavoidable; the discipline above applies to the **body**
  construction.
- **Performance.** A `length_in_studs = 15` beam should build in
  comfortably under 5 seconds on the dev-container baseline. If a
  pathological-geometry test (e.g. `length_in_studs = 50`) is run
  during developer validation, it is informational only — the v1
  performance bar is set by realistic Lego beam sizes (1M–15M).
- **Style.** New file matches the existing `technic_axle.py` style:
  AGPLv3 header → imports → class docstring (must state the origin
  convention) → class-level constants block → `__init__` → `_build()`
  → `.solid` property → `demo()` classmethod. Type hints on every
  public parameter and return type per the "Explicit Public APIs"
  rule.
- **Test fixtures.** No new test files are mandatory in v1, but the
  developer **MAY** add a `tests/test_technic_beam.py` that asserts:
  (a) body bounding box is `(length_mm, BEAM_WIDTH, BEAM_THICKNESS)`,
  (b) hole count = `length_in_studs`, (c) single solid topology.
  Test addition is at developer discretion, not a v1 gate.

## Known Domain Constraints

- **Stud-grid alignment (FR7).** All hole centres lie on integer
  multiples of `STUD_PITCH = 8 mm` offset by `STUD_PITCH/2 = 4 mm`
  from X = 0. This is a Lego Technic invariant per
  [`docs/lego-technic.md`](../../docs/lego-technic.md) and the
  "Key Constraints" section of
  [`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md).
- **`TechnicPinHole.standard()` is the canonical pin-hole cutter
  surface.** Confirmed by reading
  `vibe_cading/lego/cutters/technic_pin_hole.py:69–77` (`@classmethod
  def standard(cls, depth: float)`) and lines 115–125 (`def
  to_cutter(self, profile=None)`). Both method names are the
  load-bearing API for this task; do not invent alternate names.
- **`technic_axle.py` is the structural precedent.** Confirmed by
  reading `vibe_cading/lego/technic_axle.py:28–132` (single class,
  `_build()` private, `.solid` property, no `from_studs` classmethod,
  AGPLv3 header lines 1–14, no `__main__` block). New
  `technic_beam.py` mirrors this shape.
- **`docs/lego-technic.md` is the dimension authority.** All beam
  numeric values (`BEAM_THICKNESS = 7.8`, `BEAM_WIDTH = 7.8`,
  `BEAM_END_RADIUS = 3.9`, hole spacing 8 mm, hole diameter 4.8 mm)
  come from the just-corrected Lift Arms section (lines 126–168). If
  the doc is corrected again, this class's constants migrate with it.
- **Axis convention is doc-anchored.** The X-length / Y-hole-axis /
  Z-height convention (FR5) is fixed by
  [`docs/lego-technic.md`](../../docs/lego-technic.md) lines 162–168.
  Future Technic-beam-adjacent classes (bent beams, framework beams)
  inherit this convention.
- **Counterbore intentional FDM-friendly drift.** The 6.2 × 1.0 mm
  counterbore default in `TechnicPinHole.standard()` is the loose
  edge of Cailliau's 6.0–6.2 / 0.8–1.0 mm band, intentionally chosen
  for FDM-friendliness (see FR17 + docs reference). Do not "correct"
  it to the doc-cited 6.0 × 0.8 mm reference.
- **AGPLv3 header enforced.** Per
  `tools/check_license_headers.py:24` the glob
  `vibe_cading/**/*.py` is in the enforced CI scope; the new file
  inherits this gate.

## Out of Scope

- **Studded beams.** Traditional studded beams (Lego beam pattern
  predating the 1990s studless transition) are a separate primitive
  with a top-face stud array, hollow underside, and different
  cross-section. They are deferred to a future
  `vibe_cading/lego/technic_beam_studded.py` (or equivalent) — not
  this task.
- **Thin liftarms.** Cailliau measures thin liftarms with a different
  cross-section ratio. This task is scoped to **thick liftarms only**,
  matching the dimension table in
  [`docs/lego-technic.md`](../../docs/lego-technic.md) lines 132–143
  and its scoping note at lines 148–150.
- **Bent / L-shape / 3-4-5-triangle beams.** A `LegoTechnicBentBeam`
  family is a separate class (or family of classes); see
  `docs/lego-technic.md` lines 178–188. Deferred.
- **Per-position hole-type variants.** v1 has uniform pin holes only.
  Per-position variants (axle holes interleaved with pin holes,
  full-thickness vs counterbored mix, etc.) are deferred to a future
  ergonomic pass.
- **Tolerance-profile parameter.** Unlike screw classes, this beam
  does not take a `profile` / `material` keyword argument because the
  beam itself is the solid host, not a cutter. Pin-hole tolerances
  are baked into `TechnicPinHole.standard()` and are out of scope to
  re-thread here.
- **`from_studs` classmethod factory.** Adjusted out of FR4 during
  verification (no `TechnicAxle.from_studs` precedent exists in the
  codebase today). Future ergonomic pass may add `from_studs` to
  both classes simultaneously; not part of this task.
- **Registering in `build.toml`.** Per project rule
  ([`vibe/INSTRUCTIONS.md`](../../vibe/INSTRUCTIONS.md) — "build.toml
  — Explicit Registration Only"), the developer **MUST NOT** add a
  `[[build]]` entry for `LegoTechnicBeam` autonomously. The human
  reviewer decides at the post-implementation gate whether the beam
  enters the canonical build tree.
- **README Models table update.** Surfacing the new class in the
  README's Models table is a small follow-up task, not a v1 gate of
  this class landing. It will fold naturally into the README revision
  triggered by the downstream `examples/` task resuming.
- **`docs/lego-technic.md` revisions.** The doc was just corrected
  pre-Discovery; this task consumes it as-is. Doc revisions are
  out of scope.

## Open Questions

None — Discovery resolved every domain ambiguity. The through-Y
cutter mirroring/translation strategy that previously sat as a
design-phase nuance inside FR8 has been promoted to FR8a (single
cutter at `depth = BEAM_WIDTH + 2 · _ENTRY_OVERCUT`, translated
−Y by `BEAM_WIDTH / 2 + _ENTRY_OVERCUT` after the 90°-about-X
rotation), so it is a testable requirement rather than a deferred
decision. The FR16 single-solid topological assertion remains the
defence-in-depth guard against any residual wafer at the opposite
side face.

---

## Notes for the Developer

- **Discrepancy from spawn brief — `from_studs` classmethod.** The
  spawn brief suggested mirroring "`TechnicAxle.from_studs(...)` or
  equivalent". Direct verification of
  `vibe_cading/lego/technic_axle.py:55` shows the precedent is a bare
  `studs` constructor parameter, **no classmethod factory exists**.
  FR4 was adjusted to match the verified precedent (constructor-only,
  no `from_studs`). A future ergonomic pass may add `from_studs` to
  both classes simultaneously; piecewise addition here would create
  an inconsistency. Folded into FR4 + Out-of-Scope above.
- **Discrepancy from spawn brief — `from_studs` naming verification
  outcome.** As above: the brief said "verify the existing
  classmethod naming convention in `lego/` before encoding". The
  verification found **no** existing classmethod factory in
  `vibe_cading/lego/`; the only `@classmethod` in the package is
  `TechnicPinHole.standard(cls, depth)` (a depth-required factory,
  not a stud-count factory) and `TechnicPinHole.demo(cls, **kwargs)`
  (the standard demo classmethod). The spawn brief's parenthetical
  was a hypothesis that did not survive verification.
- **Cutter through-hole orientation — now FR8a.** This was previously
  parked here as a design-phase nuance; the single-cutter strategy
  (`depth = BEAM_WIDTH + 2 * _ENTRY_OVERCUT`, translated −Y by
  `BEAM_WIDTH / 2 + _ENTRY_OVERCUT` after the 90°-about-X rotation per
  FR9) has been promoted to FR8a as the canonical requirement. The
  two-cutter mirrored alternative is explicitly out per FR8a. See FR8a
  for the full surface contract.
- **Pin-hole counterbore symmetry.** The `TechnicPinHole.standard()`
  cutter places counterbores at **both ends** of its blind bore
  (see `technic_pin_hole.py:99–110`). When reused as a through-hole
  cutter for the beam, both Y-facing side faces will carry a
  counterbore automatically — no second cutter call needed. The
  developer should verify this visually with a section slice
  (`section_slicer.py --axis X --at <hole_x>`).
- **Validation commands** (developer should run during execution):
  - `python3 tools/preview.py vibe_cading.lego.technic_beam.LegoTechnicBeam --params length_in_studs=5 --views top front left iso_ne`
    (verify body shape, hole pattern, end caps, lead-in chamfer
    visibility against the doc).
  - `python3 tools/view.py vibe_cading.lego.technic_beam.LegoTechnicBeam --demo`
    (verify three-beam side-by-side demo).
  - `python3 tools/section_slicer.py <export>.step --axis X --at 4 --report`
    (verify through-hole geometry and counterbores at first hole).
  - Python REPL or `tmp/` probe: `assert len(beam.solid.solids().vals()) == 1`
    (already baked in via FR16; informational verification).

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human (2026-05-16, PM-relayed from user "Approve")
<!-- Do not proceed to design until this box is checked. -->

---

## Independent Designer Review (fresh context, 2026-05-16)

### Re-confirmation (2026-05-16)

- **Verdict:** `APPROVE`
- **Conditions resolved:**
  - ✓ Condition 1 (FR9 imprecise citation) — resolved at FR9, lines
    157-166. Reworded to: "the cutter's bore axis along **+Z** with its
    near face at Z=0 (the entry overcut starts at Z = -0.01 per
    `technic_pin_hole.py:96–97`)" — matches the suggested wording, and
    `technic_pin_hole.py:96–97` is verified correct (`overcut =
    self._ENTRY_OVERCUT` / `bore = cylinder(..., center=(0, 0,
    -overcut))`).
  - ✓ Condition 2 (FR8 design-phase nuance promoted) — resolved at
    FR8a, lines 139-155. The single-cutter strategy (`depth =
    BEAM_WIDTH + 2 * TechnicPinHole._ENTRY_OVERCUT`, translated −Y by
    `BEAM_WIDTH / 2 + _ENTRY_OVERCUT` after the 90°-about-X rotation)
    is now an explicit MUST; the two-mirrored-instance alternative is
    explicitly out. "Open Questions: None" on line 383 is now
    accurate.
  - ✓ Condition 3 (symmetric counterbore explicit) — resolved at FR8,
    lines 134-137. Verbatim sentence added: "Repurposing the blind
    cutter as a through-cutter at `depth = BEAM_WIDTH + 2 ·
    _ENTRY_OVERCUT` produces the symmetric two-end counterbore that
    the real liftarm has — see `technic_pin_hole.py:99–110`. No second
    cutter call is required." Lines 99-110 verified
    (`cb_bottom` + `cb_top` unioned unconditionally when
    `counterbore_depth > 0`).
- **Conditions outstanding:** none.
- **Non-blocking concerns:** Deep-modules thinness, FR13 demo Y
  offsets unpinned, and FR16 location in `_build()` remain as
  previously documented — all still acceptable for v1.
- **Verification log delta:**
  - `vibe_cading/lego/cutters/technic_pin_hole.py:96–97` — `overcut
    = self._ENTRY_OVERCUT` / `bore = cylinder(self.diameter / 2,
    self.depth + overcut, center=(0, 0, -overcut))`. ✓ confirms the
    reworded FR9 mechanic exactly.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:99–110` — `cb_bottom`
    (center Z = -overcut) and `cb_top` (center Z = depth -
    counterbore_depth) both unioned unconditionally when
    `counterbore_depth > 0`. ✓ confirms FR8's promoted symmetric-
    counterbore claim.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:67` —
    `_ENTRY_OVERCUT: float = 0.01`. ✓ confirms FR8a's
    `_ENTRY_OVERCUT` reference is valid (class-level attribute,
    importable).
  - Artifact lines 139-155 (FR8a) — new explicit MUST encoding the
    cutter-depth + translation strategy. ✓ no longer a requirements
    leak inside FR8.
  - Artifact line 383 (Open Questions) — text reads "None — Discovery
    resolved every domain ambiguity. The through-Y cutter
    mirroring/translation strategy that previously sat as a design-
    phase nuance inside FR8 has been promoted to FR8a..." ✓ self-
    consistent with the FR8a promotion.

- **Verdict (original review):** `APPROVE-WITH-CONDITIONS`

- **Strengths**
  - FR8 + Notes call out the through-hole orientation pitfall directly
    against the verified `_ENTRY_OVERCUT = 0.01` / `_THROUGH = False`
    surface of `TechnicPinHole`, and pair it with the FR16 single-solid
    topological assertion — the most likely failure mode (residual
    wafer at one side face) has a guard already in scope.
  - FR4 + the Discrepancy Note on `from_studs` show actual code
    verification overruling the spawn brief's hypothesis, with a clean
    deferral path ("future ergonomic pass on both classes simultaneously")
    rather than introducing an inconsistency. This is the right shape
    for a requirements doc.
  - FR14's constant-style decision (bare `float` for nominal geometry,
    no `os.getenv`) is correctly aligned with the existing
    `STUD_PITCH` / `PLATE_HEIGHT` / `AXLE_TIP_TO_TIP` precedent and
    explicitly contrasted with the tunable `PIN_HOLE_PRINTED` /
    `DEFAULT_LEAD_IN` / `DEFAULT_CORNER_RADIUS` pattern — no contributor
    will misclassify which knob is environment-tunable.

- **Conditions / required edits** (single-pass)
  1. **FR9 references a non-existent line — fix the citation.** FR9
     says "the cutter extrudes along +Z from Z=0; see
     `technic_pin_hole.py:_build`". The actual `_build()` at lines
     92–113 builds the cutter via the `cylinder()` helper from
     `vibe_cading.cq_utils`, not a direct extrude — and the bore
     starts at `z = -overcut` (line 97), not strictly `Z=0`. The
     statement is *substantively* correct (the cutter's bore axis is
     `+Z` and the entry face is at the cutter's near-Z extent), but
     the cited mechanic is wrong. Reword to: "the cutter's bore axis
     is +Z with its near face at Z=0 (entry overcut starts at Z = -0.01
     per `technic_pin_hole.py:96–97`)".
  2. **FR8 design-phase nuance is a requirement leak — promote it or
     pin it.** FR8's parenthetical ("Design phase: decide whether to
     build the cutter at `depth = BEAM_WIDTH + 2 * entry_overcut`, or
     to extend the cutter cleanly through both side faces using a
     second mirrored translation") is a requirements-leaking decision:
     the choice between *one cutter at extra depth* vs. *two mirrored
     instances* changes whether the FR12 single-`.solid` body's
     entry-side overcut is symmetric. Pick one (the Notes section
     already recommends the single-cutter approach with
     `depth = BEAM_WIDTH + 2 * entry_overcut`) and lift it from
     "design-phase decision" to an explicit FR (e.g. FR8a). Keeping it
     as an OQ-shaped sentence inside a MUST-shaped FR muddies what's
     testable. The "Open Questions: None" header on line 366 also
     becomes accurate.
  3. **Through-hole + counterbore-at-both-ends interacts with the
     blind-cutter docstring — call out the resolution explicitly.**
     `TechnicPinHole`'s docstring (`technic_pin_hole.py:44–47`) says
     "this cutter is **blind** by design — the bore terminates exactly
     at the requested `depth`". When FR8 repurposes it as a through-
     cutter by setting `depth = BEAM_WIDTH + 2 * entry_overcut`, the
     near-face counterbore (cb_bottom at line 100, starting at
     `z = -overcut`) becomes the entry-side counterbore at one side
     face, and the far-face counterbore (cb_top at line 106, stopping
     at `z = depth`) becomes the entry-side counterbore at the
     opposite side face — exactly the symmetry the real liftarm has.
     The brief implicitly relies on this in Notes ("both Y-facing
     side faces will carry a counterbore automatically"), but the
     reader has to reverse-engineer it. Add one sentence to FR8 (or
     to FR17) stating: "Repurposing the blind cutter as a through-
     cutter at `depth = BEAM_WIDTH + 2·entry_overcut` produces the
     symmetric two-end counterbore that the real liftarm has — see
     `technic_pin_hole.py:99–110`. No second cutter call is required."

- **Open concerns** (non-blocking)
  - **Deep-modules dual-lens is thin on the maintainer side.** A
    single-class file with no polymorphic siblings (yet) reads as a
    shallow data-class. Predicted cost if it stays shallow: the
    deferred `LegoTechnicBeamStudded` / `LegoTechnicBentBeam` siblings
    arrive piecewise and only then is a shared `LegoTechnicBeamBase`
    factored out — one refactor pass, low cost. Acceptable for v1;
    the contributor-extension lens earns the keep.
  - **FR13's three-instance demo coordinates are unpinned.** The
    artifact suggests "±12 mm" Y offsets without naming the Y span
    of the longest demo beam (a 9-stud beam is 72 mm long along X,
    but only 7.8 mm wide along Y — ±12 mm Y separation is plenty).
    Predicted cost if mis-spec'd: demo bodies overlap or are
    visually crowded; one re-edit. Trivial — design phase will pick
    a workable number.
  - **FR16 assertion lives in `_build()` per the artifact — confirm
    that's the right surface.** `technic_axle.py:84–122` shows
    `_build()` returning a `cq.Workplane`; an `assert
    len(result.solids().vals()) == 1` before `return` is fine.
    Predicted cost if it lands on the `.solid` property's first read
    instead: identical guard, just a different line; no behavioural
    difference. Non-blocking.

- **Verification log**
  - `tools/check_license_headers.py:24` — pattern tuple
    `("vibe_cading/**/*.py", "tools/**/*.py")` ✓ confirms FR1's
    AGPLv3-header requirement.
  - `tools/check_no_main_blocks.py:77` — `roots = [repo_root /
    "vibe_cading", repo_root / "parts"]` ✓ confirms FR1's no-main-
    blocks requirement.
  - `vibe_cading/lego/technic_axle.py:55` — `def __init__(self,
    studs: int | None = None, ...)`. No `@classmethod` decorator
    above it; grep of file shows zero `@classmethod` occurrences. ✓
    confirms FR4's claim that `TechnicAxle` has no `from_studs`
    factory.
  - `vibe_cading/lego/technic_axle.py:1–14` — AGPLv3 header present.
    ✓ confirms FR1's "identical wording" precedent.
  - `vibe_cading/lego/technic_axle.py:124–131` — `@property def
    solid(self) -> cq.Workplane`. ✓ confirms FR12's solid-only
    precedent.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:69–77` —
    `@classmethod def standard(cls, depth: float) -> "TechnicPinHole"`.
    ✓ confirms FR8's `TechnicPinHole.standard(depth=...)` invocation.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:22–24` —
    `TECHNIC_PIN_CB_DIAMETER = 6.2`, `TECHNIC_PIN_CB_DEPTH = 1.0`.
    ✓ confirms FR17's "DO NOT MODIFY" defaults.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:67` —
    `_ENTRY_OVERCUT: float = 0.01`. ✓ confirms FR8's `0.01 mm` figure.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:66` —
    `_THROUGH: bool = False`; combined with lines 44–47 (docstring
    "this cutter is **blind** by design"). ✓ confirms FR8's blind-
    cutter framing.
  - `vibe_cading/lego/cutters/technic_pin_hole.py:99–110` — both
    `cb_bottom` (entry-side, starts at `z = -overcut`) and
    `cb_top` (terminal-side, stops at `z = depth`) are unioned into
    the bore unconditionally when `counterbore_depth > 0`. ✓ confirms
    the Note's "both Y-facing side faces will carry a counterbore
    automatically" claim — but see condition 3 above (this deserves
    promotion from a Note to an FR sentence).
  - `vibe_cading/lego/cutters/technic_pin_hole.py:92–113` — `_build`
    uses the `cylinder()` helper from `vibe_cading.cq_utils`; the
    bore origin is `(0, 0, -overcut)`, *not* `(0, 0, 0)`. ✗ FR9's
    "the cutter extrudes along +Z from Z=0" is imprecise; condition
    1 above.
  - `vibe_cading/lego/constants.py:53` — `DEFAULT_LEAD_IN: float =
    float(os.getenv("DEFAULT_LEAD_IN", "0.3"))`. ✓ confirms FR10's
    cited line and env-var-overridable framing.
  - `vibe_cading/lego/constants.py:39–43` (Pin Holes block) and
    `:45–49` (Axle block) — both exist as separately commented
    blocks. ✓ confirms FR14's "insert between" placement instruction.
  - `vibe_cading/lego/constants.py:33` — `STUD_PITCH: float = 8.0`;
    line 34 `PLATE_HEIGHT: float = 3.2`; line 46
    `AXLE_TIP_TO_TIP: float = 4.78`. ✓ all three are bare `float`
    literals (no `os.getenv`), confirming FR14's style claim.
  - `docs/lego-technic.md:126–168` — Lift Arms section exists;
    line 134 `Beam thickness 7.8 mm`; line 135 `Beam width 7.8 mm`;
    line 140 `End radius 3.9 mm`; line 141 `1M beam total length
    8.0 mm`. ✓ all FR5 / FR6 / FR14 numeric claims trace cleanly.
  - `docs/lego-technic.md:162–168` — Hole-axis convention: "beam
    length runs along X; pin holes are parallel to Y; beam height
    runs along Z". ✓ confirms FR5's axis convention.
  - `docs/lego-technic.md:152–160` — Counterbore intentional drift
    (code defaults 6.2 × 1.0 mm, doc reference 6.0 × 0.8 mm). ✓
    confirms FR17's "DO NOT MODIFY" rationale.
  - `vibe_cading/lego/` directory listing — contains `__init__.py`,
    `constants.py`, `technic_axle.py`, `cutters/`, `gears/`. No
    `technic_beam.py` exists. ✓ confirms FR1's "new file" framing.
  - `.agents/plans/2026-05-15-examples-directory_req.md:151–162`
    (FR13) — pins the example to `vibe_cading/lego/constants.py`
    primitives + raw CadQuery, with explicit "MUST NOT import a
    non-existent `LegoTechnicBeam` class". Beam-req's Motivation
    (lines 51–57) correctly notes the FR13 wording "will be revised
    at that time" — i.e. once this beam class lands, FR13 swaps to
    consume it. Coverage check: a future revised FR13 needs only
    `LegoTechnicBeam(length_in_studs=N).solid` to compose the
    example; that surface is exactly what FR3 + FR12 provide. ✓
    no coverage gap.
  - `vibe_cading/mechanical/gears/base.py:357–370` — `from_iso`
    is on the abstract `Gear` base and requires a concrete subclass.
    Not load-bearing for the beam-req but cross-referenced from the
    downstream req's prior review; ✓ unrelated to this artifact.
  - `vibe/INSTRUCTIONS.md` → "Absolute Zero-Datum Consistency" —
    "the primary physical interface of a component (the mating face,
    rotation axis, or flat print bed surface) must mathematically sit
    exactly at `(0, 0, 0)`". FR11 places the beam's bottom face at
    `z = 0` (print-bed surface), which is the right primary
    interface for a 3D-printable beam laid flat. ✓
  - `vibe/INSTRUCTIONS.md` → "2D Sketching over 3D Booleans" —
    FR6 mandates "single 2D sketch (rectangle + two end-circles,
    unioned in `Workplane.sketch()`), extruded once along Z" and
    explicitly rejects multi-prism 3D boolean union. ✓ followed.
  - `vibe/INSTRUCTIONS.md` → "Deep-Modules — Dual-Lens Rule" —
    contributor-extension contract earns `LegoTechnicBeam`'s keep
    (deferred siblings `LegoTechnicBeamStudded`,
    `LegoTechnicBentBeam` in Out-of-Scope provide the extension
    surface). Maintainer-locality is thin but acceptable for v1
    (open concern noted above).
