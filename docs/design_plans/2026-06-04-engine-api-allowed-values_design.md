# Design: engine_api.json schema 1.1 — `allowed_values` + `value_doc` for closed-set string params
<!-- Filename: 2026-06-04-engine-api-allowed-values_design.md  (tracked in git under .agents/plans/) -->

## Meta
- **Requirements ref**: `.agents/plans/2026-06-04-engine-api-allowed-values_req.md`
- **Requester role**: @tl (REQUIREMENTS authored at Step 2; routed from PM following maintainer-acknowledged consumer RFC, issue #6)
- **Date**: 2026-06-04
- **Dialog rounds**: 4 (see Design Dialog Log)
- **Domain integrity gate**: **NO** — pure stdlib tooling / wire-contract change to `tools/engine_api/`; no CAD geometry, tolerance, axis/datum convention, or ML-domain invariant. No Visual-Contract SVG deliverable (req Out-of-Scope confirms).

> **Locked design inputs (decided at the Step-2 human gate — NOT open):**
> - **OQ1 → Approach A** — `Literal[...]` annotations as the source of truth, read from the AST. One-time annotation pass over the in-scope sites is accepted.
> - **OQ2 → Option 1** — ship `value_doc` in the schema; populate glosses selectively (fit grades first); leave self-explanatory values gloss-free.
> - **OQ3 → Option 1** — coverage = the consumer-facing enum set (`fit`, `head_type`, `drive_type`, `type_`, and the screw/standoff/nut/insert/drive `size` families), enumerated explicitly below (R9 forbids auto-inference from defaults).

---

## Objective
Extend the `engine_api.json` `params[]` schema (1.0 → 1.1) with two additive optional fields — `allowed_values` (machine-readable closed-enum set) and `value_doc` (render-only per-value gloss) — derived from `Literal[...]` annotations read by the pure-stdlib AST extractor, drift-guarded against each param's runtime authority, so a downstream code-gen consumer can constrain its output deterministically instead of inferring enums from prose.

---

## Architecture / Approach

### Approach chosen

Four coordinated changes, all additive and 1.0-safe:

1. **Annotation pass (Developer, model files).** For each in-scope param site (enumerated in *Coverage list*), change the annotation from `str` to an **inline** `Literal[...]` whose members are the param's canonical legal set. Add `from typing import Literal` to each touched module. `from_size(size=...)` declarations get `Literal["M2", "M2.5", ...]`; `head_type` / `drive_type` / `type_` / `fit` get their canonical member set. **The runtime branch tables and dicts are NOT changed** — the `Literal` is a second, type-checker-visible copy that the drift-guard test (D3) pins to the runtime authority.

2. **Extractor: `Literal[...]` → `{type, allowed_values}` mapping (`tools/engine_api/extractor.py`).** A new helper `_split_literal(annotation) -> tuple[str, list | None]` is called at the single annotation-unparse site (`extractor.py:472`, and the dataclass-field twin at `:527`). It inspects the annotation AST **before** it is unparsed into the `type` string:
   - If the annotation reads as a `Literal[...]` subscript (bare `Literal` or `typing.Literal`), return `(base_type, [members])` where `base_type` is the JSON-runtime type of the literal members (`"str"` for all 1.1 in-scope sites — every member is an `ast.Constant` whose `.value` is a `str`) and `members` is the ordered list of constant values in **source-declaration order**.
   - Otherwise return `(ast.unparse(annotation), None)` — unchanged behaviour for every other param.
   This guarantees **D1**: a param annotated `Literal["clearance", "slip", "tap"]` still emits `"type": "str"` plus `"allowed_values": ["clearance","slip","tap"]`; no 1.0 consumer reading `type` sees a retype.

3. **`Param` dataclass gains two fields + emission (`extractor.py`).** `Param` gains `allowed_values: list | None = None` and `value_doc: dict | None = None`. `to_dict` emits both as **always-present keys** (null when absent), positioned **immediately after `units`** (R1), matching the existing `units` always-present convention (`extractor.py:127`). See **D4**.

4. **`value_doc` source — co-located `# allowed-doc:` mapping read from the same module AST (`extractor.py`).** Under Approach A a `Literal` carries values but no glosses. The selective fit-grade glosses (OQ2) live in a **module-level dict literal** named by convention `_VALUE_DOC` (a plain `dict[str, dict[str, str]]` keyed by `"<Class>.<param>"`), declared in the *same module* as the annotated param. The extractor resolves it from that module's AST (a top-level `Assign` to `_VALUE_DOC`) — pure-stdlib, same-module, no cross-file graph. See **D5**.

5. **Schema-version + validator (`extractor.py`, `validate_engine_api.py`).** `SCHEMA_VERSION` 1.0 → 1.1 (`extractor.py:64`); the validator imports it (`validate_engine_api.py:42`) so the pinned check (`:178`) moves in lockstep automatically (R6). New validator assertions added to `_validate_param` cover R7/R8.

6. **Regenerate + commit (`engine_api.json`).** `python3 tools/gen_engine_api.py` rewrites the artifact; the new bytes are committed in the same PR so `gen --check` stays green (R10).

### Data flow

```
model file:  fit: Literal["clearance","slip","tap"] = "slip"   _VALUE_DOC = {"TechnicPinHole.fit": {...}}
                         │ (AST: Subscript(Literal, Tuple[Constant...]))      │ (AST: top-level Assign)
                         ▼                                                     ▼
extractor:  _split_literal(annotation) ──► ("str", ["clearance","slip","tap"])  _value_doc_for(module, "TechnicPinHole.fit")
                         │                                                     │
                         ▼                                                     ▼
Param(type="str", allowed_values=[...], value_doc={...})  ──►  to_dict()  ──►  engine_api.json
                         │
                         ▼
validator: R7 (non-empty, all-str) · R8a (default ∈ set, quote-stripped) · R8b (value_doc ⊆ set) · R8c (no value_doc without allowed_values)
```

### Critical reconciliation — `fit` on screws/nuts is NOT in the wire artifact

A material finding from re-reading the code (not visible in the requirements' citations): **the extractor only walks `__init__` and public classmethods** (`_collect_constructors`, `extractor.py:360-423`). For every screw and nut family, `fit` is a parameter of the **`to_cutter(self, profile=None, fit=...)` instance method** — which the extractor never emits. Verified against the live artifact: the ONLY `fit` params present in `engine_api.json` today are `TechnicAxleHole.__init__(fit)` and `TechnicPinHole.__init__(fit)` (the lego cutters). Therefore:

- The consumer-facing **`fit` enum that is actually emittable** is the **lego pin/axle-hole constructor `fit`** (`{"clearance","slip","press"}` — see Coverage list), NOT the screw `to_cutter` fit. These two lego sites carry the in-scope `fit` `allowed_values` and the OQ2 fit-grade `value_doc` glosses.
- Annotating the screw/nut `to_cutter(fit=...)` `Literal` is **harmless and recommended** for type-checker/IDE benefit, but it changes **zero wire bytes** (the method is never extracted), so it is **NOT a 1.1 deliverable** and is listed as an out-of-scope follow-up. The req's "fit grades first" intent (OQ2) is satisfied by glossing the *emitted* lego `fit` grades.

This reconciliation is the substance of Dialog Round 1.

### Why no new module / helper class

The change edits existing modules (the `Param` dataclass, two annotation-unparse sites in the extractor, the validator's `_validate_param`, and ~N model signatures). The only new *code unit* is `_split_literal` — a **module-private function** inside `extractor.py`, beside the existing `_units_for_param` / `_is_classvar` private helpers. It is NOT a new module, base class, or `Protocol`. Per the Dual-Lens deletion test, a single-adapter helper *seam* (e.g. a `literal_parser.py` module, or a `LiteralAnnotation` class) earns nothing: it has one internal caller, no contributor-extension contract (contributors extend by *adding a `Literal` to a signature*, a language feature — not by implementing our type), and inlining it loses no polymorphism. A private function co-located with its siblings is the honest shape. See **Module depth** below.

### Alternatives rejected
- **Emit `type: "Literal[...]"`** (let the existing `ast.unparse` flow through). Rejected — breaks 1.0 consumers reading `type` (NFC "no 1.0 field retyped", R6). D1 mandates intercepting the subscript before unparse.
- **Module-level type alias `FitGrade = Literal[...]`** instead of inline. Rejected for the *extractor-read* sites — see **D2** (the alias makes the annotation AST a bare `Name`, forcing the extractor to resolve a second cross-statement `Assign`; the alias also would have to live in a shared module to be reused, creating exactly the "distant central registry a contributor forgets" the req's contributor-ergonomics NFC warns against).
- **A central `CHOICES`/enum registry table** as the `allowed_values` source. Rejected — req Out-of-Scope forbids the `size`-dict consolidation refactor, and a central table is the low-discoverability anti-pattern OQ1-Approach-A was chosen to avoid.
- **`value_doc` as a second hand-maintained table divorced from the module.** Rejected by D5 — glosses live co-located in the same module as `_VALUE_DOC` so they are a local edit and the drift-guard can reach them via the same-module AST.
- **Conditional (omit-when-null) emission of the new keys.** Rejected by D4 — breaks parity with the always-present `units` convention and complicates the deterministic byte output.

## Data & Interface Contracts

### Wire schema (1.1) — `params[]` entry

Serialized key order (deterministic, stable for `gen --check`):

```jsonc
{
  "name": "fit",                       // unchanged (1.0)
  "type": "str",                       // unchanged (1.0) — D1: Literal base type, NOT "Literal[...]"
  "required": false,                   // unchanged (1.0)
  "default": "'slip'",                 // unchanged (1.0) — quote-wrapped via ast.unparse
  "units": null,                       // unchanged (1.0) — always present
  "allowed_values": ["free","slip","press"],   // NEW (1.1) — list | null, immediately after units
  "value_doc": {                       // NEW (1.1) — {value: gloss} | null, immediately after allowed_values
    "free": "loosest grade — generous clearance for easy hand assembly",
    "slip": "default sliding fit — pin rotates / slides without play",
    "press": "tightest grade — interference fit, firm push-in, self-retaining"
  }
}
```

**Field semantics (mirror req R1/R2):**
- `allowed_values`: `list | null`. `null` = free-form/open. Non-empty list = exact legal set, in source-declaration order. **Empty list `[]` is INVALID** (validator rejects — R8a).
- `value_doc`: `{str: str} | null`. Render-only hint; keys ⊆ `allowed_values`; MUST be `null` when `allowed_values` is `null`.

### D1 — `Literal[...]` annotation → `type: "str"` + `allowed_values` (1.0-consumer safety)

**Resolution.** The extractor intercepts the `Literal` subscript **before** the `ast.unparse(annotation)` that currently produces the `type` string at `extractor.py:472` (and the dataclass-field twin at `:527`). Concretely, replace both bare `type_str = ast.unparse(arg.annotation) ...` lines with a call to:

```python
def _split_literal(annotation: ast.expr | None) -> tuple[str, list | None]:
    """Map a parameter annotation to (type_str, allowed_values).

    A ``Literal[...]`` annotation yields the *base runtime type* of its
    members as ``type_str`` (NOT ``"Literal[...]"`` — preserving the 1.0
    ``type`` contract) plus the ordered list of member values. Any other
    annotation is unparsed verbatim with ``allowed_values = None``.
    """
    if annotation is None:
        return "Any", None
    if _is_literal_subscript(annotation):           # Subscript(value=Name|Attribute "Literal")
        members = _literal_members(annotation)      # ordered list of ast.Constant .value
        base = _literal_base_type(members)          # "str" iff every member is a str constant
        return base, members
    return ast.unparse(annotation), None
```

- `_is_literal_subscript`: `isinstance(node, ast.Subscript)` and the subscript value reads as bare `Literal` (`ast.Name(id="Literal")`) **or** `typing.Literal` (`ast.Attribute(attr="Literal", value=Name("typing"))`) — mirrors the existing `_base_is_abc` / `_base_is_protocol` AST shape so the convention is consistent.
- `_literal_members`: read `node.slice`; for a multi-member literal it is an `ast.Tuple` of `ast.Constant`; for a single-member literal it is a bare `ast.Constant`. Collect `c.value` in order. Reject non-`Constant` slice elements (a contributor writing `Literal[SOME_VAR]` is a producer bug → fail loudly, not silently).
- `_literal_base_type`: return `"str"` iff every member is a Python `str`; the 1.1 in-scope set is **all-string** (R7b / Out-of-Scope: numeric enums deferred). A future numeric enum would return `"int"` etc. — the mapping generalizes without a wire-format change.

**AST guarantee (verified).** `ast.parse` produces a real `Subscript(Literal, ...)` node for a `Literal[...]` annotation **regardless of `from __future__ import annotations`** — PEP 563 stringification affects only runtime `__annotations__`, never the parse tree the extractor walks. Verified: `standoffs.py` / `nuts/metric.py` / `nuts/tnut.py` already carry `from __future__ import annotations`; the metric/imperial/plastics/setscrew/wood screw modules do not. The extractor reads identically for both. **No 1.0 consumer sees a retype** — current artifact emits `type: "str"` for every in-scope site (verified live), and the mapping preserves exactly that.

### D2 — Inline `Literal[...]` vs module-level alias → **INLINE, uniformly**

**Resolution: inline `Literal[...]` at every in-scope param's definition site.** Rule the Developer follows uniformly: *the in-scope param's annotation is written directly as `Literal[...]`; no `FitGrade = Literal[...]` alias is introduced for any extractor-read site.*

Justification:
- **Extractor simplicity & honesty.** Inline = the annotation AST node *is* a `Subscript(Literal, ...)` the extractor reads with zero indirection. An alias makes the annotation a bare `ast.Name("FitGrade")`, forcing the extractor to also locate and resolve the alias's `Assign` node — more parsing, cross-statement resolution, and a failure mode when the alias is imported from another module (which the same-module AST cannot resolve, exactly the cross-file-graph the extractor refuses to build). Inline keeps the extractor a pure same-node reader.
- **Contributor ergonomics (req NFC).** The req's contributor-ergonomics constraint wants "a small, local, discoverable edit at the param's own definition site — not an edit to a distant central registry." A shared alias module *is* that distant registry. Inline keeps the declaration where the contributor is already typing.
- **Readability cost is acceptable & bounded.** The longest in-scope Literals are the `size` families (≤ 6 members, short strings). They appear once per `from_size`/`__init__` signature. Repetition across sibling screw classes is real but shallow — and is the *point*: each class's `size` set genuinely differs (`{M2..M5}` vs `{4-40, 6-32, ...}` vs `{#2, #4, ...}`), so a shared alias would be *wrong* anyway. Where a set repeats verbatim within a single class across `__init__` and `from_size` (e.g. `head_type`), the Developer MAY use a module-private alias **only if** it does not become an extractor-read indirection — i.e. NOT recommended; inline both for uniformity and zero extractor branching. **Decision: inline everywhere, no aliases.** (Round 2 negotiated this down from a per-class alias proposal — see Dialog Log.)

### D3 — Heterogeneous `size` families + drift-guard → per-param runtime-authority equality test

**Resolution.** Each in-scope param's `Literal` member set is a **second copy** that can drift from the runtime authority. A single parametrized unit test (`tests/tools/test_engine_api_allowed_values.py`) asserts, for **every** in-scope param, that its declared `Literal` member set **equals** its named runtime authority. The test reads the `Literal` from the AST (re-using the extractor's `_split_literal`, or directly via `ast`) and compares to the authority read from the **runtime-imported** class. A contributor who adds `"M14"` to `METRIC_SIZES` but forgets the `Literal` (or vice-versa) **red-fails CI**.

**Runtime authority per authority-kind (all verified against the code):**

| Authority kind | How the test reads it | Sites |
|---|---|---|
| Class/module-level `dict` keys | `set(<DICT>.keys())` (normalized to the canonical case the dict stores) | `METRIC_SIZES`, `IMPERIAL_SIZES`, `PLASTIC_SCREW_SIZES`, `SET_SCREW_SIZES`, `WOOD_SIZES`, `PhillipsDrive.PH_SIZES`, `TorxDrive.TORX_SIZES`, `MetricHexNut.DIMENSIONS`, `MetricSquareNut.DIMENSIONS`, `MetricNylocNut.DIMENSIONS`, `TNut.DIMENSIONS`, `HexStandoff.DIMENSIONS` |
| **Raising** `if/elif` accepted-branch set (head_type) — has `else: raise` | **Set-EQUALITY-by-acceptance.** The branch raises `ValueError` on an unknown value, so the branch *is* a closed runtime authority. Test asserts each `Literal` member constructs without `ValueError` AND (for a real two-directional guard) that a deliberately-bogus value DOES raise — proving the `Literal` set is exactly the accepted set, not a subset. | `head_type` (B1–B7) — metric/imperial/plastics/wood head if/elif each have `else: raise` (verified `metric.py:74`, `imperial.py:68`, `plastics.py:71`, `wood.py:46`) |
| **Non-raising** branch set (drive_type / type_) — NO `else: raise` (silently folds/ignores unknown) | **One-directional `Literal ⊆ named-canonical-set`.** The branch does NOT raise on an unknown value (`drive_type`: `metric.py:77-88` guards `if drive_type and "drive_size" in data:` with no `else`, unknown → `drive=None`; `type_`: `standoffs.py:60-68` `.solid` branches with no `else`, unknown → no thread). "Construct each member, assert no `ValueError`" is therefore a **tautology that pins nothing** (any string passes). The drift guard MUST instead assert `set(Literal members) ⊆ {named canonical set}` against an explicitly-named authority — never "no `ValueError`". See **D3-B** below for each group's named canonical set. | `drive_type` (C1–C9), `type_` (D1–D2) |
| `ToleranceProfile` **grade** field names (`getattr(profile, fit)`) | `{f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}` → `{"free","slip","press"}`. **`name` MUST be subtracted** — `dataclasses.fields(ToleranceProfile)` returns FOUR fields `(name, free, slip, press)` (verified `print_settings.py:263-266`); the unfiltered set would red-fail a correct `Literal["free","slip","press"]`. `getattr(profile, fit)` does NOT itself reject `fit="name"` at runtime, so the *test's* authority expression is the only pin on the three-grade set and must be exactly `… - {"name"}`. | lego `fit` |
| Function-local dict inside a classmethod (**closed/raising authority → EQUALITY**) | Read the classmethod-body `profiles` dict keys via `ast` and assert `set(Literal members) == set(profiles.keys())`. The classmethod **raises `ValueError`** on a missing key (`inserts.py:116-117`, `:134-135`), so the dict is a genuine closed authority — the key-set equality (not a "no `ValueError`" round-trip) is the guard. | `HeatSetInsert.voron(size)`, `HeatSetInsert.ruthex(size)` |

**Case-normalization wrinkle (verified, must be encoded in the test).** `from_size` normalizes input case inconsistently across families: metric/plastics/setscrew/voron-ruthex use **no normalization or `.upper()`**, imperial uses `.lower()`, wood uses **none**, standoff `__init__` does `.upper()` on `type_`. The `Literal` MUST declare the **canonical key form the dict actually stores** (e.g. `IMPERIAL_SIZES` stores lower-case `"4-40"`, `"1/4-20"`; `METRIC_SIZES` stores `"M2"`..`"M5"`). The drift test compares against `set(DICT.keys())` directly, so it pins the canonical form. The user may still pass other-case input at runtime (the class normalizes), but the *declared* enum is the canonical set — honest and minimal.

**`MetricNylocNut` inheritance wrinkle (verified — the one genuine sharp edge).** `MetricNylocNut` defines **no own `from_size`**; it inherits `MetricHexNut.from_size` (extractor `_collect_constructors` resolves the same-module ancestor — confirmed: the live artifact lists `MetricNylocNut.from_size(size)`). But `MetricNylocNut.DIMENSIONS` ≠ `MetricHexNut.DIMENSIONS` (Nyloc has no `"M2"`). If `MetricHexNut.from_size(size: Literal[...])` is annotated with `MetricHexNut`'s keys, the inherited record for `MetricNylocNut` would advertise an enum that includes `"M2"` — which `MetricNylocNut.from_size("M2")` accepts at the AST level (it calls `cls.DIMENSIONS` and `"M2"` is absent → `ValueError`). **Resolution:** the drift-guard test checks each *emitted record's* `allowed_values` against the *concrete class's* authority (`MetricNylocNut.DIMENSIONS`), so this mismatch **red-fails** and forces an explicit fix. The chosen fix (recorded in the Coverage list): **give `MetricNylocNut` its own `from_size` override** carrying its own `Literal` (a 3-line method delegating to `super().from_size`), so the inherited-annotation lie is eliminated at the source rather than papered over. This keeps the contract honest (Dual-Lens: lying contracts mislead contributors). Round 3 negotiated this from "accept the superset" to "override".

#### D3 general drift-guard principle (apply uniformly — no group on a tautological test)

The drift guard's strength depends on the *kind* of runtime authority. State the rule once and apply it to every in-scope group:

- **Hard closed-set authority → set-EQUALITY.** When the runtime authority is a hard dict-key set or an `if/elif` with an `else: raise` (an unknown value is *rejected*), the runtime is itself a closed set, so the guard is `set(Literal members) == set(authority)`. This applies to **Group A** (`size` families — dict-key authority, `from_size` raises `ValueError` on a missing key) and **Group B** (`head_type` — every head branch has an `else: raise`, verified `metric.py:74`, `imperial.py:68`, `plastics.py:71`, `wood.py:46`). A two-directional equality test here also catches a `Literal` member the branch would reject (a bogus value must raise).
- **Silently-folding authority → one-directional `Literal ⊆ named-canonical-set`.** When the runtime branches **silently fold or ignore** an unknown value (NO `else: raise`), the runtime is *not* a closed set and "construct each member, assert no `ValueError`" is a **tautology** (any string passes — zero drift protection). For these groups the guard MUST be a one-directional subset assertion against an **explicitly-named canonical authority**, never "no `ValueError`". This applies to **Group C** (`drive_type` — `metric.py:77-88` guards the drive if/elif and has no `else`, unknown → `drive=None`; siblings store-only) and **Group D** (`type_` — `standoffs.py:60-68` `.solid` branches have no `else`, unknown → no thread).

**Named canonical authorities for the subset groups (C, D):**

| Group | One-directional assertion | Named canonical authority (and where it lives) |
|---|---|---|
| **C — `drive_type` (C1–C9)** | `set(Literal members) ⊆ CANONICAL_DRIVES` | `CANONICAL_DRIVES = {"hex","phillips","slotted","torx"}` — the drive-name strings the `MetricMachineScrew.from_size` drive if/elif dispatches on (`metric.py:78-84`), in 1:1 correspondence with the four concrete `FastenerDrive` subclasses (`HexDrive`, `PhillipsDrive`, `SlottedDrive`, `TorxDrive` — `drives.py:66/106/87/155`). The test pins this set as a small **canonical tuple co-located with the test** AND asserts that tuple stays in step with the live `FastenerDrive` subclass roster (`{c for c in FastenerDrive.__subclasses__()}` has exactly four members) so the canonical set cannot silently drift from the drive family. SetScrew (C7/C8) is headless → its `Literal` is the canonical set minus `phillips`; the subset assertion still holds (`{hex,slotted,torx} ⊆ CANONICAL_DRIVES`). |
| **D — `type_` (D1–D2)** | `set(Literal members) ⊆ {"F-F","M-F","M-M"}` | The standoff `.solid` accepted-branch set (`standoffs.py:60-68` — `F-F`/`M-F`/`M-M` are the only values that produce thread geometry; verified there is NO `else: raise`). The canonical set `{"F-F","M-F","M-M"}` is read from the `.solid` branch literals (via AST of the method body, mirroring the classmethod-body read used for `voron`/`ruthex`) or pinned as a co-located tuple cross-checked against that AST. |

This removes the tautological "no `ValueError`" mechanism from the entire `drive_type` + `type_` surface (C1–C9, D1–D2 = 11 emitted sites). No in-scope group is left on a test that pins nothing.

### D4 — Emission convention → **always-present keys (null when absent)**

**Resolution: both `allowed_values` and `value_doc` are always-present keys, emitted `null` when absent**, immediately after `units`. This matches the existing `units` precedent exactly (`extractor.py:127` emits `out["units"] = self.units` unconditionally, `null` when no unit inferred — verified). Justification:
- **Determinism for `gen --check` (R5/R10).** A key that appears for some params and not others makes the byte output position-dependent on per-param state; always-present keys give a single uniform object shape, trivially deterministic.
- **Consumer simplicity.** A 1.1 consumer reads `param["allowed_values"]` unconditionally and branches on `None` — no `KeyError` guard. A 1.0 consumer ignores the unknown keys (additive-safe NFC).
- **Precedent already chosen.** The schema author already picked always-present for `units`; diverging for the new fields would be an inconsistency a reviewer would (correctly) flag.

`to_dict` therefore appends, after the `units` line:
```python
out["allowed_values"] = self.allowed_values   # list | None
out["value_doc"] = self.value_doc             # dict | None
```

### D5 — `value_doc` source under Approach A → co-located module-level `_VALUE_DOC` dict, read from the same-module AST

**Resolution.** A `Literal` carries values but no glosses, so the selective fit-grade glosses (OQ2) need a co-located, drift-resistant home. They live in a **module-level dict literal** named `_VALUE_DOC` in the *same module* as the annotated param, keyed `"<ClassName>.<param_name>"` → `{value: gloss}`:

```python
# vibe_cading/lego/cutters/technic_pin_hole.py  (illustrative — Developer authors the prose)
_VALUE_DOC = {
    "TechnicPinHole.fit": {
        "free":  "loosest grade — generous clearance for easy hand assembly",
        "slip":  "default sliding fit — pin rotates / slides without play",
        "press": "tightest grade — interference fit, firm push-in, self-retaining",
    },
}
```

The extractor reads `_VALUE_DOC` from that module's top-level `Assign` AST (pure-stdlib, same-module — no cross-file graph), then for each param looks up `_VALUE_DOC.get(f"{class}.{param}")`. Properties of this choice:
- **Single drift-resistant source.** The glosses sit beside the `Literal` in the same file; the **validator (R8b)** enforces `value_doc` keys ⊆ `allowed_values`, so a gloss whose key drifts from the `Literal` red-fails CI. There is no second table in a distant file.
- **Selective by construction (OQ2 Option 1).** Only params that *have* a `_VALUE_DOC` entry get glosses; everything else emits `value_doc: null`. Fit grades get glossed first; `"M3"`/`"flat"` stay gloss-free (no entry).
- **Pure-stdlib-AST-readable.** A top-level dict-literal `Assign` of string→(string→string) constants is trivially walkable with `ast` — no import, no runtime eval. The extractor only accepts constant string keys/values (a non-constant entry is a producer bug → fail loudly).

**Scope of `value_doc` population for 1.1 (OQ2 Option 1, fit-grades-first):** glosses are authored for the **emitted** fit-grade params — the lego `TechnicPinHole.fit` and `TechnicAxleHole.fit` (`free`/`slip`/`press`). All other in-scope params emit `value_doc: null`. (The screw `to_cutter` fit is not emitted, so it gets no `value_doc` — see the *fit reconciliation* above.)

---

## Coverage list (R9) — explicit in-scope param sites

**Contract for the Developer.** Every row below MUST carry a populated `allowed_values` in the shipped 1.1 artifact (no half-covered set). Each row names the inline `Literal` set to declare and the runtime authority the drift-guard test (D3) checks it against. Param sites are `module.Class :: ctor(param)`. **Sets are NOT auto-inferred from defaults** (R9) — each was read from the code and is listed deliberately.

### Group A — `size` families (dict-key authority)

| # | Site | Literal members (canonical case) | Drift authority |
|---|------|----------------------------------|-----------------|
| A1 | `mechanical.screws.metric.MetricMachineScrew :: from_size(size)` | `"M2","M2.5","M3","M4","M5"` | `METRIC_SIZES.keys()` |
| A2 | `mechanical.screws.imperial.ImperialMachineScrew :: from_size(size)` | `"4-40","6-32","8-32","10-24","1/4-20"` | `IMPERIAL_SIZES.keys()` (stored lower-case) |
| A3 | `mechanical.screws.plastics.PlasticsScrew :: from_size(size)` | `"M2","M2.5","M3","M4","M5"` | `PLASTIC_SCREW_SIZES.keys()` |
| A4 | `mechanical.screws.setscrew.SetScrew :: from_size(size)` | `"M2","M2.5","M3","M4","M5"` | `SET_SCREW_SIZES.keys()` |
| A5 | `mechanical.screws.wood.WoodScrew :: __init__(size)` | `"#2","#4","#6","#8","#10","3/16"` | `WOOD_SIZES.keys()` *(req omitted this dict name; it exists and is the authority)* |
| A6 | `mechanical.screws.drives.PhillipsDrive :: from_size(size)` | `"PH00","PH0","PH1","PH2","PH3"` | `PhillipsDrive.PH_SIZES.keys()` |
| A7 | `mechanical.screws.drives.TorxDrive :: from_size(size)` | `"T5","T6","T8","T10","T15","T20","T25","T30"` | `TorxDrive.TORX_SIZES.keys()` |
| A8 | `mechanical.nuts.metric.MetricHexNut :: from_size(size)` | `"M2","M2.5","M3","M4","M5","M6","M8"` | `MetricHexNut.DIMENSIONS.keys()` |
| A9 | `mechanical.nuts.metric.MetricSquareNut :: from_size(size)` | `"M2","M2.5","M3","M4","M5","M6"` | `MetricSquareNut.DIMENSIONS.keys()` |
| A10 | `mechanical.nuts.metric.MetricNylocNut :: from_size(size)` | `"M2.5","M3","M4","M5","M6","M8"` | `MetricNylocNut.DIMENSIONS.keys()` — **requires own `from_size` override** (D3 inheritance wrinkle) |
| A11 | `mechanical.nuts.tnut.TNut :: from_size(size)` | `"M3","M4","M5"` | `TNut.DIMENSIONS.keys()` |
| A12 | `mechanical.standoffs.HexStandoff :: from_size(size)` | `"M2","M2.5","M3","M4","4-40","6-32"` | `HexStandoff.DIMENSIONS.keys()` |
| A13 | `mechanical.inserts.HeatSetInsert :: voron(size)` | `"M3","M4"` | local `profiles` dict in `voron` (classmethod-body authority) |
| A14 | `mechanical.inserts.HeatSetInsert :: ruthex(size)` | `"M2","M2.5","M3","M3_short","M4","M5"` | local `profiles` dict in `ruthex` |

### Group B — `head_type` (if/elif accepted-branch authority; canonical user-facing set)

The brief pins the **canonical** set (the values a user would naturally pass); aliases that the branch silently folds (`"button"`→pan, `"round"`→pan) are **excluded** from the `Literal` to keep the consumer enum clean. **Authority kind: raising branch (`else: raise`)** — so per the D3 general principle this group uses set-EQUALITY-by-acceptance: the drift test asserts every `Literal` member constructs without `ValueError` AND that a deliberately-bogus value DOES raise (proving the declared set is exactly the accepted set, not a subset). Note the *excluded folded aliases* (`button`/`round`) are NOT in the `Literal`; the equality is against the **canonical accepted set the brief pins** (socket/flat/pan etc.), with the folded aliases handled as a documented exclusion, not a drift failure.

| # | Site | Literal members | Drift authority |
|---|------|-----------------|-----------------|
| B1 | `mechanical.screws.metric.MetricMachineScrew :: __init__(head_type)` | `"socket","flat","pan"` | metric `from_size` head if/elif (accepts socket/flat/pan; button→pan alias excluded) |
| B2 | `mechanical.screws.metric.MetricMachineScrew :: from_size(head_type)` | `"socket","flat","pan"` | (same) |
| B3 | `mechanical.screws.imperial.ImperialMachineScrew :: __init__(head_type)` | `"socket","flat","pan"` | imperial `from_size` head if/elif |
| B4 | `mechanical.screws.imperial.ImperialMachineScrew :: from_size(head_type)` | `"socket","flat","pan"` | (same) |
| B5 | `mechanical.screws.plastics.PlasticsScrew :: __init__(head_type)` | `"pan","flat"` | plastics `from_size` head if/elif (only pan/flat) |
| B6 | `mechanical.screws.plastics.PlasticsScrew :: from_size(head_type)` | `"pan","flat"` | (same) |
| B7 | `mechanical.screws.wood.WoodScrew :: __init__(head_type)` | `"flat","pan"` | wood `__init__` head if/elif (button/round→pan aliases excluded) |

### Group C — `drive_type` (silently-folding branch → `Literal ⊆ CANONICAL_DRIVES` subset authority)

**Authority kind: non-raising (no `else: raise`).** `MetricMachineScrew.from_size` dispatches the drive if/elif on `hex`/`phillips`/`slotted`/`torx` but is guarded by `if drive_type and "drive_size" in data:` with **no `else: raise`** (`metric.py:77-88`) — an unknown `drive_type` silently yields `drive=None`. Sibling screws (imperial/plastics/setscrew/wood) merely *store* `drive_type` and never branch on it. So **NO** site in this group raises on an unknown drive: a "construct each member, assert no `ValueError`" test is a tautology and pins nothing. Per the D3 general principle, the drift guard for **all of C1–C9** is the one-directional `set(Literal members) ⊆ CANONICAL_DRIVES` assertion against the named canonical authority `CANONICAL_DRIVES = {"hex","phillips","slotted","torx"}` (the four `FastenerDrive` subclasses — see *D3-B named canonical authorities*). The drift test additionally pins `CANONICAL_DRIVES` to the live `FastenerDrive.__subclasses__()` roster so the canonical tuple cannot drift from the drive family.

| # | Site | Literal members | Drift authority |
|---|------|-----------------|-----------------|
| C1 | `mechanical.screws.metric.MetricMachineScrew :: __init__(drive_type)` | `"hex","phillips","slotted","torx"` | `⊆ CANONICAL_DRIVES` — NOT a raise guard: `metric.py:77-88` drive if/elif has no `else: raise` (unknown → `drive=None`) |
| C2 | `mechanical.screws.metric.MetricMachineScrew :: from_size(drive_type)` | `"hex","phillips","slotted","torx"` | `⊆ CANONICAL_DRIVES` (same — non-raising) |
| C3 | `mechanical.screws.imperial.ImperialMachineScrew :: __init__(drive_type)` | `"hex","phillips","slotted","torx"` | `⊆ CANONICAL_DRIVES` (imperial stores `drive_type`, never branches) |
| C4 | `mechanical.screws.imperial.ImperialMachineScrew :: from_size(drive_type)` | `"hex","phillips","slotted","torx"` | `⊆ CANONICAL_DRIVES` (same) |
| C5 | `mechanical.screws.plastics.PlasticsScrew :: __init__(drive_type)` | `"phillips","hex","slotted","torx"` | `⊆ CANONICAL_DRIVES` (stored only) |
| C6 | `mechanical.screws.plastics.PlasticsScrew :: from_size(drive_type)` | `"phillips","hex","slotted","torx"` | `⊆ CANONICAL_DRIVES` (same) |
| C7 | `mechanical.screws.setscrew.SetScrew :: __init__(drive_type)` | `"hex","slotted","torx"` | `⊆ CANONICAL_DRIVES` — headless → omits `phillips`; default `"hex"` |
| C8 | `mechanical.screws.setscrew.SetScrew :: from_size(drive_type)` | `"hex","slotted","torx"` | `⊆ CANONICAL_DRIVES` (same) |
| C9 | `mechanical.screws.wood.WoodScrew :: __init__(drive_type)` | `"phillips","hex","slotted","torx"` | `⊆ CANONICAL_DRIVES` (stored only) |

> **Note on the whole `drive_type` group (C1–C9).** **No** site in this group raises on an unknown drive — `MetricMachineScrew.from_size` guards the drive if/elif with `if drive_type and "drive_size" in data:` and has **no `else: raise`** (`metric.py:77-88`; unknown → `drive=None`), and every sibling (imperial/plastics/setscrew/wood) merely *stores* `drive_type`. A "no `ValueError`" drift test would therefore be a tautology for the entire group. The drift authority is the **brief-pinned canonical tuple** `CANONICAL_DRIVES = {"hex","phillips","slotted","torx"}` (the four concrete `FastenerDrive` subclasses), and the drift guard is the **one-directional** assertion `set(Literal members) ⊆ CANONICAL_DRIVES` (see *D3-B named canonical authorities*). The test also pins `CANONICAL_DRIVES` against the live `FastenerDrive.__subclasses__()` roster (exactly four) so the canonical tuple cannot silently drift from the drive family. SetScrew (C7/C8) is headless so `phillips` is omitted — `{hex,slotted,torx} ⊆ CANONICAL_DRIVES` still holds; the Developer verifies this narrowing during impl and the brief permits the four-member set if narrowing proves arbitrary. This is deliberate — the authority is a *brief-pinned canonical tuple* (cross-checked against the runtime subclass roster), not a per-class runtime branch — flagged explicitly so the reviewer sees it is intentional, not an oversight.

### Group D — `type_` (standoff; silently-folding branch → `Literal ⊆ {"F-F","M-F","M-M"}` subset authority)

**Authority kind: non-raising (no `else: raise`).** `HexStandoff.solid` (`standoffs.py:60-68`) branches on `F-F`/`M-F`/`M-M` to add the bore / stud geometry but has **no `else: raise`** — an unknown `type_` silently produces a plain hex body (no thread). So a "no `ValueError`" drift test is a tautology here too. Per the D3 general principle, the guard is the one-directional `set(Literal members) ⊆ {"F-F","M-F","M-M"}` against the standoff `.solid` accepted-branch set (read from the `.solid` body literals via AST, or pinned as a co-located tuple cross-checked against that AST — see *D3-B named canonical authorities*). `__init__` `.upper()`-normalizes input, so the canonical declared form is the upper-case `F-F`/`M-F`/`M-M`.

| # | Site | Literal members | Drift authority |
|---|------|-----------------|-----------------|
| D1 | `mechanical.standoffs.HexStandoff :: __init__(type_)` | `"F-F","M-F","M-M"` | `⊆ {"F-F","M-F","M-M"}` — `.solid` accepted-branch set (`standoffs.py:60-68`, NO `else: raise`); `__init__` `.upper()`-normalizes |
| D2 | `mechanical.standoffs.HexStandoff :: from_size(type_)` | `"F-F","M-F","M-M"` | `⊆ {"F-F","M-F","M-M"}` (same) |

### Group E — `fit` (lego cutter constructors; ToleranceProfile-field authority) — the only emitted `fit` sites

| # | Site | Literal members | Drift authority | `value_doc`? |
|---|------|-----------------|-----------------|--------------|
| E1 | `lego.cutters.technic_pin_hole.TechnicPinHole :: __init__(fit)` | `"free","slip","press"` | `{f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}` → `{free,slip,press}` (verified `print_settings.py:263-266` — fields are `name,free,slip,press`; `name` MUST be subtracted); `getattr(profile, fit)` | **YES** (OQ2 fit-grades-first) |
| E2 | `lego.cutters.technic_axle_hole.TechnicAxleHole :: __init__(fit)` | `"free","slip","press"` | same `ToleranceProfile` grade fields (`… - {"name"}`); `getattr(profile, fit)` | **YES** |
| E3 | `lego.cutters.technic_pin_hole.TechnicPinHole :: standard(fit)` | `"free","slip","press"` | same | **annotated for IDE only — NOT EMITTED** (kwonly; see note) |

> **`TechnicPinHole.standard` (E3) `fit` is `keyword-only` and CONFIRMED NOT EMITTED.** `standard(cls, depth, *, fit, profile)` places `fit` after the bare `*`, and the extractor skips `kwonlyargs` (`extractor.py:446-451`, walks `func.args.args` only) — verified against the live `engine_api.json`: no `standard.fit` row exists (both independent reviews confirmed this empirically). **E3 is therefore NOT a wire deliverable.** The `Literal["free","slip","press"]` annotation is still **recommended on `standard`** for IDE auto-complete / type-checker benefit, but it carries **zero wire bytes** and MUST NOT be asserted in any emit / drift test (the drift test runs only against *emitted* records). E1/E2 are the only emitted `fit` sites. *Coverage accounting:* E3 is "annotated, not emitted" — do not write an emit-test for it and do not expect it in the artifact.

**Total in-scope param SITES enumerated: 35** (A: 14, B: 7, C: 9, D: 2, E: 3) — of which **E3 is annotated-but-not-emitted (kwonly, confirmed)**, so the **emitted in-scope set = 34** (A: 14, B: 7, C: 9, D: 2, E: 2). Every assertion about the shipped artifact (coverage, drift, populate, success criteria) is over the **34 emitted** sites; E3 is annotation-only and excluded from all wire-facing checks. *(Corrected 2026-06-04 per PR #26 review: earlier drafts mis-summed these as 38/37; the per-group breakdown and the Coverage rows are authoritative at 35 enumerated / 34 emitted — see `## Escalation — emitted-site count`. Scattered "37/38" figures in the historical review/dialog sections below are left as-recorded.)* Distinct emitted enum *vocabularies*: size families (14 distinct sets), head_type (3 variants), drive_type (1 canonical family set), type_ (1), fit (1 lego grade set).

### Explicitly OUT of the coverage set (free-form / internal — emit `allowed_values: null`)

- `mechanical.holes.CounterboreHole :: __init__(head_type)` — internal cutter vocabulary `{"cylinder","cone"}`, NOT consumer-facing per OQ3. Stays free-form.
- Screw/nut `to_cutter(fit=...)` — **not extracted** (instance method), so not in the artifact at all (see *fit reconciliation*).
- Every other `str` param not listed above (free-form names, labels, profile-name strings) — stays `null` (R9: honest free-form, no false enum).

## Implementation Plan
<!-- Sequenced; a Developer executes top-to-bottom. Each task independently verifiable. -->

- [x] **T1 — Extractor: `Literal` → `{type, allowed_values}` plumbing.** Add `_split_literal`, `_is_literal_subscript`, `_literal_members`, `_literal_base_type` private helpers to `tools/engine_api/extractor.py` (beside `_units_for_param` / `_is_classvar`). Wire `_split_literal` into the two annotation-unparse sites: `_extract_params` (`:472`) and `_synthesize_dataclass_init` (`:527`). Non-`Literal` annotations MUST round-trip byte-identically to today (regression-guard: the only intended byte change is on the in-scope sites). **Note on `:527` (`_synthesize_dataclass_init`):** verified NO in-scope coverage class is a synthesized `@dataclass` — every in-scope param flows through the `:472` `_extract_params` site. Wiring `:527` is correct for uniformity / future-proofing and **harmless, but changes ZERO in-scope bytes** (do not hunt for a non-existent in-scope dataclass site). Its unit test (T9) cannot be driven by any current model — it needs a **dedicated synthetic `@dataclass` fixture**, and is NOT covered by any in-scope Coverage row. *(R3, R12 — pure-stdlib AST only.)*
- [x] **T2 — `Param` dataclass: two fields + emission.** Add `allowed_values: list | None = None` and `value_doc: dict | None = None` to `Param`. In `to_dict`, append `out["allowed_values"] = self.allowed_values` then `out["value_doc"] = self.value_doc` **immediately after** the `units` line — always-present keys, `null` when absent. *(R1, R2, R4, R5, D4.)*
- [x] **T3 — `value_doc` source plumbing.** Add `_value_doc_for(module_tree, class_name, param_name)` that resolves a top-level `_VALUE_DOC` `Assign` in the param's own module AST and returns `_VALUE_DOC.get(f"{class}.{param}")` or `None`. Populate `Param.value_doc` from it at the same call sites as T1. Accept only constant str→(str→str) entries; raise on a non-constant entry. *(R4, D5.)*
- [x] **T4 — Annotation pass over the Coverage list.** For each row in *Coverage list* Groups A–E, change the param annotation `str` → inline `Literal[...]` with the listed members (canonical case). Add `from typing import Literal` to each touched module. **No runtime branch/dict is modified.** **E3 (`TechnicPinHole.standard.fit`) is annotated for IDE/type-checker benefit only — it is kwonly and NOT emitted, so do NOT add it to any emit/drift test (37 emitted sites: A14·B7·C9·D2·E2).** *(R9; inline per D2.)*
  - [x] **T4a — `MetricNylocNut.from_size` override.** Add a 3-line `from_size(cls, size: Literal["M2.5","M3","M4","M5","M6","M8"]) -> "MetricNylocNut"` override delegating to `super().from_size(size)` so the inherited annotation no longer advertises `MetricHexNut`'s `"M2"`. *(D3 inheritance wrinkle.)*
- [x] **T5 — `_VALUE_DOC` authoring (fit grades).** Add a module-level `_VALUE_DOC` dict to `technic_pin_hole.py` and `technic_axle_hole.py` with `"<Class>.fit"` → `{free,slip,press}` one-line glosses. *(R2, R4, OQ2 Option 1.)*
- [x] **T6 — Schema bump.** `extractor.py:64` `SCHEMA_VERSION = "1.0"` → `"1.1"`. The validator imports it (`validate_engine_api.py:42`) so its pinned check moves in lockstep automatically — no second literal to edit, but confirm the validator still imports (not re-declares) the constant. *(R6.)*
- [x] **T7 — Validator assertions.** In `validate_engine_api.py::_validate_param`, add: **R7a** `allowed_values` (when non-`null`) is a non-empty `list`; **R7b** every entry is a `str` (in-scope set); **R8a** if `default` present AND `allowed_values` non-`null`, the **quote-stripped** `default` (strip one layer of `ast.unparse` source-literal quoting — `"'slip'"` → `"slip"`; `None`/`null` default exempt) ∈ `allowed_values`; **R8b** `value_doc` keys ⊆ `allowed_values`; **R8c** `value_doc` MUST be `null` when `allowed_values` is `null`. Empty-list `allowed_values` → fail (R8a/R1). *(R7, R8.)*
- [x] **T8 — Drift-guard test (per-group authority kind — see D3 general principle).** Add `tests/tools/test_engine_api_allowed_values.py` parametrized over all **37 emitted** Coverage rows. Apply the authority kind per group, NOT a blanket "no `ValueError`" (which is a tautology for the non-raising groups): **set-EQUALITY** for closed authorities — Group A `== set(DICT.keys())`; Group B `head_type` `==` raising-branch accepted set (construct each member + assert a bogus value raises); Group E lego `fit` `== {f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}` (**the `- {"name"}` is mandatory** — `fields()` returns four fields incl. `name`); `voron`/`ruthex` `==` classmethod-local `profiles` dict keys (read via AST of the method body). **One-directional SUBSET** for silently-folding authorities (NO `else: raise`) — Group C `drive_type` `set(Literal) ⊆ CANONICAL_DRIVES` (a co-located tuple `{"hex","phillips","slotted","torx"}`, additionally pinned `== {drive names of FastenerDrive.__subclasses__()}` so it tracks the family); Group D `type_` `set(Literal) ⊆ {"F-F","M-F","M-M"}` (the `.solid` accepted-branch set). Exclude E3 (not emitted). *(R11 drift, D3, NFC drift-resistance.)*
- [x] **T9 — Extractor populate + negative + 1.0-`type` preservation tests.** In the same test file: (a) an in-scope param emits non-empty `allowed_values` exactly equal to its declared set; (b) a free-form `str` param emits `allowed_values: null`; (c) an in-scope param still emits `type: "str"` (D1, not `"Literal[...]"`). **(d) `:527` synthesized-dataclass path:** exercise the `_synthesize_dataclass_init` `Literal` wiring with a **dedicated synthetic `@dataclass` fixture** (no in-scope model is a synthesized `@dataclass`, so this path cannot be driven by any Coverage row — see T1 note) — assert a `Literal`-annotated dataclass field emits `type:"str"` + its `allowed_values`. *(R11, D1.)*
- [x] **T10 — Regenerate + commit artifact.** Run `python3 tools/gen_engine_api.py`; commit the new `engine_api.json` bytes in the same PR. Confirm `python3 tools/gen_engine_api.py --check` exits 0. *(R10.)*
- [x] **T11 — Full-suite + CI green (representative-scale gate).** Run `python3 tools/gen_engine_api.py --check` AND `python3 tools/validate_engine_api.py` AND `python -m pytest tests/ -v` — all green. This is the real full-pipeline exercise the tool's only true test is (the wire artifact + validator against the *whole* 65-class tree, not a single-param probe). **Local-iteration note:** `pytest` is not pre-installed in the devcontainer — `pip install pytest` first to run the test file locally; CI provides it via `ci.yml` (`python -m pytest tests/ -v`, `ci.yml:69`), so the gate itself is unaffected. *(R13; representative-scale pre-merge gate.)*

## Tests
<!-- Every R1–R13 appears in some row's "Maps to". Greppable. -->

| # | Test description | Expected assertion | File / location | Maps to |
|---|------------------|--------------------|-----------------|---------|
| 1 | In-scope param emits its declared closed set | `extract_classes` record for `MetricMachineScrew.from_size(size)` has `allowed_values == ["M2","M2.5","M3","M4","M5"]` (non-empty, ordered) | `tests/tools/test_engine_api_allowed_values.py` | **R1, R3, R11** |
| 2 | Free-form `str` param emits null | a known non-enum `str` param (e.g. a label/name param) has `allowed_values is None` AND `value_doc is None` | same | **R1, R9, R11** |
| 3 | `value_doc` present only with allowed_values; keys ⊆ set | `TechnicPinHole.__init__(fit)` record has `value_doc` keys ⊆ `allowed_values`; a param with `allowed_values is None` has `value_doc is None` | same | **R2, R4** |
| 4 | `value_doc` derives from co-located `_VALUE_DOC` (same source) | the emitted `fit` `value_doc` equals the module's `_VALUE_DOC["TechnicPinHole.fit"]` (not a second table) | same | **R4, D5** |
| 5 | Emission convention — always-present null keys | every param dict contains the keys `allowed_values` and `value_doc` (present even when `null`), positioned immediately after `units` | same | **R5, D4** |
| 6 | **D1 — 1.0 `type` preserved.** Literal param emits base type, not `Literal[...]` | `MetricMachineScrew.from_size(head_type)` has `type == "str"` (NOT `"Literal[...]"`) AND `allowed_values == ["socket","flat","pan"]` | same | **R3 (D1), NFC no-retype, R6** |
| 7 | **D3 — drift guard (per-group authority kind, per the D3 general principle).** Each in-scope `Literal` pinned to its named runtime authority | parametrized over all **37 emitted** Coverage rows. **Set-EQUALITY** groups (closed authority): Group A `==` dict keys (`set(DICT.keys())`); Group B `head_type` `==` raising-branch accepted set (each member constructs, a bogus value raises); Group E lego `fit` `==` `{f.name for f in fields(ToleranceProfile)} - {"name"}`; `voron`/`ruthex` `==` classmethod-local `profiles` dict keys. **One-directional SUBSET** groups (silently-folding authority, NO `else: raise`): Group C `drive_type` `set(Literal) ⊆ CANONICAL_DRIVES` (and `CANONICAL_DRIVES == {drive names of FastenerDrive.__subclasses__()}`); Group D `type_` `set(Literal) ⊆ {"F-F","M-F","M-M"}`. **NO group uses a tautological "no `ValueError`" assertion.** Mutating a `Literal` away from its authority red-fails (equality groups in both directions; subset groups when a member leaves the canonical set). E3 excluded (not emitted). | same | **R11, NFC drift-resistance, D3** |
| 8 | **D3 inheritance — Nyloc override honest** | `MetricNylocNut.from_size(size)` emitted `allowed_values` `==` `MetricNylocNut.DIMENSIONS.keys()` (excludes `"M2"`), proving the override (T4a) eliminated the inherited lie | same | **R3, R9, D3** |
| 9 | Validator — `allowed_values` shape & all-string | validator FAILS on a crafted record with `allowed_values: []` (empty) and on one with a non-string entry under a `str` param; PASSES the real artifact | `tests/tools/test_engine_api_allowed_values.py` (validator branch) | **R7a, R7b, R8a(empty)** |
| 10 | Validator — default ∈ allowed_values (quote-stripped) | validator strips one quote layer from `default` (`"'slip'"`→`"slip"`) before membership; FAILS a record whose quote-stripped default ∉ set; `None` default exempt | same | **R8a** |
| 11 | Validator — value_doc key-subset & null-guard | validator FAILS a record whose `value_doc` key ∉ `allowed_values` (R8b) and one with `value_doc` present while `allowed_values is null` (R8c) | same | **R2, R8b, R8c** |
| 12 | Schema version moves in lockstep | after the bump, `SCHEMA_VERSION == "1.1"` (extractor) AND `validate_engine_api.py` rejects an artifact whose `schema_version != "1.1"`; the validator imports (not re-declares) the constant | `tests/tools/test_engine_api_allowed_values.py` | **R6** |
| 13 | **Pure-stdlib, zero new deps** | `tools/engine_api/extractor.py` imports only `{ast, sys, dataclasses, pathlib}` (assert the module's import set); no CadQuery/3rd-party import added | same | **R12** |
| 14 | **`gen --check` byte-deterministic & green** | `gen_engine_api.py --check` exits 0 against the committed regenerated artifact; two back-to-back generations are byte-identical (determinism) | same (or `tests/tools/`) | **R5, R10, NFC byte-determinism** |
| 15 | **PRE-MERGE representative-scale — full pipeline green.** | `tools/gen_engine_api.py --check` + `tools/validate_engine_api.py` + `pytest tests/` all exit 0 against the **whole tree** (65 classes), exercising the real extract→serialize→validate path, not a single-param probe | manual/CI command in T11; mirrors `.github/workflows/engine-api.yml` + `ci.yml` | **R10, R13** |

> **R coverage audit (greppable):** R1→#1,2,5 · R2→#3,4,11 · R3→#1,6,8 · R4→#3,4 · R5→#5,14 · R6→#6,12 · R7→#9 · R8→#9,10,11 · R9→#2,8 · R10→#14,15 · R11→#1,2,7,8 · R12→#13 · R13→#15. **Every R1–R13 is mapped to ≥1 row.** No R relies on an out-of-scope justification.

## Success Criteria
<!-- Measurable, objectively verifiable. -->
1. `engine_api.json` `schema_version == "1.1"`; every **emitted** Coverage-list row (A1–A14, B1–B7, C1–C9, D1–D2, E1–E2 = **34 sites**; E3 is annotated-but-NOT-emitted — kwonly — and is excluded) carries a non-empty `allowed_values` exactly equal to its listed member set; every other param carries `allowed_values: null`.
2. `python3 tools/gen_engine_api.py --check` exits 0 (committed bytes == regenerated).
3. `python3 tools/validate_engine_api.py` exits 0; the R7/R8 assertions are present and fire on crafted bad input (tests #9–#11 pass).
4. `python -m pytest tests/ -v` is green, including the new `tests/tools/test_engine_api_allowed_values.py` (≥1 drift-guard + ≥1 populate + ≥1 negative + the D1 type-preservation + validator assertions).
5. The drift-guard test would red-fail if any `Literal` set is mutated away from its runtime authority (verify by a local temporary mutation during impl, then revert).
6. No 1.0 field is removed/renamed/retyped/reordered-ahead-of-`units`; a diff of a 1.0-emitted param vs 1.1 shows only the two appended trailing keys.
7. `tools/engine_api/extractor.py` import set unchanged except possibly stdlib; no third-party dependency added (`pip`-free).

## Out of Scope
<!-- Mirrors requirements; expanded by the dialog. -->
- **Visual-Contract SVG** — DOES NOT APPLY (no CAD geometry; req confirms). A reviewer MUST NOT flag the missing `_iso_ne.svg`.
- **Screw/nut `to_cutter(fit=...)` wire emission** — the extractor does not walk instance methods, so these `fit` params are not in the artifact. Annotating their `Literal` is recommended for IDE/type-checker benefit but ships **zero wire bytes** and is NOT a 1.1 deliverable. A future bump could surface `to_cutter` signatures if a consumer needs them.
- **Numeric / non-string enums** — R7b restricts entries to strings; numeric discrete sets deferred to a later bump.
- **Central `size`-dict / `CHOICES` registry refactor** — inline `Literal` per D2; consolidating `METRIC_SIZES` et al. stays out of scope.
- **Exhaustive `value_doc` for every value** — OQ2 Option 1 ships fit-grade glosses only; the rest emit `value_doc: null`.
- **Sweeping every `str` param** — OQ3 Option 1 covers only the enumerated consumer-facing set; other `str` params stay free-form.
- **Changing any model class's runtime behavior or accepted values** — annotations are additive type metadata; runtime branches/dicts untouched.

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `Literal` set silently drifts from runtime authority (contributor adds a size to the dict, forgets the `Literal`) | **D3 drift-guard test** asserts each `Literal` against its named authority by the group's authority kind — **set-EQUALITY** for closed authorities (A size dicts, B raising `head_type`, E `fit`, voron/ruthex), **one-directional SUBSET** for silently-folding authorities (C `drive_type`, D `type_`); red-fails CI. This is the NFC drift-resistance delivery mechanism. |
| `MetricNylocNut` inherits `MetricHexNut.from_size` → advertises a wrong (`"M2"`-bearing) enum | **T4a** gives Nyloc its own `from_size` override with its own `Literal`; test #8 pins it to `MetricNylocNut.DIMENSIONS`. |
| Emitting `type: "Literal[...]"` would break 1.0 consumers reading `type` | **D1** `_split_literal` intercepts the subscript before `ast.unparse`; test #6 asserts `type == "str"`. |
| `gen --check` byte-diff trips on the new fields (by design) | **T10/R10** regenerate + commit the bytes in the same PR; test #14 confirms green + determinism. |
| `default` membership check naively compares quote-wrapped `"'slip'"` → always fails | **T7/R8a** strips one quote layer before membership; test #10 covers it. `None` default exempt. |
| New extractor branch accidentally changes bytes for *non-Literal* params | **T1** regression-guard: only in-scope sites may change bytes; test #14 determinism + the full-tree `gen --check` (#15) catch any stray drift. |
| `HeatSetInsert.voron/ruthex` authority is a function-local dict, hard to read | **D3** authority-kind 4 (closed-set → EQUALITY): drift test reads the classmethod-body `profiles` dict keys via AST and asserts `set(Literal members) == set(profiles.keys())`. |
| `drive_type` (C1–C9) branches silently fold an unknown value (NO `else: raise`) → a "no `ValueError`" test would be a tautology pinning nothing | **D3 general principle + D3-B**: the guard is the one-directional `set(Literal) ⊆ CANONICAL_DRIVES`, with `CANONICAL_DRIVES` cross-checked against the live `FastenerDrive.__subclasses__()` roster. Predicted cost if the canonical set is wrong: a consumer is offered a drive the screw silently ignores — cosmetic, non-breaking (the screw still builds). |
| `type_` (D1–D2) standoff `.solid` branches silently fold an unknown value (NO `else: raise`) → same tautology risk | **D3 general principle + D3-B**: guard is `set(Literal) ⊆ {"F-F","M-F","M-M"}` (the `.solid` accepted-branch set), not "no `ValueError`". |
| lego `fit` authority `dataclasses.fields(ToleranceProfile)` returns FOUR fields incl. `name` → naive set-equality red-fails a correct `Literal` | **D3 authority-kind 3 / Group E**: the test authority is `{f.name for f in fields(ToleranceProfile)} - {"name"}` (the `- {"name"}` is mandatory; verified `print_settings.py:263-266`). |

---

## Module depth / structural-optimization (Dual-Lens deletion test)

**Verdict: N/A — no new Modules, base classes, or `Protocol`s introduced.**

The change edits existing modules (`Param` dataclass + two extractor sites + validator `_validate_param` + ~12 model signatures). The only new code unit is a cluster of **module-private functions** in `extractor.py` (`_split_literal` + 3 helpers), co-located with the existing `_units_for_param` / `_is_classvar` private siblings.

Dual-Lens audit of "should `_split_literal` be its own module / class?":
- **(a) maintainer-locality:** one internal caller-cluster (the two annotation sites). No polymorphic dispatch, no `isinstance` ladder a base class would serve. Inlining it into the call sites would only hurt readability, not lose capability — a private function is the right granularity, a *module* is not.
- **(b) contributor-locality:** an external contributor extends the enum surface by **adding a `Literal[...]` to a signature** — a Python language feature, not an implementation of our type. There is no contract for them to inherit/implement. A `LiteralAnnotation` class or `literal_parser.py` module would be a contributor-extension contract with **zero contributors to onboard** — a false-positive deep module.

Both lenses say: keep it a private function. A single-adapter helper *seam* (separate module/class) does **not** earn its keep here and is resisted per the project rule. The `_VALUE_DOC` convention is *data co-located in model modules*, not a new code module.

## Non-blocking concerns (cost-checked)

1. **E3 (`TechnicPinHole.standard.fit`) annotated-but-not-emitted (RESOLVED — no longer uncertain).** Confirmed kwonly and NOT emitted (both reviews verified against the live artifact; extractor skips `kwonlyargs`, `:446-451`). The `Literal` is annotated on `standard` for IDE benefit only and is excluded from every emit/drift test — emitted in-scope set = 37. *Residual cost:* none on the wire; if an implementer mistakenly writes an emit-test for E3 it fails immediately against the absent record. The Coverage-list E3 row and the count language now state "annotated, not emitted" explicitly so this cannot recur.
2. **C1–C9 `drive_type` canonical tuple (brief-pinned, not a runtime branch — re-specified).** The whole `drive_type` group is non-raising (no `else: raise`), so the guard is `set(Literal) ⊆ CANONICAL_DRIVES`, with `CANONICAL_DRIVES` cross-checked against the live `FastenerDrive.__subclasses__()` roster (Group C note / D3-B). *Predicted cost if the canonical set is too wide:* a consumer's picker offers a drive the screw stores-but-ignores; geometry still builds (the screw renders with the default drive). Non-breaking, cosmetic. *If too narrow:* a real drive is omitted from the picker; consumer falls back to free-form for that value. Either way: no runtime failure, no wasted print. Mitigation is a one-line tuple edit + drift-test update.
3. **`value_doc` prose quality (fit-grade glosses).** Non-blocking — render-only hint (R2), no machine semantics. *Predicted cost if a gloss is imprecise:* a consumer tooltip is slightly misleading; no generated call fails. Trivial to refine in a follow-up; the validator only checks key-subset, not prose.

---

## Design Dialog Log
<!-- Co-design rounds. D1–D5 resolved here; ≥1 substantive revision negotiated per round. -->

### Round 1 — the `fit` reconciliation (D1 framing + scope correction)
**TL proposal:**
> Map `Literal[...]` → `{type: "str", allowed_values:[members]}` by intercepting the subscript before `ast.unparse` at `extractor.py:472`. Start the in-scope `fit` work from the screw `to_cutter(fit=...)` sites since the req names `fit` as the prime consumer enum and OQ2 says "fit grades first."

**Requester challenge / contribution (TL, fresh code read):**
> The extractor only walks `__init__` + public classmethods (`_collect_constructors`, `:360-423`) — `to_cutter` is an *instance method* and is never emitted. Verified against the live artifact: the ONLY `fit` params present are `TechnicPinHole.__init__(fit)` and `TechnicAxleHole.__init__(fit)`. Annotating screw `to_cutter` fit changes **zero wire bytes**. So "fit grades first" must target the *lego* fit grades, whose vocabulary is `{free,slip,press}` (`getattr(profile, fit)` against `ToleranceProfile` fields `:264-266`) — NOT the screw `{clearance,slip,tap,interference}` set.

**Resolution:**
> **Substantive revision:** the emitted `fit` enum and its `value_doc` glosses are the **lego** `{free,slip,press}` set (Coverage Group E), not the screw `fit`. Screw `to_cutter(fit)` annotation is recommended-but-out-of-scope (Out of Scope §2). D1 mapping stands. This reframing materially corrected the scope away from a non-emitted surface.

### Round 2 — inline vs alias (D2)
**TL proposal:**
> Introduce a shared `FitGrade = Literal["free","slip","press"]` alias module so the repeated fit/head_type/drive_type Literals are declared once and reused across the sibling screw classes — DRY.

**Requester challenge / contribution:**
> A shared alias makes the annotation AST a bare `Name("FitGrade")`, forcing the extractor to resolve a cross-statement (and, if imported, cross-*file*) `Assign` — exactly the import-graph the extractor refuses to build, and a "distant central registry a contributor forgets" the req's contributor-ergonomics NFC warns against. And the `size` sets genuinely *differ* per class (`{M2..M5}` vs `{4-40..}` vs `{#2..}`), so a shared alias is semantically wrong for the largest group anyway.

**Resolution:**
> **Substantive revision:** abandon the shared-alias proposal entirely → **inline `Literal[...]` at every in-scope site, no aliases** (D2). The extractor stays a pure same-node reader; the declaration stays local to the param. Minor readability repetition is accepted and is in fact correct (per-class sets differ).

### Round 3 — `MetricNylocNut` inheritance lie (D3)
**TL proposal:**
> Annotate `MetricHexNut.from_size(size)` once; `MetricNylocNut` inherits it (the extractor already inherits the ancestor's constructor), so we get Nyloc coverage for free.

**Requester challenge / contribution:**
> `MetricNylocNut.DIMENSIONS` has no `"M2"`. Inheriting `MetricHexNut`'s `Literal` would advertise `"M2"` as legal for Nyloc, but `MetricNylocNut.from_size("M2")` raises `ValueError` (its own `DIMENSIONS` lacks the key). That is a **lying contract** — and the drift-guard test (checking each emitted record against the *concrete* class authority) would red-fail it.

**Resolution:**
> **Substantive revision:** add a 3-line `MetricNylocNut.from_size` **override** (T4a) carrying its own `Literal` keyed to `MetricNylocNut.DIMENSIONS`, delegating geometry to `super().from_size`. Honest contract over a clever-but-lying inherited one (Dual-Lens: lying contracts mislead contributors). Test #8 pins it.

### Round 4 — emission convention + value_doc source (D4, D5)
**TL proposal:**
> Emit `allowed_values`/`value_doc` only when populated (omit the key otherwise) to keep the artifact lean; author glosses in a single central `tools/engine_api/value_docs.py` table.

**Requester challenge / contribution:**
> Conditional keys break parity with the always-present `units` convention (`:127`) and make the byte output position-dependent on per-param state, complicating `gen --check` determinism. And a central `value_docs.py` is a second hand-maintained table divorced from the annotation — the exact drift the req's R4 forbids; it also can't be reached by the same-module AST the drift-guard relies on.

**Resolution:**
> **Substantive revision (two):** (1) **D4** — both new keys are **always-present, `null` when absent**, matching `units`. (2) **D5** — glosses live in a **module-level `_VALUE_DOC` dict co-located in the param's own module**, read from the same-module AST; the validator's key-subset check (R8b) enforces drift-resistance. No central table.

### Round 2 — Conditions Applied (2026-06-04, Step-3.5 post-review pass)
Both fresh-context independent reviewers (TL + Developer) returned **APPROVE-WITH-CONDITIONS**. The approved approach (inline `Literal[...]`, `_split_literal`, always-present keys, selective `value_doc`, coverage set) is UNCHANGED; these are test-specification / drift-guard precision fixes only. Conditions applied:

- **C1 — `ToleranceProfile` drift authority.** `dataclasses.fields(ToleranceProfile)` returns FOUR fields `(name, free, slip, press)` (verified `print_settings.py:263-266`), so the unfiltered set would red-fail a correct `Literal["free","slip","press"]`. Corrected the D3 authority-kind-3 cell and the E1/E2 authority column + T8 test spec to `{f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}`.
- **C2 — `drive_type` (C1–C9) drift-guard re-spec.** The metric `from_size` drive branch (`metric.py:77-88`) has no `else: raise` (unknown → `drive=None`); siblings store-only. "No `ValueError`" was a tautology. Replaced with one-directional `set(Literal) ⊆ CANONICAL_DRIVES` against the named authority `{"hex","phillips","slotted","torx"}` (the four `FastenerDrive` subclasses), additionally pinned to the live `FastenerDrive.__subclasses__()` roster. Rewrote the Group C intro, C1/C2 cells, the C-group note, and the D3 table.
- **C3 — `type_` (D1–D2) drift-guard re-spec.** `standoffs.py:60-68` `.solid` branches have no `else: raise`. Replaced with `set(Literal) ⊆ {"F-F","M-F","M-M"}` (the `.solid` accepted-branch set). Rewrote the Group D intro + cells.
- **C4 — General drift-guard principle stated once in D3.** Added the "D3 general drift-guard principle" subsection + the "D3-B named canonical authorities" table: hard/raising authorities → set-EQUALITY (A size dicts, B raising `head_type`, E `fit`, voron/ruthex); silently-folding authorities → one-directional `Literal ⊆ named-canonical-set` (C `drive_type`, D `type_`). No in-scope group left on a tautological test. Group B note tightened to the raising-equality framing; risk table + Tests #7 + T8 aligned.
- **C5 — E3 not emitted.** `TechnicPinHole.standard.fit` is keyword-only and confirmed absent from the live artifact. Reconciled the accounting: **emitted in-scope set = 37** (A14·B7·C9·D2·E2); E3 marked "annotated for IDE, NOT emitted" — no emit/drift test for it. Updated the E3 row, the count paragraph, Success Criterion #1, Tests #7, T4, and non-blocking concern #1.
- **C6 — `:527` synthesized-dataclass path.** No in-scope class is a synthesized `@dataclass`; all flow through `:472`. Added a half-line to T1 (wiring `:527` is correct + harmless, changes zero in-scope bytes) and to T9 (its test needs a dedicated synthetic-`@dataclass` fixture — not driven by any Coverage row).
- **C7 (non-blocking) — pytest install note.** Added a one-line note to T11: `pip install pytest` for local iteration; CI provides it via `ci.yml`.

No change to the architecture, the coverage set (37 emitted + E3 annotation-only), the schema-1.1 wire shape, or the Implementation-Plan task structure. Independent-reviewer sign-off boxes left untouched for the re-confirmation spawns.

---

## Sign-off

### Author sign-off (drafting role — Step 3 termination)
<!-- TL self-marks once all seven Step-3 termination conditions hold. -->
- [ ] Domain expert co-sign  *(NOT required — domain integrity gate is NO)*
- [x] Requester sign-off
- [x] TL sign-off  *(architecturally-significant wire-contract change; TL is the drafting role)*

> **Step-3 termination conditions (all satisfied):**
> 1. Every R1–R13 addressed or explicitly out-of-scope — ✔ (R-coverage audit maps all 13 to ≥1 test row; no R deferred to an out-of-scope justification).
> 2. No open questions remain — ✔ (OQ1=A, OQ2=1, OQ3=1 locked at Step-2 gate; D1–D5 resolved in this artifact).
> 3. Tests table covers every R — ✔ (greppable audit line under the table).
> 4. Success criteria measurable — ✔ (7 objective, command-verifiable criteria).
> 5. Domain gate is NO → no domain co-sign needed — ✔.
> 6. Non-blocking concerns cost-checked — ✔ (3 concerns, each with predicted failure cost).
> 7. Module-depth done or N/A — ✔ (N/A, no new Modules; Dual-Lens audit recorded).

### Independent reviewer sign-off (fresh-context — Step 3.5 termination)
<!-- NOT marked by the author. Step 4 (human review) MUST NOT begin until every box here is checked by a fresh-context reviewer. -->
- [x] Independent TL  *(always required; drafting author cannot self-sign here)* — APPROVE, see `## Independent TL Re-Review` (fresh context, 2026-06-04); all three prior TL conditions correctly resolved at source
- [x] Independent Developer  *(always required)* — APPROVE, see `## Independent Developer Re-Review` (fresh context, 2026-06-04); all four prior Developer conditions correctly resolved at source
- [ ] Independent Researcher  *(NOT required — domain integrity gate is NO)*

---

## Independent Developer Review (fresh context, 2026-06-04)

**Verdict: APPROVE-WITH-CONDITIONS**

This design is buildable as written. I verified every cited `file:line`, every Coverage-list runtime authority against the live code, the live `engine_api.json`, and the AST mechanism itself with throwaway `tmp/` probes (now removed). All material claims held. The conditions below are small precision/clarity fixes — none changes the approach, the coverage set, or the test surface. The Implementation Plan executes top-to-bottom and the R-coverage audit maps every R1–R13 to at least one concrete, writable test row.

### Strengths (≤3)
1. **The Round-1 `fit` reconciliation is correct and load-bearing.** I confirmed against the *live artifact* that the only emitted `fit` params are `TechnicPinHole.__init__(fit)` and `TechnicAxleHole.__init__(fit)` — the screw `fit` is on `to_cutter(self, …)`, an instance method the extractor never walks (`_collect_constructors` takes only `__init__` + `@classmethod`). Without this correction an implementer would have wasted effort glossing a non-emitted surface. The design caught it.
2. **Every Coverage-list authority matches the runtime today.** I read all 14 size-dict authorities (A1–A12) and the two function-local `profiles` dicts (A13/A14) at runtime; each equals the declared `Literal` set exactly (as a set). And every in-scope param that carries a default has that default ∈ its declared set, so the new R8a validator assertion is green against the regenerated artifact on day one — no day-one-red surprise.
3. **The AST mechanism is sound for every real annotation form.** A `tmp/` probe confirmed multi-member `Literal` → `Subscript`/`Tuple` (ordered members), single-member `Literal` → `Subscript`/bare-`Constant` (the design's `_literal_members` handles both), `typing.Literal` → `Subscript`/`Attribute`, and that `from __future__ import annotations` does NOT stringify the parse tree. The design's "AST guarantee (verified)" claim is genuinely true.

### Conditions / required edits (each actionable)
1. **Fix the `ToleranceProfile` field-set claim in the D3 table and the E-group authority column.** The design states `{f.name for f in dataclasses.fields(ToleranceProfile)} → {"free","slip","press"}`. Verified: `dataclasses.fields(ToleranceProfile)` actually returns **four** fields — `['name','free','slip','press']` — because `name: str` is field #1. The drift-guard test for the lego `fit` authority MUST exclude `name` (e.g. compare against `{f.name for f in fields(ToleranceProfile)} - {"name"}`, or assert the `Literal` set is a subset that round-trips through `getattr(profile, member)` for each member). As written the equality test would red-fail (`{free,slip,press} != {name,free,slip,press}`). One-line correction to the table cell + an explicit note in the T8 test spec.
2. **State that the `:527` `_synthesize_dataclass_init` wiring is currently unexercised by any in-scope row.** Verified: no Coverage-list class is a `@dataclass` with a synthesized `__init__` — every in-scope param flows through `_extract_params` (`:472`). Wiring `_split_literal` into `:527` (T1) is correct for uniformity/future-proofing and is harmless, but the implementer should know it changes **zero** in-scope bytes and that a unit test exercising the `:527` path needs a synthetic `@dataclass` fixture (it cannot be driven by any current model). Add a half-line note to T1 so the developer does not hunt for a non-existent in-scope dataclass site.

### Open concerns (non-blocking, with predicted cost of failure)
1. **`pytest` is not installed in this devcontainer** (`python3 -m pytest` → `No module named pytest`; `pytest` not on PATH). CI runs `python -m pytest tests/ -v` (`ci.yml:69`), so T9/T11's *gate* invocation is correct — but a developer iterating the new `tests/tools/test_engine_api_allowed_values.py` locally must `pip install pytest` first. *Predicted cost if missed:* a few minutes of confusion when the local test command no-ops; zero risk to the shipped artifact (CI still runs the gate). Implementer heads-up only — covered by the "install missing tools yourself" rule.
2. **E3 (`TechnicPinHole.standard.fit`) is definitively NOT emitted** — I confirmed `fit` sits after the bare `*` (keyword-only) in `standard()`, the extractor skips `kwonlyargs` (`:446-451`), and the live artifact has no `standard.fit` row. The design already predicts this and treats it as a 2-line Coverage-list correction. *Predicted cost if mishandled:* one stale "expected emitted" row in a test → an `AssertionError` the drift test (which runs only against emitted records) would surface immediately. Trivial; the design's hedge is adequate. Recommend the developer simply drop E3 from the *emitted* set up front (annotate the `Literal` for IDE benefit, but do not assert it in the wire test).
3. **C3–C9 + B/C/D "canonical-subset" authorities are brief-pinned, not pure runtime reads.** For `head_type`, stored-only `drive_type`, and `type_`, the drift authority is a *narrowed* set the brief pins (e.g. `button`→`pan` aliases excluded; SetScrew drops `phillips`), asserted via "each member constructs without `ValueError`" rather than a dict-key equality. This is honest and flagged in the design (Group C note), but the implementer must write that branch of the drift test as a *one-direction* check (every `Literal` member is accepted) — it cannot also assert "the branch accepts nothing outside the `Literal`" because the branches silently fold aliases. *Predicted cost if over-asserted:* a false-red test on a legitimately-folded alias; caught at first test run, ~10-min fix. The design already says this; restating so the implementer writes the assertion in the safe direction.

### Verification log (each code claim checked against the cited location)
| Claim (design) | Cited location | Held? |
|---|---|---|
| `SCHEMA_VERSION = "1.0"` to bump | `extractor.py:64` | ✓ exact |
| annotation-unparse site (`_extract_params`) | `extractor.py:472` | ✓ exact (`ast.unparse(arg.annotation) …`) |
| dataclass-field twin (`_synthesize_dataclass_init`) | `extractor.py:527` | ✓ exact (`ast.unparse(child.annotation) …`) |
| `units` emitted always-present | `extractor.py:127` | ✓ (`out["units"] = self.units` unconditional) |
| extractor walks only `__init__` + public `@classmethod` | `extractor.py:360-423` (`_collect_constructors`) | ✓ — instance methods (`to_cutter`) excluded |
| `kwonlyargs` out of scope (E3 dropped) | `extractor.py:446-451` | ✓ — `func.args.args` only; `standard.fit` is kwonly → absent in live artifact |
| extractor imports only `{ast, sys, dataclasses, pathlib}` | `extractor.py:55-60` | ✓ |
| validator imports (not re-declares) `SCHEMA_VERSION` | `validate_engine_api.py:42` | ✓ |
| validator pinned-check fails on mismatch | `validate_engine_api.py:178` (block 175-184) | ✓ (`elif schema_version != SCHEMA_VERSION:`) |
| new assertions land in `_validate_param` | `validate_engine_api.py` | ✓ — function exists, is the per-param hook |
| `gen --check` is a byte-diff gate | `gen_engine_api.py:109-125` | ✓; `sort_keys=False` so `to_dict` insertion order == serialized order (D4 always-present-after-`units` works) |
| `ToleranceProfile` is a `@dataclass`; fields `free/slip/press` | `print_settings.py:253-266` | PARTIAL — fields exist at 264-266, but `fields()` also returns `name` (Condition 1) |
| lego `fit` default `'slip'` ∈ `{free,slip,press}` | live `engine_api.json` | ✓ — only `TechnicPinHole.__init__(fit)` + `TechnicAxleHole.__init__(fit)` emitted, both `type=str default='slip'` |
| screw `fit` on `to_cutter` (instance method), not emitted | `screws/metric.py:132` etc. | ✓ — `to_cutter(self, profile, fit)`; absent from artifact |
| all 14 size-dict authorities exist & match declared `Literal` (A1–A14) | model files + runtime | ✓ — runtime probe: every set equal |
| `MetricNylocNut.DIMENSIONS` lacks `"M2"` (inheritance wrinkle real) | `nuts/metric.py` | ✓ — `{M2.5,M3,M4,M5,M6,M8}`; T4a override genuinely needed |
| head/drive/type_ branch sets (B/C/D) | metric/imperial/plastics/wood/setscrew/standoffs | ✓ — branches match; button/round aliases correctly excluded; setscrew has no drive branch (stored-only) |
| zero `Literal[...]` in `vibe_cading/` + `parts/` today | repo grep | ✓ — 0 occurrences (annotation pass is net-new) |
| every in-scope site emitted in live artifact | live `engine_api.json` | ✓ — 34/35 emit; only absent = E3 (predicted) |
| every in-scope default ∈ its declared set (R8a green day-one) | live artifact + Coverage list | ✓ — all 22 defaulted sites pass quote-stripped membership |
| AST: multi/single-member `Literal`, `typing.Literal`, future-import safe | `ast.parse` probe | ✓ — all forms parse to readable `Subscript` |
| baseline `gen --check` + validator green; 65 classes | live run | ✓ — both exit 0; validator reports 65 classes |
| both CI workflows exist | `.github/workflows/{engine-api,ci}.yml` | ✓ |
| `tests/tools/` has only `test_calibrate.py` (R11 no extractor test) | `tests/tools/` | ✓ |

---

## Implementation Status
<!-- Populated by #developer at Step 5 Phase A (2026-06-04). -->
- [x] All Implementation Plan tasks completed (T1–T11)
- [x] Test suite executed — result: **381 passed, 2 xfailed** (full `tests/`, final run including the +2 post-fix-hardening tests); the new `tests/tools/test_engine_api_allowed_values.py` contributes **92 passed**
- [x] No new linter / static-check errors (flake8 clean on every touched file; license-header + no-main-block checks green)
- Developer note: schema 1.1 (`allowed_values` + `value_doc`) implemented per the authoritative Coverage list; **34 emitted sites** (A14·B7·C9·D2·E2), each pinned to its runtime authority by the drift guard; E3 annotated-but-not-emitted (kwonly). See `## Escalation — emitted-site count arithmetic (34, not 37)` below — the implementation matches the design's per-group breakdown and the actual Coverage rows; only the design's prose total figure ("37"/"38") is internally inconsistent.

### Branch & commit
- **Branch:** `feat/engine-api-1.1-allowed-values` (from `main` @ `cafce01`)
- **Commit:** see return message (single conventional-commit; not pushed).

### Per-task done-state
| Task | Status | Files |
|---|---|---|
| T1 — extractor `Literal`→`{type, allowed_values}` plumbing (`_split_literal` + 3 helpers; wired at `_extract_params` and `_synthesize_dataclass_init`; non-Literal round-trips byte-identically — verified by `gen --check` exit 0) | ✅ | `tools/engine_api/extractor.py` |
| T2 — `Param` gains `allowed_values` / `value_doc`; `to_dict` emits both always-present immediately after `units` | ✅ | `tools/engine_api/extractor.py` |
| T3 — `_value_doc_for` reads top-level `_VALUE_DOC` from the param's own module AST (constant-only; raises on non-constant) | ✅ | `tools/engine_api/extractor.py` |
| T4 — annotation pass `str`→inline `Literal[...]` at every Coverage site (Groups A–E), `from typing import Literal` per touched module; E3 annotated for IDE only (kwonly, not emitted) | ✅ | 12 model files (see return) |
| T4a — `MetricNylocNut.from_size` 3-line override (own `Literal`, delegates to `super().from_size`; verified M2 raises, M3 builds) | ✅ | `vibe_cading/mechanical/nuts/metric.py` |
| T5 — `_VALUE_DOC` fit-grade glosses in both lego cutters | ✅ | `technic_pin_hole.py`, `technic_axle_hole.py` |
| T6 — `SCHEMA_VERSION` 1.0→1.1 (validator imports it — lockstep confirmed, not re-declared) | ✅ | `tools/engine_api/extractor.py` |
| T7 — validator R7/R8 in `_validate_param` (`_validate_allowed_values` helper; quote-stripped default membership) | ✅ | `tools/validate_engine_api.py` |
| T8/T9 — new test file: per-group drift guard (EQUALITY A/B/E/voron-ruthex, SUBSET C/D), populate, negative, D1 type-preservation, value_doc-source, emission-convention, validator assertions, schema lockstep, pure-stdlib, gen-determinism, `:527` synthetic-`@dataclass` fixture, Nyloc-override | ✅ | `tests/tools/test_engine_api_allowed_values.py` |
| T10 — regenerate `engine_api.json` (schema 1.1, 34 emitted `allowed_values`, 2 `value_doc`); `gen --check` exit 0 | ✅ | `engine_api.json` |
| T11 — full gates green (`gen --check`, validator, full `pytest`, flake8, license, no-main-block) | ✅ | — |

### Gate results (literal)
- `python3 tools/gen_engine_api.py --check` → exit **0**
- `python3 tools/validate_engine_api.py` → `engine_api.json OK — schema_version=1.1, 65 classes`, exit **0**
- `python -m pytest tests/ -q` → **381 passed, 2 xfailed** (2 pre-existing tolerance-profile warnings; 0 failures)
- `python -m pytest tests/tools/test_engine_api_allowed_values.py -q` → **92 passed**
- `flake8` on all touched files → exit **0**
- `python3 tools/check_license_headers.py` → "All Python files have the AGPLv3 license header."
- `python3 tools/check_no_main_blocks.py` → "OK: no `if __name__ == \"__main__\":` blocks…"
- **Drift-guard red-fail proof (Success Criterion #5):** temporarily added `"M14"` to `MetricMachineScrew.from_size`'s `size` `Literal`, regenerated → `test_drift_group_a_dict_key_equality[site3]` **FAILED** (`Literal {…,'M14'} != dict keys {…}`); reverted, re-ran → green. The drift guard genuinely pins each `Literal` to its runtime authority.

### Approved deviation / escalation
- **Escalation #1** (no behavioral deviation): the design's prose emitted-site figure ("37 emitted / 38 enumerated") is arithmetically inconsistent with the design's own per-group breakdown (`A14·B7·C9·D2·E2` = **34**) and the actual Coverage-list rows (**35 enumerated, 34 emitted**). The implementation follows the authoritative Coverage list and per-group breakdown → **34 emitted sites**, every row matching its declared ordered member set (zero missing / extra / mismatch). I did **not** fabricate 3 phantom sites to hit "37". Details in `## Escalation — emitted-site count` below.
- **Escalation #2 + in-scope implementation fix** (extractor inheritance — required to satisfy Success Criterion #6): T4a's `MetricNylocNut.from_size` override, applied literally, had an **unforeseen side-effect** — it silently DROPPED the inherited `MetricNylocNut.__init__` from the wire record (present in 1.0). Root cause: the extractor's `_collect_constructors` short-circuits the same-module ancestor-inheritance fallback once a class has *any* own constructor, so adding `from_size` removed the only path by which Nyloc's inherited `__init__` reached the artifact. I fixed this **in the extractor** (the faithful, blast-radius-of-exactly-one-class fix — see below) rather than papering it with a duplicate explicit `__init__`. Flagged for TL Phase B as an extractor-semantics change. Details in `## Escalation — inherited-__init__ drop` below.

---

## Escalation — emitted-site count (34, not 37)

**Raised by:** #developer, Step 5 Phase A (2026-06-04). Non-blocking; surfaced rather than silently absorbed (persona rule: do not deviate from the authoritative artifact silently — flag the inconsistency).

**Finding.** The design body repeatedly states **"37 emitted / 38 enumerated"** (lines ~287, 301, 306, 322, 336, 385, 441). That total does **not** match either:
- the design's **own per-group breakdown** `A14·B7·C9·D2·E2`, which sums to **34** (14+7+9+2+2), nor
- the **actual Coverage-list rows**: programmatically counting the `| A1 |`…`| E3 |` table rows gives **A:14, B:7, C:9, D:2, E:3 = 35 enumerated**; E3 is kwonly/not-emitted, so **34 emitted**.

`14+7+9+2+2 = 34`, not 37. `14+7+9+2+3 = 35`, not 38. The "37"/"38" prose figures appear to be a stale total that was never re-derived after the E3 reconciliation; the per-group breakdown and the concrete Coverage rows (the load-bearing contract) are self-consistent at 34 emitted / 35 enumerated.

**What the implementation did.** Followed the authoritative Coverage list and the per-group breakdown. The regenerated `engine_api.json` emits **exactly 34** non-null `allowed_values` sites — every Coverage row (A1–A14, B1–B7, C1–C9, D1–D2, E1–E2) with its exact ordered member set, verified programmatically (zero missing, zero extra, zero member mismatch). E3 (`TechnicPinHole.standard.fit`, kwonly) is annotated for IDE benefit only and is correctly absent from the wire artifact. The test `test_emitted_site_count` pins the emitted set to exactly these 34 sites, so the count cannot silently drift.

**Why I did not "fix" to 37.** Reaching 37 would require fabricating 3 emitted sites with no corresponding Coverage row — a violation of R9 (no auto-inferred / invented enums) and the experimental-integrity rule (do not fabricate artifacts to match a number). The substance (every consumer-facing enum covered, each drift-guarded) is fully delivered at 34. The discrepancy is a **documentation arithmetic error in the design prose**, not a coverage gap.

**Recommended resolution (for TL Phase B / Admin).** Correct the design prose figures "37 emitted → 34 emitted" and "38 enumerated → 35 enumerated" (purely a text fix; no code/test/artifact change). The per-group breakdown `A14·B7·C9·D2·E2` and all Coverage rows are already correct. Predicted cost if left unfixed: a future reader/reviewer trusts the wrong total and either hunts for 3 non-existent sites or flags a false coverage gap — a few minutes of confusion, no functional impact.

---

## Escalation — inherited-`__init__` drop from T4a (extractor fix applied)

**Raised by:** #developer, Step 5 Phase A (2026-06-04). **Blocking for Success Criterion #6 had it shipped uncaught — fixed in-scope; flagged for TL review.**

**Finding (RCA-grounded).** Applying T4a literally — add a `MetricNylocNut.from_size` override — **silently dropped the inherited `MetricNylocNut.__init__`** from `engine_api.json`. The 1.0 artifact emitted `MetricNylocNut.__init__(width_flats, thickness, thread_diameter)` (inherited from `MetricHexNut`) **plus** an inherited `from_size`. After T4a, the record collapsed to only `from_size` — a removed 1.0 wire field, violating Success Criterion #6 ("No 1.0 field is removed").

**Root cause (read from the code, not guessed).** `extractor.py::_collect_constructors` collects a class's *own* `__init__` + public classmethods, then — **only if the class has zero own constructors** (`if constructors: return constructors` short-circuits) — falls back to inheriting the *entire* constructor set from a same-module ancestor. Pre-T4a, `MetricNylocNut` had zero own constructors → it inherited both `__init__` and `from_size`. Adding the `from_size` override gave it one own constructor → the ancestor fallback was skipped wholesale → the inherited `__init__` (which Nyloc never declares itself) vanished. Verified: `MetricNylocNut` is the **only** class in the tree whose `__init__` was purely ancestor-inherited (every other size-family class declares its own `__init__`), so the blast radius is exactly one class.

**Fix (in-scope, extractor — the faithful option).** Added `_inherited_init_from_ancestor(...)` and a guarded branch in `_collect_constructors`: when a class has own constructors but **no own/synthesized `__init__`**, prepend the ancestor's inherited `__init__` (init-first ordering preserved). This makes the wire record *faithful to what the class actually exposes at runtime* (Nyloc genuinely inherits `__init__`), restores the 1.0 shape, and is a general correctness improvement — not a Nyloc-specific patch. Chosen over the alternative (a duplicated explicit `__init__` on `MetricNylocNut`) because (a) it's more honest — no signature duplication that could drift from the parent — and (b) the design scoped T4a as a *3-line `from_size` override*, so adding a full `__init__` to the model would itself be the larger deviation. **Why not escalate to TL before fixing:** the change was required to meet a non-negotiable Success Criterion, the blast radius is provably one class, and it's a minimal additive correction — but because it touches `tools/` constructor-collection *semantics*, I am flagging it explicitly for TL Phase B confirmation.

**Verification.** Post-fix, the diff of every 1.0-emitted param vs 1.1 shows **zero params dropped, zero added, zero `name`/`type`/`required`/`default`/`units` changes** — only the two appended trailing keys (Success Criterion #6 ✓). `MetricNylocNut` now emits `__init__(width_flats, thickness, thread_diameter)` (inherited, `allowed_values: null`) + `from_size(size)` (own override, `allowed_values` = Nyloc DIMENSIONS, no `"M2"`).

**Post-fix hardening (defense-in-depth).** Two regression tests added: `test_nyloc_override_preserves_inherited_init` (artifact-level — Nyloc keeps both constructors) and `test_classmethod_only_subclass_keeps_inherited_init` (extractor-level synthetic fixture — a classmethod-only subclass keeps the ancestor's `__init__`, init-first). Either red-fails if the inherited-init pass is removed.

**For TL Phase B:** confirm the extractor inheritance-semantics change is acceptable (it is additive and blast-radius-1, but it IS a behavioral change to the shared wire-contract collection logic). If the TL prefers the model-local alternative (explicit `__init__` on Nyloc), it is a small follow-up — but the extractor fix is the recommended honest path.

---

## Post-Implementation Sign-Off

### TL Review
- [x] **TL sign-off** — implementation matches design; tests pass; no unintended scope creep; `gen --check` + validator + pytest green. **PASS** — full review in `## TL Review (Phase B, 2026-06-04)` below.
- TL review notes: PASS; both deviations adjudicated acceptable; whole-artifact 1.0-safety confirmed exclusively additive. *(Persisted by orchestrator — the Phase B TL subagent completed the review + all live verification but did not finish its outcome-write; PM independently spot-checked the headline claims — 34 emitted sites, 0 `Literal` retypes, Nyloc `__init__` restored, schema 1.1, `head_type` type unchanged main↔branch — before recording.)*

### Domain Expert Review *(NOT required — domain integrity gate is NO)*
- [ ] **Domain expert sign-off** — N/A (gate NO)
- Domain expert review notes: N/A

### Human Final Approval
- [ ] **Human approved** for merge / release
- Human notes:

---

## TL Review (Phase B, 2026-06-04)

**Verdict: PASS.** Independent post-implementation architectural review of `feat/engine-api-1.1-allowed-values` @ `a6f664a` (on `main` @ `cafce01`). Every gate run live; the load-bearing claims independently re-derived, not taken on the developer's word. *(Section persisted by the orchestrator (PM) from the Phase B TL subagent's completed review — the subagent finished the review and all verification but did not complete its own outcome-write; PM re-verified the headline claims before recording. See the TL Review checkbox note above.)*

### Gate output (literal, all run by the reviewer)
```
python3 tools/gen_engine_api.py --check                → exit 0
python3 tools/validate_engine_api.py                   → engine_api.json OK — schema_version=1.1, 65 classes  (exit 0)
python3 -m pytest tests/ -q                            → 381 passed, 2 xfailed  (exit 0)
python3 -m pytest tests/tools/test_engine_api_allowed_values.py -q  → 92 passed  (exit 0)
flake8 (15 touched .py files)                          → exit 0
tools/check_license_headers.py                         → all AGPLv3 headers present  (exit 0)
tools/check_no_main_blocks.py                          → OK, no __main__ blocks  (exit 0)
```
(The 2 xfailed are pre-existing `test_tolerance_profile.py` cases, unrelated.)

### 1. Implementation Plan (T1–T11 + T4a) — COMPLETE
Verified each task against the real files (not the checkboxes): `_split_literal` + 3 helpers wired into both `:472`/`:527` sites; `Param` fields + `to_dict` after `units`; `_value_doc_for`/`_parse_value_doc_assign` (constant-only, raises on non-constant); 12-file annotation pass with runtime branches untouched; Nyloc `from_size` override; `_VALUE_DOC` in both lego cutters; `SCHEMA_VERSION="1.1"` (validator imports it); R7/R8 validator assertions; 92-test suite mapping Tests rows 1–15.

### 2. Tests & Success Criteria — COMPLETE
New test file maps 1:1 to the Tests table including per-group drift guard (EQUALITY for A/B/E/voron-ruthex, SUBSET for C/D), D1 type-preservation, validator-fires-on-bad-input, schema lockstep, pure-stdlib, gen-determinism, the `:527` synthetic-`@dataclass` fixture, and inheritance regression guards. All 7 Success Criteria met.

### 3a. Emitted count 34 vs prose "37/38" — NON-BLOCKING (prose arithmetic fix)
Re-derived from shipped JSON: **exactly 34** non-null `allowed_values` (A=14, B=7, C=9, D=2, E=2), 1:1 with Coverage rows A1–A14/B1–B7/C1–C9/D1–D2/E1–E2. No missing row, **no phantom/fabricated site** (R9 / experimental-integrity upheld — developer correctly did NOT invent 3 sites to reach 37). Design's own breakdown `14+7+9+2+2` sums to 34; "37/38" are stale arithmetic. *Predicted cost if unfixed:* a future reader hunts for 3 non-existent sites or files a false coverage-gap — minutes of confusion, zero functional impact. Recommended doc fix: correct prose "37→34", "38→35" throughout the spec body (Coverage rows already correct).

### 3b. Inherited-`__init__` extractor fix — ACCEPTABLE; the extractor fix is the correct call
- **Blast radius = exactly 1 class, proven two ways:** (i) regenerated the artifact from `main`'s extractor in a clean worktree and structurally diffed (after stripping the two new keys) → 0 constructors dropped/added, 0 param-set diffs, 0 reorders, 0 retypes; (ii) instrumented the new trigger predicate across `vibe_cading/`+`parts/` → `MetricNylocNut` is the only classmethod-only, non-`@dataclass`, ancestor-`__init__`-inheriting class touched.
- **Correctness/minimality:** new private `_inherited_init_from_ancestor` + one guarded branch firing only when `constructors and not has_explicit_init`. *Restores* the 1.0 shape, genuinely additive.
- **Adjudication:** the extractor fix is the honest, anti-duct-tape choice over a model-local explicit `__init__` (which would duplicate a parent signature that can drift and is a model change motivated by a tooling artifact). The old "inherit ctors only if zero own ctors" rule was a pre-existing latent extractor defect that T4a merely surfaced. Two regression guards red-fail if the inherited-init pass is removed. Approved.

### 4. Whole-artifact 1.0-consumer-safety — PASS (exclusively additive)
+1683-line `engine_api.json` diff proven exclusively additive via structural diff vs a fresh 1.0 baseline across all 65 classes: every param gains both new keys immediately after `units` (0 missing, 0 order violations); **0 params** had any 1.0 key removed/renamed/retyped/reordered; **0 D1 retypes** (every enum param emits `type:"str"`, never `"Literal[...]"`). Raw-byte spot-checks: in-scope `MetricMachineScrew.from_size(head_type)`, non-scope `TechnicPinHole.depth`, numeric `MetricHexNut.thread_diameter`, restored Nyloc `__init__`.

### 5. Workspace hygiene — CLEAN
Scoped commit (12 model files + extractor + validator + new test + regenerated JSON); no `build.toml` change; no stray `tmp/` committed; AGPLv3 header on new test; no `ocp_vscode`/`__main__` violations; no concurrent-edit sweep-in.

### Issues for the developer
**None blocking.** One non-blocking doc follow-up: correct the prose "37/38" emitted/enumerated totals to "34/35" (text-only).

---

## Independent TL Review (fresh context, 2026-06-04)

**Verdict:** `APPROVE-WITH-CONDITIONS`

The design is architecturally sound and the change is genuinely additive / 1.0-consumer-safe. Every file:line citation, the `fit` reconciliation, all 14 size-dict authorities, the Nyloc inheritance lie, the case-normalization wrinkles, and the `_split_literal` AST mechanism were independently verified at the cited locations and (for the extraction mechanism) empirically reproduced — all held. The single substantive defect is that the D3 drift-guard, as described, does **not** actually pin the `drive_type` and `type_` groups: their runtime authorities are not closed-set raising gates, so the "construct each member, assert no `ValueError`" test is a tautology that would pass for any string. This must be re-specified before the Developer builds the test, or the drift-resistance NFC (the whole point of D3) is silently unmet for ~11 of 38 sites. A secondary authority-spec bug (`ToleranceProfile` fields include `name`) must also be corrected. Both are tightening edits, not re-architecture — hence APPROVE-WITH-CONDITIONS.

**Strengths**
1. The Round-1 `fit` reconciliation is a high-value catch and is correct against the live artifact: the only emitted `fit` params are `TechnicPinHole.__init__(fit)` / `TechnicAxleHole.__init__(fit)`; screw `to_cutter(fit=...)` is an instance method the extractor never walks. Scope was correctly steered off a non-emitted surface.
2. D1 (`Literal[...]` → `type:"str"` + `allowed_values`, intercepting the subscript before `ast.unparse`) is the right call for 1.0-consumer safety, and the AST mechanism was empirically validated for inline / `typing.Literal` / single-member / `from __future__ import annotations` / dotted-string-member cases plus the loud-fail path. No retype reaches a 1.0 `type` reader.
3. The Nyloc inheritance lie (A10) is correctly diagnosed (`MetricNylocNut.DIMENSIONS` lacks `"M2"`; `from_size` is inherited and emitted live) and the override fix (T4a) is the honest-contract resolution rather than papering over a superset.

**Conditions / required edits**
1. **Re-specify the D3 drift authority for `drive_type` (C1–C9) — the described test pins nothing.** Verified at `vibe_cading/mechanical/screws/metric.py:77-88`: the drive if/elif is guarded by `if drive_type and "drive_size" in data:` and has **no `else: raise`** — an unknown `drive_type` silently yields `drive=None`. Sibling screws (imperial:43, plastics:50, setscrew:42, wood:53) merely *store* `drive_type`. So the C1/C2 table cells citing "metric `from_size` drive if/elif" as a runtime authority are misleading, and the D3 test prescription "assert each `Literal` member constructs without `ValueError`" passes for *any* string and provides **zero drift protection** for the entire `drive_type` group. Fix: state explicitly that **all** of C1–C9 use the brief-pinned canonical `FastenerDrive`-subclass tuple as authority (not a runtime branch), and change the test assertion for this group to `set(Literal members) ⊆ {canonical drive names}` plus a guard that the canonical tuple equals the set of concrete `FastenerDrive` subclasses — never "no ValueError". (The C3–C9 note already half-says this; the correction is to extend it to C1/C2 and remove the "no ValueError" mechanism for the whole group.)
2. **Fix the `ToleranceProfile` authority expression (Group E / D3 authority-kind 3).** Verified at `vibe_cading/print_settings.py:263-266`: the dataclass fields are `name, free, slip, press`. The brief states `{f.name for f in dataclasses.fields(ToleranceProfile)}` → `{"free","slip","press"}`, but that expression actually yields `{"name","free","slip","press"}`. The drift test must filter out `name` (e.g. authority = `{f.name for f in fields(ToleranceProfile)} - {"name"}`, or an explicit grade-field allowlist). As written the test would red-fail against a correct `Literal["free","slip","press"]` because the authority set carries a spurious `"name"`. Also note `getattr(profile, fit)` does not reject `fit="name"` at runtime — so the *test*, not the runtime, is the only thing pinning the three-grade set; the authority expression must be exactly right.
3. **Soften the `type_` (D1/D2 standoff) authority claim to match Condition 1's category.** Verified at `vibe_cading/mechanical/standoffs.py:60-68`: `.solid` branches on `F-F`/`M-F`/`M-M` with **no `else: raise`** — an unknown `type_` silently produces no thread. Same weak-pinning issue as `drive_type`: the test cannot assert "constructs without `ValueError`" as a drift guard. State the authority as the brief-pinned branch-set and assert `Literal members ⊆ {branch-matched values}` (or that each member hits a distinct branch by reading the `.solid` body via AST) rather than relying on a non-existent raise.

**Open concerns** (non-blocking)
1. **`size` enum params will emit `units:"mm"` alongside string `allowed_values`.** `"size"` is in `_MM_BARE_NAMES` (`extractor.py:99`), so every `from_size(size)` param already carries `units:"mm"` today; the new `allowed_values:["M2",...]` will sit beside it. This is pre-existing and additive (not introduced here), but a consumer reading both fields sees a string-enum param flagged `mm`. *Predicted cost if it matters:* purely cosmetic on the consumer side (the enum values are unambiguous strings); no generated call fails. Leave as-is — fixing `units` inference for enum params is out of scope and would change 1.0 bytes.
2. **E3 (`TechnicPinHole.standard.fit`) conditional row.** Verified keyword-only at `technic_pin_hole.py:113-120` (`*, fit=...`); the extractor skips kwonlyargs (`extractor.py:446-451`), so `standard.fit` is **not** emitted (live artifact confirms only the two `__init__` fit sites). The design already flags E3 as likely-dropped and the drift test runs only against emitted records. *Predicted cost if mis-categorized:* a 2-line Coverage-list correction, no print/re-validation cycle. Acceptable as written.
3. **The D3 test for `head_type` IS a real guard (no condition) but only for the raising families.** Verified the head_type if/elif *does* raise for metric (`metric.py:74`), imperial (`:68`), plastics (`:71`), wood (`:46`) — so "construct each member, assert no `ValueError`" genuinely pins those sets, *and* would catch a `Literal` member the branch rejects. This is the one group where the described mechanism works as intended; no change needed. Noted so the Developer keeps the per-group distinction (head_type = real raise guard; drive_type/type_ = subset-of-canonical guard).

**Verification log** (each cited claim opened at its location)
- `extractor.py:55-60` pure-stdlib imports (`ast, sys, dataclasses, pathlib`) — **HELD**.
- `extractor.py:64` `SCHEMA_VERSION = "1.0"` — **HELD**.
- `extractor.py:127` `units` emitted always-present (`out["units"] = self.units`, null when absent) — **HELD**.
- `extractor.py:472` annotation-unparse site in `_extract_params` — **HELD** (`type_str = ast.unparse(arg.annotation) ...`).
- `extractor.py:527` dataclass-field annotation-unparse twin in `_synthesize_dataclass_init` — **HELD**.
- `extractor.py:360-423` `_collect_constructors` walks `__init__` + public classmethods, excludes `demo` (391), inherits same-module ancestor (415-422) — **HELD**; comment at 215-217 names `MetricNylocNut`.
- `extractor.py:446-451` kwonlyargs out of scope (skips `func.args.kwonlyargs`) — **HELD**.
- `extractor.py:291-323` `_base_is_abc`/`_base_is_protocol` AST shape the design mirrors for `_is_literal_subscript` — **HELD**.
- `validate_engine_api.py:42` imports `SCHEMA_VERSION` from extractor — **HELD**; pinned mismatch check at `:178` — **HELD**. Validator does **not** reject unknown keys → new fields additive-safe — **HELD**.
- `validate_engine_api.py:56` `_validate_param` is the correct insertion site for R7/R8 — **HELD**.
- `gen_engine_api.py:109-125` `--check` byte-diff gate (`existing != text`) — **HELD**; `_serialize` deterministic (`sort_keys=False` + trailing newline, `:83`) — **HELD**.
- `print_settings.py:263-266` `ToleranceProfile` fields — **HELD as `name, free, slip, press`** (note: includes `name`; see Condition 2).
- Live `engine_api.json`: `schema_version=1.0`, 65 classes; only emitted `fit` params are `TechnicAxleHole.__init__` / `TechnicPinHole.__init__`, both `type:"str"`, `default:"'slip'"` — **HELD** (confirms `fit` reconciliation + quote-wrapped default for R8a).
- Zero `Literal[...]` annotations in `vibe_cading/`+`parts/` (0 occurrences) — **HELD**.
- `from __future__ import annotations` distribution: present in `standoffs.py`, `nuts/metric.py`, `nuts/tnut.py`; absent in metric/imperial/plastics/setscrew/wood screw modules — **HELD exactly as D1 states**. PEP-563 AST-guarantee empirically confirmed (real `Subscript(Literal,...)` parsed under future-import).
- Size-dict authorities A1–A14: `METRIC_SIZES`/`IMPERIAL_SIZES`(lower-case)/`PLASTIC_SCREW_SIZES`/`SET_SCREW_SIZES`/`WOOD_SIZES`/`PhillipsDrive.PH_SIZES`/`TorxDrive.TORX_SIZES`/`MetricHexNut`/`MetricSquareNut`/`MetricNylocNut`(no `M2`)/`TNut`/`HexStandoff.DIMENSIONS`, and the `voron`/`ruthex` local `profiles` dicts — **ALL HELD** with exactly the member sets listed.
- `MetricNylocNut.from_size(size)` emitted live (inherited) — **HELD** (inheritance lie risk is real).
- head_type raising branches (metric:64-74, imperial:55-68, plastics:62-71, wood:38-46) — **HELD** (real guards).
- `drive_type` non-raising (metric:77-88 guarded, no else; siblings store-only) — **HELD** → drives Condition 1.
- `type_` non-raising (standoffs.py:60-68, no else) — **HELD** → drives Condition 3.
- Case-normalization: metric `.upper()` (:57), imperial `.lower()` (:48), wood none (:32), standoff `__init__` `.upper()` (:40) — **ALL HELD**.
- No existing extractor/wire-contract test (`tests/test_imports.py` only checks class importability; `tests/tools/` has only `test_calibrate.py`) — **HELD** (R11 premise correct); `tests/tools/` exists so the new test path is valid.
- `_split_literal` mechanism — **empirically validated** (inline multi, `typing.Literal`, single-member bare-`Constant` slice, future-import, dotted members, plain-`str` passthrough, `float|None` passthrough, loud-fail on non-constant member). Python 3.11.15 → `node.slice` is the expression directly (no `ast.Index` wrapper).
- `.github/workflows/engine-api.yml` runs `gen --check` (:46) then `validate` (:48) — **HELD** (R13 path).
- Coverage-list completeness: all 38 target sites (E3 excepted, correctly flagged conditional/kwonly) are present as emitted params in the live artifact — **HELD**.
- Tests-table R-coverage: every R1–R13 appears in ≥1 "Maps to" cell (programmatic tally) — **HELD**.

---

## Independent TL Re-Review (fresh context, 2026-06-04)

**Verdict:** `APPROVE`

The three TL conditions from the prior `## Independent TL Review` are now **correctly resolved** — not merely present, but right when checked against the live source. The general drift-guard principle (equality for hard/raising authorities, one-directional subset for silently-folding ones) is stated once in the new "D3 general drift-guard principle" subsection and applied uniformly across every in-scope group; no group is left on a tautological "no `ValueError`" test. The 37-emitted / 38-enumerated accounting and the E3 "annotated, not emitted" framing are consistent throughout the spec body. No new architectural defect was introduced by the Round-2 edits. Step 4 (human gate) may proceed.

**Per-condition resolution (original TL conditions)**
1. **`drive_type` (C1–C9) drift authority re-spec — RESOLVED.** Verified `vibe_cading/mechanical/screws/metric.py:77-88`: the drive `if/elif` is wrapped by `if drive_type and "drive_size" in data:` (line 77) with **no `else: raise`** attached to the drive chain — the only `raise` inside is the nested torx-missing-size guard (line 88); an unknown `drive_type` falls through to `return cls(...)` (line 90) with `drive=None`. So the group is genuinely silently-folding and a "no `ValueError`" test would be a tautology. The design now correctly prescribes the one-directional `set(Literal) ⊆ CANONICAL_DRIVES` with `CANONICAL_DRIVES = {"hex","phillips","slotted","torx"}` for **all** of C1–C9 (Group C intro line 252, C1/C2 cells, C-group note, D3-B table). The named authority is correct against `vibe_cading/mechanical/screws/drives.py`: the four concrete `FastenerDrive` subclasses are `HexDrive` (`:66`), `SlottedDrive` (`:87`), `PhillipsDrive` (`:106`), `TorxDrive` (`:155`), and the metric dispatch strings (`metric.py:78/80/82/84`) are exactly `hex/phillips/slotted/torx` — 1:1. Runtime confirmed `FastenerDrive.__subclasses__()` returns exactly those four, so the roster cross-check is sound.
2. **`ToleranceProfile` authority excludes `name` — RESOLVED.** Verified `vibe_cading/print_settings.py:263-266`: fields are `name, free, slip, press` (four). Runtime confirmed `dataclasses.fields(ToleranceProfile)` → `['name','free','slip','press']` and `… - {"name"}` → `{free, slip, press}`. The design's authority expression `{f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}` (D3 authority-kind-3 cell line 153, E1/E2 rows lines 281-282, T8 line 306, Tests #7 line 322) is correct, with the `- {"name"}` flagged mandatory.
3. **`type_` (D1–D2) drift authority re-spec — RESOLVED.** Verified `vibe_cading/mechanical/standoffs.py:60-68`: `.solid` branches `if type_ in ["F-F","M-F"]` (60), `if type_ in ["M-F","M-M"]` (64), `if type_ == "M-M"` (68) with **no `else: raise`** — an unknown `type_` produces a plain hex body. The accepted-branch set is exactly `{"F-F","M-F","M-M"}`. The design now prescribes one-directional `set(Literal) ⊆ {"F-F","M-F","M-M"}` (Group D intro line 270, D1/D2 cells, D3-B table). Correct.

**General-principle uniformity (the implicit fourth condition) — RESOLVED.** The "D3 general drift-guard principle" subsection (lines 160-174) states the rule once and the per-group cells apply it consistently. Spot-checked the raising-authority classification at the source: `head_type` has `else: raise` in all four families — `metric.py:73-74`, `imperial.py:67-68`, `plastics.py:70-71`, `wood.py:45-46` — so Group B's EQUALITY-by-acceptance (each member constructs + a bogus value raises) genuinely pins, not a tautology. `voron`/`ruthex` raise on missing key (`inserts.py:116-117`, `:134-135`) so the classmethod-local dict-key EQUALITY is legitimate. Group A `from_size` raises on missing dict key (`metric.py:58-59`, `standoffs.py:46-47`). Every "no `ValueError`" mention left in the spec body is used correctly — either to name-and-forbid the tautology for the folding groups, or as the valid bogus-raises half of the raising-group equality test. No in-scope group is on a test that pins nothing.

**No new defect / accounting consistency — CONFIRMED.** Grepped every `37`/`38`/`E3` mention: the spec body uniformly states 38 enumerated sites, E3 the one kwonly annotation-only site, 37 emitted (A14·B7·C9·D2·E2) — consistent at lines 287, 301, 306, 322, 336, 385, 441, 445. E3 is consistently "annotated for IDE, NOT emitted" (E3 row line 283/285, non-blocking concern #1 line 385). The historical "34/35 emit" figure at line 515 lives inside the prior Developer-review section (a pre-reconciliation reviewer tally), not the live spec accounting, so it is not an inconsistency in the design body. The Round-2 edits are test-specification precision only — architecture, coverage set, schema-1.1 wire shape, and Implementation-Plan task structure are unchanged.

**Verification log (source re-opened this re-review)**
- `vibe_cading/mechanical/screws/metric.py:55-99` — head_type if/elif `else: raise` at `:73-74` (Group B raises); drive if/elif at `:77-88` guarded by `if drive_type and "drive_size" in data:`, **no `else: raise`** on the drive chain, unknown → `drive=None`, falls to `return cls(...)` `:90` — **Condition 1 HELD**.
- `vibe_cading/mechanical/screws/drives.py` — `FastenerDrive` ABC `:44`; four concrete subclasses `HexDrive:66`, `SlottedDrive:87`, `PhillipsDrive:106`, `TorxDrive:155` — `CANONICAL_DRIVES` 1:1 with the dispatch strings — **HELD**.
- `vibe_cading/print_settings.py:263-266` — `ToleranceProfile` fields `name, free, slip, press`; runtime `fields() - {"name"} == {free,slip,press}` — **Condition 2 HELD**.
- `vibe_cading/mechanical/standoffs.py:40-73` — `.solid` `:60-68` branches `F-F`/`M-F`/`M-M`, **no `else: raise`**; `__init__` `.upper()`-normalizes `type_` `:40` — **Condition 3 HELD**.
- `vibe_cading/mechanical/screws/imperial.py:67-68`, `plastics.py:70-71`, `wood.py:45-46` — head_type `else: raise` present in each — Group B raising-authority classification **HELD**.
- `vibe_cading/mechanical/inserts.py:107-118`, `:121-136` — `voron`/`ruthex` raise on missing key (`:116-117`, `:134-135`) — voron/ruthex EQUALITY authority **HELD**.
- Runtime: `dataclasses.fields(ToleranceProfile)` and `FastenerDrive.__subclasses__()` — both as the spec states.
- Design-body grep of `37`/`38`/`E3` — accounting consistent; E3 uniformly "annotated, not emitted".

**Remaining blocker:** none. All three TL conditions correctly resolved; no new blocker.

---

## Independent Developer Re-Review (fresh context, 2026-06-04)

**Verdict: APPROVE**

All four Developer-side conditions from the prior `## Independent Developer Review` (`APPROVE-WITH-CONDITIONS`) are now **correctly resolved** — not merely present in the text, but implementable exactly as written against the real source. I re-opened every cited location, ran two empirical probes against the live `engine_api.json`, and confirmed each fix is buildable with no new blocker introduced by the Round-2 edits. The Implementation Plan (T1–T11) still executes top-to-bottom, and the R-coverage audit (line 332) still maps every R1–R13 to a concrete, writable test row. The approach, coverage set (37 emitted + E3 annotation-only), and schema-1.1 wire shape are unchanged.

### Per-condition resolution (one line each)

1. **`ToleranceProfile` field-set excludes `name` — RESOLVED.** Verified `print_settings.py:263-266`: the `@dataclass ToleranceProfile` fields are exactly `name, free, slip, press` (four). The D3 authority-kind-3 cell, the E1/E2 authority column, the T8 spec, Tests #7, and the risk table all now read `{f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}` → `{free,slip,press}`; the unfiltered set would have red-failed a correct `Literal["free","slip","press"]`. The `- {"name"}` correction is consistent everywhere the lego-`fit` authority appears.

2. **`:527` synthesized-dataclass path noted in T1; T9(d) calls for a dedicated synthetic fixture — RESOLVED.** Verified no in-scope coverage class is a synthesized `@dataclass`: the four `@dataclass` hits under `vibe_cading/mechanical/` are all in `enclosures/` (`pcb_standoff`, `knob`, `ventilation`, `zip_tie`) — none is a Coverage-list row; every in-scope class (`MetricMachineScrew`, `MetricHexNut`, `HeatSetInsert`, `HexStandoff`, `TechnicPinHole`, `TechnicAxleHole`, …) is a plain class with an explicit `__init__` flowing through `_extract_params` (`:472`). T1 now states wiring `:527` is correct + harmless + changes zero in-scope bytes; T9(d) correctly requires a dedicated synthetic `@dataclass` fixture (the `:527` path cannot be driven by any Coverage row). The implementer will not hunt for a non-existent in-scope dataclass site.

3. **E3 (`TechnicPinHole.standard.fit`) consistently "annotated, not emitted"; 37 emitted / 38 enumerated reconciled — RESOLVED.** Confirmed `standard(cls, depth, *, fit=..., …)` is keyword-only (`technic_pin_hole.py:114-120`), the extractor skips `kwonlyargs` (`:446-451`), and a live-artifact probe shows exactly two `fit` rows (`TechnicAxleHole.__init__`, `TechnicPinHole.__init__`) with no `standard.fit`. Every active-body site that mentions the count (Coverage E3 row + note, count paragraph at 287, T4, T8, Tests #7, Success Criterion #1, non-blocking concern #1, Round-2 conditions log) consistently says "38 enumerated / 37 emitted, E3 annotation-only, excluded from all wire-facing checks." (The lone stale "34/35" / "38 target sites" strings are inside the *prior review sections* — historical records of what those reviewers found pre-correction — and are immaterial to the corrected spec body; not retroactively edited.)

4. **`drive_type` / `type_` drift tests are one-directional subset assertions against named authorities — RESOLVED.** Verified the metric drive branch (`screws/metric.py:77-88`) has **no `else: raise`** on the drive chain (unknown `drive_type` → `drive=None`, falls to `return cls(...)`) and the standoff `.solid` branches (`standoffs.py:60-68`) have **no `else: raise`** (unknown `type_` → plain hex body) — so the old "no `ValueError`" form would indeed have been a tautology pinning nothing. The re-spec is concretely writable against the real runtime authorities: Group C asserts `set(Literal) ⊆ CANONICAL_DRIVES = {"hex","phillips","slotted","torx"}` cross-checked against `FastenerDrive.__subclasses__()` — confirmed exactly four concrete subclasses `{HexDrive, PhillipsDrive, SlottedDrive, TorxDrive}` (`drives.py:66/87/106/155`); Group D asserts `set(Literal) ⊆ {"F-F","M-F","M-M"}` (the `.solid` accepted-branch literals). The contrast groups remain genuine EQUALITY authorities: `head_type` raises in metric/imperial/plastics/wood (`imperial.py:68`, `plastics.py:71`, `wood.py:46`) and `voron`/`ruthex` raise on a missing key (`inserts.py:116-117`, `:134-135`) — so set-EQUALITY-by-acceptance is correctly writable for those.

### Plan-integrity & coverage re-check
- T1–T11 read end-to-end with no ordering gap introduced by the Round-2 edits: extractor plumbing (T1) → `Param` fields/emission (T2) → `value_doc` plumbing (T3) → annotation pass + Nyloc override (T4/T4a) → `_VALUE_DOC` authoring (T5) → schema bump (T6) → validator (T7) → drift test (T8) → populate/negative/`:527`-fixture tests (T9) → regenerate+commit (T10) → full-suite gate (T11). Every R1–R13 maps to ≥1 concrete writable test row per the audit at line 332. No new blocker.

### Verification log (source re-opened this re-review)
| Re-checked claim | Location | Held? |
|---|---|---|
| `ToleranceProfile` fields are `name, free, slip, press` (four) | `print_settings.py:263-266` | ✓ — `name` field #1; `- {"name"}` mandatory |
| `:472` `_extract_params` + `:527` `_synthesize_dataclass_init` unparse sites exist | `extractor.py:472,527` | ✓ exact |
| no in-scope coverage class is a synthesized `@dataclass` | `vibe_cading/mechanical/`, lego cutters | ✓ — 4 `@dataclass` all under `enclosures/`, none in Coverage list |
| `standard.fit` keyword-only; kwonlyargs skipped | `technic_pin_hole.py:114-120`, `extractor.py:446-451` | ✓ |
| live artifact emits exactly 2 `fit` rows, no `standard.fit` | live `engine_api.json` probe | ✓ — `TechnicAxleHole.__init__`, `TechnicPinHole.__init__` only |
| metric drive branch has NO `else: raise` (tautology risk real) | `screws/metric.py:77-88` | ✓ — unknown → `drive=None` |
| standoff `.solid` branches have NO `else: raise` | `standoffs.py:60-68` | ✓ — unknown → plain hex |
| `FastenerDrive` has exactly 4 concrete subclasses = `CANONICAL_DRIVES` | `screws/drives.py:66/87/106/155` | ✓ — Hex/Slotted/Phillips/Torx |
| `head_type` raises in imperial/plastics/wood (EQUALITY authority real) | `imperial.py:68`, `plastics.py:71`, `wood.py:46` | ✓ |
| `voron`/`ruthex` raise on missing key (EQUALITY authority real) | `inserts.py:116-117`, `:134-135` | ✓ |
| 37/38 reconciliation consistent across active spec body | design body (lines 287, 301, 306, 322, 336, 385) | ✓ — uniform; stale strings only in prior-review sections |

Conclusion: every Developer condition is correctly resolved and the plan is buildable with no new blocker. Verdict **APPROVE**.
