# Planned CAD Components Library

We are expanding this repository into a broader Code-CAD mechanical toolkit. Here are the components planned for future development:

## 🔩 Mechanical & Hardware Utilities
- [x] Add fastener drive types: Support generating drive sockets (hex, phillips, slotted, torx) into screw heads for accurate visual rendering and modeling.

## 🛠️ Architecture Refactors
- [x] Refactor hole generation: Extract hole logic from fastener `.to_cutter()` methods into dedicated feature classes (e.g. `ClearanceHole`, `CounterboreHole`, `TeardropHole`) to handle tolerance injections and specialized print profiles independently.
- [x] Establish initial FDM Tolerance baselines: Run grid searches to find the optimal global values for `radial_clearance` and `screw_radial_allowance` to dial-in a standard Bambu Studio hardware profile with `XY Hole Compensation = 0.0mm`.
- [x] Refactor primitive classes (Joints, Screws, Bearings, Axles) to seamlessly support `models.print_settings.ToleranceProfile` injections instead of hardcoded float parameters.
- [ ] Explore true 3D helical thread generation for screws/nuts (behind a `render_threads: bool` flag), carefully evaluating AGPL compliance, performance regressions, and OCCT boolean stability.

## 🚀 Transition to "Open Core" Engine
Based on the new SaaS strategy, this repository (`vibe-cading`) will act as the public core engine for the `vibe-cading-platform`. We need to prepare it for external consumption:
