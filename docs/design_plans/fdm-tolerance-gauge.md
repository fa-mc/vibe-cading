# Design Brief: FDM Tolerance Baseline Gauge

**Date:** 2026-04-02
**Task ID:** `fdm-tolerance-gauge`
**Requested by:** designer

## Task Summary

Create a physical, parametric 3D Code-CAD "Tolerance Gauge" block to identify the ideal `radial_clearance` and `screw_radial_allowance` global values for the user's `bambu_p1s` FDM hardware profile. Slicers should run with `XY Hole Compensation = 0.0mm`. The generated block must iteratively test a range of specific radial dimensions (e.g., +0.00 to +0.20 mm) across standard Lego Technic pin holes, Lego Technic axle holes, and M3 machine screw clearance holes, debossing the test offset directly into the top surface of the gauge.

## Coordinate System

| Axis | Direction | Origin reference |
|---|---|---|
| X | Right | Center of the first test hole column |
| Y | Back | Center of the gauge block |
| Z | Up | Bottom face of the gauge block (Z=0) sits on the print bed. Top surface at Z = `thickness`. |

## Dimension Table

| Dimension | Value | Source |
|---|---|---|
| Gauge Block Thickness| 8.0 mm | Standard Technic stud width (fast printing) |
| Hole Y-spacing | 12.0 mm | Clearance between rows |
| Hole X-spacing | 14.0 mm | Clearance between columns (to fit 10mm OD bearings) |
| `radial_clearance` tests | `[0.0, 0.05, 0.10, 0.15, 0.20]` | Testing FDM standard fit range |
| `screw_radial_allowance` tests | `[0.0, 0.05, 0.10, 0.15, 0.20]` | Testing FDM standard fit range |

## Design Decisions

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | How will the user know which hole corresponds to which offset? | Deboss the tested tolerance offset (e.g. "0.15") on the top surface directly above/below the respective test hole. | Eliminates manual counting/measuring and error; labels print successfully face-up if debossed 0.5mm into the top surface. |

## Special Considerations

- **Minimise Material Waste:** 8mm height is adequate to test an M3 screw grip and Lego Technic pin clipping depth.
- **Fast Generation:** Perform all boolean unions of text objects *before* performing a single, bulk `.cut()` operation against the main gauge block to prevent OCCT core stalling.
- All debossed lettering should use a simple font like "Arial" and be at least 4.0mm high for FDM legibility.

## Deliverables

### D1 — Create `ToleranceGauge`
**Description:** Create `models/mechanical/tolerance_gauge.py` representing the physical test block.
**Acceptance criteria:**
- [ ] Class constructor accepts a list of offsets to test (e.g., `offsets=[0.0, 0.05, 0.10, 0.15, 0.20]`).
- [ ] The `_build()` method generates an `N x 4` grid gauge block.
- [ ] Row 1 tests M3 clearance: Generate an array of `MetricMachineScrew.from_size("M3", ...)` clearance sockets. Pass the `radial_allowance=offset` during `.to_cutter()`.
- [ ] Row 2 tests MR85 Bearings: Generate an array of `Bearing(5.0, 8.0, 2.5).outer_pocket(radial_clearance=offset)`. The MR85 bearing has an 8mm OD, which will test precise press-fit requirements for FDM holes.
- [ ] Row 3 tests MR85 Bearing ID: Generate an array of upward-facing cylindrical pegs (shafts). Nominal diameter 5.0mm, tested diameter `5.0 - 2*offset`. This will test the slip/press fit when pushing the bearing over an FDM printed shaft.
- [ ] Row 4 tests Technic pins: Generate an array of `TechnicPinHole`. Nominal diameter `PIN_HOLE_DIAMETER`, tested diameter `PIN_HOLE_DIAMETER + 2*offset`.
- [ ] Each hole/peg has 3D text debossed strictly on the `.faces(">Z")` of the main gauge block explicitly stating the offset (e.g., `"0.15"`).

### D2 — Generation Script `tmp/bambu_p1s_gauge.py`
**Description:** Create a quick launcher that builds the `ToleranceGauge` and exports it to `tmp/tolerance_gauge.step`.
**Acceptance criteria:**
- [ ] Uses `ocp_vscode.show()` and `cq.exporters.export()`.
- [ ] Checks all inputs and prints a success message.
**Dependencies:** D1

## Validation Commands

```bash
# Validate that the gauge script generates and successfully launches
python3 tmp/bambu_p1s_gauge.py

# Optional visual inspect
python3 tools/preview.py models.mechanical.tolerance_gauge.ToleranceGauge
```
