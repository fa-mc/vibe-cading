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

## R22 — release-leg inner face / release aperture (round 22, blocking)

Re-measured from `parts/24853.dat`, sectioned at the finger centre (cq `X = 12.4`,
LDraw `x = 31`) using this repo's own `analyze.walk` / `analyze.section`. Axis
mapping as elsewhere in this extract: `cq_X = ldu_x * 0.4`, `cq_Y = ldu_z * 0.4`,
`cq_Z = -ldu_y * 0.4`.

| cq Z | hook-leg outboard face | leg face bounding the aperture | aperture |
|---|---|---|---|
| 0.0 | −31.840 | −33.480 | **1.640** |
| 8.8 | −32.154 | −33.628 | 1.474 |
| 10.2 | −32.204 | −33.480 | 1.276 |
| **11.2 / 11.4 / 11.6** | −32.240 | **−33.302** | **1.062** |
| 12.2 | −32.240 | −33.124 *(the bead, not the leg)* | — |

**Finding (blocking, fixed round 22).** Rounds 18–21 built the leg from an outer
face plus a thickness, and round 21's *"held flat beyond z = 11.0"* deviation put
its inner face at **−32.320**, leaving a **0.043 mm** aperture against the
reference's **1.062 mm**. The Ø2.000 barb bead needs ~1 mm of aperture at exactly
that height, so it had nowhere to protrude and was absorbed into the crown —
`PoweredUpHubCover`'s barb was geometrically inert, and retention was in fact
occurring between `PoweredUpHubHousing`'s keeper nub and the **crown**.

**Caveat on method (read before extending this table).** Section-sampling an
LDraw part cannot reliably tell an *inner* face from an *outer* one: these are
rendering surfaces, not solids (the same limitation that got `occupancy.py`
rejected — see §12.1). A first attempt at round 22 assigned every value above to
the leg's *inner* face and rebuilt the whole profile from it; that drove the leg
1 mm outboard into the housing wall (191 mm³ of interference) and was reverted.
Only the **aperture width** — the gap between two faces — is safe to read this
way, which is why the fix moves a single profile point rather than re-deriving
the leg.

## R23 — plane reconciliation sweep (round 22): detection gap found and closed

**Why this exists.** Differences kept surfacing by eye after every gate passed.
`vibe_cading/tools/boolean_diff.py` cannot help here — the reference is a compound
of loose faces, not a closed solid, so it returns `intersection 0.00 / missing 0.00
/ extra 0.00`, Jaccard 0. That is a *failed measurement*, not a match, and it must
not be quoted as one.

**Method that does work.** Enumerate every axis-aligned plane in the reference
mesh carrying >= 5 mm² of face, and check whether the built model has a face at
the same coordinate (0.06 mm tolerance). This works on a surface mesh because it
never needs the part to be watertight. It is this project's own *Feature
reconciliation (mandatory)* convention, applied to planes rather than holes.

**First run: 23 reference planes with no counterpart.** Two were real, unmodelled
feature families:

| Missing | Area | Verdict |
|---|---|---|
| X = ±0.400, ±6.800/±7.600, ±14.000/±14.800 | 24.8 mm² each | **The 15 through-slots (§1.2)** — never modelled by rounds 18–21, despite §1.2 calling them *"the only outer-face feature"*. Now built (`SLOT_*`). |
| Y = 32.400 | 26.9 mm² | Ledge started at the plate edge (32.000) instead of §1.5's 32.400. Now `LEDGE_Y_LO`. |

**After the fix: 14 planes, all accounted for.**

* **13 planes** (X = 3.200/4.000, 17.600/18.400, −10.400/−11.200 at ~161 mm², plus
  the Y rib-end and gusset planes at −23.600…22.800) are the **three AA-cell
  divider ribs**, whose X centres −10.8 / +3.6 / +18.0 at 0.800 mm wide give
  exactly those face pairs. Deliberately deleted — design brief O1.
* **1 plane** (Z = 4.800, 117.9 mm²) is an internal face of the **hollow thumb-pad
  shell**. §1.4 records the pad as *"a thin shell"* with an internal ceiling at
  z = 2.791; this model builds it solid, so its internal faces do not exist here.
  Declared simplification, not a gap — and solid is the stronger choice for a
  printed part.

**Zero unexplained differences remain.** Re-run the sweep after any change to this
part; it is cheap and catches what review by eye does not.

### R24 — Latch crown: cross-section against the reference (round 24)

Method: `tmp/ldraw/slice_compare.py` computes a true cross-section at
X = 12.4 mm (finger centre) from each part's own triangles via one shared
`section()` routine, and overlays them. Unlike the plane-reconciliation of
§R23 this *is* sensitive to curves, extents and position-within-plane, which
is what the crown defect needed.

Two defects were visible and are now fixed:

1. **Square plateau + vertical shoulder beside the dome.** The crown's top
   edge ran horizontally at full height (`z = hook_depth`) from the bead's
   apex out to the leg's inner wall. The reference has no shoulder there —
   the release leg flows straight into the dome. Replaced with a single
   diagonal from the leg's inner wall to the bead apex.
2. **A 0.37 mm riser** between the leg top and the start of that diagonal,
   from running the crown's join above `CROWN_Z_LO`. The join now ends
   exactly at the spine's own top, so the diagonal starts at the leg top as
   it does in the reference.

**Two OCCT coincident-face traps were hit on the way** (this project's own
documented pitfall, both silent until the single-solid assertion fired).
The crown touches the spine at `leg_inner` and the finger along the bead
arc — *both* were sampled exactly on the neighbouring face, so the union
was face-to-face with zero volume overlap and the release leg (which
reaches the rest of the part only through this crown) dropped off as a
second solid. Both ends are now grown by `seam_overlap` into the
neighbour's material; neither changes the outboard silhouette.

**Bead apex sampling.** `barb_arc_points` sampled `phi` uniformly over
157.5 deg in 24 steps, which steps over `phi = 90` — so the faceted bead's
apex sat one chord sagitta (~0.0005 mm) below `lg.hook_depth`, even though
the method's own docstring promised `phi = 90` is on the curve. The tip
height is functional (it is what seats against the housing), so `90.0` is
now sampled explicitly rather than the tolerance being widened.

Retention is unchanged by all of the above: `Housing n Cover` = 7.3738 mm3.

> **CORRECTION (round 25).** This section originally also claimed "the
> aperture is 1.065 mm at z = 11.0 (reference 1.062)". **The reference value
> is wrong and the claim must not be relied on.** Measured numerically
> (`tmp/ldraw/aperture.py`, ray-cast surface crossings at X = 12.4), the
> reference's aperture at z = 11.0 is **0.087 mm**, not 1.062 mm. The two
> models agree to +-0.001 mm from z = 2 to z = 8 and then diverge; see R25.

### R25 — The real latch defect: the release leg curls the wrong way (round 25)

Found by station-ranked sweeping (`tmp/ldraw/sweep_compare.py`) plus a
numeric aperture profile (`tmp/ldraw/aperture.py`), after a hand-chosen
section had repeatedly missed it.

Aperture between the two legs of the U, at X = 12.4:

| z | reference | ours | note |
|---|---|---|---|
| 2.0 | 1.453 | 1.454 | agree |
| 6.0 | 1.080 | 1.080 | agree |
| 8.0 | 0.893 | 0.892 | agree |
| 9.0 | 0.747 | 0.951 | diverge |
| 10.0 | 0.523 | 1.010 | diverge |
| 11.0 | **0.087** | 1.069 | diverge |

Above z = 8 the reference's release leg turns **inboard** to meet the hook
leg, closing the U almost shut before the dome (inner face -33.02 -> -32.32
over z = 8..11). Ours turns **outboard** over the same band (-33.02 ->
-33.30) and the aperture re-opens. The profile constants are the cause:
`_LEG_OUTER_Y`'s top sample is (11.0, -34.000) with `_LEG_THICKNESS` 0.698,
where the reference measures -33.37 / 1.047.

Those were the ORIGINAL values. Round 20 changed (11.0, -33.367)/1.047 to
(11.0, -34.000)/0.698 on the strength of a mis-assigned section face, and
that change -- not the dome, and not the crown -- is the outstanding half of
"the U shaped tab is still wrong". Reverting is not a one-line undo: with
the leg's inner face back at -32.320 it sits inboard of the bead's own
outboard extreme (-33.200), so the spine can no longer be held flat up to
`CROWN_Z_LO` (12.400) -- it has to terminate around z = 11 where the
reference's does, and the crown has to bridge from there. That is a
structural change to the U, not a constant tweak.

**Method note.** Two tooling defects were found and fixed in the course of
this, both of which had produced confident wrong readings:
* `slice_compare.draw()` used its `lo`/`hi` window only to set scale and
  origin and **never clipped**, so any "zoomed" view silently drew the whole
  part. A plan section of the latch band accordingly looked like a grid of
  slots in the plate; they were the lid's internal ribs from far outside the
  window. Now Liang-Barsky clipped.
* A single hand-chosen station is systematically biased. X = 12.4 is
  `hook_pitch/2 + hook_width/2` -- the hook's own centreline, the most
  self-similar plane on the feature and blind to everything varying along X.
  `sweep_compare.py` now scores every station and ranks them, splitting the
  score into directed halves (`extra` = material we have and the reference
  does not; `missing` = the reverse) because a symmetric mean hides exactly
  the one-sided defects that matter.

### R26 — BLOCKER: the barb engages nothing; the latch has never worked

Found by `tmp/ldraw/catch_probe.py` after the user observed that no leg
actually hangs on the housing.

Housing material along Y at the barb's own station (X = 12.4):

| z | housing material |
|---|---|
| 9.0 - 12.0 | [-35.60, -34.40] only |
| 12.5 | [-35.60, -34.40] and [-32.13, -30.65] |

The barb sweeps Y in [-33.20, -31.20]. Over the whole engagement band that
range is **void** -- the housing's wall stops at -34.40, some 1.2 mm
outboard of the barb's furthest reach. Measured directly:

    barb cylinder n housing (seated) = 0.000 mm3   (of 42.726 mm3)

**There is no catch. The latch grabs air.** No amount of profile fidelity on
the bead, the crown or the dome changes this; the housing never had a ledge
for the barb to catch.

**How this survived 25 rounds of review.** The seated `Housing n Cover`
volume (7.374 mm3) was quoted throughout as the retention metric, including
in R22 and R24 above, and
`test_latch_catch_seated_engagement_is_the_proven_minimum` asserts
`vol > 0.0` with the comment *"proof it exists at all"*. That volume is a
clash somewhere else in the latch band -- it is not barb engagement, and it
would not be desirable if it were: two rigid printed parts cannot be
assembled through 7 mm3 of interpenetration. The test's bound was ratcheted
across rounds (45.0 -> 25.0 mm3) with increasingly elaborate justification
for the residual, without anyone asking whether a nonzero seated
interference is evidence of a working latch or evidence of a collision. It
is the latter. **A shape-similarity metric was standing in for a functional
one.**

**Required (not yet done):**
1. Give Housing a real catch window/ledge at the barb's band, so
   `barb n housing` is ~0 seated and becomes nonzero under -Z displacement.
2. Replace the seated-interference assertion with a kinematic retention
   test: seated interference ~= 0, and pull-out along -Z blocked by a
   measurable undercut. `tmp/ldraw/pullout.py` is the prototype.
3. Separately, the finger TIP clashes with the housing: the housing has
   material at y in [-32.13, -30.65] for z >= 12.5, and the cover's finger
   occupies [-32.20, -30.80] there -- 3.687 mm3 of seated interference that
   has nothing to do with the barb.
4. R25's leg correction is a structural prerequisite, not cosmetic: the
   reference's legs converge to 0.087 mm by z = 11 and are braced over
   z = 10..13, whereas ours are joined ONLY by the thin diagonal crown
   wedge at the very top. That single small wedge is the entire load path
   from thumb pad to hook -- which is why the U looks like it would break.

### R27 — CORRECTION to R26, and the validated fix (round 27)

**R26 above is partly WRONG and must not be cited for its mechanism.** Its
central measurement -- `barb n housing (seated) = 0.000 mm3`, and the
conclusion "the latch grabs air" / "the barb cannot reach the housing at any
displacement" -- came from a bead probe built on `cq.Workplane("XZ")`. That
workplane's normal is global **-Y**, so `.transformed(offset=(0, 0, dx))`
displaced the bead along -Y instead of +X, and `.center()`'s first argument
was fed a global-**Y** value as a local-**X** coordinate. The probe placed
the bead at X -33.20..-31.20, Y -19.20..-5.60 -- outside the part entirely.
It was measuring empty space. The model's own builders use `"YZ"`
(normal +X); the probes now do too.

**Re-measured correctly**, the bead against the housing:

| dz | bead n housing |
|---|---|
| 0.00 (seated) | 3.701 mm3 |
| -0.20 | 1.725 |
| -0.40 | 0.305 |
| -0.60 and beyond | 0.000 |

**The conclusion that the latch does not retain SURVIVES, for a different
reason.** The barb is not out of reach -- it is *jammed at rest* and the
interference *relieves monotonically as the cover is withdrawn*. Pulling the
lid off gets EASIER. That is a press-fit clash, not a catch, and 3.701 mm3
is the same clash as the finger-tip one in R26 item 3 (the latch head
against housing material at y in [-32.13, -30.65], z >= 12.5).

**The fix, per the user: the barb belongs on the RELEASE LEG's outboard
face, pointing at the housing wall** -- not on the finger pointing into the
U's aperture. Measured feasibility (correct `"YZ"` construction):

| z | leg outer face | free gap to wall (-34.400) | trial bead n housing |
|---|---|---|---|
| 9.0 | -33.822 | 0.578 | 6.567 mm3 |
| 10.0 | -33.911 | 0.489 | 8.613 mm3 |
| 11.0 | -34.000 | 0.400 | 10.780 mm3 |

A bead seated on that face reaches into the housing's 1.200 mm latch skin
(y -35.600..-34.400) with real material to engage. The mechanism is then:
pocket the skin over the bead's seated band so seated interference is ~0;
the solid skin BELOW the pocket is what the bead's undercut bears on when
the lid is pulled. `test_barb_is_reachable_by_the_housing_at_all` is the
acceptance contract and is `xfail(strict=True)`, so it fails the moment this
lands and the marker must come off.

**Method note (third tooling defect this round).** A mis-oriented workplane
in a *probe* produced a confident, specific, entirely fictional number that
was published in R26 and stated to the user. The probes are not covered by
the test suite, so nothing caught it; the tell was that a "trial bead" the
geometry said must overlap the wall reported 0.000. **Any probe asserting an
absence should first be shown to report a presence where one is known to
exist** -- a positive control. R26's probe never had one.

### R28 — The latch now works (round 27 implementation)

Implements R27's plan. The retention bead moved from the latch FINGER (where
it faced the U's own aperture and retained nothing) to the RELEASE LEG's
outboard face, facing the housing wall, into a pocket cut in that wall's
skin.

**Cover** (`_build_leg_barb`): the outboard half of a
``barb_diameter``/2 cylinder seated ON the leg's own outer face at
``LEG_BARB_Z`` = 10.400 -- clear of the thumb-pad window (3.600) below and
the crown (12.400) above, with a full bead radius of margin at each end. The
inboard half is discarded rather than unioned; keeping it would push
material back into the U's spring gap.

**Housing** (`_build_leg_barb_pocket`): reads ``LEG_BARB_Z`` and the bead
radius from the Cover rather than re-typing them. Cut from the skin's inner
face out to ``LEG_BARB_POCKET_Y`` (-35.100), leaving ~0.5 mm of wall behind
the pocket. It does NOT breach the skin -- the solid skin BELOW the pocket
is what blocks withdrawal.

**Measured, before -> after:**

| | before | after |
|---|---|---|
| seated Cover n Housing | 7.374 mm3 (2 lumps) | **0.000 mm3** |
| bead n housing, seated | 3.701 mm3 (jammed) | 0.000 mm3 |
| bead n housing, dz = -0.4 | 0.305 (relieving) | **0.218 (growing)** |
| dz = -0.6 / -0.8 / -1.2 | 0.0 / 0.0 / 0.0 | **1.041 / 2.231 / 5.105** |

The signature inverted: interference used to fall to zero as the lid was
withdrawn (pulling it off got easier); it now rises monotonically.

**Two vestigial features removed, both pure clash once the bead moved:**
* the catch **keeper nub** -- 6.710 mm3 of the 7.374, sitting inside the
  finger's own envelope. It reached behind the barb crest back when the barb
  was on the finger.
* the catch **ledge**'s start was `engagement_band_hi - seam` (12.500),
  inside a finger that reaches `hook_depth` (13.000); now
  `hook_depth + clearance`.

**The test that certified the broken latch failed the moment it was fixed.**
`test_latch_catch_seated_engagement_is_the_proven_minimum` asserted
`vol > 0.0` at the seated position; with the parts no longer colliding, that
assertion could not hold. It is replaced by
`test_latch_catch_seated_interference_is_zero` (seated == 0) working
together with `test_barb_is_reachable_by_the_housing_at_all` (growing under
withdrawal). Both halves are required -- either alone is satisfiable by a
broken part. That pairing, not a single tolerance bound, is the durable
guard.

### R29 — The U's thin fin becomes a solid head (round 27, structural)

User observation on the rendered cover: *"the leg makes sense, however the u
shape would just break, it had very thin edge."* Correct, and measurement
located it -- **not** in the leg. Leg thickness matches the reference closely
where it matters (z = 8: 0.715 vs 0.715; z = 9: 0.709 vs 0.718). The thin
part was the **crown**: a wedge whose root spanned only z 12.000..12.400,
i.e. a 0.4 mm fin -- and it was the ONLY connection between the release leg
and the rest of the part, carrying the entire thumb-pad-to-hook load path.

The reference has no such fin. A section at z = 12 returns a SINGLE span
(-33.19..-31.20): its two legs are fused into a solid head. Ours now does the
same above ``HEAD_Z_LO`` = 11.600, and a section at z = 12 likewise returns
one span (-34.00..-31.20).

**Why the fin existed, and why it no longer has to.** Rounds 22-26 could not
make the head solid because the barb bead sat on the FINGER at z = 12..13 --
exactly where the head goes -- and a solid head buried it (that was R26's
"crown box buried the barb"). Round 27 moved the bead to the release leg's
outboard face at ``LEG_BARB_Z`` (10.400), which vacated the head's volume.
The fin was a workaround for a defect that has since been fixed; removing it
was blocked on the barb relocation, not on anything structural.

**Deliberate deviation from the reference (FDM).** The reference's legs
converge to an **0.087 mm** slot by z = 11 before fusing. That is an
injection-moulded dimension and no FDM process can resolve it -- it would
fuse into a solid blob regardless, unpredictably and with a visible seam.
Ours keeps a printable aperture (1.069 mm at z = 11) and then fuses cleanly
at ``HEAD_Z_LO``. The structural property being copied is *the legs are one
mass at the top*; the 0.087 mm slot is not copied, on purpose.

Unchanged by this: seated Cover n Housing 0.000 mm3, retention 0.218 /
1.041 / 2.231 / 5.105 mm3 at dz = -0.4 / -0.6 / -0.8 / -1.2, single solid,
bbox z 0.000..13.000.

**Still open:** R25's leg-curl correction. The reference's leg turns inboard
above z = 8 (outer face -33.73 -> -33.37); ours holds outboard (-33.73 ->
-34.00). Ours is now the outboard-most material of the head, which is why
the head reads wider than the reference's. Note this is NOT freely
changeable any more: the leg's outer face at z = 10.400 is the seating
surface for the retention bead, and curling it inboard moves the bead's
crest away from the housing wall, so R25 and the latch now interact.

### R30 — DESIGNER REVIEW: the round-27 latch retains but cannot be RELEASED

Designer assessment of the round-27 implementation against the reference.
The implementation passes every test in the suite and is still wrong.

**1. Philo's barb is at z ~ 5, and it is small.** Profiling the reference's
release-leg outboard face at 0.25 mm resolution (`tmp/ldraw/ref_leg_face.py`)
shows a flat -34.000 baseline over z = 3.0..4.75, a local bulge peaking at
**-34.220 at z = 5.00** (0.220 mm proud) and decaying by z = 5.75, then a
monotonic inboard curl to -33.191 by z = 12. That bulge is the barb. Our
`_LEG_OUTER_Y` already carries its peak as the sample `(5.0, -34.220)` --
under-resolved into a triangular ridge by linear interpolation, but present.

**2. The round-27 bead is not in the reference.** The 1.000 mm half-disc at
`LEG_BARB_Z` = 10.400 is the largest single divergence in the part: the
MODEL -> REF deviation run puts its footprint (y -34.95..-33.05,
z 9.23..11.93) at **1.468 mm** max deviation, the worst region of 40.

**3. It cannot be released -- the disqualifying defect.** The release leg is
anchored at the fused head (`HEAD_Z_LO` = 11.600) and free at the thumb pad
(z ~ 0). As a cantilever loaded at the free end, deflection collapses toward
the anchor. Measured (`tmp/ldraw/release_travel.py`):

| bead z | distance from anchor | travel, as % of pad travel |
|---|---|---|
| 10.400 (ours) | 1.200 | **1.5%** |
| 5.000 (reference) | 6.600 | 39.3% |

To disengage a 1.000 mm bead the pad must travel **64.5 mm** with the bead at
z = 10.400, versus **2.5 mm** at the reference's z = 5.000. The lid would
snap shut permanently. Retention was verified kinematically (R28) but
**release never was** -- the same class of gap as R26, one level up: a
mechanism has TWO working directions and only one was tested.

**4. The real root cause was on the HOUSING side all along.** A 0.220 mm
bead cannot reach our latch wall, whose inner face sits at -34.400 -- 0.400 mm
off the leg. The reference's housing must run its wall far closer. Round 27
compensated by growing a 1.000 mm bead on the *cover*, near the anchor where
there was room, instead of correcting the *housing's* clearance. That is a
workaround pointed at the wrong part.

**Recommended (supersedes R28's placement):**
1. Resolve the reference's own bead properly at z ~ 4.75..5.75, ~0.220 mm
   proud, as a rounded profile rather than a single interpolated sample.
2. Bring the housing's latch-wall inner face inboard at that Z band so a
   0.220 mm bead engages, with the pocket and its lower ledge there.
3. Add a **release** test to sit beside the retention one: deflect the pad by
   a plausible thumb travel (~2..3 mm) and assert the bead clears. Retention
   without release is a defect, not a partial success.
4. Only then revisit R25's leg curl -- with the bead back at z ~ 5, the
   curl above z = 8 no longer interacts with the latch, so R25 becomes
   independently fixable again.

### R31 — Round 30: Philo's own mechanism, implemented (supersedes R28)

Implements R30. The round-27 invented bead is **backed out**, not built upon.

**Cover.** `_LEG_OUTER_Y` now resolves the reference's bead at 0.25 mm
sampling -- flat -34.000 over z = 3.00..4.75, peak **-34.220 at z = 5.00**,
decay to -34.170 at 5.50, away by 5.75. Rounds 27-29 carried only the
`(5.0, -34.220)` sample, which linear interpolation smeared across
z = 3.6..8.0: the feature was present the whole time but unusable. The
1.000 mm half-disc at z = 10.400 and its `LEG_BARB_Z` constant are gone.

**Housing.** `_build_latch_land` -- a rail on the wall's inner face standing
proud to `LATCH_LAND_Y` (-34.050), leaving 0.050 mm running clearance
against the leg's -34.000 baseline, spanning z = 3.700..4.500, i.e. strictly
BELOW the bead's seated band (asserted in the builder against
`Cover.BEAD_Z_LO`). This is the correction R30 identified: the retention
failure was always a housing-clearance problem, and round 27 compensated on
the wrong part.

**Measured, latch band only:**

| state | interference |
|---|---|
| seated | 0.0000 mm3 |
| withdrawn 0.40 mm | 0.1039 |
| withdrawn 0.80 mm | 1.7114 |
| withdrawn 0.40 mm, leg deflected 0.10 mm | **0.0000** |

Retains, and releases -- the latter for ~0.25 mm of thumb travel, against
round 27's 64.5 mm.

**Reference fidelity improved as a direct result** (`tmp/ldraw/deviation.py`):
MODEL -> REF agreement within 0.2 mm rose from **41.4% to 87.1%** (excluding
the deliberately-added side handles), mean deviation 0.547 -> **0.079 mm**,
max 1.468 -> 1.396. The invented bead was the single worst region in the
part; removing it in favour of the reference's own feature fixed fidelity and
function together, which is the usual sign that the reference was right.

**Two probe defects found and fixed while measuring, both of which produced
confident wrong numbers:**
* A whole-cover interference sweep is dominated by the **tongue** end
  (y ~ +34), which interferes under any straight -Z pull because the lid
  pivots about it. It masked the latch entirely -- the "worst lump" was at
  y +33.38..+34.40, nowhere near the latch. Measurements are now restricted
  to a latch band.
* `housing.intersect(cover).intersect(BAND)` is **unsafe**: when the first
  intersect is empty CadQuery falls back to the original stack and the second
  returns the band's own volume. Observed as a seated reading of
  2973.180 mm3 where the truth is 0.0. The cover is now clipped to the band
  first. This is the same shape as R27's workplane bug -- a probe returning a
  plausible number for a reason unrelated to the geometry.

**Test contract.** `test_latch_retains_under_withdrawal` (seated zero,
resistance growing) and `test_latch_releases_when_the_pad_is_pressed` (clears
under a 0.10 mm deflection). Round 27 had only the first, passed it, and
shipped a lid that could not be opened.

### R32 — Comparison tooling promoted, and what it says about the hook

The session's ad-hoc probes lived in git-ignored `tmp/` and would have been
lost. The durable parts are now `vibe_cading/tools/surface_diff.py`
(+ `tests/tools/test_surface_diff.py`, 7 tests).

**Unique value vs the existing `boolean_diff.py`** -- they answer different
questions:

| | `boolean_diff.py` | `surface_diff.py` |
|---|---|---|
| needs watertight solids | yes; all-zero on an open mesh (R23) | no -- triangles, so STL/mesh refs work |
| reports | one volume delta | TWO directed deviations |
| scoping | whole shape | `--region` sub-volume |
| finds *where* | residual STEP to eyeball | ranked stations, `--ray` crossings |

**The positive control is structural, not advisory.** `Comparison.agreement`
RAISES `InconclusiveRegion` when either side contributed no samples in the
region. You cannot obtain a clean number from an empty probe -- which is the
exact failure of R26/R27, where a mis-placed bead reported 0.000 mm3 and it
was published as fact. Verified: a region neither shape occupies exits 2 with
INCONCLUSIVE, and a one-sided-empty region also refuses, naming the empty side.

**A design flaw the tests caught immediately.** `sweep_stations` initially
ranked on `a_to_b` alone, making it structurally blind to material we
INVENTED -- the very asymmetry the tool exists to expose. It now ranks on the
worse of the two directions. The fix changed the answer: stations z = 3.00 and
z = 2.50 (extra 1.595 / 1.394 mm) had been invisible because their
`missing_max` was 0.013 / 0.198.

**What it says about the U hook** (region 5.6,19.2,-36,-30,0,13.5):
agreement **70.6%** within 0.2 mm -- against 39.6% whole-lid, which is
dominated by the deliberately-added side handles and tells us nothing about
the hook. Two real clusters remain, both confirmed by `--ray`:

| z | reference | ours | reading |
|---|---|---|---|
| 12.50 | -33.046 | -34.000 | head sits ~0.95 mm too far outboard |
| 12.00 | -33.191 | -34.000 | same |
| 1.50 | -34.104..-33.393 (0.711 thick) | -35.200..-33.893 (1.307) | thumb pad is bulkier and retreats later |
| 2.50..3.00 | -- | extra 1.394..1.595 | same pad bulk |

Cluster 1 **is R25's leg curl**: the reference's leg turns inboard above
z = 8 (-33.73 -> -33.37 -> -33.19 by z = 12) and ours holds at -34.000, so the
fused head inherits the outboard position. Now independently fixable -- the
round-30 bead sits at z ~ 5 and no longer interacts with the curl.

Cluster 2 is new and previously unreported: our thumb pad is a taller,
thicker block than the reference's, which narrows to 0.711 mm by z = 1.5
while ours is still 1.307 mm and reaching to -35.200.

### R33 — Both hook gaps closed; and the case for a conformance manifest

**Gap 1, R25's leg curl -- CLOSED.** `_LEG_OUTER_Y` now follows the reference
above z = 8: -33.733 -> -33.626 -> -33.519 -> -33.367 -> -33.191. Measured, our
leg's outer face now matches the reference EXACTLY at z = 6, 7, 8, 9, 10, 11.
This was blocked from round 27 to 32 because the invented bead used that face
as its seating surface; backing the bead out (R31) freed it.

*Deliberate deviation retained:* leg THICKNESS is not copied. The reference's
aperture closes to 0.087 mm by z = 11, unprintable on FDM. Ours holds
0.436..0.926 mm across z = 6..11 and fuses at `HEAD_Z_LO`. Same rationale as
R29.

**Gap 2, the thumb pad -- CLOSED.** Two errors. `PAD_TOP_Z` was 2.791, holding
our pad proud to -35.200 up to z = 2.8, where the reference's pad is a LIP
ending between z = 1.2 and 1.4 (ray-probed: -35.104 at 1.2, -34.112 at 1.4);
now 1.300. And the profile ramped linearly from (1.0, -35.120) to
(2.0, -34.063), putting our face at -34.592 at z = 1.5 where the reference
STEPS to -34.112; samples added at (1.2, -35.104) and (1.4, -34.112).

**Hook agreement 70.6% -> 73.5%**, max invented material 2.866 -> 0.888 mm.
Latch function unchanged: seated 0.000, retention 0.104/1.711, release at
0.10 mm deflection.

**Why the number stops improving.**

> **CORRECTION (R34).** This paragraph originally said the residual was
> "dominated by things we removed ON PURPOSE", citing the AA battery ribs seen
> at y = -23.6..22.8 in a ray at x = 17.5, z = 3.0. **That is wrong for this
> component.** Those ribs lie outside the latch-U region (y -36..-30) and are
> never sampled by it; an accepted-deviation entry excluding them was a no-op.
> The real 1.361 mm residual is the thumb pad's tall END-WALLS -- see R34. The
> general point below stands; the specific attribution did not.

**This is a structural limit of any whole-part number, not a tuning problem.**
Every figure in this document conflates three categories:

1. **unintended drift** -- real defects (the leg curl, the pad bulk);
2. **intended deviation** -- tray and ribs removed, side handles added,
   FDM-printable aperture instead of 0.087 mm;
3. **reference artifacts** we never intended to copy (moulding detail).

Only (1) should ever fail a gate. Today the three are indistinguishable, so
the aggregate can neither be trusted nor enforced -- which is precisely how a
non-functional latch survived 25 rounds of "the shapes match closely".

**Recommendation (Admin):** a `reference_contracts.toml` registering
*components* -- name, region AABB, model, reference, minimum agreement -- plus
explicitly declared accepted deviations with a reason. Mirrors
`visual_contracts.toml`, which the project already trusts for the same class of
problem (committed == regenerable). The gate then becomes: declared components
must not regress, and any UNDECLARED divergence must be either fixed or
declared with a reason. That converts "the shapes look close" into a
per-component number with intent attached.

*Known blocker:* the reference here is LDraw-derived and must never be
committed (design brief line 278), so this part's rows cannot run in CI. The
check must degrade to skip-with-notice when the reference is absent locally,
and that limitation should be stated in the manifest rather than papered over.

### R34 — Conformance manifest shipped; and a correction

**Built:** `reference_contracts.toml` + `check_reference_conformance.py`
(+ 6 tests), and `surface_diff --worst` / `exclude=` support.

* `accepted_deviation` requires `what` AND `why` -- the checker rejects a
  reason-less entry, because a deviation without one is indistinguishable from
  drift someone stopped fixing. Give it a `region` and its samples are excluded
  from scoring; that is what makes the declaration load-bearing.
* `open_gap` entries carry NO region, so a real shortfall keeps counting.
* `--update` may only RAISE a floor. Lowering one is exactly the ratchet that
  let a non-functional latch survive (45.0 -> 25.0 mm^3 across rounds).
* Absent references SKIP WITH NOTICE and exit 0, stating they are not CI gates
  -- the LDraw source must never be committed, and implying coverage we do not
  have would be worse than the gap.

**CORRECTION to R33.** R33 claimed the latch-U residual was dominated by the
deliberately-deleted AA battery ribs. It is not: those ribs sit at
y = -23.6..22.8, outside the component's own region (y -36..-30), so they are
never sampled and the exclusion entry declaring them was a no-op. Removed.

**What the residual actually is.** `--worst` named the coordinates:
1.361 mm at **x = 6.400 / 18.400, y = -35.377, z = 2.791** -- the thumb pad's
outer corners. Ray-probing there shows the reference holds -35.520 -> -35.384
up to z = 2.700 at x = 6.400, while by x = 7.000 it has already retreated to
-34.023 by z = 2.500. The reference's pad has narrow TALL END-WALLS flanking a
low central lip; our single `PAD_TOP_Z` extrusion cannot express a height that
varies with X.

**And how the error was made.** R33 lowered `PAD_TOP_Z` 2.791 -> 1.300 after
ray-probing **x = 12.400 only** -- the pad's own centre, where the reference
genuinely IS a low lip -- and generalised. Correct for the middle, wrong for
the ends. That is precisely the hand-picked-station error the *Verification
Samples Must Be Chosen By The Data* rule exists to prevent, committed by the
same agent that wrote the rule, and caught only because `--worst` printed
coordinates instead of a number. Recorded as an open gap, not excluded: fixing
it needs an X-varying pad top.

**Net for the latch U:** agreement 70.6% -> **73.5%**, max invented material
2.866 -> 0.888 mm, leg outer face matching the reference exactly at
z = 6..11, latch function unchanged (seated 0.000, retention 0.104/1.711,
release at 0.10 mm deflection).

### R35 — The visible gap in the U was a bad call of mine, not stale geometry

User: *"I'm still seeing the gap in the U shaped hook / tab."* The model in the
viewer WAS current. The gap was real and self-inflicted.

**1. The aperture was held open where the reference's has closed.** Measured:

| z | reference gap | ours (R34) |
|---|---|---|
| 10.5 | 0.305 | 0.527 |
| 11.0 | 0.087 | 0.436 |
| 11.5 | closed | 0.117 |

R29-R34 justified this as FDM printability, fusing only at `HEAD_Z_LO` =
11.600. **The reasoning was wrong.** A 0.087 mm slot does not need to be
printed -- it fuses. Modelling it open buys nothing and shows as a gap. The
fusion point now sits where the reference's own gap drops below printable
(~0.4 mm, z ~ 10.2): `HEAD_Z_LO` = **10.200**. The slot exists exactly where
the reference's is resolvable and is solid where it is not.
*Cost:* free length 11.600 -> 10.200, ~12% stiffer; required pad travel
~0.43 -> ~0.52 mm. Still a light press.

**2. The head was a blunt box.** Lowering the fusion point exposed this: at
x = 13.760, y = -33.199 the reference stops at z = 11.956 while our boxed head
ran to 13.000 -- **5.456 mm** of invented material at the tip, the single worst
sample in the component. The head now sweeps the leg's own outer profile
instead of holding a constant width, and `_LEG_OUTER_Y` gained
(12.5, -33.046) and (13.0, -32.200); without them the profile clamped at
-33.191 and the taper could not exist.

**Result, latch-U component:**

| | R34 | R35 |
|---|---|---|
| agreement | 73.5% | **84.1%** |
| max invented material | 0.888 | **0.800** |
| aperture at z = 11.0 | 0.436 (open) | closed, as the reference |

Latch function unchanged throughout: seated 0.000 mm3, retention 0.104 /
1.711, release at 0.10 mm deflection. Manifest floor raised 73.0 -> 84.1.

**Method note.** The 5.456 mm outlier was invisible in the agreement figure
(which *improved* to 81.3% in the same step) and surfaced only because
`--worst` prints coordinates. An aggregate can improve while a single
dimension gets much worse; the two must be read together.

**Standing correction to R29/R33's printability rationale.** "The reference is
unprintable here, so we deviate" was applied too broadly. The right question is
not *can this dimension be printed* but *what does the printed part look like*
-- a sub-printable slot resolves as fused, so modelling it fused is MORE
faithful, not less. The remaining declared deviation (leg thickness above
z = 8) still stands on its own terms and is unaffected.

### R36 — Loose ends driven: pad end-walls, viewer, CI

**1. Thumb-pad end-walls -- R34's open gap, CLOSED.** The pad is not uniform
in X. Probing z = 2.5 across the hook width: the outer face is -35.400 at
x = 5.8 and 6.2 (mirrored 18.6, 19.0) and absent from 6.6 through 18.2 -- two
walls ~0.800 mm wide at the ends of the hook width, running to z ~ 2.791,
flanking the low central lip. `_build_pad_end_walls` models them.

| | R35 | R36 |
|---|---|---|
| agreement | 84.1% | **89.0%** |
| max missing | 1.361 | **0.217** |

Latch function unchanged (seated 0.000, retention 0.104/1.711, release at
0.10 mm). Floor raised 84.1 -> 89.0. **No open gaps remain.**

**2. The viewer's assembly failure -- MY HYPOTHESIS WAS WRONG.** It was
attributed to payload size ("housing 34 k faces vs cover 1.8 k is the standing
suspect"). It is not. `tmp/viewer_probe_client.py` registers as the viewer
client itself (message type `L`, per `ocp_vscode/standalone.py`) and reports
byte counts, removing the human from the delivery check:

| push | bytes delivered |
|---|---|
| cover | 116,890 |
| housing | 1,172,162 |
| assembly | **1,282,948** |

All four messages arrived intact. Transport handles 1.28 MB fine. The blank
viewer was the registration/restart cause already identified -- `viewer_up.sh`
kills and respawns the server on every run, dropping the browser's
registration, and pushes issued around that land nowhere. Nothing to do with
the housing.

*Method note:* this is the third delivery claim this session. The first two
rested on evidence that could not have shown otherwise (an established TCP
socket to the relay, then a client-side camera warning). A client that reports
byte counts is the first check here that could actually fail.

**3. Reference conformance wired into CI.** New step in
`.github/workflows/ci.yml`. Its comment states the coverage boundary rather
than implying a gate: components whose reference is third-party geometry that
cannot be committed SKIP and exit 0, so CI validates the manifest and
exercises the tooling while the component itself is scored only on a
contributor's machine. The checker prints a NOTE naming every skipped row, so
the gap is visible in the log. Committing a redistributable reference is what
would convert a skip into a gate -- a licensing decision, not a code change.

### R37 — Reframe: the U is a SPRING, and should be modelled as one

User: *"The U shape functions as a spring. Instead of trying to model it
precisely, we may get away with modeling the cross section as a curve, then cut
the middle with another curve."* Correct, and it supersedes the approach taken
in R25-R36.

**Why the fidelity chase was the wrong objective.** Rounds 25-36 drove the
latch-U's surface agreement 70.6% -> 89.0% by matching face positions sample by
sample. That process cannot see the thing that decides whether the part works.
Measured, our aperture terminates ABRUPTLY -- 0.618 mm at z = 10.00, closed by
z = 10.25 -- a flat-bottomed slot end, i.e. a **sharp internal corner at the
most highly and most cyclically loaded point in the spring**. The reference
tapers over ~1 mm (0.523 / 0.414 / 0.305 / 0.196 / 0.087). A sharp corner and a
radiused one differ by a fraction of a millimetre of shape and by a factor of
2-5 in stress; no surface-agreement metric can distinguish them.

**Research** (two subagents, deliverables in `tmp/research/`):

* `spring-latch-practice.md` -- Ticona and Covestro snap-fit guides read in
  full. Nominal root strain here is only **0.15-0.30%** (4x margin on PLA, 8x
  on PETG), so the part is NOT strain-limited and taper is optional. But a
  sharp bend carries **Kt 2-5**, which consumes the entire PLA margin. So the
  **bend radius, not the beam, decides survival**: R_inner >= 1.0 x t.
  Print orientation is non-negotiable (PETG elongation 6.8% XY vs **1.3% Z**).
  Actuation force is only ~0.8-1.25 N -- the design is force-poor, so retention
  and roll-off, not fracture, are the likely failure modes.
* `cadquery-spring-modelling.md` -- 15 executed experiments. **`offset2D` on an
  OPEN wire returns a closed constant-thickness ribbon in one call**; thickness
  measured at 0.800000 +- 3.8e-15 over 400 samples. Measured failure threshold:
  centreline radius must exceed the offset distance (clean to r/D = 1.05, 23%
  area loss at 1.00), headroom r >= 1.5 D. **Failures are SILENT** -- a
  self-intersecting ribbon returns one closed wire, `solids() == 1`, and area
  within 0.01% of nominal; only `isValid()` plus thickness sampling catches it,
  and `isValid()` returns True for the tight-radius collapses. Both checks are
  needed, plus area-vs-nominal.

**Validated prototype** (`tmp/research/proto_u.py`), constrained by our own
envelope -- the leg's outer face must clear the housing retention land at
-34.050, and the finger's inner face lands on `PLATE_Y_LO` = -30.800:

| quantity | value | check |
|---|---|---|
| wall thickness t | 0.800 | 2 x 0.4 mm nozzle |
| centreline separation | 2.400 | |
| centreline bend radius | 1.200 | |
| **inner bend radius** | **0.800** | **= 1.00 x t** (research rec #1) |
| offset ratio r/D | 3.00 | threshold 1.05, headroom 1.5 |
| leg outer face | -34.000 | clears the land by 0.050 |
| finger inner face | -30.800 | exactly PLATE_Y_LO |
| top of wall | 13.000 | exactly hook_depth |

Built: closed wire, 1 solid, `isValid()` True, volume 295.9167 against a
nominal 289.0806 -- the 6.83 difference is **exactly** the two rounded end caps
`offset2D` adds (2 x 0.5*pi*D^2*W = 6.8318), so the ribbon reconciles
analytically rather than merely looking right.

**Deliberate consequence:** a constant-separation hairpin does not reproduce
the reference's converging legs (its centrelines close from 2.39 mm to 1.15 mm).
The reference's own bend, at its 0.70 mm wall, implies an inner radius of
~0.224 mm -- below even Covestro's 0.38 mm absolute floor. That is acceptable
for injection moulding and is not for FDM. We take the correct spring geometry
over the faithful one, deliberately.

**Integration is NOT done.** It replaces `_build_latch_finger` and
`_build_release_leg` with one `_build_latch_u`, and the blast radius is real:
`_LEG_OUTER_Y` / `_LEG_THICKNESS` / `HOOK_FACE_Y0` / `HOOK_FACE_Y1` /
`HOOK_FACE_Z1` / `CROWN_Z_LO` / `HEAD_Z_LO` all disappear or change meaning,
and Housing's `_build_latch_catch` reads `HOOK_FACE_Y1` and `barb_outboard_y`
from the Cover. The bead and thumb pad then re-attach to the ribbon as separate
features, per the user's own decomposition (U body / tab / leg).

### R38 — The U rebuilt as a spring (integration of R37)

`_build_latch_finger` and `_build_release_leg` are gone, replaced by
`_build_latch_u` -- one constant-thickness ribbon from an open centreline via a
single `offset2D`. `_build_leg_bead` re-attaches the retention bead;
`_build_thumb_pad` / `_build_pad_end_walls` re-attach the tab. This is the
user's own decomposition: U body / tab / leg.

| | rounds 18-37 | round 38 |
|---|---|---|
| wall thickness | 0.70..1.44, varying | **exactly 0.800 at every z, both legs** |
| aperture termination | flat slot, 0.618 -> closed in 0.25 mm | arc: 1.600 / 1.587 / 1.439 / 1.058 |
| inner bend radius | ~0 (sharp, Kt 2-5) | **0.800 = 1.00 x wall** |
| U construction | 5 unioned solids | 1 offset ribbon |

Ribbon volume 287.213 against 280.38 nominal + 6.83 end caps -- reconciles
analytically, not merely plausibly. Thickness is now structural rather than
arithmetic, which is why it could drift across twenty rounds and now cannot.

`PoweredUpHubHousing.LATCH_LAND_Y` moved -34.050 -> -34.000: the ribbon put the
leg's outer face 0.050 inboard, which had cut bead engagement 0.170 -> 0.120
and dropped retention at dz = -0.400 to zero. Restored, with the same 0.050
running clearance. Latch verified unchanged: seated 0.000 mm3, retention
0.0097 -> 1.4341, release at 0.10 mm deflection.

**Cost, stated plainly.** Agreement 55.2%, mean deviation 0.228 mm, max
0.801 mm. Real, not an artifact. The conformance gate FAILED and refused to
lower its own floor; the floor was lowered 89.0 -> 55.0 as a reviewed edit with
the reason written into `reference_contracts.toml`. That is the mechanism
working as designed rather than being worked around.

**A measurement bug found and fixed in the process.** `surface_diff`'s
point-to-triangle distance fell back to the nearest VERTEX when a point
projects outside a triangle. Against the 882-triangle reference this reported
**5.456 mm where the true surface distance was ~0.49 mm**. It now uses triangle
EDGES. **Consequence: every fidelity figure quoted before round 38 was a lower
bound** -- the old design's true agreement was >= 89.0%, and pre/post numbers
are not directly comparable. The vertex fallback is only correct when triangles
are small relative to the distances measured, which is exactly when it does not
matter.

**Second self-inflicted error, caught immediately.** The dead-code removal
regex was too greedy and also deleted `PAD_SCALLOP`, `BARB_AXIS_Y` and
`_BARB_ARC_SEGMENTS` (the latter two still needed by `barb_arc_points`, which
Housing's catch calls). The build failed on the next run; restored.

**Still owed:** the bead is a lens intersected onto the ribbon's outer face,
where the reference has a bulge in the wall itself (0.70 -> 1.028 at z = 5.0).
Modelling it as a local widening of the centreline offset would be truer to
both the reference and the spring.

### R39 — Thicker bend; and the tongue ("peg") compared

**Bend thickened (user-directed).** `U_BEND_WALL` = 1.050 gives a measured wall
of **1.038 at z = 11 against 0.800 down the legs** -- the reference's own bend
measures 1.047, so this matches it rather than departing from it. Achieved by
flaring the OUTER surface from `U_FLARE_Z` = 8.000, **not** by shrinking the
inner radius, which stays 0.800 (= 1.00 x leg wall); shrinking it would raise
the stress concentration the radius exists to prevent.

This required abandoning `offset2D` for the U -- a single offset cannot vary
thickness -- in favour of the two-explicit-profile build (the alternative the
CadQuery research validated). The inner arc is unchanged and still closes the
aperture smoothly (1.600 -> 1.519 -> 1.248 -> 0.555 -> closed).

| z | our leg wall | reference |
|---|---|---|
| 2..8 | 0.800 | 0.699..0.770 |
| 9 | 0.879 | 0.718 |
| 10 | 0.959 | 0.799 |
| 11 | **1.038** | **1.047** |

Latch function unchanged: seated 0.000 mm3, retention 0.0097 -> 1.4341,
release at 0.10 mm deflection.

**First attempt overshot.** `U_BEND_WALL` = 1.200 put the leg's outer face at
-34.350 -- 0.050 mm off the housing wall -- and scored 41.3%. Backed off.

**Cost, and its cause.** Agreement 55.2% -> 46.1%. The flare is SYMMETRIC, so
the finger thickens too (0.800 -> 1.038) where the reference's finger stays
constant (1.086 -> 1.073) and only its leg thickens. That accounts for the
whole drop. **Flaring the leg side alone would recover most of it** and is the
obvious next refinement. Floor lowered 55.0 -> 46.0 as a reviewed edit.

**The tongue / "peg" -- 91.1% agreement, and thickness is NOT the difference.**
Measured across X, our tongue matches the reference exactly at every station:
0.000..2.800 at the riser, 1.874..2.800 at the tip, 0.000..1.200 at the outer
band. What differs is that **the reference's tongue is SEGMENTED**: rays along
X give four blades --

| band | x range |
|---|---|
| outer left | -26.000 .. -17.200 |
| inner left | -15.600 .. -0.800 |
| inner right | 0.800 .. 15.600 |
| outer right | 17.200 .. 26.000 |

-- with 1.600 mm gaps between them, where ours is one continuous slab. The
worst deviations sit exactly on those boundaries (x = +-15.600 and +-0.800),
the reference carrying slightly more material at each segment edge. Those
edges are what reads as "reinforcements at both edges"; they are a consequence
of the segmentation, not ribs added to a solid blade.

**Implemented in round 45 (see below).**

### R45 — The tongue is segmented

User direction, on the round-39 finding above. Three gaps cut in
`_build_tongue`: the centre (`|X| <= TONGUE_GAP_X_INNER` = 0.800) and one
either side at `TONGUE_X_HALF .. TONGUE_RIB_X_HI` (15.600..17.200), each
spanning the tongue's whole Y and Z extent. Cut as gaps rather than built as
four bodies, so `TONGUE_X_HALF` / `RISER_X_HALF` keep their meaning as the
tongue's outer bounds.

**Read off the built solid, not asserted from the constants.** Rays swept
along X (`tmp/tongue_segments.py`, and the same probe inside
`test_tongue_is_segmented_into_the_reference_four_blades`):

| station | occupied X bands |
|---|---|
| riser, z = 0.600 | −26.0..−17.2, −15.6..−0.8, 0.8..15.6, 17.2..26.0 |
| ledge / tip, z = 2.3–2.4 | −15.6..−0.8, 0.8..15.6 |
| **plate, y = 31.800 (positive control)** | **−27.2..27.2, one band** |

The four riser bands are the reference table above, exactly. The tip shows
only Tongue A because Tongue B stops at `TONGUE_STEP_Y` (T5). The plate
control is what distinguishes this from a probe that finds nothing anywhere.

**Falsifier demonstrated, not just stated** (`tmp/tongue_falsifier.py`): a
subclass rebuilding the pre-round-45 continuous slab returns ONE band at
every tongue station and the test fails on it — `expected 4 blades at
y=32.2, z=0.6, got [(-26.0, 26.0)]`. *A first attempt at this control
collapsed the gap widths to zero instead; a zero-width cutter is degenerate
and OCCT mangled the solid, so its "1 band" result was an artefact and not
evidence. Rebuilding the slab honestly was the fix.*

**Cost and gain.** Same region, same tolerance, A/B on the two shapes:
worst-direction agreement **91.2% → 98.8%** (`ref → ours` mean 0.035 → 0.001,
max 0.585 → 0.320). Retention is unaffected — the blade bears on the housing
ledge in Z, and the centre gap costs 1.600 mm out of a 31.200 mm blade.

**What was still missing at the end of R45.** The housing's tongue wall was
still full width, so the slots were there but no rib entered them. Closed in
R46 below.

### R51 — The trapezoid socket on the two END walls

User direction at the round-50 checkpoint: the same mating socket the ±X side
walls got in R50 is wanted on the latch end (−Y) and the tongue end (+Y).

**Measured first, per the queued warning — and the warning was right.** The
±X numbers do NOT transfer. Ray-casting `25560.dat` along ±Y
(`tmp/ldraw/end_wall_socket.py`, then `end_wall_extent.py` bisecting for the
X at which the outer skin at `|Y| = 35.600` reappears) gives, **identically on
both ends**:

| Z | recess extends to |
|---|---|
| 22.10 | \|X\| ≤ 14.100 |
| 22.50 | \|X\| ≤ 14.500 |
| 23.10 | \|X\| ≤ 15.100 |
| 23.90 | \|X\| ≤ 15.900 |

i.e. `|X|max = Z − 8.000` exactly. Below `Z = 22.000` the skin is continuous;
above `DECK_Z` the whole shell steps in, which is the separate, already-modelled
narrowing. So: an isosceles trapezoid, narrow edge down, half-width
**14.000 → 16.000** over **Z 22.000 → 24.000**.

What *is* shared with the side sockets is only the Z band and the 45° flank
angle — the half-widths differ (14.0/16.0 vs 9.2/11.2) and so does the depth.

**Depth = 1.200**, floor at `|Y| = 34.400`. In the reference the recess removes
the 35.600 → 34.400 outer skin outright: both crossings vanish together and the
next material is a separate inner shell. On *this* part that stays a blind
pocket rather than becoming a hole, because our end walls are thicker than the
reference's skin where the recess lands — 4.800 mm at the latch end
(`LATCH_WALL_THICKNESS`), and above the bay the solid deck at both ends. The
test asserts that explicitly at nine stations across the footprint, because
"pocket, not hole" is exactly the property that would silently degrade if a
wall thickness moved.

**Positive control before the measurement was trusted:** the same probe run
along ±X reproduces the known side-wall socket (28.000 outside the recess,
27.200 inside, flank crossing between 9.2 and 11.2). A probe that cannot see
the socket already measured cannot be trusted to report one elsewhere.

**Where the cut sits in `_build`:** after the deck union, not before — above
the bay the socket's floor *is* deck material, so an earlier cut would be
undone by the union. Both overcut directions were checked rather than assumed
(the R48 lesson): outboard of ±`HALF_Y` and above `DECK_Z` are both outside the
part's bounding box (Y ends at 35.600, Z at 24.000), so neither can reach
occupied space. The vertical overcut extends the mouth straight up instead of
continuing the flanks, so it cannot widen the socket past
`END_SOCKET_X_HALF_HI`.

**Interactions checked.** The arms sit at `|X| ≈ 32` (`HOLE_X`), well outside
the socket's `|X| ≤ 16`, so nothing is clipped. Seated interference against the
Cover and `test_interior_clears_the_target_battery` both re-run clean — the
socket is above the bay's top and cuts inward from the outer face, so it does
not touch the pack envelope.

**No reference-conformance row added, deliberately.** The end walls are already
declared as a single-wall departure from the reference's two skins, so a
surface-diff percentage over this region would score our solid pocket floor
against the reference's open cavity and produce a number that measures the
declared deviation, not this feature. The ray-cast agreement is both exact and
already pinned by `test_end_walls_carry_the_trapezoid_mating_socket`, which is
the stronger evidence.

### R52 — The battery tray comes back, reshaped, and the tab goes with it

Prompted by the height investigation above: the user measured (real Hub,
physical part) at least 2 mm of headroom over the 20.9 mm pack even with the
reference's own ridges present, versus this design's 0.300 mm — a gap traced
to the round-22 decision to cap the housing at 3 studs, not to any wall
thickness error (both the housing's ceiling and the cover's plate already
match the reference exactly, verified this round with a full-footprint,
data-ranked sweep of `25560.dat` rather than a hand-picked station). Before
resizing the housing, the user asked to design the tray first: **"add back
the battery tray (move the tab from the cover to the battery tray as well). I'd
like to use a U shape, without the front and back wall. The bottom should have
battery strap holders."** The housing height decision is explicitly deferred
to a follow-up round.

**Recovered, not reinvented.** A `PoweredUpHubBatteryTray` existed from round
13 through round 22 (`git show <pre-deletion-sha>^:.../battery_tray.py`); it
already had side-mounted extraction tabs, a raised floor, and two strap-holder
slots (`STRAP_WIDTH = 20.5`, sized for a 20 mm strap — independently arriving
at almost exactly this session's own 20 mm target). It was deleted because a
full 4-walled box didn't fit under the 3-stud cap. Its numbers were **not**
copied blind: `WALL_INNER_STEP_Z` moved `22.000 → 21.200` (world) since round
50's side-wall rewrite, `DECK_THICKNESS` moved `2.000 → 1.600` since round 47,
and its own `WALL_Z_HI = 26.400` (local) would have driven the wall straight
into empty air above the current, much-shorter housing (world ceiling is now
`22.400`, not the ~27.6 mm the old class assumed). Every reused constant was
re-derived against today's geometry; see the class's own per-constant
provenance comments.

**U shape removes an entire class of collisions, not just two walls.**
Rounds 13–22's own history is a sequence of relief cuts fighting collisions
between the tray's flat-bottomed END walls and Cover's raised low-Z features
— the tongue riser (round 18, moved the relief to `-Y`), then the hairpin
spring's release leg (same round, moved it back to `+Y` with a Z restriction).
Deleting both end walls outright deletes the collision class itself: this
tray needs no relief cut anywhere. In its place, the two side walls' own Y
reach is bounded by a plain `0.100 mm` safety margin short of
`PoweredUpHubCover.LATCH_BAND_Y_HI` (`-30.000`) and `GROOVE_Y_LO` (`30.000`)
— derived live from Cover's own constants, so the two parts cannot drift back
into collision silently.

**The tab moves back to where the reference actually puts it.** Round 22 had
re-homed it onto Cover only because the tray was gone; the real 24853 lid
never had one. Cover's round-47 tab implementation (the improved 3-edge
border, correcting rounds 22–46's flat top-ledge-only version) is the one
ported, not the older, cruder pre-round-45 tray tab — every Z constant is
re-based by the Tray's own seat offset (`PoweredUpHubCover.PLATE_THICKNESS`,
1.200 mm), with X/Y unaffected. One real consequence, not an error: the
tab's usable Z reach shrinks from 8.400 mm (world, flush with the whole
assembly's absolute bottom when it lived on Cover) to 7.200 mm (local, flush
with the Tray's own bottom rim, which itself now sits 1.200 mm up) — the tab
can no longer physically reach down to world `Z = 0`, since that space
belongs to the separate Cover part. `PoweredUpHubHousing._build_side_window`
was repointed to derive from the Tray instead, converting the Z-valued
constants through the same seat offset; the window's own cut geometry is
byte-for-byte unchanged (verified: worst-case gap to the seated tab across
the whole round-over is exactly `0.150 mm`, the running clearance, both
before and after the move).

**A genuine construction bug, caught by the single-solid assert, not
guessed.** The first version of the wall's two X-bands (matching Housing's
own lower/upper split at `WALL_STEP_Z`) used independent per-side slabs that
do not share any X range — Housing's cavity genuinely narrows above the step
(inner face `27.200 → 26.400`), so the tray's own wall must narrow to match,
and the lower band's legal footprint (`X ∈ [26.400, 27.200]`) and the upper
band's (`X ∈ [25.600, 26.250]`) are disjoint. A plain Z-overlap between two
X-disjoint slabs does not connect them — `_build()`'s own
`assert len(part.solids().vals()) == 1` caught this immediately (4 solids).
Fixed with a small bridge slab at the seam, wide enough in X to be a superset
of both bands' footprints. The bridge's own first version then reintroduced
a **different** bug the single-solid assert could not see at all: it
overshot `WALL_STEP_Z` by the same seam-safety `overlap` every other band in
this codebase uses, at the WIDE cross-section — driving `4.784 mm³` into
Housing's own thickened wall material. Nothing in the single-part build
caught this; only a `Tray × Housing` interference check did. Recorded because
it is exactly the *Overcuts on the non-waste side* pitfall in
`vibe/INSTRUCTIONS.md`, on a UNION this time rather than a cutter: an overlap
that is safe in one direction (below the step) is not safe in the other
(above it), and "add a bit of overlap for seam safety" is not a
direction-agnostic default.

> **Superseded by R57.** The two-band wall and its bridge slab no longer
> exist. The bridge made the part *connected*, which is what the single-solid
> assert measures, but it never made the upper band *supported*: two
> X-disjoint slabs joined at a hairline ledge is a wall standing on nothing
> over its inboard half. The user saw it directly — "this creates a floating
> region" — and directed that the narrow part be removed. See R57 below.

**Deliberately not asserted: the pack fits.** Inserting the Tray's floor
(standoff `2.700 mm` + thickness `1.500 mm`, sized for the `2.000 mm` target
strap) between the Cover and the pack consumes headroom the current housing
never budgeted for — the interior was already only `0.300 mm` proud of the
bare pack with no tray at all. `tests/lego_adapters/test_poweredup_hub_battery_tray.py`
tests this class's own structural correctness and its zero interference
against both seated neighbours; it does not claim a fit that does not exist
yet. `test_interior_clears_the_target_battery` in the housing test file is
untouched and remains the single source of truth for that question, pending
the deferred height round.

### R53 — The strap runs the other way, and the battery's own footprint gates it

User correction on R52's strap holders: **"The strap should run across
another direction (along with the two thumb tabs in the tray). Make sure my
battery (the spektrum model I shared earlier) first in. The strap has 20mm
width."**

R52's first attempt had the direction backwards: both slots sat at
`X = 0` with two different `Y` offsets (`+-18.0`), each individually wide in
X — a pair of local loops beside the pack, not a strap that crosses over it.
The user's framing (this session, and the original pre-tray request: *"cut
two straight sockets on near each tab, so the strap can run through"*) wants
the strap running in **X**, alongside the two extraction tabs (one per side
wall) — over the pack's top, anchored near each wall.

Fixed by transposing the slot geometry and repositioning it: both slots now
share one `Y` (the tabs' own centreline, `Y = 0`) at two `X` positions,
`STRAP_HOLDER_X = +-22.000` — inboard of the floor's own edge
(`WALL_INNER_X = 26.400`) for print strength, and, per the user's "make sure
my battery fits" instruction, **verified outboard of the target pack's own
half-width** (Spektrum SPMX812SH2, `32.000 / 2 = 16.000 mm`) by
`test_strap_span_crosses_the_target_battery_footprint` — a holder position
inboard of the pack would pass every other strap test (slots exist, floor is
raised) while silently retaining nothing, which is exactly why this is a
named, separate test rather than folded into the slot-existence check.
`STRAP_WIDTH` (20.5 mm, sized for the user's stated 20 mm strap) is
unchanged from R52; only its axis moved, from the slot's `depth` (Y) to its
own `depth` again but now spanning Y at each of the two X stations, i.e. the
slot is now wide in Y and narrow in X, the transpose of before.

Zero interference re-verified against both seated Housing and Cover after
the change (unaffected, since the slots stayed within the floor's own X/Y
envelope, just relocated within it).

### R54 → R55 — The floor is split off, merged back, and given a strap channel

R54 acted on user direction for printability: **"think of the design to
make it easier to print. I would make a separate flat plate, and glue it
to the tray."** R52-53's floor was an integral shelf raised on a
`2.700 mm` standoff to open a strap-routing crawl-space beneath it — a
shelf bridging the tray's full ~53 mm width over open air, unlike the two
side walls beside it (plain upright profiles that print from the bed up).
R54 split it into its own class, `PoweredUpHubBatteryTrayFloor`: a flat
plate sitting flush at the shared `Z = 0` seating datum (no standoff at
all, since a separately-glued plate needs no clearance under it), sized to
drop inside the Tray's walls with a running-clearance gap.

**R55 reverts that split, by user direction: "Merge the tray back together
(walls and bottom plate)."** `PoweredUpHubBatteryTrayFloor` is deleted, not
merely unused, and the floor is integral to `PoweredUpHubBatteryTray`
again. Topology follows: under R54 the Tray was legitimately *two* bodies
(with no floor and no end walls its side walls did not touch) and
`_build()` asserted `== 2` with a per-half `isValid()`; R55 restores
`== 1`, and since the floor is the only thing joining the two walls that
single assertion doubles as the floor's own seam-overlap regression net.

**But merging alone would have reinstated the bridged raised floor**, so
the floor was re-datumed in the same round, on the design the user supplied
as a marked-up sketch. It is now flush with the tray's own `Z = 0` bottom
rim (`FLOOR_THICKNESS = 2.700 mm`) and prints flat on the bed; the strap's
routing space is no longer a gap *under* a raised shelf but a channel cut
*into* a thick floor. Three features implement the sketch:

1. **The corridor** (sketch: centre band, "completely cut … so the strap
   holder sockets got connected") — one opening through the floor,
   `STRAP_WIDTH = 20.500 mm` wide in Y, spanning `|X| ≤ 23.150`, which is
   exactly the union of the two R53 slots with the span between them. Entry
   and exit are therefore unchanged and still outboard of the pack's own
   16.000 mm half-width.
2. **The rebate** (sketch: hatched flanks, "make this area thinner") —
   `STRAP_CAP_THICKNESS = 1.200 mm` taken off the floor's **TOP** face on
   both Y-flanks of the corridor, leaving a `1.500 mm` ledge under it. A
   blind pocket: `+Z` opens into the tray's interior and is overcut, `−Z`
   stops dead. Tested in both directions, since "material gone above"
   alone is satisfied by a rebate that cut clean through — and the
   rebate's own X/Y bounds are guarded by a wall-WIDTH assertion, the R48
   lesson about an overcut aimed at an unchecked direction.
3. **The cap** (sketch: outlined plate) — `PoweredUpHubBatteryTrayCap`, a
   flat plate exactly the rebate's depth, dropped in from above and glued
   flush with the floor's top face. Prints flat with no supports; that is
   the whole reason it is separate — printed in place it would be a bridge
   over the corridor. Its thickness and footprint are *derived* from the
   Tray (`STRAP_CAP_THICKNESS`, `cap_rebate_half_extents(profile)`) rather
   than re-stated, so the two halves of the joint cannot drift apart.

**Orientation matters, and a first attempt at this round had it upside
down** — rebate in the underside, cap glued on below, channel above the
plate. The user corrected it: *"The strap cap should be installed ON the
tray bottom. The channel goes beneath the bottom plate."* Two independent
reasons the correction is right, both of which the inverted version fails:

* **Printability.** A pocket in the TOP face opens upward, so the ledge
  under it prints straight off the bed. An underside pocket leaves its
  flanks starting `1.200 mm` up in the air, bridging — reintroducing
  exactly the fault this redesign exists to remove. `R55`'s
  `test_the_rebate_opens_upward_so_nothing_bridges` asserts a fully solid
  column beneath the rebate down to `Z = 0`, and fails if the rebate is
  flipped back. Every other test passes either way up, which is precisely
  why that one is written.
* **What the pack lands on.** Cap flush at the top ⇒ the pack rests on one
  continuous surface. Cap below ⇒ the pack spans a `20.500 mm` open slot
  down the middle of the floor.

So the channel is bounded below by `PoweredUpHubCover`'s own face (the
tray's floor is flush at `Z = 0`, so the corridor opens straight onto it)
and above by the cap. Clear height `2.200 mm`. The strap loops up out of
it at the corridor's two ends — outboard of the pack — over the battery's
top, and back down.

**Headroom**: net stack under the pack is 2.700 mm, against R52-53's
2.700 + 1.500 = 4.200 mm -- 1.500 mm recovered. Both numbers behind that
came from the user measuring the real strap ("less than 1.5mm", "channel
just need 1.5mm"), so `STRAP_CHANNEL_HEIGHT` is an outright 1.500 constant
rather than `strap + margin`: a margin here is headroom the housing has to
pay for. Clear channel height is verified at 1.500 mm on the built solids
rather than re-derived from the constants.

**Rejected alternative, recorded rather than dropped.** The user also
offered: put the strap holders in the lower side walls and print everything
as one piece. It does not fit. This tray's lower-band outer face is at
`|X| = 27.200` and `PoweredUpHubHousing`'s lower-band inner face is *also*
27.200 — a strap leaving sideways has exactly zero mm of space to run in.
The two-part glue joint is the cost of the channel, and it is a small,
unloaded plate rather than R54's whole floor.

Zero interference re-verified for both the merged Tray and the Cap against
Housing and Cover. `assembly.py` places four parts.

### R46 — The housing's tongue wall gets the mating ribs

User direction, closing R45's own open end. `_build_tongue_ribs` builds the
three mirrored rib pairs §12.2 measures — T1/T2 give the slot side walls at
`|X|` = 0.800 / 15.600 / 17.200 / 26.000, T3 the ribs between them at
`|X|` 15.600–17.200 and 26.000–28.000, plus the centre wall inboard of 0.800
that separates the two Tongue A slots.

**Fit.** Nominal reference walls on both parts would be a zero-clearance
literal-to-literal butt, so every rib flank that faces a Cover blade is pulled
back by `profile.free.radial` (0.150 mm) — the same running-fit knob the
tongue's own back wall already routes its insertion datum through. The outer
band's 28.000 flank is the shell's own outer face with no Cover material
outboard of it and takes no clearance.

**One collision found and fixed at its cause, not by widening a bound.** A
first cut ran every rib back to the plate edge (`PLATE_Y_HI`) and reported
0.130 mm³ of seated interference at `X` ±0.650, `Y` 32.150–32.400,
`Z` 1.200–1.600. That is the Cover's *notch floor* — `_build_ledge_teeth`
lays a continuous band across the full ledge width over
`[TEETH_Y_LO, TEETH_Y_HI]`, and it crosses the centreline, so the centre slot
is only open from `LEDGE_Y_LO` forward. Each rib now starts where its own slot
actually opens: outboard of `LEDGE_X_HALF` at the plate edge, inboard of it at
the ledge front face.

**Read off the built solids, both parts, same window.** Slab at
`Y` 32.600–33.178 (`LEDGE_Y_LO`+0.2 to `TONGUE_STEP_Y`−0.2), `Z` 0.2–1.0:

| part | occupied X bands |
|---|---|
| Cover | −26.0..−17.2, −15.6..−0.8, 0.8..15.6, 17.2..26.0 |
| Housing | −28.0..−26.15, −17.05..−15.75, −0.65..0.65, 15.75..17.05, 26.15..28.0 |
| **positive control** (Cover, `Y` 10–12) | **−28.0..28.0, one band** |

One rib per slot, 0.150 mm off each blade flank. The control is what
distinguishes this from a probe reading the wrong plane.

**Falsifier, measured as a delta against a rib-free baseline** so the rest of
the part's own contacts cannot supply the signal (`_RiblessHousing` in
`test_poweredup_hub_kinematic.py`). Seated interference alone cannot fail the
claim — a rib built entirely outside its slot reports 0.000 mm³ exactly as a
working one does:

| displacement | rib contribution |
|---|---|
| seated, and ±X within the 0.150 mm clearance | 0.000 mm³ |
| ±X 0.20 / 0.30 / 0.50 mm | 0.440 / 1.320 / 3.079 mm³ |
| −Y 0.25 … 4.00 mm (withdrawal) | 0.000 mm³ at every step |

The ribs engage at exactly the designed threshold, harder the further it goes,
symmetrically in −X, and never resist the lid sliding out — the tongue end is
a lap, not a snap. Housing volume +20.524 mm³; still one solid.

**What these ribs are and are not.** §12.4 is explicit that they are the
*optional* X-location: the shell's own side walls at `|X|` 27.200 already
locate the lid. The measurement agrees — the Cover's plate edge butts that
wall at **zero** clearance along the part's whole length, so it is the primary
locator and the ribs at 0.150 mm only tighten it. Retention at this end is
still the rebate bearing in Z.

**Still open.** There is no housing reference STL under `tmp/ldraw/` (only
`ref_lid.stl`), so unlike R45 this round has no `surface_diff` agreement number
over the tongue region and no `reference_contracts.toml` row — the evidence
above is direct interleave and kinematic measurement, not surface conformance.
Producing `ref_housing.stl` needs the housing's own LDraw→model transform
established and positive-controlled first; a wrong transform would yield a
confident, meaningless percentage.

### R40 — The housing still encoded the old barb; and two clearances were zero

Round 38 rebuilt the cover's latch as a hairpin spring. The housing was never
brought along: it still carried the mating half of a barb-on-the-finger that
no longer exists, and two of its clearances against the new geometry had
silently gone to zero.

**Finding 1 — `_build_latch_catch` was dead, and had been for two rounds.**
Measured, not inferred (`tmp/catch_contribution_probe.py`), with the retention
land removed as the positive control:

| piece | contribution |
|---|---|
| slot cutter | overlaps **0.0000 mm³** of the built wall — cuts nothing |
| keeper nub | not unioned since round 27 |
| boss | 5.814 mm³/side, entirely a 0.150 mm overhang above the crown |
| control: drop the land | −8.704 mm³ (so the method does detect real loss) |

The boss's overhang duplicates what the wall itself already provides above
`hook_depth`. The whole method is removed, and with it `_LATCH_CATCH_Z_MARGIN`,
`_LATCH_CATCH_RETREAT_Y`, `_MIN_MATERIAL_BEHIND_UNDERCUT`, and the cover's
`HOOK_FACE_Y0/Y1/Z1`, `BARB_AXIS_Y`, `_BARB_ARC_SEGMENTS`, `barb_arc_points()`
and `barb_outboard_y()` — the last four were public API describing a feature
the part does not have.

**Finding 2 — the crown was butted against the wall.** `_build_latch_clearance`
cut its channel to `engagement_band_hi`, which for this geometry is the same
number as `hook_depth`, so the wall resumed at exactly the crown's top face.
Measured headroom **0.024 mm** at the apex — nonzero only because the arc falls
away either side — against 0.150 mm everywhere else on the interface. A crown
held against the ceiling preloads the spring and holds the lid off its seat.
Now `hook_depth + clearance`.

**Finding 3 — the thumb pad had no room in its window.** `_build_finger_windows`
cut to the `LATCH_WINDOW_X_LO/HI` literals, which happen to equal the hook
footprint exactly: a 13.600 mm pad into a 13.600 mm slot, **0.000 mm on both X
edges**, while the U leg's own channel next door carried 0.150 mm per side. Now
`hook_width + 2 × clearance`, with an assert tying the literals to the hook
footprint so they cannot drift apart.

**Why nothing caught findings 2 and 3.** A gap of exactly zero encloses no
volume. `test_general_body_seated_interference_is_zero` scored both at
0.000 mm³ and passed — the same unfalsifiable-check pattern as R30's
`assert seated_interference > 0.0`, in a new disguise. Two tests now pin the
gaps directly, and both were confirmed to fail on the restored old geometry
(`tmp/verify_round40.py`: 0.000 mm measured either way against a 0.150 mm
requirement) before being accepted.

That test also loses its carve-out. It had excluded the catch's footprint since
round 18 on the grounds that the catch made "a geometrically UNAVOIDABLE seated
engagement" — which was never true of a working mechanism between two rigid
printed parts. Seated interference is now asserted zero everywhere.

**Still open.** `LatchGeometry.barb_protrusion`, `undercut_depth`, `catch_width`
and `ramp_angle_deg` now have no consumer — they describe the retired barb.
Left in place so this round stays reviewable; they should go in a follow-up.

### R41 — The side window is now the tab's own outline

The housing's side window and the cover's side tab are one feature in the
reference (both measure ±12.000 half-width, shoulder at 4.800, flat top
±8.400 at 8.400), but they were modelled as two:

* the **tab** as a true `R3.600` corner round-over;
* the **window** as `WINDOW_TAPER_PROFILE = ((6.000, 11.761), (8.000, 9.966),
  (8.400, 8.400))` — three points sampled off the reference's own faceted arc
  and joined by straight lines.

A chord lies inside the arc it subtends, so the window was narrower than the
tab at every *intermediate* Z while matching it exactly at the three sampled
ones. The previous round's response was to shrink the whole tab by
`_HANDLE_CHORD_ALLOWANCE = 0.320` on top of the running clearance — deleting
0.320 mm of material the reference has, from the part, to fit a hole that was
the thing modelled wrong. The constant's own comment named the mechanism
("a chord always lies inside the arc it subtends") and sized the allowance from
the measured penetration, so the diagnosis was right and only the direction of
the fix was wrong.

**Now:** the window is the tab's outline offset outward by the running
clearance. The offset is exact rather than re-derived, because the round-over's
centre is at `(HANDLE_ROUND_CZ, HANDLE_LEDGE_Y_HALF)` and its tangent points are
the side face and the top face — so offsetting by `c` moves the sides to
`PAD_Y_HALF + c`, the top to `PAD_Z_HI + c`, and keeps the arc centre with
radius `ROUND_R + c`.

The clearance moves to the window, which is the hole rather than the shaft and
the right side of the pair for it. The tab goes back to nominal: measured bbox
now `Y ±12.000, Z 0..8.400`, i.e. the reference's own figures.

| window | worst gap over the round-over |
|---|---|
| round-41 arc | **+0.150 mm** (uniform — it is a true offset) |
| control: retired chord window, nominal tab | **−0.452 mm** at z = 8.315 |

The sweep matters here: probing only the shoulder and the top reports a clean
fit for *both* windows, because those are the stations the chords were sampled
at. `test_side_window_is_the_handle_outline_across_the_whole_round_over` sweeps
41 stations and ranks on the worst.

### R42 — The liftarms: plain beam, real pin cutter, blind middle hole

User direction: keep the arms to *the main beam and the holes*, and use the
hole cutters. Two things came off, one went in.

**Off — the face dishing.** `_dish_arm_faces` cut the real liftarm's recessed
pockets into both faces (floors at local Z 5.378 / 2.622, a 2.756 mm web,
blended by R3.600 reliefs and opened between holes by two R2.000 gap circles).
It reproduced the reference faithfully — the derivation even showed the pocket
half-width `2.546 = 3.600 · cos 45°` fell out of LDraw's own polygon. It is
still the wrong shape to *print*: it thins the section of a cantilevered arm
exactly where bending stress peaks, and asks the machine to bridge a thin web.
This is a **deliberate, declared departure from the reference in favour of
strength** — the arm's function (hole positions, pitch, envelope) is unchanged.

**Off — the hand-rolled middle bore.** Three cylinder segments
(`MID_BORE_CB_DIAMETER` / `MID_BORE_DIAMETER` / `MID_BORE_RELIEF_DIAMETER`,
`MID_BORE_GUIDED_LEN`) re-implemented a counterbored pin hole without being
one, so it never got the profile-aware bore sizing every other pin hole in the
repo has. Its `_MID_BORE_BREAKTHROUGH = 15.0` relief also punched clean through
the side wall into the battery cavity.

**In — a real `TechnicPinHole`, blind.** Entered at the boss tip
(`|X| = 36.000`) and floored at the side wall's outer face (`|X| = 28.000`), so
the 0.8 mm wall survives and the cavity stays closed. Depth is that distance,
not a literal — and it comes out at exactly one stud pitch, so the hole is
full-depth *and* blind. Both readings are asserted rather than left to hold by
coincidence.

Measured on the built solid, outboard → inboard along the hole axis:

| \|X\| | 35.9 | 32.0 | 28.4 | 27.9 | 27.6 | 27.3 | 26.5 | 22.0 |
|---|---|---|---|---|---|---|---|---|
| material | — | — | — | **solid** | **solid** | **solid** | — | — |

Bore Ø 4.96 measured against 5.020 nominal (`PIN_HOLE_DIAMETER + 2 ×
slip.radial`), counterbore Ø 6.14 against 6.200 — both within the ~0.05 mm
probe-width bias.

### R43 — Measuring Philo's arm, and building it instead of trimming it

The round-42 arms still came from the shared `PerpendicularHolesLiftarm` squared
off with three flat trims. Measuring the reference showed why that could never
look right — and that the reference already solves it.

**The arm.** From `s\24851s01.dat`:

```
1 16 80 -10 80   9 0 0 / 0 20 0 / 0 0 9   1-4cylo.dat
```

The end cap is **radius 9 LDU = 3.600 mm, centred exactly on the outer hole**,
and the arm is **7.200 mm wide** (not the shared class's 7.800). Cap radius
equals half-width, and its centre is the hole centre — so centred on the hole at
32.000 it comes out **exactly tangent to 35.600 in both plan directions**. In the
real part nothing is trimmed; the envelope is a *consequence* of the geometry.

Ours was the generic beam (7.800 wide, cap radius 3.900 seated 0.100 off the hole
line, length fixed at 3 × 8.000 = 24.000) overshooting to 36.000/35.900 and then
cut back. That is what produced, at Z = 20:

| before | after |
|---|---|
| `(28.100, 35.600) → (30.280, 35.600) → (33.720, 35.600)` — a **3.440 mm flat chord** across the tip | `(28.400, 32.000) → arc → (35.600, 32.000)` — a **true semicircle**, tangent-to-tangent |
| `(35.600, 33.600)` — a second flat down the outboard face | no flat |

The re-entrant step left by that chord is the notch reported against the end
wall; both were the same defect. The arm is now built directly — a 23.200 ×
7.200 stadium with caps on the hole centres — and `PerpendicularHolesLiftarm` is
no longer used here. That is not a loss of reuse: all three of its governing
dimensions had to be overridden, while the part that carries the shared,
profile-aware, calibrated content — `TechnicPinHole` — is still what cuts every
hole.

**The pin holes.** Philo uses LDraw's own primitives, and *two different ones*:

| | primitive | bore | depth | counterbore |
|---|---|---|---|---|
| vertical ×2 | `connhole` | Ø4.8 | 8.0 | Ø6.4 × 0.8, **both** rims |
| horizontal | `connhol3` | Ø4.8 | **7.2** | Ø6.4 × 0.8, **one** rim |

`connhol3` is placed with a matrix sending local +Y to global −X, so its
counterbored rim is the **outboard** one (the boss tip at |X| = 36.000) and the
bore floors inboard at |X| = 28.800 — **the reference's horizontal hole is blind
too**, with 0.400 mm of arm behind it. Round 42 had reached "blind" independently
but floored at 28.000 with counterbores at *both* rims, so the far flange
hollowed out exactly the thin material a blind hole has least of.

`TechnicPinHole` gains `counterbore_ends` (`"both"` default / `"entry"` /
`"none"`) to express this; `"both"` preserves every existing caller byte-for-byte.
Measured after the change, mouth → floor: counterbore Ø6.12 for 0.0–1.0, bore
Ø4.96 to 6.8, solid from 7.2. Exactly `connhol3`.

**What this does not fix.** The wall around the outer holes stays ~0.5 mm. Philo's
own is 0.4 mm (3.6 half-width − 3.2 counterbore radius); ours is slightly better
only because our counterbore is Ø6.2 rather than Ø6.4. That thinness is inherent
to the reference's proportions — the lever is the counterbore, not the cap, and
growing the cap would break the envelope.

### R44 — Flat where the arm joins the body, round at the outboard corner

R43 gave the arm the reference's own full stadium cap. A stadium touches its end
plane at a *single point* and curves away from it immediately, so where the arm
met the housing the plan outline read:

```
body edge in at Y = 35.600 → X = 28.400 → drops to Y = 32.000 → arc begins
```

— a sharp re-entrant notch at the arm's **root**, which on a cantilever is the
single worst place to put one, and which prints as a crevice. The reference has
it because injection moulding does not care; FDM and bending stress do.

Round 44 squares off the **inboard half only** (local `y <= 0`): the flank runs
straight for the arm's whole length and both end faces are flat out to the hole
line, while the outboard corner keeps R43's R3.600 round. Flat where it joins,
round where it is free — which is what the user's mark denoted, and what
reconciles the two requests that looked contradictory (*"the outer corner should
be round"* in R43, *"the place where the arm joins the housing, make it flat"*
here).

The envelope is untouched: the fill lands strictly inside `|X| <= HOLE_X` and
`Y in [ARM_Y_LO, HALF_Y]`, which the cap already bounded. Volume 21742.4 →
21910.8 mm³.

**Method note.** This was settled by *rendering the same view the user was
looking at*, not by reading coordinates. VTK cannot render in this container (no
X display) and there is no SVG rasteriser, so `tmp/plan_view.py` tessellates the
section wires and draws them with PIL. Two earlier readings of the mark — "flatten
the tip" and "fill a gap in the junction band" — were both wrong, and the picture
disambiguated them immediately where the coordinate dump had not.

**The check that policed this could not fail.** `test_middle_bore_breaks_through`
asserted the bore reached the cavity by probing `|X| = 22.0` — a point *inside*
the cavity, empty whether the bore arrives or not. Cutting cannot add material,
so no geometry could ever have failed it. Third instance this session of the
same pattern (R30's `assert seated_interference > 0.0`, R40's two zero
clearances). Replaced by `test_middle_bore_is_blind`, which asserts the wall is
solid on the hole's axis and carries its own positive control.


### R55b — The housing goes to the reference's own 29.600, and the window gets a sill

Two corrections landed after the tray work, both from the user looking at
the seated assembly.

**The side window's bottom 1.200 mm was open to daylight, and had been for
four rounds.** R51 moved the extraction tab from the Cover to the Tray. The
Tray seats `PLATE_THICKNESS` above world zero, so the tab's root rose from
Z = 0 to Z = 1.200 — while the housing's side window, cut to the tab's own
outline, still started at Z = 0. That left a 1.200 mm slot straight through
the side wall in the band `X 27.200..28.000`.

Worth dwelling on *why nothing caught it*. The window is derived from the
tab's outline and the tab still passes through it perfectly; both parts are
individually correct and individually tested. The fault existed only in the
relationship between them, at a Z neither part's own tests had reason to
probe. `test_window_sill_fills_the_bottom_of_the_side_window` now probes the
window's whole Z extent across housing + cover + tray, which is the shape of
test that could have caught it.

Fix, per the user ("I'd just add a stripe to the cover"):
`PoweredUpHubCover._build_window_sill` carries the plate's edge out through
the slot. Y half-width matches the *tab's* (12.000), not the window's, so the
window's running clearance survives on both sides; the outer face stops
0.150 mm short of the wall's outer face, because the Cover has ±0.150 mm of
deliberate sideways play from R48's plate-edge relief and a flush stripe
would stand proud whenever the lid sits off-centre.

**`DECK_Z` 24.000 -> 29.600**, user direction: *"just use 29.6 for now. I
don't need the top cover (yet)."* The tray floor plus the pack need
24.800 mm of interior; 3 studs gave 21.200. The pack now clears by 3.200 mm.

The honest accounting is in `reference_contracts.toml` as an open,
unregioned deviation, and it is worth repeating here because the number is
misleading: **29.600 matches the reference's top FACE while the shape below
it does not.** The reference steps in at exactly Z = 24.000 (bisected:
`|X|max` 35.600 at 24.000, 27.200 at 24.010) to a narrower upper section —
X ±27.200, Y −32.000..+33.200, ceiling 27.498, top skin to 29.600. This
class extrudes the full 72 × 71.2 footprint the whole way, carrying about
13,000 mm³ the reference has not got. Measured against the reference this
height is *less* faithful above the step than R22's truncation was. R22's
3-stud cap was never an approximation of the reference; it landed on the
reference's own step exactly.

Three things the height change broke, none of which were about the height:

1. **Both trapezoid sockets took their top edge from `DECK_Z`** — the same
   number as the step for R50–R54, so every socket test passed under either
   wiring. Left alone they would have stretched a trapezoid *measured* over
   Z 22.1..23.9 across 7.600 mm instead of 2.000, converting a measured
   flank angle into a derived one. New `SOCKET_Z_HI = 24.000` pins them, and
   a test asserts the wall survives above the socket.
2. **Both sockets' 1.000 mm vertical overcut** was free air while the part
   ended at 24.000, and became 1.000 mm of real wall the moment it did not.
   The overcut never moved; what it pointed at changed underneath it. This
   is the *Overcuts on the non-waste side* pitfall almost verbatim, and it
   arrived within one edit of a docstring asserting the overcut was safe.
3. **The cord port stopped being a route.** Its cutter spanned
   `DECK_THICKNESS` plus 1.000 mm of overcut each way; with the deck at
   22.400 that reached down to 21.400 and incidentally swept the descent
   clear — including the liftarms' 0.050 mm union seam, which pokes inboard
   past the wall's 26.400 inner face over Z 22.000..24.000, squarely in the
   port's X band. Raising the deck moved the cutter up and left the seam
   behind: deck opening clear, descent pinched by 0.050 mm. The cutter's
   lower bound is now *stated* (`WALL_INNER_STEP_Z`, where anything can
   first intrude into the port's X band) rather than inherited from an
   overcut that worked by accident. Caught by the existing "a hole is not a
   route" assertion — which is exactly what that assertion was written for.

The sockets were R50/R51's cap register, and a register only reads as one
because the part is truncated at the step. With the wall continuing to
29.600 they are closed recesses again, as in the reference — no longer
usable as a register. The user deferred the top cover in the same message,
so nothing depends on that today; restoring the register means restoring the
step, not re-cutting the sockets.

### R55c — The shell steps in above the step, like the reference

The follow-up above landed immediately, because the user saw the consequence
rather than the number: *"we do need to adjust the wall inwards like the
reference model, otherwise the trapezoid looks weird."* That is the right
diagnosis. The trapezoid socket only reads as a **socket** because its top
edge meets the step; with the side wall running straight past it to 29.600 it
reads as a slot milled in a flat face. The visual defect and the 13,000 mm³
fidelity defect are the same defect.

Upper footprint, ray-cast from `25560.dat` and positive-controlled at
Z = 15.000 against the lower walls this class already models:

| | outer | inner |
|---|---|---|
| X | ±27.200 | ±26.400 |
| Y (latch, −) | −32.000 | −30.800 |
| Y (tongue, +) | 33.316 → 33.234 (drafted) | +32.000 |
| ceiling / top | 28.000 / 29.600 | |

**The ceiling and skin were already right.** 28.000 and 1.600 are this
class's own `DECK_Z - DECK_THICKNESS` and `DECK_THICKNESS`: R47 arrived at
1.600 by thinning the deck to clear the pack, and landed on the reference's
own figure without knowing it. Only the plan footprint needed changing.

**Built as a subtraction.** `_build_upper_step_in` removes everything above
`REF_STEP_Z` outside the upper footprint. Every feature below the step —
stepped side walls, both end walls, the arms, both trapezoid sockets, the pin
bores — is already correct, and one cut above the step cannot disturb any of
it; re-shaping four wall builders could. The cutter has **no downward
overcut**, which is the entire correctness condition: 1 mm there would shave
the top off both sockets, the wall step, and the arms, which end at exactly
24.000 (verified before building the cutter, not assumed).

Verified face-by-face against the reference, same rays both sides: X matches
exactly on both faces, Y on three of four. The fourth is declared —
the reference's tongue-end outer face is drafted at −0.021 mm/mm and is
modelled vertical at the mid-height 33.276, so the error is ≤ ±0.042 mm and
changes sign at mid-height.

**One test had to be rewritten, and the reason is worth recording.** R55's
`test_wall_sockets_stop_at_the_reference_step_not_at_the_deck` asserted "wall
material exists above the socket, at X = 27.600". That was a valid falsifier
while the wall ran straight up. After R55b the step-in legitimately removes
X 27.200..28.000 above the step, so the probe found nothing and the test
failed — for the right reason, but it was also no longer *able* to
discriminate the two wirings it existed to tell apart. Rewritten around the
socket's **mouth width** at the step instead: pinned at 24.000 the trapezoid
opens to 11.150 just below the step; wired to `DECK_Z` the same flanks
stretched over 7.600 mm would give 9.700. A 1.450 mm difference the new form
sees and nothing else does.

**Conformance.** A new scored row, `poweredup-hub-housing-upper-side-wall`,
measures 51.3% and its floor is set there. Deliberately scoped to the WALL:
the whole upper section scores 4.2%, dominated entirely by the reference's
internal posts (PCB standoffs, declared unmodelled), so a floor on the
section would be decorative — almost no regression could fail it. The 48.7%
residual on the wall row is recorded as an **open question**, not explained
away: the wall's two faces land on the reference's numbers exactly, so
something else in the sampled band accounts for it, most likely reference
ribs tying into the inner face. If that turns out to be a real miss, the fix
belongs in the geometry, not in the floor.

**Follow-up, narrowed**: what remains above the step is the internal posts
and the drafted tongue face, both declared. The part can now carry a cap
whenever one is wanted — restoring the register means restoring nothing, the
step is back.


### R55d — The roof's short ends run out to the end trapezoids

User direction, with the purpose stated alongside it: *"extend both shorter
ends to sit inline with the trapezoid (similar to what we currently have for
the long edges)"* — the trapezoids are kept as the register for a future
cover, whose legs mate into them and whose outer wall sits flush with this
part's own side walls.

The long edges already worked that way, and that is precisely what makes a
socket read as a socket rather than as a slot milled in a flat face:

| | trapezoid floor | upper section outer | inline? |
|---|---|---|---|
| long edge (±X) | 27.200 | 27.200 | yes |
| short end (±Y), before | 34.400 | −32.000 / +33.276 | no — 2.400 / 1.124 short |
| short end (±Y), after | 34.400 | ±34.400 | yes |

`UPPER_Y_HI` is `HALF_Y - END_SOCKET_DEPTH`, **derived rather than typed**.
"Inline with the trapezoid" *is* the requirement, so it is written as the same
arithmetic `_build_end_wall_socket` uses for the floor; retyping 34.400 would
let the two drift apart silently, which is the exact failure this feature
exists to avoid.

This is a **departure from the reference**, declared in
`reference_contracts.toml`: the real part stops its upper section inboard of
its own end-trapezoid floor. X is untouched and remains reference-exact on
both faces. It also retires an earlier deviation — the reference's tongue-end
outer draft, modelled vertical at ±0.042 mm — which is moot now that face is
not where the reference puts it at all.

**Cover budget, measured on the built housing** (`tmp/cap_budget.py`), for a
cover with legs in the trapezoids and its outer wall flush:

| face | flush at | upper section | socket depth | cover wall | leg |
|---|---|---|---|---|---|
| long edge (±X) | 28.000 | 27.200 | 0.800 | 0.650 (1.6 lines) | 0.800 (2 lines) |
| short end (±Y) | 35.600 | 34.400 | 1.200 | 1.050 (2.6 lines) | 1.200 (3 lines) |

The asymmetry is the reference's own — its side sockets are 0.800 deep and
its end sockets 1.200. Widening the long edge to match would mean
`UPPER_X_OUTER` 27.200 → 26.800 *and* the upper wall's inner face
26.400 → 26.000 (or the housing's own wall drops to 0.400), which also forces
a third X-step on the Tray, whose upper band rides at 26.250. Not taken: the
user's stated requirement is that the cover "doesn't need to be super tough",
0.650 mm prints as two thin perimeters, and the retention lives in the legs.

**One free improvement worth taking when the cover is built**: put the fit
clearance on the trapezoid's tapered FLANKS, not on the pocket depth. A taper
self-centres, so that is where the clearance does the locating anyway; take it
there and the legs stay a full 0.800 / 1.200 instead of 0.650 / 1.050.

**A test failed for the right reason and had to be re-aimed.** R55b's
`test_shell_steps_in_above_the_reference_step` probed "material below the step,
just outboard of the upper footprint" on the centreline. Since `UPPER_Y_HI` is
now the end socket's own floor, that probe lands *inside* the socket recess and
reads empty — legitimately. Re-aimed to X = 22.000, outboard of the socket's
own mouth, with an assertion that it is.


### R55e — The cover's wall budget becomes the input

User direction: *"Can we use 1mm for all the cover walls? I feel 0.65 is too
thin. Then adjust the housing top accordingly."*

R55d's measurement put the long-edge cover wall at 0.650 mm — about 1.6
extrusion widths at a 0.4 mm nozzle. Since the cover's outer wall sits flush
with this part's side walls, that thickness is not the cover's choice: it is
whatever gap this class leaves between its own outer face and the upper
section, less the fit clearance. So the direction of derivation inverts —
the budget is the input now:

    COVER_WALL          1.000     the requirement
    COVER_FIT_CLEARANCE 0.150     nominal, not the live profile
    UPPER_INSET         1.150     = COVER_WALL + COVER_FIT_CLEARANCE
    UPPER_X_OUTER      26.850     = WALL_X_OUTER_LOWER - UPPER_INSET
    side socket depth   1.150     = UPPER_INSET
    inner_upper        26.050     = UPPER_X_OUTER - WALL_THICKNESS

`COVER_FIT_CLEARANCE` is deliberately a nominal constant rather than
`profile.free.radial`: this class's visual contracts are byte-compared, so its
shape must not vary with the print profile, and the cover — which does not
exist yet — will apply its own clearance when it is built.

Deriving the socket depth from the inset makes **inline with the trapezoid**
structural rather than coincidental: the depth *is* the inset, so the socket
floor and the upper wall are the same plane by construction. Two constants
that merely agreed could stop agreeing.

**The failure this round nearly shipped.** Deepening the socket 0.800 → 1.150
without moving the wall behind it leaves 0.450 mm of material between the
recess and the battery bay, where the reference has 0.800. Nothing in the part
complains: it is still one solid, still seats at zero interference, and the
socket tests only look at the recess. `inner_upper` is now derived from the
socket floor — "floor minus one wall" — so a future depth change carries the
inner face with it. The side effect is a simplification: Housing's inner face
is now uniform from `WALL_INNER_STEP_Z` all the way to `DECK_Z`, which is what
lets the Tray keep a single upper band and the cord port a single flush edge.

**The cord port, per the user's own catch** (*"you probably also want to move
the housing roof's wire pass cut to avoid super thin edge"*): its outboard
edge was flush with the LOWER band's inner face (26.400). With the roof's edge
now at 26.850 that would leave a 0.450 mm ligament of roof outboard of the
slot and notch the upper wall it passes through. `x_hi` is now
`UPPER_X_INNER`, so the roof still simply ends where the wall begins — the
same reasoning the original figure was chosen for, re-derived against geometry
that had moved under it.

**Short ends left reference-exact.** Their socket depth is 1.200, already
giving a 1.050 mm cover wall. Matching 1.150 would buy 0.050 mm — below print
resolution — for a departure from a measured figure.

**Knock-on to the Tray.** Housing's inner face moved 0.350 mm inboard, so the
tray's upper band moved with it (26.400 → 26.050 nominal, inner 25.600 →
25.250, same section). Held still it would have fouled by 0.200 mm everywhere
above world Z = 21.200, and nothing in the tray's own tests would have said
so — the single-solid and seating checks are about that part alone. The
cross-part interference check is what caught it.

**Two honesty repairs, both of the same class.**

1. `test_upper_section_x_faces_match_the_reference` (R55b) asserted against
   `UPPER_X_OUTER` rather than against literals — good practice generally, and
   here it meant the test stayed green while its *name and docstring* went on
   claiming a reference agreement that had lapsed. Renamed to
   `..._are_the_cover_budget_not_the_reference`, and given an assertion that
   fails if the inset ever reverts to the reference's own figure.
2. R55d's contract note said "X is untouched and remains reference-exact".
   True when written, false after this round. Corrected in place rather than
   left to age.

Both are the same failure the repo's own rules warn about: an artifact that
keeps asserting a property after the property has gone.

**Conformance, and a second lowered floor.** `upper-side-wall` went
48.7% → 40.0%, floor 48.0 → 39.0. Two lowerings in one round is precisely the
"accepted bound widened across rounds while the premise stayed wrong" pattern
that shipped a non-functional latch here before, so the contract now records
both with the distinction explicit: **R55d's was a sampling artifact** (the
geometry was provably unchanged; lengthening the wall's triangles in Y
redistributed the sample points), while **R55e's is real** — the wall moved
0.350 mm off the reference, deliberately, for the cover budget. The row no
longer certifies agreement with the reference's wall position; the geometry
tests carry the current numbers to 1e-6. What it still does is catch further
drift and keep the size of this departure on the record.


### R55f — The bottom edge is rounded into both end planes

User request: *"for the bottom of the housing the reference model have curve
on both end of the side wall. I want to have that too. Note on the end with
the thumb tabs, only the outer segments have the curve."*

**Slices lied; vertices did not.** The first pass measured this by slicing the
reference at a series of Z and fitting a radius to where the wall reached.
That produced two different radii which moved depending on which Z was fitted
-- ~3.2 at one end, ~3.7 at the other, and neither stable. The reason is that
a slice samples wherever the cutting plane happens to cross a facet, so it
reports the tessellation as much as the shape. Reading the reference's own
VERTICES instead -- they are the curve's control points -- gives:

| end | pullback at Z = 0 / … / 0 | fit |
|---|---|---|
| −Y latch | 3.600, 2.222, 1.054, 0.274, 0.000 at Z 0.000, 0.274, 1.054, 2.222, 3.600 | R = 3.600, **rms 0.0005 mm** |
| +Y tongue | 2.222, 1.054, 0.274, 0.000 at Z 0.000, 0.780, 1.948, 3.326 | the SAME arc, centre 0.274 lower |

One radius, one centre `|Y| = 32.000`. The tongue end is not a different
curve: its bottom face cuts the same arc 0.274 mm above the latch end's
tangent point. That is the kind of relationship a drifting radius hides
completely.

**The segments differ, and the user's qualifier was exactly right.** Vertices
at Z = 0 (`tmp/ldraw/curve_span.py`):

* **latch end** -- rounded only over `|X|` 19.200..28.000. Square vertices
  survive at `Y = -35.600` out at `X = +-5.600`, so the middle genuinely stays
  sharp.
* **tongue end** -- rounded on the RIB bands and only those: `|X| <= 0.800`
  (centre wall), 15.600..17.200 (inner ribs), 26.000..28.000 (outer ribs) --
  i.e. precisely SS12.2's T1/T2/T3, the bands `_build_tongue_ribs` already
  builds.

**Cut as the arc itself**, a cylinder along X, not a chamfer approximating it.
`_build_bottom_end_round` overcuts every direction except **X**: the bands are
the whole point of the feature, so bleeding 1 mm sideways would round segments
the reference leaves sharp. That is the one bounded direction in the builder,
and it is bounded deliberately rather than by omission.

Verified against the reference's measured stations rather than re-derived from
`BOTTOM_ROUND_R` -- re-deriving would only confirm the code agrees with
itself. Max deviation **0.046 mm**, and that residual is the probe sitting
0.02 mm above each station rather than a real offset.

**One collateral repair.** `test_bottom_face_is_z_zero_and_open` asserted
`bbox.zmin == 0.0` exactly. The cylinder cut leaves about 4e-14 mm of OCCT
float noise, so it began failing -- for no geometric reason. Moved to a 1e-9
tolerance, with the same reasoning the Cover's own datum test already carried:
an exact compare on a boolean's bounding box tests the kernel's rounding, not
the datum, and 1e-9 still catches a real datum error by six orders of
magnitude.

### R55g → R56 — "All the way" meant extent, not depth

User direction after R55f: *"for the curve, the tongue side wall should have
the curve all the way."* R55g read that as arc **depth** and gave the tongue
end's two outer rib bands (`|X| 26.000..28.000`) the full-depth arc, tangent
to `Z = 0`, while keeping the reference's segmented band structure. The user's
next message was *"Did you fix the curve on the tongue side wall? I'm still
seeing squares."*

They were right, and the amount was not marginal. Sweeping the tongue end's
outer face at the bed (`tmp/ldraw/tongue_bottom_scan.py`) found **47.200 mm**
of bottom edge still running square, in the four gaps between the rounded
bands:

| X band | state |
|---|---|
| `-28.000 .. -26.400` | round |
| `-26.000 .. -17.200` | **SQUARE** |
| `-16.800 .. -16.000` | round |
| `-15.600 .. -0.800` | **SQUARE** |
| `-0.400 .. +0.400` | round |
| `+0.800 .. +15.600` | **SQUARE** |
| `+16.000 .. +16.800` | round |
| `+17.200 .. +26.000` | **SQUARE** |
| `+26.400 .. +28.000` | round |

`BOTTOM_ROUND_X_TONGUE` is now a single band spanning `-28.000..+28.000` at
`BOTTOM_ROUND_CZ_FULL`. The latch end is untouched: its middle stays square,
by user direction and in agreement with the reference's own square vertices at
`X = ±5.600`.

**The probe lied twice before it was worth trusting**, and both failures are
the ones `vibe/INSTRUCTIONS.md` names. First it reported `hit == False` as
"rounded", so a region with *no wall at all* was indistinguishable from a
rounded one — fixed by sampling a second point above the arc's reach, which
separates *rounded* from *absent*. Then, with that fixed, the latch end read
as uniformly ABSENT: the probe stepped inboard by a fixed `−Y` offset, which
at the `−Y` end put it **outside** the part. Only after the sign fix did the
latch end report its known-square middle, and that is the positive control
that makes the tongue-end reading mean anything.

**The test changed shape, not just its expected value.** The old
`test_bottom_end_round_follows_the_reference_arc` sampled three hand-picked
stations — all of which sat on bands R55g had rounded, which is exactly why it
stayed green through a defect the user could see across half the wall. The
replacement sweeps all 141 X stations at `0.4 mm` and fails on a single square
one. Per *Verification Samples Must Be Chosen By The Data*: the stations were
picked by the agent, and the bias was invisible in the result.

**Contract fallout.** `poweredup-hub-housing-tongue-end` fell to `47.4%`
against a floor already lowered twice (`78.0 → 68.0`). It was retired rather
than lowered a third time — the ratchet. Questioning the premise: that row's
region (`Y 32.000..33.400`) was drawn around the *reference's* tongue-end wall
face; ours is at `35.600` by a separately declared deviation, so above the arc
our part has no surface there at all (`InconclusiveRegion`, verified) and
below it the only sampled surface is the arc the user chose. Rescoping was
tried in both axes and rejected by measurement
(`tmp/ldraw/tongue_rescope.py`). Coverage moved to
`poweredup-hub-housing-latch-end-arc` — the arc we did **not** deviate —
which scores `100.0%` with a `99.0%` floor and a demonstrated failing case
(`96.7%` when the rounded span is shrunk to `|X| 24.000`).

### R57 — The tray's upper wall band was connected, not supported

User direction: *"There is some issue with the tray. The wall becomes narrower
due to the housing gets narrower on top, this creates a floating region. For
the tray we can just remove the narrower part."*

This is the two-band wall from R51 (see *A genuine construction bug* above),
and the interesting part is that R51's fix was real and still insufficient.
The bands are X-disjoint — lower `[26.400, 27.200]`, upper `[25.250, 25.900]`
— because the tray was tracking Housing's cavity inboard above its step. R51
noticed they were four solids, added a bridge slab at the seam, and got one
solid. That fixed **connectivity**. It did nothing about **support**: the
upper band is a `0.650 mm` wall standing on a `0.500 mm` ledge with open air
under its inboard half, which is what the user saw.

`test_single_solid` passed for six rounds across this defect, and it was never
wrong — connectivity and printability are different properties, and only the
first one was being checked. The new
`test_no_wall_material_floats_above_a_void` checks the second directly: it
walks columns of the part and requires each to be vertically contiguous **and**
to start at the bed, sampled on a `Y` line clear of the strap channel, the cap
rebate and the extraction tabs.

Its positive control needed two attempts, and the first failure was
instructive rather than incidental. Rebuilding the defect as *wall + floating
band* produced **one** run at the floating band's `X`, not two — because
without the floor there was nothing below it, and a band floating over nothing
is a single run exactly like a wall standing on the bed. That is a hole in the
criterion, not just in the fixture: "how many runs" cannot distinguish
supported from unsupported. The helper now returns run *positions*, and the
test asserts both properties.

The fix itself is the user's: one full-thickness band ending at `WALL_Z_HI`
(the old `WALL_STEP_Z`, renamed because it is now the wall's top and not a
step). `WALL_OUTER_X_UPPER_NOMINAL`, `WALL_INNER_X_UPPER`,
`_wall_outer_x_upper` and `_wall_z_hi` are gone; the wall is now
profile-independent. Consequence recorded rather than left to be
rediscovered: the wall no longer reaches the pack's top (local `Z = 23.600`
against a `20.000` wall), so above `WALL_Z_HI` the pack is confined by
Housing's cavity rather than by this part. The `__init__` comment that used to
observe the wall "stands 3.000 mm proud of the thing it cradles for no reason
other than that is where the deck happens to be" is resolved by deletion.
