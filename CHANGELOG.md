# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/). While the
project is pre-1.0 the public API is not yet stable — see
[`docs/releasing.md`](docs/releasing.md) for the versioning policy (0.x phase) and
the release-cut process.

This changelog starts at the first tagged release. Earlier development history is
not retroactively seeded here — it lives in the git log. Every public-surface PR
from here on adds an entry under `## [Unreleased]`; cutting a release renames that
section to the new version and date.

## [Unreleased]

### Removed
- **`PoweredUpHubHousing`'s latch catch is deleted** — the catch boss, its
  undercut slot and the keeper nub were the mating half of a barb-on-the-finger
  `PoweredUpHubCover` has not had since the latch became a hairpin spring, and
  they were measured dead before removal: the slot cutter overlapped
  `0.0000 mm³` of the built wall, the nub had not been unioned since round 27,
  and the boss's only remaining effect was a `0.150 mm` overhang the wall
  already provides. With it go `_LATCH_CATCH_Z_MARGIN`,
  `_LATCH_CATCH_RETREAT_Y` and `_MIN_MATERIAL_BEHIND_UNDERCUT`.
- **Breaking** — `PoweredUpHubCover` drops the public barb API that only the
  deleted catch consumed: the `HOOK_FACE_Y0` / `HOOK_FACE_Y1` / `HOOK_FACE_Z1`
  constants and the `barb_arc_points()` / `barb_outboard_y()` classmethods.
  They described a drafted hook face and bead arc the part no longer has.
- **`PoweredUpHubBatteryTray` is deleted** (user direction, 2026-08-20). The
  housing is now capped at a 3-stud (`24.000 mm`) bottom layer, and a separate
  tray no longer fits underneath: cover plate `1.2` + tray floor `1.5` + the
  named `20 mm` pack + strap `~1.8` = `24.5 mm` against the `22.0 mm` available
  below the deck — `2.5 mm` over, even after reclaiming the tray's own
  `2.500 mm` raised-floor standoff. The pack now sits directly on
  `PoweredUpHubCover`. **Breaking**: the class, its module
  `vibe_cading.lego_adapters.poweredup_hub.battery_tray`, its two
  `visual_contracts.toml` rows and their SVGs are all gone, and
  `assembly.assemble()` returns two parts instead of three.
- `PoweredUpHubCover`: the locating land (and its `LAND_Y_LO` / `LAND_Y_HI` /
  `LAND_HEIGHT` constants) is removed — it existed solely to register the
  deleted tray's bottom rim, so it now registers nothing.

### Changed
- **`PoweredUpHubHousing` height is now a design decision, not a copy of the
  reference**: `DECK_Z` drops `29.600 → 24.000 mm`, expressed as
  `DECK_STUDS * STUD_PITCH` (3 × 8.0) so the stud count is the single source of
  truth. This part is the *bottom layer* of a two-layer box. The top deck stays
  a flat, solid, unperforated slab — the top-layer connecting holes are
  deliberately not modelled yet — and its plan footprint widens back to the
  full `±HALF_Y` (the round-21 narrowing described a shell region that no
  longer exists at this height). `DECK_THICKNESS` is a plain `2.000 mm`
  constant again, the round-21 instance-level tray clearance having lost its
  referent.
- **`PoweredUpHubHousing` end walls thickened at both ends** so they meet the
  cover instead of leaving an open perimeter slot. The latch wall goes
  `1.200 → 4.800 mm` (inner face onto `PoweredUpHubCover.PLATE_Y_LO`); the
  tongue wall gains a third Z band above the riser at
  `PoweredUpHubCover.PLATE_Y_HI`. The latch-U band (`|X| ∈ [5.600, 19.200]`,
  shared by the hook legs and release legs) is cut straight back to the
  original `1.200 mm` skin by the new `_build_latch_clearance`, so every
  round-18…21 latch interface — catch boss, undercut slot, keeper nub,
  retention ledge — still sits in the wall it was derived against. Verified:
  `Housing ∩ Cover` is byte-identical to the pre-change value.

### Fixed
- **`PoweredUpHubHousing`'s side window is now the cover tab's own outline**,
  offset outward by the running clearance, instead of a three-point
  piecewise-linear taper sampled off the reference's faceted arc. A chord lies
  inside the arc it subtends, so the old cut was narrower than the tab at every
  *intermediate* Z (worst `-0.452 mm` at `z = 8.315`) while matching it at the
  three sampled stations — and `PoweredUpHubCover` compensated by shrinking its
  whole tab `0.320 mm`, deleting reference material from the part to fit a
  mis-modelled hole. The window now carries the clearance (hole, not shaft) and
  the tab is built at reference size: bbox `Y ±12.000, Z 0..8.400`. Gap over the
  round-over is a uniform `+0.150 mm`. **Breaking**: `WINDOW_TAPER_PROFILE` is
  removed from `PoweredUpHubHousing`.
- **`PoweredUpHubHousing` had two zero clearances against the cover's latch,
  and no test could see either.** The clearance channel stopped at
  `engagement_band_hi`, which equals `hook_depth`, so the wall resumed at
  exactly the spring crown's top face — measured headroom `0.024 mm` at the
  apex (nonzero only because the arc falls away either side) against `0.150 mm`
  everywhere else; a crown held against the ceiling preloads the spring and
  holds the lid off its seat. The finger windows were cut to the
  `LATCH_WINDOW_X_LO/HI` literals, which equal the hook footprint exactly, so
  the thumb pad had `0.000 mm` on both X edges — a `13.600 mm` pad in a
  `13.600 mm` slot. Both are now `+ profile.free.radial`, and the window
  asserts its literals still match the hook footprint. Neither was visible to
  `test_general_body_seated_interference_is_zero`: a gap of exactly zero
  encloses no volume, so it scored both `0.000 mm³` and passed. Two tests now
  pin the gaps directly, each confirmed to fail on the restored old geometry.
  That test also loses its round-18 catch carve-out — seated interference is
  asserted zero everywhere now.
- **`PoweredUpHubCover`'s latch crown buried the barb, so nothing gripped.**
  Rounds 18–22 joined the two legs of the cantilever U with a box spanning
  leg-to-plate across the top. That box swallowed the barb bead whole — a
  section at `z = 12.0` returned a single solid span, no protrusion and no
  undercut anywhere — so the lid was in fact retained by the housing's keeper
  nub pressing on the *crown*, not by a barb. The crown is now the material
  between the release leg's inner wall and the bead's own outboard surface,
  over the bead's upper band only: the U stays joined at the top (so pressing
  the thumb pad still flexes the hook, per SS1.4) while everything below stays
  open, leaving the bead's re-entrant face — the 157.5° sweep passes vertical,
  so it overhangs — exposed as the surface that actually grabs. Measured: the U
  is open by 1.065 / 0.741 / 0.442 mm at `z` = 11.0 / 11.6 / 12.0 with the bead
  bulging into it, and `Housing ∩ Cover` retention is now **7.37 mm³ against
  the bead itself** instead of 18.1 mm³ against a crown box.
- **`PoweredUpHubCover`'s side handles were the wrong shape and 1.6 mm out of
  position.** The first port copied the deleted `PoweredUpHubBatteryTray`'s own
  constants, which were expressed in the *tray's* datum (its bottom rim, one
  `PLATE_THICKNESS` above the lid face) and had additionally been shrunk by that
  class's round-20 window-collision fix. Rebuilt directly from the tray part's
  own SS2.3 figures, which transfer with no rebasing because this class's `Z = 0`
  *is* the lid outer face: pad `±12.000 × 0…8.400`, ledge at `7.200…8.400`, grip
  ribs at `1.920…2.880` / `3.920…4.880`, and — the feature whose absence made it
  read as the wrong shape — the **R3.600 corner round-over**, which was simply
  absent before. The handle carries a running clearance plus a chord allowance,
  because `PoweredUpHubHousing`'s window approximates its ramp with a
  piecewise-linear taper and a chord always lies inside the arc it subtends.
- **`PoweredUpHubCover`'s ledge started 0.400 mm too far forward** — from the
  plate edge (32.000) rather than §1.5's `LEDGE_Y_LO` (32.400). Found by a
  plane-reconciliation sweep of the reference mesh, not by eye. (That sweep also
  flagged the 15 plate through-slots as unmodelled; they were built and then
  removed again at the user's direction — this box does not want them.) After both fixes 14 planes remain and **all are
  explained**: 13 are the three deliberately-deleted AA-divider ribs and their
  gussets (design brief O1), and 1 is an internal face of the hollow thumb-pad
  shell, which this model builds solid. See the reference-comparison doc,
  section R23 — including why `boolean_diff.py` cannot be used against this
  reference (it returns all-zero, Jaccard 0: a failed measurement, not a match).
- **`PoweredUpHubCover`'s latch barb did nothing.** Rounds 18–21 modelled it as a
  three-point facet whose crest sat at `z = 12.000` — inside the crown's own
  `[11.800, 13.000]` band — so the crown bridged straight over it. A section at
  `z = 12.0` returned one solid Y span: no protrusion anywhere. Retention was
  actually occurring between the housing's keeper nub and the **crown**, not a
  barb. Root cause was not the crown but the **release leg**: round 21's *"held
  flat beyond z = 11.0"* deviation put the leg's inner face at `-32.320`, closing
  the release aperture to **0.043 mm** where the reference holds it at
  **1.062 mm** (`parts/24853.dat` sectioned at the finger centre; measured at
  z = 11.2 / 11.4 / 11.6). Fixed by stepping `_LEG_OUTER_Y`'s top point out to
  `-34.000` with the reference's base `0.698 mm` thickness, which lands the inner
  face on `-33.302` exactly. The barb is now a **true R1.000 cylindrical bead**
  swept through the reference's 157.5° arc about `(-32.200, 12.000)`, and
  `PoweredUpHubHousing`'s catch slot derives from its real outboard extreme via
  the new `PoweredUpHubCover.barb_outboard_y()` instead of from the arm face.
  `PoweredUpHubHousing`'s catch boss is reduced to the retention **ledge** above
  the engagement band, since it no longer needs to refill the band the leg
  occupies. Net: envelope unchanged at `13.000 mm`, `Housing ∩ Cover` **20.71 →
  19.08 mm³** (18.1 of which is the intended keeper-nub retention).

### Added
- **Tongue-end castellation restored to the reference** (user direction): the
  6 ledge locating teeth and the 4 notches between them (`TOOTH_X_BANDS`,
  `NOTCH_FLOOR_Z`), which rounds 18–21 dropped as non-load-bearing. Both live on
  `PoweredUpHubCover` exactly as in the real part, so the housing carries a plain
  mating lip and no ridges. The **locating groove** (`GROOVE_*`, Y ∈ [30.0, 31.2]
  at 1.600 mm) is restored with them: it had been deleted alongside the tray on
  round 18's claim that it registered the tray's rim, but §1.5 of the LDraw
  extract states plainly that *the lid seats laterally* on it — a lid-to-housing
  feature that never had anything to do with the tray.
- **`PoweredUpHubCover` side handles** (`HANDLE_*`), re-homed 1:1 from the
  deleted tray's extraction tabs. The port needed no re-dimensioning: the
  tray's outer wall face and the cover's plate half-width are the same
  `27.200 mm`, so the handles still emerge through the housing's own side
  windows with the ledge `0.400 mm` proud of the outer wall face.

### Added
- `PerpendicularHolesLiftarm`: two default-preserving constructor additions
  (TL round, 2026-08-19 — see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md` →
  *Reusable classes → TL round — decisions → Q1*). `thickness: float =
  BEAM_THICKNESS` (keyword-only) lets a caller override the beam's Z-extent
  per-instance — e.g. to match a real part's thicker cross-section — without
  moving the shared `BEAM_THICKNESS` constant every other caller relies on.
  `hole_axes` gains a third member, `"none"`, leaving a position unbored so a
  caller can compose its own call-site-local hole geometry at that position
  instead of un-cutting this class's own bore. Both additions preserve every
  existing caller's geometry byte-for-byte (verified: the two registered
  `visual_contracts.toml` rows regenerate with zero byte movement).
- `PoweredUpHubCover` and `PoweredUpHubBatteryTray`: two new exported model
  classes, task 2 of the Powered Up hub battery-box implementation sequence
  (see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md`). Both
  are read from the LDraw parts library (CC BY 4.0, author Philippe
  Hurbain) as measured facts — no LDraw file or converted geometry is
  committed, only from-scratch CadQuery code.
  `PoweredUpHubCover` is an exact copy of LEGO lid `24853` minus its three
  inner AA-cell divider ribs, with the 15 outer through-slots closed
  (round-13 user decision): the flat 1.2 mm plate, both cantilever latch
  fingers (Ø2.000 mm barb, 13.6 mm wide, 11.2 mm apart), the slide-in
  tongue/ledge at the insertion end, and a locating groove sized to the
  tray's own bottom rim. `PoweredUpHubBatteryTray` repurposes LEGO tray
  `24849` for a Spektrum SPMX812SH2 LiPo pack: both internal transverse
  partitions removed (giving the pack's required 58.000 mm clear length,
  plus a 1.5 mm relief since that figure is otherwise zero-slack), both
  outer end walls and both side walls (with their extraction tabs) kept, a
  new floor, and two new strap-holder slots sized to the confirmed 20.5 mm
  opening. A shared `latch_geometry.LatchGeometry` frozen parameter object
  (barb/hook dimensions plus the derived undercut/catch-width/ramp-angle
  numbers) is the single source of truth the future `HousingBox` catch
  (a separate PR) will import alongside the Cover, so the male and female
  latch halves cannot drift apart.
- `PoweredUpHubHousing`: new exported model class, task 3 of the Powered Up
  hub battery-box implementation sequence (see
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md`). An
  exact copy of the real hub's bottom shell's own envelope (LDraw `25560`,
  72.0 × 71.2 × 29.6 mm — see the *Fixed* entry below for the round-20
  correction from the LDraw part's bounding box, 33.8 mm) with a scoped
  departure at the two lid-retention regions only
  (a single wall instead of LEGO's real two-skin sandwich, per the design's
  *Single wall at BOTH ends* section). Composes
  `PerpendicularHolesLiftarm(3, ["main", "none", "main"], thickness=8.0)`
  for the four arms (per the TL round's decision), finished locally with an
  envelope trim to the real 23.2 mm arm length, an additive Ø7.2 × 0.4 mm
  boss around each middle hole, and a housing-local three-step middle bore
  (Ø6.4 × 0.8 outer counterbore → Ø4.8 × 6.4 guided → Ø7.2 × 1.6 relief
  opening into the battery cavity). The latch-end catch (derived from
  `PoweredUpHubCover`'s own barb geometry via the shared `LatchGeometry`
  parameter object, absent from LDraw) and the tongue-end rebate (a lap,
  not a snap, fully specified from LDraw) together implement the design's
  complete retention scheme — verified by a zero-volume boolean
  intersection against the built `PoweredUpHubCover` in its seated
  position.

### Fixed
- `PerpendicularHolesLiftarm`: fixed a latent crossed-constant bug in the
  cutter depths — the main bore (which runs along Z, through `thickness`) was
  sized from `BEAM_WIDTH`, and the perp bore (which runs along Y, through
  `BEAM_WIDTH`) was sized from `BEAM_THICKNESS`. This was harmless only
  because `BEAM_WIDTH == BEAM_THICKNESS == 7.8` by coincidence; it would have
  produced blind (non-through) main holes the moment `thickness` diverged
  from `BEAM_WIDTH` (e.g. the new `thickness=8.0` override above). Fixed as a
  precondition of adding the `thickness` kwarg, with a durable regression
  test (`test_thickness_override_main_holes_break_through`) asserting both Z
  faces show through-holes at a diverging thickness.
- `PoweredUpHubBatteryTray`: fixed a `960.4 mm³` interference against
  `PoweredUpHubHousing` (design round 16, Escalation 5) — the tray's outer
  wall was uniform `27.2/26.4 mm` across its full height, numerically
  identical to Housing's own upper-band wall material above its `Z = 22.0 mm`
  step. The wall now steps inward above the tray's own local `Z = 20.800 mm`
  (Housing's step, offset for the tray's `1.2 mm` seated datum) to
  `26.400 mm minus the active profile's free.radial allowance / 25.600 mm`,
  matching Housing's real upper-band inner face with a tolerance-routed gap
  instead of a bare literal. Confirmed by cross-part boolean intersection:
  the targeted wall-vs-wall overlap is fully eliminated (zero interference in
  Housing's upper wall band); a separate, pre-existing lower-band conflict
  between Housing's arm root-bridge gusset and the tray's own (unaffected)
  lower-band wall remains open — see the design brief's Escalation 8.
- `PoweredUpHubHousing`: fixed a `72.6 mm` vs. the exact-copy `72.0 mm`
  target X envelope (design round 16, Escalation 7) — the arms kept the
  shared `PerpendicularHolesLiftarm` class's Cailliau-calibrated
  `BEAM_WIDTH` (half-width `3.9 mm`) rather than the real LDraw half-width
  (`3.6 mm`), and the middle-hole boss/bore, anchored dynamically off the
  arm's own edge, propagated the same `+0.3 mm` overshoot. Fixed with a
  housing-local composition trim (no shared-class change): one additional
  one-sided cut in `_build_arm_and_bore_local` removing arm material beyond
  the real half-width, after which the boss/bore code's existing dynamic
  read self-corrects. Verified via section slice: arm flat face at
  `X = ±35.600 mm`, boss tip at `X = ±36.000 mm`, overall envelope exactly
  `72.000 mm`.
- `PoweredUpHubHousing`: fixed the `259.014 mm³` lower-band interference
  between the arm root-bridge gusset and `PoweredUpHubBatteryTray`'s own
  (unaffected) wall that Escalation 5's fix had unmasked (design round 17,
  Escalation 8). The root bridge's single, uniform wall-reach — sized for
  the wall's narrower *upper* band (`Z ≥ 22.0 mm`) — was applied across the
  arm's *entire* thickness, so it also crossed through the wall's wider
  *lower* band (`Z < 22.0 mm`, where the tray's wall sits) and overshot
  into the tray's own territory there. Fixed with a Z-dependent two-band
  bridge in `_build_arm_and_bore_local`: the upper band (`Z ∈ [22.0, 24.0]`,
  the band that actually fuses the arm to the wall) is unchanged; the lower
  band (`Z ∈ [16.0, 22.0]`) drops the wall-reaching extension entirely,
  backed by a quantified `≈85.8 mm³` fused-overlap margin (the upper band
  alone) proving the floating-arm defect cannot return, plus two runtime
  assertions guarding both the fused-overlap height and the lower-band
  boundary against silent regression. Root-bridge-band interference against
  the tray is now `0.0 mm³` (down from `259.014 mm³`); envelope, cover
  interference (`0.000000 mm³`), and the single-solid guard are unchanged.
  Verifying this fix surfaced a separate, much smaller (`≈4.05 mm³`)
  residual at the `Z = 22.0` wall-step seam itself — Housing's and the
  tray's own independent `0.05 mm` coincident-faces overlap constructions
  each reach slightly past the step into the other part's still-present
  wall material there — confirmed unrelated to the root bridge and left
  open as a new escalation (see the design brief's Escalations).
- **Powered Up hub battery box — retention mechanism repair (design round
  18, following an independent audit that found the shipped latch had zero
  retention despite passing every static interference check)**. Root
  cause: the latch was specified and verified as a static two-body
  interference problem, not a kinematic one — see the design brief's
  *Round 18* for the full root-cause statement.
  - `PoweredUpHubHousing`: the latch catch's boss and its finger-clearance
    slot shared one bound (`y_slot_inner`), leaving no retention lip
    anywhere — the slot fully swallowed the finger's swept envelope with
    zero deflection required to enter or leave. Fixed with a
    Z-localised "keeper nub" unioned back into the slot's own footprint
    after the cut, sized from a corrected `LatchGeometry.barb_protrusion`
    (`1.040 mm`, re-derived from the barb's own axis rather than an
    eyeballed `0.83 mm` estimate). Also fixed a zero-clearance
    literal-to-literal butt at the tongue-end insertion stop (now routed
    through `profile.free.radial`, matching every other Cover/Housing
    interface) and a `0.05 mm` seam artefact reaching into
    `PoweredUpHubBatteryTray`'s wall.
  - `PoweredUpHubCover`: built the missing second leg of the latch
    finger's cantilever U (the thumb-pad/release-slot half — the U *is*
    the compliant member, not an ergonomics trim) and corrected the
    locating groove's inverted sign (a `0.4 mm` raised registration land,
    not a recess).
  - `PoweredUpHubBatteryTray`: corrected a `1.6 mm` Z-datum transcription
    error across every LDraw-derived Z constant. The design brief's own
    round-18 ruling on the `1.5 mm` seat relief (move it from `+Y` to
    `-Y`) turned out to be wrong once actually built: `PoweredUpHubCover`'s
    new U-spring release leg (B2, above) occupies `-Y` space the ruling's
    own reasoning never anticipated, and a `-Y` relief collides with it far
    worse (`373+ mm³`) than the original `+Y` collision it was meant to
    avoid — a second, escalation-worthy finding. Resolved by keeping the
    relief on `+Y` but Z-restricting it: below `RELIEF_Z_LO` the wall stays
    at its nominal position (clearing Cover's tongue riser), at/above it
    the relieved position governs — the pack's own floor (raised on
    standoffs, next) never needs the extra clearance below that height
    anyway. Also raised the floor on standoffs to give a strap actual
    routing clearance beneath it, and added two small relief pockets
    clearing Cover's own raised low-Z features (the latch thickening band
    and the corrected locating land) that the flat-bottomed end walls
    would otherwise collide with once seated.
  - New mandatory kinematic-sweep tests
    (`tests/lego_adapters/test_poweredup_hub_kinematic.py`) replace the
    single static seated-state check that let the original defect ship
    undetected — parametrised `-Z` pull-out and latch-end rotation sweeps
    now assert genuine, direction-dependent interference.
  - `LatchGeometry.hook_pitch`'s docstring corrected
    (documents the field as the gap between hooks, not their
    centre-to-centre spacing — both existing consumers already used it
    correctly; no behaviour change).
  - `assembly.py`'s `assemble()` now includes `PoweredUpHubHousing`
    alongside `PoweredUpHubCover` and `PoweredUpHubBatteryTray` — the
    view most likely to expose a seating fault had been omitted since
    before `PoweredUpHubHousing` existed.
  - **Known limitation, not fully resolved**: the corrected latch catch's
    seated-state `Cover ∩ Housing` intersection is not exactly `0.0 mm³`
    (measures `~18 mm³`, unchanged by further nub-shape tuning) — proven
    geometrically unavoidable given `PoweredUpHubCover`'s latch finger is
    a solid wedge at every `Z` from `0` to `hook_depth`, so any nub that
    reaches behind the barb crest necessarily also overlaps the finger's
    permanent "back fill" material at the seated transform. See
    `tests/lego_adapters/test_poweredup_hub_kinematic.py`'s own module
    docstring for the full proof, and the design brief's *Implementation
    Status* for the escalation this raises against the acceptance
    criterion as originally worded.
- **Build-integrity fixes found by fresh-context phase-4 review** (both TL
  and Designer independently confirmed; see the design brief's
  *Post-Implementation Sign-Off* section):
  - `vibe_cading/engine_api.json` was stale against `housing.py`'s own
    docstring — an escaped `` \|x\| `` baked into the committed JSON from an
    earlier revision, vs. the current source's `` |x| ``. A docstring edit
    landed after the last `gen_engine_api.py` run and was never followed by
    a re-generation. Regenerated; the resulting diff is exactly that one
    docstring line (no signature change).
  - `check_visual_contract_freshness.py`'s coverage gate went red: this
    stack's `2026-08-19-poweredup-hub-battery-box_design_assembly_iso_ne.svg`
    (a cross-class `assembly.py` composition the checker has no concept of
    rendering) is a tracked design SVG with no `[[contract]]` row, and the
    coverage gate treats any such file as an unregistered-manifest problem.
    Rather than silently rename or untrack the file, the checker now carries
    an explicit, commented `COVERAGE_EXEMPT_UNREGISTERED` allowlist so the
    gap is a deliberate, reviewed decision instead of an unregistered one;
    teaching the checker a real assembly-module row type (the principled
    fix) is tracked as a follow-up.
- **`PoweredUpHubHousing`/`PoweredUpHubCover`: whole-part reference-fidelity
  repair** (design round 20 — a dense surface-to-surface comparison against
  the LDraw reference found 1 blocking + 7 significant defects that two
  prior feature-checklist reviews both missed; see the design brief's
  *Round 20* and `tmp/reference-comparison.md`):
  - `PoweredUpHubHousing`: fixed a **`4.2 mm` overall-height overshoot**
    (`72.0 × 71.2 × 33.8 mm` → the corrected `72.0 × 71.2 × 29.6 mm`) —
    the earlier `TOP_Z = 33.8 mm` was the LDraw part's *bounding box*,
    reached only by two now-out-of-scope `26.9 mm²` connector-port tubes;
    the real shell's own top face is `29.6 mm`. `_build_top_deck` now
    builds the deck as a `2.082 mm` slab ending at that face
    (`z ∈ [27.518, 29.6]`) instead of a phantom slab sitting entirely
    above it (`~16,270 mm³`, `61%` of the model's own volume, outside the
    reference envelope).
  - `PoweredUpHubHousing`: dished both faces of all four arms
    (`_dish_arm_faces`, new) — a `2.756 mm`-web relief pocket between the
    pin-hole positions, blended into each hole/boss by an `R3.600 mm`
    cylindrical relief.
  - `PoweredUpHubHousing`: corrected the side windows from a flat
    `24.8 × 16.0 mm` rectangle (whose own comment wrongly claimed
    `16.0 mm` was "the ramped ends' peak" — the reference's real peak is
    `8.4 mm`) to a piecewise-linear taper matching the reference's own
    measured shoulder profile, `24.0 mm` wide.
  - `PoweredUpHubHousing`: closed a `0.100 mm` open slit between each arm
    and the side wall (`Z ∈ [16.0, 22.0]`) — round 17's own fix had
    over-corrected by dropping the root bridge's Band B reach to nothing;
    restored with the shared `SEAM_MARGIN` overlap convention instead.
  - `PoweredUpHubCover`: rebuilt the latch release leg (`_build_release_leg`)
    from a straight, constant-`0.5 mm` wall flush with Housing's own outer
    wall to the reference's own slanted, variable-thickness
    (`0.7`–`1.05 mm`) blade, read directly off exact ray-crossing
    coordinates.
  - `PoweredUpHubCover`: restored "Tongue B"'s plan-outline footprint
    (`|X| 17.2..26.0 mm`, a `1.378 mm` gap) at the riser level, matching
    Tongue A's already-correct edge — supersedes round 18's "document the
    omission" triage now that the gap's magnitude was quantified.
  - Corrected two comments that were factually wrong about their own
    geometry: the housing's `0.05 mm` step-seam overlap claimed to "not
    change any externally-visible dimension" (it does — that face is the
    part's exterior); the arm's as-built width was recorded as `7.8 mm`
    (the nominal, untrimmed `PerpendicularHolesLiftarm` figure) when the
    real as-built figure, after round 16's outboard-only trim, is
    `7.5 mm`. Neither correction changes geometry, only documentation.
  - **Three new cross-part findings surfaced by these fixes are escalated
    to the Designer, not silently patched** (design brief Escalation 11):
    the corrected deck now overlaps `PoweredUpHubBatteryTray`'s own
    topmost extent by `~0.08 mm` across most of its footprint; the
    corrected (smaller) side window no longer clears a tray tab the old,
    oversized window used to clear by construction; and the corrected
    release-leg spine now collides with Housing's own latch-catch boss
    (derived, round 18, against the old leg shape). All three are outside
    this round's own file scope and are recorded as documented, bounded
    regression-guard residuals pending Designer resolution — see the
    design brief for full detail and magnitudes.
- **`PoweredUpHubHousing`/`PoweredUpHubCover`/`PoweredUpHubBatteryTray`:
  round-21 whole-part re-verification repair** (design round 21 —
  re-running round 20's whole-part comparison against the round-20 repair
  found H1/H4 genuinely fixed but 8 further significant residuals and 2
  previously-undeclared deviations; see the design brief's *Round 21* and
  `tmp/reference-comparison.md`'s `§R0–R10`):
  - `PoweredUpHubCover`: the round-20 Tongue-B plan-outline restoration
    over-corrected its own Z-extent — the outer band (`|X|` between
    `TONGUE_X_HALF` and `RISER_X_HALF`) was built as a full-height
    `2.800 mm` riser instead of plain `1.200 mm` plate, on the tongue's
    own mating face (finding RC4). `_build_tongue` now splits the riser
    into an inner (Tongue-A-width, full-height) and outer
    (plate-thickness-only) band.
  - `PoweredUpHubCover`: prepended the release leg's own reference-derived
    flared-foot profile below `Z = 2.0` (finding RC1) — a real,
    source-readable feature (`s\24853s01.dat`) that had never been
    declared as a deviation at all, larger than the crown's own declared
    hold above `Z = 11.0`, and at the leg's structurally more important
    root. The crown hold's own stated justification ("avoids a hook-leg
    collision") is corrected in the docstring (finding RC3): it does not
    survive (the rebuilt leg collides with the housing instead, see
    Escalation 11c below) but is kept on re-derived grounds (bounded,
    stiffening-direction, no interference of its own once the housing
    catch is fixed) — no geometry change.
  - `PoweredUpHubHousing`: capped the latch-end and tongue-end walls at
    `END_WALL_Z_HI` (`24.000 mm`, was `29.600 mm`) and narrowed the deck's
    own plan footprint to `x ±27.200 × y [-32.000, 33.200]` (was the full
    `±28.000 / ±35.600` housing footprint) — the largest remaining visual
    difference after round 20's H1 fix (finding RH1).
  - `PoweredUpHubHousing`: widened the arm-dish's plan footprint from
    `0.84 mm` to `4.000 mm` on each side of the pocket (finding H2/RH2),
    via an independent gap-opening relief circle centred at each
    inter-hole midpoint rather than shrinking either hole's own `R3.600`
    relief (which either reopens the exact `1.054 mm` end rail or, at the
    middle hole, disconnects the arm once the co-located middle bore is
    cut through it — caught by the single-solid assert during development).
    The dish's cross-section (floors, rails, pocket walls) is unchanged.
  - `PoweredUpHubHousing`: corrected the side window's peak from
    `8.500 mm` back to `8.400 mm` and widened the taper at `Z = 8.0` by
    `0.690 mm` (finding H3/RH3) — `24851.dat` carries a genuine planar
    face at `Z = 8.400` (not a point apex); the window's own taper
    profile now ends in a flat top segment instead of converging to a
    point.
  - `PoweredUpHubHousing`: routed the top deck's own thickness through
    `profile.free.radial` instead of a flat `2.082 mm` literal (finding
    E11-a) — the literal was round 20's own prior extraction, explicitly
    flagged there as the *centre value of a corrugated ceiling* with the
    off-centre thickness undetermined; applying it as a global plane
    collided with `PoweredUpHubBatteryTray`'s own top face
    (`21.094 mm³`). Fixed: `Tray/Housing` seated interference `0.0 mm³`
    (was `~21 mm³`).
  - `PoweredUpHubBatteryTray`: reduced the extraction tab's own Y-reach
    (`TAB_PAD_Y_HALF_NOMINAL`, now running-clearance-corrected) to clear
    Housing's own corrected window taper at the pad's actual seated Z
    (finding E11-b, `2.344 mm³`) — the tray's own fault, not the
    window's; re-widening the window would reopen H3/RH3.
  - `PoweredUpHubHousing`: retreated the latch catch boss's own Y-reach
    to `_LATCH_CATCH_RETREAT_Y` (`-34.400 mm`, the real part's own
    inner-skin depth) outside a Z-window bracketing the barb axis
    (finding E11-c ⑴) — the release leg, correctly positioned by round
    20's C1-C3 fix, fouls the boss's own locally-thickened material over
    the Y-band the real part's two-skin construction leaves clear for it
    (root cause: this class's own round-14 single-wall departure).
    Reduces the new collision from `21.324 mm³` to a `~2.6 mm³` residual
    at the barb window's own boundary (the structural floor for the
    undercut's backing material requires some full-reach window there);
    the pre-existing, separately-accepted `18.088 mm³` barb-in-catch
    seated residual (Escalation 10) is unchanged.
  - **Two declaration-process findings, not geometry fixes**: RC1 (the
    release leg's flared foot) had never been recorded as a deviation at
    all until this round; RC3 (the crown hold)'s stated justification was
    corrected rather than the geometry re-derived. See the design brief's
    *Round 21* for the full framing.
- **Deliverable provenance** (phase-4 TL review BLOCK, see the design brief's
  `TL Review — CURRENT`): the design brief and its lineage sibling
  (`docs/design_plans/2026-08-19-poweredup-hub-battery-box_{design,lineage}.md`)
  were committed for the first time — 16 tracked files already cited them
  by path and would have carried dangling citations on merge (finding B1).
  The three LDraw extraction/comparison analysis documents that are the
  sole stated derivation for most Cover/Tray/Housing/LatchGeometry
  dimensional literals moved from git-ignored `tmp/` to tracked
  `docs/design_plans/2026-08-19-poweredup-hub-battery-box_{ldraw-parts-geometry,ldraw-housing-geometry,reference-comparison}.md`,
  each carrying the LDraw CC BY 4.0 / Philippe Hurbain attribution
  prominently — own measurements and prose, no `.dat` file or converted
  geometry committed (finding B2). All 15 `tmp/`-pointing citations across
  `cover.py`, `battery_tray.py`, `housing.py`, `latch_geometry.py`, and
  `test_poweredup_hub_cover.py` repointed at the new tracked paths;
  `engine_api.json` regenerated to pick up the docstring moves.
- `PoweredUpHubHousing`/`PoweredUpHubCover`: added
  `test_barb_crest_matches_ldraw_reference`, pinning
  `PoweredUpHubCover.HOOK_FACE_Y1 + LatchGeometry.barb_protrusion` to the
  LDraw-measured barb crest (`-31.200 mm`) — the exact invariant
  `LatchGeometry` exists to protect, previously unguarded by any test
  (TL phase-4 review, finding M2).
- `assembly.py`'s `assemble()` (the repo's only assembly-module function,
  and therefore the convention future assembly modules copy): replaced the
  unreachable `**kwargs` / nested `*_kwargs` dict surface — `view.py`'s
  `--assembly` path always calls it bare — with a real
  `profile: ToleranceProfile | str | None = None` parameter, forwarded to
  all three parts (TL phase-4 review, finding M3). Also corrected an
  unlabeled citation of the Claude-specific `CLAUDE.md` to the
  provider-neutral `vibe/INSTRUCTIONS.md`.

## [0.1.6] - 2026-08-10

### Added
- `TechnicPinHoleBushing`: new exported model class — a plain round tube
  bushing that fits into a real Lego Technic pin hole (Ø4.8 mm nominal) on
  its outer diameter and carries an independently-graded clearance
  through-bore, bridging a Lego beam pin hole to a machine screw (M3 by
  default; M2/M2.5/M4 via `bore_nominal_diameter`). Constructor
  `TechnicPinHoleBushing(length=BEAM_THICKNESS, fit="slip",
  bore_fit="slip", flange=True, flange_od=5.5, flange_thickness=0.8,
  bore_nominal_diameter=None, profile=None)`.
  `length` is the TOTAL axial span of the whole part (barrel plus the
  nested flange, when enabled) — a caller sets it to the target insertion
  depth (e.g. one beam thickness) and gets exactly that depth back
  regardless of the `flange` flag. OD is computed as
  `PIN_HOLE_DIAMETER - 2 * getattr(profile, fit).radial` — the sign is
  negated relative to every other `fit` consumer in the codebase because
  this is the first *male* (printed-peg-into-real-hole) fit site rather
  than a printed-void site; `fit` defaults to `"slip"` rather than
  `"press"` because a printed-and-measured unit showed shipped `press`
  radial values don't model genuine interference on a real printer — the
  OD lands at the modelled (under-nominal) target and spins freely, i.e.
  it measures as `slip`, not `press`. The bore is independently graded via
  `bore_fit` (ordinary, non-inverted female/void semantics), cut with a
  hand-rolled through-hole cutter (not `ClearanceHole`, which hardcodes
  `free.radial` with no override, and not `MetricMachineScrew.to_cutter()`,
  which would destroy the flange with an oversized counterbore). The
  optional single retaining flange sits strictly below `Z=0`, default
  enabled, sized (Ø5.5 mm default) to nest inside the standard Technic
  pin-hole counterbore recess rather than sit on the beam's flat outer
  face. Registered in `build.toml` — M2 / M2.5 / M3 variants under
  `xlego/bushings/`, each at `length=3.6`. An M4 variant was test-printed
  and found unprintable (wall too thin — M4's clearance bore is
  intrinsically close to the whole barrel OD, fixed by the Lego pin hole)
  and is not registered; the class still constructs one programmatically
  via `bore_nominal_diameter=4.3`.

## [0.1.5] - 2026-06-26

### Added
- `PerpendicularHolesLiftarm`: new exported model class — a parametric thick
  studless Lego-Technic liftarm where each hole position bores along either the
  flat-face axis (+Z, `"main"`) or the narrow side-face axis (±Y, `"perp"`),
  generalizing the LEGO 6435016 / design-2391 "Liftarm Thick with Perpendicular
  Holes" family. Constructor `PerpendicularHolesLiftarm(num_holes, hole_axes=None,
  fit="slip", profile=None)`; `hole_axes=None` defaults to the alternating
  `[perp, main, …]` pattern. Reuses `TechnicPinHole` (rotated 90° for the perp
  bores) and the shared `LegoTechnicBeam` stadium body; counterbored pin holes +
  lead-in chamfers on both axes. Registered in `build.toml`
  (`lego/perpendicular_holes_liftarm_5hole.step`).

### Changed
- `LegoTechnicBeam`: stadium-body construction extracted to a shared module-level
  `stadium_beam_body()` helper (internal refactor, no behavior change).
- `_HoleMouthSelector`: gained an additive `axis="z"|"y"` discriminator; existing
  `LegoTechnicBeam` / `LegoTechnicLLiftarm` call sites are unchanged.

## [0.1.4] - 2026-06-26

### Added
- `BevelGear`: new exported model class — a parametric straight-bevel involute
  gear for intersecting-axis (e.g. 90°/miter) drives, completing the gear family
  alongside `SpurGear` / `HelicalGear` / `RackGear`. Constructor
  `BevelGear(module, teeth, mate_teeth, face_width, bore=None,
  pressure_angle=20.0, shaft_angle=90.0, n_flank=32)`; the pitch-cone angle is
  derived from `(teeth, mate_teeth, shaft_angle)`. Teeth are built via a Tredgold
  scaled-section loft (heel + scaled-toe cross-section, common pitch apex); the
  flat back/mounting face sits at `Z=0`. Reuses the shared `Gear` involute
  primitives, `from_iso`, and composable `Bore` shapes. `mesh_with` is overridden
  to pose an apex-coincident, shaft-angle-tilted mate (visual layout only; the
  parallel-axis `Gear.center_distance_to` is not used).

## [0.1.3] - 2026-06-26

### Added
- `HelicalGear.double_helix`: new optional `bool` parameter (default `False`).
  When `True`, builds a herringbone (double-helical) gear — two opposite-hand
  helical halves of `face_width / 2` meeting at a mid-plane chevron, cancelling
  the axial thrust a single helix produces.
- `HelicalGear.crossed_mesh_with()` / `HelicalGear.crossed_center_distance_to()`:
  pose a pair of single-helical gears on crossed (skew) shafts — crossed-helical
  ("screw") gears — with the shaft angle auto-derived from the two helix angles
  or overridden via `shaft_angle`. Posing only; the base `Gear.mesh_with` /
  `center_distance_to` (parallel-axis) are unchanged.

### Changed
- README sample gallery now features a double-helical `HelicalGear` in place of
  the spur gear.

## [0.1.2] - 2026-06-26

_Documentation and release-tooling only — no library code change; upgrading from
0.1.1 is optional._

### Changed
- README: added a PyPI install section (`pip install vibe_cading` /
  `vibe_cading[mcp]`) and a headless-Linux `libgl1` / OpenGL caveat for
  CadQuery's geometry kernel; standardized agent terminology to "AI agents".
- Release pipeline: PyPI publish is now gated by a per-release required-reviewer
  approval on the `pypi` GitHub Environment (replacing the `PYPI_PUBLISH` repo
  variable).

## [0.1.1] - 2026-06-24

### Added
- `LegoTechnicLLiftarm`: new 90°-bent Lego Technic studless liftarm (L-shaped / bent
  beam) class (`vibe_cading.lego.technic_l_liftarm`), parametric in both arm lengths
  (default 3×5), with chamfered pin holes on the 8 mm stud grid and rounded ends.
- `PrintInPlaceHinge.screw_holes`: new countersunk M3 flat-head mount holes — 2 per
  leaf (4 total) — controlled by `screw_holes: bool` (default `True`).

## [0.1.0] - Initial

### Added
- Initial public release of the `vibe-cading` CadQuery library: parametric
  mechanical models (screws, joints, bearings, axles, gears) and Lego-Technic /
  RC interface parts.
- Tolerance system: `vibe_cading.print_settings.get_profile()` and the
  `ToleranceProfile` shape, with user-overridable `print_profiles*.json` and
  `<machine>__<material>[__<brand>]` profile keys.
- Shared primitives in `vibe_cading.cq_utils` and Lego constants in
  `vibe_cading.lego.constants`.
- `vibe_cading.tools.*` CLI utilities (preview, section slicer, hole finder,
  boolean diff, calibration helper, STEP analysis).
- `engine_api.json` wire contract (carries its own `schema_version`).
- Build provenance: `vibe_cading.__version__` (from package metadata) and
  `vibe_cading.__commit__` (build-stamped git SHA).
- MCP (stdio) interface — `python -m vibe_cading.mcp`: a `vibe_cading.mcp`
  subpackage exposing the engine's deterministic introspection tools
  (`list_engine_classes`, `query_engine_class`, `get_design_context`) plus a
  local `compile_model`, over MCP stdio (JSON-RPC on stdin/stdout — no network
  listener, no API key). `mcp` ships as an optional `[mcp]` extra
  (`pip install -e ".[mcp]"`, pinned `mcp>=1,<2`), so a plain install never
  pulls the SDK's ASGI tree; a two-layer CI guard
  (`tools/check_mcp_import_isolation.py`) enforces that `vibe_cading.mcp` never
  enters the library import graph. `get_design_context` surfaces the curated
  Lego nominal allowlist (incl. the studded-System block nominals) + the live
  tolerance profile + doc pointers. (RFC #41.)
