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
- **Breaking** — **`PoweredUpHubBatteryTray`'s upper wall band is gone**
  (round 57, user direction: *"the wall becomes narrower due to the housing
  gets narrower on top, this creates a floating region… for the tray we can
  just remove the narrower part"*). The tray used to follow the housing's
  cavity inboard above its step with a second, narrower band (outer face
  `26.050 − clearance`, inner `25.250`) stacked on the main one. Those two
  bands shared **no X range** — `25.250…25.900` sits entirely inboard of the
  lower band's `26.400` inner face — so they were joined only by a hairline
  horizontal ledge at the seam. That is legal as a solid, and
  `test_single_solid` passed the whole time: connectivity and printability are
  different properties and only the first was ever checked. On a printer it is
  a `0.650 mm` wall standing on a `0.500 mm` ledge with nothing under its
  inboard half. The wall is now one full-thickness band ending at the step.
  Removed with it: `WALL_OUTER_X_UPPER_NOMINAL`, `WALL_INNER_X_UPPER`, and the
  `_wall_outer_x_upper` / `_wall_z_hi` instance fields; `WALL_STEP_Z` is
  renamed **`WALL_Z_HI`**, since it is the wall's top and no longer a step.
  Consequence worth stating: the wall no longer reaches the pack's top (local
  `Z = 23.600` against a `20.000` wall) — above `WALL_Z_HI` the pack is
  confined by the housing's own cavity, not by the tray. The wall is also now
  profile-independent.
- **`PoweredUpHubHousing`'s arm face-dishing is deleted** (user direction) —
  `_dish_arm_faces` cut the real liftarm's recessed pockets into both faces of
  each arm, leaving a `2.756 mm` web. It matched the reference, and it is the
  wrong shape to print: it thins the section of a cantilevered arm exactly where
  bending stress peaks and asks an FDM machine to bridge a thin web. The arms
  are now plain full-thickness beams — a declared departure from the reference
  in favour of strength, with hole positions, pitch and envelope unchanged.
  `_DISH_GAP_OPEN_RADIUS` goes with it.
- **Breaking** — the hand-rolled middle-bore constants are removed from
  `PoweredUpHubHousing`: `MID_BORE_CB_DIAMETER`, `MID_BORE_CB_DEPTH`,
  `MID_BORE_DIAMETER`, `MID_BORE_GUIDED_LEN`, `MID_BORE_RELIEF_DIAMETER`.
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
- **`PoweredUpHubCover` gains a whole-lid running clearance — width, length
  and the tongue-side gaps** (round 59, user direction). Same root cause as
  the hook one round earlier: the reference is a **zero-clearance model
  throughout**, so every face this lid slides past had been built to the
  housing's own nominal figure. Measured on the built pair *before* changing
  anything:

  | interface | before | after |
  |---|---|---|
  | width, X plate edge | 0.150 | **0.295** |
  | length, latch end | **0.005** | 0.145 |
  | length, tongue step | **0.005** | 0.150 |
  | tongue blade, outboard | 0.150 | **0.295** |

  The two length figures are the ones that mattered — 0.005 is the probe's own
  step, so the lid was a hard face-to-face fit against the cavity at **both**
  ends, which no amount of width clearance can relieve. Applied as **derived
  build dimensions, not by editing the constants**: `PLATE_WIDTH`,
  `TONGUE_STEP_Y`, `TONGUE_X_HALF` and the rest are reference *measurements*
  cited as such throughout the class and in `reference_contracts.toml`, so
  rewriting them would destroy that provenance and leave no record of what the
  real part measures. Male faces shrink and female voids grow — the centre
  tongue gap **opens** by the clearance while the blades narrow — so this is
  not a single scale factor. New knob: `PoweredUpHubCover._fit`. A new
  assertion guards the one coupling this could have broken silently: moving
  the plate edge inboard eats the overlap the latch finger needs to fuse to
  the plate, so that overlap is now checked at construction rather than
  assumed.
- **`PoweredUpHubCover`'s latch hook gains lateral running clearance**
  (round 58, from a printed part: *"May need to adjust the width of the U hook
  as well to add a little clearance. Currently it gets stuck."*). The
  **reference gives this pair none** — measured off both reference meshes,
  24853's hook and 25560's slot both span X `5.600…19.200`, `13.600` against
  `13.600`, zero per side. That is not an omission to correct: LDraw models
  *nominal* geometry and a moulded LEGO part takes its working fit from mould
  tolerance and material. Printed on FDM the same pair is a press fit.
  The bind was **not a modelling defect** — measured on the built parts, the
  housing's round-40 channel allowance already delivered a uniform `0.150 mm`
  on all four gaps over the full leg height, with no taper and no local pinch.
  `0.150 mm` per side is simply too tight here in print. Per user direction the
  **housing stays reference-faithful**, so the cover's male features narrow by
  `free.radial` per side, taking the pair to `2 × free.radial` = **`0.300 mm`
  per side** (measured 0.295, the balance being the probe's step). Applied to
  all four features sharing that footprint — U ribbon, retention bead, pad end
  walls and scalloped thumb pad — since narrowing only the ribbon would leave
  the pad jamming at full width; the scallop is *scaled* about the footprint
  centre so it keeps its shape. The hook stays centred on the **nominal**
  centre so the clearance splits evenly: deriving the centre from the narrowed
  width would slide it against one wall for the same total width and no
  clearance, which no seated interference check would report (touching faces
  measure `0.000 mm³`). Retention is unaffected — it acts in Y via the bead
  against the housing's land, which is still the full `13.600` wide. New knob:
  `PoweredUpHubCover._hook_lateral_clearance`.
- **`reference_contracts.toml`: `poweredup-hub-cover-latch-u`'s floor drops
  `46.0 → 43.0`.** The cost was isolated before the floor was touched, not
  inferred: rebuilding the cover with the clearance forced to each value and
  scoring the identical region gives `46.1%` at `0.000` (the pre-change score
  exactly) and `43.5%` at `0.150`, so the whole 2.6-point drop is the
  user-directed clearance and nothing else. The row's region keeps its
  **nominal** X bounds on purpose — shrinking them to the printed footprint
  would stop the clearance counting, which is what defining a deviation away
  looks like. Recorded with it: if a further loosening is ever needed, the
  repeated re-flooring *is* the ratchet, and the answer is to stop scoring the
  hook's X faces rather than to lower this again.
- **`PoweredUpHubHousing`'s tongue end is rounded all the way across**
  (round 56, user direction). Round 55g read *"the tongue side wall should
  have the curve all the way"* as arc **depth** and gave the two outer rib
  bands the full-depth arc while keeping the reference's segmented band
  structure. The user's follow-up — *"I'm still seeing squares"* — was
  correct: that left **`47.200 mm` of the tongue end's bottom edge running
  square to the bed** in the four gaps between bands
  (`tmp/ldraw/tongue_bottom_scan.py`). *"All the way"* is about **extent
  along X**. `BOTTOM_ROUND_X_TONGUE` is now a single band spanning the full
  wall at `BOTTOM_ROUND_CZ_FULL`; `BOTTOM_ROUND_CZ_TRUNCATED` is retained as
  the recorded reference measurement but is no longer used by the built part.
  The **latch end is unchanged** and stays segmented — its middle is square by
  user direction and in the reference (square vertices at `X = ±5.600`).
  `test_the_tongue_end_is_rounded_all_the_way_across` replaces the old
  three-station probe with a sweep over all 141 X stations, because the
  defect was invisible to a hand-picked sample: all three stations sat on
  bands that *had* been rounded, and the gaps between them were what the user
  could see. The latch end's own square middle is its positive control.
- **`reference_contracts.toml`: the `poweredup-hub-housing-tongue-end` row is
  retired and replaced by `poweredup-hub-housing-latch-end-arc`.** After round
  56 the tongue-end row scored `47.4%` against a `68.0%` floor that had
  already been lowered twice (`78.0 → 68.0`). It was **not** lowered a third
  time — that is the ratchet `vibe/INSTRUCTIONS.md` names explicitly. The
  premise, questioned: the row's region (`Y 32.000…33.400`) was drawn around
  the *reference's* tongue-end wall face, and ours is at `35.600` by a
  separately declared deviation — so above the arc our part has no surface in
  that region at all (the checker returns `InconclusiveRegion`), and below it
  the only surface sampled is the arc the user chose. Every achievable value
  measured a deliberate departure. Rescoping was tried in both axes and
  rejected by measurement (`tmp/ldraw/tongue_rescope.py`). Coverage is
  replaced rather than dropped: the new row scores the **latch** end's arc,
  which *is* reference-faithful at `100.0%`, with a `99.0%` floor and a
  demonstrated failing case (shrinking the rounded span to `|X| 24.000` scores
  `96.7%`) — a floor from a check that cannot fail would be decoration.
- **`PoweredUpHubHousing` gives the Cover's plate edge a running clearance**
  (round 48). `PoweredUpHubCover.PLATE_WIDTH/2` and this class's own
  `WALL_X_OUTER_LOWER − WALL_THICKNESS` are both `27.200 mm` — both
  reference-measured, and the same number — so the lid had to pass through a
  slot exactly its own width over the full `62.8 mm` length. Seated
  interference could never catch it (faces that touch without overlapping
  measure `0.000 mm³`); a `0.050 mm` sideways displacement already produced
  `2.366 mm³`, which is what made the round-46 tongue ribs' own `0.150 mm`
  clearance moot. New `_build_plate_edge_relief` takes `profile.free.radial`
  off the wall's *inner* face over the Z band the plate edge occupies
  (`PLATE_EDGE_RELIEF_Z_HI`, derived as the max of the Cover's own
  `PLATE_THICKNESS` / `GROOVE_THICKNESS` / `LATCH_BAND_THICKNESS` = `2.000`).
  The clearance goes on the housing because shrinking the plate would leave
  the side tabs — which root at the independent literal `HANDLE_ROOT_X =
  27.200` — floating clear of it, breaking the Cover into two solids. Local
  because the plate edge is short: the wall keeps its full `0.800 mm` section
  above the band and thins to `0.650 mm` only in a 2 mm strip at the bottom
  rim, which carries no load (the Cover *is* the floor). The relief is bounded
  in Y to the plate's own `[PLATE_Y_LO, PLATE_Y_HI]` span — a first version ran
  the full envelope with a 1.0 mm inboard overcut on the assumption that
  everything inboard of the wall is void, and ate most of the round-46 outer
  rib pair (1.850 mm rib reduced to a 0.050 mm sliver) before
  `test_tongue_ribs_interleave_with_the_cover_tongue_slots` caught it. The lid
  is now free sideways to exactly `±0.150 mm` and locates beyond it, under both
  the shipped `fdm_standard` and the local `bambu_p1s` profile.

### Added
- `PoweredUpHubCover.fit_clearance(profile)` — public classmethod returning the
  per-face running clearance taken off the lid's mating surfaces. A seam, not
  decoration: a subclass returning `0.0` reproduces the pre-round-59
  zero-clearance lid, which is what
  `test_plate_edge_has_running_clearance_against_the_side_walls` needs in order
  to *demonstrate* binding rather than assert it — once the lid carried its own
  clearance, a relief-free housing alone no longer bound, so the falsifier
  required both clearances removed. `PoweredUpHubHousing._build_tongue_ribs`
  also reads it, so the locating ribs track the lid's real slot walls instead
  of the nominal reference ones. Appears in `engine_api.json`.
- Visual contracts for `PoweredUpHubBatteryTray` (`iso_ne`, `front`) and
  `PoweredUpHubBatteryTrayCap` (`iso_ne`), registered in
  `visual_contracts.toml`. Both classes are new in this cycle and shipped
  without one. The tray's `front` elevation is registered as well as its iso
  because a wall-height / section change — exactly what round 57 made — is the
  class of edit a front view catches and an iso can hide.
- **`PoweredUpHubBatteryTray` is one piece again, and the strap now runs
  in a channel cut INTO its floor** (round 55, user direction + marked-up
  sketch). Round 54's split of the whole floor into a separately-printed
  `PoweredUpHubBatteryTrayFloor` is reverted and that class deleted. The
  floor is integral again, but on new geometry rather than the rounds
  52–53 shape:
  - **No standoff.** The floor's underside is flush with the tray's own
    `Z = 0` bottom rim (`FLOOR_THICKNESS = 3.400 mm`), so the part prints
    flat on the bed with nothing bridged — which is the printability
    problem round 54 was trying to solve, solved without splitting the
    part.
  - **One through-corridor** replaces the two separate strap slots,
    joining them into a continuous opening `STRAP_WIDTH = 20.500 mm` wide
    in Y and spanning `|X| ≤ 23.150`. Entry/exit positions are unchanged
    and still outboard of the pack's own `16.000 mm` half-width. The
    corridor is deliberately open at the top — the pack bridges it, which
    is what lets the strap loop over the battery.
  - **`STRAP_CAP_THICKNESS = 1.200 mm` rebate** in the floor's **top**
    face flanking the corridor (blind pocket — asserted in both
    directions, not just "material gone above"). Top rather than
    underside: a top-face pocket opens upward so the floor beneath it
    prints straight off the bed, whereas an underside rebate would leave
    the flanks bridging 1.200 mm in the air — the exact printability fault
    this redesign removes. Guarded by
    `test_the_rebate_opens_upward_so_nothing_bridges`, which fails if the
    rebate is flipped back.
  - `STRAP_CHANNEL_HEIGHT = 1.500 mm` and `STRAP_THICKNESS_TARGET = 1.500`
    — both user-measured on the real strap ("less than 1.5mm", "channel
    just need 1.5mm"). The channel height is an outright constant, NOT
    `strap + margin`: the user sized it from the part, so an added margin
    would only spend headroom the housing has to pay for.
  - Net stack under the pack: `2.700 mm` vs. rounds 52–53's
    `2.700 + 1.500 = 4.200 mm` — **1.500 mm of headroom recovered**.
  - `FLOOR_STANDOFF` and `_STRAP_CRAWLSPACE_MARGIN` are **gone**;
    `STRAP_CHANNEL_HEIGHT` (2.200), `STRAP_CAP_THICKNESS` (1.200),
    `STRAP_CAP_MARGIN_Y`, `STRAP_CAP_Y_HALF` and the classmethod
    `cap_rebate_half_extents(profile)` are new.
- **`PoweredUpHubBatteryTrayCap`** (new class, round 55) — the flat plate
  that drops into that rebate from above and glues down flush with the
  floor's top face, roofing the corridor. **The strap channel runs UNDER
  the plate**: floored by `PoweredUpHubCover`'s own face, roofed by the
  cap. Prints flat on the bed with no supports, which is the entire reason
  it is a separate part — printed in place it would be a bridge over the
  corridor. Its print datum is its own bottom face at `Z = 0` per the
  zero-datum convention, so placing it adds `SEAT_Z = 2.200` on top of the
  Tray's seat translate. Its thickness is *derived* from
  `PoweredUpHubBatteryTray.STRAP_CAP_THICKNESS` and its footprint from
  `cap_rebate_half_extents(...)`, so the two halves of the joint cannot
  drift apart — a mating pair that each re-derive the same dimension is one
  edit away from silently not fitting. Verified: zero interference with the
  Tray (a real glue gap, with a Z-overlap positive control so "no
  interference" isn't two parts that never met), the corridor genuinely
  roofed above and genuinely open below, the seated cap flush with the
  floor's top face so the pack lands on one continuous surface, and the
  clear channel height measured **on the built solids** at 1.500 mm.
  `assembly.py` places four parts.
- **`PoweredUpHubHousing.DECK_Z` 24.000 → 29.600** (round 55, user
  direction: *"just use 29.6 for now. I don't need the top cover (yet)"*).
  The tray floor plus the caliper-measured 20.900 mm pack need 24.800 mm of
  interior and a 3-stud shell gave 21.200; the pack now clears by
  **3.200 mm**, and `test_interior_clears_the_battery_above_the_tray_floor`
  asserts it on the built solids (rounds 51–54 deliberately did not, because
  it was known false).
  - Round 22's 3-stud cap was *not* an approximation of the reference — it
    landed on the reference's own step exactly. Ray-cast of `25560.dat`
    bisects that step at Z = 24.000 (`|X|max` is 35.600 at 24.000 and
    27.200 at 24.010).
- **`PoweredUpHubHousing` steps in above Z = 24.000, like the reference**
  (`_build_upper_step_in`, round 55b, user direction: *"we do need to adjust
  the wall inwards like the reference model, otherwise the trapezoid looks
  weird"*). Raising `DECK_Z` alone extruded the full 72 × 71.2 lower
  footprint the whole way, carrying ~13,000 mm³ the reference lacks — and,
  as the user spotted from the rendered part, leaving the trapezoid socket
  reading as a slot in a flat face rather than the recess it is. The socket
  only reads as a socket because its top edge meets the step.
  - Upper footprint, ray-cast from the reference and positive-controlled at
    Z = 15.000 against the lower walls this class already models:
    X ±27.200 outer / ±26.400 inner, Y −32.000 outer / −30.800 inner at the
    latch end and +32.000 inner at the tongue end, ceiling 28.000, top face
    29.600. **The 28.000 ceiling and 1.600 skin are already this class's own
    `DECK_Z − DECK_THICKNESS` and `DECK_THICKNESS`** — round 47 arrived at
    1.600 by thinning the deck to clear the pack and landed on the
    reference's own figure.
  - Verified face-by-face against the reference: X matches **exactly** on
    both faces, Y on three of four. The fourth is a declared simplification
    — the reference's tongue-end outer face is *drafted* (33.316 at Z 24.1
    to 33.234 at Z 28.0, −0.021 mm/mm) and is modelled vertical at the
    mid-height 33.276, so the error is ≤ ±0.042 mm and changes sign at
    mid-height.
  - Implemented as a **subtraction**, not by re-shaping the wall builders:
    every feature below the step — stepped side walls, both end walls, the
    arms, both trapezoid sockets, the pin bores — is already correct and one
    cut above the step cannot disturb it. The cutter has **no downward
    overcut**; that is the whole correctness condition, since 1 mm here
    would shave the sockets, the wall step, and the arms (which end at
    exactly 24.000 — verified, not assumed).
  - `reference_contracts.toml` gains a scored
    `poweredup-hub-housing-upper-side-wall` row (51.3%, floor set to the
    measurement) plus two documented deviations: the drafted tongue face
    above, and the reference's internal posts/ribs in the upper cavity,
    which are not modelled under the same *internal structure is simplified*
    scope as the lower shell. The row is **scoped to the wall**: the whole
    upper section scores 4.2%, dominated entirely by those omitted posts, so
    a floor on it would be decorative rather than a check.
  - `DECK_STUDS` is **retired**; `DECK_Z` now derives from the new
    `REF_SHELL_Z = 29.600`. The kinematic test's stud-multiple assertion is
    retired with it (29.600 / 8 = 3.7 states nothing) and replaced by one
    tying `DECK_Z` to the measured reference figure.
  - **`SOCKET_Z_HI = 24.000` (new)** — both trapezoid sockets took their top
    from `DECK_Z`, which was the same number for rounds 50–54. Left wired
    that way they would have stretched a trapezoid measured over
    Z 22.1…23.9 across 7.600 mm instead of 2.000, extrapolating the mouth
    5.600 mm past the sampled band. Guarded by
    `test_wall_sockets_stop_at_the_reference_step_not_at_the_deck`.
  - **Both sockets' vertical overcut removed.** It ran 1.000 mm above the
    socket top, which was free air while the part ended at 24.000 and became
    1.000 mm of real side/end wall once it did not — the *overcuts on the
    non-waste side* pitfall, where the overcut never moved and the thing it
    pointed at changed underneath it.
  - **The cord port's Z bound is now stated, not inherited.** Its cutter
    spanned `DECK_THICKNESS` + 1.000 mm of overcut, which while the deck sat
    at 22.400 happened to reach Z 21.400 and sweep the descent clear — in
    particular removing the liftarms' 0.050 mm union seam, which pokes
    inboard past the wall's 26.400 inner face over Z 22.000…24.000, squarely
    in the port's X band. Raising the deck moved the cutter up and left that
    seam behind: deck opening clear, descent pinched. The cutter now spans
    from `WALL_INNER_STEP_Z` (where anything can first intrude into the
    port's X band) to the deck top. Caught by the existing *"a hole is not a
    route"* assertion, which is the reason that test exists.
- **The upper section's two short ends run out to the end trapezoids'
  floor** (round 55d, user direction: *"extend both shorter ends to sit
  inline with the trapezoid (similar to what we currently have for the long
  edges)"*). `UPPER_Y_HI` is now `HALF_Y − END_SOCKET_DEPTH` = **34.400**
  (and `UPPER_Y_LO` its negation), *derived* rather than typed — "inline with
  the trapezoid" is the requirement, so it is the same arithmetic the end
  socket's own floor uses and the two cannot drift apart.
  - The long edges already worked this way, which is what makes a socket read
    as a socket: the side trapezoid's floor is at `|X| = 27.200` and the
    upper section's outer face is the same 27.200, one continuous plane. The
    reference does *not* do this at the ends — it stops at −32.000 / +33.3,
    inboard of its own end-trapezoid floor, leaving those sockets a lip the
    side ones lack.
  - **A departure from the reference**, recorded in
    `reference_contracts.toml`: above the step the Y faces are now ours at
    both ends. X is untouched and stays reference-exact. It also retires the
    previous "tongue-end draft modelled vertical" deviation — that ±0.042 mm
    simplification is moot now the face isn't where the reference puts it.
  - The `poweredup-hub-housing-upper-side-wall` floor moved 51.0 → 48.0
    against a measured 48.7%. **This is a lowered floor**, which this repo
    otherwise forbids, so the reason is written out in full in the contract:
    the region's geometry is provably unchanged (its faces are still asserted
    at exactly 26.400 / 27.200 by a passing unit test), and the metric moved
    because `surface_diff` keeps whole triangles intersecting the region and
    clips only the sampled points — so lengthening the wall's triangles in Y
    redistributes samples at fixed density. Deterministic at 48.7% on
    repeated runs. Re-established, not relaxed.
- **The cover budget is now an input, and the upper section is derived from
  it** (round 55e, user direction: *"Can we use 1mm for all the cover walls?
  I feel 0.65 is too thin. Then adjust the housing top accordingly"*). New
  `COVER_WALL = 1.000`, `COVER_FIT_CLEARANCE = 0.150` (nominal, not the live
  profile — this class's visual contracts are byte-compared, and the cover
  will apply its own clearance when built), `UPPER_INSET = 1.150`.
  - `UPPER_X_OUTER` 27.200 → **26.850**, side socket depth 0.800 → **1.150**,
    and the doubled band's inner face `inner_upper` 26.400 → **26.050**, all
    derived from `UPPER_INSET`. That makes *inline with the trapezoid*
    structural: the socket's depth **is** the upper section's inset, so floor
    and wall are one plane by construction rather than by two constants
    agreeing.
  - **Deepening the socket without moving the wall behind it left 0.450 mm**
    instead of 0.800 — caught mid-round. `inner_upper` is now derived from
    the socket floor ("floor minus one wall") so the next depth change can't
    repeat it. A side effect worth having: Housing's inner face is now
    *uniform* from `WALL_INNER_STEP_Z` to `DECK_Z`.
  - **The roof's cord port moved with the wall** (user: *"you probably also
    want to move the housing roof's wire pass cut to avoid super thin
    edge"*). `x_hi` is now `UPPER_X_INNER` (26.050), not the lower band's
    26.400 — which would have left a 0.450 mm ligament of roof outboard of
    the slot *and* notched the upper wall. Flush, the roof still ends where
    the wall begins, which is the reasoning the original figure was picked
    for, re-derived against geometry that moved under it.
  - **Short ends left alone**: the reference's own 1.200 end-socket depth
    already gives a 1.050 mm cover wall. Moving it to 1.150 buys 0.050 mm —
    below print resolution — at the cost of departing from a measured figure.
  - **`PoweredUpHubBatteryTray`'s upper band moved 26.400 → 26.050** to match
    (inner 25.600 → 25.250, same section). The tray's own tests would not
    have caught the 0.200 mm interference; the cross-part seating check did.
  - **Two honesty repairs.** `test_upper_section_x_faces_match_the_reference`
    asserted against `UPPER_X_OUTER` rather than literals, so it kept passing
    while its *name* claimed a reference agreement that had lapsed — renamed
    to `..._are_the_cover_budget_not_the_reference` and given an assertion
    that fails if the inset reverts. The R55d contract note claiming "X is
    untouched and remains reference-exact" was likewise corrected in place.
  - Conformance: `upper-side-wall` 48.7% → **40.0%**, floor 48.0 → 39.0. This
    lowering is a **real** departure (the wall moved 0.350 mm inboard), unlike
    R55d's, which was a sampling artifact — both are now written out in the
    contract with that distinction explicit, since two lowerings in one round
    is the exact pattern this repo has shipped a broken part behind before.
- **The shell's bottom edge is rounded into both end planes** (round 55f,
  user request). `BOTTOM_ROUND_R = 3.600`, arc centre at `|Y| = 32.000`.
  - **Measured off the reference's own vertices, not off slices.** Slicing
    samples wherever the cutting plane crosses a facet, which made this look
    like two different radii (≈3.2 at one end, ≈3.7 at the other) that
    drifted depending on which Z was fitted. The vertices are the curve's
    control points: both ends fit **one** arc, R = 3.600, rms **0.0005 mm** at
    the latch end. The tongue end is the *same* arc with its centre 0.274 mm
    lower (`BOTTOM_ROUND_CZ_LATCH = 3.600`, `..._TONGUE = 3.326`) — its bottom
    face cuts the arc above the tangent point rather than at it.
  - **The two ends round different segments**, also measured
    (`tmp/ldraw/curve_span.py`): the latch end only `|X|` 19.200–28.000, with
    square vertices surviving at `Y = −35.600` out at `X = ±5.600` — the
    user's *"on the end with the thumb tabs, only the outer segments have the
    curve"*. The tongue end rounds the rib bands and only those: `|X| ≤
    0.800`, 15.600–17.200, 26.000–28.000 — exactly SS12.2's T1/T2/T3.
  - Cut as a true arc (a cylinder along X), not a chamfer. **The X bands take
    no overcut** — the one bounded direction in that builder, because
    bleeding sideways would round segments the reference leaves sharp.
  - Verified against the reference's own stations rather than re-derived from
    the constant: max deviation **0.046 mm**, and that residual is the probe
    sitting 0.02 mm above each station.
  - `test_bottom_face_is_z_zero_and_open` moved from `bbox.zmin == 0.0` to a
    1e-9 tolerance: the cylinder cut leaves ~4e-14 mm of OCCT float noise, and
    an exact compare tests the boolean kernel's rounding rather than the
    datum — the same reasoning the Cover's own datum test already carried.
- **The tongue end's side wall gets the full arc** (round 55g, user
  direction: *"the tongue side wall should have the curve all the way"*).
  The reference truncates the tongue end's arc 0.274 mm up, which beside its
  own neighbours reads as an unfinished curve; the tongue's side-wall bands
  (`|X|` 26.000–28.000) now use the full arc tangent to `Z = 0`, matching the
  latch end. The tongue's **rib** bands keep the reference's truncated one.
  `BOTTOM_ROUND_CZ_LATCH` / `..._TONGUE` are renamed `..._CZ_FULL` /
  `..._CZ_TRUNCATED`, since the choice is now per-band rather than per-end.
  - The conformance cost was **isolated before the floor moved**, not
    inferred: rebuilding with each variant scores 78.61% for the
    reference-faithful rounds (unchanged) and 68.79% as shipped, so the whole
    9.8-point drop is this one deviation. Floor 78.0 → 68.0 on that evidence.
    Rescoping the row to exclude the side wall was tried first and rejected —
    it scores 64.9%, i.e. worse, and the outer rib band overlaps the side wall
    so there is no clean split.
- **`PoweredUpHubCover` gains a window sill** (`_build_window_sill`, round
  55, user direction: *"I'd just add a stripe to the cover"*). Round 51 moved
  the extraction tab from the Cover to the Tray, which seats
  `PLATE_THICKNESS` higher — so the tab now starts at Z = 1.200 while the
  housing's side window it passes through still starts at Z = 0, leaving a
  1.200 mm slot straight through the side wall, open to daylight, for four
  rounds. Nothing detected it: the window is cut to the *tab's* outline and
  the tab still fits it perfectly, so no single-part test could see it — only
  where two parts meet. The sill carries the plate's edge out through that
  slot, at the tab's own `Y` half-width (12.000, so the window's running
  clearance survives on both sides) and stopping 0.150 mm short of the wall's
  outer face (the Cover has ±0.150 of deliberate sideways play from the
  round-48 relief, so a flush stripe would stand proud off-centre).
  `PoweredUpHubCover.solid`'s bounding box therefore grows in X from
  `PLATE_WIDTH` to 2 × 27.850; `test_plate_envelope` now asserts the plate's
  own width separately, at a Z above the sill.
- **Rejected and recorded, not silently dropped**: routing the strap
  through slots in the tray's lower side walls (the user's own alternative,
  which would need no second part). The tray's lower-band outer face is at
  `|X| = 27.200` and `PoweredUpHubHousing`'s lower-band inner face is
  *also* `27.200` — a strap leaving sideways has exactly zero mm to run in.
- **`PoweredUpHubBatteryTray`'s strap holders run alongside the two
  extraction tabs** (user correction, round 53), not across them. Round 52's
  first attempt put both slots at `X = 0` with two `Y` offsets (`±18.0`,
  each wide in X) — a pair of local loops beside the pack, not a strap
  crossing over it. Now both slots share one `Y` (the tabs' own centreline)
  at two `X` positions, `STRAP_HOLDER_X = ±22.000`, transposed to be wide in
  Y (`STRAP_WIDTH`) and narrow in X (`STRAP_THICKNESS_TARGET` + clearance).
  **Verified against the target battery, not just built**:
  `test_strap_span_crosses_the_target_battery_footprint` confirms
  `STRAP_HOLDER_X` clears the Spektrum SPMX812SH2's own half-width
  (`16.000 mm`) — a holder placed inboard of the pack would pass every other
  strap test while silently retaining nothing. `STRAP_HOLDER_Y` is gone;
  `STRAP_HOLDER_X` replaces it. Zero interference against seated
  Housing/Cover re-verified unchanged.
- **`PoweredUpHubBatteryTray` is back** (user direction, round 52) — a
  U-channel, not a copy of the box round 22 deleted: both end walls are
  gone outright, leaving the two long side walls (each carrying the real
  extraction tab from LDraw tray `24849`) and a raised floor with two
  strap-holder slots (`STRAP_WIDTH = 20.500 mm`, sized for a `20 mm` strap;
  `STRAP_THICKNESS_TARGET = 2.000 mm`, user-directed this session, fallback
  `12 × 1.5 mm` noted if a print shows it's too tight). Removing the end
  walls is not a cosmetic simplification — every collision the retired
  class fought from round 13 to round 22 (the tongue riser, the latch-end
  release leg, the raised locating land) was a collision between a
  flat-bottomed END wall and one of `PoweredUpHubCover`'s own raised,
  low-Z features; deleting the end wall deletes the collision class with
  it, and this class needs no relief cut. Instead, the side walls' own Y
  reach (`WALL_Y_LO`/`WALL_Y_HI`) stops a `0.100 mm` safety margin short
  of Cover's `LATCH_BAND` and locating groove so their footprints never
  overlap by construction. Zero interference confirmed against both
  seated `PoweredUpHubHousing` and `PoweredUpHubCover`.
  **Deliberately not asserted**: whether the pack still fits above this
  Tray's floor inside the current 3-stud housing — it does not, at
  `21.200 mm` of interior against a floor that alone consumes down to
  `Z = 5.200 mm` above the cover, and the user explicitly asked to design
  the tray first and revisit the housing's height in a follow-up round.
- **The extraction tab moves from `PoweredUpHubCover` back to
  `PoweredUpHubBatteryTray`** (round 52) — round 22 re-homed it onto Cover
  as a stand-in once the tray was deleted; this is a return to the real
  reference's own division of labour (`24849` carries the tab, `24853`
  never did). **Breaking**: `PoweredUpHubCover.HANDLE_*` (11 constants) and
  `_build_side_handle` are gone; the equivalent `PoweredUpHubBatteryTray
  .TAB_*` constants and `_build_extraction_tab` take their place, in the
  Tray's own local Z frame (its bottom rim, not world `Z = 0`).
  `PoweredUpHubHousing._build_side_window` now derives its cut from the
  Tray's tab instead of Cover's, converting the Z-valued constants through
  the fixed `PLATE_THICKNESS` seating offset — the window's own geometry
  is unchanged, only its source class. `PoweredUpHubCover`'s overall X
  envelope shrinks back to its plain `PLATE_WIDTH` (`54.4 mm`), since
  nothing on it stands proud past the plate edge anymore.
- **The trapezoid mating socket in each END wall's outer face** (user
  direction, round 51) — the other half of the cap register. Measured off
  `25560.dat` along ±Y rather than assumed to transfer from the side walls,
  and it does not transfer: identically on both ends the recess extends to
  `|X| = Z − 8.000`, i.e. an isosceles trapezoid `28.000 mm` wide at
  `Z = 22.000` opening to `32.000 mm` at `Z = 24.000`. Only the Z band and the
  45° flank angle are shared with the side sockets; the half-widths
  (`14.000 → 16.000` vs `9.200 → 11.200`) and the depth are not. Depth is
  `1.200 mm` — the outer skin the reference removes outright — with the floor
  at `|Y| = 34.400`; it stays a blind pocket here because our end walls are
  thicker than the reference's skin there (`4.800 mm` at the latch end, the
  solid deck above the bay at both ends). New constants `END_SOCKET_Z_LO`,
  `END_SOCKET_X_HALF_LO`, `END_SOCKET_X_HALF_HI`, `END_SOCKET_DEPTH`. The cut
  runs after the deck union, since above the bay the socket's floor *is* deck
  material. Both overcut directions verified to lie outside the part's
  bounding box before use.
- **The trapezoid mating socket in each side wall's outer face** (user
  direction, round 50) — the intended register for a future cap. Measured off
  `25560.dat`: an isosceles trapezoid at `X = 27.200`, narrow edge down,
  `18.400 mm` wide at `Z = 22.000` opening to `22.400 mm` at `Z = 24.000`,
  45° flanks, area `40.800 mm²` = `(18.4+22.4)/2 × 2` exactly. New constants
  `SOCKET_Z_LO`, `SOCKET_Y_HALF_LO`, `SOCKET_Y_HALF_HI`, `WALL_INNER_STEP_Z`.
- **Corrected: the side wall's outer step was never a full-length feature.**
  Rounds 16–49 read the design doc's §4 line *"side-wall step at 22.0"* as
  running the whole wall and recessed the outer face to `27.200` above
  `Z = 22` everywhere — which is the socket's own depth applied along the
  entire length, so the part had no socket because it was *all* socket. §4
  does record that step's extent (`z ±23` = `Y ±9.200`) but never says it is
  local. Ray-cast against the reference the outer face steps back at
  `Z = 22.000` inside the trapezoid and `Z = 24.000` outside it. The wall now
  runs `28.000` outer for its full height, doubling to `1.600 mm` at
  `WALL_INNER_STEP_Z = 21.200` (the reference's own `X = 26.400` panel starts
  there) so the socket is a pocket and not a hole. Verified by ray-section at
  four stations against Philo's own geometry, and the wall immediately below
  the socket band measures **100.0% agreement, mean 0.000 mm** against the
  reference. Battery fit is unaffected — interior height is unchanged and the
  pack is `±16.0` against a wall that thickens to `26.400`. Guarded by
  `test_side_wall_carries_the_trapezoid_mating_socket`, whose falsifier is
  locality: the pre-round-50 geometry reads `27.200` at both stations.
- **A cord pass-through in `PoweredUpHubHousing`'s deck** (user direction,
  round 49) — `CORD_PORT_WIDTH` × `CORD_PORT_LENGTH` = `10.0 × 20.0 mm` clear,
  sized so an EC3-class connector passes, not just the IC2 the pack ships with.
  **The orientation is forced, not chosen**: the pack fills the box (`20.9` of
  `21.2 mm` in Z, `58.0` of `62.8` in Y), so the only route is the side channel
  beside it — and at deck level that channel is `10.4 mm` wide, not the `11.2`
  it is lower down, because the wall steps inward at `WALL_STEP_Z`. So the 20
  runs along Y. The outboard edge is flush with the stepped wall's inner face
  (`26.400`); a slot stopping short would leave a 20 mm long, one-extrusion-wide
  ligament of deck. The `−Y` edge derives from `PoweredUpHubCover.LATCH_BAND_Y_HI`
  rather than the latch end wall: flush with the wall cut a perfectly good
  opening that a connector could **not descend through**, because the Cover's
  latch U reaches `Y = −30.700`, `Z = 12.160` into that channel — a hole is not
  a route. `CORD_PORT_MARGIN` keeps the clear opening at the full `20 × 10`
  despite the `1.000 mm` corner radius (a sharp box needs `m ≥ r(1−1/√2)`).
  Guarded by `test_cord_port_is_a_clear_opening_into_the_battery_bay`, which
  pushes a solid block down the real descent path against housing, cover and a
  seated pack, and cross-checks the opening's position against the built solid
  so its duplicated arithmetic cannot silently drift.
- **A reference-conformance contract for the housing's tongue end.** The
  LDraw reference for the housing (`parts/25560.dat` → `24851` → subparts,
  Philippe Hurbain [Philo], CC BY 4.0) is now dumped to an STL by
  `tmp/ldraw/dump_housing_stl.py`, so the round-46 tongue ribs finally have a
  measured `surface_diff` number instead of only interleave and kinematic
  evidence. Registered in `reference_contracts.toml` as
  `poweredup-hub-housing-tongue-end` at a `78.0%` floor (measured `78.6%`),
  with the single-wall departure declared **without** a region so it keeps
  counting rather than being defined away. The frame is established rather
  than assumed — the dump re-datums to our bottom-face-at-`Z=0` convention and
  three independent figures confirm it (`Y ±35.600` = `HALF_Y`, `X` envelope
  `72.000` = `test_envelope_is_exactly_72mm_in_x`, height `33.800` = the
  design doc's own measured value). Like the lid row, the reference is not
  committed, so this SKIPS WITH NOTICE in CI and is a contributor-local check.
- **`PoweredUpHubHousing`'s deck thins `2.000 → 1.600 mm` so the target battery
  actually fits** (round 47). The box exists to hold a Spektrum SPMX812SH2.
  Every vendor lists it as `58 × 32 × 20 mm`, which is what rounds 22–46
  designed against; caliper-measured on the real part it is **`20.900 mm`**
  tall. Interior height is `DECK_Z − DECK_THICKNESS − PLATE_THICKNESS` =
  `24.0 − 2.0 − 1.2` = `20.800 mm`, so the real pack interfered by `0.100 mm`
  and held the Cover proud of its own latch — a functional miss, not a
  cosmetic one. At `1.600` the interior is `21.200 mm` and the measured pack
  clears by `0.300 mm`. The external 3-stud / `24.000 mm` height is
  deliberately unchanged (the round-22 decision stands); what is given up is
  the deck landing exactly on `WALL_STEP_Z`, which was the reason `2.000` was
  picked and costs nothing structural. `1.600 mm` is still four perimeters at
  a 0.4 mm nozzle. Guarded by `test_interior_clears_the_target_battery`, which
  measures the built solids against the pack — until now every test in this
  family checked the two printed parts against each other and none checked
  them against their payload; verified to fail at the old `2.000`.
- **`PoweredUpHubCover`'s side tabs get their raised border** (user direction,
  round 47). SS2.3 recorded the `X = ±28.400` level as a straight "finger ledge"
  over `Y ±8.400`, `z 7.200…8.400`, and rounds 22–46 built exactly that. Read
  back off `24849`'s own triangles, that plane spans the tab's whole envelope
  (`Y ±12.000`, `z 0…8.400`) at only `42.702 mm²` — ~21% of its own bounding
  box, which no solid band can be. It is a **uniform `1.200 mm` border**
  tracing the tab outline round three edges, enclosing the recessed pad face at
  `X = 28.000`; SS2.3's separately-listed "R2.400 quarter-round recess at each
  corner" is that interior's own corner, not another feature. One new constant,
  `HANDLE_FRAME_WIDTH`, because the interior profile is the outer profile inset
  by that single number and all three measured pairs confirm it exactly
  (`12.000−1.200=10.800`, `3.600−1.200=2.400`, `8.400−1.200=7.200`, shared
  round-over centre). The old straight band is dropped — the border's top
  segment spans the same two planes and is wider, so it was a strict subset.
  `HANDLE_LEDGE_X/_Y_HALF/_Z_LO/_Z_HI` keep their values and meanings, so
  `PoweredUpHubHousing._build_side_window` is untouched and the seated
  interference stays `0.000 mm³`.
- **`PoweredUpHubCover`'s tongue is segmented into the reference's four
  blades** (user direction, round 45). Rounds 18–44 built it as one continuous
  slab; the reference is four separate blades — `|X|` in `[0.800, 15.600]`
  (Tongue A, either side of the centreline) and `[17.200, 26.000]` (Tongue B) —
  with `1.600 mm` gaps between them that receive the housing's own locating
  ribs. Two new constants, `TONGUE_GAP_X_INNER` and `TONGUE_RIB_X_HI`;
  `TONGUE_X_HALF` and `RISER_X_HALF` keep their meaning as the tongue's outer
  bounds, so the gaps are *cut* rather than the blades being built separately.
  Measured over the tongue region against the reference, worst-direction
  surface agreement goes `91.2% → 98.8%` — the residual the slab carried sat
  exactly on the four blade boundaries, which is what earlier rounds read as
  "reinforcements at both edges" (a consequence of the segmentation, not ribs
  added to a solid blade). Retention is unchanged: the blade bears on the
  housing ledge in Z, and the centre gap costs `1.600 mm` of a `31.200 mm`
  blade. Mirrored on the housing in the entry below.
- **`PoweredUpHubHousing`'s tongue wall now carries the locating ribs that
  enter those slots** (round 46). The wall was full width, so the Cover's new
  slots opened onto nothing and the reference's ±X location at this end
  (§12.2, "Sideways → located") existed on neither part. `_build_tongue_ribs`
  builds the three mirrored rib pairs the reference measures — centre
  `|X| ≤ 0.800`, inner `|X| 15.600…17.200`, outer `|X| 26.000…28.000` (T1/T2/T3)
  — via two new constants, `TONGUE_RIB_CENTRE_X_HALF` and
  `TONGUE_RIB_X_BANDS`. Every flank that faces a Cover blade is pulled back by
  `profile.free.radial`; the outer band's `28.000` flank is the shell's own
  outer face and takes none. Each rib starts where its own slot actually opens
  — the centre one at `LEDGE_Y_LO`, not the plate edge, because the Cover's
  castellated notch floor crosses the centreline and a full-depth centre rib
  collided with it by `0.130 mm³`. Measured against a rib-free baseline so the
  numbers are the ribs' own: seated interference stays `0.000 mm³`, the ribs
  contribute nothing to a sideways displacement within their `0.150 mm` flank
  clearance and a monotonically growing amount beyond it, and nothing at any
  distance to withdrawal along `−Y` (the tongue end is a lap, not a snap).
  These ribs are the reference's *optional* X-location — the shell's own side
  walls at `|X| 27.200` already locate the lid at zero clearance and remain the
  primary locator; retention is still the rebate bearing in Z.
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

### Added
- **`TechnicPinHole` gains `counterbore_ends`** (keyword-only; `"both"` /
  `"entry"` / `"none"`, default `"both"`). LEGO uses two different pin-hole
  shapes and LDraw ships a primitive for each: `connhole`, counterbored at both
  rims, for a through hole, and `connhol3`, counterbored at the entry rim only,
  where the hole stops inside the part. Cutting a far-side flange into a blind
  hole hollows out the material immediately behind its floor — exactly where
  there is least to spare. The default preserves every existing caller
  byte-for-byte.

### Fixed
- **`PoweredUpHubHousing`'s arms are built at the reference's own dimensions
  instead of being trimmed to fit.** Measured off Philo's `s\24851s01.dat`, the
  arm is `7.200 mm` wide with an end cap of radius `3.600 mm` centred **on** the
  outer hole — cap radius equals half-width, so centred at `32.000` it is
  naturally tangent to `35.600` in both plan directions and nothing needs
  cutting. Rounds 16–42 instead took `PerpendicularHolesLiftarm`'s generic
  `7.800`-wide, `3.900`-cap, `24.000`-long beam and squared it off with three
  flat trims, which left a **`3.440 mm` flat chord across the tip**, a flat down
  the outboard face, and the re-entrant notch where the arm met the end wall.
  The arm is now a `23.200 × 7.200` stadium with caps on the hole centres and
  `TechnicPinHole` cutters; `ARM_WIDTH_TRIM_Y` is removed, `ARM_LENGTH` /
  `ARM_WIDTH` / `ARM_CAP_R` added, and `PerpendicularHolesLiftarm` is no longer
  used by this class. Envelope unchanged at `72.0 × 71.2 × 24.0`.
- **`PoweredUpHubHousing`'s arms now meet the body on a flat face** (user
  direction). A full stadium cap touches its end plane at a single point, so the
  arm joined the housing at a sharp re-entrant cusp — body edge in at
  `Y = 35.600` to `X = 28.400`, dropping to `Y = 32.000` before the arc began —
  a notch at the root of a cantilever, and a crevice to print. The inboard half
  is now squared off for the arm's full length, giving flat end faces out to the
  hole line, while the outboard corner keeps its `R3.600` round. Envelope
  unchanged; volume `21742.4 → 21910.8 mm³`.
- **The horizontal arm hole now matches `connhol3`** — `7.200 mm` deep, floored
  at `|X| = 28.800` with `0.400 mm` of arm behind it, counterbored at the
  outboard rim only. Round 42 floored it at `28.000` with counterbores at both
  rims. `MID_BORE_DEPTH` / `MID_BORE_FLOOR_X` replace the round-42
  `MID_BORE_MIN_FLOOR`-only derivation.
- **`PoweredUpHubHousing`'s middle arm hole is a real, blind Technic pin hole.**
  It was three hand-rolled cylinder segments re-implementing a counterbored pin
  hole without being one — so it never got the profile-aware bore sizing every
  other pin hole in the repo has — and its `15 mm` relief overcut punched clean
  through the side wall into the battery cavity. It is now a
  `TechnicPinHole.standard()` cutter entered at the boss tip (`|X| = 36.000`)
  and floored at the side wall's outer face (`|X| = 28.000`), leaving the
  `0.8 mm` wall intact. The depth is that distance rather than a literal, and
  works out to exactly one stud pitch, so the hole is full-depth *and* blind;
  both readings are asserted. Measured bore Ø `4.96` against `5.020` nominal.
  `test_middle_bore_breaks_through` — which asserted the breach by probing a
  point **inside** the cavity, empty whatever the bore did, and so could not
  fail — is replaced by `test_middle_bore_is_blind`.
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

### Added
- `vibe_cading/mechanical/bearings.py`: `Bearing.blind_pocket_dims()` (static
  method — diameter/depth for a blind bearing pocket, given just an OD and
  width — not registered in `engine_api.json`'s wire contract, which
  catalogs only `__init__` and public classmethod factories, by design) and
  `Bearing.mr85()` (the MR85-2RS preset, matching the existing
  `b608()`/`b623()`/etc. classmethods). Consolidates bearing-pocket-sizing
  math that `FreespinHexHub`, `HexHubNut`, and `BearingHexHousing` each
  previously duplicated independently — `FreespinHexHub` and `HexHubNut`
  now delegate their pocket-dimension properties to the shared formula
  (verified behavior-identical by a regression test that computes each
  consumer's expected diameter/depth independently, from the original
  inline formula against an explicit fit-grade profile — not by
  re-deriving "expected" via the same shared call under test, which
  couldn't catch a drift in the shared formula's own defaults). Pure
  refactor — no consumer's printed geometry changes. See `TODO.md`'s
  "Consolidate blind bearing-pocket sizing" entry (flagged in PR #88's
  review cycle).

### Changed
- `vibe_cading/mechanical/bearings.py`: `MR85_ID`/`MR85_OD`/`MR85_W` now
  live once here (the single source of truth for the `vibe_cading.rc.*`
  hex-hub family) instead of being duplicated in `freespin_hex_hub.py`,
  `hex_hub_bearing/hex_hub_nut.py`, and `hex_hub_bearing/bearing_hex_housing.py`.
  `MR85_ID` was previously importable from `vibe_cading.rc.freespin_hex_hub`
  (unused there) and is no longer — import it from
  `vibe_cading.mechanical.bearings` instead.
- **(minor bump — breaking geometry change to `BearingHexHousing`'s existing
  bearing pocket, see below)** `vibe_cading/rc/hex_hub_bearing/`: `HexHubNut`
  now carries its own blind bearing pocket sunk into its outward (top,
  wheel-facing) face, sized for the identical MR85-2RS bearing seated on the
  shaft side by `BearingHexHousing` (new `bearing_od` / `bearing_width`
  constructor params, default 8.0 mm / 2.5 mm) — both ends of the fused
  `HexHubWithBearing` deliverable now seat a bearing, not just the shaft
  side. Both the new hex-side pocket and the pre-existing shaft-side pocket
  now use `free` fit grade (drop-in/pop-out by hand) rather than the prior
  `press` grade — a behavior change to `BearingHexHousing`'s already-shipped
  printed geometry (pocket diameter 8.08 mm -> 8.30 mm on `fdm_standard`),
  not merely additive, hence the minor version bump — so the bearing is
  user-replaceable at both ends.
  `Bearing.outer_pocket()` gained a `fit: Literal["press", "free", "slip"] =
  "press"` parameter to support this (defaults to the prior behavior for
  every other caller; raises `ValueError` on an unrecognized grade name).

### Fixed
- `vibe_cading/tools/view.py`: no longer reports a false success when no OCP CAD
  Viewer is listening. Previously it printed `Showing <Class>` and exited 0 while
  the model was never transmitted (the underlying connection failure surfaced only
  as a warning). It now resolves the target port, probes it, and aborts with exit 1
  and a message naming both ways to start a viewer. The probe is deliberate:
  `ocp_vscode.get_port()` trusts `OCP_PORT` without checking it, so resolution alone
  would let `OCP_PORT=<dead port>` reopen the same false success.
  `--export` is unaffected — the STEP file is written and the command still exits 0,
  warning on stderr that nothing was displayed, so headless export keeps working in
  scripts and `&&` chains.

### Added
- `docs/viewer.md`: guide to running the OCP CAD Viewer **in a plain browser tab**
  via the standalone server that ships inside `ocp_vscode`
  (`python3 -m ocp_vscode --host 0.0.0.0 --port 3939` → `http://localhost:3939/viewer`),
  with no VS Code required. Covers the client/server split, port forwarding, and
  the "browser tab must be open before you push" behaviour. Port 3939 was already
  in the dev container's `forwardPorts`, so no container change was needed.
- `vibe_cading/rc/hex_hub_bearing/`: RC 12 mm hex-wheel-adapter hub fused with
  an MR85-2RS bearing housing (`HexHubNut`, `BearingHexHousing`, and the
  primary deliverable `HexHubWithBearing`, which `.union()`s the two into a
  single printed body with a 0.02 mm boolean-robustness overlap epsilon at the
  flush join — no press-fit register). `HexHubNut`'s through-bore is 6.0 mm
  nominal (`free`-fit-grade), sized as a running-clearance hole around a
  uniform 5 mm-nominal stub axle — matching `FreespinHexHub`'s established
  convention. See `docs/design_plans/2026-08-25-rc-hex-hub-bearing_design.md`.
- `vibe_cading/lego_adapters/axle_hex_hub/`: Lego Technic axle -> 12 mm RC hex
  hub adapter (`AxleCompressionCollet`, `HexInsertHub`, and the primary
  deliverable `AxleHexHubAdapter`, which `.union()`s the two into a single
  printed body with the same 0.02 mm boolean-robustness overlap epsilon
  convention as `HexHubWithBearing`). `AxleCompressionCollet` is a 10 mm OD,
  10 mm-tall slotted split-collet cylinder carrying a keyed cross-shaped
  Technic-axle bore cut to exactly its own height (`free` fit plus a small
  extra radial clearance bump scoped to the bore only), with 2 axial collet
  slots (0.6 mm gap) aligned with the bore's arm-tip axis for an
  off-the-shelf compression collar's grub screws, a raised stop ring 6.5 mm
  from the shaft end limiting collar insertion depth, and two locating
  dimples 90 deg off the slots for the collar's set screws. `HexInsertHub`
  is a 12 mm hex prism carrying a parametrized straight-walled M3-class
  heat-set-insert pocket (`insert_length` default 5.0 mm) with no axle-bore
  feature of its own.
  See `docs/design_plans/2026-08-25-lego-axle-hex-hub-adapter_design.md`.

### Deprecated
- `vibe_cading.rc.freespin_hex_hub.FreespinHexHub` — superseded by
  `vibe_cading.rc.hex_hub_bearing.hex_hub_with_bearing.HexHubWithBearing`
  (same "12 mm hex + MR85-2RS bearing" family, modelled as fused component
  classes with tolerance-profile-driven fit grades on both the bore and the
  bearing pocket). `FreespinHexHub` now emits a `DeprecationWarning` on
  construction; its `build.toml` registration (`rc/hex_wheel_hub_12mm.step`)
  is unchanged pending a separate human decision on migration. May be removed
  in a future release.

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
