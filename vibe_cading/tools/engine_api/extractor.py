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

"""AST walker that extracts engine API records from ``vibe_cading/**`` and ``parts/**``.

Pure stdlib: imports nothing from CadQuery or the model packages themselves
so it runs deterministically in CI without needing the geometry stack.

Public surface
--------------
- ``extract_classes(roots)`` — discover and extract class records under the
  supplied directory roots.
- ``Param``, ``Constructor``, ``ClassRecord`` dataclasses mirroring the JSON
  schema produced by ``tools/gen_engine_api.py``.
- ``SCHEMA_VERSION`` — pinned schema version string. Bumped in lockstep
  with the validator (see ``.agents/plans/engine-api-json.md`` §8).

Discovery rule (brief §3)
-------------------------
Include any top-level ``ast.ClassDef`` whose name does not start with ``_``
and which is not abstract. A class is considered abstract if any of its
bases reads as ``ABC`` / ``abc.ABC`` *or* it has at least one method
decorated with ``@abstractmethod``.

Field derivation rules (brief §2)
---------------------------------
- ``module``: posix path of the file relative to the repo root, dotted,
  minus ``.py``.
- ``constructors[]``: ``__init__`` (kind="init") plus every
  ``@classmethod`` whose name does not start with ``_`` (kind="classmethod").
- ``params[]``: iterate ``func.args.args`` skipping the leading ``self`` /
  ``cls``. Annotations are emitted verbatim via ``ast.unparse``;
  ``"Any"`` is used when no annotation is present. ``default`` is the
  ``ast.unparse`` of the default expression (so it round-trips as a
  source-equivalent string), present iff the parameter has a default.
- ``units``: suffix-inferred (see ``_units_for_param``); ``deg`` for
  ``*_angle``, ``mm`` for the standard length-like suffixes, otherwise
  ``null``.
- ``result_accessor``: defaults to ``".solid"``. Override ladder lives in
  ``_result_accessor_for_class``.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# Pinned schema version. Bumped in lockstep with the validator (which
# imports this constant) per design brief §8.
SCHEMA_VERSION = "1.1"


# Parameter-name suffixes that imply mm. Ordered alphabetically for
# readability; lookup is by membership so order does not matter.
_MM_SUFFIXES: tuple[str, ...] = (
    "_clearance",
    "_depth",
    "_diameter",
    "_height",
    "_length",
    "_lift",
    "_offset",
    "_overlap",
    "_pitch",
    "_radius",
    "_thickness",
    "_tolerance",
    "_width",
)


# Bare parameter names that imply mm. The suffix matcher below only fires
# on ``_<suffix>`` forms (e.g. ``flange_thickness``); bare names like
# ``thickness`` need an exact-match table to avoid emitting ``units: null``
# for genuinely length-like params. ``module`` (gear-module ratio) and
# ``teeth`` (count) are deliberately excluded.
_MM_BARE_NAMES: frozenset[str] = frozenset({
    "bore",
    "depth",
    "diameter",
    "height",
    "length",
    "pitch",
    "radius",
    "size",
    "thickness",
    "tolerance",
    "width",
})


@dataclass
class Param:
    """A constructor / classmethod parameter record."""

    name: str
    type: str
    required: bool
    default: str | None = None  # ast.unparse of default expr; None if required.
    units: str | None = None  # "mm" / "deg" / None.
    # Schema 1.1 additive fields (design §D1/§D4). Both are always-present
    # keys in the wire output (``null`` when absent), matching the existing
    # ``units`` always-present convention.
    allowed_values: list | None = None  # closed enum set | None (free-form).
    value_doc: dict | None = None  # {value: gloss} | None (render-only hint).

    def to_dict(self) -> dict:
        out: dict = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
        }
        if not self.required:
            # Schema requires `default` present iff `required is false`. We
            # carry None through verbatim (e.g. ``flange_diameter: float | None
            # = None`` -> default="None").
            out["default"] = self.default
        out["units"] = self.units
        # Always-present 1.1 keys, immediately after ``units`` (design §D4).
        # ``null`` when the param is free-form / has no gloss.
        out["allowed_values"] = self.allowed_values
        out["value_doc"] = self.value_doc
        return out


@dataclass
class Constructor:
    """A constructor entry: ``__init__`` or a public classmethod."""

    kind: str  # "init" | "classmethod" | "factory" (factory reserved).
    name: str
    doc: str | None
    params: list[Param] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "doc": self.doc,
            "params": [p.to_dict() for p in self.params],
        }


@dataclass
class ClassRecord:
    """A discovered class record."""

    module: str
    name: str
    fqn: str
    doc: str | None
    constructors: list[Constructor]
    result_accessor: str | None  # ".solid" / ".cutter" / null.

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "name": self.name,
            "fqn": self.fqn,
            "doc": self.doc,
            "constructors": [c.to_dict() for c in self.constructors],
            "result_accessor": self.result_accessor,
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_classes(
    roots: list[Path],
    exclude: Iterable[Path] | None = None,
) -> list[ClassRecord]:
    """Walk *roots* and return discovered class records.

    Each root is treated as a directory; ``*.py`` files beneath it are
    parsed with ``ast.parse``. The repo root (used to compute the dotted
    module path) is inferred as the parent of the first root — for the
    standard call ``extract_classes([Path("vibe_cading"), Path("parts")])``
    this resolves to the current working directory, which the CLI sets to
    the repo root.

    *exclude* is an optional iterable of directories whose subtree is
    skipped during the walk (default ``None`` = no exclusions, so every
    existing caller keeps its full coverage). Unlike ``experiments/``,
    which is excluded simply by being *absent* from ``roots``, a subtree
    such as ``vibe_cading/mcp/`` lives *inside* the walked ``vibe_cading``
    root and cannot be omitted that way — it needs this explicit seam.
    The ``mcp`` subpackage is a runtime MCP-server entry point that
    imports an optional third-party SDK; its classes are server plumbing,
    never catalog model classes, so any *public* class added there must
    not leak into ``engine_api.json``.

    Records are returned in deterministic order (FQN ascending) so the
    JSON output is stable across runs and platforms.
    """
    records: list[ClassRecord] = []
    seen_fqns: set[str] = set()

    # Resolve the excluded directories once so the per-file membership test
    # below compares fully-resolved ``Path.parents`` against fully-resolved
    # exclude dirs (``py_path`` is itself resolved via ``root.resolve()``).
    resolved_exclude = [Path(p).resolve() for p in (exclude or ())]

    for root in roots:
        root = root.resolve()
        repo_root = root.parent
        for py_path in sorted(root.rglob("*.py")):
            if "__pycache__" in py_path.parts:
                continue
            # Skip any file living under an excluded subtree (e.g.
            # ``vibe_cading/mcp/``). This is the seam that keeps an
            # inside-a-walked-root subpackage out of the class catalog;
            # see the *exclude* note in the docstring above.
            if any(excl in py_path.parents for excl in resolved_exclude):
                continue
            module = _module_path(py_path, repo_root)
            try:
                tree = ast.parse(py_path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                # Skip files that don't parse — they would also fail at
                # import time, which is a separate problem to fix in the
                # offending file rather than in the extractor. Emit to
                # stderr so a typo'd model file does not silently vanish
                # from the artifact.
                print(
                    f"[engine_api] skipped {py_path}: {exc}",
                    file=sys.stderr,
                )
                continue
            # Index top-level classes in this file by name so subclasses
            # can inherit constructors from a same-module ancestor when
            # they don't define one themselves (e.g. ``MetricNylocNut``
            # extends ``MetricHexNut`` with only a class-level
            # ``DIMENSIONS`` override). Cross-file inheritance resolution
            # would require an import graph and is out of scope for v1.
            local_classes: dict[str, ast.ClassDef] = {
                n.name: n for n in tree.body if isinstance(n, ast.ClassDef)
            }
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if not _is_discoverable(node):
                    continue
                record = _build_class_record(
                    node, module=module, local_classes=local_classes,
                    module_tree=tree,
                )
                if not record.constructors:
                    # No own constructors and no resolvable same-module
                    # ancestor — skip rather than emit a record that
                    # would fail the validator's non-empty constructors
                    # rule.
                    continue
                if record.fqn in seen_fqns:
                    # Duplicate FQNs would also fail validation; skip the
                    # later occurrence and let the validator surface the
                    # collision via a separate run if it slips through.
                    continue
                seen_fqns.add(record.fqn)
                records.append(record)

    records.sort(key=lambda r: r.fqn)
    return records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _module_path(py_path: Path, repo_root: Path) -> str:
    """Convert a file path under *repo_root* to a dotted module path."""
    rel = py_path.relative_to(repo_root)
    parts = list(rel.with_suffix("").parts)
    # ``foo/__init__.py`` -> ``foo`` (drop trailing ``__init__``).
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_discoverable(node: ast.ClassDef) -> bool:
    """Apply the discovery rule (brief §3)."""
    if node.name.startswith("_"):
        return False
    # Exclude classes whose declared base reads as ``ABC`` or ``abc.ABC``.
    # Mirror exclusion for ``typing.Protocol`` (PEP 544 structural-typing
    # contracts) — Phase 5 introduces ``ScrewProtocol`` / ``NutProtocol`` /
    # ``JointProtocol`` / ``CutterProtocol`` as contract-only types; they
    # are never instantiated, declare no constructor, and must NOT leak
    # into the engine_api wire JSON (gate test asserts zero ``*Protocol``
    # leaks).  CPython sets a private ``_is_protocol = True`` attribute on
    # Protocol subclasses at runtime, but the extractor walks AST without
    # importing modules, so we identify protocols by inspecting their
    # declared bases instead.
    for base in node.bases:
        if _base_is_abc(base):
            return False
        if _base_is_protocol(base):
            return False
    # Exclude classes that declare any ``@abstractmethod`` method. This
    # also catches ABCs that subclass ``object`` but use the decorator
    # directly — belt-and-braces per brief §2.
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _has_decorator(child, "abstractmethod"):
                return False
    return True


def _base_is_abc(base: ast.expr) -> bool:
    """True if a class base node reads as ``ABC`` or ``abc.ABC``."""
    if isinstance(base, ast.Name) and base.id == "ABC":
        return True
    if (
        isinstance(base, ast.Attribute)
        and base.attr == "ABC"
        and isinstance(base.value, ast.Name)
        and base.value.id == "abc"
    ):
        return True
    return False


def _base_is_protocol(base: ast.expr) -> bool:
    """True if a class base node reads as ``Protocol`` or ``typing.Protocol``.

    Matches both forms commonly seen in this codebase: bare
    ``class Foo(Protocol):`` (when the user has done
    ``from typing import Protocol``) and the qualified
    ``class Foo(typing.Protocol):`` form.  Mirrors the AST shape of
    ``_base_is_abc`` so the two exclusions stay symmetric.
    """
    if isinstance(base, ast.Name) and base.id == "Protocol":
        return True
    if (
        isinstance(base, ast.Attribute)
        and base.attr == "Protocol"
        and isinstance(base.value, ast.Name)
        and base.value.id == "typing"
    ):
        return True
    return False


def _has_decorator(func: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """True if *func* carries a decorator with the bare *name*.

    Matches both ``@name`` and ``@module.name`` forms so e.g.
    ``@abc.abstractmethod`` is detected as well as ``@abstractmethod``.
    """
    for dec in func.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == name:
            return True
        if isinstance(target, ast.Attribute) and target.attr == name:
            return True
    return False


def _build_class_record(
    node: ast.ClassDef,
    *,
    module: str,
    local_classes: dict[str, ast.ClassDef] | None = None,
    module_tree: ast.Module | None = None,
) -> ClassRecord:
    fqn = f"{module}.{node.name}"
    constructors = _collect_constructors(
        node, local_classes=local_classes or {}, module_tree=module_tree,
    )

    return ClassRecord(
        module=module,
        name=node.name,
        fqn=fqn,
        doc=ast.get_docstring(node),
        constructors=constructors,
        result_accessor=_result_accessor_for_class(node),
    )


def _collect_constructors(
    node: ast.ClassDef,
    *,
    local_classes: dict[str, ast.ClassDef],
    module_tree: ast.Module | None = None,
) -> list[Constructor]:
    """Walk the class body and gather constructors.

    Order: ``__init__`` first (whether literal or synthesized from a
    ``@dataclass`` decorator), then public classmethods in source order.
    If the class defines neither and is not a dataclass, fall back to
    inheriting constructors from a same-module ancestor (one level deep
    is sufficient for current usage; multi-level chains would loop here
    via the recursive call).
    """
    constructors: list[Constructor] = []
    has_explicit_init = False

    for child in node.body:
        if not isinstance(child, ast.FunctionDef):
            continue
        if child.name == "__init__":
            constructors.append(
                _build_constructor(
                    child, kind="init",
                    module_tree=module_tree, class_name=node.name,
                )
            )
            has_explicit_init = True
            continue
        if child.name.startswith("_"):
            continue
        # ``demo`` is a viewer-only convention surfaced by ``tools/view.py
        # --demo`` — see ``vibe/INSTRUCTIONS.md`` § "OCP Viewer".  It is not
        # a class constructor and MUST be excluded from the engine_api wire
        # contract so the post-Wave-B sweep keeps the JSON byte-identical
        # vs. pre-sweep output.
        if child.name == "demo":
            continue
        if _has_decorator(child, "classmethod"):
            constructors.append(
                _build_constructor(
                    child, kind="classmethod",
                    module_tree=module_tree, class_name=node.name,
                )
            )

    # Synthesize an init for ``@dataclass`` decorated classes that do not
    # define one explicitly. The dataclass decorator generates
    # ``__init__`` at class-creation time from the annotated class-body
    # fields; the extractor mirrors that here so the JSON artifact still
    # describes a callable signature. The synthesized record is prepended
    # so "init first" ordering holds.
    if not has_explicit_init and _is_dataclass(node):
        synthetic = _synthesize_dataclass_init(node, module_tree=module_tree)
        if synthetic is not None:
            constructors.insert(0, synthetic)
            has_explicit_init = True

    if constructors:
        # The class has at least one own constructor (an ``__init__`` and/or
        # public classmethods).  If it defines public classmethods but NO
        # own/synthesized ``__init__``, it still *inherits* the ancestor's
        # ``__init__`` at runtime — and that inherited ``__init__`` is a real
        # callable signature consumers rely on.  Pull it from the same-module
        # ancestor and prepend it so "init first" ordering holds.
        #
        # Why this matters: ``MetricNylocNut`` defines only a ``from_size``
        # classmethod override (added in schema 1.1 to advertise its own size
        # enum) but inherits ``MetricHexNut.__init__``.  Without this branch,
        # adding the override would silently DROP the inherited ``__init__``
        # from the wire record (it was present in schema 1.0), violating the
        # additive-only contract.  This keeps the emitted constructor set
        # faithful to what the class actually exposes.
        if not has_explicit_init:
            inherited_init = _inherited_init_from_ancestor(
                node, local_classes=local_classes, module_tree=module_tree,
            )
            if inherited_init is not None:
                constructors.insert(0, inherited_init)
        return constructors

    # Inherit ALL constructors from a same-module ancestor when the class
    # has no own constructors at all. We look up bases by bare name;
    # ``ast.Attribute`` bases (e.g. ``foo.BaseClass``) are not resolved —
    # that requires import graph walking which v1 does not implement.
    # ``module_tree`` flows through so an inherited ``Literal`` param resolves
    # its ``_VALUE_DOC`` gloss against the (same) module's AST keyed by the
    # ancestor's class name.
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in local_classes:
            ancestor = local_classes[base.id]
            inherited = _collect_constructors(
                ancestor, local_classes=local_classes, module_tree=module_tree,
            )
            if inherited:
                return inherited
    return []


def _inherited_init_from_ancestor(
    node: ast.ClassDef,
    *,
    local_classes: dict[str, ast.ClassDef],
    module_tree: ast.Module | None = None,
) -> Constructor | None:
    """Return the ``__init__`` Constructor inherited from a same-module ancestor.

    Used when a subclass defines public classmethods but no own ``__init__``
    so the runtime-inherited ``__init__`` is not dropped from the wire
    record.  Resolves bare-name bases only (same one-level same-module scope
    as the full-inheritance fallback); returns ``None`` if no ancestor
    contributes an ``__init__``.
    """
    for base in node.bases:
        if not (isinstance(base, ast.Name) and base.id in local_classes):
            continue
        ancestor = local_classes[base.id]
        inherited = _collect_constructors(
            ancestor, local_classes=local_classes, module_tree=module_tree,
        )
        for ctor in inherited:
            if ctor.kind == "init":
                return ctor
    return None


def _build_constructor(
    func: ast.FunctionDef,
    *,
    kind: str,
    module_tree: ast.Module | None = None,
    class_name: str | None = None,
) -> Constructor:
    return Constructor(
        kind=kind,
        name=func.name,
        doc=ast.get_docstring(func),
        params=_extract_params(
            func, kind=kind,
            module_tree=module_tree, class_name=class_name,
        ),
    )


def _extract_params(
    func: ast.FunctionDef,
    *,
    kind: str,
    module_tree: ast.Module | None = None,
    class_name: str | None = None,
) -> list[Param]:
    """Extract positional-or-keyword parameters from *func*.

    Skips the leading ``self`` (init) or ``cls`` (classmethod). Defaults
    are right-aligned per Python semantics: an N-arg function with K
    defaults has them apply to the last K args.

    ``*args`` / ``**kwargs`` are intentionally ignored — the schema
    targets concrete user-facing parameters, and no current model uses
    var-args in a public constructor.

    ``module_tree`` / ``class_name`` are threaded through so a
    ``Literal``-annotated param can resolve its co-located ``_VALUE_DOC``
    gloss (schema 1.1, design §D5).  Both may be ``None`` (e.g. the
    synthetic-dataclass twin passes its own context) — in which case no
    ``value_doc`` is attached.
    """
    # ``func.args.kwonlyargs`` is intentionally out of scope for v1 — no
    # current model exposes keyword-only constructor params.
    # TODO: revisit if a future model needs them; will require pairing
    # against ``func.args.kw_defaults`` (which uses None as a sentinel
    # for "no default", not "default is None") and emitting them after
    # the positional-or-keyword params here.
    args = list(func.args.args)
    if args:
        leading = args[0].arg
        if (kind == "init" and leading == "self") or (
            kind == "classmethod" and leading == "cls"
        ):
            args = args[1:]

    defaults = list(func.args.defaults)
    # Right-align defaults onto the tail of args.
    n_required = len(args) - len(defaults)
    paired: list[tuple[ast.arg, ast.expr | None]] = []
    for idx, arg in enumerate(args):
        if idx < n_required:
            paired.append((arg, None))
        else:
            paired.append((arg, defaults[idx - n_required]))

    out: list[Param] = []
    for arg, default in paired:
        # ``_split_literal`` intercepts a ``Literal[...]`` subscript before
        # the historical ``ast.unparse`` so the 1.0 ``type`` contract is
        # preserved (``"str"``, not ``"Literal[...]"``) and the member set
        # surfaces as ``allowed_values`` (schema 1.1, design §D1).  A
        # non-``Literal`` annotation round-trips byte-identically.
        type_str, allowed_values = _split_literal(arg.annotation)
        value_doc = (
            _value_doc_for(module_tree, class_name, arg.arg)
            if allowed_values is not None
            else None
        )
        if default is None:
            out.append(
                Param(
                    name=arg.arg,
                    type=type_str,
                    required=True,
                    default=None,
                    units=_units_for_param(arg.arg),
                    allowed_values=allowed_values,
                    value_doc=value_doc,
                )
            )
        else:
            out.append(
                Param(
                    name=arg.arg,
                    type=type_str,
                    required=False,
                    default=ast.unparse(default),
                    units=_units_for_param(arg.arg),
                    allowed_values=allowed_values,
                    value_doc=value_doc,
                )
            )
    return out


def _is_dataclass(node: ast.ClassDef) -> bool:
    """True if *node* is decorated with ``@dataclass`` (any import form)."""
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == "dataclass":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "dataclass":
            return True
    return False


def _synthesize_dataclass_init(
    node: ast.ClassDef,
    *,
    module_tree: ast.Module | None = None,
) -> Constructor | None:
    """Build a synthetic ``__init__`` constructor from dataclass fields.

    Reads class-body ``AnnAssign`` nodes (annotated assignments) which is
    how ``@dataclass`` collects fields. ``ClassVar`` and assignments
    without annotations are ignored. A field with a default value (RHS of
    the AnnAssign) is emitted as optional; one without becomes required.

    A ``Literal``-annotated dataclass field surfaces its member set as
    ``allowed_values`` via the same ``_split_literal`` interception used
    by ``_extract_params`` (schema 1.1).  No in-scope Coverage-list class
    is a synthesized ``@dataclass`` — every in-scope param flows through
    ``_extract_params`` — so this wiring changes zero in-scope wire bytes
    today; it is here for uniformity / future-proofing and is exercised
    only by the dedicated synthetic fixture in the test suite (design T9d).
    """
    params: list[Param] = []
    for child in node.body:
        if not isinstance(child, ast.AnnAssign):
            continue
        if not isinstance(child.target, ast.Name):
            continue
        # Skip ClassVar / private fields.
        if _is_classvar(child.annotation):
            continue
        name = child.target.id
        if name.startswith("_"):
            continue
        type_str, allowed_values = _split_literal(child.annotation)
        value_doc = (
            _value_doc_for(module_tree, node.name, name)
            if allowed_values is not None
            else None
        )
        if child.value is None:
            params.append(
                Param(
                    name=name,
                    type=type_str,
                    required=True,
                    default=None,
                    units=_units_for_param(name),
                    allowed_values=allowed_values,
                    value_doc=value_doc,
                )
            )
        else:
            params.append(
                Param(
                    name=name,
                    type=type_str,
                    required=False,
                    default=ast.unparse(child.value),
                    units=_units_for_param(name),
                    allowed_values=allowed_values,
                    value_doc=value_doc,
                )
            )
    if not params:
        return None
    return Constructor(
        kind="init",
        name="__init__",
        doc=None,
        params=params,
    )


def _is_classvar(annotation: ast.expr | None) -> bool:
    """True if *annotation* reads as ``ClassVar[...]`` / ``typing.ClassVar``."""
    if annotation is None:
        return False
    target = annotation
    if isinstance(target, ast.Subscript):
        target = target.value
    if isinstance(target, ast.Name) and target.id == "ClassVar":
        return True
    if isinstance(target, ast.Attribute) and target.attr == "ClassVar":
        return True
    return False


def _is_literal_subscript(annotation: ast.expr | None) -> bool:
    """True if *annotation* reads as ``Literal[...]`` / ``typing.Literal[...]``.

    Mirrors the AST shape used by ``_is_classvar`` / ``_base_is_abc`` /
    ``_base_is_protocol`` so the convention stays consistent across the
    extractor.  Matches both the bare ``Literal`` (after
    ``from typing import Literal``) and the qualified ``typing.Literal``
    subscript forms.  ``ast.parse`` produces a real ``Subscript`` node for
    a ``Literal[...]`` annotation regardless of
    ``from __future__ import annotations`` — PEP 563 stringification
    affects only runtime ``__annotations__``, never the parse tree walked
    here.
    """
    if annotation is None or not isinstance(annotation, ast.Subscript):
        return False
    value = annotation.value
    if isinstance(value, ast.Name) and value.id == "Literal":
        return True
    if (
        isinstance(value, ast.Attribute)
        and value.attr == "Literal"
        and isinstance(value.value, ast.Name)
        and value.value.id == "typing"
    ):
        return True
    return False


def _literal_members(annotation: ast.Subscript) -> list:
    """Return the ordered member values of a ``Literal[...]`` subscript.

    A multi-member literal's slice is an ``ast.Tuple`` of ``ast.Constant``;
    a single-member literal's slice is a bare ``ast.Constant``.  Member
    values are collected in source-declaration order.  A non-constant
    slice element (e.g. ``Literal[SOME_VAR]``) is a producer bug — fail
    loudly rather than emit a silently-wrong enum.
    """
    node = annotation.slice
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    members: list = []
    for elt in elements:
        if not isinstance(elt, ast.Constant):
            raise ValueError(
                "engine_api: Literal[...] members must be constants; got "
                f"{ast.dump(elt)}"
            )
        members.append(elt.value)
    return members


def _literal_base_type(members: list) -> str:
    """Return the JSON-runtime base type of a ``Literal``'s members.

    ``"str"`` iff every member is a Python ``str`` (the entire 1.1
    in-scope enum surface is all-string).  A future numeric enum would
    return ``"int"`` / ``"float"`` — the mapping generalizes without a
    wire-format change.  Returns the unparsed annotation only for the
    all-same-type cases the schema supports; mixed-type literals are out
    of scope and fall back to ``"str"`` only when truly all-string.
    """
    if members and all(isinstance(m, str) for m in members):
        return "str"
    if members and all(isinstance(m, bool) for m in members):
        # ``bool`` is a subclass of ``int`` — check it before ``int``.
        return "bool"
    if members and all(isinstance(m, int) for m in members):
        return "int"
    if members and all(isinstance(m, float) for m in members):
        return "float"
    # Mixed-type or empty literal — out of scope for the 1.1 schema; the
    # caller should never reach here for an in-scope site.  Fall back to a
    # neutral type string so the artifact stays serializable.
    return "str"


def _split_literal(annotation: ast.expr | None) -> tuple[str, list | None]:
    """Map a parameter annotation to ``(type_str, allowed_values)``.

    A ``Literal[...]`` annotation yields the *base runtime type* of its
    members as ``type_str`` (NOT ``"Literal[...]"`` — preserving the 1.0
    ``type`` contract so no 1.0 consumer sees a retype) plus the ordered
    list of member values.  Any other annotation is unparsed verbatim
    with ``allowed_values = None`` — byte-identical behaviour to the
    pre-1.1 ``ast.unparse(annotation)`` path.
    """
    if annotation is None:
        return "Any", None
    if _is_literal_subscript(annotation):
        members = _literal_members(annotation)
        return _literal_base_type(members), members
    return ast.unparse(annotation), None


def _parse_value_doc_assign(node: ast.Dict) -> dict:
    """Parse a ``_VALUE_DOC`` dict-literal AST into a nested str dict.

    Expects ``{"<Class>.<param>": {value: gloss, ...}, ...}`` where every
    key and gloss is a constant ``str``.  A non-constant key, a non-dict
    inner value, or a non-constant gloss is a producer bug — fail loudly
    rather than silently drop a gloss (design §D5).
    """
    result: dict[str, dict[str, str]] = {}
    for outer_key, outer_val in zip(node.keys, node.values):
        if not (isinstance(outer_key, ast.Constant) and isinstance(outer_key.value, str)):
            raise ValueError(
                "engine_api: _VALUE_DOC keys must be constant strings; got "
                f"{ast.dump(outer_key) if outer_key is not None else 'None'}"
            )
        if not isinstance(outer_val, ast.Dict):
            raise ValueError(
                f"engine_api: _VALUE_DOC['{outer_key.value}'] must be a dict literal"
            )
        inner: dict[str, str] = {}
        for k, v in zip(outer_val.keys, outer_val.values):
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                raise ValueError(
                    f"engine_api: _VALUE_DOC['{outer_key.value}'] keys must be "
                    "constant strings"
                )
            if not (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                raise ValueError(
                    f"engine_api: _VALUE_DOC['{outer_key.value}']['{k.value}'] "
                    "gloss must be a constant string"
                )
            inner[k.value] = v.value
        result[outer_key.value] = inner
    return result


def _value_doc_for(
    module_tree: ast.Module | None,
    class_name: str | None,
    param_name: str,
) -> dict | None:
    """Resolve a co-located ``_VALUE_DOC`` gloss for ``<class>.<param>``.

    Reads a top-level ``_VALUE_DOC`` ``Assign`` from *module_tree* (pure
    same-module AST — no import, no cross-file graph) and returns
    ``_VALUE_DOC.get(f"{class_name}.{param_name}")`` or ``None``.  Returns
    ``None`` when no module tree / class name is available, or the module
    declares no ``_VALUE_DOC`` (design §D5).
    """
    if module_tree is None or class_name is None:
        return None
    for stmt in module_tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        targets = stmt.targets
        if not any(
            isinstance(t, ast.Name) and t.id == "_VALUE_DOC" for t in targets
        ):
            continue
        if not isinstance(stmt.value, ast.Dict):
            raise ValueError(
                "engine_api: _VALUE_DOC must be assigned a dict literal"
            )
        mapping = _parse_value_doc_assign(stmt.value)
        return mapping.get(f"{class_name}.{param_name}")
    return None


def _units_for_param(name: str) -> str | None:
    """Suffix-inferred unit per brief §9.1.

    Resolution order: angle (bare or ``_angle``-suffix) → bare-name table
    (``_MM_BARE_NAMES``) → mm-suffix table (``_MM_SUFFIXES``) → ``None``.
    """
    if name == "angle" or name.endswith("_angle"):
        return "deg"
    if name in _MM_BARE_NAMES:
        return "mm"
    for suffix in _MM_SUFFIXES:
        if name.endswith(suffix):
            return "mm"
    return None


def _result_accessor_for_class(node: ast.ClassDef) -> str | None:
    """Resolve the ``result_accessor`` field per brief §2."""
    # Abstract classes never make it here (filtered in discovery), but
    # belt-and-braces: if any abstractmethod slipped through, return None.
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _has_decorator(child, "abstractmethod"):
                return None

    properties: list[str] = []
    for child in node.body:
        if not isinstance(child, ast.FunctionDef):
            continue
        if not _has_decorator(child, "property"):
            continue
        if child.name.startswith("_"):
            continue
        properties.append(child.name)

    if "solid" in properties:
        return ".solid"
    if len(properties) == 1:
        return f".{properties[0]}"
    if len(properties) == 0:
        # No public property at all — fall back to the ``.solid``
        # convention. The validator will not flag this; if a class has
        # neither ``.solid`` nor any other public property it is most
        # likely a data carrier (e.g. ``ToleranceProfile``) which the
        # platform will treat as opaque.
        return ".solid"
    # Multiple public properties, none called ``solid``: ambiguous.
    return None
