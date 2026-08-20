# Whole-part geometric comparison — PoweredUp hub battery box vs LDraw reference

Date: 2026-08-20 · Branch `feat/poweredup-hub-housing` @ `1bc1281` · **read-only review, nothing fixed**

Scope: `PoweredUpHubCover` vs LDraw `24853`, `PoweredUpHubHousing` vs LDraw `25560`,
`PoweredUpHubBatteryTray` vs LDraw `24849`. This is the *whole-part* comparison that the two
prior feature-checklist reviews did not run.

Source: LDraw official parts library, author Philippe Hurbain [Philo], CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). **Dimensions and derived comparison figures
read as facts; no converted geometry is committed.**

**Provenance note.** Tracked design-record artifact (moved from git-ignored `tmp/` per the
phase-4 TL review, `docs/design_plans/2026-08-19-poweredup-hub-battery-box_design.md` §TL
Review — CURRENT, finding B2).

---

## 1. Axis mapping, and its proof

LDraw uses X / Y(vertical, **−Y is up**) / Z, 1 LDU = 0.4 mm. The CadQuery classes are Z-up.
The mapping used throughout this document (implemented in `tmp/refcmp/ldmesh.py`) is

```
cq_x =  ldraw_X  * 0.4
cq_y =  ldraw_Z  * 0.4
cq_z = (zref_LDU - ldraw_Y) * 0.4      zref = 0 LDU for 24853 / 24849 (their own local frame)
                                       zref = 50 LDU for 25560 (the hub frame)
```

Handedness: the linear part maps (X,Y,Z) → (X, Z, −Y); its determinant is **+1**, so it is a
proper rotation — no mirroring, and triangle winding is preserved.

`zref = 50 LDU` for the housing is not a fitted constant: `22127.dat` places `24849` and `24853`
at translation `(0, 50, 0)` with identity rotation, and `25561c01.dat` places `25560c01` at the
identity, so the lid's own local `Y = 0` **is** hub `Y = +50 LDU`. Both classes take that plane
as their `Z = 0`.

**Proof — independent bounding-box agreement on all three axes:**

| part | reference (mapped) | implementation (`.solid` bbox) | agreement |
|---|---|---|---|
| Cover `24853` | x −27.200…27.200, y −35.600…34.400, z 0.000…13.000 | x −27.200…27.200, y −35.600…34.400, z 0.000…13.000 | exact, 3/3 axes |
| Housing `25560` | x −36.000…36.000, y −35.600…35.600, z 0.000…33.800 | x −36.001…36.001, y −35.601…35.601, z 0.000…33.800 | ±0.001 mm |
| Tray `24849` | x −28.400…28.400, y −30.800…32.800, z 0.000…28.000 | x −28.400…28.400, y −30.400…32.300, z 0.000…26.400 | x exact; y/z differ (§5) |

A sign error on any axis would break at least one of these six independent extents on the Cover,
which matches to the micron on every one. Additional per-feature confirmations that would each
independently break under a flip: the Cover's latch-end thickening band (z 0→2.000 over
y −30.800…−30.000) and its locating land (z 0→1.600 over y 30.000…31.200) each reproduce the
reference **exactly**, at the correct end.

---

## 2. Method and sampling density

`boolean_diff.py` cannot be pointed at these meshes — LDraw parts are *rendering surfaces*, not
watertight solids (the hub alone has 2,535 boundary edges). Every technique below therefore avoids
any inside/outside question about the reference. `tmp/ldraw/occupancy.py` (already rejected on
calibration) was not used.

1. **Two-sided surface-to-surface distance** (`tmp/refcmp/surfdist.py`) — the primary whole-part
   sweep. Both meshes are sampled with an area-proportional barycentric lattice; every sample is
   given its exact distance to the *nearest triangle* of the other mesh (Ericson closest-point,
   uniform-grid broad phase). Surface present in one part and absent from the other appears as a
   cluster of high-distance samples. This is valid on non-watertight meshes because it never asks
   "inside or outside".
   Sample pitch 0.5 mm (Cover), 0.6 mm (Housing, Tray). Sample counts: Cover 41,257 impl→ref /
   54,772 ref→impl; Housing 184,930 / 118,436; Tray 60,571 / 85,216. Outlier threshold 0.05 mm.
2. **Spatial clustering of the outliers** (`tmp/refcmp/cluster.py`) — 26-connected bucket
   flood-fill, reporting each region's AABB, max/mean deviation and the originating LDraw subpart.
3. **Cross-section overlays** (`tmp/refcmp/seccmp.py`) — both meshes sliced by the same plane and
   rasterised together (`R` = reference only, `I` = implementation only, `#` = both). Used along
   all three axes.
4. **Exact axis-parallel ray crossings** (`tmp/refcmp/ray.py`) — lists the *exact* coordinates at
   which a line crosses each mesh. This is where every number in §3–§5 comes from; it is immune to
   raster error. ~120 rays were fired, swept at 1–2 mm pitch through the latch, tongue, arms,
   window and end walls.
5. **Planar-face-area maps** (`tmp/refcmp/zmap.py`, `planeloc.py`) — total planar face area per
   constant-X/Y/Z plane on both meshes, which surfaces *whole families of faces* one part has and
   the other does not. This is what caught finding H1.
6. **Ground-truth solid classification of the implementation** (`tmp/refcmp/inside.py`, OCCT
   `BRepClass3d_SolidClassifier`) — used to confirm every implementation-side claim, since the
   CadQuery solid *is* watertight.
7. **LDraw `.dat` source reads** (`tmp/ldraw/region_dump.py`) — used wherever exact numbers or a
   primitive's identity mattered (finding H2's R3.600 mm blend radius was read off `1-4cyli.dat`
   vertices, not inferred from the mesh).

---

## 3. Findings — Cover (`PoweredUpHubCover` vs `24853`)

The brief's expectation was **exactly two** intended differences: the three inner AA divider ribs
deleted, and the 15 outer through-slots closed. Both of those are present and clean (§6). But they
are **not the only differences** — four more were found.

| # | region | reference | implemented | magnitude | `file:line` | severity |
|---|---|---|---|---|---|---|
| C1 | latch U-spring **release leg**, outer face | slanted/curved blade: y = −34.220 @ z=5, −33.733 @ z=8, −33.367 @ z=11, −33.046 @ z=12.5 | straight vertical wall, y = −32.840 for all z ∈ [0, 3.6+] | **1.380 mm** peak Y error (@z=5); two-sided surface distance up to **1.600 mm** (impl→ref) / **1.536 mm** (ref→impl) over 2,867 samples | `cover.py:194` (`PAD_OUTER_Y = -35.600`), `cover.py:193-196`, `_build_release_leg` (`cover.py:~300-330`) | **significant** |
| C2 | release-leg **thickness** | 1.028 mm @ z=5, 0.715 mm @ z=8, 1.047 mm @ z=11 (varying, drafted) | constant 0.500 mm | 0.215–0.528 mm | `cover.py:193` (`LEG_B_THICKNESS = 0.500`), `cover.py:312` | **significant** |
| C3 | **thumb pad** at z = 2.0 | thin blade, y −34.063…−33.365 (0.698 mm) | solid block, y −35.600…−32.290 (3.310 mm) | **+2.612 mm** of material, extending 1.537 mm further into −Y than the reference reaches at that height | `cover.py:194`, `cover.py:195` | **significant** |
| C4 | **"Tongue B"** footprint, \|x\| 15.6…26.0 | plate/tongue extends to y = +33.378 | plate stops at y = +32.000 | **1.378 mm** short over 2 × 8.8 mm of width; ref→impl cluster max **1.378 mm**, 1,170 samples | `cover.py:169` (`TONGUE_X_HALF = 15.600`) | **significant** (changes the plan outline) |
| C5 | tongue **riser root**, \|x\| ≤ 15.6 | riser starts at y = +32.400 | riser starts at y = +32.000 | **0.400 mm** of extra material, z 1.2…2.8 | `cover.py:169-176` | cosmetic |
| C6 | tongue **teeth / ledge notches** | 6 locating teeth + notches | one uniform blade | up to **0.800 mm** profile deviation (impl→ref cluster, 437 samples, y 31.26…34.40) | `cover.py:169-176` | cosmetic |
| C7 | barb crest | R1.000 mm cylindrical bead, 157.5° arc | faceted crest | < 0.030 mm | `latch_geometry.py` | cosmetic |

C1–C3, C5 and C6 are *disclosed* in the class docstring as "known simplifications" / Developer-chosen
dimensions — but they are real geometry differences, several of them larger than a millimetre, and
they are **not** in the two-item intended-delta list. C4 is disclosed as an outright omission.

**Verified identical (reference == implementation, to ≤0.001 mm):**
plate outline (x ±27.200, y −30.800…+32.000) and its 1.200 mm thickness at every sampled interior
point; sharp plan corners; the latch-end thickening band (2.000 mm over y −30.800…−30.000); the
locating land (raised to 1.600 mm over y 30.000…31.200 — the corrected sign is right); and — notably
— the **hook's drafted inboard face**, which tracks the reference exactly: y = −32.019 @ z=5,
−32.126 @ z=8, −32.233 @ z=11, all matching to the micron.

---

## 4. Findings — Housing (`PoweredUpHubHousing` vs `25560`)

Expected intended differences: latch catch added (absent from LDraw), single wall instead of two at
both retention ends, arms at 7.8 mm instead of 7.200 mm. **Five further differences were found, one
of them blocking.**

| # | region | reference | implemented | magnitude | `file:line` | severity |
|---|---|---|---|---|---|---|
| **H1** | **top deck** | material at the part centre occupies **z 27.518 … 29.600**; the top face is the plane **z = 29.600** carrying **3,469.6 mm² of up-facing area**. Above it the part is *empty* except the two connector-port tubes (only **26.9 mm²** of face exists at z = 33.800, at x ±18.8…20.0, y −14.8…−1.2) | **void** at z 27.518…29.600 (classifier: `(0,0,28.5)` is OUT); **solid slab** over the full 54.4 × 71.2 mm footprint at **z 29.600 … 33.800** (3,873.3 mm² top face; classifier: `(0,0,32.0)` is IN) | the part is **4.200 mm too tall over its whole footprint**; ≈ **16,270 mm³** of fabricated material — **61 % of the model's 26,471 mm³ total volume**. The real 2.082 mm deck is missing and replaced by a slab sitting entirely outside the reference envelope | `housing.py:210-211` (`TOP_Z = 33.800`, `DECK_Z = 29.600`), `housing.py:407-417` (`_build_top_deck`) | **BLOCKING** |
| **H2** | **arm faces**, all four arms | between the pin holes both faces are **dished**: flat pocket floors at z = 18.622 and z = 21.378 (`rect3.dat`, 86.7 mm² per plane), x 29.454…34.546, blended into each hole boss by an **R3.600 mm** cylinder (`1-4cyli.dat`, centre on the hole axis) — leaving a 2.756 mm web and 1.054 mm full-thickness edge rails | solid slab, z 16.000…24.000 throughout | **2.622 mm** pocket depth on *each* face × 8 pockets; the arms' entire visible top and bottom surfaces are wrong | `housing.py:227-236`, `_build_arm_and_bore_local` (`housing.py:423+`) | **significant** |
| **H3** | **side windows** | opening **24.000 mm wide × 8.400 mm tall**, with ramped shoulders above z ≈ 4.8 (half-width 12.000 @ z ≤ 4.8 → 11.761 @ z=6.0 → 8.903 @ z=8.3 → closed by z=8.5) | plain rectangle **24.800 mm × 16.000 mm**, half-width 12.400 constant to z = 16.000 | **+7.600 mm** height (90 % taller), +0.400 mm per side. The docstring justifies 16.000 mm as "the ramped ends' peak" — the source's ramped ends peak at **8.400 mm**, so that justification is factually wrong | `housing.py:220-221` (`WINDOW_Y_HALF`, `WINDOW_Z_HI`), `housing.py:387-400` | **significant** |
| **H4** | **arm-to-side-wall joint** | continuous material | an **open 0.100 mm slit** at \|x\| 28.000…28.100, spanning the full Y (−35.600…35.600) and **z 16.000…22.000** (classifier: `(28.05, 0, 18.0)` and `(28.05, 20.03, 18.0)` are OUT). Bridged only in z 22.000…24.000 | 0.100 × 6.000 × 71.200 mm open crack on each side | `housing.py:455-460` (gap acknowledged), `housing.py:484-495` (Band-B bridge deliberately omitted) | **significant** (prints as a slot; the arm hangs off a 2 mm-tall bridge) |
| H5 | upper side wall, outer face | \|x\| = 27.200 | \|x\| = **27.250** — 435.7 mm² of externally-visible face, z 22.000…29.600 | **0.050 mm** proud. The code comment asserts this "does not change any externally-visible dimension"; it does (that face *is* the outside of the part) | `housing.py:357-366` (`overlap = 0.05`) | cosmetic |
| H6 | pin holes (all 12) | Ø **4.800** mm | Ø **5.018** mm (x −34.509…−29.491 at the corner hole) | **+0.218 mm** diameter. Almost certainly a deliberate print clearance from `PerpendicularHolesLiftarm`, but it is a departure from the reference and from `docs/lego-technic.md`'s 4.8 mm | `housing.py:437`, `technic_beam_perp.py` | cosmetic (verify intent) |
| H7 | arm width and root | arm spans x 28.400…35.600 (**7.200 mm**); root inner end at \|y\| = 12.400 | arm spans x 28.100…35.600 (**7.500 mm**); root inner end at \|y\| = **12.001** | width +0.300 mm — note this is **7.5 mm, not the 7.8 mm the design claims**, because the outer edge is trimmed at 35.600; root 0.399 mm longer | `housing.py:229` (`ARM_Y_LO = 12.400`), `housing.py:236` (`ARM_WIDTH_TRIM_Y`) | cosmetic |
| H8 | tongue-end rebate, outer face | y = 34.400 | y = **34.550** | 0.150 mm (looks like a deliberate fit clearance) | `housing.py` tongue-end wall | informational |
| H9 | interior detail | reference carries planar face families at z = 2.674, 4.800, 8.400, 14.800, 16.800, 21.200, 23.200, 24.536, 26.400, 27.200, 28.000 (ribs, cradle ceiling, port keying) | absent | — | docstring "Known simplifications" | cosmetic (disclosed) |

**Verified matching:** overall X/Y envelope; the wall step at z = 22.000 (0.800 mm outward, x 28.000 →
27.200); end-wall X extent 28.000 mm; the 12-hole pin map (holes on 8.000 mm pitch at y = ±16, ±24,
±32, x = ±32, verified by ray at four positions); the arm Z band 16.000…24.000; the middle-hole
three-step bore, which opens the side wall at y ≈ 22…26 in *both* meshes identically.

---

## 5. Findings — Battery tray (`PoweredUpHubBatteryTray` vs `24849`)

Large intended differences (partitions removed, floor added, strap holders added, AA shelf removed),
so per the brief these are not itemised. Two-sided surface distance: 70.2 % / 76.7 % of samples off
by more than 0.05 mm, dominated by one part-spanning cluster in each direction — i.e. the part is a
redesign, not a copy, exactly as intended.

One thing worth recording because it is *envelope*, not internal redesign, and nothing in the
intended-difference list calls for it:

| # | region | reference | implemented | magnitude | severity |
|---|---|---|---|---|---|
| T1 | outer envelope | y −30.800 … +32.800, z 0 … 28.000 | y −30.400 … +32.300, z 0 … **26.400** | −0.400 mm at the −Y edge, −0.500 mm at the +Y edge, **−1.600 mm** in height | informational — confirm this shrink is intended |

X is exact (±28.400).

---

## 6. The intended-delta lists: confirmed or refuted

**Cover — REFUTED.** The two intended deltas are present and clean, but they are not the only ones.

* *Divider ribs deleted* — **confirmed and complete.** All three ribs (crest x = −10.8, +3.6, +18.0)
  and their gusset families are absent from the implementation and present in the reference
  (ref→impl clusters 0–19, `s\24853s02.dat` / `rect1.dat` / `rect3.dat`, z 0.2…4.8). No stub, no
  partial rib, and the asymmetry of the +18.0 rib (gusset on its −X flank only) is reflected in the
  cluster extents (x 14.0…18.4, not 14.4…21.6). Nothing *adjacent* was disturbed: the plate is
  1.200 mm thick at every probe point around the deleted ribs.
* *15 through-slots closed* — **confirmed and complete.** All 15 appear as `box4.dat` outliers on the
  reference side at the documented columns (x = 0, ±7.2, ±14.4) and rows (y −22.64…−16.40,
  −4.80…+3.20, +14.80…+21.20), and as flat-plate outliers on the implementation side, max 0.600 mm =
  the 1.2 mm plate seen from both faces. Nothing beyond the slot footprints changed.
* **But also:** C1, C2, C3 (latch release leg / thumb pad — up to 1.600 mm), C4 (Tongue B omitted —
  1.378 mm of missing plate over 17.6 mm of width), C5, C6, C7. So the Cover differs from `24853`
  in **at least seven** ways, not two.

**Housing — REFUTED.** The three named intended departures are all present:

* latch catch added (absent from LDraw) — confirmed;
* single wall at both retention ends — confirmed (latch end: reference is solid y −35.600…−30.800 at
  x = 0, z = 5; implementation is 1.200 mm at y −35.600…−34.400. Tongue end: reference's inner skin
  at y 32.000…33.234 is absent from the implementation);
* arms thicker than LDraw's 7.200 mm — confirmed, though realised as **7.500 mm**, not 7.8 mm (H7).

But **H1–H5 are all outside that list**, and H1 is a 4.2 mm, 16,000 mm³ departure that the class
docstring's own "exact copy … 72.0 × 71.2 × 33.8 mm" claim actively conceals: the 33.8 mm figure is
the reference's *bounding box*, reached by 26.9 mm² of port-tube tips, not by the shell, whose top
face is at 29.600 mm.

---

## 7. Verdict — would these read as the real thing?

**Cover: mostly yes, with one wrong-looking end.** The plate, its outline, thickness, corners, latch
band, locating land and the hook's drafted face are the real part to within a micron. But the whole
cantilever U — the part a user actually looks at and presses — is a boxy 0.5 mm-walled prism where the
reference is a slanted, variable-thickness blade, off by up to 1.6 mm; and the plate's plan outline is
visibly short at the tongue end over 17.6 mm of its width. Someone comparing it to a real lid would
notice the latch and the tongue.

**Housing: no.** Three independent reasons, any one of which is enough:

1. It is **4.2 mm too tall over its entire footprint** (H1). The real shell's top face is at
   z = 29.600 mm; ours puts a solid slab from 29.600 to 33.800. That is 61 % of the model's volume,
   it changes the part's proportions in every view, and it is the single most likely cause of the
   user's "it still doesn't look right".
2. The **arms are flat solid slabs** where the real arms are dished on both faces to a 2.756 mm web
   with R3.6 mm blends around each hole boss (H2) — a 2.6 mm-deep feature on eight visible surfaces.
3. The **side windows are nearly twice as tall** as the real ones (16.0 vs 8.4 mm) (H3), and the
   justification recorded in the code for that number does not match the source.

Plus H4, an actual 0.1 mm open crack between each arm and the side wall over 6 mm of height.

**Tray:** a deliberate redesign; only the 1.6 mm height / 0.9 mm length envelope shrink (T1) is worth
a confirmation.

---

## 8. Summary counts

| severity | Cover | Housing | Tray | total |
|---|---|---|---|---|
| blocking | 0 | 1 (H1) | 0 | **1** |
| significant | 4 (C1–C4) | 3 (H2, H3, H4) | 0 | **7** |
| cosmetic / informational | 3 (C5–C7) | 5 (H5–H9) | 1 (T1) | **9** |

"Could not determine": none of the findings above rest on parity/inside-outside reasoning about the
LDraw mesh. Every magnitude quoted comes from exact ray-crossing coordinates, planar-face-area maps,
or direct `.dat` vertex reads, and every implementation-side claim was re-confirmed with the OCCT
solid classifier. The one thing deliberately **not** determined is the reference's *internal* deck
thickness away from the part centre (the cradle ceiling is corrugated); only the centre value
(27.518 → 29.600, 2.082 mm) is quoted, and H1 does not depend on it — H1 rests on the top face
plane, which is unambiguous at 29.600 mm with 3,469.6 mm² of up-facing area.

## 9. Tooling written for this review (all under `tmp/refcmp/`, read-only, disposable)

`mesh_impl.py` · `ldmesh.py` · `surfdist.py` · `cluster.py` · `seccmp.py` · `ray.py` · `zmap.py` ·
`planeloc.py` · `normals.py` · `inside.py`

---
---

# RE-VERIFICATION — ROUND 2 (post-repair)

Date: 2026-08-20 · Branch `feat/poweredup-hub-housing` @ **`29bf06c`** (round 1 was `1bc1281`)
· read-only review, nothing fixed · **§1–§9 above are the round-1 record and are left unedited.**

Full sweep re-run at round-1 density — not targeted verification. Sample counts this round:
Cover 41,286 impl→ref / 54,772 ref→impl at 0.5 mm pitch; Housing 203,273 / 118,436 at 0.6 mm;
Tray 60,571 / 85,216 at 0.6 mm. Same probes (`surfdist.py`, `cluster.py`, `zmap.py`, `ray.py`,
`planeloc.py`, `inside.py`), plus two new ones: `scan.py` (OCCT solid-classifier line scan, for
ground-truth IN/OUT spans on the implementation) and `collide.py` (pairwise seated-interference
volumes with per-lump decomposition). Round-1 meshes/outliers archived under `tmp/refcmp/r1/`.

## R0. Axis mapping re-proved on the new build

The mapping is unchanged (`cq_x = ldraw_X·0.4`, `cq_y = ldraw_Z·0.4`, `cq_z = (zref−ldraw_Y)·0.4`,
`zref` = 0 LDU for `24853`/`24849`, 50 LDU for `25560`) — it is fixed by the LDraw library and the
`22127` / `25561c01` placements, neither of which changed. But the housing's height changed, so the
round-1 bbox proof no longer carries; re-proved from features instead:

* **Cover** — x ±27.200 exact; y_max +34.400 exact; z 0…13.000 exact; latch-end band 0→**2.000** over
  y −30.800…−30.000 exact; locating land 0→**1.600** over y 30.000…31.200 exact; plate **1.200** at
  six independent interior probes. (y_min is now −34.220 against the reference's −35.600 — that is
  finding **RC1** below, not a mapping error: every other extent still matches to the micron, and the
  reference reaches −35.600 only on a *sloped* foot surface at cq z = 0, read directly from
  `s\24853s01.dat`.)
* **Housing** — x ±36.001 vs ±36.000; y ±35.601 vs ±35.600; wall step at z = **22.000** with the
  outer face going 28.000 → 27.200, exact; the 12-hole pin map at x = ±32.000, y = ±16/±24/±32,
  exact; arm band z **16.000…24.000** exact; and — decisively — the new arm-dish floors land on
  z = **18.622** and **21.378**, reproducing the reference's own two planes to three decimals.
  Five-significant-figure agreement on a pair of planes cannot survive a sign or datum error.
* The housing's z-max is now 29.600 against the reference's 33.800; that is the declared
  out-of-scope port-tube omission (**RH10**), and the shared z = 29.600 plane (ref 3,506.2 mm²
  up-facing vs impl 3,883.8 mm²) anchors the datum from both sides.

## R1. Aggregate movement, round 1 → round 2

| metric | round 1 | round 2 |
|---|---|---|
| Housing volume | 26,471.0 mm³ | **17,787.0 mm³** (−32.8 %) |
| Housing envelope | 72.0 × 71.2 × **33.8** | 72.0 × 71.2 × **29.600** |
| Housing impl→ref, p90 | 1.425 mm | **0.764 mm** |
| Housing ref→impl, samples > 0.3 mm | 44,964 | **37,429** |
| Cover volume | 5,207.5 mm³ | 5,137.5 mm³ |
| Cover impl→ref, p90 | 0.254 mm | **0.093 mm** |
| Cover impl→ref, > 0.05 mm | 16.68 % | **12.56 %** |
| Cover latch region, impl→ref max | 1.600 mm | **0.739 mm** |
| Tray | 12,031.0 mm³ | 12,031.0 mm³ (untouched — byte-identical mesh) |

## R2. Verdict on each claimed fix (verified independently)

| fix | claim | independent result | verdict |
|---|---|---|---|
| **H1** deck | slab moved to z 27.518…29.600, height → 29.600 | envelope z-max **29.600** ✓; `(0,0,28.5)` **IN**, `(0,0,29.5)` **IN**, `(0,0,30.0)` **OUT** ✓; impl now carries planar faces at z = 27.518 (3,640.6 mm²) and z = 29.600 (3,883.8 mm²); the phantom 33.800 slab is gone | **FIXED** — but see **RH1** (footprint/height at the ends) and **E11-a** (it now collides with the tray) |
| **H2** arm dish | reproduces 29.454 / 34.546 / 18.622 / 21.378 / 1.054 | cross-section **exact** (pocket walls at x 29.454 / 34.546, floors at z 18.622 / 21.378, rails 1.054 — the x-ray at y = 20.03 reproduces the reference crossing-for-crossing at both z = 16.10 and z = 17.00). Plan footprint **not** reproduced — see **RH2** | **PARTIAL** |
| **H3** windows | swept taper, 24.0 wide, 8.5 peak | width and taper match the reference exactly at z = 0.3, 2.0, 4.8, 6.0 and 8.3; **peak is 8.500, reference is 8.400** — see **RH3** | **PARTIAL** (my 8.400 stands, see below) |
| **H4** slit | closed via `SEAM_MARGIN` | `(28.05, 20.03, 18.0)` was **OUT** in round 1, is now **IN**; a 0.02 mm line scan at x = 28.05, z = 18.0 gives IN over y [−35.55,−27.00] ∪ [−21.00,−12.45] ∪ [12.45,21.00] ∪ [27.00,35.55] — i.e. solid across the entire arm footprint, with the only voids being the (correct) between-arms region and the middle-hole breakout, both of which the reference shares | **FIXED** |
| **C1/C2/C3** release leg | swept to the reference's ray crossings | **exact** at z = 2.0, 5.0, 8.0 and 11.0 (all four crossings identical to the micron); latch-region impl→ref max 1.600 → **0.739 mm**, mean 0.357 → 0.228 | **LARGELY FIXED**, with **RC1**, **RC2**, **RC3** residual and **E11-c** introduced |
| **C4** Tongue B | plan outline restored via `RISER_X_HALF` | plan outline **restored** (plate now reaches y = +33.378 at x = 21.0 and 24.0; ref→impl tongue cluster x-extent ±26.00 → ±24.74, max 1.378 → 0.800). But it was restored as a **full-height riser** — see **RC4** | **FIXED then over-corrected** |
| arm width 7.5 | ruled correct-as-built | unchanged (28.100…35.600 vs ref 28.400…35.600) | accepted, **RH7** |

### On H3's 8.5 vs my 8.400 — my figure was right

`24851.dat` carries a **planar face at cq z = 8.400 exactly**, 26.9 mm², spanning x −28.000…28.000
and y −8.400…8.400 (`planeloc.py`). That is the window's flat top, and it is a face in the source,
not an interpolation. Ray probes agree: at x = 27.3 the reference is open (half-width 8.903) at
z = 8.3 and closed at z = 8.45; the implementation is still open at z = 8.45 (half-width 2.226) and
closes by 8.6. **The reference peak is 8.400; the implementation's is 8.500 — 0.100 mm too tall**,
and the reference's *flat* 16.8 mm-wide top has been replaced by an apex.

## R3. Residual differences — Cover (`24853`)

**The two-item intended-delta list still does NOT hold.** Seven residuals, one of them newly
introduced by the repair.

| # | region | reference | implemented | magnitude | severity |
|---|---|---|---|---|---|
| **RC4** ⚠ NEW | Tongue B, \|x\| 15.6…25.98, y 32.000…33.378 | plain **1.200 mm** plate (z-ray at (21.0, 32.7), (24.0, 32.7), (18.0, 33.2) all give 0.000…1.200) | full-height riser, **2.800 mm** (same three probes give 0.000…2.800) | **+1.600 mm**, ≈ **45.8 mm³**, on the tongue's *mating* face; drives a new impl→ref cluster of max **1.600 mm**, 1,026 samples | **significant** |
| **RC1** | release-leg **foot**, z 0…2.0 | flares out to y = **−35.600** at z = 0 (a ramped/gusseted foot, `s\24853s01.dat`, at x −19.2…−16.5 and −8.3…−5.6), pulling back to −35.184 @ z=0.2, −35.152 @ z=0.6, −35.120 @ z=1.0, −34.063 @ z=2.0 | plain prism, held flat at y = **−34.063** for all z ≤ 2.0 | up to **1.121 mm** deficit at z = 0.2; the part's y-min is **1.380 mm** short of the reference's; ref→impl cluster max **1.537 mm** (unchanged from round 1) | **significant** |
| **RC3** | crown, z > 11.0 (**the declared deviation**) | tapers to a rounded nose: 1.991 mm wide @ z=12.0, 1.692 @ 12.5, **0.836 @ 12.9** | held flat: **2.567 mm** wide from z = 11.0 to 13.0 | z=12.0 +0.176 out / +0.400 in; z=12.5 +0.321 / +0.554; **z=12.9 +0.749 / +0.982 (tip 3.1× the reference's section)** | **significant** — see judgment §R6 |
| **RC2** | release-leg profile between samples | smooth, non-monotonic curve | piecewise-linear through z = 2.0, 5.0, 8.0, 11.0 | 0.154 mm @ z=6.0 (outer), 0.167 mm @ z=10.0 (inner) | cosmetic |
| **RC5** | tongue riser root | y = +32.400 | y = +32.000 | **0.400 mm** extra (unfixed round-1 C5) | cosmetic |
| **RC6** | tongue teeth / ledge notches | 6 teeth + notches | uniform blade | **0.800 mm** (unfixed C6) | cosmetic |
| **RC7** | barb crest | R1.000 arc | faceted | < 0.030 mm (unfixed C7) | cosmetic |

**Adjacency re-check — clean.** The two intended deltas are still surgical, and the repairs disturbed
nothing around them: locating land 0→1.600 ✓, latch band 0→2.000 ✓, plate 1.200 at (20,0), (26,20),
(−26,−20), (10.8,0) ✓, all three rib positions still fully deleted with the plate intact beneath, all
five slot columns still closed with no change to the 0.400 mm slot-face signature, and Tongue A's tip
band still 1.874…2.800 exactly. The 0.739 mm latch cluster is confined to y −34.19…−30.80; nothing
leaked into the plate.

## R4. Residual differences — Housing (`25560`)

**The three-item intended-delta list (+ out-of-scope port tubes) still does NOT hold.** Ten residuals,
two significant. One of them (**RH1**) is a *round-1 miss of mine*, not a regression — see §R7.

| # | region | reference | implemented | magnitude | severity |
|---|---|---|---|---|---|
| **RH1** ⚠ missed in round 1 | end walls & deck plan | end walls at y = ±35.600 span z **0…24.000** (−Y) and **3.326…24.000** (+Y); above z = 24 the shell narrows to the inner-skin line, so the deck top face spans only x ±27.200 × y −32.000…+33.200 = **3,506.2 mm²** | end walls span z **0…29.600**; deck top face spans x ±28.000 × y ±35.600 = **3,883.8 mm²** | **+5.600 mm** of wall height at both ends; deck overhangs by **0.800 mm** in X and **2.400–3.600 mm** in Y; +377.6 mm² of top face. Visible silhouette change | **significant** |
| **RH2** | arm dish plan footprint & rim | dish open (at z = 17.0, x = 32.03) over y ≈ [18.5, 22.5] and [25.5, 29.5] — **~4.0 mm each**; rim is a curved blend, so the face sits at z = 18.090 @ y=21.03 and 18.179 @ y=27.03; floor planes total **86.7 mm²**, footprint \|y\| ≤ **29.454** | open only over y [19.58, 20.42] and [27.58, 28.42] — **0.84 mm each** (0.02 mm classifier scan); rim is a vertical wall, so the face is already at 16.000 at those y; floor planes total **69.5 mm²**, footprint \|y\| ≤ **35.600** | residual extra material **2.179 mm** @ y=27.03, **2.090 mm** @ y=21.03, **1.622 mm** @ y=19.03; floor area **−19.8 %**; independently confirmed by four impl→ref clusters, **max 1.491 mm**, 754 samples each, at z 16.00…18.62 | **significant** (H2 only partly fixed) |
| **RH3** | side-window top | flat top face at z = **8.400** (26.9 mm², y ±8.400); half-width 9.966 @ z=8.0 | apex at z = **8.500**; half-width **9.276** @ z=8.0 | +0.100 mm peak; **0.690 mm** too narrow at z = 8.0; flat top replaced by a point | cosmetic |
| **RH5** ⚠ new observation | pin-hole counterbore | Ø **6.388**, depth **0.800** (face at z = 16.800) | Ø **6.198**, depth **0.990** (face at z = 16.990) | −0.190 mm Ø, +0.190 mm depth | cosmetic |
| **RH4** | pin holes | Ø 4.788 | Ø **5.018** | +0.230 mm — deliberate print clearance | informational |
| **RH6** | upper side wall, outer face | \|x\| 27.200 | \|x\| **27.250** (435.7 mm² of visible face) | 0.050 mm proud (round-1 H5, unfixed) | cosmetic |
| **RH7** | arm width / root end | 7.200 mm; root \|y\| 12.406 | 7.500 mm; root \|y\| **12.001** | +0.300 / 0.405 mm — ruled correct-as-built | informational |
| **RH8** | tongue-end rebate face | y 34.400 | y **34.550** | 0.150 mm — deliberate clearance | informational |
| **RH9** | deck underside & interior | corrugated AA-cradle ceiling; ribs at z = 2.674, 4.800, 14.800, 16.800, 21.200, 23.200, 24.536, 26.400, 27.200, 28.000; port keying ribs; screw boss | flat plane at z = 27.518; ribs absent | disclosed simplification — but it is the *direct cause* of **E11-a** | cosmetic (with a fit consequence) |
| **RH10** | connector-port tubes | x ±18.8…20.0, y −14.8…−1.2, z 30.18…**33.800** | absent | ref→impl clusters max **1.500 mm**, 834 samples each | **declared out of scope** |

**Adjacency re-check.** The repairs did not disturb: the wall step (x 28.000→27.200 at z = 22.000,
exact at z = 10.0); the arm pocket cross-section (exact); the 12-hole pin map (crossing-for-crossing
at z = 20.07, deltas only from RH4/RH7); the arm band z 16.000…24.000; the middle-hole three-step
bore breakout, which still matches the reference. Two things the repairs *did* move that were
previously fine — the deck's underside plane (RH9 → E11-a) and the window's admitted envelope
(RH3 → E11-b).

## R5. Escalation 11 — three collisions, measured independently

`tmp/refcmp/collide.py` intersects the three seated solids straight out of
`assembly.py` (`Housing` and `Cover` untransformed; `BatteryTray` lifted by
`PLATE_THICKNESS = 1.200`) and decomposes each interference into connected lumps.

| collision | Developer's figure | my measurement | reading |
|---|---|---|---|
| **E11-a** Housing ↔ Tray, deck | ~21 mm³ | **21.094 mm³**, one lump, x ±26.250, y −30.400…32.300, **z 27.518…27.600** — a 0.082 mm sliver over the whole tray footprint | **Genuine defect, not an artifact.** The tray's top sits at 26.400 + 1.200 = **27.600**; the new deck underside is at **27.518**. My round-1 report gave 27.518 explicitly as *the centre value of a corrugated ceiling* and flagged that the deck's thickness away from the centre was **not determined**; the repair applied that single point as a global plane, which necessarily pushes the deck onto the tray. Magnitude is sub-layer-height, but it is a hard rigid-body overlap on a seating face, not a snap residual. |
| **E11-b** Housing ↔ Tray, window taper | ~2.3 mm³ | **2.344 mm³** = 4 × 0.586 mm³, at \|x\| 27.200…28.000, \|y\| **10.767…12.000**, **z 4.800…6.800** | **Genuine defect *and* an expected consequence of a corrected shape.** Round 1's oversized rectangular window was hiding it — exactly the masking relationship the housing docstring itself predicted ("only ever removes *more* material… cannot introduce an unintended interference"). The party at fault is the **tray**: its tab reaches \|y\| = 12.000 while the real window admits ≈11.5 at z = 6.8. Fix the tab, not the window — re-widening the window would re-introduce **RH3/H3**. |
| **E11-c** Cover ↔ Housing, latch | 39.4 mm³, "was < 25" | **39.413 mm³ in 4 lumps — and they are two different things:** ⑴ **2 × 10.662 = 21.324 mm³** at y −33.733…−33.320, **z 8.000…13.000**, x ±5.6…19.2; ⑵ **2 × 9.044 = 18.088 mm³** at y −32.130…−30.800, **z 12.500…13.000** | **Mixed — and the framing is misleading.** Lump ⑵ (18.088 mm³) *is* the barb-in-catch seated residual, i.e. the previously-accepted rigid-body snap artifact, and it is **below** the old < 25 mm³ figure. Lump ⑴ (21.324 mm³, 54 % of the total) is a **new, different collision in a different place**: the rebuilt release leg — now correctly at y = −33.733 at z = 8 — fouls the housing's locally-thickened latch catch over 5 mm of height. The rise from < 25 to 39.4 is *not* deeper barb engagement. Root cause: the **intended single-wall departure**. The real part keeps its inner skin at y −32.000…−30.800 and leaves y −34.400…−32.000 clear for the leg; our single wall plus catch thickening occupies part of that clearance. This needs resolving in the catch's Y extent or the leg profile — it is not an artifact. |
| Cover ↔ Tray | — | **0.000 mm³** | clean |

## R6. Judgment — the release leg held flat above z = 11.0

**The declared deviation is acceptable in isolation but is not the larger one, and it was declared on
only one end of the profile.**

* **Shape.** The reference's crown tapers to a **0.836 mm** rounded nose at z = 12.9. Held flat, ours
  is a **2.567 mm** square block from z = 11.0 to 13.0 — 3.1× the reference's section at the tip and
  1.29× at z = 12.5. The consequence is not just cosmetic: this is the surface that has to clear the
  housing's catch on insertion, and a square 2.567 mm nose has no lead-in where the real part has a
  rounded one.
* **Compliance.** The U's compliance is dominated by the hook leg (which matches the reference to the
  micron at z = 5, 8, 11) and by the crown's rotational stiffness. Squaring and thickening the crown
  over the top 2 mm — 15 % of the 13 mm height — moves stiffness in the **stiffening** direction,
  roughly 3× locally at z = 12.5 and up to ~29× at the very tip on a t³ basis. Partially offset by the
  fact that our inter-leg slot stays open 0.5 mm higher than the reference's (ours closes at ≈11.8,
  the reference's at ≈11.2–11.5). Net effect: a **modestly stiffer** latch, not a softer one — the
  safe direction for retention, the wrong direction for insertion force. Unquantified anywhere.
* **The collision justification does not survive.** The stated reason for the flat hold is that
  extrapolating causes a hook-leg collision. But the rebuilt leg **already collides** — with the
  *housing*, 21.324 mm³ over z 8.000…13.000 (**E11-c** ⑴). So the profile was constrained to avoid one
  interference while introducing a larger one; that trade was not made explicitly.
* **The undeclared half is worse.** The profile is held flat **below z = 2.0** as well as above 11.0,
  and that end is a **1.121 mm** deficit rising to a **1.380 mm** shortfall in the part's own
  y-extent (**RC1**) — larger than the declared z > 11.0 deviation at every comparable z. The
  reference's flared foot is a real, source-readable feature (`s\24853s01.dat`, ramping to
  y = −35.600 at cq z = 0), not an extrapolation artifact, and it is structurally the *root* of the
  compliant leg — the section where a cantilever's bending stress peaks.

**Verdict: accept the z > 11.0 hold as a bounded, documented shape simplification (max 0.982 mm,
stiffening direction, no interference of its own); do not accept it as the whole story. The flat hold
below z = 2.0 is undeclared, larger, and at the structurally important end.**

## R7. Where round 1 was wrong

* **H4's extent was over-claimed.** I wrote that the 0.100 mm slit spanned "the full Y
  (−35.600…35.600)". That was read off the *plane's* bbox; the arms only exist at \|y\| ≥ 12.4, so
  the actual open slit was ≈0.100 × 6.000 × 23.2 mm per arm, not × 71.2. The defect was real
  (classifier: `(28.05, 20.03, 18.0)` OUT) and is now fixed; only my figure for its length was wrong.
* **RH1 is a round-1 miss, not a regression.** I observed at z = 26 that "the reference's end walls do
  not extend up to z = 26" and folded it into the intended single-wall bucket instead of raising it.
  It is a distinct difference (**+5.600 mm of wall height, and a deck footprint 0.800 mm oversize in X
  and 2.400–3.600 mm in Y**), and the H1 repair made it more consequential by turning the overhanging
  perimeter into the part's actual top surface.
* **RH5 (counterbore Ø and depth) was not raised in round 1.** It is small (0.190 mm each way) but it
  was measurable then.
* **My 8.400 mm window peak was correct** and is corroborated by a planar face in the source; the
  repair's 8.500 is 0.100 mm high.
* **E11-a is a spec-application issue, not a measurement error.** Round 1 §8 explicitly stated the
  deck's off-centre thickness was *not determined* and quoted 27.518 as the centre value only.

## R8. Round-2 summary counts

| severity | Cover | Housing | Escalation 11 | Tray | total |
|---|---|---|---|---|---|
| blocking | 0 | 0 *(H1 cleared)* | 0 | 0 | **0** |
| significant | 3 (RC1, RC3, **RC4 new**) | 2 (**RH1**, RH2) | 3 (E11-a, E11-b, E11-c ⑴) | 0 | **8** |
| cosmetic / informational | 4 (RC2, RC5–RC7) | 8 (RH3–RH10) | 1 (E11-c ⑵, accepted class) | 1 (T1) | **14** |

**Intended-delta lists: both still refuted.** Cover: 7 residuals beyond the two intended (was 7 —
different ones; C4 fixed-then-over-corrected into RC4, C1–C3 reduced from 1.600 to 0.739 mm but
leaving RC1/RC3). Housing: 10 residuals beyond the three intended plus the declared port tubes
(was 9; H1 and H4 cleared, H2/H3 reduced to partial, RH1 and RH5 added by scrutiny not by regression).

## R9. Verdict — would they read as the real thing now?

**Housing: yes, at the silhouette level — the blocking defect is genuinely gone.** Removing the
4.2 mm phantom slab is the single biggest correctness gain in this round; the part is now the right
height, the arms are dished, the windows taper, and the arm/wall crack is closed. What remains
visible: the deck perimeter overhangs and the end walls run 5.6 mm past where the real shell stops
(**RH1**), and the arm dishes are ~1/5 the length they should be (**RH2**), so the arms still read
as slabs with two small dimples rather than the reference's long scalloped panels. Neither is
wrong-part territory. **Not blocking; visibly not yet the real part.**

**Cover: better at the latch, worse at the tongue.** The release leg went from 1.600 mm wrong to
0.739 mm wrong — a real improvement, and the hook leg is exact. But the C4 repair put a 1.600 mm
full-height riser on the tongue's mating face where the reference has plain 1.200 mm plate
(**RC4**), which is a *functional* surface, and the leg's foot no longer reaches the reference's own
extent (**RC1**). Net: the cover reads better in a viewer and fits worse in principle.

**Assembly:** the three seated collisions are all genuine — none is purely a rigid-body artifact
except the 18.088 mm³ barb-in-catch component. Two of them (E11-a, E11-b) are *consequences of
correcting shapes that were previously over-generous*, which is expected and healthy; the third
(E11-c ⑴, 21.324 mm³) is a new interference introduced this round and the one that needs a decision.

## R10. Tooling added this round

`tmp/refcmp/scan.py` (OCCT solid-classifier line scan → IN/OUT spans) ·
`tmp/refcmp/collide.py` (seated pairwise interference volumes, decomposed per lump).
Round-1 meshes and outlier sets archived under `tmp/refcmp/r1/`.
