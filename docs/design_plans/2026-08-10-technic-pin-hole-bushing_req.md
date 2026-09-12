# Requirements: Technic Pin-Hole Bushing

<!-- Filename: 2026-08-10-technic-pin-hole-bushing_req.md (tracked in git under docs/design_plans/) -->

## Meta
- **Initiator role**: @admin (on behalf of user request)
- **Date**: 2026-08-10
- **Domain integrity gate**: NO — no data/model contracts involved; this is a new parametric mechanical part.

---

## Problem Statement

The user wants to 3D-print (TPU) a round bushing that friction-fits into a standard
Lego Technic pin hole, with a bore sized so an M3 screw shaft passes freely through it
(the screw does not thread into the bushing, and the bushing is not required to spin
freely on the screw — just clear it). No existing model class covers this: the closest
analogs (`TechnicAxleToBearingSleeve`, `HexStandoff`) are a flanged bearing sleeve and a
hex-profile standoff respectively, neither a plain round pin-hole friction bushing.

## User Story / Motivation

As a Lego-Technic-and-RC-hardware builder, I need a simple round bushing that lets an
M3 screw pass through a Technic beam's pin hole without the screw binding on the Lego
plastic (or, here, the TPU bushing), so that an M3 fastener can be used to clamp a
Technic assembly the same way a Lego pin normally would, while spreading axial clamp
load over a formed bushing.

## Functional Requirements

1. A new class, `TechnicPinHoleBushing`, MUST model a plain cylindrical tube: an
   outer cylinder with a concentric bore, no flange, no external features.
2. The bushing's outer diameter (OD) MUST be sized to friction-fit into a Lego Technic
   pin hole (`PIN_HOLE_DIAMETER` in `vibe_cading/lego/constants.py`), using the
   project's `ToleranceProfile`/`fit` convention (`fit: Literal["free","slip","press"]`,
   same pattern as `TechnicPinHole`) rather than a hardcoded diameter. Default `fit`
   MUST be `"press"` (friction fit is the class's whole purpose).
3. The bushing's bore MUST be sized as a clearance hole for an M3 screw shaft — the
   screw MUST pass through freely without threading and MUST NOT be required to spin
   freely (a plain clearance fit is sufficient). The bore sizing MUST reuse the
   project's existing M3 clearance-fit convention (`MetricMachineScrew.from_size("M3",
   ...).to_cutter(fit="clearance", profile=...)` or equivalent) rather than a
   hardcoded bore diameter.
4. The bushing's length (its dimension along the bore axis) MUST default to one Lego
   Technic liftarm thickness (`BEAM_THICKNESS` in `vibe_cading/lego/constants.py`,
   currently 7.8 mm), but MUST be an overridable constructor parameter so a user can
   size it to span multiple stacked liftarms.
5. The class MUST expose a `.solid` property (positive geometry, `cq.Workplane`) per
   the project's boolean-interface convention. It MAY additionally expose
   `.to_cutter(profile=None)` if a bushing-shaped cutter is useful downstream (e.g. for
   subtracting a bushing pocket from an enclosing part), but this is not required by
   this task.
6. The bushing MUST accept a `material`/`profile` keyword per the project's
   Material-Specific Screw Tolerances convention (default `"fdm_standard"`), resolved
   via `vibe_cading.print_settings.get_profile`.
7. If the class exposes a `fit: Literal["free","slip","press"]` constructor parameter
   (per Requirement 2), it MUST be registered in the engine-api allowed-values
   registry (`tests/tools/test_engine_api_allowed_values.py`) and `engine_api.json`
   MUST be regenerated in the same PR.
8. The origin convention MUST place the bushing centered on its rotation/bore axis at
   `(0, 0, 0)`, with the bushing extruded from `Z=0` upward to `Z=length`, consistent
   with other cylindrical Lego-adapter parts in this codebase.
9. A visual-contract SVG (`iso_ne` at minimum) MUST be generated and registered in
   `visual_contracts.toml`, per the project's Visual Contract Deliverable rule (new
   visible geometry).
10. The class MUST support an optional flange/collar at the `Z=0` end (single-sided
    shoulder), gated by a constructor parameter (default enabled) with overridable
    flange outer diameter and thickness. Purpose: when `length` spans more than one
    stacked liftarm, the flange acts as a positive axial stop so the bushing cannot
    slide/fall through the stack; when `length` equals the single-liftarm default the
    flange still sits flush against the beam face and is harmless. The pin-hole-fit
    barrel geometry (Requirements 1–4) MUST be unaffected by whether the flange is
    enabled — the flange is strictly additive material at `Z<=0`, extruded downward
    from `Z=0` (not into +Z, so it never displaces the friction-fit barrel).

## Non-Functional Constraints

- No new third-party pip dependencies.
- New file MUST carry the AGPLv3 header per project licensing rules.
- Class MUST NOT be auto-registered in `build.toml` — present the proposed entry to
  the human for explicit approval, per project rule.
- No wall-time/build-time budget assertions apply to this task (not a CLI/build-time
  change).

## Known Domain Constraints

- `PIN_HOLE_DIAMETER = 4.8` mm (`vibe_cading/lego/constants.py`) — real-Lego nominal
  Technic hole envelope; printer clearance is added via `ToleranceProfile`, never
  baked into the constant itself.
- `BEAM_THICKNESS = 7.8` mm (`vibe_cading/lego/constants.py`) — current liftarm
  thickness value (project's own prior confirmation supersedes the user's informal
  "7.2 mm" estimate in this task's origin request).
- `ToleranceProfile` fit-grade convention: `free` → clearance/loose, `slip` → standard
  running fit, `press` → friction/interference fit. `TechnicPinHole` bores
  `PIN_HOLE_DIAMETER + 2 × profile.<fit>.radial`; a bushing OD is the inverse
  (positive/male) side of the same interface and should apply the profile's radial
  allowance with the opposite sign convention used for male vs. female features
  elsewhere in the codebase (co-design to confirm exact sign/formula against
  `TechnicPinHole` and any existing male-cylinder-into-hole precedent).
- M3 clearance-hole sizing must come from `MetricMachineScrew`'s existing thread-size
  table + `fit="clearance"`, not a new hardcoded diameter constant.
- No TPU-specific constants exist in this codebase; TPU's added compressibility
  (relevant to a friction fit) is expected to be handled by the user calibrating
  `slip`/`press` radial allowance in `print_profiles_user.json`, not by a
  material-name branch in the class.

## Out of Scope

- Chamfers, external grip features, printed labels, or any geometry beyond a plain
  OD/bore tube with the single optional flange in Requirement 10.
- Double-flanged (both-ends) or user-shaped flange profiles — a single flange at
  `Z=0` is sufficient for the axial-stop purpose.
- A `to_cutter()`-driven pocket-cutting workflow for embedding the bushing into a
  larger part (may be a natural follow-up, not required here).
- `build.toml` registration (requires separate explicit human approval per project
  rule).
- TPU-specific print-profile calibration values (the user calibrates their own
  `print_profiles_user.json`; this task only ensures the class consumes the profile
  correctly).

## Open Questions

- [ ] Exact OD formula/sign convention vs. `profile.press.radial` for a *male*
      cylinder entering a hole (as opposed to `TechnicPinHole`'s female bore) —
      resolve in co-design against existing precedent in the codebase.
- [ ] File location: `vibe_cading/lego_adapters/technic_pin_hole_bushing.py` (adapter
      between Lego Technic and a generic M3 fastener) vs. `vibe_cading/lego/` (pure
      Lego geometry) — resolve in co-design; `lego_adapters/` is the initiator's
      working assumption since the part exists specifically to interface Lego with a
      non-Lego M3 screw.

---

## Human Confirmation Checkpoint
- [x] Requirements reviewed and confirmed by human
<!-- Do not proceed to design until this box is checked. -->
