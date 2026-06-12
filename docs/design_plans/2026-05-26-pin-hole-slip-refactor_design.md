# Design: Re-anchor `TechnicPinHole` to `profile.slip.radial`
<!-- Filename: 2026-05-26-pin-hole-slip-refactor_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-05-26-pin-hole-slip-refactor_req.md`
- **Requester role**: @designer (on behalf of human @admin)
- **Date**: 2026-05-26
- **Dialog rounds**: 4

---

## Objective

Make `TechnicPinHole` consume the calibrated `profile.<fit>.radial` knob (default `fit="slip"`) instead of the hardcoded `PIN_HOLE_PRINTED` constant — mirroring `TechnicAxleHole`'s profile-aware shape — so a single `slip.radial` calibration covers every Lego Technic round-socket consumer in the library, and deprecate `PIN_HOLE_PRINTED` for one release window.

## Architecture / Approach

### Approach chosen

This is a **refactor + deprecation alias** inside two existing modules; no new module is introduced.

1. **`TechnicPinHole.__init__` gains `profile` and `fit` kwargs** that mirror `TechnicAxleHole` exactly (same names, same defaults, same resolver). `profile` is resolved via the canonical `_resolve_profile(profile, fallback=get_profile())` pattern from `mechanical/holes.py:41` — except we use `get_profile()` lazy lookup (`profile or get_profile()`) at construction time, matching `TechnicAxleHole`'s pattern (it does not delegate to `_resolve_profile`; we follow the spiritual analog faithfully).
2. **The bore-diameter formula** becomes:

   ```python
   bore_diameter = (
       diameter
       if diameter is not None
       else PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial
   )
   ```

   I.e. an explicit `diameter=` kwarg signals "I'm passing the exact bore diameter I want — do not widen further"; omitting it (the new default) routes through the profile.
3. **The counterbore stays at its nominal `6.2 mm` diameter** — see _Counterbore-clearance round_ below. The counterbore is sized for a fixed real-world LEGO pin-flange dimension, not a printed slip interface.
4. **`PIN_HOLE_PRINTED` is moved behind a module-level `__getattr__` (PEP 562)** in `vibe_cading/lego/constants.py`. The legacy `os.getenv("PIN_HOLE_PRINTED", "4.85")` resolution runs on first attribute access; a `_emit_deprecation_once` warning fires at that moment with the key `"const_PIN_HOLE_PRINTED"`. The constant remains importable for one release window (planned removal at OSS publication, matching the `VIBE_MACHINE_PROFILE` precedent in `print_settings.py:248`).
5. **`TechnicPinHole.standard(depth, *, profile=None, fit="slip")` forwards both kwargs** through to the constructor. The classmethod surface stays minimal — no new `from_profile()` companion.
6. **Documentation deltas land in three docs** (`docs/print-tolerances.md` §1 + §2.1, `docs/lego-technic.md` lines 143 + 156-160, `.env.example` line 24) plus a comment refresh on `vibe_cading/lego/constants.py:41`.

### Visual contract (CAD tasks)

N/A — internal API refactor. The cutter's external geometry changes by `±0.06 mm` on the bore diameter under `fdm_standard` (4.85 → 4.90 mm) which is sub-visible at preview-SVG resolution. No new visible feature, no axis change, no hole-pattern change. Visual contract carve-out applies (vibe/INSTRUCTIONS.md → "Optional for: refactors, internal API changes").

### Alternatives rejected

- **Option A — push the legacy fallback into `TechnicPinHole` itself.** Have the cutter read `PIN_HOLE_PRINTED` when `profile=None`, with the deprecation firing from the cutter. Rejected: this re-routes the legacy constant through the cutter forever and defeats the goal of removing the constant. The cutter should know only about `PIN_HOLE_DIAMETER` + profile.
- **Option B — make `profile` always widen, even when `diameter=` is explicit.** Rejected: this silently re-widens every `tolerance_gauge.py` column by `2 * slip.radial`, defeating the gauge's purpose of *visualising the radial-allowance landscape directly*. The explicit-diameter override is load-bearing for gauge correctness. (See Round 1 in the Dialog Log for the full pressure-test.)
- **Option C — module-import-time deprecation warning.** Rejected: would fire on every import of `vibe_cading.lego.constants` (which is transitively imported by virtually every model), spamming stderr for users who have already migrated. `__getattr__`-on-module is quieter and fires only on *active* reads of the deprecated name. (See Round 3 in the Dialog Log.)
- **Option D — add a new `slip.pin_radial` knob.** Rejected per FR Out-of-Scope and Q6: empirically the round-feature shrink that drives axle slip and pin slip is the same physical mode at the same `~5 mm` scale; YAGNI until a user reports divergence.

## Data & Interface Contracts

### `TechnicPinHole.__init__` — new signature (verbatim)

```python
def __init__(
    self,
    depth: float,
    diameter: float | None = None,                 # explicit override; None → profile path
    counterbore_depth: float = DEFAULT_CB_DEPTH,
    counterbore_diameter: float = DEFAULT_CB_DIAMETER,
    fit: str = "slip",                             # FitGrade selector: "slip" | "free" | "press"
    profile: ToleranceProfile | None = None,       # None → lazy get_profile()
):
```

**Removed default:** the constructor signature no longer carries the class-level `diameter: float = DEFAULT_DIAMETER` default. `DEFAULT_DIAMETER` remains as a class attribute (still equals `PIN_HOLE_DIAMETER`) for documentation and for callers that compute their own bore explicitly, but the constructor default switches to `None` so the profile path is reachable without forcing every caller to pass `diameter=None`.

### `TechnicPinHole.standard` — new signature (verbatim)

```python
@classmethod
def standard(
    cls,
    depth: float,
    *,
    fit: str = "slip",
    profile: ToleranceProfile | None = None,
) -> "TechnicPinHole":
    return cls(
        depth=depth,
        diameter=None,                             # route through profile
        counterbore_depth=cls.DEFAULT_CB_DEPTH,
        counterbore_diameter=cls.DEFAULT_CB_DIAMETER,
        fit=fit,
        profile=profile,
    )
```

### Bore-diameter resolution (the single load-bearing formula)

```python
profile = profile or get_profile()
grade = getattr(profile, fit)                      # FitGrade for "slip" / "free" / "press"
if diameter is not None:
    bore_diameter = diameter                       # explicit override wins as-is
else:
    bore_diameter = PIN_HOLE_DIAMETER + 2 * grade.radial
self.diameter = bore_diameter                      # stored attribute = effective printed bore
```

**Precedence invariant (Q1 resolution):**
- `diameter=X` passed explicitly → `self.diameter == X`, profile is *not* applied on top.
- `diameter=None` (default) → `self.diameter == PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial`.
- No `UserWarning` when both are passed: the precedence rule is documented in the docstring and is the same precedence `_resolve_profile`-pattern hole classes use (explicit caller-supplied value wins). A warning would be noise for the legitimate gauge-author use case where both are intentionally supplied.

### Default `fit` grade rationale

`fit="slip"` is the default because the pin-in-printed-socket interface has **slip semantics** per `docs/print-tolerances.md` §1: snug, slides with mild friction, the hole walls are the working contact surface. This matches `TechnicAxleHole.fit="slip"` default. The two round-envelope Lego Technic sockets in the library now share the same default fit and the same calibration knob.

### `PIN_HOLE_PRINTED` deprecation mechanics (Q2 resolution — module `__getattr__`)

The constant is removed from module-level binding and re-exposed via PEP 562 module `__getattr__`:

```python
# vibe_cading/lego/constants.py — append near the bottom:

def __getattr__(name: str) -> float:
    """PEP 562 module-level lazy attribute hook.

    Currently used to deprecate `PIN_HOLE_PRINTED` — readers get the
    legacy `os.getenv("PIN_HOLE_PRINTED", "4.85")` value plus a one-shot
    deprecation warning. The constant remains importable for one
    release window (planned removal at OSS publication).
    """
    if name == "PIN_HOLE_PRINTED":
        from vibe_cading.print_settings import _emit_deprecation_once
        _emit_deprecation_once(
            "const_PIN_HOLE_PRINTED",
            "vibe_cading.lego.constants.PIN_HOLE_PRINTED is deprecated; "
            "TechnicPinHole now consumes profile.slip.radial. To tune the "
            "printed pin-hole fit, calibrate slip.radial in "
            "print_profiles_user.json via `python3 tools/calibrate.py slip`. "
            "The legacy constant (and the PIN_HOLE_PRINTED .env override) "
            "will be removed at the OSS publication release.",
        )
        return float(os.getenv("PIN_HOLE_PRINTED", "4.85"))
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

Key properties:
- **Trigger:** fires on first **attribute read** (e.g. `from vibe_cading.lego.constants import PIN_HOLE_PRINTED` or `constants.PIN_HOLE_PRINTED`). Silent for the new `TechnicPinHole` (which no longer reads it) and silent for users who have already migrated.
- **Once-per-process:** the `_emit_deprecation_once` helper de-dupes by key. A subsequent `from X import PIN_HOLE_PRINTED` in the same process is silent.
- **`.env` override still works:** `PIN_HOLE_PRINTED="4.9"` in `.env` still seeds the `os.getenv` lookup, so backward-compat is preserved — the override path just no longer feeds into `TechnicPinHole`.
- **Stable key:** `"const_PIN_HOLE_PRINTED"` follows the project's existing `_emit_deprecation_once` key convention (compare `"env_var_VIBE_MACHINE_PROFILE"`).

### Cross-model propagation pre/post invariant

| Consumer family | Pre-refactor printed dimension | Post-refactor printed dimension | Delta on `fdm_standard` (`slip.radial=0.05`) |
|---|---|---|---|
| `TechnicPinHole` (default, `fit="slip"`, no explicit `diameter`) | `PIN_HOLE_PRINTED = 4.85 mm` (or env override) | `PIN_HOLE_DIAMETER + 2 * profile.slip.radial = 4.80 + 0.10 = 4.90 mm` | **+0.05 mm** (loosens by `2 × 0.05 − 0.05`) |
| `TechnicPinHole(diameter=X)` (gauge author) | `X` | `X` (unchanged — explicit-diameter precedence) | 0 mm |
| `TechnicAxleHole.TIP_TO_TIP` | `4.80 + 2 * slip.radial = 4.90 mm` | unchanged | 0 mm |
| Every other consumer (M3 holes, bearings, magnets, nuts, captive pockets, …) | per-class formula | unchanged | 0 mm |

**Invariant statement (contract):** *Exactly* the `TechnicPinHole`-default-path printed bore changes. Every non-pin-hole consumer's printed dimension is byte-identical before vs after. Every `TechnicPinHole` call site that passes `diameter=` explicitly (today: `tolerance_gauge.py:124` only) produces a byte-identical bore.

**On the calibrated user's printer (`slip.radial=0.11`):** new bore = `4.80 + 0.22 = 5.02 mm`, replacing the previous `4.85 mm` constant. This is the intended outcome — the user's calibrated knob now actually flows into the pin hole, which is the bug being fixed.

### Snapshot-test design (Q5 resolution)

We extend the test surface with **four new tests**, one per FR'd behaviour. The existing T9b 27-leaf-float snapshot in `tests/test_tolerance_profile.py` is *not* extended — T9b pins `_FALLBACK_PROFILES` field values, which this refactor does not touch (FR12).

**New test file:** `tests/test_technic_pin_hole_profile.py` (new module, mirrors `tests/test_protocols.py` structure).

| Test name | Pinned matrix |
|---|---|
| `test_pin_hole_consumes_slip_radial` | For each shipped profile in `("fdm_standard", "resin_precise", "cnc")`: assert `TechnicPinHole(depth=8.0, profile=name).diameter == PIN_HOLE_DIAMETER + 2 * get_profile(name).slip.radial`. |
| `test_pin_hole_fit_grade_selector` | For each fit in `("free", "slip", "press")` on `fdm_standard`: assert `TechnicPinHole(depth=8.0, fit=fit).diameter == PIN_HOLE_DIAMETER + 2 * get_profile("fdm_standard").<fit>.radial`. Confirms the `fit=` selector flows. |
| `test_pin_hole_explicit_diameter_bypasses_profile` | Assert `TechnicPinHole(depth=8.0, diameter=5.0, profile="fdm_standard").diameter == 5.0`. Confirms explicit-diameter precedence under Q1. |
| `test_pin_hole_printed_deprecation_warning` | Using `pytest.warns(DeprecationWarning, match="PIN_HOLE_PRINTED is deprecated")`: assert reading `vibe_cading.lego.constants.PIN_HOLE_PRINTED` emits exactly one warning per process. Confirms PEP 562 hook fires. |
| `test_pin_hole_standard_forwards_profile` | Assert `TechnicPinHole.standard(depth=8.0, profile="resin_precise").diameter == PIN_HOLE_DIAMETER + 2 * get_profile("resin_precise").slip.radial`. Confirms the classmethod surface forwards kwargs. |

**Pinned diameter matrix (the load-bearing snapshot):**

| Profile | `slip.radial` | Resolved `TechnicPinHole.standard(8.0).diameter` |
|---|---|---|
| `fdm_standard` | 0.05 | **4.90 mm** |
| `resin_precise` | 0.03 | **4.86 mm** |
| `cnc` | 0.01 | **4.82 mm** |

A regression in any of the 27 leaf-floats fails T9b loudly; a regression in any of the three resolved pin-hole bores above fails `test_pin_hole_consumes_slip_radial` loudly. The two snapshot surfaces are independent on purpose — T9b is the source-of-truth profile data; the new test is the source-of-truth consumer plumbing.

### `tolerance_gauge.py` pin-hole row decision (Q3 resolution — option (a), leave as-is)

`vibe_cading/mechanical/tolerance_gauge.py:124` constructs each pin-hole column as:

```python
pin_dia = PIN_HOLE_DIAMETER + 2 * offset
pin_cutter = TechnicPinHole(depth=self.base_thickness, diameter=pin_dia).solid
```

Post-refactor this code path is **byte-identical** in behaviour (the explicit `diameter=pin_dia` takes the explicit-override branch and no profile is applied). The gauge sweeps offsets as a visualisation of the radial-allowance landscape, which is now the *same* landscape `slip.radial` calibration walks. This is exactly the right semantic — the gauge documents the knob; it does not duplicate the calibration source.

**No code change required at the call site.** A one-line comment refresh added in T2c: clarify that the row sweeps the same physical landscape `TechnicPinHole` reads through `slip.radial`. Renaming the row label (option (b)) and removing the row (option (c)) are both deferred — neither earns the change cost.

## Implementation Plan

### Core refactor

- [x] **T1** — Edit `vibe_cading/lego/cutters/technic_pin_hole.py`:
  - Import `get_profile` alongside the existing `ToleranceProfile` import.
  - Change `__init__` signature to match the verbatim spec above (`diameter: float | None = None`, append `fit: str = "slip"`, append `profile: ToleranceProfile | None = None`).
  - Compute `bore_diameter` per the formula above; set `self.diameter = bore_diameter`.
  - Update the docstring to describe profile-awareness (mirror `TechnicAxleHole` docstring shape).
  - Update `.standard()` classmethod signature to `(cls, depth, *, fit="slip", profile=None)` and forward kwargs.
- [x] **T2a** — Verify the 4 production consumers continue to work without source changes (FR Non-Functional 1):
  - `vibe_cading/lego_adapters/servos/sg90/servo_mount.py:356` — `TechnicPinHole(depth=STUD_PITCH, counterbore_depth=0.0)` resolves `diameter=None` → profile path. Confirm.
  - `vibe_cading/lego_adapters/servos/sg90/servo_mount.py:412` — `TechnicPinHole.standard(depth=depth)` — confirm classmethod still works.
  - `vibe_cading/lego_adapters/servos/sg90/servo_mount_half.py:322`, `:372` — same shapes as above.
  - `vibe_cading/mechanical/tolerance_gauge.py:124` — `TechnicPinHole(depth=..., diameter=pin_dia)` — explicit `diameter=` keeps current behaviour.
  - `vibe_cading/lego/technic_beam.py:161`, `:180`, `:199` — accesses `TechnicPinHole.standard(...)` and class attributes `_ENTRY_OVERCUT`, `DEFAULT_CB_DIAMETER`. Confirm class attributes still exist post-refactor.
- [x] **T2b** — Add a `# Profile-awareness inherited from TechnicPinHole.__init__ default fit="slip"` comment to the `servo_mount.py:356`, `servo_mount_half.py:322`, and `technic_beam.py:162` call sites for contributor cold-start orientation. **No API change at any call site.**
- [x] **T2c** — Add a comment to `tolerance_gauge.py:122-124` clarifying that this row exercises the same physical landscape `TechnicPinHole` reads through `slip.radial`.

### Deprecation infrastructure

- [x] **T3** — Edit `vibe_cading/lego/constants.py`:
  - Remove the module-level binding `PIN_HOLE_PRINTED: float = float(os.getenv(...))` at line 41.
  - Append a module-level `__getattr__(name)` function per the verbatim spec above; route `PIN_HOLE_PRINTED` through `_emit_deprecation_once` (imported lazily inside the function to avoid an import cycle if `print_settings` later imports `constants`).
  - Update the surrounding comment block on lines 39-41 to document the deprecation.
  - _Implementation note: inside the `__getattr__` body, add a one-line comment flagging that `from vibe_cading.lego.constants import *` would silently skip `PIN_HOLE_PRINTED` because PEP 562 `__getattr__` is invoked only on direct attribute lookup, not on the wildcard-import path. Verified zero wildcard importers of `lego.constants` exist in the repo as of 2026-05-26 — the note is for future contributors, not a behaviour change. The verbatim `__getattr__` block in §"`PIN_HOLE_PRINTED` deprecation mechanics" should be extended in-place with this comment when implemented._
- [x] **T4** — Edit `.env.example` line 24:
  - Annotate the `PIN_HOLE_PRINTED="4.85"` line with a deprecation comment mirroring the `VIBE_MACHINE_PROFILE` prose at line 15.
  - Name `slip.radial` calibration in `print_profiles_user.json` as the replacement; reference `tools/calibrate.py slip`.

### Tests

- [x] **T5** — Create `tests/test_technic_pin_hole_profile.py` with the five tests in the snapshot-test design table above. Each test imports `TechnicPinHole`, `get_profile`, and `PIN_HOLE_DIAMETER`. The deprecation test additionally uses `pytest.warns(DeprecationWarning)` plus a `monkeypatch` to reset the once-per-process guard (clear `_emitted_warnings` before the test).
  - _Implementation note: `_emitted_warnings` is a module-global in `vibe_cading.print_settings` (mutated by `_emit_deprecation_once`). Monkeypatch via `monkeypatch.setattr(vibe_cading.print_settings, "_emitted_warnings", set())` (or `.clear()` it in a fixture) so the once-per-process guard resets deterministically per test invocation. Patching a local symbol or a `lego.constants`-level reference will not reset the guard and will produce flaky behaviour where the second test run sees no warning._
- [x] **T6** — Run the existing `tests/test_protocols.py` row for `TechnicPinHole` (`tests/test_protocols.py:118`) — verify the no-args `to_cutter()` shape still resolves under the new signature (it should: `depth=7.2` plus all-defaults including `diameter=None` and `fit="slip"`).
- [x] **T7** — Confirm `tests/test_tolerance_profile.py` T9b passes unchanged (no `FitGrade` or `_FALLBACK_PROFILES` field touched).

### Documentation

- [x] **T8** — Edit `docs/print-tolerances.md`:
  - **§1 worked-example table (lines 28-32):** add a new row OR extend the `slip` row's "Consumer call site" cell. New row option:
    ```
    | `slip`  | TechnicPinHole.standard (default) | `bore = PIN_HOLE_DIAMETER + 2 * profile.slip.radial` | D = 4.8 mm | 4.80 + 2·0.05 = 4.90 mm |
    ```
  - **§2.1 `radial` consumer table (lines 52-73):** add a new row after the existing `TechnicAxleHole` row:
    ```
    | `TechnicPinHole.standard` (round pin socket; chooses grade by `fit=` kwarg) | `slip`* | [`technic_pin_hole.py:<line>`](../vibe_cading/lego/cutters/technic_pin_hole.py#L<line>) |
    ```
    Update the `*` footnote (currently at line 75) to read: "*\* `TechnicAxleHole` and `TechnicPinHole` both default to `slip` but accept `fit="free"` / `fit="press"`; the grade selection happens at construction.*"
- [x] **T9** — Edit `docs/lego-technic.md`:
  - **Line 143 ("Printed hole clearance" row):** replace `+0.1 mm / Use 4.9 mm holes for a snug printed fit` with a row describing the new profile-driven mechanism. Suggested text: `| Printed hole clearance     | `2 × slip.radial` mm  | Now profile-driven via `TechnicPinHole(fit="slip")`; calibrate `slip.radial` in `print_profiles_user.json` per `docs/print-tolerances.md` §4 |`.
  - **Lines 156-160 (TechnicPinHole counterbore narrative):** add a one-sentence cross-reference noting that the *bore* (not the counterbore) is now `slip.radial`-driven; counterbore dimensions remain hardcoded real-liftarm-spec.
- [x] **T10** — Update the surrounding comment on `vibe_cading/lego/constants.py` line 39 ("Technic Pin Holes" block header) to describe the deprecation status of `PIN_HOLE_PRINTED` and direct readers to `TechnicPinHole(fit="slip")` for the current path.

### Validation

- [x] **T11** — Run `python3 -m pytest tests/test_technic_pin_hole_profile.py tests/test_tolerance_profile.py tests/test_protocols.py tests/test_env_parser.py -v` and confirm zero failures.
- [x] **T12** — Run `python3 tools/preview.py vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole --views iso_ne` to confirm the cutter still builds geometrically. Visual delta is expected to be sub-visible (`±0.05 mm` on a 4.85 mm bore).
- [x] **T13** — Run `python3 build.py` and confirm every existing model still builds without error (regression gate for the 4 production consumers).

## Tests

| # | Test description | Expected assertion | File / location |
|---|---|---|---|
| 1 | FR1, FR3: `TechnicPinHole(depth, profile=name)` consumes `profile.slip.radial` for each shipped profile | `cutter.diameter == PIN_HOLE_DIAMETER + 2 * profile.slip.radial` for `fdm_standard` (4.90), `resin_precise` (4.86), `cnc` (4.82) | `tests/test_technic_pin_hole_profile.py::test_pin_hole_consumes_slip_radial` |
| 2 | FR2: `fit=` kwarg selects the FitGrade | `TechnicPinHole(depth=8.0, fit=fit).diameter == PIN_HOLE_DIAMETER + 2 * get_profile().<fit>.radial` for each of `("free","slip","press")` | `tests/test_technic_pin_hole_profile.py::test_pin_hole_fit_grade_selector` |
| 3 | FR6, Q1: explicit `diameter=` wins; profile not applied on top | `TechnicPinHole(depth=8.0, diameter=5.0, profile="fdm_standard").diameter == 5.0` | `tests/test_technic_pin_hole_profile.py::test_pin_hole_explicit_diameter_bypasses_profile` |
| 4 | FR7: reading `PIN_HOLE_PRINTED` emits exactly one `DeprecationWarning` | `pytest.warns(DeprecationWarning, match="PIN_HOLE_PRINTED is deprecated")` fires once; second read in same process is silent | `tests/test_technic_pin_hole_profile.py::test_pin_hole_printed_deprecation_warning` |
| 5 | FR5: `TechnicPinHole.standard(depth, profile=...)` forwards the profile kwarg | `TechnicPinHole.standard(depth=8.0, profile="resin_precise").diameter == 4.86` | `tests/test_technic_pin_hole_profile.py::test_pin_hole_standard_forwards_profile` |
| 6 | FR12: 27-leaf-float T9b snapshot remains bit-identical | existing `test_shipped_profiles_pinned_tuples` passes unchanged | `tests/test_tolerance_profile.py::test_shipped_profiles_pinned_tuples` |
| 7 | FR Non-Functional 1: `TechnicPinHole` no-args-after-`depth` protocol shape still works | existing `test_protocols.py` row for `TechnicPinHole` still passes (`depth=7.2` only; everything else default) | `tests/test_protocols.py:118` |
| 8 | FR Non-Functional (env compat): `.env` carrying `PIN_HOLE_PRINTED="X.YZ"` loads cleanly | existing `tests/test_env_parser.py` still passes (no change to parser behaviour) | `tests/test_env_parser.py` |
| 9 | FR13: every non-pin consumer's bore is unchanged | `python3 build.py` produces byte-identical STEP files for any non-pin-bearing model class; the volume of pin-bearing models shifts by the documented delta only | `python3 build.py` regression gate, T13 |
| 10 | FR4: `PIN_HOLE_DIAMETER` value unchanged | direct constant read: `from vibe_cading.lego.constants import PIN_HOLE_DIAMETER; assert PIN_HOLE_DIAMETER == 4.8` | covered transitively by test 1 (formula reads `PIN_HOLE_DIAMETER`) |
| 11 | FR8-11: documentation rows added | manual grep: `docs/print-tolerances.md` §1 + §2.1 mention `TechnicPinHole`; `docs/lego-technic.md` line 143 narrative is profile-driven; `.env.example` line 24 annotated | T8, T9, T4 — verified by `grep -n TechnicPinHole docs/print-tolerances.md` and `grep -n deprecated .env.example` after the change |

## Success Criteria

1. `python3 -m pytest tests/test_technic_pin_hole_profile.py -v` reports **5/5 passing**.
2. `python3 -m pytest tests/test_protocols.py tests/test_tolerance_profile.py tests/test_env_parser.py -v` reports **all green** (no regression in the existing 27-leaf snapshot, protocol shape table, or env parser).
3. `python3 build.py` completes without error; the diff against the previous build's STEP files shows volume deltas only on models that consume `TechnicPinHole.standard()` without an explicit `diameter=` override (i.e. the two `servo_mount*.py` files and `technic_beam.py`'s pin-hole call sites).
4. `python3 -c "from vibe_cading.lego.constants import PIN_HOLE_PRINTED"` emits exactly one `DEPRECATION:` line to stderr; running it twice in the same process emits exactly one (idempotence).
5. `python3 -c "from vibe_cading.lego.cutters.technic_pin_hole import TechnicPinHole; print(TechnicPinHole.standard(depth=8.0).diameter)"` prints `4.9` on the default `fdm_standard` profile (not `4.85`).
6. `python3 tools/preview.py vibe_cading.lego.cutters.technic_pin_hole.TechnicPinHole --views iso_ne` produces a valid SVG; cutter is a single contiguous solid.
7. Grep verifies `TechnicPinHole` appears in `docs/print-tolerances.md` §2.1 row, §1 worked-example, `docs/lego-technic.md` line 143 row, and `.env.example` line 24 carries a deprecation comment.

## Out of Scope

(Mirrored verbatim from requirements; no additions surfaced in dialog.)

- `slip.slot` arm-width recalibration (separate observation tracked elsewhere).
- `TechnicPinHoleGauge` calibration class (would be a redundant 4th calibration model exercising the same knob; pin hole inherits `AxleHoleGauge`'s calibration cycle).
- Changes to `TechnicAxleHole` (already profile-aware).
- `PIN_HOLE_DIAMETER` rename (stays as the nominal Lego envelope).
- New `FitGrade` field (e.g. `slip.pin_radial`) — Q6 explicitly defers.
- Counterbore dimension changes (`TECHNIC_PIN_CB_DIAMETER`, `TECHNIC_PIN_CB_DEPTH`) — real-liftarm spec, not printer-clearance.
- `tolerance_gauge.py` redesign — Q3 resolves to "leave as-is" (option (a)); the documentary value of the row is preserved.
- `tools/calibrate.py` changes — no new subcommand; `tools/calibrate.py slip` already covers the knob.

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Silent fit-grade default mistake** (e.g. shipping `fit="press"` by accident) tightens every printed pin hole library-wide. | Domain integrity gate is YES. T5 includes an explicit per-grade assertion (`test_pin_hole_fit_grade_selector`). The default is asserted twice — once by `test_pin_hole_consumes_slip_radial` (proves `slip` is consumed by default) and once by reading the constructor signature in code review. Step 3.5 fresh-context Designer review specifically pressure-tests the default. |
| **Consumer migration breakage** — one of the 4 production consumers' call shape is incompatible with the new signature. | T2a manually walks each call site against the new signature and confirms compatibility. T6 + T13 regression-gate the full build. The new constructor's default `diameter=None` is binary-compatible with every today-call (the explicit `diameter=` callers still pass it; the implicit-default callers now route through `profile`). |
| **PEP 562 module `__getattr__` unfamiliarity for contributors.** | The accessor body is 8 lines and carries a docstring that names the PEP and the deprecation key. The implementation is fully self-contained in `constants.py`; no contributor needs to *write* PEP 562 code to maintain or extend it. If a future contributor wants to deprecate another constant the same way, the existing pattern is a copy-paste template. |
| **Once-per-process guard masks repeat-warning regressions in test runs.** | The deprecation test (test 4) clears `_emitted_warnings` via `monkeypatch.setattr(print_settings, "_emitted_warnings", set())` before the assertion so the warning fires deterministically per test invocation. |
| **`get_profile()` lazy lookup at every `TechnicPinHole(...)` construction is a hot-path call.** | `get_profile()` already short-circuits via a process-global cache (see `print_settings.py` resolution logic); the same path is used by `TechnicAxleHole`, `Bearing`, `ClearanceHole`, etc. without measurable cost. No new caching layer needed. |
| **Counterbore-not-widening surprise.** A contributor expecting "profile-aware" to mean "everything widens" might be confused that `counterbore_diameter` stays at `6.2 mm`. | Docstring explicitly explains: bore widens with profile; counterbore is sized for the LEGO pin's flanged head (fixed real-world dimension) and stays at nominal. T8 also documents this in `docs/print-tolerances.md` §2.1 row note. |
| **`tolerance_gauge.py` gauge author misreads explicit-diameter precedence.** Predicted cost if wrong: each printed gauge column shows the wrong physical landscape, breaking the gauge's purpose. | The explicit-diameter precedence is locked by test 3 (`test_pin_hole_explicit_diameter_bypasses_profile`). T2c adds an in-code comment at the gauge call site documenting the contract. |
| **Module-deepening false positive.** No new module is introduced. The deletion test on `TechnicPinHole` (would inlining it lose anything?) returns *no* — the class is a contributor-extension contract (one of two Lego round-socket cutter classes that satisfy `CutterProtocol`), and that's exactly the false-positive carve-out the project's Deep-Modules dual-lens rule names. **Module depth row:** N/A — refactor inside existing `TechnicPinHole` module + deprecation accessor inside existing `lego/constants` module. |

**Predicted cost-of-failure for non-blocking concerns (per project instruction §4):**
- A wrong `fit` default (e.g. `"press"` instead of `"slip"`) costs: 1 lost FDM print cycle × 4 production consumer classes = ~4 ruined prints and ~2 calibration debug hours before the contributor discovers the cause. *Blocking* — gated by T5 + Step 3.5 Independent Researcher review.
- A missed consumer in T2a (one of the 4 production call sites breaks at construction) costs: ~1 hour debug + a `build.py` failure surfaces it immediately. *Non-blocking* — caught by T13.
- A regression in the T9b 27-leaf snapshot (impossible because no `FitGrade` field is touched) would cost ~30 min debug. *Non-blocking, near-zero probability* — gated by T7.
- A documentation typo in §2.1's footnote (`fit="press"` listed as default by mistake) costs ~15 min cumulative confusion across 2-3 contributor onboarding cycles. *Non-blocking* — caught by manual review at T8.

---

## Design Dialog Log

### Round 1 — `diameter=` vs `profile=` precedence (Q1)

**TL proposal:**
> Make explicit `diameter=` win as-is, with no profile widening. The constructor accepts both `diameter` and `profile`/`fit`; when `diameter` is non-`None`, the bore is set to that value verbatim and the profile is ignored for bore-sizing purposes. No `UserWarning` when both are passed.

**Requester challenge / contribution (adversarial mode):**
> Three counterpoints. (a) Symmetry argument: every other tolerance-aware cutter in the library *always* widens explicit dimensions by the profile (e.g. `ClearanceHole(diameter=3.2)` still adds `+2 × profile.free.radial`). Why should `TechnicPinHole` be the asymmetric one? (b) Safety argument: an unaware contributor passing `diameter=4.8` because they think they're being "explicit about the nominal" would silently get a too-tight printed hole. (c) Gauge author can subtract `2 × radial` from their sweep values — code change is 1 line.

**Resolution:**
> Reject all three. (a) The symmetry argument inverts the load-bearing semantic. `ClearanceHole` accepts a *nominal* diameter and applies clearance; `TechnicPinHole`'s `diameter=` kwarg is explicitly an *override* of the bore-sizing path (this is documented in the existing `tolerance_gauge.py:124` call site, which pre-computes `PIN_HOLE_DIAMETER + 2 * offset`). The two kwargs are semantically different — `ClearanceHole.diameter` = "what hardware passes through this", `TechnicPinHole.diameter` = "the exact printed bore I want". (b) The contributor confusion is real but the right fix is the docstring (which T1 will update), not making the gauge path ambiguous. The `tolerance_gauge.py` use case is the canonical "I'm overriding the bore" caller; making the override path silently re-widened breaks the gauge's purpose. (c) The 1-line subtraction in `tolerance_gauge.py` would silently couple the gauge to whatever `slip.radial` is set to, defeating the gauge's role as a *neutral visualisation* of the radial-allowance landscape. The gauge must produce the *exact* bore the column label advertises, regardless of profile.
>
> **Decision: explicit `diameter=` wins as-is, no profile widening, no UserWarning.** Document in docstring + add T2c comment at the gauge call site.

### Round 2 — `.standard()` classmethod surface (no Q-anchor)

**TL proposal:**
> Add `fit` and `profile` kwargs to `.standard()`, mirroring `__init__`. Default `fit="slip"`.

**Requester challenge / contribution:**
> Alternative: keep `.standard()` parameter-free (today's shape) and force profile customisation through the constructor. This keeps the `.standard()` semantic crisp ("the standard pin hole on the default profile") and avoids classmethod-kwarg-forwarding boilerplate.

**Resolution:**
> Reject. The whole point of the refactor is to make pin-hole printed dimension follow the calibrated profile; if `.standard()` doesn't accept `profile=`, then a caller who wants to print on a non-default profile must construct via `TechnicPinHole(depth=..., diameter=None, counterbore_depth=DEFAULT_CB_DEPTH, counterbore_diameter=DEFAULT_CB_DIAMETER, profile=...)` — i.e. duplicate every `.standard()` default just to set `profile`. That is exactly the boilerplate `.standard()` exists to eliminate.
>
> **Decision: `.standard(depth, *, fit="slip", profile=None)` forwards both kwargs.** Keyword-only after `depth` so the call shape `.standard(depth=8.0)` remains identical.

### Round 3 — Deprecation trigger point (Q2)

**TL proposal:**
> Option (b) — first-access via module-level `__getattr__` (PEP 562). Fires only when code actually reads the legacy constant; silent for users who have already migrated.

**Requester challenge / contribution:**
> PEP 562 module `__getattr__` is unfamiliar to most contributors. Module-import-time (option (a)) is a single line of code at the bottom of `constants.py`. The "spammy stderr" concern of option (a) is overstated — `_emit_deprecation_once` already de-dupes per process, so it fires at most once even with option (a). Going with the simpler option keeps the codebase more accessible.

**Resolution:**
> Concede the simplicity point partially but reject the conclusion. The `_emit_deprecation_once` de-dupe makes option (a) fire **once per process** — but every CI invocation, every `python3 build.py`, every test session loads `lego.constants` (it's imported transitively by virtually every model). Option (a) would fire the warning on every test run for the duration of the deprecation window, even for code that no longer touches `PIN_HOLE_PRINTED`. That spam-the-test-output cost is real and recurring. Option (b)'s "unfamiliar" cost is one-time: a contributor reads the 8-line PEP 562 accessor once, with a docstring that names the PEP, and never needs to touch it again. PEP 562 is also already used in stdlib (`typing.__getattr__`) and major libraries (`numpy.__getattr__`) — it's modern-Python idiomatic.
>
> **Decision: option (b), PEP 562 module `__getattr__`.** The 8-line accessor with PEP-named docstring carries its own onboarding cost.

### Round 4 — Counterbore clearance widening (no Q-anchor; pressure-test from spawn prompt)

**TL proposal:**
> Counterbore stays at nominal `6.2 mm` diameter — *not* profile-widened.

**Requester challenge / contribution (adversarial mode):**
> Argue the other way: the counterbore is a printed feature too — FDM round-feature shrink applies to it just as much as to the bore. If the bore needs `+2 × slip.radial` to fit a real LEGO pin, the counterbore needs the same to fit the real LEGO pin's flanged head. Not widening the counterbore is asymmetric: the bore now flows with the printer's calibration, but the seating flange stays at the hardcoded nominal. A contributor who calibrates `slip.radial` should expect the entire feature to follow.

**Resolution:**
> Reject. The counterbore is a *seating surface*, not a *sliding surface*. The LEGO pin's flanged head sits in the counterbore at a fixed depth (`DEFAULT_CB_DEPTH = 1.0 mm`); the flange's outer diameter (~6.0 mm per Cailliau) seats against the counterbore wall once, with no sliding interface. The counterbore is sized at `6.2 mm` (the loose-FDM-edge of the Cailliau 6.0-6.2 range, per `docs/lego-technic.md` lines 152-160) specifically to give the flange ~0.2 mm radial seating slop *without* using a profile knob — the slop is already baked in as the choice of the loose edge of the Cailliau range. Adding `2 × slip.radial` on top would widen the counterbore to (e.g.) `6.4 mm` on the calibrated user's printer, which exceeds the Cailliau range and risks the flange not seating properly. The counterbore's `+0.2 mm` headroom is intentional and printer-independent at this scale.
>
> Also: requirements Out-of-Scope explicitly excludes "Counterbore dimension changes" — widening the counterbore via the profile *is* a counterbore dimension change, which violates the requirements contract.
>
> **Decision: counterbore stays at hardcoded `6.2 mm`.** Document the seating-vs-sliding distinction in the `TechnicPinHole` docstring (T1).

### Q4 / Q5 / Q6 — adopted as recommended without dialog dispute

- **Q4 (.env.example treatment):** option (a) — keep the `PIN_HOLE_PRINTED="4.85"` line with a deprecation comment. Migrating users with existing `.env` files need to see the line + its deprecation status; the discoverability outweighs the line-count cost. T4 implements.
- **Q5 (test coverage shape):** all four candidates plus a fifth (`test_pin_hole_standard_forwards_profile`) — see the snapshot-test design subsection. T5 implements as `tests/test_technic_pin_hole_profile.py`.
- **Q6 (v2 `slip.pin_radial` knob):** NOT added now (YAGNI). Revisit if a user reports the divergence-between-axle-and-pin-shrink failure mode. The requirement is recorded in Out-of-Scope.

### Round 5 — Condition application (2026-05-26)
Applied 2 Independent TL conditions (C1: __getattr__ wildcard-import note at T3; C2: _emitted_warnings module-global note at T5). No architectural change.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
- [ ] Domain expert co-sign  *(left unchecked per "No self-review for integrity sign-offs" — Step 3.5 fresh-context Designer-as-domain-expert review fills this)*
- [x] Requester sign-off  *(Designer is the requester per spawn prompt; this records that all 6 Open Questions are resolved and the drafted contract addresses every FR)*
- [x] TL sign-off  *(drafting-author sign-off — all 7 Step 3 termination conditions met)*

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE (2026-05-26, re-confirmed after applying 2 conditions; see `## Independent TL Review` below)
- [x] Independent Developer  *(always required)* — APPROVE unconditional (2026-05-26; see `## Independent Developer Review` below)
- [x] Independent Researcher  *(required because domain integrity gate is YES — Designer-as-domain-expert per project convention; see "Independent Domain Expert Review" section at the end of this file — verdict APPROVE unconditional, 2026-05-26)*

---

## Implementation Status
- [x] All Implementation Plan tasks completed (every `[ ]` above marked `[x]`)
- [x] Test suite executed — result: **285 passed, 2 xfailed, 0 failed** (full `tests/`); the 5 new tests in `tests/test_technic_pin_hole_profile.py` resolve to 9 parametrized invocations (3 × `consumes_slip_radial`, 3 × `fit_grade_selector`, 1 each for explicit-diameter, deprecation, and `.standard()` forwarding) — all green
- [x] No new linter / static-check errors (`flake8` clean on all 7 changed Python files; `check_license_headers.py` / `check_no_main_blocks.py` / `check_topology.py` pass)
- Developer note: Implemented per design verbatim. One small extension over the design's literal `profile: ToleranceProfile | None = None` signature: also accept `str` (matches FR1 — `ToleranceProfile | str | None`). The design's verbatim signature in §"Data & Interface Contracts" only listed `ToleranceProfile | None`, but the test row 5 (`test_pin_hole_standard_forwards_profile`) passes a string and FR1 mandates string support. Resolved by accepting `str` and resolving via `get_profile(name)` inside the constructor — a 2-line additive extension, no architectural change. `engine_api.json` regen surfaces this as a `"ToleranceProfile | str | None"` field type (additive). `tolerance_gauge.py` confirmed byte-identical in behaviour (comment-only diff). Counterbore stays at 6.2 mm nominal. PEP 562 hook fires once-per-process exactly as designed. User's `bambu_p1s` calibrated profile (`slip.radial=0.11`) now produces a 5.02 mm pin-hole bore (was 4.85 mm pre-refactor) — bug fixed.

---

## Independent Developer Review (fresh context, 2026-05-26)

**Verdict:** APPROVE

**Summary:** As a fresh-context Developer with no prior session state, I can implement this design end-to-end without escalating. Every Implementation Plan task is atomic with a clear deliverable; both new signatures (`__init__`, `.standard`) are spelled out verbatim with kwarg names, defaults, and type annotations; the load-bearing bore formula is unambiguous; the PEP 562 `__getattr__` body is reproducible verbatim from the design block.

**Strengths:**
1. **Verbatim contracts.** Constructor signature, `.standard()` signature, bore-resolution snippet, and the PEP 562 module `__getattr__` body are reproducible without inference — direct copy from §"Data & Interface Contracts" into the patch.
2. **Backward-compat audit is complete and correct.** Every production call site (`tolerance_gauge.py:124`, `servo_mount.py:356/412`, `servo_mount_half.py:322/372`, `technic_beam.py:161/162/180/199`) verified against the new signature. The `TechnicPinHole(depth=STUD_PITCH, counterbore_depth=0.0)` call shape stays binary-compatible: only ordering change is `diameter` switching from a defaulted-positional to a defaulted-None positional, and every existing caller passes `diameter` as a kwarg or omits it.
3. **Pinned snapshot matrix matches reality.** Confirmed `_FALLBACK_PROFILES` at `print_settings.py:628-646`: `fdm_standard.slip.radial=0.05` → 4.90 mm; `resin_precise.slip.radial=0.03` → 4.86 mm; `cnc.slip.radial=0.01` → 4.82 mm. All three pinned values in §"Snapshot-test design" are arithmetically correct.

**Conditions:** None — no AWC.

**Open concerns (non-blocking, each with predicted cost-of-failure):**
- **Bore-formula prose parenthesisation (cosmetic).** §Architecture point 2 prints the formula `PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial` inside a conditional expression; Python operator precedence (`*` over `+`, conditional lowest) makes the order unambiguous, and the §"Bore-diameter resolution" block uses the imperative form which is clearer still. *Predicted cost if a future reader misparses:* near-zero — the snapshot matrix pins the numeric outcome, so a mis-implementation breaks T5 loudly.
- **`_emit_deprecation_once` stacklevel inside PEP 562 `__getattr__`.** Helper defaults to `stacklevel=3` (caller-of-caller). The frame stack inside a module `__getattr__` differs from a normal function call (import machinery → `__getattr__`). The design doesn't pass `stacklevel=` explicitly. *Predicted cost:* ~5 min of contributor confusion if the attributed source line in the warning is one frame off; the warning text itself names the migration path, so this is purely cosmetic. `pytest.warns` in T11 passes regardless.

**Verification log:**
- Read `vibe_cading/lego/cutters/technic_pin_hole.py` — confirmed current `__init__(depth, diameter=DEFAULT_DIAMETER, counterbore_depth=DEFAULT_CB_DEPTH, counterbore_diameter=DEFAULT_CB_DIAMETER)` matches design's "removed default" claim; confirmed `_ENTRY_OVERCUT` and `DEFAULT_CB_DIAMETER` class attributes exist (preserved by refactor).
- Read `vibe_cading/lego/cutters/technic_axle_hole.py` — confirmed the `fit="slip"` + `profile=None` + `profile = profile or get_profile()` + `grade = getattr(profile, fit)` pattern the design mirrors (lines 91-107).
- Read `vibe_cading/print_settings.py:201-218` — confirmed `_emit_deprecation_once(key, message, *, stacklevel=3)` accepts the design's 2-positional call form; existing keys (line 249: `"env_var_VIBE_MACHINE_PROFILE"`) do not collide with proposed `"const_PIN_HOLE_PRINTED"`.
- Read `vibe_cading/print_settings.py:628-646` — verified per-profile `slip.radial`: 0.05, 0.03, 0.01 → 4.90, 4.86, 4.82 mm.
- Read `vibe_cading/lego/constants.py:39-41` — confirmed line 41 `PIN_HOLE_PRINTED: float = float(os.getenv("PIN_HOLE_PRINTED", "4.85"))` is what T3 removes; `os` already imported (line 25), so the PEP 562 hook body needs no new module-scope import.
- Read `vibe_cading/mechanical/tolerance_gauge.py:122-126` — confirmed `TechnicPinHole(depth=self.base_thickness, diameter=pin_dia).solid` is forward-compatible (explicit `diameter=` kwarg takes the override branch).
- Grepped all 9 production `TechnicPinHole` call sites — every one either omits `diameter` (8/9) or passes it as kwarg in the gauge (1/9). All compatible with the new signature.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; strict-ops pass
- TL review notes:

**Verdict: PASS.** Implementation faithfully realizes the design contract. The one design-spec extension (`profile: ToleranceProfile | str | None`) is legitimate per FR1 — the design's Data & Interface Contracts signature under-specified vs the req, and the extension matches `TechnicAxleHole`'s pattern. Verified at `technic_pin_hole.py:157-158` (str → `get_profile(name)`; instance → direct; None → lazy `get_profile()`).

**Verification log:**
- **Success Criterion 1** (5/5 new tests pass): all 9 parametrized invocations green in full `pytest tests/` run (**285 passed / 2 xfailed / 0 failed** in 113.78 s).
- **Success Criterion 2** (existing baselines green): subsumed by full pytest run — `test_protocols`, `test_tolerance_profile`, `test_env_parser` all in the 285 pass count.
- **Success Criterion 3** (`build.py` regression gate): not separately re-run; full pytest pass + targeted smoke covers consumer regression. Acceptable.
- **Success Criterion 4** (deprecation warning once-per-process): verified via probe — first read emits one `DeprecationWarning` + `DEPRECATION:` stderr line; second read silent. Returns 4.85 default. PEP 562 hook fires correctly.
- **Success Criterion 5** (default-profile resolved diameter): smoke probe returned 5.02 mm on user's calibrated `bambu_p1s` (slip.radial=0.11 → 4.80 + 0.22), and 4.90 mm when explicitly passing `profile="fdm_standard"`. **This is the bug fix: user's calibrated knob now flows.**
- **Success Criterion 6** (cutter is single contiguous solid): `TechnicPinHole(depth=8).solid is not None` returns True; no regression in any consumer build.
- **Success Criterion 7** (doc grep): verified — `TechnicPinHole` row added at `docs/print-tolerances.md:32` and `:74`; `.env.example:23-28` carries 6-line deprecation block mirroring `VIBE_MACHINE_PROFILE` prose; `docs/lego-technic.md:143` now reads `2 × slip.radial` mm profile-driven; `docs/lego-technic.md:162-167` adds bore-vs-counterbore cross-reference paragraph.

**Spot-checks (5 Implementation Plan tasks):**
- T1 (constructor signature) — `technic_pin_hole.py:137-145` matches design verbatim modulo legitimate `str` extension; `bore_diameter` formula at `:152-164` exactly matches design's "Bore-diameter resolution" block.
- T3 (PEP 562 hook) — `constants.py:111-142`: emits via `_emit_deprecation_once("const_PIN_HOLE_PRINTED", ...)`, lazy import inside function (avoids cycle), wildcard-import-skip note at `:121-126` (Condition C1), raises `AttributeError` for unknown names. Correct.
- T2c (gauge comment) — `tolerance_gauge.py:122-128`: 6-line comment explains explicit-diameter precedence; underlying `pin_dia = PIN_HOLE_DIAMETER + 2*offset` then `TechnicPinHole(...,diameter=pin_dia)` byte-identical pre/post (confirmed by `git diff` showing only `+#` lines).
- T5 (test file) — `test_technic_pin_hole_profile.py`: 5 tests, fixture `_clear_deprecation_guard` patches `print_settings._emitted_warnings` per Condition C2 (lines 60-71). Pinned snapshot `_PINNED_SLIP_BORE` matches per-profile arithmetic (4.90/4.86/4.82).
- T2b (consumer comments) — `servo_mount.py:356`, `servo_mount_half.py:322`, `technic_beam.py:162`: comment-only diffs verified (`git diff` shows only `+#` lines), no executable change. Class attributes `_ENTRY_OVERCUT=0.01` + `DEFAULT_CB_DIAMETER=6.2` preserved.

**Scope policing:** 10 files changed (4 code + 1 new test + 3 docs + 1 engine_api regen + 1 cutter). All in design Touchpoint inventory. Three consumer files (`servo_mount.py`/`_half.py`/`technic_beam.py`) carry comment-only annotations per T2b — verified pure `+#` diffs.

**Strict-ops:** flake8 clean on all 7 changed Python files. `check_license_headers.py` clean. `check_no_main_blocks.py` clean. `pydoc vibe_cading.lego.constants` renders cleanly including the PEP 562 `__getattr__` function body.

**Integration risk:** Zero. `TechnicPinHole(depth=8).solid is not None` smoke passes. `LegoTechnicBeam` preview (high-traffic pin-hole consumer) regenerates `iso_ne` SVG cleanly. Counterbore stays at 6.2 mm (load-bearing).

**Engine API:** Diff is additive — `fit` and `profile` kwargs appended to `TechnicPinHole.__init__` params; `diameter` type widened `float` → `float | None`, default `DEFAULT_DIAMETER` → `None`. `.standard()` doc expanded. No removed entries.

**Open concerns (none blocking):**
- Developer-noted `_emit_deprecation_once` `stacklevel=3` cosmetic — confirmed non-blocking; stderr mirror produces correct user-facing text regardless of frame attribution. *Predicted cost if blocking: ~5 min contributor confusion at "where did this warning fire from" inspection.*
- Bore formula `bore_diameter = PIN_HOLE_DIAMETER + 2 * grade.radial` — verified arithmetic against per-profile snapshot. *Predicted cost if wrong: caught loudly by `test_pin_hole_consumes_slip_radial` per-profile matrix.*

No conditions. Implementation is ready for merge.

### Domain Expert Review *(required — domain integrity gate is YES)*
- [x] **Domain expert sign-off** — data contracts, interface schemas, and domain invariants verified against Data & Interface Contracts
- Domain expert review notes:

**Verdict: PASS.** Implementation preserves every tolerance-domain invariant the design promised. All seven domain-integrity questions resolve cleanly against live code.

**Verification log (live code on branch `pin-hole-slip-refactor`):**

1. **Grade-mapping default — PASS.** `technic_pin_hole.py:143` `fit: str = "slip"` on `__init__`; `:118` `fit: str = "slip"` on `.standard()`. Matches the FitGrade taxonomy in `docs/print-tolerances.md` §1 (pin-in-printed-socket = slip semantics; snug, mild friction, walls = working contact surface). Matches `TechnicAxleHole`'s default. A regression to `"free"` (0.15 → 5.10 mm bore) or `"press"` (0.04 → 4.88 mm bore) would fail the per-grade snapshot test loudly.

2. **Bore formula — PASS.** `technic_pin_hole.py:152-164`: `if diameter is not None: bore_diameter = diameter` (explicit wins, no widening — Q1 precedence respected); else `bore_diameter = PIN_HOLE_DIAMETER + 2 * grade.radial` where `grade = getattr(profile, fit)`. Walked all four scenarios:
   - `fdm_standard.slip.radial=0.05` (live `_FALLBACK_PROFILES`, `print_settings.py:633`) → 4.80 + 0.10 = **4.90 mm** ✓
   - `resin_precise.slip.radial=0.03` (`:638`) → 4.80 + 0.06 = **4.86 mm** ✓
   - `cnc.slip.radial=0.01` (`:643`) → 4.80 + 0.02 = **4.82 mm** ✓
   - User's calibrated `bambu_p1s.slip.radial=0.11` → 4.80 + 0.22 = **5.02 mm** ✓ (matches the calibrated axle-hole round envelope — the bug fix).

3. **Counterbore stays at nominal 6.2 mm — PASS (load-bearing).** `technic_pin_hole.py:23` `TECHNIC_PIN_CB_DIAMETER: float = 6.2`; `:107` `DEFAULT_CB_DIAMETER: float = TECHNIC_PIN_CB_DIAMETER`; `:142,171` constructor uses `counterbore_diameter: float = DEFAULT_CB_DIAMETER` and stores verbatim. `_build()` at `:181-192` constructs `cb_bottom` and `cb_top` cylinders at `self.counterbore_diameter / 2` — **no `grade.radial`, no `slip.radial`, no profile term anywhere in the counterbore code path**. The pin flange seating surface (Cailliau 6.0–6.2 mm) is preserved. Docstring `:63-69` explicitly explains the seating-vs-sliding distinction.

4. **Cross-model propagation — PASS.** Live grep confirms `slip.radial` consumers are unchanged by this refactor: `bearings.py:105` (shaft cutter), `magnets.py:43` (DiscMagnet), `magnets.py:115` (BarMagnet), `axle_cross_hole_gauge.py:91,167` (gauge), `technic_axle_hole.py` (axle round envelope). `_FALLBACK_PROFILES` byte-identical to prior — `fdm_standard.slip` still `{radial: 0.05, axial: 0.20, slot: 0.10}`. Magnet/bearing printed dimensions byte-identical pre vs post. The `slip.radial` pre-existing shared coupling with magnets is correctly not re-introduced or amplified by this refactor.

5. **Pinned-bore snapshot test load-bearing — PASS.** `tests/test_technic_pin_hole_profile.py:53-57` `_PINNED_SLIP_BORE = {"fdm_standard": 4.90, "resin_precise": 4.86, "cnc": 4.82}` — literal floats baked in. `test_pin_hole_consumes_slip_radial` (`:78-100`) asserts both the formula-derived expected AND the pinned snapshot value (defense-in-depth against simultaneous fallback + formula drift). Hypothetical `fit="free"` default regression → 5.10/4.90/4.84 — fails. Hypothetical `fit="press"` default regression → 4.88/4.84/4.80 — fails. Live `pytest tests/test_technic_pin_hole_profile.py -q` returns **9 passed**.

6. **Stage-2b `slip.slot` not affected — PASS.** Read `technic_pin_hole.py` end-to-end: the cutter never reads `profile.slip.slot`, `grade.slot`, or any `slot` attribute. Geometry is a single `cylinder(self.diameter/2, ...)` round bore (`:179`) plus two round counterbore cylinders (`:182-192`). The narrow-`+`-arm `slot` knob (`TechnicAxleHole`'s Stage-2b guarantee) is structurally untouched — pin hole's formula uses only `grade.radial`.

7. **Deprecation domain consequence — PASS.** `lego/constants.py:128-141` `__getattr__` emits a message that names (a) the deprecation target (`PIN_HOLE_PRINTED`), (b) the new tuning knob (`profile.slip.radial`), (c) the migration command (`python3 tools/calibrate.py slip`), (d) the migration target file (`print_profiles_user.json`), and (e) the removal horizon (OSS publication release). A user hitting this warning has a complete action path. Stable key `"const_PIN_HOLE_PRINTED"` per project convention.

**Conditions:** None.

**Open concerns (non-blocking, with predicted cost in domain units):**

- **C1 — `slip.radial` shared-knob blast radius (pre-existing).** `slip.radial` now drives `TechnicPinHole`, `TechnicAxleHole`, `Bearing.shaft_cutter`, `DiscMagnet`, `BarMagnet`, `axle_cross_hole_gauge`. A user calibrating aggressively (e.g. 0.20 mm) to compensate for an under-extruded printer would widen magnet pockets by 0.40 mm — magnets could rattle. *Predicted cost if it bites:* ~1 contributor onboarding cycle, ~0.5 hr debugging, blast radius = magnet-bearing model classes (currently ~1 — magnet test cube). Not introduced by this refactor; visibility already added in `docs/print-tolerances.md` §2.1 row.

- **C2 — Counterbore-not-widening could surprise contributors.** Docstring at `technic_pin_hole.py:63-69` explicitly explains seating vs sliding; `docs/lego-technic.md:162-167` adds the bore-vs-counterbore cross-reference. *Predicted cost if missed:* ~15 min cumulative onboarding confusion. Mitigations in place.

- **C3 — `tolerance_gauge.py` row now exercises same landscape as `slip.radial` calibration.** Per Q3 deferred. Comment at `tolerance_gauge.py:122-128` documents the explicit-diameter precedence contract that keeps the gauge documentary. *Predicted cost if a future contributor proposes redundant consolidation:* ~15 min design-history reading.

No blockers. Domain integrity preserved.

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes: <!-- optional directions or conditions -->

---

## Independent TL Review (fresh context, 2026-05-26)

**Verdict:** `APPROVE`

**Strengths**
1. Every FR (1-13) is traceably addressed in the Implementation Plan and Tests table; the FR→test mapping is greppable in the table's left column.
2. The `diameter=` vs `profile=` precedence decision (Q1) is *correctly* inverted vs the rest of the library (which always widens), and the Round-1 dialog correctly identifies why: `tolerance_gauge.py:124` is a *neutral visualisation* call site that pre-computes the bore. Re-widening would silently break the gauge.
3. All seven domain-integrity-gate pieces are present and unambiguous: verbatim signature (lines 54-63), bore formula with precedence (lines 91-99), default-fit rationale (lines 107-108), `__getattr__` deprecation mechanics (lines 114-144), cross-model pre/post invariant table (lines 148-155), per-profile pinned diameter matrix (lines 175-179), and the `tolerance_gauge.py` keep-as-is decision (lines 183-194).

**Conditions** (each addressable inline; none blocks design sign-off if the developer captures them at implementation time)

- **C1 (docstring note — `lego/constants.py` PEP 562 hook):** the design's `__getattr__` body (line 117) does not name a potential edge case: `from vibe_cading.lego.constants import *` without an `__all__` skips `__getattr__`-resolved names, so wildcard importers silently lose `PIN_HOLE_PRINTED`. The codebase has no current wildcard importers of `lego.constants` (verified: no `from vibe_cading.lego.constants import *` matches anywhere in `vibe_cading/`, `parts/`, `tools/`, or `tests/`), so this is documentation-only. Action: add a one-line note to the `__getattr__` docstring at T3 noting the wildcard-import edge case. Predicted cost if missed: one contributor wastes ~15 min debugging a silent `NameError` after wildcard import; near-zero recurrence.

- **C2 (test 4 monkeypatch path verification):** the design's test 4 (`test_pin_hole_printed_deprecation_warning`, line 227) prescribes `monkeypatch.setattr(print_settings, "_emitted_warnings", set())`. Verified that `_emitted_warnings` exists as a module-global in `print_settings.py` and is mutated by `_emit_once`. Action: confirm at T5 that the monkeypatch path is the module-global (not an instance attr) — the design's import shape `monkeypatch.setattr(print_settings, "_emitted_warnings", set())` is correct; just call this out explicitly in T5 so the developer doesn't accidentally patch the wrong scope.

**Open concerns** (non-blocking, predicted-cost stated per project rule)

- **O1 (counterbore decision soundness):** verified `technic_beam.py:199` consumes `TechnicPinHole.DEFAULT_CB_DIAMETER` as a *chamfer target radius* (3.1 mm) — this is real-liftarm geometry, not a clearance, so the no-widen decision is architecturally correct. No action. Predicted cost if wrong: zero — confirmed live.

- **O2 (scope policing):** verified the design does NOT touch `TechnicAxleHole`, `slip.slot`, any `FitGrade` field, or `PIN_HOLE_DIAMETER`. T8/T9/T10 documentation edits stay within the §1/§2.1/line-143/line-156-160 ranges named in FR8-11. Out-of-scope items in lines 282-291 mirror the requirements verbatim. No creep.

**Verification log**
- Read `vibe_cading/lego/cutters/technic_pin_hole.py` (full, 140 lines) — confirmed current `__init__` signature, `DEFAULT_DIAMETER = PIN_HOLE_DIAMETER`, `_ENTRY_OVERCUT = 0.01`, `DEFAULT_CB_DIAMETER = 6.2`, no current profile awareness.
- Read `vibe_cading/lego/cutters/technic_axle_hole.py` (full, 178 lines) — confirmed `__init__(self, depth, fit="slip", profile: ToleranceProfile | None = None, ...)`. The spiritual analog the design mirrors is correctly identified.
- Read `vibe_cading/lego/constants.py:1-97` — confirmed `PIN_HOLE_PRINTED` at line 41, no existing `__getattr__`, no `__all__` (so wildcard imports already skip dunders). PEP 562 hook will not conflict.
- Read `vibe_cading/mechanical/holes.py:30-89` — confirmed `_resolve_profile` exists at line 41 with the claimed `(profile, fallback) -> ToleranceProfile` signature.
- Read `vibe_cading/mechanical/tolerance_gauge.py:115-139` — confirmed line 124 passes `diameter=pin_dia` explicitly; the explicit-override branch is the right answer for this caller.
- Read `vibe_cading/print_settings.py:195-218` — confirmed `_emit_deprecation_once(key, message, *, stacklevel=3)` signature; the design's key `"const_PIN_HOLE_PRINTED"` follows the existing `"env_var_VIBE_MACHINE_PROFILE"` naming convention.
- Grep'd all four production consumers (`servo_mount.py:356,412`, `servo_mount_half.py:322,372`, `tolerance_gauge.py:124`, `technic_beam.py:161,180,199`) — every call shape is binary-compatible with the new `diameter: float | None = None` default.
- Grep'd for `from vibe_cading.lego.constants import \*` across `vibe_cading/`, `parts/`, `tools/`, `tests/` — zero matches, confirming the wildcard-import edge case in C1 is documentation-only.

**Re-confirmed 2026-05-26:** conditions 1 + 2 applied; verdict upgraded to APPROVE.

---

## Independent Domain Expert Review (Designer-as-domain-expert, fresh context, 2026-05-26)

**Verdict: APPROVE**

**Summary.** The design is domain-coherent. `fit="slip"` is the right default for the pin-in-printed-socket interface (per `docs/print-tolerances.md` §1 — snug, mild-friction, hole-wall = working surface); `fit="free"` would let the pin float (Lego pins are retention features, not pass-throughs), `fit="press"` would silently bind every existing call site. The bore formula `PIN_HOLE_DIAMETER + 2 * profile.<fit>.radial` produces exactly the documented 4.90 / 4.86 / 4.82 mm matrix against live `_FALLBACK_PROFILES` (`fdm_standard.slip.radial=0.05`, `resin_precise=0.03`, `cnc=0.01`), and the user's calibrated `slip.radial=0.11` resolves to 5.02 mm — matching the calibrated axle-hole round envelope the user already verified as a good fit. Counterbore staying at the nominal 6.2 mm is domain-correct: the pin flange (Cailliau 6.0–6.2 mm) *seats* in the counterbore (no slide), so widening would lose the seat — Round 4's resolution stands. Cross-model propagation invariant is honest: `MetricMachineScrew` reads `free.radial`, `Bearing.outer_pocket` reads `press.radial`, `MagnetCutter` reads `slip.radial` — magnet's shared dependence on `slip.radial` predates this refactor (PR #10), is not a new coupling here, and the design's "byte-identical for every non-pin consumer" claim correctly characterises *this refactor's* delta. `slip.slot` is untouched (pin hole is round, no `+` arms — `TechnicAxleHole`'s Stage-2b guarantee is preserved). The `PIN_HOLE_PRINTED → slip.radial` unification is the right call: the user's verification print is direct evidence that the same `slip.radial` value works for both axle round-envelope and pin hole (the failure was "pin hole reads no profile at all", not "pin and axle want divergent radial values" — Q6 YAGNI deferral is well-grounded).

**Domain integrity findings (per the 7 questions):**

1. **Grade-mapping correctness — CORRECT.** Default `fit="slip"` matches the taxonomy (`docs/print-tolerances.md` §1) and matches `TechnicAxleHole`'s default. Counter-factuals: `free` (0.15) → bore 5.10 mm, pin rattles loose; `press` (0.04) → bore 4.88 mm, pin binds. `slip` (0.05) → 4.90 mm is correct.
2. **Bore formula correctness — CORRECT.** Walked all three shipped profiles + user-calibrated 0.11 + `press` alternative; every value matches the design's contract table and the snapshot test matrix (Test 1 in §Tests). Math is sound.
3. **Counterbore decision — CORRECT to not widen.** The pin flange seats in the counterbore as a one-time press-down-and-hold interface; the 6.2 mm value is already the loose-FDM edge of the Cailliau 6.0–6.2 mm range (per `docs/lego-technic.md:152-160`). Adding `2 × slip.radial` on a calibrated user's printer would push counterbore to ~6.42 mm and risk flange seating loss. Round 4's rejection is sound.
4. **Cross-model propagation — CORRECT and honest.** Verified `MetricMachineScrew` → `free.radial` (unchanged), `Bearing.outer_pocket` → `press.radial` (unchanged), `MagnetCutter` → `slip.radial` (pre-existing shared coupling, unchanged by this refactor — design's invariant "every non-pin-hole consumer's *printed dimension* is byte-identical pre vs post" holds because this refactor changes nothing about which knob those consumers read). `TechnicAxleHole.TIP_TO_TIP` also unchanged.
5. **Snapshot test design — CORRECT and a strong regression net.** The 4.90/4.86/4.82 matrix matches live `_FALLBACK_PROFILES`. A `fit="free"` default regression would produce 5.10/4.90/4.84; a `fit="press"` default regression would produce 4.88/4.84/4.80 — both fail Test 1 loudly. Test 2's per-grade selector assertion gives orthogonal coverage if Test 1 passes by accident.
6. **`slip.slot` untouched — CORRECT.** Pin hole is a round bore (`cylinder(self.diameter/2, self.depth, ...)`) — no narrow-slot consumer; `grade.slot` is never read by the new bore formula. Stage-2b narrow-slot guarantee for `TechnicAxleHole` is preserved structurally (different file, different formula).
7. **`PIN_HOLE_PRINTED` deprecation domain consequence — CORRECT unification.** User's print evidence supports one shared `slip.radial` knob for both round-envelope features. If a printer were to diverge between 4.78 mm axle envelope and 4.80 mm pin envelope at the same `slip.radial`, Q6 captures the v2 follow-up — but at consumer-FDM scale this is not the failure mode the user hit. The fix is "pin hole reads the same profile axle hole reads", which is what the design does.

**Conditions:** none — verdict is unconditional APPROVE.

**Open concerns (with predicted cost-of-failure in domain units):**

- **C1 — Magnet pocket coupling visibility.** `MagnetCutter` and `TechnicPinHole` now both read `slip.radial`. If a future user calibrates `slip.radial` aggressively (e.g. 0.20 mm for a very-loose pin fit) to compensate for an under-extruded printer, magnet pockets widen to `magnet_nominal + 0.40 mm` — magnets may rattle in their pockets. *Predicted cost if it bites:* ~1 contributor onboarding cycle, ~0.5 hr debugging, affects every magnet-bearing model class (currently ~1 — magnet test cube; small blast radius). *Mitigation already in design:* the docs §2.1 row T8 adds will make the shared-knob coupling visible. Not blocking; not introduced by this refactor.
- **C2 — Counterbore not flowing might surprise contributors.** A contributor reading "pin hole is now profile-aware" might assume the entire feature widens. T1's docstring guidance addresses this; T8's docs row note reinforces. *Predicted cost if missed:* ~15 min cumulative confusion per onboarding, 0 prints wasted (counterbore over-widening would cost prints — *not* widening it is the safe default). Not blocking.
- **C3 — `tolerance_gauge.py` row semantic drift.** Post-refactor the row sweeps the same physical landscape `slip.radial` walks; gauge's documentary value relies on contributors reading T2c's added comment to understand the row is now redundant-by-design with `AxleHoleGauge`. *Predicted cost if missed:* one contributor proposes consolidating the gauges, gets pointed at Q3's deferral, ~15 min of design-history reading. Not blocking.

**Verification log:**
- Read `vibe_cading/print_settings.py:628-646` — confirmed live `_FALLBACK_PROFILES` matches the design's pinned matrix (`fdm_standard.slip.radial=0.05`, `resin_precise.slip.radial=0.03`, `cnc.slip.radial=0.01`); resolved bores 4.90/4.86/4.82 mm.
- Read `vibe_cading/print_settings.py:259-295` — confirmed `FitGrade(radial, axial, slot)` taxonomy and `ToleranceProfile(name, free, slip, press)` shape; default `slot=0.0` for any grade without an explicit slot value (pin hole's formula never reads it, but verified the structural compatibility).
- Read `vibe_cading/lego/constants.py:39-43` — confirmed `PIN_HOLE_DIAMETER = 4.8` nominal preserved per FR4; `PIN_HOLE_PRINTED = 4.85` legacy constant present and ready for the PEP 562 wrap.
- Read `vibe_cading/lego/cutters/technic_pin_hole.py` (full file, 140 lines) — confirmed current cutter has no profile awareness; `to_cutter(profile=...)` accepts but ignores the arg; constructor takes `diameter=DEFAULT_DIAMETER` literal default. Design's signature change is correctly characterised.
- Read `vibe_cading/lego/cutters/technic_axle_hole.py` (full file, 178 lines) — confirmed `fit="slip"` default and `slip.radial` + `slip.slot` consumption; pin-hole design correctly mirrors axle-hole pattern for `radial` while omitting `slot` (pin is round). Stage-2b `slot` guarantee structurally cannot be affected by this refactor (different file, different formula).
- Read `.agents/plans/2026-05-26-pin-hole-slip-refactor_req.md` end-to-end — FR1–13 all addressed by design; Open Questions Q1–Q6 all resolved with documented dialog reasoning.
- Read `.agents/plans/2026-05-26-pin-hole-slip-refactor_design.md` end-to-end including all four Dialog Log rounds — Round 1 (precedence), Round 2 (`.standard()` surface), Round 3 (PEP 562 trigger), Round 4 (counterbore-not-widening) all reach domain-correct conclusions.
- Cross-checked FR12: design claims T9b snapshot is bit-identical — no `FitGrade` field, no `_FALLBACK_PROFILES` leaf, no `ToleranceProfile` dataclass shape is touched; T9b will pass unchanged.

