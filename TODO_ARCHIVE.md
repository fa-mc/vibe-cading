# Archived TODOs

## 🗄️ Archive (Completed)
- [x] Metric Machine Screws (Flat/Socket/Hex profiles)
- [x] Imperial Machine Screws (UNC 6-32, 4-40)
- [x] Hex Nuts and Captive Slots
- [x] Heat-Set Threaded Inserts (standard Voron/Ruthex specs)
- [x] Self-Tapping Plastics Screws (PT/K-Jet thread forming geometry)
- [x] Set Screws (Grub Screws)
- [x] Hexagonal Standoffs (M-F/F-F Spacers)
- [x] Parametric Bearings (608, 623, 6702) including outer-race press-fit and inner-race shaft cutters
- [x] Neodymium Magnet press-fit cavities and glue pockets
- [x] Dovetail joints (Generators for matching male/female profiles with print tolerances)
- [x] Snap-fit cantilever hooks (For snapping cases and lids together)
- [x] Print-in-place hinges
- [x] PCB Standoffs (Takes an array of (x,y) coordinates to generate mounting pillars with pilot holes)
- [x] Zip-tie anchor points (Unionable loops for cable management)
- [x] Parametric ventilation grilles (Hexagonal matrices and slotted grilles for motor covers)
- [x] Knurled knobs and grip surfaces
- [x] **License Audit:** Ensure the AGPLv3 `LICENSE` file is at the repository root and applied to all headers if necessary.
- [x] **CLA Implementation:** Set up CLA-Assistant (or similar) on GitHub Actions to require contributors to sign a Contributor License Agreement before merging PRs.
- [x] **Dependency Hygiene:** Ensure the `pyproject.toml`/`requirements.txt` is strictly limited to geometry (CadQuery/OCP) and testing. Remove any extraneous web/API dependencies.
- [x] **Packaging:** Convert the directory structure into an installable pip package (e.g., `pip install .`) so the separate private platform worker can import the classes dynamically.
