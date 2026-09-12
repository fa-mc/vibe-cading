# LDraw geometry extraction — LEGO Powered Up Technic Hub (88012) battery lid & tray

Source: LDraw official library, `tmp/ldraw/full/ldraw/parts/`.
Parts: `24853.dat` (+ `s/24853s01.dat`, `s/24853s02.dat`), `24849.dat`, `24849c01.dat`.
Author Philippe Hurbain [Philo], CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). **Dimensions read as facts; no converted
geometry is committed.**

**Provenance note.** Tracked design-record artifact (moved from git-ignored `tmp/` per the
phase-4 TL review, `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md` §TL
Review — CURRENT, finding B2). Own measurements and prose analysis of the cited LDraw parts,
not converted geometry or `.dat` file content.

Extraction method: recursive type-1 reference resolution with matrix composition
(`tmp/ldraw/analyze.py`, extends `tmp/ldraw/measure.py`) → triangle soup → axis-aligned
face maps + planar cross-sections + direct reading of the `.dat` primitive references.
Both approaches were cross-checked against each other.

---

## 0. Coordinate frames

| | |
|---|---|
| Unit | 1 LDU = 0.4 mm; stud pitch 20 LDU = 8.0 mm; brick height 24 LDU = 9.6 mm |
| LDraw vertical axis | **Y**, and **−Y is up** |
| Hub placement | `22127.dat` places **both** `24849` and `24853` at translation `(0, 50, 0)`, identity rotation — so lid and tray share one local frame, offset only in Y |
| Hub envelope | 72.0 × 71.2 × 40.0 mm; hub Y spans −50…+50 LDU, so **hub Y = +50 LDU is the hub's bottom face** |

**Lid local origin `(0,0,0)`**: X = 0 is the plate's mid-width (plate is symmetric in X);
Y = 0 is the **outer / bottom face plane** (flush with the hub's bottom exterior);
Z = 0 is ~0.6 mm off the plate's mid-length (plate spans Z −77…+80 LDU).

**Tray local origin `(0,0,0)`**: X = 0 mid-width (symmetric); Y = 0 coincides with the lid's
**outer** face plane (i.e. the tray's own structure starts 1.6 mm above it, at Y = −4 LDU);
Z = 0 near mid-length (tray spans Z −77…+82 LDU).

**Recommended CadQuery mapping** (right-handed, Z up, outer face of lid on the bed):

```
cq_x =  ldraw_X * 0.4      cq_y = ldraw_Z * 0.4      cq_z = -ldraw_Y * 0.4
```

With that mapping the lid's outer face sits at `cq_z = 0` and all its features extrude
into +Z — consistent with the project's Absolute Zero-Datum rule.

**All mm figures below are in this CQ frame unless the LDU column says otherwise**
(i.e. `z` = height above the lid's outer face, `y` = LDraw Z).

---

## 1. Part A — Battery lid `24853`

Envelope (resolved): **54.400 × 70.000 × 13.000 mm** (X × LDraw-Z × height).

### 1.1 Plate

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Plate outline | rectangle, X −27.2…+27.2, Y −30.8…+32.0 | ±68, −77…+80 | measured (off-grid: 136 × 157 LDU) |
| Plate width | 54.400 | 136 | measured, off-grid (6.8 studs) |
| Plate length (excl. latch tabs) | 62.800 | 157 | measured, off-grid |
| Plate thickness | **1.200** | 3 | on-grid-idealized (LEGO nominal wall) |
| Outer (bottom) face | **flat plane at z = 0**, no dish, no step | y = 0 | measured |
| Inner face | flat plane at z = 1.200 | y = −3 | measured |
| Plan-view corners | **sharp** — no corner radii, no plan chamfer | — | measured |

The plate is **flat**, not dished or stepped, over its whole area. The only thickness
variations are two local stiffening bands at the two short ends (§1.4, §1.5).

### 1.2 Through-slots in the plate (the only outer-face feature)

15 rectangular **through-slots** cut the full 1.2 mm plate thickness (LDraw: `box4.dat`
under `BFC INVERTNEXT`, Y-extent exactly 0…−3 LDU, no end caps → through).

| | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Slot width (X) | 0.800 | 2 | measured |
| Column X centres | 0.0, ±7.2, ±14.4 | 0, ±18, ±36 | measured (7.2 mm = 18 LDU, off-grid) |
| Row 1 (Y span) | −22.64 … −16.40 (len 6.240) | −56.6…−41 | measured, off-grid (−56.6!) |
| Row 2 (Y span) | −4.80 … +3.20 (len 8.000) | −12…+8 | measured |
| Row 3 (Y span) | +14.80 … +21.20 (len 6.400) | +37…+53 | measured |

### 1.3 ⚠ Rib families — there is only ONE, and it is on the INNER face

**Finding that contradicts the prior research brief.** The lid has exactly one family of
ribs. It is on the **inner** (battery-facing) face. **The outer/bottom face carries no
ridges of any kind** — it is a flat plane at y = 0 whose only interruptions are the 15
through-slots of §1.2 and the latch aperture of §1.4.

Prior report said "bashing-guard / longitudinal ribs on the outer face, keep these" and
"AA guide ridges on the inner face, delete these". In the LDraw source those are **the
same three ribs**. See §5 for the decision this forces on the Designer.

Proof that the three ribs are AA-cell dividers, not outer bumpers:

* They project in the **−Y (inward)** direction from the plate's inner face — LDraw −Y is
  up, the lid is at the hub bottom, so −Y points into the battery bay.
* Their X centres (−10.8, +3.6, +18.0 mm) sit exactly at the **14.4 mm pitch** of the
  tray's cell corrugation, and exactly midway between the tray's lower-row cell pockets
  (§2.5). 14.4 mm ≈ AA diameter 14.5 mm.
* The tray's own lower-row cell dividers are at X = −10.8 and +3.6 mm — **the same two
  positions**, approaching from above.

| Rib feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Count | 3 | | measured |
| Crest X centres | **−10.8, +3.6, +18.0** | −27, +9, +45 | measured; pitch 14.4 mm = 36 LDU |
| Crest (web) thickness | 0.800 | 2 | measured |
| Height above inner face | **3.600** (z = 1.200 → 4.800) | −3 → −12 | measured, off-grid |
| Length (Y) | 46.400, Y −23.6 … +22.8 | −59…+57 | measured |
| Orientation | runs parallel to LDraw Z (= cell axis) | | measured |
| Flank fillet gussets | concave 45° cove, 3.6 × 3.6 mm, **0.8 mm thick, discrete** | | measured |
| Gusset Y positions | [−23.6,−22.8], [−8.4,−7.6], [+6.8,+7.6], [+22.0,+22.8] | | measured |
| Gusset profile polyline (local, LDU) | (0,−9) → (2.2929,−5.2929) → (5.2929,−2.2929) → (9,0) | | measured; a 45° chord sagged 1 LDU perpendicular ⇒ concave arc R ≈ 18 LDU (7.3 mm) |

Note the gussets are **not** a continuous fillet: subpart `s/24853s02.dat` supplies a
2 LDU (0.8 mm) thick buttress only, chained by coincident end caps. Between gussets the
rib flanks are plain vertical walls.

Asymmetry (real, verified): the **X = +18.0 mm rib has a gusset on its −X side only**. Its
+X flank is a plain vertical wall at X = +18.4 mm (LDU 46), same 3.6 mm height. The other
two ribs are symmetric.

### 1.4 Latch end (LDraw −Z, i.e. cq −Y)

Local stiffening band first: the plate thickens from 1.2 mm to **2.0 mm** (y 0 → −5 LDU)
over Y ∈ [−30.8, −30.0] mm across the full width; end face at Y = −30.8 mm.

Two latch fingers, mirrored about X = 0. **Prior research's numbers verified:**

| Feature | Prior claim | Verified value | LDU | Provenance |
|---|---|---|---|---|
| Count | 2 | **2** ✓ | | measured |
| Hook width (X) | 13.6 mm | **13.600** ✓ (\|X\| 5.6…19.2 mm) | 14…48 | measured, off-grid |
| Gap between hooks | 11.2 mm | **11.200** ✓ (X −5.6…+5.6) | ±14 | measured, off-grid |
| Outer span of the pair | — | 38.400 | 96 | measured |
| Depth | 13.0 mm | **13.000** ✓ **from the outer face** (z = 0 → 13.0); **11.800 from the inner face** | 0…−32.5 | measured — quote the datum! |
| Lip / barb | Ø2.0 mm rounded | **Ø2.000** ✓ — a true cylindrical bead, axis ∥ X | R = 2.5 | measured |
| Barb axis position | — | z = 12.000 above outer face, Y = −32.200 mm | y −30, z −80.5 | measured |
| Barb arc | — | 7/16 circle = **157.5°**, φ = 0° (+Y side, Y = −31.2 mm) → 90° (tip, z = 13.0) → 157.5° (Y = −33.124, z = 12.383) | `7-16cylo` | measured |
| Barb facing direction | — | **protrudes toward +Y (inboard, toward the lid centre)**, ≈ 0.83 mm proud of the arm face | | measured |
| Arm draft angle | — | **≈ 2.0°** (arm's +Y face: Y = −31.840 at z = 0 → Y = −32.240 at z = 11.200) | −79.6 → −80.6 | measured |
| Release aperture | — | **through-slot in the outer face**, 1.640 mm wide, Y ∈ [−33.480, −31.840], over the full 13.6 mm hook width | −83.7…−79.6 | measured |

Structure: each finger is a **cantilever U**. The lid's outer skin continues past the
release slot to Y = −35.6 mm, forming the thumb pad; that pad is joined to the plate
**only** through the hook body, so pressing it flexes the finger and pulls the barb out of
its groove in the hub bottom shell.

Extra detail on the thumb pad (measured, off-grid):

* Plan-view scallop on the outer edge: Y = −35.6 mm for \|X\| 5.6…8.32 mm, ramping to
  Y = −35.2 mm at \|X\| 11.04…13.76 mm, ramping back to −35.6 mm at \|X\| 16.48…19.2 mm.
* Corner chamfer at the tab's X-ends (X 18.4…19.2 mm), and an internal ceiling at
  z = 2.791 mm (LDU −6.9777) over Y ∈ [−35.377, −34.000] — the pad is a thin shell.
* The pad's inner face carries a small boss at z = 4.8…6.8 mm (LDU −12…−17), Y −34.24…−33.84.

### 1.5 Insertion end (LDraw +Z) — a slide-in lip, **not a hinge**

Verified: **not** a hinge, **not** discrete tabs — a stepped **slide-in tongue plus a
full-width inner ledge**. The "shallow 2.8 mm insertion lip" in the prior brief is the
z = 2.800 mm ledge below; that number is right, but it is a ledge height, not a lip depth.

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Full-width plate edge | Y = +32.000 | 80 | measured |
| Locating groove (inner face) | inner face steps 1.200 → **1.600** deep over Y ∈ [30.0, 31.2] mm, full width | y −3→−4, z 75…78 | measured |
| Inner ledge | raised to **z = 2.800** (1.600 mm proud of the inner face) over Y ∈ [32.4, 34.4] mm, \|X\| ≤ 15.6 mm | y = −7, z 81…86 | measured |
| Ledge locating teeth | 6 teeth (3 per half) extend the ledge forward to Y = 31.2 mm; each **1.200 mm wide** at \|X\| = 0.8–2.0, 7.6–8.8, 14.4–15.6 mm | | measured |
| Tongue A (inner pair) | \|X\| 0.8…15.6 mm, plate y 0…−3 extends to **Y = 33.378 mm** | x 2…39, z 83.4443 | measured (off-grid, arc-derived) |
| Tongue B (outer pair) | \|X\| 17.2…26.0 mm, plate y 0…−3 extends to **Y = 33.378 mm** | x 43…65 | measured |
| Tongue tip | \|X\| ≤ 15.6 mm, Y 33.378…**34.400** mm, at z **1.874…2.800** — i.e. **recessed 1.874 mm from the outer face**, tip thickness **0.926 mm** | y −4.6849…−7 | measured |
| Notches between teeth | ledge floor drops back to z = 1.600 over \|X\| ∈ [2.0,7.6] and [8.8,14.4] mm, Y ∈ [31.2, 32.4] | | measured |

**Engagement**: the lid is inserted +Y-first; the 0.926 mm tongue tip, recessed 1.874 mm
from the outer plane, slides **under** the housing's lip; the plate then rotates down and
the two latch barbs snap into the hub bottom shell at the other end. The lid seats laterally
on the 1.600 mm groove at Y ∈ [30.0, 31.2] mm.

### 1.6 Draft, chamfers, fillets on the lid

| Item | Value | Provenance |
|---|---|---|
| Latch arm draft | ≈ 2.0° on the +Y face | measured |
| Latch barb | full R1.0 mm bead (157.5° of arc) | measured |
| Rib flank cove | concave, R ≈ 7.3 mm equivalent, 3.6 mm run | measured |
| Latch tab X-end corner chamfer | ≈ 0.8 mm | measured |
| Plate perimeter fillets/chamfers | **none modelled** | absent |
| General mould draft | **not modelled** anywhere else | absent (LDraw convention) |

---

## 2. Part B — Battery tray `24849` / `24849c01`

Envelope (resolved, both variants identical): **56.800 × 63.600 × 28.000 mm**.
LDraw X ±71, Y 0…−70, Z −77…+82.

### ⚠ 2.0 Trustworthiness — read before using any number below

`24849.dat` carries, immediately after its header and **before every geometry line**:

```
0 // Internal structure is simplified
```

The comment therefore scopes the **whole part**, and it is empirically confirmed:

* The "cell cradles" are a 0.8 mm corrugated sheet of only **1.28 mm** amplitude. Real AA
  cradles need ≈ 7 mm of scallop. This is a stylised stand-in.
* The cell dividers are only **2.0 mm** tall. Real dividers separating AA cells need ≈ 7 mm.
* `24849c01` models exactly **two** contact plates. A 6-cell series pack needs at least
  seven contact features. The rest are simply absent.
* The two compartment heights (12.560 and 12.160 mm) are **less than an AA diameter**
  (14.5 mm) — geometrically impossible for a real tray, and proof the internal Y levels
  were idealised, not traced.

**Trustworthy (traced from the real part — outer / user-visible surfaces):**
outer envelope, side wall thicknesses, the **side extraction tabs and their grip ribs**,
the end walls, top/bottom rim positions, the +Z guide rails.

**NOT trustworthy (simplified):** corrugated shelf amplitude and exact Y levels, cell
divider heights, cell-pocket X centres to better than ±1 LDU, contact geometry, internal
stiffener detail. Use these for *topology and intent*, and re-derive the actual clearances
from the LiPo pack, not from these numbers.

The 14.4 mm corrugation **pitch** and the 51.2 mm cell-bay **length** are, by contrast,
functionally constrained and consistent with an AA cell (Ø14.5 × 50.5 mm) in a staggered
two-row pack (row offset 14.5·√3/2 = 12.557 mm ≈ the measured 12.560 mm). Treat pitch and
length as reliable; treat depths as simplified.

### 2.1 Cell architecture (for context — all of this is to be removed)

6 AA cells, axes along LDraw Z, in **two staggered rows of 3**, separated by the corrugated
shelf. Lower row rests directly on the lid. Row X centres (LDraw LDU → mm):

* Lower row: X ≈ **−18.2, −3.6, +10.6 mm** (LDU −45.5, −9, +26.5)
* Upper row: X ≈ **−10.8, +3.6, +18.0 mm** (LDU −27, +9, +45) — directly above the lid ribs

### 2.2 Outer shell

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Side wall, outer face | X = ±27.200 | ±68 | measured |
| Side wall, inner face | X = ±26.400 | ±66 | measured |
| Side wall thickness | **0.800** | 2 | measured |
| Side wall vertical extent | z ≈ 1.6 … 22.4 (LDraw y −4…−56) | | measured |
| Bottom rim plane | z = **1.600** (LDraw y = −4) | −4 | measured |
| Top frame plane | z = 27.600 / 28.000 (LDraw y −69 / −70) | | measured |
| −Y end wall | Y −30.400 … −28.800, **1.600 thick**, X ±26.4, full height | z −76…−72 | measured |
| −Y outer skin lip | Y = −30.800 | −77 | measured |
| +Y end wall | inner face Y = **+29.200** (lower compartment) / **+29.600** (upper); outer Y = **+30.800**; 1.2–1.6 thick | 73 / 74 / 77 | measured |
| +Y guide rails (protrude to Y = 32.800) | horizontal rail X ±(18.4…25.6), z 3.2…4.4; vertical rail X ±(20.8…22.0), z 4.4…13.6 | z 77…82 | measured |
| Top corner rounds | R 1.600, axis ∥ Z, at the four top-outer corners | `1-4cylo` r4 | measured |

### 2.3 ★ Side extraction tabs — MUST BE KEPT

One on each side face (X = +27.2 mm and X = −27.2 mm), mirror-symmetric, and symmetric in
Y about Y = 0. This is the feature the user explicitly wants preserved.

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| Pad face | X = **±28.000** — i.e. **0.800 mm proud** of the side wall | 70 | measured |
| Pad extent (Y) | −12.000 … +12.000 (24.000 long) | ±30 | measured, off-grid |
| Pad extent (z, above lid outer face) | **0.000 … 7.200** | y 0…−18 | measured |
| Finger ledge | X = **±28.400** — **1.200 mm proud** — over z 7.200…8.400, Y ±8.400 | 71; y −18…−21 | measured |
| Ledge underside | flat, z = 8.400 (LDraw y = −21), X 27.2…28.4 | | measured |
| Corner rounds | **R 3.600**, axis ∥ X, centred (z = 4.800, Y = ±8.400), sweeping to z 8.400 / Y ±12.000 | `1-4cylo` r9 | measured |
| Recess in the ledge face | R 2.400 quarter-round, 0.400 mm deep (X 28.0→28.4) at each corner | `1-4cylo` r6 + `1-4ring2` | measured |
| **Grip rib 1** | X = ±**28.320** (0.320 mm proud of the pad), z **1.920…2.880** (0.960 tall), Y ±8.800 (17.600 long) | 70.8; y −4.8…−7.2 | measured, off-grid |
| **Grip rib 2** | X = ±**28.320**, z **3.920…4.880** (0.960 tall), Y ±8.800 | y −9.8…−12.2 | measured, off-grid |
| Rib root chamfer | 0.320 mm run at X 28.0→28.32 (`rect2p` transition faces at each rib edge) | | measured |

**How a finger engages it**: the tab pad projects 0.8 mm outboard of the tray's side wall
and 1.2 mm at the bottom ledge, into the clearance between the tray and the hub's bottom
pocket. The lid is only ±27.200 mm wide, so **the tabs sit exactly outboard of the lid** and
become exposed the instant the lid is removed. The 1.2 mm ledge at z = 7.2…8.4 mm gives a
fingernail/fingertip a positive undercut to pull down on; the two 0.32 mm grip ribs at
z ≈ 2–5 mm give friction. All of this reads as **traced from the real part** (0.32 / 0.96 /
2.4 mm are off-grid values that no idealisation would produce).

### 2.4 Cell dividers / partitions — MAP FOR REMOVAL

Four longitudinal divider walls, LDraw primitive `box3u2p` (a U-channel: tip face + two
side faces, open at both ends and at the root):

| # | X centre (mm) | X span (mm) | Side of shelf | z span (mm) | Length (mm) | Provenance |
|---|---|---|---|---|---|---|
| 1 | **−10.800** | −11.400 … −10.200 | below (into lower row) | 11.760 … 13.760 | 51.200 (Y ±25.6) | simplified |
| 2 | **+3.600** | +3.000 … +4.200 | below | 11.760 … 13.760 | 51.200 | simplified |
| 3 | **−3.600** | −4.200 … −3.000 | above (into upper row) | 15.840 … 17.840 | 51.200 | simplified |
| 4 | **+10.800** | +10.200 … +11.400 | above | 15.840 … 17.840 | 51.200 | simplified |

Thickness 1.200 mm, height 2.000 mm each. **Height is simplified** (real part must be
much taller). Positions are on the 14.4 mm cell pitch and are reliable as *positions*.

Two **transverse** partitions (these bound the cell bay lengthwise):

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| −Y partition | Y −26.800 … −25.600, thickness **1.200**, X ±26.4, z 1.800…27.600 | −67…−64 | measured |
| +Y partition | Y +25.600 … +26.800, thickness **1.200**, X ±26.4, z 1.800…27.600 | 64…67 | measured |
| Cell bay clear length | **51.200** (Y −25.6 … +25.6) | 128 | measured |

Two **longitudinal channel walls** (wiring routes, diagonal to each other):

| Feature | Value (mm) | LDU | Provenance |
|---|---|---|---|
| +X channel wall | X +19.200 … +20.400 (1.200 thick), z 1.600…13.760 (**lower** compartment only), Y −28.8…+29.2 | 48/51 | measured |
| −X channel wall | X −20.800 … −19.600 (1.200 thick), z 15.840…27.600 (**upper** compartment only), Y −28.8…+29.6 | −52/−49 | measured |
| Side stiffener ribs | 1.200 thick plates at Y = ±(15.200…16.400), inside the side channels (X −26.0…−20.8 and +20.4…+25.6), z 7.400…22.200 | ±38/±41 | simplified |

### 2.5 Corrugated shelf (the "false floor") — MAP FOR REMOVAL

A single 0.800 mm thick corrugated sheet spanning X ±26.400, Y −28.800 … +29.600.

| Face | z levels (mm) | LDraw y | Provenance |
|---|---|---|---|
| Lower face (lower-row ceiling) | alternates **13.760 / 15.040** | −34.4 / −37.6 | simplified |
| Upper face (upper-row floor) | alternates **14.560 / 15.840** | −36.4 / −39.6 | simplified |
| Corrugation pitch | **14.400** | 36 | measured (= AA Ø) |
| Corrugation amplitude | **1.280** | 3.2 | simplified (real ≈ 7 mm) |
| Row-to-row offset | **12.560** | 31.4 | measured (= 14.5·√3/2) |

Lower-row pockets (lower face at 15.040) centred X = **+10.6, −3.6, −18.2 mm**.
Upper-row seats (upper face at 14.560) centred X = **+18.0, +3.6, −10.8, (−24.8) mm**.

### 2.6 Floor — there is NONE

Confirmed by face-area accounting: the y = −4 LDU plane (z = 1.600 mm) carries only
2 094 LDU² of face out of a 20 944 LDU² footprint (**10 %**), and every one of those faces
is a peripheral strip:

| Rim segment | Extent (mm) | Provenance |
|---|---|---|
| +X rim | X 25.600 … 27.200, full length | measured |
| −X rim | X −27.200 … −26.400, full length | measured |
| −Y rim | Y −30.400 … −28.800, full width | measured |
| +Y rim | Y +29.200 … +30.800, full width | measured |
| Transverse-wall feet | z 1.600…2.000 at Y ±(25.6…26.8), X ±22.8 | measured |

So the lower compartment is **completely open at the bottom** — the AA cells rest directly
on the lid's inner face and on the lid's three 3.6 mm ribs. Adding a floor, as the user
wants, is a genuine addition, not a modification.

The top is likewise open apart from a peripheral frame at z = 27.600 / 28.000 mm
(X ±23.200, Y −30.400…+30.800) — the hub's top shell `25561` closes it.

### 2.7 "Two walls at one end" — disambiguation with numbers

The LiPo is 58 × 32 × 20 mm. Measured tray clearances:

| Dimension | Available (mm) | Needed | Verdict |
|---|---|---|---|
| Width (X, wall-to-wall) | **52.800** (X ±26.400) | 32 | ✔ comfortable |
| Height (z, bottom rim → top frame) | **26.400** (1.600 → 28.000) | 20 | ✔ **only if the corrugated shelf AND all 4 dividers are deleted** — each compartment alone is 12.16 / 12.56 mm |
| Length (Y), cell bay as-is | **51.200** (Y ±25.600) | 58 | ✘ 6.8 mm short |
| Length, remove +Y partition only | 54.800 (Y −25.6 … +29.2) | 58 | ✘ 3.2 mm short |
| Length, remove +Y partition **and** +Y end wall | 56.400 (Y −25.6 … +30.8) | 58 | ✘ 1.6 mm short |
| Length, **remove BOTH transverse partitions** (keep both end walls) | **58.000** (Y −28.800 … +29.200) | 58 | ✔ **exact** |

**Recommendation to the Designer**: the only interpretation that yields the stated 58 mm is
**delete the two transverse partitions at Y = ±(25.6…26.8) mm** — one at each end — keeping
the outer end walls at Y = −30.4…−28.8 and +29.2…+30.8. That gives exactly 58.000 mm of
clear length with zero slack, so a real strap-retained pack will need the end walls thinned
or a 1–2 mm relief pocket; flag this to the user.

If the user genuinely means *one* end (both the partition and the end wall at +Y), the clear
length is 56.400 mm and the pack will not fit without further material removal. **Ask.**

### 2.8 Electrical contacts (in `24849c01` only) — EXCLUDE

`24849c01.dat` = `24849.dat` + two `box.dat` instances in LDraw colour 494 (electric contact).

| Contact | X (mm) | z (mm) | Y (mm) | Provenance |
|---|---|---|---|---|
| 1 | −5.200 … +2.800 (8.000 wide) | 16.000 … 28.000 (12.000 tall) | 29.200 … 29.600 (0.400 thick) | simplified |
| 2 | −19.600 … −11.600 | 16.000 … 28.000 | 29.200 … 29.600 | simplified |

Both sit in the **upper** compartment at the +Y end. Only two of the ≥7 real contacts are
modelled — treat as a marker for "contacts live here", not as geometry.

---

## 3. Grid check summary

| Dimension | mm | LDU | On/off grid |
|---|---|---|---|
| Lid plate width | 54.400 | 136 | off-grid (6.80 studs) — measured |
| Lid plate length | 62.800 | 157 | off-grid — measured |
| Lid / tray wall thickness | 1.200 / 0.800 | 3 / 2 | LEGO-standard idealized |
| Latch hook width | 13.600 | 34 | off-grid — measured |
| Latch hook gap | 11.200 | 28 | off-grid (1.4 studs) — measured |
| Latch depth from outer face | 13.000 | 32.5 | off-grid (half-LDU!) — measured |
| Latch barb Ø | 2.000 | 5 | round number, idealized |
| Rib / cell pitch | 14.400 | 36 | off-grid (1.8 studs) — measured, = AA Ø |
| Rib height | 3.600 | 9 | off-grid — measured |
| Tray extraction-tab proud | 0.800 / 1.200 | 2 / 3 | idealized |
| Grip rib proud / tall | 0.320 / 0.960 | 0.8 / 2.4 | **sub-LDU, off-grid — caliper-traced** |
| Tray envelope | 56.800 × 63.600 × 28.000 | 142 × 159 × 70 | off-grid — measured |
| Cell bay length | 51.200 | 128 | off-grid (6.4 studs) — measured |
| Row offset | 12.560 | 31.4 | off-grid, = 14.5·√3/2 — measured |
| `83.4443`, `−4.6849`, `−6.9777`, `−30.9568`, … | | | **construction artefacts** (points on arcs / 45° chamfers), not independent measurements — do not treat as design intent |

---

## 4. Explicitly ABSENT / NOT MODELLED

* **Any ridge, rib or boss on the lid's outer (bottom) face.** The outer face is a flat
  plane; the only interruptions are 15 through-slots and the 1.64 mm latch release slot.
* Mould draft anywhere except the ≈2° on the latch arm's +Y face.
* Edge fillets/chamfers on the lid perimeter and on the tray's rectangular internals.
* Real AA cradle scallops in the tray (replaced by a 1.28 mm corrugation).
* 5 of the ≥7 electrical contacts, all spring contacts, all wiring.
* Any hinge feature on the lid — the +Z end is a slide-in tongue, there is no pivot.
* Ejector-pin marks, gate marks, part-number embossing.

---

## 5. Designer decision list

### OMIT (delete from the re-model)

| # | Feature | Where | Ref |
|---|---|---|---|
| O1 | The **3 AA-cell divider ribs** on the lid's inner face (crest + 4 gussets each) | lid, X = −10.8 / +3.6 / +18.0 mm, z 1.2→4.8 | §1.3 |
| O2 | The plain vertical wall at lid X = +18.4 mm (the +X flank of rib 3) | lid | §1.3 |
| O3 | The **4 longitudinal cell dividers** | tray, X = −10.8, −3.6, +3.6, +10.8 mm | §2.4 |
| O4 | The **corrugated shelf** (mandatory — a 20 mm pack cannot fit either 12 mm compartment) | tray, z 13.76…15.84 | §2.5 |
| O5 | The **two transverse partitions** at Y = ±(25.6…26.8) mm — required to reach 58.0 mm | tray | §2.7 |
| O6 | The **two electrical contacts** in `24849c01` | tray +Y end, upper compartment | §2.8 |
| O7 | The side stiffener rib plates at Y = ±(15.2…16.4) mm (they intrude into the pack volume) | tray side channels | §2.4 |

### KEEP (carry into the re-model)

| # | Feature | Where | Ref |
|---|---|---|---|
| K1 | **Both latch fingers** with the Ø2.0 mm barb, 13.6 mm wide, 11.2 mm apart, 13.0 mm deep from the outer face, barb facing +Y, 2° arm draft, 1.64 mm release slot | lid −Y end | §1.4 |
| K2 | **The slide-in tongue + inner ledge + 6 locating teeth + 1.6 mm locating groove** | lid +Y end | §1.5 |
| K3 | The flat 1.2 mm plate and its rectangular outline | lid | §1.1 |
| K4 | The 15 through-slots — **the only candidate for the "bashing guard / longitudinal ribs" the user asked to keep**; see the flag below | lid | §1.2 |
| K5 | **Both side extraction tabs**: 0.8 mm pad + 1.2 mm finger ledge + R3.6 mm corners + 2 grip ribs (0.32 × 0.96 × 17.6 mm) | tray X = ±27.2 mm | §2.3 |
| K6 | Tray outer shell, 0.8 mm side walls, both end walls, top frame, +Y guide rails | tray | §2.2 |
| K7 | Bottom rim at z = 1.600 mm (the new floor should be built onto this datum) | tray | §2.6 |

### ⚠ Flag to raise with the user before design freeze

The brief said "remove the AA guide ridges on the inner face, keep the bashing-guard ridges
on the outer/bottom face." **The lid has no outer-face ridges.** All three ribs are inner-face
AA dividers and are structurally identical. Ask the user to confirm one of:

1. They meant the **15 through-slots** (which read as longitudinal grooves from outside) —
   keep those, delete all three ribs. *This is the reading the geometry supports.*
2. They saw the ribs in a render/photo of the lid held inner-face-up and want them kept for
   stiffness — in which case keep the ribs but note they will foul a LiPo layer.
3. They want *new* outer bumper ribs added as a design change (not present on the original).

Second flag: with both transverse partitions removed the clear length is **exactly 58.000 mm**
for a 58 mm pack — zero clearance. Recommend a 1–2 mm relief at one end wall, or a
tolerance-profile-driven `pack_clearance` parameter.

---

## 6. Reproducing this extraction

```
python3 tmp/ldraw/measure.py 24853.dat 24849.dat 24849c01.dat 22127.dat
python3 tmp/ldraw/analyze.py 24853.dat faces xyz      # axis-aligned face maps
python3 tmp/ldraw/analyze.py 24853.dat sec z x -58 -20 20   # ASCII cross-sections
python3 tmp/ldraw/analyze.py 24849.dat faces xyz
```

`tmp/ldraw/analyze.py` also exposes `section(axis, at, up_axis)` returning exact segment
endpoints, which is how the latch and extraction-tab vertex tables above were produced.
