# Reference digest — Perpendicular Holes Liftarm Generator

<!-- Orchestrator-authored digest of a user-attached image (2026-06-26). The image
cannot be passed to spawned subagents, so this file is the durable textual
reference per INSTRUCTIONS.md "Designer pre-digests reference material". The
Designer turns this into formal requirements; the human confirms the geometry
read at the Step-2 requirements gate. Motivated by LEGO part 6435016 / design
2391 family ("Liftarm Thick with Perpendicular Holes") but explicitly NOT a
byte-for-byte reproduction — the user's directive is "generalize the design". -->

## Source

User-attached image titled **"Perpendicular Holes Liftarm Generator"** (Autodesk
Fusion 360 badge, "LEGO Technic Compatible"). It is a **parameter-legend diagram**:
two orthographic views of one liftarm with the generator's input parameters called
out by dimension arrows. It is a *concept/parameter* reference, not a dimensioned
manufacturing drawing — no numeric values are printed on it.

## What the two views show (geometry read)

The diagram draws **one** liftarm in two mutually-perpendicular orthographic views:

- **Upper view** — looking down the **main-hole axis**. Full round holes = main
  pin holes whose bore axis points at the viewer (model **+Z**, through the
  flat faces). The "H"/bracket marks between them = perpendicular holes seen
  **edge-on** (you see their two counterbore-collar walls, not the bore).
- **Lower view** — the part rotated 90° about its long axis, looking down the
  **perpendicular-hole axis** (model **±Y**, through the side faces). Now the
  round holes are the perpendicular ones (bore points at viewer) and the
  brackets are the main holes seen edge-on. The stadium end-caps are visible.

**Key read:** a hole that is *round* in one view is a *bracket* in the other.
That is only physically consistent if **each hole position bores along a single
axis**, and **adjacent positions alternate axis**. The drawn example has 5 holes
in the order **perp · main · perp · main · perp** (the two end holes are
perpendicular). Because main (Z) and perpendicular (Y) bores sit at *different*
X positions, **they never intersect** — no cross-drilling in the drawn example.

> The Designer must decide how far to generalize the per-position axis choice
> (alternating default vs. an explicit per-position axis list vs. allowing both
> axes at one position = cross-drilled). The image only fixes the *example*; the
> user's directive is "flexible and principled, generalize the design."

## Labelled parameters (generator inputs) → repo mapping

| Diagram label | Meaning | Existing repo constant / source (to confirm) |
|---|---|---|
| **number of holes X** | count of hole positions along the length | new param (cf. `LegoTechnicBeam.length_in_studs`) |
| **Technic Unit** | centre-to-centre pitch between adjacent holes | `STUD_PITCH = 8.0` |
| **Interior Diameter** | the through-bore Ø (the white circle) | `PIN_HOLE_DIAMETER = 4.8` (printed Ø comes from the active `ToleranceProfile`, not a literal) |
| **Pin Hole Diameter** | the wider counterbore / collar mouth Ø (bracket outer width) | `TECHNIC_PIN_CB_DIAMETER = 6.2` |
| **Depth** | beam dimension along **Y** (width) | `BEAM_WIDTH = 7.8` |
| **Height** | beam dimension along **Z** (thickness) | `BEAM_THICKNESS = 7.8` |
| **Pin Hole Offset** | offset of the hole axis from the reference face; drawn as the small vertical gap from the top face down to the hole-row centreline | default = centred = `Depth/2 = 3.9` (square section) — confirm at gate |

The two-diameter callout (**Pin Hole Diameter** outer vs **Interior Diameter**
bore) corresponds to the Technic pin hole's counterbored mouth (6.2) vs its
narrow waist (4.8) — already modelled by `TechnicPinHole.standard()`
(`vibe_cading/lego/cutters/technic_pin_hole.py`), which carries the symmetric
two-end counterbore.

## Open geometry questions for the Designer to resolve (and the human to confirm)

1. **Per-position axis model** — alternating default? explicit list? allow both
   axes (cross-drill) at one position? This is the core generalization decision.
2. **Pin Hole Offset semantics** — is it the perpendicular-hole axis offset from a
   face (default centred, `Depth/2`), or the end-to-first-hole offset? The repo's
   existing beam fixes the first hole centre at `X = STUD_PITCH/2 = 4.0`.
3. **Pin Hole Diameter vs Interior Diameter** label-to-constant mapping above —
   confirm 6.2 (counterbore mouth) vs 4.8 (bore), or whether the generator means
   something else by "Pin Hole Diameter".
4. **Counterbores on the perpendicular holes** — the brackets in the image read as
   collared/counterbored mouths, matching `TechnicPinHole`'s symmetric two-end
   counterbore. Confirm perpendicular holes reuse the same cutter (rotated 90°).

## Reuse anchors (existing code)

- `vibe_cading/lego/technic_beam.py` — `LegoTechnicBeam`: stadium body via 2D
  sketch → +Z extrude; main holes cut with a single `TechnicPinHole.standard()`
  cutter translated per position; lead-in chamfer via `_HoleMouthSelector`;
  single-solid topological guard. The perpendicular-hole feature is *additive*
  to exactly this body — same square 7.8×7.8 section, same cutter rotated 90°.
- `vibe_cading/lego/cutters/technic_pin_hole.py` — `TechnicPinHole`.
- `vibe_cading/lego/constants.py` — all dimensions above.
