---
description: Run the full STEP-file reverse-engineering pipeline (summary, iso preview, face catalog, hole finder, face distances)
argument-hint: <reference.step>
---

Run the standard STEP analysis pipeline against `$1`, in the order documented in `vibe/INSTRUCTIONS.md` under "Reverse-engineering from STEP files":

1. `python3 vibe_cading/tools/step_summary.py $1` — establishes envelope, body count, volume, centre of mass.
2. `python3 vibe_cading/tools/step_preview.py $1 --views iso_ne iso_sw` — reveals rotationally-symmetric features that are ambiguous in flat orthographics. Read the resulting SVGs **before** extracting any dimensions.
3. `python3 vibe_cading/tools/face_catalog.py $1 --summary` then `python3 vibe_cading/tools/face_catalog.py $1 --type Cylinder --min-area 5` — surface-type breakdown, then significant cylindrical features.
4. `python3 vibe_cading/tools/hole_finder.py $1 --grid 8` — diameter, depth, axis, centre for every hole and boss; checks Lego 8 mm grid alignment.
5. `python3 vibe_cading/tools/face_distances.py $1 --unique` — wall thicknesses, tab heights.

After all five steps complete, produce the **feature reconciliation checklist** described in `vibe/INSTRUCTIONS.md` (every boss / hole with diameter ≥ 1 mm or area ≥ 5 mm² mapped to a model method or marked NOT MODELLED). Do not skip ahead to `boolean_diff.py` until reconciliation is complete.

Process objects large → small (main body → tabs/flanges → bosses/collars → holes/chamfers) and establish the STEP-to-model coordinate mapping explicitly before comparing any numbers.
