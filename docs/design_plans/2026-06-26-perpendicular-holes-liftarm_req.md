# Requirements: Parametric Perpendicular Holes Liftarm Generator

<!-- Filename: 2026-06-26-perpendicular-holes-liftarm_req.md  (tracked in git under docs/design_plans/) -->

## Meta

- **Initiator role**: @designer
- **Date**: 2026-06-26
- **Domain integrity gate**: NO — this is new visible geometry on an existing
  part family, not a change to core data contracts, domain model, ML pipeline,
  or serialization format. The gate does not apply.

---

## Problem Statement

The vibe-cading liftarm family currently ships only `LegoTechnicBeam` — a
straight studless beam with through-pin holes bored along the **flat-face axis
(+Z)**. There is no Lego-Technic-compatible part that additionally bores holes
through the **narrow side faces (±Y axis)**. The LEGO part family 6435016 /
design 2391 ("Liftarm Thick with Perpendicular Holes") demonstrates the concept:
a thick-liftarm body where selected hole positions are bored perpendicular to the
flat-face holes (i.e., through the side faces). This capability is absent from
the repo, blocking users from printing parts that, e.g., let a pin enter
orthogonally from a structure's side face without a separate adapter.

The user directive is explicit: **generalize the concept** rather than
byte-for-byte reproduce part 6435016. The generator must be flexible enough to
place perpendicular or main-axis holes at any position independently.

---

## User Story / Motivation

As a Lego Technic CAD designer, I need a parametric liftarm generator that
lets me choose, per hole position, whether the bore runs through the flat
faces (main / Z-axis) or through the narrow side faces (perpendicular / Y-axis),
so that I can build custom structural parts that accept pins from two orthogonal
directions without designing separate adapter beams.

---

## Functional Requirements

### Body geometry

1. The part MUST have a straight studless liftarm body with the same square
   cross-section as `LegoTechnicBeam`: `BEAM_THICKNESS × BEAM_WIDTH = 7.8 mm ×
   7.8 mm` (constants `BEAM_THICKNESS` and `BEAM_WIDTH` from
   `vibe_cading/lego/constants.py`). Body length MUST be `n × STUD_PITCH`
   (`STUD_PITCH = 8.0 mm`) where `n` is the number of hole positions.

2. The body MUST use hemicircular stadium end-caps (radius `BEAM_END_RADIUS =
   3.9 mm`), consistent with `LegoTechnicBeam`'s 2D-sketch-extrude approach.
   End-cap centres are at `X = BEAM_END_RADIUS` and `X = length_mm -
   BEAM_END_RADIUS`, producing a total bounding box of `X ∈ [0, length_mm]`.

### Parameter model

3. The generator MUST accept the following constructor parameters:
   - `num_holes: int` — number of hole positions along the beam length (≥ 1).
   - `hole_axes: list[Literal["main", "perp"]] | None` — explicit per-position
     bore-axis selector. Length MUST equal `num_holes` when provided. Each
     element is `"main"` (bore along +Z, through flat faces) or `"perp"` (bore
     along ±Y, through narrow side faces). When `None`, the **default alternating
     pattern** applies (see FR 4).
   - `fit: Literal["free", "slip", "press"]` — tolerance fit grade passed to
     `TechnicPinHole.standard()`. Default `"slip"`.
   - `profile: ToleranceProfile | str | None` — manufacturing tolerance profile,
     forwarded to `TechnicPinHole.standard()`. Default `None` (process-global
     profile).

4. When `hole_axes=None`, the generator MUST default to the **alternating
   pattern** starting with `"perp"` at position 0 (i.e., `["perp", "main",
   "perp", "main", …]`). This matches the drawn 5-hole example from the
   reference image (positions 0, 2, 4 = perp; 1, 3 = main).

5. The generator MUST NOT allow a position to carry both a main-axis and a
   perpendicular-axis bore simultaneously (no cross-drilling). Each position
   carries exactly one bore axis. The `hole_axes` parameter enforces this: one
   string per position.

   > **Rationale for no cross-drill:** The square cross-section is
   > 7.8 × 7.8 mm. A main bore (Ø ≈ 4.8 mm through Z) and a perpendicular bore
   > (Ø ≈ 4.8 mm through Y) at the same X position share the same centre
   > (`X = pos * STUD_PITCH + STUD_PITCH/2`, `Y = 0`, `Z = BEAM_THICKNESS/2`).
   > Their cylinders are orthogonal and intersect at centre — the intersection
   > volume is a non-trivial lens-shaped region that removes material the pin
   > cannot occupy. The resulting geometry creates a structurally unsound pocket
   > at the crossing and is not a real LEGO feature. Prohibiting it keeps the
   > domain honest and the cutter logic simple. If a future use-case requires
   > cross-drilling, it should be a deliberate new design with explicit
   > intersection analysis — not a toggle on this part.

### Hole geometry — main-axis holes

6. Main-axis holes (axis `"main"`) MUST be placed using `TechnicPinHole.standard()`
   with `depth = BEAM_WIDTH + 2 × TechnicPinHole._ENTRY_OVERCUT`, bored along
   +Z, centred at `(X_pos, 0.0)` where `X_pos = i * STUD_PITCH + STUD_PITCH/2`
   for 0-indexed position `i`. This is identical to `LegoTechnicBeam`'s existing
   hole-cutting logic.

7. The cutter for main-axis holes MUST be translated to `Z = -TechnicPinHole._ENTRY_OVERCUT`
   so it clears both flat faces with strictly positive overcut on both sides.

8. Main-axis holes MUST receive the same 0.3 mm × 45° lead-in chamfer at
   every counterbore-rim edge as `LegoTechnicBeam` (`LEAD_IN = 0.3 mm`). The
   chamfer selector MUST correctly identify only the main-hole counterbore rims
   at `Z = 0` and `Z = BEAM_THICKNESS`.

### Hole geometry — perpendicular holes

9. Perpendicular-axis holes (axis `"perp"`) MUST be bored along the **±Y axis**,
   through the narrow side faces. The bore centre MUST be at mid-height:
   `Z = BEAM_THICKNESS / 2 = 3.9 mm`. The bore centre X is the same as for main
   holes: `X_pos = i * STUD_PITCH + STUD_PITCH/2`.

10. Perpendicular holes MUST reuse `TechnicPinHole.standard()` with the same
    `fit` and `profile` parameters as the main holes, but with the cutter
    **rotated 90° about the X-axis** so its bore axis points along ±Y instead
    of ±Z. The cutter depth MUST be `BEAM_THICKNESS + 2 × TechnicPinHole._ENTRY_OVERCUT`
    (through the full narrow-face span), ensuring the cutter clears both side
    faces with strictly positive overcut.

11. Perpendicular holes MUST also receive a 0.3 mm × 45° lead-in chamfer at
    every counterbore-rim edge. The chamfer selector MUST correctly select the
    perpendicular counterbore rims at `Y = -BEAM_WIDTH/2` and
    `Y = +BEAM_WIDTH/2`, distinct from main-hole rims.

12. The axis mid-height placement (`Z = BEAM_THICKNESS / 2`) corresponds to
    **"Pin Hole Offset" = Depth / 2 = 3.9 mm** in the parameter-legend image.
    This is the centred default and matches the square cross-section. No other
    offset value is required; the offset is not a user-exposed parameter. (See
    Open Question OQ-1 for confirmation.)

### Non-intersection invariant

13. When positions are assigned to different axes (some `"main"`, some `"perp"`),
    the bore cylinders MUST NOT geometrically intersect each other. For the
    standard alternating pattern, this is structurally guaranteed by the 8 mm
    pitch between hole centres along X: main and perp holes never share the same
    X position, so their bore cylinders (Ø ≈ 4.8 mm, plus counterbores Ø 6.2 mm)
    are separated by `≥ STUD_PITCH - max_counterbore_radius × 2 ≈ 8.0 - 6.2 =
    1.8 mm` of centre-to-centre spacing. This is sufficient clearance; no
    additional non-intersection logic is required for the alternating default.

14. For arbitrary `hole_axes` inputs, the generator MUST enforce FR 5 (no
    cross-drilling) but MUST NOT check for counterbore-counterbore proximity
    between adjacent perpendicular and main holes — 8 mm pitch separation is
    sufficient for the standard 6.2 mm counterbore diameter.

### Coordinate / origin convention

15. The origin convention MUST match `LegoTechnicBeam` exactly:
    - `Z = 0`: bottom flat face (FDM print-bed datum).
    - `X = 0`: outermost tangent of the first end-cap.
    - `Y = 0`: beam centreline (width is symmetric about Y = 0, spanning
      `[-BEAM_WIDTH/2, +BEAM_WIDTH/2]`).
    - Beam bounding box: `X ∈ [0, length_mm] × Y ∈ [-BEAM_WIDTH/2, +BEAM_WIDTH/2] × Z ∈ [0, BEAM_THICKNESS]`.

16. First hole position centre: `X = STUD_PITCH / 2 = 4.0 mm` (0-indexed
    position 0). This inherits the `LegoTechnicBeam` convention
    (`STUD_PITCH * i + STUD_PITCH / 2` for position `i`).

### Tolerance / profile handling

17. Bore diameters for BOTH main and perpendicular holes MUST be resolved
    through the active `ToleranceProfile` via `TechnicPinHole.standard(fit=..., profile=...)`.
    No hardcoded clearance values (`+ 0.2 mm`, etc.) are permitted inside
    the model.

18. The counterbore diameter for both hole types MUST remain at the nominal
    `TECHNIC_PIN_CB_DIAMETER = 6.2 mm` (printer-independent seating surface),
    consistent with `TechnicPinHole`'s documented profile-awareness policy
    (the counterbore is NOT profile-widened).

### Public API

19. The class MUST expose a `.solid` property (returns `cq.Workplane`) following
    the project's `CutterProtocol`-adjacent positive-geometry convention.

20. The class MUST include a top-level docstring that states:
    - What `(0, 0, 0)` represents (FDM print-bed datum, see FR 15).
    - The meaning of each constructor parameter.
    - The alternating default pattern (FR 4).
    - The hole-axis rotation convention (main = +Z bore, perp = ±Y bore).

21. The class MUST carry the AGPLv3 license header.

### Topological invariants

22. The finished solid MUST satisfy `len(result.solids().vals()) == 1` — a
    single contiguous body. A programmatic assertion MUST be present in `_build()`.

23. The chamfer-edge count assertion (defensive guard matching `LegoTechnicBeam`'s
    pattern) MUST cover both main-hole rim edges and perpendicular-hole rim edges
    independently. Specific edge counts: `2 × count("main" in hole_axes)` for
    main-hole rims; `2 × count("perp" in hole_axes)` for perp-hole rims.

### Visual contract

24. Because this is new visible geometry, an `_iso_ne.svg` visual contract MUST
    be generated and tracked in `visual_contracts/` before the human design gate
    (Step 4). An additional `_front.svg` is strongly recommended to show the
    perpendicular counterbore profile from the side-face perspective. Both MUST
    be registered in `visual_contracts.toml`.

---

## Non-Functional Constraints

- **Backward compatibility with `LegoTechnicBeam`:** A `PerpendicularHolesLiftarm(num_holes=N, hole_axes=["main"]*N)` MUST produce geometry dimensionally identical to a `LegoTechnicBeam(length_in_studs=N)` (within OCCT floating-point tolerance). This is the regression baseline.
- **No new third-party dependencies:** Only `cadquery` and project-internal modules.
- **Code quality:** No hardcoded magic numbers; all dimensions derived from `vibe_cading/lego/constants.py` or `TechnicPinHole` class attributes.
- **2D-sketch-extrude body:** The beam body MUST use the same 2D sketch + single extrude approach as `LegoTechnicBeam` (not boolean unions of 3D primitives) for performance and seam-artifact avoidance.
- **Build registration:** A `build.toml` entry MUST NOT be added without explicit user approval (project policy).
- **`engine_api.json` refresh:** If implemented as a new class in `vibe_cading/lego/`, running `python3 vibe_cading/tools/gen_engine_api.py` is required to regenerate the engine API contract (per the `[regenerate-engine-api-on-new-class]` memory note).

---

## Known Domain Constraints

- `STUD_PITCH = 8.0 mm`: all hole centres must land on the 8 mm stud grid.
- `BEAM_THICKNESS = BEAM_WIDTH = 7.8 mm`: square cross-section. The perpendicular bore depth through the narrow face equals `BEAM_THICKNESS = 7.8 mm`; the main bore depth through the flat face equals `BEAM_WIDTH = 7.8 mm`. They are numerically equal for this square section.
- `PIN_HOLE_DIAMETER = 4.8 mm` (nominal, no clearance baked in). Actual bore = `4.8 + 2 × profile.slip.radial` on `fdm_standard` (≈ 4.90 mm).
- `TECHNIC_PIN_CB_DIAMETER = 6.2 mm`: counterbore mouth diameter, printer-independent. `TECHNIC_PIN_CB_DEPTH = 1.0 mm`.
- `BEAM_END_RADIUS = 3.9 mm`: end-cap radius. End-cap centres at `X = 3.9 mm` and `X = length_mm - 3.9 mm`, with a 0.1 mm offset from the first/last hole centres (per `LegoTechnicBeam` design decision — inherited, not re-examined here).
- `LEAD_IN = 0.3 mm`: chamfer depth at all hole-mouth counterbore rims.
- `TechnicPinHole._ENTRY_OVERCUT = 0.01 mm`: entry overcut so the cutter clears the host face cleanly.
- The OCP/OCCT boolean kernel requires cutters to extend strictly beyond the target face (not be coincident). All cutters MUST use the `_ENTRY_OVERCUT` extension.

---

## Out of Scope

- Cross-drilling (both main and perp bore at the same position). Explicitly excluded (FR 5).
- Non-square cross-sections or beam widths different from `BEAM_WIDTH = BEAM_THICKNESS = 7.8 mm`.
- Axle holes (cross-shaped bore) — only round pin holes are in scope.
- Studded top surface or decorative features.
- Angled (non-90°) perpendicular holes.
- Support structures, print-orientation modeling, or slicer profiles.
- Per-position custom counterbore diameter or depth overrides (one spec for all holes per instance).
- Exact byte-for-byte reproduction of LEGO part 6435016 / design 2391.

---

## Open Questions

- [x] **OQ-1 [Human confirm] Pin Hole Offset semantics:** **CONFIRMED (human,
  2026-06-26).** "Pin Hole Offset" = the perpendicular-hole bore's offset from the
  bottom flat face, defaulting to `BEAM_THICKNESS / 2 = 3.9 mm` (centred, matching
  the square section). Not a user-exposed parameter for this part.

- [x] **OQ-2 [Human confirm] Counterbore on perpendicular holes:** **CONFIRMED
  (human, 2026-06-26).** Perpendicular holes reuse `TechnicPinHole.standard()` with
  the full symmetric two-end counterbore (`Ø 6.2 mm × 1.0 mm deep`) on both ±Y entry
  faces — the bracket-like (`H`) markers in the image are those counterbore collars
  seen edge-on.

- [x] **OQ-3 [Human confirm] Label-to-constant mapping:** **CONFIRMED (human,
  2026-06-26).** "Interior Diameter" → `PIN_HOLE_DIAMETER = 4.8 mm` (narrow bore);
  "Pin Hole Diameter" → `TECHNIC_PIN_CB_DIAMETER = 6.2 mm` (counterbore mouth).

- [ ] **OQ-4 [TL architecture call] Generalize `LegoTechnicBeam` vs. introduce
  a new class:** The requirements are written to be implementable as either (a) a
  new standalone class (e.g., `PerpendicularHolesLiftarm` or
  `LegoTechnicBeamPerp`) or (b) an extension/subclass/refactor of the existing
  `LegoTechnicBeam`. **This is explicitly the TL's architecture call.** The
  domain-level lean from the Designer is toward **a new class** for the following
  reasons:
  - `LegoTechnicBeam` has a single-parameter API (`length_in_studs: int`) with a
    clean, narrow contract. Adding a `hole_axes` list parameter would change the
    public surface, requiring a default-of-all-main to preserve backward
    compatibility (FR non-functional), which implies the existing class is being
    used as a base case rather than being meaningfully refactored.
  - The perpendicular-hole variant is a genuinely different part family (different
    use-cases, different assembly instructions, different visual contract). Separate
    classes make `build.toml` registration, docstrings, and `demo()` classmethods
    independently clean.
  - A new class allows the TL to decide the right inheritance shape (sibling,
    subclass, or shared base) without constraining the existing class's interface.
  - However, **if the TL determines that a shared base class or a unified
    `LegoTechnicBeam(hole_axes=...)` extension is cleaner** (avoiding duplication
    of the body-building logic), that decision supersedes this lean. The TL must
    weigh the code-duplication cost of two nearly identical `_build()` methods
    against the API clarity cost of adding optional parameters to an existing class.

- [ ] **OQ-5 [TL decision] Chamfer selector for perpendicular holes:** The
  existing `_HoleMouthSelector` in `LegoTechnicBeam` selects edges by
  `(geomType=Circle, radius=3.1 mm, |center.z - BEAM_THICKNESS/2| ≈ 3.9 mm)`.
  For perpendicular-hole counterbore rims, the selector must instead match edges
  by `(geomType=Circle, radius=3.1 mm, center.z ≈ BEAM_THICKNESS/2, |center.y|
  ≈ BEAM_WIDTH/2)`. The TL must decide whether `_HoleMouthSelector` should be
  generalized (adding a Y-axis discrimination parameter), or whether a second
  selector class / inline edge selector is appropriate.

- [ ] **OQ-6 [TL decision] Module location:** Should the new class live in
  `vibe_cading/lego/technic_beam.py` (alongside `LegoTechnicBeam`) or in a new
  file `vibe_cading/lego/technic_beam_perp.py`? The TL's architecture call on
  OQ-4 will likely determine this.

---

## Tests / Acceptance Criteria

The following acceptance criteria MUST be verifiable before merge:

| # | Criterion | Verification method |
|---|-----------|---------------------|
| AC-1 | Single-solid topology for any valid `hole_axes` input | Programmatic assertion `len(solid.solids().vals()) == 1` in `_build()` |
| AC-2 | Correct number of main-axis holes | `hole_finder.py` on the built STEP: count round holes with axis parallel to Z |
| AC-3 | Correct number of perpendicular-axis holes | `hole_finder.py` on the built STEP: count round holes with axis parallel to Y |
| AC-4 | Main holes at correct X positions (8 mm grid) | `hole_finder.py` X centres = `[i * 8.0 + 4.0 for i in main_indices]` |
| AC-5 | Perpendicular holes at correct X and Z positions | `hole_finder.py` X centres = `[i * 8.0 + 4.0 for i in perp_indices]`, Z centre = `3.9 mm` |
| AC-6 | No main∩perp intersection volume | Programmatic: build both-hole cutters, compute `.intersect()` → must be empty / volume = 0.0 (for standard alternating pattern) |
| AC-7 | All-main case = `LegoTechnicBeam` dimensions | `boolean_diff.py` against a `LegoTechnicBeam(N)` STEP: volume delta < 0.5% |
| AC-8 | Bore diameter matches profile | `hole_finder.py` bore Ø = `PIN_HOLE_DIAMETER + 2 × profile.slip.radial` (on `fdm_standard`) |
| AC-9 | Counterbore diameter at 6.2 mm | `section_slicer.py --axis Z` (for perp holes, `--axis X`) confirms counterbore Ø = 6.2 mm at both entry faces |
| AC-10 | Lead-in chamfer present at all hole-mouth edges | Visual inspection via `preview.py --views iso_ne front` and section slice confirms chamfer present |
| AC-11 | Visual contract SVG committed and registered | `visual_contracts/2026-06-26-perpendicular-holes-liftarm_design_iso_ne.svg` exists, is registered in `visual_contracts.toml`, and passes `check_visual_contract_freshness.py` |
| AC-12 | AGPLv3 header present | Manual check: first 15 lines of new file contain the license header |
| AC-13 | No `ocp_vscode` import or `__main__` block | `check_no_main_blocks.py` CI gate passes |
| AC-14 | `engine_api.json` regenerated | `gen_engine_api.py` runs without error; output committed |

---

## Human Confirmation Checkpoint

- [x] Requirements reviewed and confirmed by human (2026-06-26). OQ-1/2/3 resolved
  as recorded above; OQ-4/5/6 (architecture) deferred to TL co-design (Step 3).
<!-- Do not proceed to design until this box is checked. -->
