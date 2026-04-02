# Planned CAD Components Library

We are expanding this repository into a broader Code-CAD mechanical toolkit. Here are the components planned for future development:

## 🛠️ Architecture Refactors
- [ ] Refactor primitive classes (Joints, Screws, Bearings, Axles) to seamlessly support `models.print_settings.ToleranceProfile` injections instead of hardcoded float parameters.
- [ ] Explore true 3D helical thread generation for screws/nuts (behind a `render_threads: bool` flag), carefully evaluating AGPL compliance, performance regressions, and OCCT boolean stability.

## 🚀 Transition to "Open Core" Engine
Based on the ***REMOVED***, this repository (`vibe-cading`) will act as the public core engine for the `***REMOVED***`. We need to prepare it for external consumption:
