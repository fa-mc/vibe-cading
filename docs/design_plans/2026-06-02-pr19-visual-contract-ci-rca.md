# RCA — PR #19 visual-contract freshness check fails in CI

**Date:** 2026-06-02
**PR:** #19 `visual-contract-freshness` — "ci(visual-contract): add SVG freshness check + manifest"
**Status:** OPEN, GitHub-mergeable, but **CI RED**. Branch is 2 commits behind `main`.
**Related design brief:** `.agents/plans/2026-05-29-visual-contract-freshness_design.md`

## What the PR adds
- `visual_contracts.toml` — manifest mapping each tracked `.agents/plans/*_design_*.svg` → `(model, view, params)`.
- `tools/check_visual_contract_freshness.py` — regenerates each contract via `tools.preview.export_previews` into a temp dir and **byte-compares** against the committed SVG; plus a bidirectional coverage gate; plus `--update`. Forces `PRINT_PROFILE=fdm_standard` (Phase-B fix) to neutralize local tolerance profiles.
- `.github/workflows/ci.yml` — new "Visual contract freshness" step after Topology check.
- 5 regenerated SVGs + TODO close + a `vibe/INSTRUCTIONS.md` doc paragraph.

## The failure
CI "Visual contract freshness" step exits 1: **`3 / 9 contracts fresh, 6 drifted`**. All other CI steps pass.

Drifted (6): `axle-hole-tip-to-tip-gauge` (iso_ne, top), `axle-cross-hole-gauge` (iso_ne, top), `m3_clearance` (iso_ne), `m3_nut_pocket` (iso_ne).
Fresh (3): `lego-technic-beam` (iso_ne, top, front).

## Root cause (empirically proven)
1. **Clean worktree in the dev container** (no `.env`, no `print_profiles_user.json` — CI-equivalent local state): check returns **`9/9 fresh`**. → local profile files are NOT the cause.
2. **CI installs the identical CAD stack**: `cadquery 2.7.0`, `cadquery-ocp 7.8.1.1.post1` (from the CI install log). → NOT an OCCT/version mismatch.
3. The **6 drifting contracts are exactly the 4 gauge classes that call `cq.Workplane.text()`**; the **3 fresh contracts are the beam (no text())**. Verified by grepping the model files. The drifters are also the large SVGs (119–169 KB — the "heavy tail" the PR body attributes to text-label glyph tessellation).
4. `cq.Workplane.text()` defaults to `font="Arial"`. Arial has no canonical Linux binary; **fontconfig substitutes a host-specific font** — in this Debian container `Arial → LiberationSans-Regular.ttf`. The CI Ubuntu runner resolves/tessellates the font differently (different font binary and/or freetype version), producing **different glyph wire geometry → different SVG path bytes → drift**.

**Conclusion:** The freshness check's byte-exact SVG comparison is **not portable across hosts for any contract whose model uses `cq.Workplane.text()`**. Glyph tessellation depends on the host's resolved font + freetype, which differs between the dev container and the CI runner. The `fdm_standard` pin (Phase-B fix) correctly closed the *tolerance* leak but the design never addressed *font-dependent text rendering*.

**Why prior validation missed it:** The PR validated "9/9 fresh in a clean worktree." A clean worktree neutralizes local `.env`/profile files but runs in the *same container* that produced the committed bytes, so it shares that container's fonts. Only a *different host* (or CI itself) could surface a font-resolution difference.

## Note on the contract's stated purpose
`vibe/INSTRUCTIONS.md` §Visual Contract Deliverable: the SVG exists "to catch axis-orientation, hole-pattern, and convention errors that are invisible in numeric specs alone." Label glyphs are NOT part of that purpose — byte-pinning them adds no model-regression protection while creating the portability failure.

## Fix options on the table (evaluate independently; propose better ones if any)
- **(1) Geometry-only contracts** — render contract SVGs WITHOUT label glyphs (no-label render mode + manifest param), pinning only the geometry the contract protects. Host-independent; keeps a byte guarantee on geometry. Touches the 4 gauge classes' render path.
- **(2) Coverage-only for text contracts** — byte-freshness for plain-geometry contracts (beam); the 6 text gauges become coverage-only (must exist + be registered, not byte-compared). Smallest robust change; loses byte-drift detection on gauges.
- **(3) Pin the font** — vendor Liberation Sans in-repo + pass `fontPath` in every gauge `text()` call (+ install in CI). Preserves full byte-compare; shared-surface change; residual freetype-version risk.
- **(4) Quick CI font install** — add `fonts-liberation` to CI and re-run. Fastest to attempt; may be insufficient (freetype parity); fragile.

## Secondary merge items
- Branch 2 commits behind `main` (#18 + developer-doc) → rebase before merge.
- PR body stale: lists the `INSTRUCTIONS.md` doc as a deferred follow-up, but commit `37b4759` already includes it.

## Advisor outputs
- **TL** recommended **Option 1 (geometry-only contracts)** — byte-compare primitive is correct; its input domain (glyph soup) was wrong. Consolidate the duplicated engraving block into `cq_utils.engraved_labels(..., labels=True)`; gauges register contracts with `labels=false`. Inline fix on the PR branch (not a design-flow reopen).
- **Admin** concurred: inline fix; governance follow-ups = a `cq.text()`-is-host-dependent note in §Visual Contract Deliverable + a §4 "certify on a different host / in CI" rule.

## Resolution (2026-06-02 — CLOSED)
- **PR #19** (squash `5902372`, merged) — implemented Option 1: `engraved_labels()` helper, `labels: bool = True` on the 4 gauges, 6 contracts re-rendered `labels=false` (890→22 paths), `engine_api.json` regenerated, merged `main` in. All CI green; the freshness step now passes on the CI runner.
- **PR #20** (squash `08b3eb4`, merged) — the two governance follow-ups landed in `vibe/INSTRUCTIONS.md` (§Visual Contract Deliverable host-dependent-rendering note + §4 Cross-Host Reproducibility Verification rule). Independently reviewed (APPROVE).
- **Auto-memory** `feedback_validate_reproducible_checks_in_clean_worktree` refined: clean worktree is necessary but not sufficient — certify on a different host / in CI; don't byte-pin `cq.text()`.
- **Wrap-up sign-offs (2026-06-02):** TL OK · Designer OK · Developer OK — no blocking findings.
