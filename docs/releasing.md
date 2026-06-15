# Releasing vibe-cading

> **Canonical release process** — maintainer-confirmed 2026-06-15; the versioning
> policy and release-cut workflow below are in force. Packaging shipped in **PR #30**
> (commit `455ade0`): `pyproject.toml` tracked at `version = "0.1.0"` (hatchling +
> `hatch_build.py`); `vibe_cading/__commit__.py` is build-generated (untracked).
> PyPI publication remains **gated** — see Decision 1. Referenced from
> [`CONTRIBUTING.md`](../CONTRIBUTING.md) §12 and [`vibe/INSTRUCTIONS.md`](../vibe/INSTRUCTIONS.md).

vibe-cading is an AGPLv3, OSS-bound CadQuery library. Once it ships a `pip`-installable
wheel, the version number is a **consumer-facing contract**: external users pin against
it and SemVer signals tell them whether an upgrade can break their code. This document
defines how that number is chosen, when it is bumped, and how a release is cut.

## Two distinct identifiers — do not conflate them

| Identifier | Source of truth | Meaning | Who/what sets it |
|---|---|---|---|
| `vibe_cading.__commit__` | `vibe_cading/__commit__.py` (generated) | 40-char git SHA — strict **build provenance** / reproducibility | `hatch_build.py` at wheel-build time. **Never hand-edited.** |
| `vibe_cading.__version__` | `pyproject.toml` `[project].version` | Human-facing **release number** (SemVer) | A human, per this document. |

`__commit__` answers *"exactly which tree built this wheel?"*; `__version__` answers
*"what compatibility contract does this release promise?"*. They move independently —
every commit changes `__commit__`, but `__version__` changes only on a deliberate bump.

## Versioning scheme — SemVer, 0.x phase

The package follows [Semantic Versioning](https://semver.org/). While the project is
pre-1.0 (`0.y.z`), the public API is explicitly **not yet stable**, so the 0.x convention
applies:

- **Minor (`y`)** — any **breaking** change to the public surface (below).
- **Patch (`z`)** — additive or backward-compatible change (new model class, new
  optional parameter, bug fix, internal refactor with no surface change).

Graduation to **`1.0.0`** is a maintainer decision, made when the public API is
declared stable and the project is willing to honor full SemVer breakage rules.

### What counts as the "public surface"

A change is **breaking** if it alters any of these in a non-backward-compatible way:

- Public constructor signatures and `.solid` / `.male()` / `.female()` / `.to_cutter()`
  contracts of exported model classes.
- `vibe_cading/cq_utils.py` and base-class / `Protocol` contracts that external
  contributors implement.
- `vibe_cading.print_settings.get_profile()` and the `ToleranceProfile` shape.
- Public names in `vibe_cading/lego/constants.py`.
- `vibe_cading.tools.*` CLI flags and output formats that consumers script against.
- The top-level `vibe_cading/__init__.py` re-export set.

> The `engine_api.json` wire contract carries its **own** `schema_version`
> ([CONTRIBUTING.md](../CONTRIBUTING.md) "Bumping `schema_version`") — that mechanism is
> unchanged and is independent of the package version. A schema bump is a public-surface
> change and therefore *also* drives a package version bump.

## When to bump — per-PR discipline

Mirrors the existing `schema_version` discipline: the bump rides in the **same PR** as
the change that necessitates it, so it is reviewed as part of the diff and can never
drift out of band.

1. A PR that changes the public surface **must** bump `[project].version` in the same diff.
2. A PR with no public-surface change leaves the version untouched.
3. `[project].version` is the **single source of truth**; `vibe_cading/__init__.py`
   re-exports it as `__version__` (no duplicated literal).
4. The reviewer treats an absent-but-required bump (or a bump in the wrong tier) as a
   blocking review finding.

## Changelog

`CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/) format) is **started at the
first post-#30 release** — history is *not* retroactively seeded. From that release on it
carries an `## [Unreleased]` section at the top; every public-surface PR adds its entry
there, and cutting a release renames `Unreleased` to the new version + date.

## Cutting a release

A **GitHub Actions release workflow** (`.github/workflows/release.yml`, added with the
wiring step) automates build + publish; a human only bumps the version and pushes the tag.

1. Confirm `CHANGELOG.md` `Unreleased` is complete for everything since the last tag.
2. Bump `[project].version`; move `Unreleased` → a dated `[x.y.z]` section.
3. Merge that PR to `main`.
4. Tag the merge commit `vX.Y.Z` (annotated tag) and push the tag — this **triggers the
   release workflow**.
5. The workflow runs `python -m build`, asserts the embedded `vibe_cading.__commit__`
   matches the tagged commit and `vibe_cading.__version__` matches the tag, then attaches
   the wheel + sdist to a GitHub Release.
6. **PyPI upload** is a final workflow step using **trusted publishing** (OIDC — no stored
   API token), **gated** behind the publication trigger (see Decision&nbsp;1). Until that
   gate opens, the workflow stops at the GitHub-Release artifacts.

## Decision log

| # | Decision | Resolution |
|---|---|---|
| 1 | PyPI publish trigger | **Confirmed 2026-06-15:** keep the demand gate for the supported public release; **reserve the `vibe-cading` PyPI name now** via a placeholder/yanked `0.1.0` (name-squatting is the only *irreversible* risk). The reservation is a public AGPL publish → it is the maintainer's call; tracked under *Outstanding setup* below, not yet executed. |
| 2 | Tag-on-`main` vs `release/*` branch | **Confirmed 2026-06-15:** tag `vX.Y.Z` directly on `main`; no `release/*` branches. |
| 3 | Publish mechanism | **Confirmed: GitHub Actions release workflow** (`.github/workflows/release.yml`) using trusted publishing (OIDC) — no hand-managed PyPI token. |
| 4 | `CHANGELOG.md` adoption | **Confirmed: start at the first post-#30 release**, no retroactive seeding. |
| 5 | Canonical wiring | **Done 2026-06-15:** pointer added to `CONTRIBUTING.md` §12 and `vibe/INSTRUCTIONS.md` (Licensing & Open Source). |

## Outstanding setup

These follow-up actions implement the confirmed policy; none block the rule from being in force:

1. **Create `.github/workflows/release.yml`** — tag-triggered build (`python -m build`) + version/SHA assertions + GitHub Release upload, with a trusted-publishing PyPI step gated behind Decision 1.
2. **Reserve the `vibe-cading` PyPI name** (maintainer action) — placeholder or yanked `0.1.0` under the project's PyPI trusted-publisher config.
3. **Start `CHANGELOG.md`** at the first post-#30 release (Decision 4).
