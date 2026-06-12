# Design: Arrma Granite Roof Skid Plate
<!-- Filename: 2026-06-07-granite-roof-skid-plate_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: .agents/plans/2026-06-07-granite-roof-skid-plate_req.md
- **Requester role**: @designer
- **Date**: 2026-06-07
- **Dialog rounds**: 1

---

## Objective
A fully parametric CadQuery model of a replaceable roof skid plate for the Arrma Granite V4 body shell, featuring a concave mating surface for adhesive bonding and a domed fore-aft ridge for sliding.

## Architecture / Approach

### Approach chosen
- **Model structure**: A single `GraniteRoofSkidPlate` class returning a `.solid` property.
- **Coordinate System & Orientation**: 
  - **X-axis** = Fore-Aft (vehicle travel direction). **Y-axis** = Lateral.
  - The origin `(0,0,0)` sits at the lowest points of the mating face (the outer edges of the footprint), with the body extruded into +Z. The footprint is centered on X=0, Y=0.
- **Underside geometry**: A concave cylindrical surface (transverse crown) aligned with the X-axis, defined by `roof_radius` (default 200 mm), allowing the plate to seat securely on the roof.
- **Top profile**: A single fore-aft rounded ridge. To avoid costly 3D boolean operations, the entire shape is created by sketching a 2D cross-section in the YZ plane (combining the bottom concave arc, vertical side walls, and top domed arc) and extruding it along the X-axis.
- **Fillets**: Exposed perimeter edges (top curved edges, front/back edges) are filleted (`edge_fillet`) to prevent snagging during a slide. The bottom mating edges remain sharp to sit flush against the shell.
- **Mounting**: Optional vertical bolt holes (disabled by default) subtracted through the plate.

### Visual contract (CAD tasks)
![Design preview — iso_ne](2026-06-07-granite-roof-skid-plate_design_iso_ne.svg)

### Alternatives rejected
- **3D Boolean intersections**: Rejected building a solid box and subtracting an oversized cylinder for the roof, then adding another cylinder for the top dome. This produces floating-point seams and is computationally expensive. The 2D cross-section extrusion is cleaner and more robust.
- **Multiple low ribs**: Rejected in favor of a single thick central ridge, which provides better slide performance and is more economical to print.

## Data & Interface Contracts
- Class `GraniteRoofSkidPlate`
- Constructor arguments:
  - `length: float = 80.0`
  - `width: float = 90.0`
  - `roof_radius: float = 200.0`
  - `wall_thickness: float = 2.5`
  - `ridge_height: float = 6.0`
  - `edge_fillet: float = 3.0`
  - `enable_holes: bool = False`
  - `hole_diameter: float = 5.0`
  - `hole_positions: list[tuple[float, float]] = None`  *(default fallback positions generated if None and holes enabled)*
  - `clearance_profile: ToleranceProfile = None`

## Implementation Plan
- [x] **T1** – Create `vibe_cading/parts/rc/granite_roof_skid_plate.py` containing the `GraniteRoofSkidPlate` class with the specified parameters.
- [x] **T2** – Implement the 2D cross-section sketch in the YZ plane (bottom concave arc, side walls, top domed arc) and extrude along the X-axis. Center the extrusion on the origin.
- [x] **T3** – Apply edge fillets to the exposed perimeter edges, avoiding the bottom mating face edges.
- [x] **T4** – Implement optional bolt-through mounting holes (`enable_holes` logic) using the provided `hole_positions` and `hole_diameter`.
- [x] **T5** – Add the visual contract view to `visual_contracts.toml`.
- [x] **T6** – Write the test suite in `tests/parts/rc/test_granite_roof_skid_plate.py`.

## Tests

| # | Test description | Expected assertion | File / location |
|---|------------------|--------------------|-----------------|
| 1 | Basic geometry generation | `len(result.solids().vals()) == 1`, valid BBox lengths | `tests/parts/rc/test_granite_roof_skid_plate.py` |
| 2 | Bolt holes conditionally cut | When `enable_holes=True`, volume is reduced compared to `enable_holes=False` | `tests/parts/rc/test_granite_roof_skid_plate.py` |
| 3 | Degenerate large roof radius | When `roof_radius=10000`, the bottom is near-planar | `tests/parts/rc/test_granite_roof_skid_plate.py` |
| 4 | Pre-merge representative scale | `python3 tools/preview.py vibe_cading.parts.rc.granite_roof_skid_plate.GraniteRoofSkidPlate --views iso_ne` runs without error | Terminal (Manual step) |

## Success Criteria
1. `GraniteRoofSkidPlate` produces a valid, single contiguous solid.
2. The visual contract matches the intent (concave bottom, top ridge, centered on origin, X-axis travel direction).
3. All tests pass and are CI-ready.

## Out of Scope
- Reverse-engineering actual Granite body STEP/STL.
- Precise body-post hole positions (holes ship disabled by default).
- Multi-part assembly or Lego-Technic interface.
- Drilling guidance / kitting for bolt-through option.
- `build.toml` registration.

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Edge fillets failing | Use a conservative default fillet (3 mm) and select edges carefully. Instruct user to adjust if custom parameters break fillets. |
| Roof dimensions inaccurate | Fully parametric design allows the user to override defaults after measuring their physical shell. |

---

## Design Dialog Log

### Round 1
**TL proposal:**
> Use a 2D sketch extruded along the X-axis to generate the primary geometry instead of 3D booleans.

**Requester challenge / contribution:**
> Agreed. This aligns with the "Prefer 2D sketch" non-functional constraint.

**Resolution:**
> Implemented 2D sketch approach in the Architecture section.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign
- [x] Requester sign-off
- [x] TL sign-off

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [ ] Independent TL
- [ ] Independent Developer
- [ ] Independent Researcher

---

## Implementation Status
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: 3/3 tests pass (100%)
- [x] No new linter / static-check errors
- Developer note: Created the 2D cross-section and extruded to form the robust `GraniteRoofSkidPlate`. Tested geometry with hole clearances resolving dynamically.

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes: Implementation successfully followed the 2D cross-section approach. Tests verify geometric robustness and dynamic hole clearances.

### Domain Expert Review
- [x] **Domain expert sign-off** — data contracts, interface schemas, and domain invariants verified against Data & Interface Contracts
- Domain expert review notes: Interface matches the defined contract.

### Human Final Approval
- [x] **Human approved** for merge / release
- Human notes: "Yes and auto approve going forward"
