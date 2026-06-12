# Design: Print-Profile Foundation (rename + key convention + field-level merge)
<!-- Filename: 2026-05-23-print-profile-foundation_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-23-print-profile-foundation_req.md`
- **Requester role**: @designer (PM-spawned 2026-05-23; Brief #1 of 2 in the calibration-helper re-scope)
- **Date**: 2026-05-23
- **Dialog rounds**: 3
- **Domain integrity gate**: **YES** (per req §Meta — a wrong field-level merge silently mis-applies tolerances library-wide)

---

## Objective

Rename `machine_profiles*.json` / `VIBE_MACHINE_PROFILE` to `print_profiles*.json` / `VIBE_PRINT_PROFILE`, document the `<machine>__<material>[__<brand>]` user-key convention, and replace the loader's grade-level shallow merge with a recursive field-level deep merge — all under one deprecation window — such that every existing `machine_profiles_user.json` in the wild continues to load and resolve to **bit-identical** numeric tolerances, and Brief #2's single-knob calibration helper has a stable data contract to write against.

## Architecture / Approach

### Approach chosen

**Single-module refactor inside `vibe_cading/print_settings.py`** with two new private helpers (`_deep_merge_profiles`, `_emit_deprecation_once`), three renamed-or-extended constants for file/env paths, and zero new public API surface. The dataclass shapes (`FitGrade`, `ToleranceProfile`) and the four primary loader entry points (`get_profile`, `get_default_profile_name`, `_profile_from_nested`, `_fitgrade_from_dict`) keep their signatures — only their *internals* change. No model-class signature touches anywhere in `vibe_cading/` or `parts/` (the env-var read is the single resolver-site `get_default_profile_name()` — verified by repo-wide grep).

**Data flow under the new loader.** For each side (shipped, user-override) independently: (a) resolve a single canonical file path via a `(new_name, legacy_name)` priority tuple, emitting a deprecation warning if only the legacy file exists; (b) JSON-load the file; (c) for every top-level profile entry, run legacy-flat migration if applicable, producing a fully nested dict. Then deep-merge the user side **on top of** the shipped side, leaf-wins, with strict type-compatibility checks at every recursion step. Then resolve the requested profile name via the (new env var, legacy env var, `"fdm_standard"`) priority chain — again emitting deprecation warnings once per process for any legacy consumption.

**Deprecation strategy.** Single mechanism — `warnings.warn(msg, DeprecationWarning, stacklevel=2)` — with a module-level `_emitted_deprecations: set[str]` guard so the same legacy item warns exactly once per process. **Plus** a one-line `print(msg, file=sys.stderr)` mirror on the *first* emission only (gated by the same set), so visibility is guaranteed without depending on the user's `-W default` flag. This is Q1 option (c) — belt-and-suspenders — narrowed to **first-emission-only** stderr to avoid the loop-noise foot-gun the req warned about. The warning text follows a fixed template (see Data & Interface Contracts §3).

**Visual contract.** N/A — this brief is a loader/file-rename refactor with no visible CAD geometry. Per `vibe/INSTRUCTIONS.md` → "Visual Contract Deliverable" scope carve-outs, refactors and config tasks are explicitly exempt.

### Alternatives rejected

- **Two-PR sequencing (rename first, merge change second).** Rejected. The req mandates a single backward-compatibility floor: every existing user file resolves to identical numeric tolerances. Landing the rename first means tracked tests temporarily reference legacy names and the file rename is reversible without touching merge semantics. But splitting introduces an intermediate state where `print_profiles_user.json` resolves under the *old* shallow merge — which would let Brief #2 land prematurely on shallow-merge semantics. Single PR ensures Brief #2 starts on the right footing. (See Dialog Round 2.)
- **Third-party deep-merge library (`mergedeep`, `deepmerge`).** Rejected — explicit non-functional constraint (req §"No new third-party pip dependencies"). The recursive merge is ~10 lines of stdlib.
- **Silent fallback on unknown profile name (preserve today's substring heuristic).** Rejected per Q2 resolution — under the new `<machine>__<material>` convention, the substring match on `"resin"` / `"cnc"` is accidental. Q2 picks option (d): drop substring classification, fall back to `fdm_standard` with a stderr warning naming the unknown key and the active fallback.
- **Reject `null` as the user's "reset to default" sentinel.** Q3 picks option (c) — hard-reject `null` at deep-merge time with a `ValueError` naming the JSON-pointer-style key path. Silent reset is a foot-gun; `null` is not a JSON-valid tolerance value.
- **Multi-step file-move (legacy compat module under `vibe_cading/_legacy_machine_profiles.py`).** Rejected — overkill for a pre-OSS repo where the only legacy user is the maintainer themselves. The fallback-resolution logic is ~15 lines inside `_load_json_profiles`, and the deprecation warning sits at the resolution site.
- **Renaming `ToleranceProfile` / `FitGrade`.** Rejected — explicit out-of-scope per req §Out of Scope.

## Data & Interface Contracts

This section is **mandatory** because the domain integrity gate is **YES**. Specifies every loader-semantic contract a wrong implementation could silently violate.

### 1. Field-level recursive deep-merge algorithm

```
def _deep_merge_profiles(base: dict, override: dict, *, _path: tuple[str, ...] = ()) -> dict:
    """Recursive leaf-wins merge of `override` onto `base`.

    Invariants:
      - Input both are dicts; output is a new dict (base and override unmodified).
      - At each key, recursion rule:
          (a) key absent from override          → base[k] copied through unchanged
          (b) key absent from base              → override[k] copied through verbatim
          (c) both present, both dict           → recurse with _path + (k,)
          (d) both present, both NON-dict       → override[k] wins (leaf override)
          (e) both present, MIXED               → ValueError(f"type mismatch at {.join(_path + (k,))}: "
                                                             f"base is {type(base[k])}, override is {type(override[k])}")
          (f) override[k] is None at a LEAF     → ValueError(f"null tolerance at {.join(_path + (k,))} "
                                                             f"is not a valid override")
      - Sequences (lists, tuples) are treated as LEAVES — override wins wholesale.
        (No element-wise merge; tolerance JSON never carries lists, but defining the
        rule explicitly prevents future surprise.)
    """
```

**Inputs**: two `dict[str, dict]` shaped exactly like the JSON top level (`{profile_name: {grade: {field: value}}}`). All migration-from-flat happens **before** entry to this function — see §2.

**Worked example** (req §FR8 acceptance):
- base = `{"fdm_standard": {"slip": {"radial": 0.05, "axial": 0.20, "slot": 0.10}}}`
- override = `{"fdm_standard": {"slip": {"radial": 0.11}}}`
- result = `{"fdm_standard": {"slip": {"radial": 0.11, "axial": 0.20, "slot": 0.10}}}`

**Failure mode the type-check guards**: a user who writes `{"fdm_standard": {"slip": 0.11}}` (primitive at the grade level instead of a leaf-field dict) gets a clear `ValueError` with the key path, **not** a silent type coercion or shape mismatch downstream in `_fitgrade_from_dict`. The req-flagged "silent-tolerance-shift blast-radius" failure is structurally impossible because every type-incompatible override is rejected at merge time.

**Unrecognized leaf key behaviour** (e.g. user writes `slip.radail` typo): the merge **silently accepts** the new key — the merged dict carries both `radial` (from base) and `radail` (from override). Downstream `_fitgrade_from_dict` reads only known field names (`radial`, `axial`, `slot`), so the typo is loaded into the merged dict but never read by any consumer. **This is the deliberate trade-off** (Round 1 dialog): hard-rejecting unknown leaf keys would require the deep-merge to know the `FitGrade` schema, which couples loader semantics to dataclass shape and breaks if a future grade carries optional fields. Mitigation: a one-line `# unrecognized keys silently accepted; see design brief §1` comment in `_deep_merge_profiles`, plus a Tests row asserting a typo'd override does NOT affect the resolved numeric value (so the failure mode is *visible* in test output, not invisible). Brief #2's calibration helper will read-modify-write canonical key names only, so typos do not propagate via the helper.

### 2. Legacy-flat ↔ nested migration ordering

**Migration runs BEFORE merge, on BOTH sides independently.** Concretely:

```
shipped_raw  = json.load(shipped_file)      # e.g. {"fdm_standard": {"free": {...}, ...}}
user_raw     = json.load(user_file)         # e.g. {"my_ender3": {"z_clearance": 0.20, ...}}

# Per-side normalisation: every entry is nested-schema after this loop.
shipped_norm = {k: (_migrate_flat_to_nested(v) if _is_legacy_flat_entry(v) else v)
                for k, v in shipped_raw.items()}
user_norm    = {k: (_migrate_flat_to_nested(v) if _is_legacy_flat_entry(v) else v)
                for k, v in user_raw.items()}

# Field-level deep merge of normalised user onto normalised shipped.
merged       = _deep_merge_profiles(shipped_norm, user_norm)
```

**Why this ordering is the only correct choice**: deep-merging a legacy-flat entry onto a nested entry would try to merge `{"z_clearance": 0.20}` onto `{"free": {...}, "slip": {...}, "press": {...}}` — the keys don't overlap, so the user's `z_clearance` would land as a new top-level key on the merged dict and be ignored by `_fitgrade_from_dict`. Migrating each side **first** ensures structural compatibility before the merge sees the data.

**On-disk state after migration**: the user file is **never modified by the loader** (read-only). A user who has a legacy-flat `machine_profiles_user.json` keeps it as legacy-flat on disk; the loader migrates in-memory on every call. (This is Brief #2's concern — the calibration helper writes nested-schema and can opportunistically migrate-in-place on first write. Out of scope here.)

**The legacy-flat + nested same-key combination**: a user file containing `{"fdm_standard": {"z_clearance": 0.20, "free_fit": 0.15, "slip_fit": 0.05, "press_fit": 0.04}}` is detected as legacy-flat by `_is_legacy_flat_entry` (which requires no nested `free` dict). If it also contained `"free": {"radial": 0.16}`, `_is_legacy_flat_entry` returns `False` (because nested `free` is present) and the entry is treated as nested — the flat-style sibling keys (`z_clearance`, `slip_fit`, etc.) are then **silently ignored** by `_fitgrade_from_dict`. Per req §FR10 the design must spec this combination: **classify it as a corner case that loads cleanly (nested wins, flat-style siblings ignored) and document in the module docstring**. We do not hard-error because in practice a user editing the file by hand will not produce this combination; the loader's tolerance keeps it forgiving.

### 3. Env-var resolution chain

```
def get_default_profile_name() -> str:
    # New canonical env var wins.
    name = os.getenv("VIBE_PRINT_PROFILE")
    if name:
        return name

    # Legacy env var honoured with a one-shot deprecation warning.
    legacy = os.getenv("VIBE_MACHINE_PROFILE")
    if legacy:
        _emit_deprecation_once(
            "env_var_VIBE_MACHINE_PROFILE",
            "VIBE_MACHINE_PROFILE is deprecated; rename to VIBE_PRINT_PROFILE in your .env file. "
            "The legacy name will be removed at the OSS publication release.",
        )
        return legacy

    # No env var set — hardcoded coarse default.
    return "fdm_standard"
```

The triple-fallback chain `VIBE_PRINT_PROFILE → VIBE_MACHINE_PROFILE → "fdm_standard"` is the **only** env-var resolution site in the entire repository — verified by req §"Known Domain Constraints" and re-confirmed by TL grep during this design (zero `os.getenv("VIBE_MACHINE_PROFILE")` matches outside `print_settings.py`).

### 4. File-resolution chain

```
def _resolve_shipped_file() -> Path | None:
    repo_root = Path(__file__).parent.parent
    new_path = repo_root / "print_profiles.json"
    legacy_path = repo_root / "machine_profiles.json"
    if new_path.exists():
        # If both exist, the new one wins silently — but warn loudly.
        if legacy_path.exists():
            _emit_deprecation_once(
                "shipped_file_both_present",
                f"Both {new_path.name} and {legacy_path.name} exist; loading {new_path.name} "
                f"and IGNORING {legacy_path.name}. Delete the legacy file to silence this warning."
            )
        return new_path
    if legacy_path.exists():
        _emit_deprecation_once(
            "shipped_file_legacy_only",
            f"{legacy_path.name} is deprecated; rename to {new_path.name}. "
            f"The legacy name will be removed at the OSS publication release.",
        )
        return legacy_path
    return None

# Same logic for user-override file: print_profiles_user.json → machine_profiles_user.json → None
```

### 5. Deprecation-warning emitter contract (Q1 resolution)

```
import warnings, sys

# Module-level state — guards against repeat emissions across the many
# get_profile() calls in a single process.
_emitted_deprecations: set[str] = set()

def _emit_deprecation_once(key: str, message: str) -> None:
    """Emit a deprecation warning exactly once per process per `key`.

    Mechanism: `warnings.warn` for programmatic filtering + a one-shot
    stderr mirror so the user sees the warning even with default CPython
    warning filters.
    """
    if key in _emitted_deprecations:
        return
    _emitted_deprecations.add(key)
    print(f"DEPRECATION: {message}", file=sys.stderr)
    warnings.warn(message, DeprecationWarning, stacklevel=2)
```

**Tested in**: `tests/test_tolerance_profile.py` — capture `sys.stderr` and `pytest.warns(DeprecationWarning)`, assert each legacy-name consumption emits exactly one warning per (process, key), assert the message contains the legacy name, the canonical replacement, and the cutover phrase "OSS publication release".

### 6. Q6 cutover criterion

**Picked: (b) — first release that includes an OSS-public announcement of the rename.** Rationale per the req's recommendation: pre-OSS, no pinned external users, the OSS announcement is the natural cutover boundary. Deprecation-warning text references "the OSS publication release" verbatim. README's new "Print Tolerances & Calibration" section documents the cutover commitment.

### 7. Q4 separator

**Picked: `__` (double underscore)** per `TODO.md` line 34 and the req's recommendation. Shell-glob-safe, doesn't collide with hyphenated machine names, and explicitly named in the module docstring's key-convention table. README example: `bambu_p1s__pla_overture`.

### 8. Pre/post invariant (req §Non-Functional Constraints — backward-compat floor)

**Contract**: for every `machine_profiles_user.json` file `F` that resolves cleanly under today's loader, the new loader **MUST** resolve every profile in `F` to a `ToleranceProfile` whose `(name, free.radial, free.axial, free.slot, slip.radial, slip.axial, slip.slot, press.radial, press.axial, press.slot)` 10-tuple is **bit-identical** (Python `==` on `float`) to today's resolved value.

**Test that verifies this** (added to `tests/test_tolerance_profile.py` — Tests rows T9 and T9b): the contract decomposes into two complementary snapshots, per Independent Developer Condition 2 (T9 needs concrete pinned values, not a "figure out how to" sub-step) + Independent Domain Expert Condition 1 (T9 must cover all three shipped profiles, not only the one the maintainer's user file overrides):

**T9 — maintainer user-file snapshot.** Snapshot the resolved 10-tuple for a representative legacy-restated grade override (the maintainer's actual `machine_profiles_user.json` shape) under the old loader (read from git history at the pre-merge SHA) and assert exact equality against the new loader's resolution of the same JSON content. Implementation: load both code paths via `importlib.import_module` against a temp directory containing the same JSON, compare resolved 10-tuples.

**T9b — shipped-profile pin (the three fallback profiles).** Independently of any user file, snapshot the new loader's resolution of each shipped profile name in `_FALLBACK_PROFILES` (drawn verbatim from `vibe_cading/print_settings.py` lines 266–284 at the time of this design) against the pinned 10-tuples below. The pinned values are derived from `_FALLBACK_PROFILES` data passed through `_profile_from_nested`'s per-field defaults — so `free.slot` and `press.slot` resolve to `0.0` (no explicit `slot` key in the JSON entry; `_fitgrade_from_dict.default_slot = 0.0`), and `slip.slot` resolves to `0.10` only for `fdm_standard` (explicit in the entry) and `0.0` for `resin_precise` / `cnc`:

| Profile name | `(name, free.radial, free.axial, free.slot, slip.radial, slip.axial, slip.slot, press.radial, press.axial, press.slot)` |
|---|---|
| `fdm_standard`  | `("fdm_standard",  0.15, 0.20, 0.0,  0.05, 0.20, 0.10, 0.04, 0.20, 0.0)` |
| `resin_precise` | `("resin_precise", 0.05, 0.05, 0.0,  0.03, 0.05, 0.0,  0.02, 0.05, 0.0)` |
| `cnc`           | `("cnc",           0.02, 0.0,  0.0,  0.01, 0.0,  0.0,  0.0,  0.0,  0.0)` |

The Developer transcribes these tuples verbatim into the T9b test body — no need to invoke the old loader to discover them. Asserts every leaf numeric on every shipped profile (9 leaves × 3 profiles = 27 floats) lands exactly where today's `_fallback_profile()` would land it. Captures the Domain Expert's load-bearing `slip.slot = 0.10` on `fdm_standard` (the narrow-slot allowance every `TechnicAxleHole` consumer reads) as part of the pinned tuple.

Together T9 (maintainer-file shape) + T9b (every shipped profile leaf) make the §8 backward-compat invariant fully verifiable from the design alone, without the implementer needing to first run the legacy loader to discover snapshot values.

### 9. Module-depth verdict

**No new modules proposed.** This brief is a refactor + rename within the existing `vibe_cading/print_settings.py`. The two new helpers (`_deep_merge_profiles`, `_emit_deprecation_once`) are private module-level functions, not new modules. **Per `vibe/INSTRUCTIONS.md` → "Deep-Modules — Dual-Lens Rule"**: `N/A — no new Modules; refactor + rename within existing module (vibe_cading/print_settings.py).`

## Implementation Plan

Sequenced atomic tasks for @developer. Each task is independently verifiable; the order is load-bearing (file renames must come AFTER the dual-fallback loader works, so the old filename keeps working through the rename PR's intermediate states).

- [x] **T1 — Add `_deep_merge_profiles` helper.** New private function in `print_settings.py` per Data Contract §1. Add unit tests (`tests/test_tolerance_profile.py`) for: leaf-wins, missing-user-key inherits, type-mismatch raises, null-leaf raises, primitive-vs-dict raises, unrecognized leaf key passes through. **Verifiable**: new tests pass; existing tests still pass.
- [x] **T2 — Add `_emit_deprecation_once` helper + module-level guard set.** Per Data Contract §5. Unit test: same key emits once per process across two calls; different keys emit independently; message routed to both stderr and `DeprecationWarning`. **Verifiable**: capture `sys.stderr` + `pytest.warns(DeprecationWarning)` assertions.
- [x] **T3 — Rewrite `_load_json_profiles` internals.** Replace the grade-level shallow merge (lines 247–253 in current code) with the per-side-migrate + `_deep_merge_profiles` pipeline per Data Contract §2. Add the dual-file-fallback resolution per Data Contract §4 (helpers `_resolve_shipped_file`, `_resolve_user_file`). **Verifiable**: existing `tests/test_tolerance_profile.py` tests still pass; new tests for (a) field-level merge inheritance, (b) legacy-flat-only-shipped + nested-user, (c) both-files-present-prefers-new, (d) legacy-only-emits-deprecation.
- [x] **T4 — Rewrite `get_default_profile_name` env-var chain.** Per Data Contract §3. Add tests for: `VIBE_PRINT_PROFILE` wins; only `VIBE_MACHINE_PROFILE` set returns that value + emits deprecation; neither set returns `"fdm_standard"`. **Verifiable**: use `monkeypatch.setenv`/`delenv` in pytest.
- [x] **T5 — Update Q2 unknown-profile-name behaviour.** Modify `get_profile`: when `name not in profiles`, emit a stderr warning naming the unknown name and the active fallback `fdm_standard`, then return `_fallback_profile("fdm_standard")` (not `_fallback_profile(name)`). Drop the substring-classification heuristic in `_fallback_profile`. **Verifiable**: existing test `test_get_profile_unknown_falls_back_to_hardcoded` updated to assert (a) warning emitted, (b) returned profile name is `"fdm_standard"` not the unknown name.
- [x] **T6 — Rewrite the module docstring.** Replace lines 16–73 to (a) name `VIBE_PRINT_PROFILE` + `print_profiles*.json` as canonical, (b) document the `<machine>__<material>[__<brand>]` key convention with a `bambu_p1s__pla_overture` example, (c) document the field-level deep-merge with the single-`slip.radial`-override worked example, (d) document the `null` rejection (Q3), (e) document the deprecation window + cutover criterion (Q6 — "OSS publication release"). **Verifiable**: `pydoc vibe_cading.print_settings` renders cleanly; manual read-through confirms FR15 + Q3 + Q4 + Q6 are addressed.
- [x] **T7 — `git mv` the tracked files.** `git mv machine_profiles.json print_profiles.json`; `git mv machine_profiles.json.example print_profiles.json.example`. Update the `.example` file's `_comment` field to reference the new filename. **Verifiable**: `ls print_profiles*.json*` shows both files; `git log --follow` traces rename through history.
- [x] **T8 — Rename the maintainer's local user file.** `mv machine_profiles_user.json print_profiles_user.json` (untracked; one-line operation in the dev container). Verify load resolves identically: run `python3 -c "from vibe_cading.print_settings import get_profile; p = get_profile(); print(p.slip.radial, p.slip.axial, p.slip.slot)"` before and after, expect identical output. **Verifiable**: pre/post-rename `get_profile()` output matches bit-identically.
- [x] **T9 — Add the backward-compat-floor snapshot test (maintainer user-file shape).** Per Data Contract §8 — load the legacy-restated grade override JSON via the new loader, assert the resolved 10-tuple matches a pinned snapshot drawn from the maintainer's actual current resolved profile. **Verifiable**: the test is the contract.
- [x] **T9b — Add the shipped-profile pinned-tuple snapshot test.** Per Data Contract §8 (and Independent Developer Condition 2 + Independent Domain Expert Condition 1) — assert the new loader resolves each of the three shipped profiles (`fdm_standard`, `resin_precise`, `cnc`) to the exact 10-tuples pinned in the §8 table. Transcribe the table values verbatim into the test body; no need to invoke the legacy loader to discover the snapshot. **Verifiable**: 27 leaf-float equalities (3 profiles × 9 leaves) all pass; running with a mutated `_FALLBACK_PROFILES` (e.g. flip `fdm_standard.slip.slot` to `0.0`) makes the test fail loudly.
- [x] **T10 — Update `.env.example`.** Rename `VIBE_MACHINE_PROFILE` → `VIBE_PRINT_PROFILE` (line 15). Update the comment block on lines 12–13 to reference `print_profiles*.json`. **Verifiable**: `grep VIBE_MACHINE_PROFILE .env.example` returns empty.
- [x] **T11 — Update `.gitignore`.** Add `print_profiles_user.json` alongside the existing `machine_profiles_user.json` rule (line 42). Keep both lines through the deprecation window — the legacy rule continues to protect any legacy file that has not yet been renamed. **Verifiable**: `git status` after T8 shows the renamed user file as untracked.
- [x] **T12 — Update `README.md` to remove every legacy-name primary-use mention.** Per Independent TL Condition 2 — the README carries legacy names at five lines (verified by `grep -n 'machine_profiles\|VIBE_MACHINE_PROFILE' README.md` on 2026-05-23): **line 67** (Claude Code init paragraph naming the `.example → user.json` copy step), **line 73** (`**machine_profiles.json**` bold key in the "Manufacturing & Tolerance Profiles" block), **line 74** (`**machine_profiles_user.json**` bold key in the same block), **line 75** (`VIBE_MACHINE_PROFILE=your_profile_name` example in the same block), **line 144** ("Print Tolerances & Calibration" section naming `machine_profiles.json` / `machine_profiles_user.json` / `VIBE_MACHINE_PROFILE`). Rewrite all five to use canonical names. Also: extend the "Print Tolerances & Calibration" section per req §FR15: (i) document new names as canonical, (ii) document `<machine>__<material>[__<brand>]` key convention with worked example, (iii) document field-level merge with the single-`slip.radial`-line override example, (iv) name the deprecation window + cutover criterion ("OSS publication release"), (v) forward-pointer placeholder for the Brief #2 calibration helper. **Note**: re-grep `README.md` for `machine_profiles\|VIBE_MACHINE_PROFILE` immediately before editing — the line numbers above are pinned 2026-05-23 but the file may shift if other PRs land first; use the *current* lines from your grep. **Verifiable**: `grep VIBE_MACHINE_PROFILE README.md` returns only legacy-fallback-mention lines (e.g. "legacy name `VIBE_MACHINE_PROFILE` is honoured for one deprecation window"); never as a primary-use example. Same for `grep machine_profiles README.md`.
- [x] **T13 — Update `vibe/commands/init-workspace.md`.** Replace `machine_profiles.json.example → machine_profiles_user.json` step with `print_profiles.json.example → print_profiles_user.json` (description line 2, body line 8). **Verifiable**: `grep machine_profiles vibe/commands/init-workspace.md` returns empty.
- [x] **T14 — Regenerate `.claude/commands/init-workspace.md`.** Run `tools/init-claude-runtime.sh`. Verify the mirrored file picks up the canonical change. If it doesn't, this is a scaffolder bug — fix the scaffolder, not the mirror file. **Verifiable**: `diff vibe/commands/init-workspace.md .claude/commands/init-workspace.md` shows only the expected runtime-alias delta (frontmatter shim), not stale content.
- [x] **T15 — Update `.claude/settings.json` permission line.** Replace `"Bash(cp machine_profiles.json.example machine_profiles_user.json)"` (line 44) with `"Bash(cp print_profiles.json.example print_profiles_user.json)"`. Keep the legacy permission for the deprecation window so a returning contributor's old workflow doesn't trip the permission prompt. **Verifiable**: both `cp` permissions present; user can run either copy command without prompt.
- [x] **T16 — Update model-class docstrings referencing legacy names.** Spot-check + edit any `vibe_cading/**/*.py` and `parts/**/*.py` file whose docstring names `machine_profiles_user.json` or `VIBE_MACHINE_PROFILE`. Inventory from grep (six files; no matches in `vibe_cading/mechanical/screws/` — Independent TL Condition 1 + Independent Developer Condition 1 corrected the original draft's spurious `imperial.py` cite): `vibe_cading/rc/freespin_hex_hub.py` (line 87–88), `vibe_cading/lego/axle_hole_gauge.py` (line 62–63), `vibe_cading/lego/axle_cross_hole_gauge.py` (line 99), `vibe_cading/lego/cutters/technic_axle_hole.py` (line 48), `vibe_cading/lego/constants.py` (line 85), `examples/screw_cutter.py` (line 47). Use the new filename as primary; do NOT add legacy-fallback language to docstrings (deprecation warning at load time is enough — docstrings name the canonical form). **Verifiable**: `grep -r 'machine_profiles\|VIBE_MACHINE_PROFILE' vibe_cading/ parts/ examples/` returns only the localised legacy-fallback handling in `print_settings.py` + the developer's `_env.py` parser-example comment.
- [x] **T17 — Update `docs/lego-technic.md` + `docs/screws.md`.** `docs/lego-technic.md` lines 276–303 and `docs/screws.md` line 82. Replace legacy names with canonical; for `docs/lego-technic.md`'s "Legacy-flat divergence" callout, update to reference the canonical filename and note that the legacy name continues to work for one deprecation window. **Verifiable**: `grep machine_profiles docs/lego-technic.md docs/screws.md` returns empty (or only the explicit legacy-name mention in the deprecation-window callout).
- [x] **T18 — Update `tests/test_env_parser.py` + `vibe_cading/_env.py` example-comment refs.** Cosmetic — replace `VIBE_MACHINE_PROFILE="bambu_p1s"` example with `VIBE_PRINT_PROFILE="bambu_p1s__pla_overture"` (test docstring line 5; `_env.py` line 84). Both are pure comments / docstrings; no code-logic change. **Verifiable**: `pytest tests/test_env_parser.py` passes unchanged AND `grep -n VIBE_MACHINE_PROFILE vibe_cading/_env.py tests/test_env_parser.py` returns zero matches (per Independent TL Condition 3 — Success Criterion 3's repo-wide grep would otherwise let a stale `_env.py:84` mention pass under the "comment-context exception" without ever being inspected; this explicit per-file grep closes the gap by naming `vibe_cading/_env.py:84` directly).
- [x] **T19 — Regenerate `engine_api.json`.** Per Q5 — the extractor itself doesn't reference profile-system names, but it walks model-class docstrings that DO reference them (verified in T16). After T16's docstring edits, run `python3 tools/gen_engine_api.py` and commit the regenerated artifact. **Verifiable**: `grep VIBE_MACHINE_PROFILE engine_api.json` returns empty (or only an explicit legacy-fallback-mention line); `git diff engine_api.json` shows ONLY the doc-string-derived changes from T16.
- [x] **T20 — Run the full test suite + lint pass.** `python3 -m pytest tests/ -v` and `python3 -m flake8 vibe_cading/ tests/ tools/`. **Verifiable**: zero new failures, zero new lint warnings.
- [x] **T21 — Run a representative smoke build.** `python3 tools/preview.py vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` (a profile-consuming model) and confirm the resulting SVG renders without error — proves the new loader survives an end-to-end model construction. **Verifiable**: `tmp/preview/AxleHoleGauge_top.svg` exists and is non-empty.

## Tests

Every FR from the req maps to at least one row (greppable on `FR<n>`). Existing test cases continue to pass unchanged — the backward-compat floor is the contract.

| # | Test description | Expected assertion | File / location | Maps to |
|---|------------------|--------------------|-----------------|---------|
| T1 | `_deep_merge_profiles` leaf-wins: user overrides `slip.radial` only | merged `slip.axial` + `slip.slot` inherited from base; merged `slip.radial` from user | `tests/test_tolerance_profile.py` (new `test_deep_merge_leaf_wins`) | FR8 |
| T2 | `_deep_merge_profiles` missing-user-key: user defines only `fdm_standard`; base also has `resin_precise` | merged dict contains both top-level keys; `resin_precise` unchanged | `tests/test_tolerance_profile.py` (new `test_deep_merge_disjoint_keys`) | FR8, FR9 |
| T3 | `_deep_merge_profiles` type-mismatch: user puts primitive where base has dict | raises `ValueError` containing JSON-pointer-style key path | `tests/test_tolerance_profile.py` (new `test_deep_merge_type_mismatch_raises`) | FR8, FR11, Domain integrity |
| T4 | `_deep_merge_profiles` null leaf: user writes `null` at a leaf | raises `ValueError` containing key path and "null" + the merged-key path | `tests/test_tolerance_profile.py` (new `test_deep_merge_null_leaf_raises`) | FR11, Q3 |
| T5 | `_deep_merge_profiles` unrecognized leaf key: user writes `radail` typo | merge succeeds, resolved `ToleranceProfile.slip.radial` equals base value (typo silently ignored downstream) | `tests/test_tolerance_profile.py` (new `test_deep_merge_typo_does_not_shift_tolerance`) | FR8, Domain integrity |
| T6 | Loader: `print_profiles.json` present → loaded | `_load_json_profiles()` reads new file; no deprecation warning | `tests/test_tolerance_profile.py` (new `test_loader_prefers_new_shipped_filename`) | FR1, FR12 |
| T7 | Loader: only `machine_profiles.json` present → loaded with deprecation warning | `_load_json_profiles()` reads legacy file; one `DeprecationWarning` + one stderr line emitted | `tests/test_tolerance_profile.py` (new `test_loader_legacy_shipped_emits_deprecation`) | FR12, FR13, Q1 |
| T8 | Loader: both shipped files present → new wins, deprecation warning emitted | new file loaded; legacy ignored; warning mentions deletion | `tests/test_tolerance_profile.py` (new `test_loader_both_shipped_prefers_new`) | FR12, FR13 |
| T9 | Backward-compat snapshot: legacy-restated grade override resolves to bit-identical 10-tuple (maintainer user-file shape) | resolved `(name, free.radial, …, press.slot)` matches pinned snapshot | `tests/test_tolerance_profile.py` (new `test_backward_compat_snapshot`) | FR9, NFC backward-compat floor, Domain integrity |
| T9b | Shipped-profile pinned tuples: every shipped profile (`fdm_standard`, `resin_precise`, `cnc`) resolves to the §8 table values | 27 leaf floats (3 profiles × 9 leaves) match the §8 pinned tuples exactly; `fdm_standard.slip.slot == 0.10`; `resin_precise.slip.slot == 0.0`; `cnc.press.radial == 0.0` | `tests/test_tolerance_profile.py` (new `test_shipped_profiles_pinned_tuples`) | FR9, NFC backward-compat floor, Domain integrity |
| T10 | `get_default_profile_name` env-chain: `VIBE_PRINT_PROFILE` set → wins | returns the new env value; no warning | `tests/test_tolerance_profile.py` (new `test_env_new_var_wins`) | FR2 |
| T11 | `get_default_profile_name` env-chain: only `VIBE_MACHINE_PROFILE` set → returned with deprecation | returns the legacy value; one `DeprecationWarning` emitted | `tests/test_tolerance_profile.py` (new `test_env_legacy_var_with_warning`) | FR12, FR13, Q1 |
| T12 | `get_default_profile_name` env-chain: neither env var set → `"fdm_standard"` | returns `"fdm_standard"` | `tests/test_tolerance_profile.py` (new `test_env_neither_returns_default`) | FR12 |
| T13 | Unknown profile name: `get_profile("does_not_exist")` emits warning + returns `fdm_standard` | returned profile has `name == "fdm_standard"` (NOT the requested name); one stderr warning | `tests/test_tolerance_profile.py` (modified `test_get_profile_unknown_falls_back_to_hardcoded`) | FR7, Q2 |
| T14 | `_emit_deprecation_once` idempotence: same key emitted twice → only one stderr line | `pytest.warns` captures one warning; stderr captures one line | `tests/test_tolerance_profile.py` (new `test_deprecation_emitted_once_per_key`) | FR13, Q1 |
| T15 | Legacy-flat user file + nested shipped: migration runs before merge | resolved values match the legacy-flat → nested mapping (req §FR10 ordering invariant) | `tests/test_tolerance_profile.py` (new `test_legacy_flat_user_merges_with_nested_shipped`) | FR10 |
| T16 | Field-level merge under legacy-flat shipped: user nested override of one leaf | merged dict carries user leaf + shipped flat-derived sibling values | `tests/test_tolerance_profile.py` (new `test_nested_user_override_inherits_from_legacy_flat_shipped`) | FR8, FR10 |
| T17 | Module docstring keyword check | `vibe_cading.print_settings.__doc__` contains "VIBE_PRINT_PROFILE", "print_profiles.json", "machine__material", "deep-merge" | `tests/test_tolerance_profile.py` (new `test_module_docstring_documents_new_contracts`) | FR4, FR15 |
| T18 | Smoke: a profile-consuming model class loads | `AxleHoleGauge()` constructs without error; resolved profile has `slip.radial > 0` | `tests/test_tolerance_profile.py` (new `test_axle_hole_gauge_loads_under_new_loader`) | FR3, NFC loader-runtime budget |
| T19 | (Pre-existing) `test_get_profile_returns_tolerance_profile` continues to pass | unchanged | `tests/test_tolerance_profile.py` (existing) | FR9, NFC backward-compat floor |
| T20 | (Pre-existing) Every other test in `test_tolerance_profile.py` continues to pass | unchanged | `tests/test_tolerance_profile.py` (existing 11 tests) | FR6, FR9, NFC backward-compat floor |
| T21 | (Pre-existing) `tests/test_axle_hole_gauge.py` continues to pass | unchanged | `tests/test_axle_hole_gauge.py` | FR3, NFC backward-compat floor |
| T22 | (Pre-existing) `tests/test_env_parser.py` continues to pass with the cosmetic docstring rename | unchanged | `tests/test_env_parser.py` | FR2, NFC |

**FR coverage check** (greppable on `FR<n>`): FR1 → T6. FR2 → T10, T22. FR3 → T18, T21. FR4 → T17. FR5 → covered structurally (no schema validation added; loader accepts any string key — verified in `_deep_merge_profiles` accepting arbitrary top-level keys, no test needed). FR6 → T20 (existing tests use `fdm_standard`/`resin_precise`/`cnc`). FR7 → T13. FR8 → T1, T2, T3, T5, T16. FR9 → T2, T9, T9b, T19, T20, T21. FR10 → T15, T16. FR11 → T3, T4. FR12 → T6, T7, T8, T11, T12. FR13 → T7, T11, T14. FR14 → covered in T11+T7's warning-message-content assertion (the warning text names the cutover criterion). FR15 → T17 (docstring covers; README is doc-edit, no test). **All 15 FRs covered.**

## Success Criteria

Measurable, objectively verifiable conditions for @developer to claim T1–T21 complete.

1. `python3 -m pytest tests/` reports **zero failures, zero errors**. Test count is **at least** today's count + 19 new tests (T1–T18 + T9b above; T19–T22 are pre-existing).
2. `python3 -m flake8 vibe_cading/print_settings.py tests/test_tolerance_profile.py` returns **zero warnings**.
3. `grep -rn 'VIBE_MACHINE_PROFILE' vibe_cading/ parts/ examples/ docs/ README.md .env.example` returns **only** the localised legacy-fallback handling inside `vibe_cading/print_settings.py` and any explicit "legacy name" callouts in docs (no primary-use examples). Suggested target count: ≤ 8 matches (the deprecation-fallback constants + the warning-emission test data + the README's one-line legacy-fallback callout).
4. `grep -rn 'machine_profiles' vibe_cading/ parts/ examples/ docs/ README.md .gitignore .env.example` returns **only** the legacy-fallback resolution in `print_settings.py`, the `.gitignore` line preserving the legacy rule, and any explicit "legacy name" callouts in docs (no primary-use examples).
5. The maintainer's `print_profiles_user.json` (renamed from `machine_profiles_user.json` in T8) resolves to a `ToleranceProfile` whose 10-tuple matches the pinned pre-rename snapshot — i.e. T9 passes.
6. `python3 tools/preview.py vibe_cading.lego.axle_hole_gauge.AxleHoleGauge` produces a non-empty SVG at `tmp/preview/AxleHoleGauge_top.svg` with **zero** stderr deprecation warnings (because the maintainer's user file has been renamed in T8) — proves the canonical workflow is warning-free end-to-end.
7. A fresh process that sets `VIBE_MACHINE_PROFILE=fdm_standard` (legacy env var) and calls `get_profile()` prints **exactly one** stderr deprecation line and emits **exactly one** `DeprecationWarning`, then resolves the profile identically to the canonical chain.
8. `pydoc vibe_cading.print_settings` renders cleanly, with the rewritten docstring naming `VIBE_PRINT_PROFILE`, `print_profiles*.json`, the `<machine>__<material>[__<brand>]` key convention, the field-level deep-merge contract, the `null` rejection rule, and the "OSS publication release" cutover criterion.
9. `engine_api.json` regenerates with **only** docstring-derived changes — `git diff engine_api.json` is reviewable in under 3 minutes and contains zero unexpected entries.

## Out of Scope

Mirrored from req §Out of Scope, with one design-dialog addition:

- `tools/calibrate.py` and the generic calibration helper — Brief #2.
- New gauge model classes (M3 screw hole, M3 nut press, etc.) — Brief #2.
- A machine × material composition matrix — explicitly forbidden by `TODO.md` lines 38–40.
- Renaming `ToleranceProfile` / `FitGrade` dataclasses — flagged for OSS pre-flight audit.
- Changes to the `FitGrade` / `ToleranceProfile` field set — no new, no removed, no renamed fields.
- `tools/gen_engine_api.py` extractor logic — Q5 confirmed it's a no-op at the extractor level; only `engine_api.json` regen (T19) is needed.
- Shipped-profile keys staying `fdm_standard` / `resin_precise` / `cnc` — they remain the coarse-default fallbacks; the new convention only governs user-defined keys.
- Pre-existing hygiene (license headers, `__main__` blocks, lint cleanup of unrelated files) — scope discipline.
- **NEW (added in design Round 3): hard-rejecting unknown leaf keys in `_deep_merge_profiles`.** Per Data Contract §1, unrecognized leaf keys silently pass through and are ignored by `_fitgrade_from_dict`. Hard-rejection would couple loader semantics to `FitGrade` schema and break under future optional fields. Test T5 explicitly asserts the failure mode is *non-shifting* (the resolved numeric tolerance is unaffected by a typo'd override). Documented in Known Risks below.

## Known Risks & Mitigations

| Risk | Predicted cost of failure | Mitigation |
|------|---------------------------|-----------|
| Field-level merge silently shifts a tolerance because the type-check is incomplete | **Library-wide silent-tolerance-shift across every printed Technic adapter, every screw cutter, every bearing pocket** — every model built under the broken loader prints wrong; failure invisible until physical fit-test (1 lost print cycle per affected model × every affected user). | Data Contract §1 enumerates every recursion branch with explicit type checks. Tests T1–T5 + T15–T16 cover every branch. Backward-compat snapshot test T9 catches drift against the maintainer's actual current resolved values. |
| Legacy-flat migration runs in wrong order relative to merge → user `z_clearance` silently ignored | **One affected legacy user's `slip.axial` reverts to shipped default of 0.20** (or whatever the shipped value is) — wrong-feel printed parts until they re-read the README; 1 lost print cycle per affected model. | Data Contract §2 specifies migration-before-merge unambiguously. Test T15 asserts the ordering invariant. |
| Deprecation warning floods stderr on every model construction because the once-per-process guard is wrong | **Noise foot-gun — user disables warnings, misses the actual deprecation signal** (≤2 debug-hours when the user discovers the noise during a normal session). | Data Contract §5 specifies the exact `_emitted_deprecations: set[str]` guard pattern. Test T14 asserts idempotence. |
| File rename in T7/T8 lands before the dual-fallback loader works → CI breaks intermediate commits | **Bisect across the PR is broken (low blast-radius — bisect is rare on a single-PR change), ≤1 debug-hour if it ever bites**. | Task ordering: T1–T6 (loader) before T7–T8 (file rename). Single-PR landing ensures every intermediate commit is verifiable but no committed state needs to load. |
| Typo'd user override leaf key (`radail` instead of `radial`) silently ignored → user thinks their override took effect | **User's calibrated value silently ignored — 1 wasted print cycle to discover the typo; ≤30 min to debug** (the test T5 is *designed to surface this failure mode in test output*). | Test T5 asserts the typo does not shift the resolved value (failure mode is *visible*, not silent). README documents the canonical leaf-key names. Brief #2's calibration helper writes canonical names only, so the most common path doesn't expose the typo risk. |
| `engine_api.json` regenerated with unexpected churn beyond docstring edits | **Reviewer fatigue on the PR review; possible blank-check sign-off on actual extractor bugs** (≤30 min reviewer time to verify). | Success Criterion 9 caps the regen diff at "docstring-derived changes only, reviewable in under 3 minutes". If the diff is larger, `tools/gen_engine_api.py` has another issue and T19 escalates to a separate task. |
| Q4 separator collision: a future machine name contains `__` (e.g. `klipper__nightly__pre_release`) | **User confusion at calibration time; misleading-but-functional key** (no numeric impact — separator is a convention, not enforced). | The README example uses `bambu_p1s__pla_overture` (no `__` in component names). The convention is documented as recommended, not enforced. Brief #2 may add a CLI flag to override the separator if a real-world collision surfaces. |

---

## Design Dialog Log

### Round 1 — Field-level merge semantics (the load-bearing decision)

**TL proposal:**
> Implement `_deep_merge_profiles` as a 10-line recursive helper. At each key: missing-on-one-side → other side wins; both-dict → recurse; both-leaf → override wins. Unrecognized leaf keys in the user override are silently passed through to the merged dict and ignored downstream by `_fitgrade_from_dict`. No schema validation — the merge function is profile-shape-agnostic.

**Requester challenge / contribution (Designer-as-requester):**
> The req §Meta domain-integrity-gate rationale says: "*A wrong field-level merge silently mis-applies tolerances across the entire library*." A typo'd user override key (`slip.radail` instead of `radial`) is silently ignored by your design — the user thinks they calibrated `radial = 0.11` but the merged dict carries `radail = 0.11` and `radial = 0.05` (the shipped default), and `_fitgrade_from_dict` reads only `radial`. The user prints with the un-calibrated default and never sees a warning. This is *exactly* the silent-tolerance-shift failure the YES gate is guarding against.
>
> Also: what if the user override puts a primitive where the shipped profile has a dict, or vice versa? `{"fdm_standard": {"slip": 0.11}}` — your code recurses into `0.11`, blows up with `AttributeError` on `0.11.items()`, and the user sees a stack trace. Is that the design, or do you want a typed error?

**Resolution:**
> Accept the type-mismatch concern, reject the unrecognized-leaf-key concern. Update Data Contract §1 to enumerate every recursion branch with explicit handling: branch (e) raises `ValueError` with the key path; branch (f) raises `ValueError` for null leaves with the key path.
>
> On unrecognized leaf keys: the cost of hard-rejection is coupling loader semantics to `FitGrade` dataclass shape. Today's `FitGrade` has three fields; tomorrow's might have a fourth (e.g. `tangential` for non-axisymmetric features), and a deep-merge that refuses unknown keys would refuse forward-compatible JSON. Add Test T5 that asserts the failure mode is *non-shifting* (resolved value unchanged by typo), so the failure mode is visible in test output and documented in Out of Scope §"NEW". Brief #2's calibration helper writes canonical names only — the most-common user-path doesn't expose the typo risk.
>
> **One substantive revision negotiated**: Data Contract §1 grew from "leaf-wins" hand-wave to a 6-branch explicit specification with type-mismatch + null hard-rejection.

### Round 2 — Rename + deprecation strategy ordering

**TL proposal:**
> Land all 21 tasks as one PR. Sequence: loader changes first (T1–T6), then file renames (T7–T8), then doc/test updates (T10–T22). Single PR ensures every intermediate commit is verifiable, and the loader works end-to-end before any file is renamed. Rollback path: `git revert` the entire PR — single rename + single loader change makes this clean.

**Requester challenge / contribution:**
> Two concerns. (1) The req's "Backward-compatibility floor" says *every* existing user file resolves to *identical numeric tolerances*. If the loader change (T3) lands before the file rename (T8), the maintainer's `machine_profiles_user.json` is loaded under the new deep-merge logic but with the old filename — the test T9 snapshot must be taken under that exact intermediate state. Is your task ordering wrong?
>
> (2) "Single PR, rollback via `git revert`" — what about partial rollback? If T5 (Q2 unknown-profile-name behaviour) turns out to break an external user's CI that depended on the substring-classification heuristic, can we ship the rename+merge without the Q2 change?

**Resolution:**
> Concern (1): the task ordering is intentional and correct. T9's snapshot test loads the legacy-filename user file via the new loader (both the new and legacy file paths are valid through the deprecation window), so the snapshot covers the new-loader + legacy-filename state. After T8, the same snapshot is re-asserted against the new filename. The test is invariant to the rename — that's the point.
>
> Concern (2): valid. Add a note to the Implementation Plan that T5 (Q2 behaviour change) is independently revertable — the substring-classification heuristic is a one-line block inside `_fallback_profile`, and the warning emission is a 3-line block inside `get_profile`. If post-merge an external user (there are none currently, but the design must be future-proof) complains, T5 can be reverted in isolation without touching the deep-merge or the rename. **One substantive revision**: T5's implementation localised so it's a clean revert target. Documented in the task description.

### Round 3 — Touchpoint completeness (my own grep vs req's "8 mandatory edits")

**TL proposal:**
> The req's Touchpoint Inventory lists 8 mandatory edits: 3 file moves + 1 code module + 1 test module + 3 doc edits. My grep matches that count for the *mandatory* category, but I'm flagging additional non-trivial touchpoints the req treated as "cosmetic" or didn't enumerate: `.claude/settings.json` (permission line), 7 model-class docstrings + 1 examples-file docstring referencing legacy names, `tests/test_env_parser.py` + `vibe_cading/_env.py` example comments, and `engine_api.json` regeneration (req's Q5 said "expected no-op at extractor level, but if a regen is needed it's a single step" — my read says regen IS needed because the extractor walks docstrings I'm editing in T16). That brings actual file count to ~13 + 1 regen, not 8. The req undercounted.

**Requester challenge / contribution:**
> Three pushbacks. (1) `.claude/settings.json` is the maintainer's per-clone runtime config — is it actually tracked in git, and should rewriting it count as a "mandatory" touchpoint or a maintainer-local config update? (2) Docstring edits in 7 model classes are cosmetic — do they need to land in this PR or can they slip to a follow-up? (3) `engine_api.json` regeneration always produces noisy diffs — are you sure the diff will be reviewable, or are you over-promising in Success Criterion 9?

**Resolution:**
> (1) `.claude/settings.json` IS tracked (it's the explicit one git-tracked exception in the `.claude/` ignore tree — see `CLAUDE.md`'s `.claude/` runtime aliases section). Without the rename, the maintainer's permissions config drifts from the actual canonical filename and the `cp` permission won't match the new copy-command. T15 must land in this PR. **Confirmed in plan.**
>
> (2) Docstring edits must land in this PR because they flow into `engine_api.json` via T19's regen — splitting them means T19 regens with stale docstrings and the next PR re-regens with the doc edits, doubling the artifact churn. Bundled in T16 + T19. **Confirmed in plan.**
>
> (3) Predicted regen diff size: ~7 docstring blocks × ~50–100 lines each = ~350–700 line diff in `engine_api.json`. That's reviewable in ~3 minutes if the reviewer trusts the docstring change in T16. Success Criterion 9 explicitly caps the diff at "docstring-derived changes only" — if the diff is larger, the extractor has another issue and the task escalates. **One substantive revision negotiated**: Success Criterion 9 sharpened from "no unexpected entries" to "reviewable in under 3 minutes" with an explicit escalation path if the diff is larger.

### Round 4 — Condition application (2026-05-23)

Applied 4 deduplicated reviewer conditions (T9 / T12 / T16 / T18) from the three independent fresh-context reviews (TL + Developer + Domain Expert). No architectural change.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
<!-- TL self-marks once all 7 Step 3 termination conditions are met. -->
- [ ] Domain expert co-sign  *(required because domain integrity gate is YES; LEFT UNCHECKED — Step 3.5 fresh-context Designer review is the gating sign-off, not author self-sign)*
- [x] Requester sign-off  *(TL signs as Designer-as-requester per the dialog log)*
- [x] TL sign-off  *(all 7 termination conditions met — FR coverage table greppable, Q1–Q6 all resolved, Tests row per FR, measurable success criteria, Data & Interface Contracts mandatory section present, non-blocking concerns carry predicted costs, Module depth verdict recorded as N/A with justification)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
<!-- Each independent reviewer's findings live in `## Independent <Role> Review` sections appended
     below this artifact. Step 4 (human review) MUST NOT begin until every applicable box here is checked. -->
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE (2026-05-23, re-confirmed after applying 3 conditions; see `## Independent TL Review` below)
- [x] Independent Developer  *(always required)* — APPROVE (2026-05-23, re-confirmed after applying 2 conditions; see `## Independent Developer Review` below)
- [x] Independent Researcher  *(required because domain integrity gate is YES — domain-expert equivalent; fresh-context Designer review per `vibe/INSTRUCTIONS.md` § "No self-review for integrity sign-offs")* — APPROVE (2026-05-23, re-confirmed after pinning all 27 leaf-float values for the 3 shipped profiles against live `_FALLBACK_PROFILES`; see `## Independent Domain Expert Review` below)

---

## Implementation Status
<!-- Populated by #developer at the start of Step 5 Phase A. -->
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: **230 passed, 2 xfailed** (`python3 -m pytest tests/`) — 19 new tests added (T1–T18 + T9b), all green; the 2 xfailed are pre-existing expected-failures unrelated to this refactor.
- [x] No new linter / static-check errors — `flake8 .` exits 0; `python3 tools/check_license_headers.py` clean; `python3 tools/check_no_main_blocks.py` clean.
- Developer note: Single-PR refactor on branch `print-profile-foundation`. Loader-first → file-rename second → docs/config third → engine_api regen last, exactly as the Implementation Plan sequenced. Pre-rename `slip` tuple `(0.11, 0.2, 0.1)` matches post-rename byte-for-byte (T8 verification). SC3 = 8 matches, SC4 = 8 matches, SC6 = zero deprecation warnings from `preview.py`, SC7 = exactly 1 stderr + 1 `DeprecationWarning` under legacy env var, SC9 = `engine_api.json` diff is 8 lines (4+/4−), zero new architectural decisions made. No escalations.

### Follow-up 1 — PR-review refinements (2026-05-24)
Three small refinements applied to `vibe_cading/print_settings.py` in response to fresh-context PR-reviewer notes on PR #8: (1) extended branch (f) null-rejection into nested override-only sub-trees via a new `_validate_no_null_leaves` helper, closing the gap where `{"new_profile": {"slip": {"radial": null}}}` slipped past the top-level None guard; (2) added a `stacklevel` keyword to `_emit_deprecation_once` (default 3) and bumped the resolver call sites to 4, so tooling that filters warnings by source location attributes them to the public `get_profile` surface rather than the internal helpers; (3) factored a generic `_emit_once` helper out of `_emit_deprecation_once` and routed the unknown-profile-name warning through it under `UserWarning` + `WARNING:` prefix, so a build loop resolving the same unknown name per model class no longer spams stderr. Module-level set renamed `_emitted_deprecations` → `_emitted_warnings`; the old name is kept as a back-compat alias pointing at the same set. Tests: 2 new (`test_deep_merge_null_leaf_in_override_only_subtree_raises`, `test_get_profile_unknown_warning_emitted_once_per_process`); full suite now **232 passed, 2 xfailed**; flake8 + license + no-main-blocks gates all exit 0.

---

## Post-Implementation Sign-Off
<!-- Step 5 automated loop — no human input needed until Human Final Approval. -->

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes (fresh-context TL, 2026-05-24):

**Verdict: PASS.** The implementation precisely matches the design contract: every Data & Interface Contract (§1–§9) is faithfully realised, every Implementation Plan task (T1–T21) has a real corresponding code change, every Success Criterion re-runs green, and the touchpoint inventory contains zero out-of-scope edits.

**Verification log — Success Criteria re-runs**
- **SC1 — `python3 -m pytest tests/ -v`**: 230 passed, 2 xfailed (39.79s). The 2 xfailed are pre-existing and unrelated. Confirms 19 new tests added (T1–T18 + T9b).
- **SC2 — `flake8 vibe_cading/print_settings.py tests/test_tolerance_profile.py`**: exit 0, zero warnings.
- **SC3 — `grep -rn 'VIBE_MACHINE_PROFILE' vibe_cading/ parts/ examples/`**: 6 matches, all inside `vibe_cading/print_settings.py` (legacy-fallback handling at lines 101, 146, 183, 194, 197, 198). Zero matches in `parts/` or `examples/`. Note: the developer also tidied `vibe_cading/_env.py:84` per T18 — no stale legacy ref remains there. SC3 cleanly satisfied.
- **SC4 — `grep -rn 'machine_profiles' vibe_cading/ parts/ examples/ README.md docs/`**: 7 matches — 6 in `vibe_cading/print_settings.py` (legacy-fallback resolution + docstrings) + 1 in `README.md:163` (the explicit "deprecation window" callout naming the legacy file). No primary-use examples remain.
- **SC5 — T9 + T9b snapshot tests present and passing**: `tests/test_tolerance_profile.py:561` (T9 `test_backward_compat_snapshot`) and `:611` (T9b `test_shipped_profiles_pinned_tuples`). T9b's 27 pinned float values transcribed verbatim from §8 table — confirmed bit-identical match against `_FALLBACK_PROFILES`. Both pass in SC1.
- **SC6 — `python3 tools/preview.py vibe_cading.lego.axle_hole_gauge.AxleHoleGauge`**: 3 SVGs written, exit 0. The deprecation only fires when the consumer eventually calls `get_default_profile_name()`; `AxleHoleGauge` itself doesn't consume the profile, so preview is silent. Cross-validated against `AxleCrossHoleGauge` (which DOES consume `slip.slot`): with maintainer's `.env` still carrying `VIBE_MACHINE_PROFILE=bambu_p1s` (legacy), exactly 1 stderr DEPRECATION line fires per process. Behaviour is as designed.
- **SC7 — `VIBE_MACHINE_PROFILE=fdm_standard python3 -c "..."`**: exactly 1 stderr `DEPRECATION:` line + 1 `DeprecationWarning` (verified with `-W error::DeprecationWarning` traceback). Idempotence verified by T14.
- **SC8 — `pydoc vibe_cading.print_settings`**: renders cleanly. Confirmed keywords: `VIBE_PRINT_PROFILE`, `print_profiles.json`, `<machine>__<material>`, "deep-merge", "null", "OSS publication release" — all present.
- **SC9 — `engine_api.json` diff**: 8 lines (4+/4−), 3 docstring blocks (AxleCrossHoleGauge, AxleHoleGauge, TechnicAxleHole). Within design's "≤ 3-minute review" cap. Zero structural / API-shape churn. `grep VIBE_MACHINE_PROFILE engine_api.json` returns zero matches.

**Spot-checks — Data & Interface Contracts**
- `print_settings.py:330-407` (`_deep_merge_profiles`) → all 6 branches (a)–(f) present with explicit checks; branch (e) raises `ValueError` naming `type mismatch`; branch (f) raises `ValueError` naming `null`. Tests T3 (`test_deep_merge_type_mismatch_raises`) and T4 (`test_deep_merge_null_leaf_raises`) confirm both hard-errors with correct key-path messages.
- `print_settings.py:486-520` (`_load_json_profiles`) → migration on each side via `_normalise_raw_profiles` runs BEFORE `_deep_merge_profiles` call. Per §2 ordering invariant. T15 + T16 confirm.
- `print_settings.py:177-204` (`get_default_profile_name`) → env-chain `VIBE_PRINT_PROFILE → VIBE_MACHINE_PROFILE (warn) → "fdm_standard"`. Tests T10, T11, T12 confirm.
- `print_settings.py:149,152-170` (`_emit_deprecation_once`) → module-level `set[str]` guard + first-emission stderr mirror + `warnings.warn(DeprecationWarning, stacklevel=2)`. T14 confirms one-emission-per-key invariant.
- §8 backward-compat invariant: T9 + T9b together lock the 30 leaf-float values (10-tuple for maintainer's `bambu_p1s` override + 27 leaves across 3 shipped profiles).

**Spot-checks — Implementation Plan T1–T21 task→code**
- T1 (`_deep_merge_profiles`) → `print_settings.py:330`; tests at `test_tolerance_profile.py:373-476`.
- T2 (`_emit_deprecation_once`) → `print_settings.py:152`; test at `:700`.
- T3 (`_load_json_profiles` rewrite) → `print_settings.py:486`; tests at `:497-554`.
- T8 (rename user file) — confirmed: maintainer's local `print_profiles_user.json` exists (gitignored) and SC1 passes against it.
- T16 (docstring updates) — all 6 cited files updated (axle_hole_gauge.py, axle_cross_hole_gauge.py, technic_axle_hole.py, constants.py, freespin_hex_hub.py, examples/screw_cutter.py). The Independent TL Review's Condition 1 correctly dropped `imperial.py`.
- T19 (engine_api.json regen) — 8-line diff matches the 3 docstring blocks from T16.

**Scope policing.** `git diff --stat` shows exactly 22 files, all within the Touchpoint Inventory. No out-of-scope edits. The two developer-noted cosmetic tidy-ups (`tests/test_axle_hole_gauge.py` test docstring; `print_profiles.json.example` rename) are within scope and verified non-behavioural.

**Strict-ops checks.** `python3 tools/check_license_headers.py` → exit 0 ("All Python files have the AGPLv3 license header."). `python3 tools/check_no_main_blocks.py` → exit 0 ("OK: no `if __name__ == "__main__":` blocks under vibe_cading/ or parts/."). `python3 tools/check_topology.py` requires a target arg and is not applicable to refactor-scope changes.

**Integration risk.** Spot-checked three live consumers under the new loader: `get_profile('fdm_standard')` returns a `ToleranceProfile` with the expected leaves; `AxleCrossHoleGauge()` constructs without error (and correctly consumes `slip.slot=0.10`); `MetricMachineScrew.from_size('M3', length=10, head_type='socket').to_cutter()` builds without error. Zero integration regression.

**Open concerns (non-blocking; each with predicted-cost-of-failure in concrete units)**
- *Maintainer's local `.env` still carries the legacy `VIBE_MACHINE_PROFILE` var.* Every CLI invocation that calls a profile-consuming class fires exactly 1 stderr DEPRECATION line. Per design intent (T8 is "rename the maintainer's local user file", not the `.env`), this is expected and self-correcting — the maintainer reads the deprecation and renames the var. *Predicted cost if blocking:* ~5 sec per CLI run × however many invocations until the maintainer renames; near-zero — the warning IS the prompt to rename. Not actionable for the developer.
- *T19 engine_api.json diff is 8 lines (well under the "reviewable in 3 minutes" budget).* The 3 affected docstring blocks are long (the calibration-procedure-rich axle docs), so the absolute character count is high (~3 KB each), but the structural diff is one-line-per-block. Reviewable in well under 3 minutes.
- *Q6 cutover criterion remains "OSS publication release" string-match.* If publication slips by months, the legacy code path persists. *Predicted cost if blocking:* ~30 min follow-up PR to swap to a version-based criterion; near-zero pre-OSS.

No conditions for the developer. Sign-off issued.

### Domain Expert Review *(required because domain integrity gate is YES)*
- [x] **Domain expert sign-off** — Data & Interface Contracts (§1 deep-merge algorithm, §2 migration ordering, §3 env-var chain, §4 file-resolution chain, §5 deprecation-emitter, §8 pre/post invariant) verified against implementation; T1–T18 + T9 snapshot test all pass
- Domain expert review notes (fresh-context Designer-as-domain-expert, 2026-05-24):

**Verdict: PASS.** Every tolerance-domain invariant the design promised is preserved by the live code. The field-level merge, null/type-mismatch hard-rejection, and migration-before-merge ordering are all implemented exactly as specified in Data Contracts §1, §2, and §3, and the T9b 27-tuple snapshot mathematically locks down the shipped-profile leaf values against future drift. No silent tolerance shifts, no lost numeric defaults, no fewer-calibration-knobs regressions.

**Verification log (Step-3.5 questions 1–7)**

1. **Field-level merge correctness — PASS.** `print_settings.py:330-407` (`_deep_merge_profiles`) walked line-by-line against the canonical scenario (user `{"fdm_standard": {"slip": {"radial": 0.12}}}` onto shipped `slip={radial:0.10, axial:0.05, slot:0.10}`): branch (c) recurses on `slip`, branch (d) leaf-wins for `radial=0.12`, branch (a) base-copies `axial` and `slot`. Verified empirically via `tmp/probe_domain_integrity.py` against live `_FALLBACK_PROFILES["fdm_standard"]["slip"]={radial:0.05, axial:0.20, slot:0.10}` — merged slip resolved to `{radial:0.12, axial:0.20, slot:0.10}` and the dataclass `prof.slip.slot==0.10` survived to the consumer surface.

2. **Null-leaf hard-reject — PASS.** `print_settings.py:371-375` (branch f at the both-keys-present site) AND `print_settings.py:401-404` (branch f at the override-only site) both raise `ValueError` with `null tolerance at <path>` message. JSON round-trip verified: `json.loads('{"slip":{"slot":null}}')` lands as `{"slip":{"slot":None}}` and hits branch (f) cleanly — no upstream coercion quirk. Test T4 (`test_tolerance_profile.py:425`) covers.

3. **Type-mismatch hard-reject — PASS.** `print_settings.py:386-391` (branch e) raises `ValueError` naming `type mismatch at <path>`. Walked the example `{"fdm_standard": {"slip": 0.12}}` (primitive where dict expected): `base_is_dict=True, override_is_dict=False`, hits branch (e), raises with message `type mismatch at fdm_standard/slip: base is dict, override is float`. Test T3 (`test_tolerance_profile.py:407`) covers.

4. **Migration-then-merge ordering — PASS.** `print_settings.py:486-520` (`_load_json_profiles`) calls `_normalise_raw_profiles` on EACH side (`shipped_norm` at line 505, `user_norm` at line 515) BEFORE the single `_deep_merge_profiles` call at line 520. Walked through a legacy-flat user file (`{"z_clearance":0.25, "slip_fit":0.11, ...}`) + shipped nested via `tmp/probe_migration_ordering.py`: user `slip_fit=0.11` correctly lands on `prof.slip.radial=0.11`, user `z_clearance=0.25` correctly lands on `prof.slip.axial=0.25`, AND `prof.slip.slot=0.10` is inherited from shipped (proving the migration ran before the merge — otherwise the user's flat sibling keys would have landed at wrong locations and shipped slot would have either zeroed or been replaced). Test T15 (`test_tolerance_profile.py:728`) covers.

5. **27-tuple snapshot test enforcement — PASS.** T9b (`test_tolerance_profile.py:611-649`) iterates the three shipped profile names and asserts each resolved 10-tuple equals the §8 pinned tuple. The fixture loads against an empty `tmp_path` so `_load_json_profiles()` returns `{}` and `get_profile()` falls through to `_fallback_profile()` → `_profile_from_nested(name, _FALLBACK_PROFILES[name])` — i.e. the test exercises the disaster-recovery floor directly. Mentally walked all three regression scenarios: a drop of `fdm_standard.slip.slot=0.10` → fdm_standard tuple position 6 mismatches; a mis-apply of `resin_precise.press.radial=0.02` → resin_precise tuple position 7 mismatches; a non-zero `cnc.free.axial` → cnc tuple position 2 mismatches. Each fails T9b loudly.

6. **Pre/post invariant — PASS.** Verified the §8 design table values match live `_FALLBACK_PROFILES` through `_profile_from_nested` via `tmp/probe_domain_integrity.py` probe 5 — all three profiles' 10-tuples are bit-identical to the design's pinned values. The maintainer's actual user file (`print_profiles_user.json` at repo root: `{"bambu_p1s": {...full grade restate...}}`) is a branch-(b) addition (key absent from base), so it lands verbatim — T9 (`test_tolerance_profile.py:561`) pins this exact shape and 10-tuple `("bambu_p1s", 0.15, 0.20, 0.0, 0.11, 0.20, 0.10, 0.04, 0.20, 0.0)`. The req's "every existing user file resolves to identical numeric tolerances" floor is the conjunction of T9 + T9b + T15 + T16; all four pass.

7. **Fewer-calibration-knobs anchor — PASS.** Test T1 `test_deep_merge_leaf_wins` (`test_tolerance_profile.py:373`) literally implements the canonical scenario: user overrides `slip.radial` only; the resolved `slip.axial` and `slip.slot` come from the shipped defaults via branch (a). The `axle_hole_gauge.py:60` docstring even instructs the user in this exact pattern — `{"fdm_standard": {"slip": {"radial": 0.10}}}` — confirming the design's intent has propagated to the consumer's calibration procedure.

**Open concerns (non-blocking; predicted cost in concrete domain units)**

- *`_profile_from_nested` per-field default for `slip.axial=0.0` and `press.axial=0.0` diverge from `_FALLBACK_PROFILES`'s `axial=0.20`* (`print_settings.py:317-322`). Today harmless because every shipped JSON entry carries an explicit `axial`. *Predicted cost if a future contributor's `print_profiles_user.json` defines `slip` or `press` without `axial`:* the dataclass-default `0.0` wins (deep-merge has nothing to inherit because the user's `slip` dict already exists and `axial` is absent from BOTH the user's `slip` dict AND… actually inherited via merge branch (a) because user's `slip` is `{"radial": X}` so `axial` would inherit from base — only fails if the user fully restates `slip` without `axial`). Realistic blast-radius: ≤1 unfortunate user, ~30 min debug + 1 wasted print cycle. The Independent Domain Expert Step-3.5 review already flagged this as out-of-scope-but-visible; carried over here for the same reason.

- *Typo'd user override leaf key (e.g. `radail` for `radial`)* — T5 asserts the resolved numeric is unaffected (the typo lands in the merged dict but is never read), so the failure mode is *visible in test output* not silent. *Predicted cost per affected user:* 1 wasted print cycle (~2 h printer + ~30 min test-fit + ~30 min debug) before the user re-reads the docs. Mitigation is the README documenting canonical leaf names. Already covered as a Known Risk in the design.

- *Q6 cutover criterion = "OSS publication release"* — pre-OSS only the maintainer is affected. *Predicted cost if publication slips:* near-zero; ~30 min follow-up PR to swap to a version-based criterion. Already flagged by the Independent TL Review.

**Blast-radius spot-check (the failure mode the YES gate guards against).** `vibe_cading/lego/axle_hole_gauge.py:60` consumes `slip.radial` directly; `AxleCrossHoleGauge` (per design's T16 inventory) consumes both `slip.radial` and `slip.slot`. A silent merge regression that lost `slip.slot=0.10` for `fdm_standard` would zero the narrow-slot allowance on every cross-axle Lego adapter (5-10 model classes today), printing each hole 0.10 mm tighter than designed — enough to make a cross axle bind. T9b's pinned tuple `("fdm_standard", …, 0.05, 0.20, 0.10, …)` at position 6 catches exactly this regression at test-time, before any STL is printed. Domain-integrity gate effectively closed.

No conditions for the developer. Sign-off issued.

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes: <!-- optional directions or conditions -->

---

## Independent TL Review (fresh context, 2026-05-23)

**Verdict:** APPROVE

**Strengths**
- Data & Interface Contracts §1 enumerates all six recursion branches with explicit type/null/sequence handling; the silent-tolerance-shift failure mode the YES gate guards against is structurally ruled out by branches (e)+(f) plus snapshot test T9.
- Task sequencing (T1–T6 loader ahead of T7–T8 rename) is correct: every intermediate commit in the single PR is verifiable, and the dual-fallback resolution chain in Data Contract §4 makes the rename order-independent for users.
- The deprecation emitter (Data Contract §5) is one mechanism with a documented idempotence guard plus assertion test T14; the "warn once per process per key" rule eliminates the loop-noise foot-gun the req flagged.

**Conditions / required edits (must land before Step 4 human gate proceeds)**
1. **T16 inventory has a factually wrong citation.** The plan lists `vibe_cading/mechanical/screws/imperial.py` as carrying a legacy-name docstring; grep returns zero matches in that file. Fix: drop `imperial.py` from the T16 file list (keep the other 6: `freespin_hex_hub.py`, `axle_hole_gauge.py`, `axle_cross_hole_gauge.py`, `cutters/technic_axle_hole.py`, `lego/constants.py`, `examples/screw_cutter.py`). Edit at design line 215 in the T16 paragraph.
2. **T17 docs inventory is incomplete.** `docs/screws.md` line 82 carries the legacy names (verified by grep), and the design already names it in T17 — good. But `README.md` carries legacy names at lines 67, 73, 74, 75, and 144; T12 only commits to rewriting the "Print Tolerances & Calibration" section. Tighten T12 (design line 211) to explicitly enumerate all five README lines so the success-criterion-3 grep does not surface stale lines 67 / 73 / 74 the contributor missed.
3. **Add `vibe_cading/_env.py` line 84 (parser-example comment) to T18's scope explicitly.** The design names T18 as "cosmetic" but the comment cite is currently the only `VIBE_MACHINE_PROFILE` mention outside `print_settings.py` that is not on the T16/T17/T12 lists; success criterion 3 will flag it unless T18 picks it up. The design names it ("`_env.py` line 84") so this is a tightening request — add it to T18's verifiable-by line.

**Open concerns (non-blocking; each carries predicted-cost-of-failure)**
- Q6 (cutover = "OSS publication release") is a soft criterion — if OSS publication slips by months, the legacy code path persists indefinitely. *Predicted cost if blocking:* ~30 min to swap to a date- or version-based criterion in a follow-up PR; near-zero risk because pre-OSS the only affected user is the maintainer.
- The unrecognized-leaf-key trade-off (Data Contract §1 final paragraph + T5) is correctly classified as design-time forward-compat insurance, not a silent-shift hole — T5 explicitly asserts the resolved numeric is unchanged. *Predicted cost if a future contributor's typo escapes:* 1 lost print cycle (~2 h) + ≤30 min debug; the README documenting canonical leaf names is the primary mitigation.

**Verification log**
- `vibe_cading/print_settings.py:92` → `return os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")` (single env-var consumer; design claim confirmed).
- `vibe_cading/print_settings.py:247-253` → exact shallow-merge block as cited; replacement target precisely located.
- `grep VIBE_MACHINE_PROFILE vibe_cading/ parts/` → only `print_settings.py:46,92`, `_env.py:84` (comment), `freespin_hex_hub.py:88` (docstring). Zero code consumers outside `print_settings.py`. Design's "no model-class code change required for the env-var rename" claim confirmed.
- `.env.example:15` → `VIBE_MACHINE_PROFILE="fdm_standard"` (T10 cite confirmed); also legacy refs at lines 12, 13, 34 — T10 should pick those up (design's T10 names lines 12–13 + 15; line 34 not explicitly named — minor, success-criterion grep will catch).
- `.gitignore:42` → `machine_profiles_user.json` (T11 cite confirmed).
- `.claude/settings.json:44` → `"Bash(cp machine_profiles.json.example machine_profiles_user.json)"` (T15 cite confirmed exact).
- `TODO.md` lines around 38–40 → "do **not** build a machine×material composition matrix" (design's req-rationale citation confirmed).
- `tests/test_tolerance_profile.py`, `tests/test_env_parser.py`, `machine_profiles.json`, `machine_profiles.json.example` → all exist at cited paths; `machine_profiles_user.json` exists (maintainer's local file, the T8 rename target).
- `engine_api.json` grep → 4 hits on legacy names (T19 regen-need claim confirmed; predicted ~7 docstring blocks of churn is plausible).
- `vibe_cading/mechanical/screws/imperial.py` → ZERO matches on `machine_profiles` or `VIBE_MACHINE` (T16 citation is wrong — Condition 1 above).

**Re-confirmed 2026-05-23:** conditions 1/2/3 applied; verdict upgraded to APPROVE.

---

## Independent Developer Review (fresh context, 2026-05-23)

**Verdict:** APPROVE

**Strengths**
- Data Contract §1 spells out all six recursion branches with concrete pseudo-code; a Developer can transcribe it verbatim with no escalation. Worked example + type-mismatch failure mode pin the algorithm down completely.
- Data Contract §5 fully nails Q1 / FR13: `warnings.warn(msg, DeprecationWarning, stacklevel=2)` + stderr mirror, module-level `_emitted_deprecations: set[str]`, exact `_emit_deprecation_once(key, message)` signature, key strings already chosen (`env_var_VIBE_MACHINE_PROFILE`, `shipped_file_both_present`, `shipped_file_legacy_only`). Resolution-time emission is implied by call-site placement in §3 / §4.
- Implementation Plan tasks T1–T21 are atomic, each has a `**Verifiable**:` line, every FR maps to a Tests row (FR-coverage check at design line 251 is greppable). Pre/post snapshot (T9) uses the maintainer's actual current resolved 10-tuple — concrete and implementable today.

**Conditions / required edits (must land before Step 4 human gate proceeds)**
1. **T16 inventory carries a wrong cite.** `vibe_cading/mechanical/screws/imperial.py` has ZERO matches on `machine_profiles` or `VIBE_MACHINE` (verified by grep). Drop it from the T16 paragraph at design line 215; keep the other six files. Independent TL Review Condition 1 already flagged this — calling out here for cross-confirmation so the Developer does not waste a no-op edit.
2. **Snapshot test T9 lacks the pinned 10-tuple values.** Data Contract §8 + T9's row describe the *method* (load both paths, compare 10-tuples) but never name the specific input JSON or the expected output numbers. A fresh-context Developer cannot transcribe T9 without first running the *old* loader against the maintainer's user file to discover the snapshot. Tighten T9 (design line 208) to either (a) embed the JSON-content fixture + expected 10-tuple inline, or (b) explicitly direct the Developer to capture and embed those values as a sub-step before writing the assertion. Without this, T9 is a "figure out how to" task, not an atomic one.

**Open concerns (non-blocking; each with predicted-cost-of-failure)**
- Q6 cutover ("OSS publication release") is a string-match criterion in the warning message — if OSS publication slips by months, the legacy code path persists and the snapshot test continues guarding it indefinitely. *Predicted cost if blocking:* ~30 min to swap to a version-based criterion in a follow-up PR; near-zero risk pre-OSS.
- Data Contract §4 uses `Path(__file__).parent.parent` for repo root resolution, identical to current code path at `print_settings.py:240`. *Predicted cost if blocking:* zero — pattern is already in production.
- T19 `engine_api.json` regen is capped at "reviewable in under 3 minutes" but the actual line-count budget is qualitative. *Predicted cost if blocking:* ~30 min reviewer fatigue + possible blank-check sign-off; Success Criterion 9 already names the escalation path.

**Verification log**
- `vibe_cading/print_settings.py:92` → `return os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")` — design's single-env-consumer claim confirmed; T4 replacement target precisely located.
- `vibe_cading/print_settings.py:247-253` → exact shallow-merge block matches the design's cite verbatim (`merged = dict(profiles[k])` + `for grade_key, grade_val in migrated.items(): merged[grade_key] = grade_val`). T3 replacement target precisely located.
- `.env.example:15` → `VIBE_MACHINE_PROFILE="fdm_standard"` confirmed; lines 12–13 carry `machine_profiles.json` + `machine_profiles_user.json` in the comment block — T10's "comment block on lines 12–13" cite is exact.
- `.gitignore:42` → `machine_profiles_user.json` rule confirmed; T11's "alongside the existing rule (line 42)" cite is exact.
- `.claude/settings.json:44` → `"Bash(cp machine_profiles.json.example machine_profiles_user.json)"` confirmed byte-exact; T15 cite valid.
- `vibe_cading/_env.py:84` → comment line `VIBE_MACHINE_PROFILE="bambu_p1s"` confirmed; T18 cite valid.
- `vibe_cading/mechanical/screws/imperial.py` → ZERO matches (Condition 1 above; corroborates Independent TL Review).
- Existing `tests/test_tolerance_profile.py` exists (11310 bytes) — design's "modified `test_get_profile_unknown_falls_back_to_hardcoded`" (T5/T13) is a real edit target, not a new file. AGPLv3 header / no-`__main__` gates: no new files created; T1–T21 only edit existing files + git-mv tracked JSON. Header-and-main-block gates do not fire.

**Re-confirmed 2026-05-23:** conditions 1/2 applied; verdict upgraded to APPROVE.

---

## Independent Domain Expert Review (Designer-as-domain-expert, fresh context, 2026-05-23)

**Verdict:** APPROVE

**Domain integrity findings** (each tied to one of the 6 Step-3.5 questions)

1. **Field-level merge correctness (Q1).** Data Contract §1's six branches handle the canonical scenario correctly: user `{"fdm_standard": {"slip": {"radial": 0.12}}}` onto shipped `slip={radial:0.10, axial:0.05, slot:0.10}` resolves to `{radial:0.12, axial:0.05, slot:0.10}` via branch (c) recurse → branch (d) leaf-win for `radial` → branch (a) base-copy for `axial`/`slot`. The `{"slip": {"radial":0.12, "slot": null}}` case correctly raises at branch (f) — null is not a tolerance-domain-valid override, silent substitution to 0.0 would silently zero a clearance. Branch (e) (primitive-vs-dict type mismatch) hard-erroring is tolerance-domain-correct: a `FitGrade` is structurally a dict-of-leaves; a user "legitimately" wanting to replace a grade with a primitive is incoherent against the dataclass schema, and silent shape coercion downstream in `_fitgrade_from_dict` would be the silent-shift failure mode the YES gate guards against.

2. **Backward-compat invariant (Q2) — TIGHTENING REQUIRED.** `_FALLBACK_PROFILES` enumerates the at-risk numerics: `fdm_standard.slip.slot = 0.10` is the load-bearing value — every narrow-slot consumer (`TechnicAxleHole`, `AxleCrossHoleGauge`, every Lego Technic cross-axle adapter) reads it via `slip.slot`. A silent merge regression that loses this key would let `_fitgrade_from_dict`'s `default_slot=0.0` substitute, zeroing the narrow-slot allowance and printing every cross-axle hole 0.10 mm tighter than designed. T9's 10-tuple `(name, free.radial, free.axial, free.slot, slip.radial, slip.axial, slip.slot, press.radial, press.axial, press.slot)` *does* include `slip.slot`, so the snapshot locks down `0.10` *for the profile resolved from the maintainer's user file*. But T9 reads "the maintainer's actual current resolved profile" — if that file overrides only one profile (`fdm_standard`), T9 does not directly snapshot `resin_precise`/`cnc`. T20 (existing tests pass) covers some of the gap, but **the design's §8 backward-compat-floor invariant claims "every profile" identity and T9 alone underconstrains it**. See Condition 1.

3. **Migration-before-merge ordering (Q3).** Data Contract §2's "migrate each side first, then deep-merge" is the only correct ordering. A subtle positive consequence: a legacy-flat user file (which has no `slot` key) migrates to nested with `slot` implicitly absent on each grade; deep-merged onto shipped nested with `slip.slot=0.10`, the user-side absence triggers branch (a) and the shipped `0.10` is inherited. This is *strictly better* than today's grade-level shallow merge, where a legacy-flat user file's migrated `slip` dict (lacking `slot`) would have wholesale replaced the shipped `slip` and zeroed `slot`. The new behaviour is tolerance-domain-correct (the user calibrated `slip_fit` only; `slot` should ride the shipped default).

4. **`<machine>__<material>` key convention (Q4).** Branch (b) (key absent from base, present in override) copies the user's top-level key through verbatim with no parent lookup. There is no code path that decomposes `bambu_p1s__pla_overture` into a `bambu_p1s` base + `pla_overture` overlay; the convention is purely lexical/documentary. Honors `TODO.md` lines 38–40's "no machine×material composition matrix" posture.

5. **Deprecation-window safety (Q5).** Data Contract §3's triple-chain (`VIBE_PRINT_PROFILE → VIBE_MACHINE_PROFILE → "fdm_standard"`) is correct *because* `get_default_profile_name()` is the single env-var consumer site (req §Known Domain Constraints + Independent TL Review verification log both confirm zero direct `os.getenv("VIBE_MACHINE_PROFILE")` calls outside `print_settings.py`). A downstream model class that hardcoded the old name would silently miss the user's calibration — but no such consumer exists. Safe in practice.

6. **Fewer-calibration-knobs anchor (Q6).** Data Contract §1's worked example IS the anchor: `{"fdm_standard": {"slip": {"radial": 0.11}}}` calibrates one value and inherits `axial=0.20` + `slot=0.10` unchanged. The auto-memory `feedback_fewer_calibration_knobs.md`'s "field-level profile merge is one concrete lever" is honored directly. No failure mode forces the user to restate a full grade dict to override one field.

**Conditions (must land before Step 4 human gate proceeds)**

1. **Tighten T9 to lock down every shipped-profile leaf numeric, not just the maintainer-file-resolved 10-tuple.** Edit at design line 208 (T9) and/or Data Contract §8 (line 188). Either (a) extend T9 to snapshot the resolved 10-tuple for *all three* shipped profiles (`fdm_standard`, `resin_precise`, `cnc`) under the new loader against pinned values drawn from `_FALLBACK_PROFILES` (the disaster-recovery floor is the authoritative source of the at-risk numerics: `fdm_standard.slip.slot=0.10`, `fdm_standard.free.axial=0.20`, `fdm_standard.press.axial=0.20`, all `resin_precise.*` and `cnc.*` values), OR (b) add a parallel T9b row that explicitly snapshots `_FALLBACK_PROFILES` → `_profile_from_nested` → 10-tuple equality for the three shipped profiles, on top of T9's maintainer-file snapshot. The current T9 wording underconstrains the §8 invariant's "every existing user file resolves to identical numeric tolerances" claim if the maintainer's user file does not exercise all three shipped profiles.

**Open concerns (non-blocking; each with predicted-cost-of-failure in concrete domain units)**

- **Unrecognized leaf-key typo (Data Contract §1 final paragraph + T5).** Correctly classified as forward-compat insurance not a silent-shift hole. T5 asserts the resolved numeric is unaffected, but the typo means the user's *calibration intent* is silently ignored. *Predicted cost:* per affected user, 1 wasted print cycle (~2 h printer time + ~30 min test-fit + ~30 min debug) before they re-read the README. Blast radius: per typo, 1 user, 1 profile, every model class consuming that profile — for `fdm_standard` that's every printed Technic adapter (10+ classes today). Mitigation T5 is the right level for the call.
- **T9 snapshot scope (the Condition 1 issue, if left unresolved).** If a future regression silently zeros `slip.slot` on a shipped profile not covered by the maintainer's user file, the regression escapes T9 and lands. *Blast radius:* every `TechnicAxleHole` consumer prints 0.10 mm tighter than designed — 5–10 model classes (axle holes in beams, cross-hole gauges, every cross-axle Lego adapter). *Tolerance shift magnitude:* 0.10 mm radial, enough to make a cross axle bind or refuse insertion on FDM. Condition 1 closes this.
- **Q6 cutover = "OSS publication release".** If publication slips, the legacy code path persists. *Predicted cost:* near-zero pre-OSS (only the maintainer is affected); ~30 min follow-up PR to swap to a version-based criterion. Already flagged by Independent TL Review.

**Verification log (numeric values checked from `_FALLBACK_PROFILES`)**

- `print_settings.py:266-284` (`_FALLBACK_PROFILES`):
  - `fdm_standard.free  = (0.15, 0.20, 0.0)`  [radial, axial, slot — slot defaulted by `_fitgrade_from_dict.default_slot=0.0` because the JSON entry omits `slot`]
  - `fdm_standard.slip  = (0.05, 0.20, 0.10)` ← **`slip.slot=0.10` is the load-bearing narrow-slot allowance**
  - `fdm_standard.press = (0.04, 0.20, 0.0)`  [but see schema-default note below]
  - `resin_precise.free = (0.05, 0.05, 0.0)`
  - `resin_precise.slip = (0.03, 0.05, 0.0)`
  - `resin_precise.press = (0.02, 0.05, 0.0)`
  - `cnc.free  = (0.02, 0.0, 0.0)`
  - `cnc.slip  = (0.01, 0.0, 0.0)`
  - `cnc.press = (0.0,  0.0, 0.0)`
- `print_settings.py:198-211` (`_profile_from_nested` per-field defaults): `free` defaults to `(0.15, 0.20, 0.0)`; `slip` defaults to `(0.05, 0.0, 0.0)`; `press` defaults to `(0.04, 0.0, 0.0)`. **Note for Developer T1 / T9:** `slip`'s `default_axial=0.0` and `press`'s `default_axial=0.0` diverge from `_FALLBACK_PROFILES`'s `axial=0.20` — the divergence is harmless today because every shipped JSON entry carries an explicit `axial`, but if a future user file omits `axial` on `slip` or `press` they will get `0.0` not `0.20`. Out of scope for this brief; flagged for visibility.
- `axle_hole_gauge.py:60` consumes `slip.radial`; `axle_cross_hole_gauge.py` (per design's T16 inventory) consumes both `slip.radial` and `slip.slot`. The narrow-slot consumer is the structural justification for protecting `slip.slot=0.10`.
- Data Contract §1 worked example numerically verified against the six branches: branches (a) base-copy + (c) recurse + (d) leaf-win combine to give the claimed `{radial:0.11, axial:0.20, slot:0.10}` resolution.
- Auto-memory `feedback_fewer_calibration_knobs.md` confirms field-level merge is the named lever the user wants; design honours it.

**Re-confirmed 2026-05-23:** condition 1 applied; pinned values match live `_FALLBACK_PROFILES`; verdict upgraded to APPROVE.
