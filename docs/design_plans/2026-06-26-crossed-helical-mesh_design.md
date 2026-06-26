# Design: Crossed-axis (crossed-helical / "screw") gear meshing

## Meta

- **Date:** 2026-06-26
- **Role:** TL (architecture blueprint — NOT production code)
- **Scope:** `vibe_cading/mechanical/gears/` — add crossed-axis pose support
  to the gear meshing layer. Visualization/layout posing only (like the
  existing `mesh_with`), not a motion sim.
- **Status:** Blueprint ready for Developer implementation.

## Objective

`Gear.mesh_with(other, phase)` today poses a **parallel-axis external mesh**:
translate `other` along +X by the parallel center distance, rotate about +Z.
Add a **crossed-axis** pose (shafts skew, typically Σ=90°) for a pair of
single-helical gears (crossed-helical / "screw" gears).

## Verified premises (probed, not taken on faith)

All four technical constraints from the brief were verified against the live
code with two throwaway `tmp/` probes (since deleted):

1. **Crossed is a *posing* relationship, not geometry.** A single-helical
   `HelicalGear.solid` is unchanged when used in a crossed pair. Confirmed:
   the same `solid` reused in both the parallel and crossed transforms below.
   → Crossed must NOT be a constructor flag; it is a meshing-layer concern.
   It is also mutually exclusive in *use* with `double_helix` (herringbone
   cancels axial thrust on parallel shafts; crossed pairs are normally
   same-hand single-helical). We do **not** forbid the combination in code —
   a double-helical gear has a well-defined axis and could be posed crossed —
   but the validation will warn-by-docstring, not hard-block.

2. **Crossed mesh condition = equal *normal* module + equal *normal* pressure
   angle**, with possibly different helix angles → different *transverse*
   modules. Probed `β₁=60°, β₂=30°` (Σ=90°): `normal_module` matched (2.0=2.0),
   `normal_pressure_angle` matched (20°=20°), but transverse modules **differed**
   (4.000 vs 2.309).

3. **`center_distance_to()` is WRONG for crossed gears.** It checks equal
   `self.module` (the *transverse* module on the base). Probe confirmed it
   raises `ValueError("Gears must have the same module to mesh properly.")`
   on the `β₁=60/β₂=30` pair. → A crossed-aware sibling is required.

4. **Posing transform (the risky part) — verified geometrically.** For
   `β₁=β₂=45°` (Σ=90°), with `self` axis along +Z at origin:
   `other.solid.rotate((0,0,0),(1,0,0), Σ).translate((cd,0,0))` places `other`
   with its axis along −Y (bbox confirmed Y∈[−12,0], symmetric in X/Z about
   the `cd` centre), `cd = r1+r2 = 56.57`. Both gears remain **single solids**
   (`len(solids)==1` each). The two axis lines are then mutually perpendicular
   and skew, separated by `cd` along their common perpendicular (the X axis).

## Decisions

### D1 — Where the API lives → **dedicated method on `HelicalGear`**

`def crossed_mesh_with(self, other, *, shaft_angle=None, phase=0.0)` on
`HelicalGear`, NOT a `shaft_angle=None` parameter on base `Gear.mesh_with`.

**Rationale (Deep-Modules / dual-lens):**

- **Contributor-locality:** Crossed meshing *requires* `normal_module`,
  `normal_pressure_angle`, and `helix_angle` — attributes that exist **only**
  on `HelicalGear`. Putting `shaft_angle` on `Gear.mesh_with` would create a
  method that is half-defined on its own ABC: a `SpurGear` (a `Gear`) calling
  `mesh_with(other, shaft_angle=90)` has no `helix_angle` to derive Σ from and
  no `normal_module` to validate against — the parameter would be a documented
  lie on 2 of the 3 concrete subclasses (`SpurGear`, `RackGear`). A method that
  lives where its preconditions live is an honest contract; a method whose
  parameter is meaningless for most implementers is a leaky one. The dual-lens
  rule explicitly prefers *honest contracts that onboard contributors* over
  contracts that mislead them.
- **Maintainer-locality:** No internal caller of `mesh_with` exists outside
  `base.py` (verified: `grep` finds zero callers in `vibe_cading/`/`parts/`).
  So widening the base signature buys nothing for current callers and risks
  the parallel-mesh path.
- **Backward-compat:** `Gear.mesh_with` is untouched → existing (zero) callers
  and the documented parallel behavior are byte-for-byte preserved. This is the
  decisive backward-compat argument: the safest change to a shared base method
  is no change at all.

**Rejected (a) — `shaft_angle` on base `Gear.mesh_with`:** leaky on
`SpurGear`/`RackGear` (see above), and forces base `Gear` to reach for
helix attributes it does not define (an `isinstance(self, HelicalGear)`
branch *inside the ABC* — a downward dependency from base to subclass, an
architectural smell).

**Rejected (c) — free function `crossed_mesh(g1, g2, …)`:** loses the
OO-component-API convention the project standardizes on (methods over bare
functions), and loses IDE discoverability from a `HelicalGear` instance.

### D2 — Signature & shaft-angle default → **derive by default, allow override**

```python
def crossed_mesh_with(
    self,
    other: "HelicalGear",
    *,
    shaft_angle: float | None = None,
    phase: float = 0.0,
) -> tuple[cq.Workplane, cq.Workplane]:
```

- `shaft_angle=None` (default) → **auto-derive** Σ from the two helix angles
  with hand detection:
  - **same hand** (`sign(β₁) == sign(β₂)`, treating 0 as either): `Σ = |β₁| + |β₂|`.
  - **opposite hand**: `Σ = | |β₁| − |β₂| |`.
  - This matches the standard crossed-helical relation Σ = β₁ + β₂ (same hand)
    / |β₁ − β₂| (opposite hand). Probed: `45+45 → 90`, `60+30 → 90`.
- `shaft_angle=<float>` → **user override** in degrees (e.g. force exactly 90°
  for a tidy layout even when the derived Σ is 89.7°). When supplied, it is
  used verbatim for the *pose*; the derived Σ is still computed and, if it
  disagrees with the override by more than a small tolerance (say 0.5°), a
  one-line note is added to the returned-tuple docstring contract — **no raise**
  (this is a layout tool, the user may deliberately want an idealized angle).
- `phase` keeps the existing meaning: extra CCW degrees about `other`'s *own
  axis* (post-tilt — see D4), for fine alignment. Default 0.0.

Keyword-only (`*`) for `shaft_angle`/`phase` so call sites read self-documenting
(`g1.crossed_mesh_with(g2, shaft_angle=90)`).

### D3 — Validation contract

`crossed_mesh_with` validates, in order:

1. **`other` must be helical.** Require `isinstance(other, HelicalGear)`.
   A `SpurGear`/`RackGear` has no helix and cannot form a crossed-helical
   pair → `TypeError("crossed_mesh_with requires a HelicalGear; got SpurGear. "
   "Crossed-axis meshing is defined for single-helical (screw) gears.")`.
   (Using `isinstance` rather than `hasattr` is correct here: the attribute is
   a *type* property, and `HelicalGear` is the contract that guarantees it.)
2. **Equal normal module** — `math.isclose(self.normal_module, other.normal_module)`
   else `ValueError("Crossed gears must share the same NORMAL module ...")`.
3. **Equal normal pressure angle** — `math.isclose(self.normal_pressure_angle,
   other.normal_pressure_angle)` else `ValueError`.
   - Use `math.isclose(..., rel_tol=0, abs_tol=1e-9)` to mirror the existing
     `from_iso` style and avoid float-equality brittleness (note the existing
     `center_distance_to` uses raw `!=`; we deliberately do **not** copy that —
     `isclose` is the better contract here because transverse-derived values
     can carry float noise; the equality is on *normal* inputs which are
     user-supplied and usually exact, so `abs_tol=1e-9` is safe).
4. **`double_helix` advisory (no raise).** If either gear has
   `double_helix=True`, this is an unusual crossed configuration. Do **not**
   block it (the gear has a valid axis); the method docstring states crossed
   pairs are normally same-hand single-helical. No runtime warning channel is
   introduced (the project has no logging convention for model code); the
   advisory lives in the docstring only.
5. **Hand handling** is implicit in the Σ derivation (D2), not a separate
   gate — opposite-hand pairs are *valid* crossed gears, just with a different Σ.

`SpurGear` passed as `self` is impossible — `crossed_mesh_with` only exists on
`HelicalGear`, so `spur.crossed_mesh_with(...)` raises `AttributeError`
naturally (acceptable; the method is helical-scoped by design).

### D4 — Posing geometry (concrete, verified)

`self` stays at the origin, axis +Z, bottom face at Z=0 (unchanged datum).

For `other`, in this exact order:

```python
cd = self.crossed_center_distance_to(other)   # = r1 + r2, see D5
other_solid = (
    other.solid
    # 1. Pre-spin about other's OWN axis (+Z) for phase + the half-pitch
    #    flip, BEFORE tilting, so phase is always "about other's axis".
    .rotate((0, 0, 0), (0, 0, 1), half_pitch_flip + phase)
    # 2. Tilt the shaft: rotate about +X by the shaft angle Sigma. This
    #    swings other's axis from +Z down toward -Y (CCW about +X).
    .rotate((0, 0, 0), (1, 0, 0), sigma)
    # 3. Translate along +X by the centre distance to the mesh line.
    .translate((cd, 0, 0))
)
return self.solid, other_solid
```

- **Rotation axis for the shaft angle: +X**, applied as the *second* op, about
  the origin, before the +X translation. Probed: Σ=90° puts `other`'s axis along
  −Y, bbox Y∈[−12,0], X/Z symmetric about the cd centre. The common
  perpendicular between the two skew axes is the X axis; `cd` is measured along
  it. This is the natural choice: `self` spins in the XY plane (axis +Z), the
  crossed partner spins in the XZ plane (axis ±Y after a 90° tilt) — the two
  shafts are visibly orthogonal in an iso view, which is what a crossed-helical
  layout should look like.
- **Order matters and is fixed:** axis-spin (about +Z) **then** tilt (about +X)
  **then** translate (+X). Because step 1 rotates about the same +Z the gear is
  currently centred on, and step 2 tilts about +X through the origin (still the
  gear centre at that moment), `phase` stays a clean "about other's own axis"
  rotation regardless of Σ. Translating last keeps both rotations centred on the
  gear's own axis. **Do not** translate before rotating — that would swing the
  gear around `self` instead of spinning it in place.
- **`half_pitch_flip`** — reuse the parallel rule's intent: a half-tooth-pitch
  offset (`180.0 / other.teeth`) so a tooth pocket faces `self`'s tip. The 180°
  flip from the parallel path is **dropped** for crossed (the parallel flip
  exists because parallel external gears rotate in opposite senses about
  *parallel* axes; crossed gears engage point-contact on skew axes where the
  flip is not the same geometric necessity). The Developer should treat the
  half-pitch term as a *visual* alignment nicety, not a kinematic guarantee —
  crossed-helical meshes are point-contact and this is a layout pose, not a
  conjugate-action sim. **Implementation note:** keep the half-pitch offset; the
  exact constant is a visual-tuning choice the Developer may adjust so the iso
  preview reads as "meshed," and it must be commented as visual-only.

### D5 — `center_distance_to` sibling → **new `crossed_center_distance_to`**

Do NOT relax `center_distance_to`. Add a sibling on `HelicalGear`:

```python
def crossed_center_distance_to(self, other: "HelicalGear") -> float:
    """Common-perpendicular centre distance for a crossed-helical pair.

    a = r1 + r2 (sum of the two TRANSVERSE pitch radii). Validates equal
    normal module / normal pressure angle (the crossed mesh condition),
    NOT equal transverse module (which parallel center_distance_to checks
    and which crossed gears legitimately violate).
    """
```

- Returns `self.pitch_radius + other.pitch_radius` (both are transverse on the
  base — verified `r1=40.0, r2=34.64 → 74.64` for the `60/30` pair).
- Runs the same normal-module / normal-PA validation as D3 (factor the check
  into one private helper `_assert_crossed_meshable(self, other)` called by both
  `crossed_center_distance_to` and `crossed_mesh_with`, so the contract is
  defined once — DRY, single source of truth for the mesh condition).

**Rationale for a sibling over relaxing the base:** `center_distance_to` is an
ABC method with a precise documented contract (equal module + equal PA →
parallel operating distance). Crossed gears have a *different* meshability
condition and a *different* distance semantics (common-perpendicular vs.
coplanar centre-to-centre). Overloading one method to mean both would force a
runtime mode flag and blur two genuinely different engineering relations. A
named sibling keeps each contract honest and self-documenting — the same
repair-don't-distort principle behind D1.

### D6 — Exports / discoverability

No new export needed — `crossed_mesh_with` / `crossed_center_distance_to` are
methods on the already-exported `HelicalGear`. Optionally extend
`HelicalGear.demo()` to add a crossed-pair tuple (a single + a crossed pose
side by side) so `view.py ... HelicalGear --demo` shows it. **Defer** the demo
extension to the Developer's discretion (it is a `to_cutter`/`solid` overlay-
free multi-instance case — exactly when `demo()` earns its keep), but it is not
load-bearing for the contract.

## Data & Interface Contracts (summary table)

| Symbol | Home | Signature | Returns / Raises |
|---|---|---|---|
| `crossed_mesh_with` | `HelicalGear` | `(self, other: HelicalGear, *, shaft_angle: float \| None = None, phase: float = 0.0)` | `(self_solid, other_solid)` posed. Raises `TypeError` (non-helical `other`), `ValueError` (normal-module / normal-PA mismatch). |
| `crossed_center_distance_to` | `HelicalGear` | `(self, other: HelicalGear) -> float` | `r1 + r2` (transverse). Raises `ValueError` on mesh-condition mismatch. |
| `_assert_crossed_meshable` | `HelicalGear` (private) | `(self, other: HelicalGear) -> None` | validates type + normal module + normal PA. |
| `_derived_shaft_angle` | `HelicalGear` (private, optional) | `(self, other) -> float` | Σ from β₁,β₂ with hand detection. |
| `Gear.mesh_with` | `Gear` | **UNCHANGED** | parallel pose, byte-for-byte preserved. |
| `Gear.center_distance_to` | `Gear` | **UNCHANGED** | parallel operating distance, preserved. |

Datum: `self` axis = +Z, bottom at Z=0 (existing `Gear` convention, unchanged).

## Implementation Plan (phases for the Developer)

1. **P1 — private mesh-condition helper.** Add `_assert_crossed_meshable` and
   (optionally) `_derived_shaft_angle` to `HelicalGear`. Use
   `math.isclose(rel_tol=0, abs_tol=1e-9)`.
2. **P2 — `crossed_center_distance_to`.** Calls the helper, returns
   `self.pitch_radius + other.pitch_radius`. Docstring states "transverse" and
   "common-perpendicular."
3. **P3 — `crossed_mesh_with`.** Derive/override Σ, compute `cd`, apply the
   D4 transform (spin-about-+Z → tilt-about-+X → translate-+X). Comment the
   half-pitch term as *visual-only*. Return the tuple.
4. **P4 — validation evidence.** Run the Tests table below; assert single
   solids; capture an iso preview for the post-impl review.
5. **P5 — (optional) `demo()` extension** for `view.py --demo`.

No `build.toml` change (no new buildable part). No new constants. No tolerance
profile plumbing (posing has no clearance). AGPLv3 header already present in the
edited files.

## Tests

| # | Assertion | Method |
|---|---|---|
| T1 | `crossed_mesh_with` returns two single solids: `len(s.solids().vals())==1` for both. | tmp probe |
| T2 | Σ=90° sanity (β₁=β₂=45°): `other` bbox is symmetric in X & Z about `cd`, and Y∈[−fw,0] (axis swung to −Y). Verified in blueprint probe; re-assert in impl. | tmp probe |
| T3 | Unequal helix (β₁=60°, β₂=30°, same normal module): `crossed_center_distance_to` returns `r1+r2` (≈74.64) and does **NOT** raise; parallel `center_distance_to` on the same pair **DOES** raise. | tmp probe |
| T4 | Hand detection: same-hand `45,45 → Σ=90`; opposite-hand `45,−45 → Σ=0`; opposite-hand `60,−30 → Σ=30`. | unit probe |
| T5 | `shaft_angle=90` override is honored when derived Σ≠90 (pose uses 90). | tmp probe |
| T6 | Non-helical `other` (`SpurGear`) → `TypeError`; `spur.crossed_mesh_with` → `AttributeError` (method absent). | tmp probe |
| T7 | Mismatched normal module (m_n=2 vs 3) → `ValueError`; mismatched normal PA (20° vs 25°) → `ValueError`. | tmp probe |
| T8 | **Backward-compat regression:** existing `mesh_with` parallel pose output (bbox of both solids) unchanged vs. pre-change. | tmp probe |
| T9 | Visual contract: iso_ne SVG of a crossed pair reads as two orthogonal shafts (post-impl review eyeball; not byte-pinned — no `cq.text`). | `preview.py` / probe |

These are fast, targeted probes (per Fast-Feedback Gate). **No full
`build.py` / `boolean_diff` row** is required: this task ships **no new
buildable model class** and **no `build.toml`-registered geometry change** —
it adds two posing methods to an existing class. The Representative-Scale rule
triggers on new build-registered geometry, which this is not. (If the Developer
adds a `demo()` tuple, that is exercised by `view.py --demo`, still not a build
path.)

## Visual Contract

> **Scope note (added post-review, F2):** the PR that ships this design
> (#75) also bundles the earlier `HelicalGear.double_helix` herringbone flag
> from the same session's gallery work. That flag **does** change single-gear
> geometry. The statement below applies strictly to the *crossed-mesh* feature
> this brief specifies; `double_helix` is out of this brief's original scope
> (see CHANGELOG 0.1.3). No gear class is registered in `visual_contracts.toml`,
> so neither feature trips the freshness gate.

The **crossed-mesh** feature changes **no single-gear visible geometry** (the
`HelicalGear.solid` is byte-identical for a posed pair). It adds a *posing
relationship*. Per the visual-contract
scope carve-outs (refactors / additive-only / no change to a single part's
visual outcome), a registered `visual_contracts/` SVG is **not required**. The
post-impl review (T9) should still eyeball an iso preview of a posed crossed
pair to confirm the two shafts are orthogonal and the gears appear engaged —
but it is review evidence, not a tracked, freshness-checked contract (and must
not be, since a two-body pose has no stable single-class registration row).

## Known Risks & Mitigations

- **R1 — half-pitch/flip visual tuning.** Crossed meshes are point-contact;
  the half-pitch offset is cosmetic. *Mitigation:* comment it as visual-only;
  Developer may adjust the constant so the iso preview reads as meshed. Not a
  correctness gate.
- **R2 — float equality on normal PA.** *Mitigation:* `math.isclose` with
  `abs_tol=1e-9` (D3), not raw `!=`.
- **R3 — `double_helix` crossed combination.** Geometrically valid but unusual.
  *Mitigation:* docstring advisory, no hard block (D3.4).
- **R4 — someone expects `crossed_mesh_with` on `SpurGear`.** *Mitigation:* it
  is intentionally helical-scoped; `AttributeError` is the honest signal, and
  the `TypeError` message on a helical `self` + spur `other` explains why.

## Out of Scope

- Motion/kinematic simulation (this is layout posing only).
- Worm-gear (worm + worm-wheel) meshing — a distinct geometry, not just a pose.
- Sliding-velocity / efficiency calc for crossed-helical contact.
- Any change to single-gear geometry, `build.toml`, constants, or tolerance
  profiles.
- A tracked visual-contract SVG (see Visual Contract section).
