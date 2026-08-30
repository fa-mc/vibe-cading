# Powered Up hub battery box — physical measurements (2026-08-28)

**These measurements supersede the LDraw reference for every dimension they
cover.** They were taken with calipers on the real LEGO parts by the project
owner. Where they disagree with LDraw parts `24853` (cover) / `25560`
(housing), the calipers win.

This file is our own measurement record of hardware we hold. It contains no
third-party geometry and is safe to track, unlike the LDraw-derived meshes.

## Why this file exists

The design record up to round 59 treated the LDraw library as ground truth,
because it was the only quantitative source available and it is internally
consistent to the digit — the cover's width is drawn at exactly `±68.000 LDU`
(`54.400 mm`), its length at `175 LDU`, its height at `32.5 LDU`, all whole-LDU
grid values, with every subpart resolving cleanly
(`tmp/ldraw/measure_ldu.py`, which reads the `.dat` source directly with no
conversion in the path).

It is nevertheless **wrong about the real part**, by ~2 mm on the cover's
width. That is far outside anything tolerance or measurement technique
explains. Three independent readings of the LDraw source — the raw `.dat` in
LDU, the converted mesh, and the STEP — all agree with each other and all
disagree with the hardware, which is what rules out our conversion pipeline as
the cause.

## Measured — cover

| Dimension | Measured | LDraw said | Delta |
|---|---|---|---|
| Width, excluding the window strips | **52.33** | 54.400 | **−2.07** |
| Length, including tongues | **63.60** | — | — |
| Length, excluding tongues (at the top) | **61.90** | — | — |
| U base: thumb-tab surface → hook end at the cover body | **6.24** | 4.800 | +1.44 |
| Hook tongue → U base | **5.00** | — | — |
| Hook width | **12.20** | 13.600 | **−1.40** |
| Tongue width | **13.80** | — | — |
| Gaps — 3, between tongues and the edge | **2.30** | — | — |

Note: *"The hook can go slightly thicker."*

## Measured — housing

| Dimension | Measured | Note |
|---|---|---|
| Inner wall, width end to end | **52.96** | the cavity the cover sits in |
| Inner wall, length end to end | **61.66** | |
| Outer wall width, excluding side arms | **55.60** | fits 7 studs (56.0) |
| Outer wall length | **71.15** | fits 9 studs (72.0) |

Owner direction: *"Outer wall is not that important, you can use our own lego
generator measure, as long as fit within the range it'll be fine."*

## What this implies, before any code changes

**The outer envelope was already right; the WALL THICKNESS is what is wrong.**
Our housing's outer faces (`56.000 × 71.200`, from the 8 mm stud grid) sit
within `0.400` and `0.050` of the measured part — the grid anchor held. But we
took the wall thickness from LDraw at `0.800 mm`, which puts our cavity at
`54.400` against a measured `52.960`. The real wall is therefore about
`(55.60 − 52.96) / 2 = 1.32 mm`, roughly **1.65× thicker** than modelled.

The same applies lengthwise: measured outer `71.15` against inner `61.66`
gives end walls of about `4.75 mm` each.

**The cover/housing fit works out consistently**, which is a good sign the two
readings are of the same real assembly: cover `52.33` in a `52.96` cavity is
`0.63 mm` total lateral slop, `0.315` per side — close to the running clearance
we arrived at empirically in round 59 (`0.295`), reached from the wrong datum.

## Consequence for `reference_contracts.toml` — needs a decision

Every `poweredup-hub-*` row scores our geometry against the LDraw meshes. Those
rows now measure agreement with a source known to be wrong about the hardware,
so **raising their agreement actively pulls the model away from the real
part**. They cannot simply be re-floored; the question is whether a reference
we have shown to be incorrect should gate anything at all. Left open here
rather than resolved unilaterally — it is a gate change.

## Resolved (owner, 2026-08-28)

**`63.60` is plate + tongues only; the latch U is extra.** So the cover's
overall length is about `61.90 + 1.70 + 6.24 = 69.84`, and **LDraw's `70.000`
overall length is roughly right**. The reference's errors are the *width* and
the *wall thickness*, not the length — a much smaller blast radius than a
whole re-datum.

Tongue arithmetic corroborates the readings independently: 2 tongues ×
`13.80` + 3 gaps × `2.30` = **`34.50`**, against our modelled tongue span of
`34.40`. The tongue *region* is right; its internal division is not — real
tongues are `13.80` wide with `2.30` gaps, ours are `14.80` with `1.60`.

## Derived target constants

| Constant | Now | Target | From |
|---|---|---|---|
| Housing cavity width | 54.400 | **52.960** | measured inner wall |
| Housing wall thickness | 0.800 | **~1.520** | (56.000 − 52.960) / 2, using our stud-grid outer |
| Housing cavity length | ~62.800 | **61.660** | measured inner wall |
| Housing end-wall thickness | — | **~4.770** | (71.200 − 61.660) / 2 |
| Cover plate width | 54.400 | **52.330** | measured, clearance already included |
| Cover plate length (excl. tongues) | 62.800 | **61.900** | measured at the top |
| Cover tongue width | 14.800 | **13.800** | measured |
| Cover tongue gaps | 1.600 | **2.300** | measured, 3 of them |
| Latch hook width | 13.600 | **12.200** | measured |
| U base depth | 4.800 | **6.240** | thumb-tab face → hook root |
| Hook tongue → U base | — | **5.000** | measured |

**Do not stack our clearance knobs on top of these.** The cover-vs-housing
figures were measured on a real mating pair, so the working clearance is
already inside them: `52.33` in `52.96` is `0.315 mm` per side. Applying
`_fit` again would double it. Notably, round 59 reached `0.295 mm` per side
empirically from the *wrong* datum — within `0.02 mm` of the real assembly.

## RESOLVED 2026-08-30 (round 61) — the length conflict, and how

The `61.90` reading above is **superseded**. It was recorded here as
unconfirmed because it put the cover plate `0.24 mm` LONGER than the `61.66`
cavity it sits inside — impossible for a part that assembles. That doubt was
correct, and it was the *unconfirmed* figure that turned out to be wrong.

After printing the round-60 cover, the owner measured the body directly at
**`59.800`** (tongues excluded) and the tongue protrusion directly at
**`4.000`**. Both reconcile where the old pair did not:

- `59.800` in a `61.660` cavity → `0.930 mm` per end. Assembles.
- `59.800 + 4.000 = 63.800` against the `63.600` whole-part reading → `0.200`.

**The lesson is about method, not about these two numbers.** `61.90` and
`1.700` were both *differences of two whole-part readings*
(`63.600 − 61.900 = 1.700`), so each carried the sum of two measurement
errors, and the arithmetic gave no hint which end the error was at. The
round-61 figures measure each feature directly. Where a derived figure and a
direct one disagree, prefer the direct one — and treat a derived figure that
fails a physical sanity check as evidence about *itself*, not as an anomaly to
be caveated and worked around.

### Round-61 measurements (printed part, supersede the table above)

| Constant | Round 60 | **Round 61** | From |
|---|---|---|---|
| Cover body length (excl. tongues) | 61.900 | **59.800** | measured directly |
| Cover tongue protrusion | 1.700 | **4.000** | measured from body end |
| Latch finger wall thickness | 0.800 | **1.600** | measured |
| Bead reach, outboard of body edge | 3.420 | **5.000** | measured |

The `5.000` and the earlier `6.240` U-base depth are **independent
corroboration of each other**: taken on different features a round apart, they
ask for the same `~1.5 mm` of latch deepening. The cover drives the bead off
the first and the thumb pad off the second, so neither is discarded; they land
`6.250` apart, `0.010` from the reading.

The latch crown is a **slope**, not the semicircular bend we built. Verified
independently on the LDraw reference (`tmp/ldraw/latch_shape_r61.py`), whose
outer profile converges `2.153 → 1.286 mm` over `z = 11.25…12.75`.

> **Where the reference still disagrees with the hardware.** The same probe
> shows the reference latch is a genuine hairpin `4.4 mm` deep in Y, against
> the `6.24 mm` measured. So LDraw is wrong about this feature too, in the same
> direction as the width. The reference can confirm the crown's *shape*; it
> cannot arbitrate the latch's *dimensions*.

## Consequence applied

All `[[component]]` rows in `reference_contracts.toml` were **retired** on this
date (renamed `[[retired_component]]`, so the checker ignores them while every
line of their rationale survives). The checker now accepts an empty manifest
only when it carries a written `all_rows_retired_reason`, so "nothing is
gated" cannot be reached by a mis-edit; `test_empty_manifest_without_a_reason_is_rejected`
is the falsifier for that guard.
