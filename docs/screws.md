# Screws and Standard Fasteners

This document explains how to use the procedural screw models to generate hardware and boolean cutting tools (holes) in your CadQuery designs.

## Overview

The screw system provides generic standard fasteners (Machine Screws, Wood Screws) and a robust toolset for generating holes with proper clearances and countersinks/counterbores.

### Key Concepts

1.  **Simplified Geometry:** The screw models generate simplified 3D shapes (cylinders instead of true helical threads). This ensures boolean operations (cuts and unions) in CadQuery remain fast and mathematically stable.
2.  **`to_cutter()`:** The primary use of a screw object is to call its `.to_cutter()` method. This generates the negative volume needed to subtract the screw's shape from your part.
3.  **Coordinate Z=0 is the Mating Surface:** For all screws, Z=0 represents the surface of the part the screw is entering.
    *   For a **countersunk (flat) head**, the top of the head is at Z=0. The head extends down into the part (-Z).
    *   For a **non-countersunk (socket/pan) head**, the bottom of the head is at Z=0. The head sits on top of the part (+Z), and the shaft extends down into the part (-Z).

## Generating Standard Screws

Instead of defining every constraint manually, use the provided subclasses with standard designations.

### Metric Machine Screws

```python
from vibe_cading.mechanical.screws import MetricMachineScrew

# Create an M4 flat head (countersunk) screw, 12mm long
m4_flat = MetricMachineScrew.from_size(size="M4", length=12.0, head_type="flat", drive_type="hex")

# Get the basic 3D shape representing the physical screw
solid = m4_flat.solid
```

### Wood / Self-Tapping Screws

```python
from vibe_cading.mechanical.screws import WoodScrew

# Create a 3/16" pan head wood screw, 1 inch (25.4mm) long
wood_screw = WoodScrew(size="3/16", length=25.4, head_type="pan", drive_type="phillips")
```

## Using `to_cutter()` for Holes

The most important feature of the screw class is generating the "cutter"—the negative space you subtract from your model.

A cutter automatically includes:
*   The shaft volume (scaled up for different fit types).
*   The head volume (to recess the head via a countersink or counterbore).
*   **Overcuts:** Infinite vertical extensions at the ends of the cutter so that boolean subtractions don't leave thin, non-manifold skins of material.

### Fits

The `fit` parameter determines how tight the hole is:

1.  **`fit="clearance"`**: A loose hole meant for the screw to pass straight through. The hole diameter is larger than the thread's major diameter (e.g., 4.2mm or 4.4mm for an M4).
2.  **`fit="tap"`**: A tighter hole meant for the threads to bite into the material. The hole diameter is equal to the root (minor) diameter of the thread (e.g., ~3.3mm for an M4).
3.  **`fit="interference"`**: An interference fit (slightly under the major diameter) for press-in applications.

### Examples

```python
import cadquery as cq
from vibe_cading.mechanical.screws import MetricMachineScrew

# 1. We have a 10mm thick plate
plate = cq.Workplane("XY").box(20, 20, 10).translate((0, 0, -5)) # Surface at Z=0

# 2. We want to put an M3 socket cap screw through it
m3_screw = MetricMachineScrew.from_size("M3", length=15, head_type="socket")

# 3. Generate a clearance cutter (loose fit, includes the counterbore for the socket head)
cutter = m3_screw.to_cutter(fit="clearance")

# 4. Subtract the cutter from the plate
plate_with_hole = plate.cut(cutter)
```

### Material-Specific Print Clearances via ToleranceProfile

For parts intended to be 3D printed, different materials shrink or bridge differently, resulting in undersized holes (especially in PETG or ASA).

`to_cutter()` accepts a `profile` keyword that carries the radial and axial allowances together.  Pass a named profile from `print_profiles.json` (the global default is configured via the `VIBE_PRINT_PROFILE` env var) or construct a `ToleranceProfile` literal in code.  The profile's `free.radial` slot drives shaft inflation and `free.axial` drives the head recess depth — no separate `radial_allowance` / `head_recess_depth` floats are required.

```python
import cadquery as cq
from vibe_cading.mechanical.screws import MetricMachineScrew
from vibe_cading.print_settings import get_profile

class MyPlate:
    def __init__(self, material: str = "PLA") -> None:
        # 1. Resolve the tolerance profile for the target material.  The
        #    profile encapsulates all radial / axial allowances; no need
        #    to thread individual floats through call sites.
        self.profile = get_profile(material)

    def _build(self) -> cq.Workplane:
        screw = MetricMachineScrew.from_size("M3", length=12, head_type="flat")

        # 2. Pass the profile straight to to_cutter().
        cutter = screw.to_cutter(profile=self.profile, fit="clearance")

        # ... logic to cut plate ...
```

For a one-off override, construct a `ToleranceProfile` directly:

```python
from vibe_cading.print_settings import ToleranceProfile, FitGrade

snug = ToleranceProfile(
    name="snug",
    free=FitGrade(radial=0.05, axial=0.05),
    slip=FitGrade(radial=0.02, axial=0.0),
    press=FitGrade(radial=-0.02, axial=0.0),
)
cutter = screw.to_cutter(profile=snug, fit="clearance")
```
