# Design Brief: Fastener Drives

## Objective
Implement parameterized cutter classes for screw head drive sockets (Hex, Slotted, Torx, Phillips) to allow high-fidelity rendering, following the object-oriented tooling architecture.

## Architecture
- **Location:** `models/mechanical/screws/drives.py`
- **Base Class:** `FastenerDrive(ABC)` exposing a `.cutter(self) -> cq.Workplane` property.
- **Implementations:**
  - `HexDrive(across_flats: float, depth: float)`
  - `SlottedDrive(length: float, width: float, depth: float)`
  - `TorxDrive(size: str, depth: float)` (Simplified 6-point star geometry)
  - `PhillipsDrive(size: str | int, depth: float)` (Simplified cross geometry)

## Technical Constraints
- The `cutter` must originate at `Z=0` and extend in the `-Z` direction by `depth`.
- Must use 2D sketching (`.polyline()`, `.polygon()`, or standard 2D primitives) followed by `.extrude(-depth)` for performance.
- Add an outward overcut (e.g., `+ 0.1` mm on Z=0 if needed, though for a socket going into a head, starting at `Z=0.1` and going to `-depth` ensures it cleanly breaks the top surface).

## API Integration Goal
Later, `MetricMachineScrew` will accept `drive: FastenerDrive | bool = False`.
