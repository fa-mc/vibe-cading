# Screw Base Class and Standard Fasteners

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
from models.mechanical.screws import MetricMachineScrew

# Create an M4 flat head (countersunk) screw, 12mm long
m4_flat = MetricMachineScrew.from_size(size="M4", length=12.0, head_type="flat", drive_type="hex")

# Get the basic 3D shape representing the physical screw
solid = m4_flat.solid
```

### Wood / Self-Tapping Screws

```python
from models.mechanical.screws import WoodScrew

# Create a 3/16" pan head wood screw, 1 inch (25.4mm) long
wood_screw = WoodScrew(size="3/16", length=25.4, head_type="pan", drive_type="phillips")
```

## Using `to_cutter()` for Holes

The most important feature of the screw class is generating the "cutter"—the negative space you subtract from your model.

A cutter automatically includes:
*   The shaft volume (scaled up for different fit types).
*   The head volume (to recess the head via a countersink or counterbore).
*   **Overcuts:** Infinite vertical extensions at the ends of the cutter so that boolean subtractions don't leave thin, non-manifold skins of material.

### Modes

The `mode` parameter determines how tight the hole is:

1.  **`mode='clearance'`**: A loose hole meant for the screw to pass straight through. The hole diameter is larger than the thread's major diameter (e.g., 4.2mm or 4.4mm for an M4).
2.  **`mode='tap'`**: A tighter hole meant for the threads to bite into the material. The hole diameter is equal to the root (minor) diameter of the thread (e.g., ~3.3mm for an M4).

### Examples

```python
import cadquery as cq
from models.mechanical.screws import MetricMachineScrew

# 1. We have a 10mm thick plate
plate = cq.Workplane("XY").box(20, 20, 10).translate((0, 0, -5)) # Surface at Z=0

# 2. We want to put an M3 socket cap screw through it
m3_screw = MetricMachineScrew.from_size("M3", length=15, head_type="socket")

# 3. Generate a clearance cutter (loose fit, includes the counterbore for the socket head)
cutter = m3_screw.to_cutter(mode="clearance")

# 4. Subtract the cutter from the plate
plate_with_hole = plate.cut(cutter)
```

### Advanced Cutters: Fits and Extra Depth

If you have specific 3D printing tolerance needs, you can override the default allowances:

```python
# Create an M4 tapped hole, but make it slightly looser than standard (+0.1mm radius)
# and sink the head an extra 1mm deep into the plate.
my_cutter = m4_flat.to_cutter(
    mode="tap",
    radial_allowance=0.1,
    head_recess_depth=1.0
)
``````

### Material-Specific Print Clearances

For parts intended to be 3D printed, different materials shrink or bridge differently, resulting in undersized holes (especially in PETG or ASA).

Instead of hardcoding radial allowances per-class, use the global print settings module to fetch standardized offsets based on the target material string. This allows models to parametrically adapt their tolerance gaps when users configure `build.toml`.

```python
import cadquery as cq
from models.mechanical.screws import MetricMachineScrew
from models.print_settings import get_screw_allowances

class MyPlate:
    def __init__(self, material="PLA"):
        # 1. Fetch material parameters
        allowances = get_screw_allowances(material)
        self.radial_allowance = allowances["radial_allowance"]
        self.head_recess = allowances["head_recess_depth"]
        
    def _build(self):
        screw = MetricMachineScrew.from_size("M3", length=12, head_type="flat")
        
        # 2. Inject parameters when generating the cutter
        cutter = screw.to_cutter(
            mode="clearance", 
            radial_allowance=self.radial_allowance, 
            head_recess_depth=self.head_recess
        )
        
        # ... logic to cut plate ...
```
