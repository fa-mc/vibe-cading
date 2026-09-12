# LDraw geometry extraction — LEGO Powered Up Technic Hub (88012) bottom housing `25560`

Companion to [`2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md`](2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md)
(lid `24853`, tray `24849`). Same conventions, same provenance discipline, same extraction method.

**Provenance note.** This is a tracked design-record artifact (moved from git-ignored `tmp/` per
the phase-4 TL review, `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md` §TL
Review — CURRENT, finding B2). It contains our own measurements and prose analysis of the cited
LDraw parts — dimensions read as facts — not converted geometry or `.dat` file content. Source
part data: LDraw official parts library, author Philippe Hurbain [Philo], CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/).

Source: LDraw official library, `tmp/ldraw/full/ldraw/`.
Part chain: `parts/25560.dat` → `parts/24851.dat` → `parts/s/24851s01.dat` (×2, X-mirrored)
→ `parts/s/24851s02.dat` (×4 total). Author Philippe Hurbain [Philo], CC BY 4.0.

Extraction method: recursive type-1 reference resolution with matrix composition
(`tmp/ldraw/analyze.py`, `tmp/ldraw/housing_probe.py`, `tmp/ldraw/region_dump.py`) →
triangle soup → axis-aligned face maps, planar cross-sections, box-region triangle dumps,
**plus direct reading of the `.dat` primitive references**. Where the two disagreed, the
`.dat` source won (per the prior extraction's conclusion). A ray-cast inside/outside probe
(`tmp/ldraw/inside_test.py`) was written and then **discarded as unreliable** — LDraw meshes
are rendering surfaces, not watertight solids, so parity counting misfires.

---

## 0. Coordinate frames and how to read the tables

| | |
|---|---|
| Unit | 1 LDU = 0.4 mm; stud pitch 20 LDU = 8.0 mm; brick height 24 LDU = 9.6 mm |
| LDraw vertical axis | **Y**, and **−Y is up** |
| Hub assembly | `parts/22127.dat` = `25561c01` (top, identity) + `24849` + `24853` both at `(0, 50, 0)` identity |
| Hub envelope | 72.0 × 71.2 × 40.0 mm; hub Y spans −50…+50 LDU ⇒ **hub Y = +50 LDU is the bottom face (0 mm)** |
| `25560` envelope | **72.000 × 71.200 × 33.800 mm** (X × Z × height); X ±36.0, Z ±35.6, Y −34.5…+50 LDU |

**Height convention used throughout this document.** Every "height" figure is
**mm above the hub's bottom face**:

```
height_mm = (50 − ldraw_Y) × 0.4          ldraw_Y = 50 − height_mm / 0.4
```

so LDraw `y = +50 → 0.0 mm`, `y = 0 → 20.0 mm`, `y = −34.5 → 33.8 mm`.
X and Z are quoted directly as `ldraw × 0.4` mm.

**Recommended CadQuery mapping** (same handedness/datum as the lid extraction — lid outer
face on the bed, everything extrudes into +Z):

```
cq_x =  ldraw_X * 0.4      cq_y = ldraw_Z * 0.4      cq_z = (50 - ldraw_Y) * 0.4
```

**Envelope cross-check.** `25560` and `24851` measure *identically* (72.0 × 71.2 × 33.8).
`25560.dat` is 3 geometry lines: `24851.dat` at identity plus **two extra `s/24851s02.dat`
connector ribs at `z = −20`** (identity + X-mirror). The 4-port Control+ hub bottom is
therefore the 2-port battery-box bottom plus one more pair of port ribs. Everything else —
including **all twelve pin holes and all four arms** — is inherited unchanged from `24851`.

---

## ⚠ 0.1 Trustworthiness — read before using any number below

**There is no author caveat.** `grep '^0 //'` over `25560.dat`, `24851.dat`,
`s/24851s01.dat`, `s/24851s02.dat`, `25561.dat`, `s/25561s01.dat` returns **nothing** — none
of the housing files carries the `0 // Internal structure is simplified` comment that scopes
the whole of the tray `24849.dat`. That is a meaningful positive signal, but it is **not** a
warranty. Two limits apply:

1. **LDraw models visible surfaces.** Where an inner face is *not* visible from outside
   through an opening, it is simply absent. Concretely: the top deck at 29.6 mm has a
   21 914 LDU² surface at `y = −24` and **no matching underside face anywhere** — so the deck's
   thickness is *not modelled*, and no wall thickness can be read for it. The side walls *do*
   have both faces (they are visible through the bottom opening and the side windows), so
   their 0.8 mm is real data.
2. **Technic-pin-hole geometry is on-grid-idealized, not caliper-traced.** Every hole is built
   from the stock `connhole.dat` / `connhol3.dat` / `peghole.dat` primitives, whose radii are
   whole LDU (6, 8, 9). The arms measure exactly 7.200 × 8.000 × 23.200 mm — **byte-identical
   to LDraw's own 3-hole liftarm `32523.dat`** (verified: `measure.py 32523.dat` →
   `X 7.200 / Y 8.000 / Z 23.200`). This is LDraw's idealisation of the beam family, not a
   measurement of *this* mould.

**Trustworthy (traced / structurally forced):** overall envelope, hole centre coordinates and
pitch, hole axis directions, arm vertical extent, wall thicknesses where both faces exist,
lid latch-slot and tongue-slot positions, side-window extents, top-shell landing planes.

**Idealized (grid-snapped, treat as nominal not measured):** all pin-hole diameters and
counterbore depths, the 7.2 / 8.0 arm section, the 0.8 / 1.2 mm wall values.

**Absent:** see §8. Notably the latch bite feature (§5.2) and every internal cavity surface
that is not visible from outside.

---

## 1. THE PRIORITY QUESTION — the pin-hole map, verified

### 1.1 Hole census — 12 holes, and exactly 12

`housing_probe.py prims 25560.dat conn` lists **8 × `connhole.dat` + 4 × `connhol3.dat`**.
The `peghole.dat` instance count is **20** = 8 × 2 (both ends of each through-hole) + 4 × 1
(single end of each one-sided hole) — an exact accounting with no leftovers. The primitive
inventory over the whole part contains **no `stud*.dat`, no `box5*.dat`, no axle-hole
primitive** (§7).

**Prior research's report is CONFIRMED in every particular**: 12 holes, x = ±32 mm,
z = ±16 / ±24 / ±32 mm, mid-height 20.0 mm, axis pattern V–H–V per group of three with the
middle hole horizontal.

| # | Arm | Hole | X (mm) | Z (mm) | Height (mm) | LDU centre | Axis | Primitive | Provenance |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +X +Z | outer | **+32.000** | **+32.000** | **20.000** | (80, 0, 80) | **vertical (Y)** | `connhole` | measured (on-grid) |
| 2 | +X +Z | middle | +32.000 | +24.000 | 20.000 | (80, 0, 60) | **horizontal (+X)** | `connhol3` | measured |
| 3 | +X +Z | inner | +32.000 | +16.000 | 20.000 | (80, 0, 40) | vertical (Y) | `connhole` | measured |
| 4–6 | +X −Z | | +32.000 | −16 / −24 / −32 | 20.000 | (80, 0, −40/−60/−80) | V / H / V | ″ | measured |
| 7–9 | −X +Z | | −32.000 | +16 / +24 / +32 | 20.000 | (−80, 0, 40/60/80) | V / H / V | ″ | measured |
| 10–12 | −X −Z | | −32.000 | −16 / −24 / −32 | 20.000 | (−80, 0, −40/−60/−80) | V / H / V | ″ | measured |

* Pitch along Z: **8.000 mm** (20 LDU) — exactly one stud, on-grid.
* All twelve axes intersect the plane **height = 20.000 mm** = exactly half the hub's 40 mm
  height, and the planes **|x| = 32.000 mm** = exactly 4 studs from centre.
* The four groups are related by the two mirror planes x = 0 and z = 0; there is **no**
  handedness anywhere in the arms.

**Axis derivation (worked, so it can be re-checked).** `connhol3` is placed with
matrix `[0 −1 0 / 1 0 0 / 0 0 ±1]` at `(±80, 0, ±60)`. Its local +Y (the primitive's bore
axis) maps to world column 2 = `(∓1, 0, 0)` ⇒ **the bore axis is world X**. Its single
`peghole` sits at local `y = −10`, which maps to world `x = ±90` ⇒ **the counterbore mouth is
on the part's outermost X face (±36.000 mm)**, and the bore runs *inward*.

### 1.2 What the LDraw primitives resolve to

```
connhole.dat  (Technic Connector Hole Long)     axis Y, faces at y = ±10
  ├ peghole @ y=+10 (flipped)  ┐ counterbore
  ├ 4-4ring8 @ y=+10           ┘ + face annulus
  ├ 4-4cyli  r=6, y −8 … +8      ← the Ø4.8 bore  (BFC INVERTNEXT ⇒ inner surface)
  ├ 4-4ring8 @ y=−10           ┐
  └ peghole  @ y=−10           ┘ second counterbore

peghole.dat  (Peg Hole End)                     axis Y, 0 … +2
  ├ 4-4edge r=8 @ y=0 and y=2, r=6 @ y=2
  ├ 4-4ring3 ×2  @ y=2          ← annular shoulder, inner r=6 outer r=8
  └ 4-4cyli r=8, y 0 … 2        ← counterbore wall (BFC INVERTNEXT)

connhol3.dat  (Technic Connector Hole One-Sided)  axis Y, mouth at y=−10 only
  ├ 4-4cyli r=6, y +8 … −8      ← the Ø4.8 bore
  ├ peghole  @ y=−10            ← ONE counterbore
  └ 4-4ring8 @ y=−10            ← ONE face annulus;  the y=+8 end is left OPEN
```

| Feature | LDU | **mm** | Provenance |
|---|---|---|---|
| Bore diameter | Ø12 | **Ø4.800** | on-grid-idealized (stock primitive) |
| Counterbore diameter | Ø16 | **Ø6.400** | on-grid-idealized |
| Counterbore depth (each mouth) | 2 | **0.800** | on-grid-idealized |
| Face annulus around each mouth | r 8→9 | Ø6.4 → **Ø7.200** | on-grid-idealized |
| Through-hole total depth (vertical holes) | 20 | **8.000** | = arm thickness; through |
| ↳ of which full-Ø4.8 bore | 16 | **6.400** | measured from primitive extents |
| Blind-hole depth (middle holes) | 18 | **7.200** | from outer face 36.000 → 28.800 mm |
| ↳ counterbore 0.800 + Ø4.8 bore | 2 + 16 | 0.800 + **6.400** | measured |
| ↳ then Ø7.2 relief pocket to the wall inner face | 4 | further **1.600**, to 27.200 mm | `2-4cylo` r=9, x 72→68 |

### 1.3 Cross-check against `docs/lego-technic.md`

| Quantity | LDraw `25560` | `docs/lego-technic.md` | repo code (`vibe_cading/lego/`) | Verdict |
|---|---|---|---|---|
| Pin-hole bore Ø | **4.800** | 4.8 nominal (`PIN_HOLE_DIAMETER`) | 4.8 + 2 × `slip.radial` ≈ **4.90** | **agree** on nominal; repo adds a deliberate FDM allowance |
| Counterbore Ø | **6.400** | 6.0 (Cailliau "real-liftarm-faithful"); text notes a real range **6.0–6.2** | `TECHNIC_PIN_CB_DIAMETER = 6.2` | **disagree**: LDraw is 0.4 above the doc, 0.2 above the code, and 0.2 **outside** the doc's stated real range |
| Counterbore depth | **0.800** | 0.8 | `TECHNIC_PIN_CB_DEPTH = 1.0` | LDraw **agrees with the doc**, disagrees with the code by 0.2 |
| Face ring Ø around the mouth | **7.200** | not stated | not modelled | doc gap |
| Beam thickness | **8.000** | 7.8 (`BEAM_THICKNESS`; Cailliau measured 7.4–7.8, theoretical 8.0) | 7.8 | LDraw uses the *theoretical* 8.0; the doc uses the *measured* 7.8 |
| Beam width | **7.200** | 7.8 (`BEAM_WIDTH`, square section) | 7.8 | LDraw uses the on-grid 18 LDU; the doc uses the measured 7.8 |
| End radius | **3.600** | 3.9 (`BEAM_END_RADIUS` = width/2) | 3.9 | consequence of the width difference |

**Interpretation.** The 0.6 mm width and 0.2 mm thickness differences are *not* a
disagreement about the real part — they are a disagreement about **who idealises**. LDraw
snaps the liftarm section to 18 × 20 LDU; Cailliau (and therefore this repo) uses caliper
values ~7.8 × 7.8. Since real liftarms measure 7.4–7.8 in both directions, **the repo's
7.8 × 7.8 is closer to the moulded reality than LDraw's 7.2 × 8.0.** Do not "correct" the
repo toward LDraw here.

The counterbore is the one place LDraw carries a number the repo does not: **Ø6.4 × 0.8**.
Ø6.4 is exactly the pin's collar-flange OD quoted in `docs/lego-technic.md` line 62 — so on
the real part the flange seats flush into the counterbore. The repo's Ø6.2 × 1.0 will **not**
receive a 6.4 mm collar; it leaves the collar standing 1.0 mm proud. That is a cosmetic /
stack-up difference, not a fit failure (see §3.4).

---

## 2. The four arms — full characterisation

### 2.1 They are literally LDraw 3-hole liftarms

| Dimension | Arm in `25560` | `32523.dat` (LDraw Technic Liftarm 3) | Match |
|---|---|---|---|
| Width (projection direction) | 7.200 | 7.200 | ✔ exact |
| Thickness | 8.000 | 8.000 | ✔ exact |
| Length | 23.200 | 23.200 | ✔ exact |
| End radius | 3.600 | 3.600 | ✔ exact |
| Hole pitch | 8.000 | 8.000 | ✔ exact |

Philo built each arm from the **same primitive vocabulary as a stock liftarm** (`connhole`,
`1-4cylo` r=9 end caps, `3-16cylo` r=9 perpendicular-hole boss, `1-8ndis` face fillers). The
only departure is the perpendicular middle hole, which a plain `32523` does not have.

### 2.2 Arm placement and envelope

Four arms, one per (±X, ±Z) quadrant. Each carries one group of three holes.

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Count | **4** | | measured |
| Long axis | parallel to **Z** | | measured |
| Length (Z span) | **23.200**, \|z\| 12.400 … 35.600 | 31 … 89 | measured; = 2 × pitch + 7.2 |
| Inboard end (Z) | \|z\| = **12.400** | 31 | measured (`z = ±31` face, x 70…80, y ±10, area 400 LDU²) |
| Outboard end (Z) | \|z\| = **35.600** — **coincident with the housing's own Z extent** | 89 | measured |
| Thickness (vertical) | **8.000** | 20 | on-grid-idealized |
| Top face | **24.000 mm** above the hub bottom | y = −10 | measured — *and it is a functional landing plane, see §6* |
| Bottom face | **16.000 mm** | y = +10 | measured |
| Hole-axis plane | 20.000 mm — exactly mid-thickness of the arm **and** mid-height of the 40 mm hub | y = 0 | measured |
| Outboard flat face | \|x\| = **35.600** | 89 | measured (face area 1141.8 LDU², z 40…80) |
| Boss around the middle hole | \|x\| = **36.000**, i.e. **0.400 proud**, Ø**7.200** | `4-4cylo` r=9, x 89→90 | measured — **this boss alone is why the part measures 72.0 mm and not 71.2 mm in X** |
| Root (below 22.0 mm) | shell wall at \|x\| = **28.000**; arm projects **7.600** | 70 → 89 | measured |
| Root (above 22.0 mm) | shell wall at \|x\| = **27.200**; arm projects **8.400** | 68 → 89 | measured |

### 2.3 Outer profile — plan view (looking down the Y axis)

The arm's plan outline is the standard liftarm **stadium**, centred on the hole line
\|x\| = 32.000 mm:

* outboard flank: flat at \|x\| = 35.600 mm over \|z\| 16.000 … 32.000 mm;
* R **3.600** quarter-round about each *vertical* hole centre at both ends
  (`1-4cylo` r=9, full height y −10…+10);
* the outboard half of the stadium is exposed; the **inboard flank of the stadium
  (\|x\| = 28.400 mm) is buried in / blended into the shell wall** — a 0.4 mm bridge face at
  y = ±10 runs x 70 → 71 for the full length (`rect1` @ `(70.5, 10, 60)`, z ±31…±89);
* the **outboard end cap** is a *quarter* round from (35.600, 32.000) to (32.000, 35.600) —
  the other quarter is absorbed into the housing's end wall, which itself spans only
  \|x\| ≤ 32.000 mm at z = ±35.600;
* the **inboard end** is a flat face at \|z\| = 12.400 mm spanning \|x\| 28.000 … 32.000 mm,
  plus the R3.6 quarter-round out to (35.600, 16.000).

So: **not** a free-floating rounded wing, **not** tapered, **no fillet** where it meets the
wall. A rectangular-in-elevation, stadium-in-plan liftarm, fused flush.

### 2.4 Outer profile — the middle-hole neck

Around each *horizontal* (middle) hole the arm's top and bottom faces are **rolled off to a
cylinder of radius 9 LDU = 3.600 mm about the middle-hole axis** — four `3-16cylo` patches
(4 × 67.5° = 270° of arc), spanning x 73.636 … 86.364 LDU (29.454 … 34.546 mm):

| | Value (mm) | Provenance |
|---|---|---|
| Arm thickness at the vertical holes | **8.000** (16.000 … 24.000) | measured |
| Arm thickness at the middle hole | **7.200** (16.400 … 23.600) | measured — a 0.4 mm neck on each face |
| Neck extent along X | 29.454 … 34.546 (5.092 wide) | measured, off-grid (= 32.000 ± 9/√2 LDU) |
| Flat top/bottom faces resume | \|x\| < 29.454 and > 34.546 | measured |

This neck is **functional, not decorative**: the top shell `25561` lands on the arm's top face
(§6) and carries a matching `2-4cylo` r=9 relief at `(±70, 0, ±60)` so its skirt clears the
neck. Two mating parts model the same cylinder — strong evidence it is real.

### 2.5 The middle hole is BLIND, not through

This is the single most consequential arm finding and it is easy to miss.

```
outer face 36.000 ─┐
                   ├ 0.800  Ø6.400 counterbore     (peghole)
   35.200 ─────────┤
                   ├ 6.400  Ø4.800 bore            (4-4cyli r=6, x 88 → 72)
   28.800 ─────────┤
                   ├ 1.600  Ø7.200 relief pocket   (2-4cylo r=9, x 72 → 68)
   27.200 ─────────┘  ← shell inner wall face; opens into the battery cavity
```

* Counterbore on the **outer face only**; there is no counterbore on the inboard side.
* Guided (Ø4.8) engagement length = **6.400 mm**.
* The Ø7.2 relief means a fully inserted Technic pin **can pass through into the battery
  cavity** — it is functionally a through-hole with a 7.2 mm guided lead-in, not a blind
  socket that bottoms out.

---

## 3. Comparison — real moulded arm vs `PerpendicularHolesLiftarm(3, ["main","perp","main"])`

Read from source: `vibe_cading/lego/technic_beam_perp.py`,
`vibe_cading/lego/cutters/technic_pin_hole.py`, `vibe_cading/lego/constants.py`.

### 3.0 Axis correspondence (get this right before comparing numbers)

The class's own frame: `X` = beam length, `Y` = beam width (7.8), `Z` = beam thickness (7.8),
Z = 0 is the print-bed datum, X = 0 is the outermost end-cap tangent.
`"main"` bores along **+Z** (through the flat faces); `"perp"` bores along **±Y** (through the
narrow side faces), centred at `Z = BEAM_THICKNESS/2`.

Mapping onto the housing arm:

| class axis | housing axis | class value | housing value |
|---|---|---|---|
| X (length) | Z (arm long axis) | 24.000 | 23.200 |
| Y (width) | X (projection out of the wall) | 7.800 | 7.200 |
| Z (thickness) | height (vertical) | 7.800 | 8.000 |
| `"main"` bore ‖ +Z | ‖ vertical | ✔ | ✔ |
| `"perp"` bore ‖ ±Y | ‖ X (outward) | ✔ | ✔ |

`hole_axes = ["main","perp","main"]` therefore reproduces the real **V–H–V** pattern exactly,
with the perpendicular bore correctly emerging through the arm's outboard face.

### 3.1 Hole pattern — exact match

| | Real `25560` arm | `PerpendicularHolesLiftarm(3, …)` | Verdict |
|---|---|---|---|
| Hole count | 3 | 3 | ✔ |
| Pitch | 8.000 | `STUD_PITCH` = 8.000 | ✔ |
| Axis sequence | V, H, V | main, perp, main | ✔ |
| Bore axis height | mid-thickness (20.000 mm) | `Z = BEAM_THICKNESS/2` | ✔ |
| Hole centres along the beam | 4.0 / 12.0 / 20.0 from the **hole-line end**, i.e. 3.6 / 11.6 / 19.6 from the beam tip | 4.0 / 12.0 / 20.0 from X = 0 (the end-cap tangent) | **0.4 mm offset per end** — the class's end cap is centred 0.1 mm inboard of the hole centre and the cap radius is 3.9 not 3.6 |

**The pattern matches. The dimension chain from the pattern to the beam ends does not.**

### 3.2 Cross-section

| | Real (LDraw) | Class | Δ |
|---|---|---|---|
| Projecting width | 7.200 | 7.800 (`BEAM_WIDTH`) | class **+0.600** |
| Thickness (vertical) | 8.000 | 7.800 (`BEAM_THICKNESS`) | class **−0.200** |
| Section shape | rectangle, stadium in plan, **necked to 7.200 thick at the middle hole** | uniform stadium, **no neck** | neck absent |
| End-cap radius | 3.600 | 3.900 (`BEAM_END_RADIUS`) | class **+0.300** |
| Overall length | 23.200 | 24.000 (`num_holes × STUD_PITCH`, hard-coded) | class **+0.800** |

Note §0.1: the width/thickness deltas are LDraw-idealisation artefacts, not measurement
disagreements — real liftarms are ~7.8 × 7.8. **Only the length and the neck are genuine
shape differences.**

### 3.3 Where the extra 0.8 mm of length actually lands

The arm's outboard end at \|z\| = 35.600 mm **is** the housing's Z envelope. A 24.000 mm
class instance placed to keep the hole pitch and hole positions correct overhangs that end by
**0.400 mm**, pushing the housing footprint from 71.200 to 72.000 mm in Z. (The X envelope is
already 72.000 mm — but for a different reason: the Ø7.2 × 0.4 boss of §2.2.) You would end up
with a 72.0 × 72.0 mm housing instead of 72.0 × 71.2 mm. Small, but it is a *stud-grid*
consequence: 71.2 mm = 8.9 studs is deliberate.

### 3.4 Bore and counterbore — does it matter for pin fit?

| | Real | Class (`fit="slip"`, `fdm_standard`) | Functional consequence |
|---|---|---|---|
| Bore Ø | 4.800 | ≈ 4.90 (4.8 + 2 × `slip.radial`) | **Correct as-is.** The allowance is what makes an FDM print accept a real pin. Copying 4.800 literally would print tight. |
| Counterbore Ø | 6.400 | 6.200 | Real pin collar OD is 6.4 → real part seats the collar flush, class leaves it 1.0 mm proud. **Stack-up/appearance only** — no pin ever bears on the counterbore. |
| Counterbore depth | 0.800 | 1.000 | ″ |
| Face ring Ø | 7.200 | absent | cosmetic |
| Lead-in chamfer | none in LDraw | 0.300 (`LEAD_IN`) | class is **better** for printed parts |
| Vertical holes: guided bore length | 6.400 (8.0 − 2 × 0.8) | 5.800 (7.8 − 2 × 1.0) | **−0.600 mm, −9 % of friction length** |
| Middle hole: guided bore length | 6.400 (blind, counterbore on the outer face only) | 5.800, **and a Ø6.2 counterbore cut into the shell's inner wall** | −9 % friction; plus the inner counterbore removes 1.0 mm from a 0.8 mm wall — it would punch a Ø6.2 hole into the battery cavity |

The last row is the only bore/counterbore item with real consequence, and it is a one-line
fix: for the perpendicular hole, do not counterbore the inboard face.

### 3.5 Structural difference — integral moulded wing vs beam fused onto a wall

| | Real moulded part | Printed liftarm fused to a printed wall |
|---|---|---|
| Construction | injection-moulded ABS; the arm is a **solid 8.0 mm boss** hanging off a **0.8 mm** shell wall | FDM; both arm and wall print at whatever infill/perimeter the slicer gives |
| Load path from a pin | pin → arm → 0.8 mm wall → 71 mm-long box section (the shell acts as the beam) | pin → arm → wall → box section — **same topology** |
| Weak link | the 0.8 mm wall/arm junction, in bending and in peel | the printed layer interface at the junction, **plus** FDM layer adhesion across the fuse |
| Stiffness | wall-limited | at least equal — a printed wall will be ≥ 1.2–1.6 mm and the fuse is a solid union, not a glued joint |
| Anisotropy | none | **the dominant real risk**: if the housing prints with layers ⊥ to the pin axis, an arm loaded in shear peels along a layer line |
| Root geometry | the wall **steps 0.8 mm** at 22.0 mm height (from \|x\| 28.0 to 27.2 — see §4), so the arm's root face is **not planar** | a single-plane fuse cannot reproduce a stepped root; you get a 0.8 mm mismatch across the top 2.0 mm of the arm |
| Stress raiser | sharp, unfilleted junction (LDraw shows none; the real mould certainly has one, **not modelled**) | sharp unless you add a fillet — and adding one is an improvement |

**Net:** the structural difference favours the liftarm-fused-to-wall approach, not against it.
The real part is weaker than a printed equivalent because it is a thin-wall moulding.

### 3.6 ⭐ Bottom line — the functional gap, cosmetics set aside

**Verdict: for pin insertion and pin load, a `PerpendicularHolesLiftarm(3, ["main","perp","main"])`
fused onto the wall is functionally equivalent to the real moulded arm. It is not a
compromise on the Technic interface.** Everything that decides whether a Technic pin goes in
and holds — hole count, 8.000 mm pitch, V–H–V axis alternation, mid-thickness bore plane,
Ø4.8 nominal bore, ≥ 5.8 mm of guided bore, 8 mm of material to bore through — is matched or
bettered.

The gaps that are real are **not pin gaps, they are dimension-chain and interface gaps**, and
there are exactly four:

1. **Length 24.000 vs 23.200 mm.** The class hard-codes `length = num_holes × STUD_PITCH`.
   The 0.8 mm surplus lands on the housing's Z envelope, turning 71.2 mm (8.9 studs) into
   72.0 mm. *Blocking for an "exact copy"; needs a length override or a bespoke body.*
2. **Thickness 7.800 vs 8.000 mm.** The arm's **top face at 24.000 mm is the plane the upper
   layer sits down on** (§6, verified against `25561`). A 7.8 mm arm centred on 20.0 mm gives
   16.100 … 23.900 — the whole upper layer drops 0.1 mm, or the arm is no longer symmetric
   about the hole axis. *Blocking for the layer interface; trivially fixed by pinning the arm
   to 16.000–24.000.*
3. **The Ø7.200 × 0.400 boss around each middle hole is missing.** It is the *sole* reason
   `25560` measures 72.000 mm in X rather than 71.200 mm. Omit it and the X envelope is wrong
   by 0.8 mm. *Blocking for an exact copy; additive, easy.*
4. **The middle hole is one-sided in the real part.** The class bores through with a
   counterbore at both mouths; the inboard mouth lands in the shell wall/cavity. *Not
   blocking for pin fit, but it thins the wall and opens a Ø6.2 hole into the battery bay.*

Two further differences are **genuinely cosmetic** and can be dropped without argument: the
0.4 mm thickness neck at the middle hole (its only function is clearing the top shell's
skirt — if you model the upper layer yourself, you control that clearance), and the
counterbore Ø6.4 × 0.8 vs Ø6.2 × 1.0.

**Recommendation:** reuse the class. Do not hand-roll the arm. Add (a) an explicit
length/thickness override or a thin subclass, (b) the middle-hole boss as a separate
`union()`, (c) suppress the inboard counterbore on the perpendicular hole. If the class
cannot take a length override without churn, that is an argument for extending the class —
its hole pattern, cutter pipeline, chamfer selectors and single-solid guard are all exactly
what this part needs.

---

## 4. Wall thicknesses

| Region | Height band (mm) | Faces (LDU) | Thickness (mm) | Provenance |
|---|---|---|---|---|
| Side wall, **lower** | 0.0 … 22.0 | x 68 (inner) → 70 (outer) | **0.800** | measured, both faces present |
| Side wall, **upper** | 22.0 … 29.6 | x 66 (inner) → 68 (outer) | **0.800** | measured, both faces present |
| Side-wall step | at **22.0** (y = −5) | ledge face x 68…70, z ±23 | 0.800 outward step | measured (`rect3` @ `(69,−5,0)`) |
| Latch-end wall (−Z) | 3.6 … 22.0 | z −89 (outer) → −86 (inner) | **1.200** | measured |
| Latch-slot inboard wall | 16.0 … 21.2 | z −80 → −77 | **1.200** | measured |
| Top deck | at 29.6 (y = −24) | outer face only, area 21 914 LDU² | **NOT MODELLED** | absent — no underside face exists anywhere |
| Tongue-end (+Z) walls | 0.0 … 20.0+ | z 80 / 83.4443 / 86 / 89 | 1.200–2.400, varies | measured, see §5.3 |

**Envelope consequence of the step:** the housing is **56.000 mm** wide (\|x\| ≤ 28.000) below
22.0 mm and **54.400 mm** wide (\|x\| ≤ 27.200) above it. The lid `24853` is 54.400 mm wide —
it seats inside the *lower* 56.0 mm section against the x = ±68 faces, flush with the bottom.

---

## 5. Lid interface

The lid sits at hub `(0, 50, 0)` identity, so lid-local Z = housing Z directly, and lid-local
"height above the outer face" = housing height above the hub bottom.

### 5.1 Bottom rim / lid seat

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Bottom face plane | 0.000 | y = 50 | measured; total face area only 931.8 LDU² |
| Rim strips | \|x\| **27.200 … 28.000** (0.800 wide) along both sides, plus end strips | x 68…70 | measured |
| Rim interruption | **absent over \|z\| ≤ 12.000 mm** — the tray-tab windows (§7.2) | z −30 … +30 | measured |
| Lid location | lid outer face flush at 0.000 mm; located laterally by the x = ±27.200 mm faces | | derived |

The bottom is otherwise **wide open** — the lid is the floor.

### 5.2 Latch end (Z = −35.600 mm) — and the missing bite

Two mirrored latch slots receive the lid's two hook fingers.

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Slot count | 2 | | measured |
| Slot X extent | \|x\| **5.600 … 19.200** (13.600 wide) | 14 … 48 | measured — **exactly matches the lid hook width 13.600** ✔ |
| Gap between slots | **11.200** (\|x\| ≤ 5.600) | ±14 | measured — **exactly matches the lid hook gap 11.200** ✔ |
| Slot outboard face | z = **−34.400** | −86 | measured, full slot height |
| Slot inboard face | z = **−32.000**, existing only over height **16.000 … 21.200** | −80, y −3…10 | measured |
| Slot ceiling | height **16.000**, z −32.000 … −30.800 | y = 10 | measured (`rect` @ `(31,10,−78.5)`) |
| Slot floor step | height **4.800**, z −34.400 … −34.000 | y = 38 | measured |
| Slot vertical extent (clear) | **4.800 … 16.000** | y 38 … 10 | measured |
| Side walls | x = ±5.600 and ±19.200, 0-thickness skins in LDraw | 14 / 48 | measured |
| Access windows in the end face | two, \|x\| **5.600 … 19.200**, height **0.000 … 3.600** | z = −89, y 41…50 | measured — the lid's thumb pads show through these |
| Central bridge at the end face | \|x\| ≤ 5.600, height 0.000 … 3.600, **solid** | z −89, x ±14, y 41…50 | measured |

#### ⚠ The latch bite ramp is NOT modelled

The lid's barb is a Ø2.000 mm bead whose axis sits at **height 12.000 mm** (LDraw y = +20)
with its most-inboard point at z = **−31.200 mm** (LDraw z = −78). The barb therefore
occupies **heights 11.000 … 13.000 mm**.

There is **no groove, no undercut, no ramp, no catch** anywhere in the slot, and the only
candidate surface — the inboard wall at z = −32.000 mm — **stops at height 16.000 mm**,
i.e. 3.0 mm *above* the top of the barb.

> **This negative result was independently re-audited — see §11, which supersedes this
> paragraph.** §11 derives the lid→housing transform from the tracked file chain rather
> than by inference, re-runs the search with a stronger (AABB-overlap, ±3 mm padded) test,
> sweeps nine sibling parts, and establishes the stronger finding that the wall which would
> carry the catch is itself *absent* at the barb's height. Verdict: **CONFIRMED ABSENT**.
> Note also that the triangle counts originally quoted here came from a centroid-containment
> test that under-reports; §11.6 gives the corrected counts.

What LDraw *does* give you, and what is reliable, is the slot envelope (13.600 wide ×
2.400 deep in Z × 11.200 tall) and the 11.200 mm centre spacing.

*(Note for the design brief: prior research described "an 11.2 mm release window in the
housing". The 11.200 mm dimension is real, but it is the **gap between the two hooks / slots**
and at the end face that strip is **solid**. The finger access is the **two 13.600 × 3.600 mm
windows either side of it**, at heights 0.000–3.600 mm. A finger or thumb reaches the lid's
thumb pads through those, not through the 11.2 mm centre.)*

### 5.3 Tongue end (Z = +35.600 mm) — modelled, and it matches

The lid's slide-in tongue tip (0.926 mm thick, heights 1.874 … 2.800 mm, \|x\| ≤ 15.600 mm,
Z 33.378 … 34.400 mm) has a matching receiver in the housing:

| Housing feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Ledge underside | height **1.874**, \|x\| ≤ **15.600**, z 33.378 … 34.400 | y = 45.3151, x ±39 | measured — **1.874 matches the lid tongue tip datum exactly** ✔ |
| Second ledge | height **2.674**, \|x\| ≤ **26.000**, z 33.378 … 34.400 | y = 43.3151, x ±65 | measured, off-grid (arc-derived) |
| Wall planes | z = **32.000** (x ±27.2, heights 0…28), **33.378** (x ±26.0), **34.400** (x ±27.2), **35.600** (x ±32.0) | 80 / 83.4443 / 86 / 89 | measured |

`83.4443` and `45.3151` are the same construction constants seen in the lid — they are points
on shared arcs/45° chamfers, not independent measurements.

> **Fully characterised in §12**, which audits this end for retention: the tongue tip rests
> on a ledge at height 1.874 mm — a sliding **lap/rebate, not a snap** — and unlike the latch
> end it is completely modelled. §12 also covers the 6 locating teeth (engage nothing), the
> 1.6 mm groove (a *tray* feature, not a housing one), and the single-wall collapse.

---

## 6. Top interface — how `25560` nests with `25561`

This becomes the top interface of our layer, so it is worth being precise.

| | Value (mm) | LDU | Provenance |
|---|---|---|---|
| `25561` envelope | 56.000 × 71.200 × 23.600, heights **16.400 … 40.000** | y −50 … +9 | measured |
| `25560` envelope | 72.000 × 71.200 × 33.800, heights **0.000 … 33.800** | y +50 … −34.5 | measured |
| Bounding-box overlap | 16.400 … 33.800 = **17.400** | 43.5 | measured — but this is *only* a bbox overlap, **not** the mating interface |

**The actual mating interface has two levels**, both verified by sectioning `25561`:

| Where | Bottom shell presents | Top shell lands at | Provenance |
|---|---|---|---|
| **Between the arms** (\|z\| ≲ 12.4 mm and the central band) | a 0.800 mm wide ledge at **height 22.000 mm**, \|x\| 27.200 … 28.000 | its skirt wall (x 68…70) bottoms on that ledge — `25561` face at y = −5, area **604.0 LDU²**, identical to `25560`'s y = −5 face area **604.0** | measured, both parts |
| **Over the arms** (\|z\| 12.4 … 35.6 mm) | the **arm's top face at height 24.000 mm** | `25561`'s skirt stops at y = −10 at z = 50 (verified by section) — it sits down on the arms | measured, both parts |
| At each middle hole | the Ø7.200 neck (§2.4) | `25561` carries a matching `2-4cylo` r=9 relief at `(±70, 0, ±60)` spanning x 68…70 | measured, both parts |

**Lap joint.** The bottom shell's wall steps *inward* 0.800 mm at height 22.000 mm (outer face
28.000 → 27.200 mm). The top shell's 0.800 mm skirt occupies exactly the vacated 27.200 …
28.000 mm annulus, so the assembled hub is **flush 56.000 mm wide** over its whole height.
Engagement depth of the lap = 22.000 − 16.400 = **5.600 mm** between the arms.

**Design consequence for our layer:** the top interface is *(a)* a flush outer surface at
\|x\| = 28.000 mm, *(b)* a 0.800 mm wide seating ledge at 22.000 mm over the central band,
*(c)* the arm top faces at 24.000 mm as the primary landing plane, and *(d)* an inner
locating face at \|x\| = 27.200 mm above 22.000 mm. The 17.4 mm "overlap" figure should not
be used as an interface dimension.

---

## 7. Other features

### 7.1 Studs / anti-studs — there are NONE

The complete primitive inventory of `25560` (826 instances) contains **no `stud*.dat`, no
`box5*.dat`, no `4-4disc` stud top, and no axle-hole primitive**. The part is entirely
studless. Its *only* System/Technic connection features are the 12 pin holes of §1.

### 7.2 Side windows (tray-tab access)

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Count | 2 (one per ±X side) | | measured |
| Z extent | **−12.400 … +12.400** (24.800 long) | ±31 | measured |
| Height (central portion) | **0.000 … 8.400**, over \|z\| ≤ 8.400 | y 50 → 29 | measured (`rect2p` @ `(69,29,0)`, z ±21) |
| Height (ends, ramped) | rises to **0.000 … 16.000** at \|z\| = 12.400 | y 50 → 10 | measured (quad @ x = 70, (29,−21)(29,21)(10,31)(10,−31)) |
| Upper bound | the arms' bottom faces at 16.000 mm | | derived |

Cross-check against the tray `24849`: its extraction-tab pad is **24.000 mm long** (z ±12.000)
with the finger ledge underside at **8.400 mm**. The window is 24.800 × 8.400 mm. **Exact
match** — the window exists to expose those tabs, and the ramped ends give finger clearance.
This also resolves the apparent interference noted during extraction: the tray's ledge reaches
\|x\| = 28.400 mm, which is 0.400 mm outboard of the housing's 28.000 mm wall — but the wall
is *absent* over exactly that z band, so there is no interference. The tab protrudes through
the window.

### 7.3 Connector-port ribs (top deck)

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Count | **4** — 2 inherited from `24851` (via `s01`), 2 added by `25560.dat` | | measured |
| Positions | \|x\| ≈ 18.800 … 20.000, centred at **z = −24.000** and **z = −8.000** | (±48.5, −60) and (±48.5, −20) | measured |
| Rib pair | two 1.200 mm walls at \|x\| = 18.800 and 20.000 | 47 / 50 | measured |
| Length (Z) | **13.600** each | 34 | measured |
| Height | **29.600 … 33.800** (4.200 proud of the deck) | y −24 … −34.5 | measured |
| Mouth detail | four R0.800 quarter-rounds per rib at z offsets ±5.400 and ±3.600 mm | `1-4cylo` r=2 | measured |

**Only the keying ribs are modelled.** The socket cavity, the contacts, the port surround and
the port labelling are **absent**.

### 7.4 AA-cell cradles (battery-bay ceiling)

The bay ceiling carries a corrugated cradle profile (`1-8cylo` r≈16 LDU patches at heights
22.09 mm and a `rect` band at 24.54 mm, X centres at LDU −10 and +26, Z spans −57…+55 and
−72…+68). This is the underside of the top deck and it *is* modelled, because it is visible
through the open bottom. It corresponds to the 6-AA layout the tray `24849` also stages.
Treat depths as idealized; treat the 14.4 mm pitch as reliable (it is the AA diameter).

### 7.5 Single asymmetric boss on the top deck

At **(x = +10.400, z = +20.000) mm**, height 29.600 → 32.000 mm: a Ø**4.800** blind bore
(`4-4cylo` r=6, `BFC INVERTNEXT`) inside a Ø**7.200** raised collar (`4-4cyli` r=9), with a
45°-rotated chamfer stack (`1-4ring2`, `1-4ring11`, `1-4cylo` r≈3.889). Sits on a raised pad
spanning x 8.000 … 12.800 mm, z 17.600 … 22.400 mm. **Not mirrored** — it exists once. Reads
as an assembly/screw boss. Function not determinable from LDraw.

---

## 8. Explicitly ABSENT / NOT MODELLED

Everything in this list is a "you must measure the real part" item, not a number you can lift.

1. **The latch bite feature** (groove/ramp/undercut for the lid's Ø2.0 mm barb). Verified
   absent — §5.2, re-audited and **CONFIRMED ABSENT** in §11 (derived transform, padded
   AABB search, nine-part sibling sweep). **Highest-priority physical measurement.**
2. **The top deck's thickness.** The deck at 29.600 mm has no underside face. No wall
   thickness can be read.
3. **Every internal cavity surface not visible from outside** — ribs, bosses, screw columns,
   PCB standoffs, battery-contact mounts, wire routing. LDraw models the outer skin plus what
   shows through the bottom opening and the side windows.
4. **The port sockets themselves** — only the two keying ribs per port exist. No cavity, no
   contacts, no surround.
5. **Mould draft.** None anywhere on this part (the lid's 2° latch-arm draft has no analogue
   here).
6. **Fillets and chamfers at the arm/wall junction.** LDraw shows a sharp junction; a real
   moulding will have a root radius.
7. **Edge fillets on the shell perimeter, the bottom rim, and the latch slot.**
8. **The lid's snap-in retention on the tongue end** beyond the two ledge planes of §5.3.
9. **Ejector-pin marks, gate marks, part-number embossing, LEGO logo.**
10. **Any material/colour/texture information.**

### What an exact copy needs that LDraw cannot give

| # | Needed | Why LDraw fails | How to get it |
|---|---|---|---|
| E1 | Latch catch profile (depth, ramp angle, height on the z = −32.000 mm face) | absent (§5.2) | caliper + a section through a scrap hub, or reverse-fit from the lid's Ø2.0 barb at 11.0–13.0 mm |
| E2 | Top-deck thickness | no underside face | caliper through a port opening |
| E3 | Real arm section (7.2 × 8.0 is idealized) | grid-snapped primitives | caliper the arm; expect ≈7.8 × 7.8 per Cailliau |
| E4 | Real counterbore Ø and depth | stock primitive Ø6.4 × 0.8 | caliper; doc range says 6.0–6.2 |
| E5 | Arm root fillet radius | not modelled | caliper / optical |
| E6 | Wall thickness of the +Z tongue-end structure | partially inferable only | caliper |
| E7 | Whether the middle pin hole really opens into the battery cavity, or has a moulded blind boss | LDraw shows a Ø7.2 relief straight through to the inner wall face | inspect a real hub from inside |

---

## 9. Grid check summary

| Dimension | mm | LDU | On/off grid |
|---|---|---|---|
| Overall X (with middle-hole bosses) | 72.000 | 180 | on-grid — 9.0 studs |
| Overall X (nominal faces) | 71.200 | 178 | off-grid — 8.9 studs |
| Overall Z | 71.200 | 178 | off-grid — 8.9 studs |
| Overall height | 33.800 | 84.5 | off-grid, **half-LDU** — from the port ribs at y = −34.5 |
| Hub height (assembled) | 40.000 | 100 | on-grid — 5.0 studs |
| Hole X plane | ±32.000 | ±80 | on-grid — 4 studs |
| Hole Z planes | ±16 / ±24 / ±32 | ±40/60/80 | on-grid |
| Hole axis height | 20.000 | 0 | on-grid — exact mid-height |
| Hole pitch | 8.000 | 20 | on-grid — 1 stud |
| Arm length | 23.200 | 58 | off-grid — 2.9 studs (= 2 pitches + 1 width) |
| Arm width / thickness | 7.200 / 8.000 | 18 / 20 | on-grid-idealized |
| Bore / counterbore / cb depth | 4.800 / 6.400 / 0.800 | 12 / 16 / 2 | on-grid-idealized |
| Middle-hole boss proud | 0.400 | 1 | on-grid-idealized |
| Wall thickness | 0.800 | 2 | LEGO-standard idealized |
| Wall step height | 22.000 | y = −5 | on-grid-idealized |
| Arm top / bottom faces | 24.000 / 16.000 | y = ∓10 | on-grid-idealized |
| Latch slot width / gap | 13.600 / 11.200 | 34 / 28 | off-grid — measured (matches the lid exactly) |
| Side window | 24.800 × 8.400 | 62 × 21 | off-grid — measured (matches the tray tabs) |
| Tongue ledge heights | 1.874 / 2.674 | 45.3151 / 43.3151 | **construction artefacts** (arc/45° points), not design intent |
| Arm neck extent | ±2.546 about the hole | ±9/√2 | construction artefact |
| `83.4443`, `−34.5`, `86.3639` … | | | construction artefacts — do not treat as measurements |

---

## 10. Reproducing this extraction

```
python3 tmp/ldraw/measure.py 25560.dat 24851.dat 25561.dat 22127.dat 32523.dat

python3 tmp/ldraw/housing_probe.py prims  25560.dat conn        # hole census + transforms
python3 tmp/ldraw/housing_probe.py prims  25560.dat ""          # full primitive inventory
python3 tmp/ldraw/housing_probe.py faces  25560.dat xyz         # axis-aligned face maps
python3 tmp/ldraw/housing_probe.py sec    25560.dat z x 45 50 60 70   # numeric sections
python3 tmp/ldraw/housing_probe.py asc    25560.dat z x 70 64 92 -14 14   # windowed ASCII
python3 tmp/ldraw/region_dump.py 25560.dat 14 48 12 28 -86 -76  # latch-bite box (empty)
```

`housing_probe.py` extends `analyze.py` with (a) a recursive primitive-instance walker that
reports each `.dat` reference with its **composed world matrix**, (b) numeric section-vertex
dumps, and (c) a windowed ASCII section. `region_dump.py` lists every triangle whose centroid
falls inside an LDU box, with its source subpart — this is the tool that proved the latch bite
absent. `inside_test.py` (ray-cast parity) was written and **must not be trusted**: LDraw
meshes are not watertight.

**Caveat on the ASCII plots:** `ascii_plot` draws increasing values upward, and LDraw's −Y is
up, so every elevation plot is vertically mirrored relative to the physical part.

---

# 11. RE-VERIFICATION — the latch bite feature

**Verdict: CONFIRMED ABSENT.** *(supersedes the negative reported in §5.2)*

This section exists because the §5.2 negative is the one finding that sends the user to a
caliper, and because a false negative there is far more likely to come from a cross-part
coordinate-frame error than from Philo actually omitting the feature. The audit was run
against that hypothesis specifically.

## 11.1 The lid→housing transform is READ, not derived

The premise behind the concern — *"the lid is never instanced inside the housing's file, so
the seating transform has to be inferred"* — turns out **not to hold**. The two parts are
composed together, one level up, in a tracked file. The full chain:

```
parts/22127.dat  (Electric Control+ Hub)
  ├ 1 16  0   0 0   1 0 0  0 1 0  0 0 1   25561c01.dat      ← identity
  │    └ 1 16  0 0 0   1 0 0  0 1 0  0 0 1   25561.dat       (top shell)
  │    └ 1 72  0 0 0   1 0 0  0 1 0  0 0 1   25560c01.dat    ← identity
  │         └ 1 16  0 0 0   1 0 0  0 1 0  0 0 1   25560.dat  ← identity  ★ HOUSING
  ├ 1 72  0  50 0   1 0 0  0 1 0  0 0 1   24849.dat          (tray)
  └ 1 72  0  50 0   1 0 0  0 1 0  0 0 1   24853.dat          ← ★ LID
```

Composing the matrices (all identity rotations, so this is pure translation):

```
housing → 22127 :  T = (0,  0, 0),  R = I        (three identity hops)
lid     → 22127 :  T = (0, 50, 0),  R = I

⇒  LID → HOUSING :   x_h = x_l ,   y_h = y_l + 50 ,   z_h = z_l        [LDU]
```

**There is no rotation and no sign flip.** LDraw's −Y-is-up convention is common to both
parts, so it cancels: it never enters the transform. The `50` is a translation *along* the
shared Y axis, applied to the lid, in the direction that moves the lid's `y = 0` outer face
onto the housing's `y = +50` bottom plane.

### Three independent confirmations

| # | Anchor | Prediction under `T = (0, +50, 0)` | Observed | Result |
|---|---|---|---|---|
| A | **Envelope closure** | lid's max y (`0`) → hub `+50`; hub spans y −50…+50 = 40.000 mm | `22127` measures exactly **40.000 mm** tall, and its y-max is **+50** | ✔ exact |
| B | **Slide-in tongue** (§5.3) | lid tongue-tip datum at local y = **−4.6849** → housing y = **+45.3151** | housing carries a face at **y = 45.3151** exactly (x ±39, z 83.444…86) — the ledge the tongue slides under | ✔ exact to 4 dp |
| C | **Finger windows** (§5.2) | lid thumb pads at \|x\| 14…48 LDU reaching z = −89 must sit inside the housing's end-face windows | housing windows are **x 14…48, z = −89, y 41…50** — identical x bounds, identical z plane | ✔ exact |

Anchor B is the decisive one: `45.3151` is a construction artefact (a point on a 45° chamfer),
not a round number. Two parts carrying the *same* four-decimal artefact at the *same* place
under the transform cannot be coincidence. **The three anchors agree with each other and with
the file chain. There is no disagreement to report.**

## 11.2 Barb geometry re-read at source

Not taken from the prior summary. `parts/s/24853s01.dat` line 132:

```
1 16  48 -30 -80.5   0 -34 0   0 0 -2.5   2.5 0 0   7-16cylo.dat
```

Decomposing (`7-16cylo` = 7/16 of a unit cylinder, local axis Y, local circle in XZ,
θ ∈ [0°, 157.5°], axis parameter t ∈ [0, 1]):

```
X_lid = -34·t  + 48          ⇒  x ∈ [14, 48]      (34 LDU = 13.600 mm hook width ✔)
Y_lid = -2.5·sinθ - 30       ⇒  y ∈ [-32.5, -30]
Z_lid =  2.5·cosθ - 80.5     ⇒  z ∈ [-82.81, -78.0]
```

So: a **bead of radius 2.5 LDU = Ø2.000 mm**, axis ∥ X at lid-local `(y = −30, z = −80.5)`,
running the full 13.600 mm hook width. `24853.dat` instances `s01` twice (identity + X-mirror),
so there are two, at \|x\| 5.600…19.200 mm, 11.200 mm apart. All of this matches §5.2 and the
lid extraction. The arc wraps the hook's tip: θ = 0 is the most-inboard point, θ = 90° the
highest, θ = 157.5° back down on the outboard side.

## 11.3 Barb position and search volume, in HOUSING coordinates

Applying `y_h = y_l + 50`, and `height = (50 − y_h) × 0.4`:

| | LDU (housing frame) | **mm** |
|---|---|---|
| Bead axis | y = **+20**, z = **−80.5**, x ∈ [14, 48] | height **12.000**, z **−32.200**, x **5.600 … 19.200** |
| Bead AABB | x [14, 48], y [17.5, 22.5], z [−83.0, −78.0] | x [5.600, 19.200], height [**11.000, 13.000**], z [−33.200, −31.200] |
| Most-inboard point | (y = 20, z = **−78.0**) | height 12.000, z = **−31.200** |
| Mirror copy | x ∈ [−48, −14] | x −19.200 … −5.600 |
| **Search volume, padded ±3 mm (±7.5 LDU)** | **x [6.5, 55.5] · y [10, 30] · z [−90.5, −70.5]** | **x [2.600, 22.200] · height [8.000, 16.000] · z [−36.200, −28.200]** |

## 11.4 Was the original dump box correct?

**Yes — the frame and the sign were both right. The *test* was too weak.**

| | x (LDU) | y (LDU) | z (LDU) |
|---|---|---|---|
| Correctly-derived bead AABB | 14 … 48 | 17.5 … 22.5 | −83.0 … −78.0 |
| Original dump box (§5.2) | 14 … 48 | 12 … 28 | −86 … −76 |
| Contains the bead? | ✔ exactly | ✔ with 5.5 LDU margin | ✔ with 3 LDU margin |

The original box **strictly contains** the correctly-derived barb volume on all three axes, so
no offset error occurred and the conclusion was not built on a mis-framed search. It had two
real methodological weaknesses, both now fixed:

1. **No padding in x** — the box ended exactly on the hook edges, so a catch flaring wider
   than the hook would have been clipped. Now padded ±3 mm in every axis.
2. **Centroid-containment test** — `region_dump.py` originally counted a triangle only if its
   *centroid* fell inside the box, which silently drops large walls that pass *through* it.
   That is unsafe for proving absence, and it is why §5.2 quoted "5 triangles". The tool has
   been rewritten to use **AABB overlap** (plus an optional strict vertex-inside mode). The
   corrected count for the same region is **30**, not 5. The conclusion is unchanged, but the
   original number should not have been quoted as evidence of emptiness.

## 11.5 Re-run against the corrected volume

```
python3 tmp/ldraw/region_dump.py 25560.dat 6.5 55.5 10 30 -90.5 -70.5
```

**30 triangles overlap. Every single one is an axis-aligned planar wall. Zero curved or
sloped triangles.**

| Plane | LDU | mm | Tris | What it is |
|---|---|---|---|---|
| x | 14.0 / 48.0 | ±5.600 / ±19.200 | 4 + 4 | latch-slot side walls |
| y | 10.0 | height 16.000 | 2 | slot ceiling (z −80 … −77) |
| z | −89.0 | −35.600 | 7 | outer end face |
| z | −86.0 | −34.400 | 3 | end-wall inner face |
| z | −80.0 | −32.000 | 2 | inboard slot wall — **spans only y −10 … +10** |
| z | −77.0 | −30.800 | 8 | main inboard wall |
| — | — | — | **0** | **no cylinder, cone, ramp, chamfer, bead or undercut** |

A catch of any kind — snap ridge, ramp, groove, undercut — is necessarily either a curved
surface or a sloped plane. **The count of non-axis-aligned triangles in the padded volume is
zero.**

## 11.6 Sibling-part sweep

Same padded volume, same test, across every plausible sibling:

| Part | Description | Tris in part | Overlapping box | Curved | Latch-engagement feature? |
|---|---|---|---|---|---|
| `25560` | Control+ hub bottom (clip lid) | 4592 | 30 | **0** | **none** |
| `25560c01` | ″ with contacts | 4736 | 30 | **0** | **none** — the `c01` adds only contact plates |
| `24851` | shared 2-port battery-box bottom | 4396 | 30 | **0** | **none** |
| `s/24851s01` | its mirrored half-subpart | 2039 | 24 | **0** | **none** — this is where the slot lives |
| `s/24851s02` | connector rib subpart | 98 | 0 | 0 | n/a — nowhere near |
| `25561` | top shell | 3451 | **0** | 0 | **ruled out** — no geometry in the volume at all |
| `80738` | 2025 Control+ bottom, **screw** lid | 5668 | 60 | **32** | **screw boss — not a clip catch** (§11.7) |
| `80738c01` | ″ with contacts | 5812 | 60 | 32 | ″ |
| `u9336` | 2025 2-port battery-box bottom, screw lid | 5472 | 60 | 32 | ″ |
| `u9336c01` | ″ with contacts | 5504 | 60 | 32 | ″ |

## 11.7 What the 2025 screw variants have instead — and why it matters

`80738` / `u9336` are the September-2025 revision, which replaces the clip lid with a screwed
lid. In the *same pocket*, they carry a screw boss. From `parts/s/u9336s01.dat` lines 13–19:

| Feature | Primitive | Housing coords | Provenance |
|---|---|---|---|
| Screw pilot bore | `4-4cylc` r = 2.5 | **Ø2.000 mm**, x = **±18.000 mm**, z = **−32.800 mm**, heights **4.200 → 12.000 mm** (7.800 deep) | measured |
| Entry counterbore | `4-4ring2` ×1.25 | Ø2.000 → **Ø3.000 mm** annulus at height 4.200 mm | measured |
| Entry lead-in cone | `4-4con4` | heights 3.600 → 4.200 mm | measured |
| Outer edge | `4-4edge` | Ø3.750 mm | measured |

And the clip slot is **gone**: `u9336` has **no z = −86 and no z = −85 face at all** (compare
§5.2), and its z = −80 wall spans y −24…−5 (heights 22.0–29.6 mm) instead of `25560`'s
y −24…+10 (heights 16.0–29.6 mm). The pocket was filled in and a screw column put through it.

**Why this strengthens the negative rather than weakening it:** it shows Philo *does* model
lid-retention hardware when it takes the form of a bore or boss — he modelled the screw column
in full, including its lead-in cone. What he did not model, in any variant, is a **snap
undercut**. That is a consistent, explicable omission (a small internal undercut on a surface
invisible from outside), not an oversight that some other file happens to fix.

It also tells the user something directly useful: **the retention site is that pocket**, in
both generations. The clip catch, whatever its exact profile, lives inside the envelope
established in §5.2.

## 11.8 Is there material there at all? — the wall is ABSENT, not featureless

This is the more informative version of the finding, and it changes how the physical
measurement should be approached.

Restricting to the barb's own band — `x 14…48, y 17.5…22.5` (heights 11.000–13.000 mm) — and
sweeping inboard from the end face to the middle of the part:

```
python3 tmp/ldraw/region_dump.py 25560.dat 14 48 17.5 22.5 -89 -60 --verts
  →  0 triangles with any vertex inside the band
```

The only triangles whose bounding boxes overlap that band are large walls *passing through*
it. Resolving which of them actually cover the barb's footprint:

| Candidate surface | Its y-extent | Covers heights 11–13 mm? |
|---|---|---|
| z = −86.0 (end-wall inner face) | y −3 … +38 | ✔ **yes — present, outboard of the barb** |
| z = −89.0 (outer end face) | y −5 … +41 | ✔ yes (outboard, behind −86) |
| x = ±14, ±48 (slot sides) | diagonal edge (10, −80) → (38, −86) | ✔ yes |
| **z = −80.0 (inboard slot wall)** | **y −10 … +10 only** | ✘ **no — its lowest edge is height 16.000 mm** |
| **z = −77.0 (main inboard wall)** | at the hook width, y ≤ +10 only | ✘ **no** |

So at the barb's height and width, **inboard of z = −86 there is no housing material at all
until z = −30 LDU (−12.000 mm)** — that is, the barb protrudes into the open battery
compartment.

Consequences, stated precisely:

* The barb does **not** pass through solid housing wall — there is no interpenetration. The
  LDraw assembly is geometrically valid.
* The barb does **not** float in an unbounded void either. Outboard of it the end wall's
  inner face at z = **−34.400 mm** is present at this height, sitting **3.200 mm** behind the
  barb's crest (z = −31.200 mm) and only ≈ **0.920 mm** behind the hook's rearmost modelled
  surface — the release-slot outer edge at z = −33.480 mm. The hook is closely backed; it is
  the *inboard* side that is open.
* The surface that would have to carry the catch — the inboard slot wall at z = −32.000 mm —
  **terminates 3.000 mm above the top of the barb** (its lowest edge is at height 16.000 mm;
  the barb tops out at 13.000 mm). The hook's own tip only reaches 13.000 mm.
* Therefore **the LDraw hub is modelled inserted-but-not-latched**: the geometry is
  self-consistent and clash-free, and the latch simply does not engage anything.

**"There is nothing to catch on because the wall stops 3 mm short"** is a materially different
statement from "the wall is there but featureless", and it is the correct one. It means the
physical measurement must capture **two** things, not one: the catch profile *and* how far the
inboard wall actually extends downward on a real part.

## 11.9 Verdict and what the user must measure

**CONFIRMED ABSENT.** The transform is read from the tracked file chain (not inferred) and
corroborated by three independent anchors including a 4-decimal construction artefact shared
between the two parts. The original search box was correctly framed and correctly signed and
did contain the barb volume; only the test was weakened by centroid containment and zero
padding, and re-running with AABB overlap and ±3 mm padding returns **zero curved or sloped
triangles**. Nine sibling parts were swept; the only geometry any of them adds in that volume
is a screw boss belonging to a different lid design. The user's physical measurement **is
justified**.

What to measure on a real `88012`, with the LDraw-established envelope to work inside:

| # | Measure | LDraw-established constraint it must fit |
|---|---|---|
| M1 | The catch profile on the inboard face of the latch pocket — depth, ramp angle, and its height above the hub's bottom face | must engage a Ø2.000 mm bead centred at height **12.000 mm**, protruding inboard to z = **−31.200 mm** |
| M2 | **How far down the inboard wall at z = −32.000 mm actually extends** | LDraw stops it at height 16.000 mm; on the real part it must reach at least ~13.000 mm or the catch cannot exist there |
| M3 | Pocket depth in Z at the catch height | LDraw gives z −34.400 … −32.000 mm (2.400 mm) at heights 16.0–21.2 mm, opening to −34.400 mm-only below that |
| M4 | Whether the catch spans the full 13.600 mm hook width or is a local rib | pocket sides are fixed at \|x\| 5.600 and 19.200 mm |

Dimensions that do **not** need measuring — LDraw gives them, and both parts agree: hook width
**13.600 mm**, hook spacing **11.200 mm**, pocket side walls \|x\| **5.600 / 19.200 mm**, outer
pocket face z **−34.400 mm**, pocket ceiling height **16.000 mm**, finger windows
**13.600 × 3.600 mm** at heights 0–3.600 mm.

## 11.10 Reproducing the re-verification

```
grep -n '^1 ' parts/22127.dat parts/25561c01.dat parts/25560c01.dat   # the transform chain
sed -n '132p' parts/s/24853s01.dat                                    # the barb primitive

# corrected search — AABB overlap, +/-3 mm padding
python3 tmp/ldraw/region_dump.py 25560.dat 6.5 55.5 10 30 -90.5 -70.5

# barb band only, strict vertex-inside test
python3 tmp/ldraw/region_dump.py 25560.dat 14 48 17.5 22.5 -89 -60 --verts

# sibling sweep
for P in 25560.dat 25560c01.dat 24851.dat s/24851s01.dat s/24851s02.dat \
         80738.dat 80738c01.dat u9336.dat u9336c01.dat 25561.dat; do
  python3 tmp/ldraw/region_dump.py "$P" 6.5 55.5 10 30 -90.5 -70.5
done

# clip slot vs screw variant
python3 tmp/ldraw/housing_probe.py faces u9336.dat z
python3 tmp/ldraw/housing_probe.py faces 25560.dat z
```

`region_dump.py` was **rewritten** for this audit: it now tests **AABB overlap** rather than
centroid containment, reports the axis-aligned planes present with per-plane triangle counts,
and explicitly reports the count of **non-axis-aligned** triangles — which is the number that
actually decides whether a catch feature exists. `--verts` adds a strict "at least one vertex
inside the box" mode. Any future absence claim in this document should be made with this tool,
not with a centroid test.

---

# 12. THE TONGUE END ("leg retainer") — §A–D audit

**Headline: retention at the tongue end IS present and IS fully modelled — but it is a
sliding lap/rebate, not a snap.** There is no undercut, lip or detent anywhere in it.

Same transform as §11 (`y_h = y_l + 50` LDU, pure translation, three independent anchors);
no re-derivation. All heights below are **mm above the hub's bottom face**.

## 12.1 Method note — why occupancy here is argued from the mate, not measured

Two geometric occupancy probes were built and **both were rejected on calibration**:
`inside_test.py` (ray parity) and a new `occupancy.py` (BFC-aware nearest-hit normal). On
points whose answer is known independently — inside the 0.8 mm side wall, inside an arm, in
the open hub cavity — the BFC probe returned split votes (5/6, 2/6, 2/5). LDraw parts are
rendering surfaces, not solids: they carry one-sided sheets, untrimmed overlaps and
deliberately unmodelled hidden faces, so no ray method can be trusted here.

Occupancy below is therefore established by the **mating-part argument**: where the housing
and the lid each carry a face on the *same plane with the same x/z footprint*, they are
mating faces, the two solids lie on opposite sides, and the side each occupies follows from
which part's other faces bound it. This is stated as **derived** wherever it is not directly
observed. `occupancy.py` is left in `tmp/ldraw/` with its calibration failure documented in
its docstring — do not use it for verdicts.

## 12.2 (A) What the housing presents opposite each lid feature

Lid features from `2026-08-19-poweredup-hub-battery-box_ldraw-parts-geometry.md` §1.5, re-read at source in `24853s01.dat`
(lines 42–79) and confirmed.

| # | Lid feature (housing coords) | Housing counterpart | Dimensions | Provenance |
|---|---|---|---|---|
| T1 | **Tongue A** (inner pair), \|x\| 0.800…15.600 mm, heights 0…1.2 (top ramping to 1.874), reaching z = 33.378 mm | **Slot** through the end structure | side walls at \|x\| = **0.800** and **15.600** mm, heights **0…4.800**, z **32.000…33.378**; ceiling at height **4.800** | measured (`rect3` ×4, L329–332, L343) |
| T2 | **Tongue B** (outer pair), \|x\| 17.200…26.000 mm, heights 0…1.200, reaching z = 33.378 mm | **Slot** | side walls at \|x\| = **17.200** and **26.000** mm, heights 0…4.800, z 32.000…33.378; partial ceiling at 4.800 over \|x\| 17.2…19.2 and 23.2…26.0 | measured (L336, L337) |
| T3 | Ribs between the slots | solid, reaching the bottom face | \|x\| **15.600…17.200** and **26.000…28.000** mm | measured (bottom-rim strips at height 0, z 32.000…33.378) |
| T4 | **Tongue tip**: 0.926 mm blade, heights **1.874…2.800**, z **33.378…34.400**, \|x\| ≤ 15.600 | ⭐ **REBATE** — a ledge under it and a back wall in front of it | ledge top face at height **1.874** (x 0.8…15.6, z 33.378…34.400); back wall at z = **34.400** rising to height 21.200; side walls \|x\| 0.800/15.600 over heights 1.874…21.200 | measured (L345, L347, L351, L352, L360) — **coincident with the lid's own face at height 1.874 (`24853s01` L43)** |
| T5 | (no lid feature) | second ledge for the outer band | top face at height **2.674**, \|x\| 17.200…26.000 mm, z 33.378…34.400 | measured (L344, L346) — Tongue B stops at z = 33.378 and does **not** enter it; it acts as an end-stop face only |
| T6 | Lid inner ledge, top at height **2.800**, z 32.400…34.400 | slot ceiling at height **4.800** | **2.000 mm clearance** — not a mating face | measured |
| T7 | **6 locating teeth**, 1.200 mm wide, heights 1.600…2.800, z 31.200…32.400, at \|x\| 0.8–2.0 / 7.6–8.8 / 14.4–15.6 mm | **NOTHING** | housing: **0 triangles** in x 0…28.0, heights 1.2…2.8, z 31.0…32.6 apart from the slot side walls. Tray `24849`: **0 triangles** in the same band | measured — absent from **both** mating parts |
| T8 | **1.600 mm locating groove**, full width, z 30.000…31.200, floor at height 1.600 | **NOTHING in the housing** — it is a **tray** feature | tray `24849` presents its bottom rim (height **1.600**, 4 tris) and its +Y end-wall outer face (z = **30.800**, 4 tris) into it | measured — the groove is the **tray-to-lid** seat, not a housing interface |
| T9 | (exterior) | **R3.600 mm rounded bottom-outer edge**, full width | `3-16cyli`/`3-16cylo` r = 9 LDU, axis ∥ X, centred at (height **3.326**, z **32.000**); sweeps from (height 0, z 33.378) to (height 3.326, z **35.600**) | measured (`24851.dat`) |

**Two findings worth pulling out of the table:**

* **The lid's 6 locating teeth engage nothing.** Not the housing, not the tray. They are the
  moulded transition between the lid's ledge and its groove — anti-sink / stiffening, or a
  moulding artefact. **Not load-bearing in any modelled interface.**
* **The lid's 1.6 mm groove is not a housing interface at all.** It seats the *tray*. It
  belongs to the tray discussion, not to this layer's top or bottom interface.

## 12.3 (B) Retention verdict — PRESENT, fully modelled, and it is a lap not a snap

### Is there an undercut, lip or detent?

```
python3 tmp/ldraw/region_dump.py 25560.dat -5.5 72.5 35.5 57.5 72.5 93.5   # padded ±3 mm
  → 93 triangles overlap; 6 non-axis-aligned
```

All 6 curved triangles were identified individually. **None is at the tongue.** They are:
four large sloped wall panels at \|x\| = 27.200 mm (the shell side walls, `24851s01`) and two
`3-16chrd`/`3-16cyli` triangles at \|x\| = 28.000 mm belonging to the exterior bottom-edge
round T9. Every surface that actually forms the tongue interface — slot walls, ceiling,
ledges, back wall — is **axis-aligned planar**.

**So: no ramp, no undercut, no detent, no snap. The tongue end is a pure prismatic lap.**

### But retention IS present, and here is the mechanism

The lid's tongue tip is a 0.926 mm blade occupying heights **1.874…2.800 mm**. The housing's
ledge occupies heights **0…1.874 mm** over the identical x/z footprint. The blade therefore
**rests on the ledge**:

| Lid motion at the tongue end | Constrained by | Result |
|---|---|---|
| **Down / out of the hub** (−height) | the blade bears on the ledge top at height 1.874 | ✔ **BLOCKED — this is the retention** |
| **Further in** (+Z) | blade front face butts the back wall at z = 34.400 | ✔ blocked (hard stop / insertion datum) |
| **Out** (−Z, sliding) | nothing at this end | ✘ free — the tongue simply withdraws |
| **Up** (+height) | nothing until the slot ceiling at 4.800 mm | ✘ free (2.0 mm of slop) |
| **Sideways** (±X) | slot side walls at \|x\| 0.800 / 15.600 / 17.200 / 26.000 | ✔ located |
| **Rotation about the tongue** (lifting the far end) | nothing | ✘ free — the blade swings up out of the rebate |

This is exactly why the latch exists at the other end: **the tongue rebate blocks translation
but not rotation.**

### Contrast with the latch end — why this negative/positive split is credible

| | Latch end (§11) | Tongue end (§12) |
|---|---|---|
| Coincident mating faces between lid and housing? | **none** | **yes** — height 1.874 plane, identical x/z footprint, opposite outward normals |
| Curved/sloped triangles in the padded search volume | **0** | 6, all identified, **none at the interface** |
| Feature type | snap (undercut) | lap (prismatic step) |
| Modelled in LDraw? | **NO** | **YES** |

An undercut is a small internal feature on a face invisible from outside — routinely omitted.
A prismatic step is part of the part's own visible section — and it is here, complete.

### Honest caveat on one face

The ledge's **own bottom face** (height 0, x 0.8…15.6 mm, z 33.378…34.400 mm) is **not
modelled**: the housing's height-0 plane stops at z = 33.378 mm. The ledge's existence and its
0…1.874 mm occupancy are therefore **derived** — from the coincident mating faces plus
non-interpenetration with the lid — not directly observed. Every other face of the rebate
(top, back wall, both sides, inboard end) *is* directly observed. This is a
"one-face-short-of-direct" derivation, not a guess, and not the same as the latch end's
"looked and it is not there".

### Sibling sweep at the tongue end

| Part | Overlapping / curved in the tongue box | Has the height-1.874 and 2.674 ledges? | Verdict |
|---|---|---|---|
| `25560`, `25560c01`, `24851` | 42 / 4 (all exterior corner round) | **yes** | rebate present |
| `25561` (top shell) | **0 / 0** | n/a | ruled out |
| `80738`, `80738c01`, `u9336`, `u9336c01` (2025 screw lid) | 47 / **20** | **NO — both ledges deleted** | rebate removed; replaced by a screw |

The 2025 screw revision carries a **second screw boss at this end**: `4-4cylc` r = 2.5 at
`(35, 20, 82)` in `u9336s01` → **Ø2.000 mm pilot, \|x\| = 14.000 mm, z = +32.800 mm, heights
4.200…12.000 mm**, with the same `4-4ring2` counterbore and `4-4con4` lead-in cone as the
latch-end boss (§11.7). Four screws total, two per end.

**This is strong corroboration.** When LEGO moved retention to screws they deleted *both*
clip features together — the latch slot at −Z *and* the tongue rebate at +Z. The rebate is
therefore genuinely a retention feature, not incidental moulding, and unlike the latch catch
it is fully drawn in the clip variant.

## 12.4 (C) Two-wall construction, and what a single wall must provide

### Is it two-wall? Yes.

| Element | Position | Provenance |
|---|---|---|
| Inner wall | z = **32.000 mm**, heights 0…28.0 | measured (z = 80 face, area 7556 LDU²) |
| Outer skin | z = **35.600 mm** from height 3.326 upward; below that the R3.600 round T9 sweeps in to z = 33.378 at height 0 | measured |
| Connecting ribs | \|x\| **15.600…17.200** and **26.000…28.000** mm | measured |
| Cavity between the skins | ≈ **3.600 mm** (32.000 → 35.600) | derived |

Same topology as the latch end: two skins with the lid's feature entering the gap between
them. So the user's single-wall simplification applies here too.

### What the single wall must provide

Only **one** feature is load-bearing. Reproduce this and nothing else:

| Must reproduce | Value | Why |
|---|---|---|
| **The rebate** — wall inner face at z = **33.378 mm** for heights **0…1.874 mm**, stepping back to z = **34.400 mm** above | step depth **1.022 mm**, step height **1.874 mm** | this *is* the retention (blade rests on the 1.874 ledge) |
| Its width | \|x\| ≤ **15.600 mm** (or simply run it full width — simpler and harmless) | matches the lid's tongue tip |
| Back wall | z = **34.400 mm** | +Z hard stop / insertion datum |
| X location | slot walls at \|x\| = 0.800 / 15.600 / 17.200 / 26.000 mm | **optional** — the hub's own side walls at \|x\| 27.200 already locate the lid in X; these only tighten it |

| Can be dropped | Why |
|---|---|
| **The 6 locating teeth** | engage **nothing** in either mating part (T7). Not load-bearing. Drop. |
| **The 1.6 mm locating groove** | a *tray*-to-lid feature, not a housing interface (T8). Keep only if the tray design still needs it. |
| The second ledge at height 2.674 (outer band) | receives nothing; it is just the outer tongues' end-stop face — a plain wall face does the same job |
| The 4.800 mm slot ceiling | 2.0 mm clear of the lid; pure moulding relief |

### Wall thickness — the tongue end does NOT have the latch end's problem

This is the important asymmetry, and it is good news.

* At the **latch end**, the catch is an **undercut**: material must overhang a void, so the
  wall carrying it must be thicker than the ~1.0 mm engagement depth *plus* a back
  thickness ⇒ local thickening to ≈ 2 mm is unavoidable.
* At the **tongue end**, the rebate is a **step, not an undercut**: the wall is *thicker*
  below height 1.874 mm and *thinner* above it. The step removes material going upward, so
  it imposes **no thickness floor at all**.

Keeping LEGO's own planes (outer face 35.600, inner face 34.400 above the step, 33.378
below) gives a wall of **1.200 mm above the step and 2.222 mm below** it — 1.200 mm is three
perimeters at a 0.4 mm nozzle, printable as-is. If a thicker upper wall is wanted, move the
*inner* face inward (the outer face at 35.600 mm is the housing's Z envelope and must not
move), accepting a correspondingly shallower rebate and shortening the lid blade to match.

### Printability, outer face on the bed

| Feature | Overhang behaviour | Support? |
|---|---|---|
| **The rebate step** at height 1.874 | material is *removed* going up — a receding step | ✅ **none needed; self-supporting** |
| Slot side walls, back wall, ceiling | vertical / upward-facing | ✅ none |
| Slot ceiling at height 4.800 mm | a 15.6 mm-wide downward-facing span | ⚠️ bridged, or drop the ceiling entirely (it is non-functional, see above) |
| **T9 exterior R3.600 bottom-edge round** | flares outward from z 33.378 at height 0 to 35.600 at height 3.326 — the surface starts at only **22.5° from horizontal** | ⚠️ **worst overhang at this end.** Replace with a 45° chamfer, or accept droop |

**Verdict: single-walling the tongue end is genuinely easier than the two-wall original, and
easier than the latch end.** The one retention feature is self-supporting in the intended
orientation, needs no local thickening, and needs no support. The only printability item to
decide is the exterior corner round T9 — and that is a cosmetic edge treatment, not a
retention feature.

## 12.5 (D) How the lid is actually retained — the one-sentence statement

> **The lid slides in tongue-first at the +Z end, where a 0.926 mm blade on its leading edge
> enters a rebate and comes to rest on a ledge 1.874 mm above the hub's bottom face — that
> ledge is what stops that end dropping out; the lid then swings down at the −Z end, where two
> 13.600 mm-wide cantilever fingers, 11.200 mm apart, snap their Ø2.000 mm barbs into catches
> at height 12.000 mm; the lid is thus trapped between a sliding lap at one end and a snap at
> the other, and is released by pressing the two thumb pads through the 13.600 × 3.600 mm
> finger windows and swinging that end down.**

Checks on that statement:

* The tongue rebate blocks translation but **not** rotation — so the latch is load-bearing,
  not merely a convenience. Removing it would let the lid swing open about the tongue.
* The barbs block the lid sliding back out in −Z as well as dropping at their own end; the
  tongue end provides no −Z constraint at all.
* Both retention features vanish together in the 2025 screw revision (§11.7, §12.3), which
  confirms they are one scheme, not two independent ones.
* **Our derived design reproduces this function** provided both halves are built: the rebate
  (fully specified above from LDraw) and the catch (derived from the lid's barb, since LDraw
  omits it — §11). Building only one of the two gives a lid that either falls out or cannot
  be fitted.

## 12.6 Reproducing §12

```
# housing features opposite the lid tongue / teeth / groove
python3 tmp/ldraw/region_dump.py 25560.dat -5.5 72.5 35.5 57.5 72.5 93.5   # tongue, padded
python3 tmp/ldraw/region_dump.py 25560.dat 0 70 43 47 77.5 81.5            # teeth band
python3 tmp/ldraw/region_dump.py 25560.dat 0 70 45 47.5 74.5 78.5          # groove band
python3 tmp/ldraw/region_dump.py 24849.dat 0 70 -7 -3 77.5 81.5            # tray vs teeth
python3 tmp/ldraw/region_dump.py 24849.dat 0 70 -5 -2.5 74.5 78.5          # tray vs groove

# the mating faces that establish the rebate
python3 tmp/ldraw/region_dump.py 25560.dat 2 39 45.3 50.1 83.4 86.1 --verts
python3 tmp/ldraw/region_dump.py 24853.dat 2 39 -4.7 0.1 83.4 86.1 --verts

# sibling sweep + does the screw variant keep the ledges?
for P in 25560.dat 24851.dat 80738.dat u9336.dat 25561.dat; do
  python3 tmp/ldraw/region_dump.py "$P" -5.5 46.5 41 51 82 88; done
python3 tmp/ldraw/housing_probe.py faces u9336.dat y     # no 43.3151 / 45.3151 rows
```
