# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# vibe-cading is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for the engine_api schema 1.1 ``allowed_values`` + ``value_doc`` fields.

Covers the design's Tests table (rows 1–15) for
``.agents/plans/2026-06-04-engine-api-allowed-values_design.md``:

* extractor populate / negative / 1.0-``type`` preservation (T9 a/b/c);
* the ``_synthesize_dataclass_init`` synthetic-``@dataclass`` fixture (T9d);
* the per-group drift guard (T8) — set-EQUALITY for closed/raising
  authorities (Groups A/B/E + voron/ruthex), one-directional SUBSET for
  silently-folding authorities (Groups C ``drive_type`` / D ``type_``);
* the new validator R7/R8 assertions firing on crafted bad input (T7);
* the schema-version lockstep bump (T6); pure-stdlib import set (R12);
* the always-present null-key emission convention (D4); and
* ``gen --check`` byte-determinism (R5/R10).

The drift guard reads each emitted record's declared ``allowed_values``
straight from the regenerated artifact and pins it to its *runtime*
authority (dict keys / dataclass fields / raising branches) so a
contributor who edits a runtime dict but forgets the ``Literal`` (or
vice-versa) red-fails CI.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vibe_cading.tools.engine_api import extractor as E  # noqa: E402
from vibe_cading.tools.engine_api.extractor import (  # noqa: E402
    SCHEMA_VERSION,
    extract_classes,
)
import vibe_cading.tools.validate_engine_api as V  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: the live engine_api.json + a freshly-extracted record set
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artifact() -> dict:
    """The committed ``engine_api.json`` payload."""
    return json.loads(
        (_REPO_ROOT / "vibe_cading" / "engine_api.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def records() -> list:
    """Freshly extracted class records (independent of the committed file)."""
    roots = [
        d
        for d in (_REPO_ROOT / "vibe_cading", _REPO_ROOT / "parts")
        if d.exists()
    ]
    return extract_classes(roots)


def _emitted_params(payload: dict) -> dict[tuple[str, str, str], dict]:
    """Index every emitted param by ``(short_class, ctor_name, param_name)``."""
    out: dict[tuple[str, str, str], dict] = {}
    for c in payload["classes"]:
        short = c["fqn"].split(".")[-1]
        for ctor in c["constructors"]:
            for p in ctor["params"]:
                out[(short, ctor["name"], p["name"])] = p
    return out


def _find_param(records: list, fqn_tail: str, ctor_name: str, param: str) -> dict:
    for rec in records:
        if rec.fqn.split(".")[-1] != fqn_tail:
            continue
        for ctor in rec.constructors:
            if ctor.name != ctor_name:
                continue
            for p in ctor.params:
                if p.name == param:
                    return p.to_dict()
    raise AssertionError(f"param {fqn_tail}.{ctor_name}({param}) not found")


# ---------------------------------------------------------------------------
# Coverage list — the authoritative emitted-site contract (design Coverage list).
# Each entry: (short_class, ctor_name, param) -> ordered Literal member list.
# E3 (TechnicPinHole.standard.fit) is kwonly → NOT emitted → NOT listed here.
# ---------------------------------------------------------------------------

# Group A — size families (dict-key / classmethod-local-dict authority → EQUALITY)
_GROUP_A: dict[tuple[str, str, str], list[str]] = {
    ("MetricMachineScrew", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "M5"],
    ("ImperialMachineScrew", "from_size", "size"): ["4-40", "6-32", "8-32", "10-24", "1/4-20"],
    ("PlasticsScrew", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "M5"],
    ("SetScrew", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "M5"],
    ("WoodScrew", "__init__", "size"): ["#2", "#4", "#6", "#8", "#10", "3/16"],
    ("PhillipsDrive", "from_size", "size"): ["PH00", "PH0", "PH1", "PH2", "PH3"],
    ("TorxDrive", "from_size", "size"): ["T5", "T6", "T8", "T10", "T15", "T20", "T25", "T30"],
    ("MetricHexNut", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "M5", "M6", "M8"],
    ("MetricSquareNut", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "M5", "M6"],
    ("MetricNylocNut", "from_size", "size"): ["M2.5", "M3", "M4", "M5", "M6", "M8"],
    ("TNut", "from_size", "size"): ["M3", "M4", "M5"],
    ("HexStandoff", "from_size", "size"): ["M2", "M2.5", "M3", "M4", "4-40", "6-32"],
    ("HeatSetInsert", "voron", "size"): ["M3", "M4"],
    ("HeatSetInsert", "ruthex", "size"): ["M2", "M2.5", "M3", "M3_short", "M4", "M5"],
}

# Group B — head_type (raising if/elif → EQUALITY-by-acceptance)
_GROUP_B: dict[tuple[str, str, str], list[str]] = {
    ("MetricMachineScrew", "__init__", "head_type"): ["socket", "flat", "pan"],
    ("MetricMachineScrew", "from_size", "head_type"): ["socket", "flat", "pan"],
    ("ImperialMachineScrew", "__init__", "head_type"): ["socket", "flat", "pan"],
    ("ImperialMachineScrew", "from_size", "head_type"): ["socket", "flat", "pan"],
    ("PlasticsScrew", "__init__", "head_type"): ["pan", "flat"],
    ("PlasticsScrew", "from_size", "head_type"): ["pan", "flat"],
    ("WoodScrew", "__init__", "head_type"): ["flat", "pan"],
}

# Group C — drive_type (silently-folding → SUBSET ⊆ CANONICAL_DRIVES)
_GROUP_C: dict[tuple[str, str, str], list[str]] = {
    ("MetricMachineScrew", "__init__", "drive_type"): ["hex", "phillips", "slotted", "torx"],
    ("MetricMachineScrew", "from_size", "drive_type"): ["hex", "phillips", "slotted", "torx"],
    ("ImperialMachineScrew", "__init__", "drive_type"): ["hex", "phillips", "slotted", "torx"],
    ("ImperialMachineScrew", "from_size", "drive_type"): ["hex", "phillips", "slotted", "torx"],
    ("PlasticsScrew", "__init__", "drive_type"): ["phillips", "hex", "slotted", "torx"],
    ("PlasticsScrew", "from_size", "drive_type"): ["phillips", "hex", "slotted", "torx"],
    ("SetScrew", "__init__", "drive_type"): ["hex", "slotted", "torx"],
    ("SetScrew", "from_size", "drive_type"): ["hex", "slotted", "torx"],
    ("WoodScrew", "__init__", "drive_type"): ["phillips", "hex", "slotted", "torx"],
}

# Group D — type_ (silently-folding → SUBSET ⊆ {F-F, M-F, M-M})
_GROUP_D: dict[tuple[str, str, str], list[str]] = {
    ("HexStandoff", "__init__", "type_"): ["F-F", "M-F", "M-M"],
    ("HexStandoff", "from_size", "type_"): ["F-F", "M-F", "M-M"],
}

# Group E — fit (ToleranceProfile grade fields → EQUALITY; emitted sites only)
_GROUP_E: dict[tuple[str, str, str], list[str]] = {
    ("TechnicPinHole", "__init__", "fit"): ["free", "slip", "press"],
    ("TechnicAxleHole", "__init__", "fit"): ["free", "slip", "press"],
}

_ALL_EMITTED = {**_GROUP_A, **_GROUP_B, **_GROUP_C, **_GROUP_D, **_GROUP_E}


# ---------------------------------------------------------------------------
# Tests-table row 1 / 6 — populate + 1.0-`type` preservation (D1)
# ---------------------------------------------------------------------------


def test_in_scope_param_emits_declared_set(records):
    """Row 1 (R1/R3/R11): an in-scope param emits its exact ordered set."""
    p = _find_param(records, "MetricMachineScrew", "from_size", "size")
    assert p["allowed_values"] == ["M2", "M2.5", "M3", "M4", "M5"]
    assert p["type"] == "str"


def test_literal_param_preserves_str_type(records):
    """Row 6 (D1/R6): a Literal param emits base type, NOT 'Literal[...]'."""
    p = _find_param(records, "MetricMachineScrew", "from_size", "head_type")
    assert p["type"] == "str"  # NOT "Literal['socket', 'flat', 'pan']"
    assert p["allowed_values"] == ["socket", "flat", "pan"]


# ---------------------------------------------------------------------------
# Tests-table row 2 — free-form `str` param emits null
# ---------------------------------------------------------------------------


def test_free_form_str_param_emits_null(records):
    """Row 2 (R1/R9/R11): a non-enum str param emits both new keys null."""
    # `name` on MetricMachineScrew has no Literal — free-form (but it does
    # not exist); use a plain str param: CounterboreHole.__init__(head_type)
    # is internal free-form (design: stays null).
    p = _find_param(records, "CounterboreHole", "__init__", "head_type")
    assert p["allowed_values"] is None
    assert p["value_doc"] is None


# ---------------------------------------------------------------------------
# Tests-table rows 3 / 4 — value_doc present only with allowed_values; from
# the co-located _VALUE_DOC; keys ⊆ allowed_values
# ---------------------------------------------------------------------------


def test_value_doc_only_with_allowed_values_and_keys_subset(records):
    """Row 3 (R2/R4): fit record's value_doc keys ⊆ allowed_values."""
    p = _find_param(records, "TechnicPinHole", "__init__", "fit")
    assert p["allowed_values"] == ["free", "slip", "press"]
    assert p["value_doc"] is not None
    assert set(p["value_doc"]).issubset(set(p["allowed_values"]))


def test_value_doc_derives_from_colocated_module_dict(records):
    """Row 4 (R4/D5): emitted value_doc equals the module's _VALUE_DOC entry."""
    mod = importlib.import_module(
        "vibe_cading.lego.cutters.technic_pin_hole"
    )
    expected = mod._VALUE_DOC["TechnicPinHole.fit"]
    p = _find_param(records, "TechnicPinHole", "__init__", "fit")
    assert p["value_doc"] == expected


# ---------------------------------------------------------------------------
# Tests-table row 5 — always-present null keys, positioned after `units`
# ---------------------------------------------------------------------------


def test_emission_keys_always_present_after_units(artifact):
    """Row 5 (R5/D4): every param carries the two keys right after `units`."""
    for c in artifact["classes"]:
        for ctor in c["constructors"]:
            for p in ctor["params"]:
                assert "allowed_values" in p
                assert "value_doc" in p
                keys = list(p.keys())
                u = keys.index("units")
                assert keys[u + 1] == "allowed_values"
                assert keys[u + 2] == "value_doc"


# ---------------------------------------------------------------------------
# Tests-table row 7 — the per-group drift guard (T8)
# ---------------------------------------------------------------------------


def _ast_literal_members(module: str, cls: str, ctor: str, param: str) -> list:
    """Read a param's declared Literal members straight from the source AST.

    Mirrors what the extractor reads — proves the artifact is faithful to
    the annotation, not a stale committed copy.
    """
    mod = importlib.import_module(module)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == ctor:
                    for arg in child.args.args:
                        if arg.arg == param and E._is_literal_subscript(arg.annotation):
                            return E._literal_members(arg.annotation)
    raise AssertionError(f"no Literal for {module}.{cls}.{ctor}({param})")


# --- Group A: dict-key / classmethod-local-dict authority → set-EQUALITY ---

# Map each Group-A site to (module, runtime-authority-callable).
def _dict_keys(dotted: str):
    """Resolve ``module:DICT`` or ``module:Class.ATTR`` to its key set."""
    mod_name, _, tail = dotted.partition(":")
    obj = importlib.import_module(mod_name)
    for part in tail.split("."):
        obj = getattr(obj, part)
    return set(obj.keys())


_GROUP_A_AUTHORITY = {
    ("MetricMachineScrew", "from_size", "size"):
        "vibe_cading.mechanical.screws.metric:METRIC_SIZES",
    ("ImperialMachineScrew", "from_size", "size"):
        "vibe_cading.mechanical.screws.imperial:IMPERIAL_SIZES",
    ("PlasticsScrew", "from_size", "size"):
        "vibe_cading.mechanical.screws.plastics:PLASTIC_SCREW_SIZES",
    ("SetScrew", "from_size", "size"):
        "vibe_cading.mechanical.screws.setscrew:SET_SCREW_SIZES",
    ("WoodScrew", "__init__", "size"):
        "vibe_cading.mechanical.screws.wood:WOOD_SIZES",
    ("PhillipsDrive", "from_size", "size"):
        "vibe_cading.mechanical.screws.drives:PhillipsDrive.PH_SIZES",
    ("TorxDrive", "from_size", "size"):
        "vibe_cading.mechanical.screws.drives:TorxDrive.TORX_SIZES",
    ("MetricHexNut", "from_size", "size"):
        "vibe_cading.mechanical.nuts.metric:MetricHexNut.DIMENSIONS",
    ("MetricSquareNut", "from_size", "size"):
        "vibe_cading.mechanical.nuts.metric:MetricSquareNut.DIMENSIONS",
    ("MetricNylocNut", "from_size", "size"):
        "vibe_cading.mechanical.nuts.metric:MetricNylocNut.DIMENSIONS",
    ("TNut", "from_size", "size"):
        "vibe_cading.mechanical.nuts.tnut:TNut.DIMENSIONS",
    ("HexStandoff", "from_size", "size"):
        "vibe_cading.mechanical.standoffs:HexStandoff.DIMENSIONS",
}


@pytest.mark.parametrize("site", sorted(_GROUP_A_AUTHORITY))
def test_drift_group_a_dict_key_equality(site, artifact):
    """Row 7 (Group A): declared Literal == runtime dict-key authority."""
    declared = set(_emitted_params(artifact)[site]["allowed_values"])
    authority = _dict_keys(_GROUP_A_AUTHORITY[site])
    assert declared == authority, (
        f"{site}: Literal {sorted(declared)} != dict keys {sorted(authority)}"
    )


def _classmethod_local_dict_keys(module: str, cls: str, method: str, var: str) -> set:
    """Read a classmethod-body local dict's keys via AST (voron/ruthex)."""
    mod = importlib.import_module(module)
    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method:
                    for stmt in ast.walk(child):
                        if (
                            isinstance(stmt, ast.Assign)
                            and any(
                                isinstance(t, ast.Name) and t.id == var
                                for t in stmt.targets
                            )
                            and isinstance(stmt.value, ast.Dict)
                        ):
                            return {
                                k.value
                                for k in stmt.value.keys
                                if isinstance(k, ast.Constant)
                            }
    raise AssertionError(f"no local dict {var} in {cls}.{method}")


@pytest.mark.parametrize("method", ["voron", "ruthex"])
def test_drift_group_a_insert_local_dict_equality(method, artifact):
    """Row 7 (Group A — voron/ruthex): Literal == classmethod-local dict keys."""
    declared = set(_emitted_params(artifact)[("HeatSetInsert", method, "size")]["allowed_values"])
    authority = _classmethod_local_dict_keys(
        "vibe_cading.mechanical.inserts", "HeatSetInsert", method, "profiles"
    )
    assert declared == authority


# --- Group B: raising head if/elif → EQUALITY-by-acceptance ---

_GROUP_B_FACTORY = {
    ("MetricMachineScrew", "__init__", "head_type"): (
        "vibe_cading.mechanical.screws.metric", "MetricMachineScrew",
        lambda C, ht: C.from_size("M3", 10, head_type=ht),
    ),
    ("MetricMachineScrew", "from_size", "head_type"): (
        "vibe_cading.mechanical.screws.metric", "MetricMachineScrew",
        lambda C, ht: C.from_size("M3", 10, head_type=ht),
    ),
    ("ImperialMachineScrew", "__init__", "head_type"): (
        "vibe_cading.mechanical.screws.imperial", "ImperialMachineScrew",
        lambda C, ht: C.from_size("4-40", 10, head_type=ht),
    ),
    ("ImperialMachineScrew", "from_size", "head_type"): (
        "vibe_cading.mechanical.screws.imperial", "ImperialMachineScrew",
        lambda C, ht: C.from_size("4-40", 10, head_type=ht),
    ),
    ("PlasticsScrew", "__init__", "head_type"): (
        "vibe_cading.mechanical.screws.plastics", "PlasticsScrew",
        lambda C, ht: C.from_size("M3", 10, head_type=ht),
    ),
    ("PlasticsScrew", "from_size", "head_type"): (
        "vibe_cading.mechanical.screws.plastics", "PlasticsScrew",
        lambda C, ht: C.from_size("M3", 10, head_type=ht),
    ),
    ("WoodScrew", "__init__", "head_type"): (
        "vibe_cading.mechanical.screws.wood", "WoodScrew",
        lambda C, ht: C("#6", 10, head_type=ht),
    ),
}


@pytest.mark.parametrize("site", sorted(_GROUP_B_FACTORY))
def test_drift_group_b_head_type_equality_by_acceptance(site, artifact):
    """Row 7 (Group B): every Literal head_type constructs; a bogus value raises.

    EQUALITY-by-acceptance — the head if/elif has ``else: raise`` so the
    accepted set is closed; the Literal members must all construct AND a
    deliberately-bogus value must raise (proving the declared set is
    exactly the accepted set, not a subset).
    """
    module, cls_name, builder = _GROUP_B_FACTORY[site]
    C = getattr(importlib.import_module(module), cls_name)
    declared = _emitted_params(artifact)[site]["allowed_values"]
    for member in declared:
        builder(C, member)  # must not raise
    with pytest.raises(ValueError):
        builder(C, "definitely-not-a-head-type")


# --- Group C: silently-folding drive_type → SUBSET ⊆ CANONICAL_DRIVES ---

CANONICAL_DRIVES = {"hex", "phillips", "slotted", "torx"}


def test_canonical_drives_tracks_fastener_subclass_roster():
    """Row 7 (Group C authority pin): CANONICAL_DRIVES == FastenerDrive roster.

    Pins the co-located canonical tuple to the live concrete-subclass set
    so it cannot silently drift from the drive family.
    """
    from vibe_cading.mechanical.screws.drives import (
        FastenerDrive, HexDrive, PhillipsDrive, SlottedDrive, TorxDrive,
    )
    # Force the four concretes to be imported/registered before reading
    # __subclasses__ (they are imported on the line above).
    _ = (HexDrive, PhillipsDrive, SlottedDrive, TorxDrive)
    subclasses = set(FastenerDrive.__subclasses__())
    assert subclasses == {HexDrive, PhillipsDrive, SlottedDrive, TorxDrive}
    assert len(CANONICAL_DRIVES) == 4


@pytest.mark.parametrize("site", sorted(_GROUP_C))
def test_drift_group_c_drive_type_subset(site, artifact):
    """Row 7 (Group C): declared drive_type ⊆ CANONICAL_DRIVES (one-directional)."""
    declared = set(_emitted_params(artifact)[site]["allowed_values"])
    assert declared.issubset(CANONICAL_DRIVES), (
        f"{site}: {sorted(declared)} not ⊆ {sorted(CANONICAL_DRIVES)}"
    )


# --- Group D: silently-folding type_ → SUBSET ⊆ standoff .solid branch set ---

STANDOFF_TYPES = {"F-F", "M-F", "M-M"}


@pytest.mark.parametrize("site", sorted(_GROUP_D))
def test_drift_group_d_type_subset(site, artifact):
    """Row 7 (Group D): declared type_ ⊆ {F-F, M-F, M-M} (one-directional)."""
    declared = set(_emitted_params(artifact)[site]["allowed_values"])
    assert declared.issubset(STANDOFF_TYPES), (
        f"{site}: {sorted(declared)} not ⊆ {sorted(STANDOFF_TYPES)}"
    )


# --- Group E: ToleranceProfile grade fields → EQUALITY (name subtracted) ---


@pytest.mark.parametrize("site", sorted(_GROUP_E))
def test_drift_group_e_fit_grade_equality(site, artifact):
    """Row 7 (Group E): declared fit == ToleranceProfile grade fields - {name}.

    ``dataclasses.fields(ToleranceProfile)`` returns FOUR fields
    ``(name, free, slip, press)`` — ``name`` MUST be subtracted or this
    equality would red-fail a correct ``Literal['free','slip','press']``.
    """
    from vibe_cading.print_settings import ToleranceProfile
    grades = {f.name for f in dataclasses.fields(ToleranceProfile)} - {"name"}
    declared = set(_emitted_params(artifact)[site]["allowed_values"])
    assert declared == grades, (
        f"{site}: fit Literal {sorted(declared)} != grade fields {sorted(grades)}"
    )


# --- Cross-check: the declared Literal AST matches the emitted artifact ---


@pytest.mark.parametrize("site", sorted(_ALL_EMITTED))
def test_artifact_matches_source_literal(site, artifact):
    """Every emitted allowed_values equals the source-AST Literal members.

    Catches a stale committed artifact: the committed bytes must equal what
    the annotation actually declares today.
    """
    short, ctor, param = site
    p = _emitted_params(artifact).get(site)
    assert p is not None, f"{site} not emitted in artifact"
    assert p["allowed_values"] == _ALL_EMITTED[site]


def test_emitted_site_count(artifact):
    """The artifact emits exactly the Coverage-list emitted-site set.

    34 emitted sites = Coverage Groups A(14)+B(7)+C(9)+D(2)+E(2); E3
    (TechnicPinHole.standard.fit) is keyword-only → not emitted.
    """
    emitted = {
        site
        for site, p in _emitted_params(artifact).items()
        if p.get("allowed_values") is not None
    }
    assert emitted == set(_ALL_EMITTED), (
        f"missing: {set(_ALL_EMITTED) - emitted}; "
        f"extra: {emitted - set(_ALL_EMITTED)}"
    )
    assert len(emitted) == 34


def test_standard_fit_kwonly_not_emitted(artifact):
    """E3: TechnicPinHole.standard.fit is keyword-only → NOT emitted."""
    params = _emitted_params(artifact)
    assert ("TechnicPinHole", "standard", "fit") not in params


def test_nyloc_override_excludes_m2(artifact):
    """Row 8 (D3): MetricNylocNut.from_size advertises Nyloc DIMENSIONS, not hex.

    Proves the T4a override eliminated the inherited 'M2' lie.
    """
    from vibe_cading.mechanical.nuts.metric import MetricNylocNut
    declared = _emitted_params(artifact)[("MetricNylocNut", "from_size", "size")]["allowed_values"]
    assert "M2" not in declared
    assert set(declared) == set(MetricNylocNut.DIMENSIONS.keys())


def test_nyloc_override_preserves_inherited_init(artifact):
    """Post-fix hardening: adding the T4a `from_size` override must NOT drop
    the inherited `__init__` from the wire record.

    ``MetricNylocNut`` defines only a ``from_size`` classmethod but inherits
    ``MetricHexNut.__init__``.  The extractor's per-class collection
    short-circuits once any own constructor exists; without an explicit
    inherited-init pass, adding ``from_size`` would silently drop the
    inherited ``__init__`` (present in schema 1.0) — an additive-contract
    violation.  This guards that the inherited ``__init__`` is still emitted
    with its parent's three params.
    """
    nyloc = next(
        c for c in artifact["classes"] if c["fqn"].endswith("MetricNylocNut")
    )
    kinds = {(ctor["kind"], ctor["name"]) for ctor in nyloc["constructors"]}
    assert ("init", "__init__") in kinds
    assert ("classmethod", "from_size") in kinds
    init = next(
        ctor for ctor in nyloc["constructors"] if ctor["name"] == "__init__"
    )
    # Inherited from MetricHexNut.__init__(width_flats, thickness, thread_diameter).
    assert [p["name"] for p in init["params"]] == [
        "width_flats", "thickness", "thread_diameter",
    ]
    # The inherited init params carry no Literal → free-form.
    for p in init["params"]:
        assert p["allowed_values"] is None


# ---------------------------------------------------------------------------
# Tests-table row 9–11 — validator R7/R8 assertions fire on crafted bad input
# ---------------------------------------------------------------------------


def _make_param(**overrides) -> dict:
    base = {
        "name": "fit",
        "type": "str",
        "required": False,
        "default": "'slip'",
        "units": None,
        "allowed_values": ["free", "slip", "press"],
        "value_doc": None,
    }
    base.update(overrides)
    return base


def _validate_one(param: dict) -> list[str]:
    errors: list[str] = []
    V._validate_param(param, ctor_label="X.__init__", errors=errors)
    return errors


def test_validator_rejects_empty_allowed_values():
    """Row 9 (R7a/R8a): empty allowed_values list fails."""
    errors = _validate_one(_make_param(allowed_values=[]))
    assert any("non-empty" in e for e in errors)


def test_validator_rejects_non_string_entry():
    """Row 9 (R7b): a non-string allowed_values entry fails."""
    errors = _validate_one(_make_param(allowed_values=["slip", 3]))
    assert any("must be a string" in e for e in errors)


def test_validator_passes_real_artifact():
    """Row 9: the real committed artifact validates clean."""
    payload = json.loads(
        (_REPO_ROOT / "vibe_cading" / "engine_api.json").read_text(encoding="utf-8")
    )
    errors, _ = V.validate(payload)
    assert errors == [], errors


def test_validator_default_quote_stripped_membership():
    """Row 10 (R8a): quote-stripped default must be ∈ allowed_values."""
    # In-set default passes.
    assert _validate_one(_make_param(default="'slip'")) == []
    # Out-of-set default fails (after stripping the quote layer).
    errors = _validate_one(_make_param(default="'banana'"))
    assert any("not in allowed_values" in e for e in errors)


def test_validator_none_default_exempt():
    """Row 10 (R8a): a required (no-default) param is exempt from membership."""
    # A required=True param carries no `default` key, so R8a's membership
    # check must not fire — a closed enum can still be a required param.
    clean = {
        "name": "x", "type": "str", "required": True, "units": None,
        "allowed_values": ["a", "b"], "value_doc": None,
    }
    assert _validate_one(clean) == []


def test_validator_value_doc_key_subset():
    """Row 11 (R8b): a value_doc key outside allowed_values fails."""
    errors = _validate_one(
        _make_param(value_doc={"slip": "ok", "ghost": "bad"})
    )
    assert any("value_doc keys" in e for e in errors)


def test_validator_value_doc_null_guard():
    """Row 11 (R8c): value_doc present while allowed_values null fails."""
    errors = _validate_one(
        _make_param(allowed_values=None, value_doc={"x": "y"})
    )
    assert any("must be null when 'allowed_values' is null" in e for e in errors)


# ---------------------------------------------------------------------------
# Tests-table row 12 — schema version lockstep
# ---------------------------------------------------------------------------


def test_schema_version_is_1_1():
    """Row 12 (R6): the extractor's SCHEMA_VERSION moved to 1.1."""
    assert SCHEMA_VERSION == "1.1"


def test_validator_rejects_wrong_schema_version():
    """Row 12 (R6): validator imports SCHEMA_VERSION and rejects a mismatch."""
    # The validator imports the constant (not re-declares it).
    assert V.SCHEMA_VERSION == SCHEMA_VERSION
    payload = {"schema_version": "1.0", "classes": [
        {"module": "m", "name": "C", "fqn": "m.C",
         "constructors": [{"kind": "init", "name": "__init__", "params": []}],
         "result_accessor": ".solid"},
    ]}
    errors, _ = V.validate(payload)
    assert any("schema_version" in e for e in errors)


# ---------------------------------------------------------------------------
# Tests-table row 13 — pure-stdlib, zero new deps
# ---------------------------------------------------------------------------


def test_extractor_imports_are_pure_stdlib():
    """Row 13 (R12): the extractor imports only the four stdlib modules."""
    tree = ast.parse(
        (_REPO_ROOT / "vibe_cading" / "tools" / "engine_api" / "extractor.py").read_text(
            encoding="utf-8"
        )
    )
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # `__future__` is a stdlib pseudo-module; the real runtime deps are
    # the four below — no CadQuery / third-party import added.
    imported.discard("__future__")
    assert imported == {"ast", "sys", "dataclasses", "pathlib"}, imported


# ---------------------------------------------------------------------------
# Tests-table row 14 — gen --check byte-determinism & green
# ---------------------------------------------------------------------------


def test_gen_check_green_and_deterministic():
    """Row 14 (R5/R10): gen --check exits 0; two builds are byte-identical."""
    proc = subprocess.run(
        [sys.executable, "vibe_cading/tools/gen_engine_api.py", "--check"],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    # Two in-memory builds are byte-identical (determinism).
    from vibe_cading.tools.gen_engine_api import _build_payload, _serialize
    a = _serialize(_build_payload(_REPO_ROOT))
    b = _serialize(_build_payload(_REPO_ROOT))
    assert a == b


# ---------------------------------------------------------------------------
# T9d — the :527 _synthesize_dataclass_init Literal path (synthetic fixture)
# ---------------------------------------------------------------------------


_SYNTH_DATACLASS_SRC = '''
from typing import Literal
from dataclasses import dataclass

_VALUE_DOC = {
    "Widget.mode": {"fast": "go fast", "slow": "go slow"},
}

@dataclass
class Widget:
    mode: Literal["fast", "slow"] = "fast"
    label: str = "x"
    count: int = 3
'''


_INHERITED_INIT_SRC = '''
class Base:
    def __init__(self, a: float, b: str = "x"):
        pass

class Child(Base):
    # No own __init__; adds only a classmethod override.
    @classmethod
    def make(cls, size: str) -> "Child":
        pass
'''


def test_classmethod_only_subclass_keeps_inherited_init():
    """Extractor: a subclass with only a classmethod still emits the
    ancestor's inherited ``__init__`` (the MetricNylocNut interaction).

    Pins the behavior at the source (independent of the model tree) so a
    future extractor refactor cannot silently re-drop inherited inits.
    """
    tree = ast.parse(_INHERITED_INIT_SRC)
    local = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    rec = E._build_class_record(
        local["Child"], module="m", local_classes=local, module_tree=tree,
    )
    kinds = [(c.kind, c.name) for c in rec.constructors]
    assert ("init", "__init__") in kinds  # inherited, not dropped
    assert ("classmethod", "make") in kinds
    init = next(c for c in rec.constructors if c.name == "__init__")
    assert [p.name for p in init.params] == ["a", "b"]
    # Init is first (init-first ordering preserved).
    assert rec.constructors[0].name == "__init__"


def test_synthesized_dataclass_literal_field_emits_allowed_values():
    """T9d: a Literal-annotated @dataclass field flows through the :527 path.

    No in-scope model is a synthesized @dataclass, so this path is driven
    by a dedicated synthetic fixture (design T1/T9 note).
    """
    tree = ast.parse(_SYNTH_DATACLASS_SRC)
    local = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    node = local["Widget"]
    rec = E._build_class_record(
        node, module="synthetic", local_classes=local, module_tree=tree,
    )
    init = rec.constructors[0]
    assert init.name == "__init__"
    params = {p.name: p.to_dict() for p in init.params}
    # The Literal field surfaces base type + allowed_values + value_doc.
    assert params["mode"]["type"] == "str"
    assert params["mode"]["allowed_values"] == ["fast", "slow"]
    assert params["mode"]["value_doc"] == {"fast": "go fast", "slow": "go slow"}
    # Non-Literal fields stay free-form.
    assert params["label"]["allowed_values"] is None
    assert params["label"]["value_doc"] is None
    assert params["count"]["type"] == "int"
    assert params["count"]["allowed_values"] is None
