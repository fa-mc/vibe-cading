---
description: Slice a model with tools/section_slicer.py to verify internal geometry (blind holes, snap rings, counterbores)
argument-hint: <module.path.ClassName-or-step-file> --axis X|Y|Z --at <mm>... [--report]
---

Run the section slicer for `$ARGUMENTS`:

```
python3 tools/section_slicer.py $ARGUMENTS
```

Use this tool whenever a model contains blind holes, internal cavities, snap rings, counterbores, or any feature that cannot be reliably validated from external orthographic / iso views. Per `CLAUDE.md` ("Blind Holes and Internal Geometry Under-visibility" and "Validating Internal Intersections and Mating Surfaces"), `section_slicer.py` is **mandatory** in those cases — `iso_ne` previews physically cannot see inside a blind hole.

After running, read the `--report` table (if requested) and the generated cross-section SVGs in `tmp/section/`, and report:

1. Edge types, radii, and centres on each slice.
2. Any unexpected zero-thickness wafers, missing cuts, or asymmetric features.
3. Whether the internal Z-steps and widths match the design brief's acceptance criteria.
