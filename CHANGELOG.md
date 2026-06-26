# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/). While the
project is pre-1.0 the public API is not yet stable — see
[`docs/releasing.md`](docs/releasing.md) for the versioning policy (0.x phase) and
the release-cut process.

This changelog starts at the first tagged release. Earlier development history is
not retroactively seeded here — it lives in the git log. Every public-surface PR
from here on adds an entry under `## [Unreleased]`; cutting a release renames that
section to the new version and date.

## [Unreleased]

## [0.1.2] - 2026-06-26

_Documentation and release-tooling only — no library code change; upgrading from
0.1.1 is optional._

### Changed
- README: added a PyPI install section (`pip install vibe_cading` /
  `vibe_cading[mcp]`) and a headless-Linux `libgl1` / OpenGL caveat for
  CadQuery's geometry kernel; standardized agent terminology to "AI agents".
- Release pipeline: PyPI publish is now gated by a per-release required-reviewer
  approval on the `pypi` GitHub Environment (replacing the `PYPI_PUBLISH` repo
  variable).

## [0.1.1] - 2026-06-24

### Added
- `LegoTechnicLLiftarm`: new 90°-bent Lego Technic studless liftarm (L-shaped / bent
  beam) class (`vibe_cading.lego.technic_l_liftarm`), parametric in both arm lengths
  (default 3×5), with chamfered pin holes on the 8 mm stud grid and rounded ends.
- `PrintInPlaceHinge.screw_holes`: new countersunk M3 flat-head mount holes — 2 per
  leaf (4 total) — controlled by `screw_holes: bool` (default `True`).

## [0.1.0] - Initial

### Added
- Initial public release of the `vibe-cading` CadQuery library: parametric
  mechanical models (screws, joints, bearings, axles, gears) and Lego-Technic /
  RC interface parts.
- Tolerance system: `vibe_cading.print_settings.get_profile()` and the
  `ToleranceProfile` shape, with user-overridable `print_profiles*.json` and
  `<machine>__<material>[__<brand>]` profile keys.
- Shared primitives in `vibe_cading.cq_utils` and Lego constants in
  `vibe_cading.lego.constants`.
- `vibe_cading.tools.*` CLI utilities (preview, section slicer, hole finder,
  boolean diff, calibration helper, STEP analysis).
- `engine_api.json` wire contract (carries its own `schema_version`).
- Build provenance: `vibe_cading.__version__` (from package metadata) and
  `vibe_cading.__commit__` (build-stamped git SHA).
- MCP (stdio) interface — `python -m vibe_cading.mcp`: a `vibe_cading.mcp`
  subpackage exposing the engine's deterministic introspection tools
  (`list_engine_classes`, `query_engine_class`, `get_design_context`) plus a
  local `compile_model`, over MCP stdio (JSON-RPC on stdin/stdout — no network
  listener, no API key). `mcp` ships as an optional `[mcp]` extra
  (`pip install -e ".[mcp]"`, pinned `mcp>=1,<2`), so a plain install never
  pulls the SDK's ASGI tree; a two-layer CI guard
  (`tools/check_mcp_import_isolation.py`) enforces that `vibe_cading.mcp` never
  enters the library import graph. `get_design_context` surfaces the curated
  Lego nominal allowlist (incl. the studded-System block nominals) + the live
  tolerance profile + doc pointers. (RFC #41.)
