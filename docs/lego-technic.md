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
| Technic axle hole (cross)     | 4.80 mm | Tip-to-tip of the + cross section         |
| Cross axle flat-to-flat       | 1.83 mm | The flat sides of the + cross             |
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

Lift arms (also called beams) are flat with round ends. They lie flat and have
holes on the 8 mm stud grid.

| Property                   | Value    | Notes                                        |
|----------------------------|----------|----------------------------------------------|
| Beam thickness             | 7.2 mm   | Height of the beam (tall axis)               |
| Beam width                 | 4.0 mm   | Narrow axis (depth when lying flat)          |
| Hole diameter              | 4.8 mm   | Technic pin/axle hole                        |
| Hole center spacing        | 8.0 mm   | Stud pitch                                   |
| End radius                 | 4.0 mm   | Rounded ends = half of beam thickness        |
| 1M beam total length       | 8.0 mm   | One-hole beam (measured center-to-edge × 2)  |
| nM beam total length       | (n-1)×8 + 8 mm | e.g. 5M = 40 mm, 9M = 72 mm          |
| Printed hole clearance     | +0.1 mm  | Use 4.9 mm holes for a snug printed fit      |

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
- Beam ends are typically modelled as a semicircle of radius `beam_thickness / 2`
  centred on the outermost hole.
- When modelling friction pin holes, use **4.7 mm** diameter; for frictionless
  use **4.9 mm**. Adjust by ±0.1 mm per printer calibration.
- When exporting STEP files for Lego-compatible parts, **do not scale** — CadQuery
  works in mm natively.