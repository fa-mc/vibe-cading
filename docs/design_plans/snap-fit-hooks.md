# Design Brief: Snap-Fit Cantilever Hooks

## 1. Goal
Design a parametric snap-fit cantilever hook and its corresponding mating catch (hole/ledge) for generating 3D-printable snap-fit joints. This is part of the "Joints & Modular Connectors" library.

## 2. Components

### A. Cantilever Hook (`CantileverHook`)
A positive geometry (solid) representing the flexible beam and the hook head.
**Parameters:**
- `beam_length` (L): The flexible length of the cantilever beam.
- `beam_thickness` (T): The thickness of the beam (determines flexibility/force).
- `beam_width` (W): The width of the beam.
- `hook_depth` (D): How far the hook protrudes beyond the beam.
- `lead_angle` ($\alpha$): The insertion ramp angle (e.g., 30° for easy insertion).
- `return_angle` ($\beta$): The retention angle (e.g., 90° for permanent, 45° for removable).

**Geometric Approach:**
- Draw a 2D profile on the XZ plane representing the side-view of the hook (the beam rectangle + the hook tip polygon).
- Extrude the profile by `beam_width` symmetrically along the Y axis.

### B. Cantilever Catch (`CantileverCatch`)
A tool to cut the necessary recess and catch lip into a female body.
**Parameters:**
- Takes the corresponding `CantileverHook` properties.
- `clearance`: Tolerance gap (e.g., 0.2mm) to expand the cavity so the hook can easily slide in and flex.

**Geometric Approach:**
- Create a cutting volume that includes the insertion shaft (slightly larger than beam thickness + hook depth for flexion room).
- Define the engagement lip where the hook physically rests.
- Best implemented as a boolean cutter returned as a CadQuery solid.

## 3. Integration & Testing
- To visually validate, a `test_snap_fit` method or demo script should instantiate a base block with the catch cut out, and the hook aligned for insertion.
- The default material clearance logic (using `print_settings` where appropriate, or a standard 0.2mm offset) should be applied.

## 4. Edge Cases & Constraints
- Deflection space: The catch cutter *must* carve out enough empty space behind the hook head so the beam can bend backwards during insertion.
- Sharp internal corners: The root of the cantilever beam is prone to stress concentration. A small fillet (e.g., `beam_thickness * 0.5`) at the base root is highly recommended.

## 5. Next Steps
Once approved, the Developer will implement these in `models/mechanical/snap_fit.py` and write the corresponding builder/exporter sequence.