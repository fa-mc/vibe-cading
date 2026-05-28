# Lego Technic Dimensions Reference

This document provides accurate Lego Technic part dimensions for use when
designing compatible or interfacing CadQuery models. All measurements are in
millimeters (mm). Where tolerances are noted, they reflect typical FDM 3D
printing clearances for functional fits.

---

## Grid & Stud Spacing

| Property              | Value   | Notes                              |
|-----------------------|---------|------------------------------------|
| Stud pitch (X/Y)      | 8.0 mm  | Center-to-center in any direction  |
| Plate height          | 3.2 mm  | 1 plate = 3.2 mm vertically        |
| Brick height          | 9.6 mm  | 1 brick = 3 plates = 9.6 mm        |
| Stud diameter         | 4.8 mm  | Top of stud                        |
| Stud height           | 1.8 mm  | Height above top face of brick     |

---

## Technic Holes & Axle Holes

| Property                      | Value   | Notes                                     |
|-------------------------------|---------|-------------------------------------------|
| Technic pin hole diameter     | 4.8 mm  | Nominal; use 4.85 mm for printed parts    |
| Technic axle hole (cross)     | 4.80 mm | Nominal; defaults to 4.82 mm for FDM |
| Cross axle flat-to-flat       | 1.83 mm | Nominal; defaults to 1.64 mm for FDM |
| Technic hole center spacing   | 8.0 mm  | Same as stud pitch                        |
| Hole center from part edge    | 4.0 mm  | Half the stud pitch                       |

---

## Axles

| Property                  | Value   | Notes                                              |
|---------------------------|---------|----------------------------------------------------|
| Axle cross tip-to-tip     | 4.75 mm | Outer diameter of the + profile                    |
| Axle cross flat-to-flat   | 1.78 mm | Width across flats of the + profile                |
| Axle arm protrusion       | 1.50 mm | How far each arm extends past the flat face        |
| Axle length per stud unit | 8.0 mm  | e.g. a 3-stud axle is 24 mm long                   |
| Printed axle clearance    | 0 mm    | No clearance; size axle holes to exact tip-to-tip  |

---

## Technic Pins

Technic pins come in two main variants: **friction pins** (blue/black) and
**frictionless pins** (grey/tan). Both share the same outer diameter and hole
spacing but differ in surface detail and intended use.

### Common Pin Geometry

| Property                        | Value    | Notes                                            |
|---------------------------------|----------|--------------------------------------------------|
| Pin body diameter               | 4.8 mm   | Nominal; fits standard 4.8 mm Technic holes      |
| Pin total length (full pin)     | 16.0 mm  | Spans two 8 mm holes (one stud pitch each side)  |
| Pin total length (half pin / 1L)| 8.0 mm   | One stud pitch, one insertion side only          |
| Collar diameter                 | 6.4 mm   | Centre collar flanges between the two arms        |
| Collar total thickness          | 1.8 mm   | Combined width of both collar flanges            |
| Each collar flange thickness    | 0.9 mm   | Per flange, one either side of centre            |
| Collar flange outer diameter    | 6.4 mm   | Prevents pin sliding through hole                |
| Insertion depth per side        | 7.1 mm   | Body length per side (16 mm total − 1.8 mm collar)|
| Pin hole (axle socket) diameter | 3.2 mm   | Round hole through pin centre for axle stacking  |

### Friction Pins (Blue / Black)

Friction pins have raised longitudinal ribs on the body surface. These ribs
create resistance inside Technic holes so beams and bricks do not rotate freely.

| Property                  | Value    | Notes                                              |
|---------------------------|----------|----------------------------------------------------|
| Body diameter (nominal)   | 4.8 mm   | Same as frictionless                               |
| Friction rib height       | 0.3 mm   | Ribs protrude radially, effective Ø ≈ 5.0–5.1 mm  |
| Number of ribs            | 3        | Equally spaced at 120° around body circumference  |
| Rib width                 | ~0.6 mm  | Approximate tangential width of each rib           |
| Rib length                | ~6.0 mm  | Runs axially along insertion section               |
| Intended fit              | Friction | Beam/hole does NOT rotate freely on pin            |

**Use case:** Structural connections where joints should hold their position
(e.g. fixed angles in frames, non-rotating linkages).

### Frictionless Pins (Light Grey / Tan)

Frictionless pins have a smooth body. Beams rotate freely around them.
They also have a small groove near the collar for a click-fit retention feature.

| Property                    | Value    | Notes                                            |
|-----------------------------|----------|--------------------------------------------------|
| Body diameter (nominal)     | 4.8 mm   | Smooth surface                                   |
| Friction ribs               | None     | Smooth cylinder                                  |
| Retention groove depth      | ~0.3 mm  | Circumferential groove near collar for snap-fit  |
| Retention groove width      | ~0.6 mm  | Axial width of groove                            |
| Retention groove position   | ~1.0 mm  | Distance from collar face to groove centre       |
| Intended fit                | Rotating | Beam/hole rotates freely on pin                  |

**Use case:** Pivot points, rotating joints, hinges, wheels, and any connection
that needs free rotation (e.g. suspension arms, steering linkages).

### Pin Variants Summary

| Variant              | LEGO colour  | Ribs | Rotation | Common Use                  |
|----------------------|--------------|------|----------|-----------------------------|
| Full pin (2L)        | Blue         | Yes  | No       | Fixed structural joints     |
| Full pin (2L)        | Light grey   | No   | Yes      | Pivots, rotating joints     |
| Half pin (1L)        | Blue         | Yes  | No       | Plate/beam connections      |
| Pin with axle (3L)   | Blue         | Yes  | No       | Combined pin+axle           |
| Pin with stud        | Various      | Yes  | No       | Stud-compatible connections |
| Connector peg / bush | Light grey   | No   | Yes      | Axle end stops, spacers     |

### Pin Hole Tolerances for 3D Printing

| Fit Type        | Hole Diameter | Notes                                        |
|-----------------|---------------|----------------------------------------------|
| Friction fit    | 4.7 mm        | Pin will not rotate; mimics LEGO friction pin|
| Standard fit    | 4.8 mm        | Nominal; may still have some friction when printed |
| Free rotation   | 4.9–5.0 mm    | Pin rotates freely; mimics frictionless pin  |
| Loose/clearance | 5.1 mm        | Loose movement, useful for alignment only    |

> **Tip:** For printed parts that receive real LEGO pins, use **4.9 mm** holes
> for frictionless behaviour and **4.7 mm** for friction behaviour. Actual values
> may need tuning ±0.1 mm depending on your printer and filament.

---

## Technic Lift Arms (Beams)

Lift arms (also called beams) have round ends and holes on the 8 mm stud
grid. Thick liftarms have a **square cross-section** (7.8 × 7.8 mm); the
beam is as deep (along its short transverse axis) as it is tall.

| Property                   | Value    | Notes                                        |
|----------------------------|----------|----------------------------------------------|
| Beam thickness             | 7.8 mm   | Height of the beam (Cailliau measured 7.4–7.8 mm; theoretical nominal 8.0 mm less ~0.2 mm relief) |
| Beam width                 | 7.8 mm   | Short transverse axis; thick liftarms are square in cross-section (7.8 × 7.8 mm) per Cailliau |
| Hole diameter              | 4.8 mm   | Technic pin/axle hole                        |
| Pin-hole counterbore Ø     | 6.0 mm   | Recessed ring around each pin hole (real-liftarm-faithful per Cailliau) |
| Pin-hole counterbore depth | 0.8 mm   | Axial depth of the counterbore (real-liftarm-faithful per Cailliau)     |
| Hole center spacing        | 8.0 mm   | Stud pitch                                   |
| End radius                 | 3.9 mm   | Rounded ends = half of beam width (7.8 / 2); per Cailliau |
| 1M beam total length       | 8.0 mm   | One-hole beam (measured center-to-edge × 2)  |
| nM beam total length       | (n-1)×8 + 8 mm | e.g. 5M = 40 mm, 9M = 72 mm          |
| Printed hole clearance     | `2 × slip.radial` mm | Profile-driven via `TechnicPinHole(fit="slip")`; calibrate `slip.radial` in `print_profiles_user.json` per `docs/print-tolerances.md` §4 |

Numeric values above (beam thickness, beam width, end radius, counterbore
diameter, counterbore depth) are sourced from
[Cailliau — Lego Dimensions](https://www.cailliau.org/Alphabetical/L/Lego/Dimensions/More%20Dimensions/BBEditPreviewTemp.html),
the primary external authority on measured real-liftarm geometry. The audit
that produced these values was scoped to **thick liftarms only**; thin
liftarms (if discussed elsewhere) use a different cross-section.

**Counterbore — code defaults vs. real-liftarm values.** Cailliau gives a
real-liftarm counterbore tolerance range of **6.0–6.2 mm diameter** and
**0.8–1.0 mm depth**. This document records the real-liftarm-faithful values
(6.0 × 0.8 mm) as the reference. The project's code defaults in
[`TechnicPinHole.standard()`](../vibe_cading/lego/cutters/technic_pin_hole.py)
(see lines 22–24) use **6.2 × 1.0 mm**, the **loose / FDM-friendly edge**
of the Cailliau range. The code defaults are intentional, not a doc/code
drift: FDM-printed parts benefit from the looser counterbore so a real
LEGO pin's collar seats reliably despite layer-line variation.

Only the **bore** is now profile-driven (`PIN_HOLE_DIAMETER + 2 *
profile.<fit>.radial`, default `fit="slip"`).  The counterbore dimensions
stay at the hardcoded real-liftarm spec — the LEGO pin flange seats once
in the counterbore (no sliding interface), and the 6.2 × 1.0 mm value is
already the FDM-friendly edge of the Cailliau range, so widening it
further would risk flange-seat loss.

**Hole-axis convention.** Liftarm pin holes pass perpendicular to beam
length. In this project's convention:

- **Beam length runs along X** (extent = N × 8 mm for an N-stud beam).
- For **thick (square 7.8 × 7.8) liftarms** (this v1's scope), pin holes
  pass **parallel to Z** — i.e. **vertically, when the beam is laid flat
  on a table**, entering and exiting through the **top face (Z =
  BEAM_THICKNESS) and the bottom face (Z = 0)**. Both faces are pierced;
  both carry the symmetric counterbore from `TechnicPinHole.standard()`.
- For **thin liftarms** (separate part class, **not modelled in v1**),
  holes pass through the narrow transverse dimension — also
  conventionally aligned with **Z when laid flat**, so the same
  "holes-parallel-to-Z when flat" rule applies.

A reader designing an adapter that bolts a pin into a liftarm hole should
expect to insert the pin along **Z** (vertically into a beam lying flat),
not along Y or X.

> *Audit note (2026-05-17).* An earlier 2026-05-16 edit of this paragraph
> claimed pin holes were "parallel to Y" on the grounds that they pass
> through the beam's "short transverse axis". For thin liftarms this is
> well-defined (narrow ≠ wide). For **thick** liftarms with a square
> 7.8 × 7.8 cross-section the two transverse axes (Y and Z) are
> geometrically equivalent, and the "narrow axis" framing does not pin
> a direction. The dual-axis equivalence held the prior misclaim for a
> day; user Phase-D feedback against the OCP CAD viewer demo caught it
> — a real Lego liftarm laid flat on a table has its wide face up and
> its holes vertical. This paragraph now follows the
> orientation-when-laid-flat convention.

### Lift Arm Length Formula

$$L = (n - 1) \times 8 + 8 = n \times 8 \text{ mm}$$

Where $n$ is the number of holes.

---

## Technic Liftarm (L-Shape / Bent Beams)

Common bent beam angles are **90°** and **53.13°** (3–4–5 triangle geometry).

| Property         | Value      | Notes                               |
|------------------|------------|-------------------------------------|
| Standard bend    | 90°        | Most common                         |
| 3-4-5 bend angle | 53.13°     | Based on Pythagorean 3-4-5 triangle |
| Short arm (3M)   | 24 mm      | Center-to-bend center               |
| Long arm (5M)    | 40 mm      | Center-to-bend center               |

---

## Gears

| Gear Type          | Module | Tooth Count | Outer Diameter | Notes                 |
|--------------------|--------|-------------|----------------|-----------------------|
| Small bevel gear   | 1.0    | 12          | ~14 mm         |                       |
| Large bevel gear   | 1.0    | 20          | ~22 mm         |                       |
| Spur gear (small)  | 1.0    | 8           | ~10 mm         |                       |
| Spur gear (24t)    | 1.0    | 24          | ~26 mm         |                       |
| Worm gear          | 1.0    | 1           | ~9.6 mm dia    | 1 module pitch        |

---

## Common Tolerances for 3D Printed Parts

| Fit Type        | Adjustment | Use Case                              |
|-----------------|------------|---------------------------------------|
| Sliding fit     | +0.2 mm    | Axles through holes, pins in holes    |
| Press fit       | −0.1 mm    | Bushings, press-in inserts            |
| Snug fit        | +0.1 mm    | Repeated-use connections              |
| Clearance fit   | +0.4 mm    | Non-functional, loose movement        |

---

## Notes for CadQuery Modelling

- All hole centers should align to multiples of **8.0 mm** on the XY grid.
- Use `.polygon(4, axle_tip_to_tip).cutBlind(depth)` for cross-axle holes,
  rotated 45° — or model the actual + cross profile for accuracy.
- Beam ends are typically modelled as a semicircle of radius `beam_width / 2`
  (≈ 3.9 mm for thick liftarms) centred on the outermost hole — thick liftarms
  have a square cross-section, so half-thickness and half-width coincide.
- When modelling friction pin holes, use **4.7 mm** diameter; for frictionless
  use **4.9 mm**. Adjust by ±0.1 mm per printer calibration.
- When exporting STEP files for Lego-compatible parts, **do not scale** — CadQuery
  works in mm natively.
---

## Tuning Tolerances

Because different 3D printers and materials (FDM vs Resin) shrink differently,
the default clearance might result in axle holes that are too tight or too
loose on your specific machine.

The axle-hole *nominal* dimensions in `vibe_cading/lego/constants.py`
(`AXLE_HOLE_TIP_TO_TIP = 4.80`, `AXLE_HOLE_ARM_WIDTH = 1.83`) are fixed
real-Lego geometry — **do not edit them to fix a fit.** Printer clearance is
applied separately, from your active `ToleranceProfile`: `TechnicAxleHole`
sizes its cutter `nominal + 2 × slip.radial`. Calibrate the *profile*, not the
constant:

1. Print the `AxleHoleGauge` model (`vibe_cading/lego/axle_hole_gauge.py`): a
   flat block of swept round through-holes, each engraved with its diameter.
   Print it flat (hole axes vertical, parallel to build-Z) with the same
   slicer settings used for real parts.
2. Insert a real Lego Technic axle into each hole. The smallest hole the axle
   slips into — judged by axial slide feel, not rotational wobble — gives the
   effective fitting modelled diameter `D` for your printer and material.
3. Convert that diameter to a profile clearance with:

       slip.radial = (D − 4.80) / 2

   (4.80 is `AXLE_HOLE_TIP_TO_TIP`; `radial` is half-extra-material on
   diameter.)
4. Write the result into the untracked `print_profiles_user.json` (it
   field-level deep-merges over `print_profiles.json`), e.g. for a fitting
   `D = 5.00`:

       { "fdm_standard": { "slip": { "radial": 0.10 } } }

   You only need to specify the single overridden leaf — `axial` and `slot`
   inherit from the shipped grade. These local overrides stay out of git,
   and every slip-fit consumer picks them up automatically.

### The `slot` allowance — narrow `+` cross slots

`slip.radial` calibrates the **round** axle-hole envelope. The narrow `+`
*cross* axle-hole slot (`TechnicAxleHole.ARM_WIDTH`) has a physically
distinct clearance need: a narrow slot prints tighter on FDM than the round
envelope of the same nominal. `FitGrade` therefore carries a third optional
allowance, `slot`, applied **only** to the cross-arm slot width on top of
`radial`:

       ARM_WIDTH  = AXLE_HOLE_ARM_WIDTH + 2 × slip.radial + 2 × slip.slot
       TIP_TO_TIP = AXLE_HOLE_TIP_TO_TIP + 2 × slip.radial           (unchanged)

The shipped `fdm_standard` profile already ships a conservative
`slip.slot = 0.10` — a geometric floor that puts the cross-arm slot in the
tight half of the proven working band. The arm fit is **forgiving** (~0.20 mm
acceptable band), so most users **leave `slot` at its shipped default and
calibrate only `slip.radial`**. Override `slot` in `print_profiles_user.json`
only on an unusual printer whose narrow-slot tightening differs markedly.

> **Legacy-flat divergence.** A `print_profiles_user.json` still in the
> legacy *flat* schema (`slip_fit` / `z_clearance` / …) has no `slot` concept.
> It migrates to `slot = 0.0`, so its cross arms keep the pre-`slot` width
> (`AXLE_HOLE_ARM_WIDTH + 2 × slip.radial`) — narrower than the shipped
> nested `fdm_standard`. This is intentional (a stale config gets stable
> legacy behaviour, not a silent geometry change), but if you maintain a
> legacy-flat user file and want the cross-arm widening, migrate it to the
> nested schema and add `"slot": 0.10` to the `slip` grade.

### Concave-corner blowout — verified adequate

The `+` cross hole's four inner concave corners are where FDM extrusion
over-deposits ("corner blowout"), which can choke the slot. The
`AxleCrossHoleGauge` calibration tool isolates the arm-slot width from this
effect by relieving the corners with a **dog-bone** pocket; production
`TechnicAxleHole` instead keeps a plain `concave_radius` fillet (default
0.3 mm). A confirmation print (2026-05-22, `bambu_p1s` + PLA) of production
cross holes at the calibrated `slot` found 2 of 3 holes fitting well and 1
slightly tight, **none binding** — the 0.6 mm fillet was adequate once the
arm slot was correctly widened. No dedicated corner-relief parameter is needed
at the calibrated arm width; revisit only if a printer with more aggressive
blowout shows the fillet binding a real axle.

Follow-up 2026-05-28 on the same printer at a re-calibrated `slip.slot`
(0.1125): a 2-variant in-script sweep (`tmp/print_concave_sweep_2.py`)
showed 0.30 prints clean while 0.35 does not, so the shipped default is
now 0.3 mm. The original 0.6 mm value was acceptable at the prior
calibration point but consumed more slot wall than needed; 0.3 mm is the
best-current-evidence point at the calibrated slot.
