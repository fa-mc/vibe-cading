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

"""AST walker that extracts engine API records from ``models/**``.

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
from dataclasses import dataclass, field
from pathlib import Path

# Pinned schema version. Bumped in lockstep with the validator (which
# imports this constant) per design brief §8.
SCHEMA_VERSION = "1.0"


# Parameter-name suffixes that imply mm. Ordered alphabetically for
# readability; lookup is by membership so order does not matter.
_MM_SUFFIXES: tuple[str, ...] = (
    "_clearance",
    "_depth",
    "_dia",
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


@dataclass
class Param:
    """A constructor / classmethod parameter record."""

    name: str
    type: str
    required: bool
    default: str | None = None  # ast.unparse of default expr; None if required.
    units: str | None = None  # "mm" / "deg" / None.

    def to_dict(self) -> dict:
        out: dict = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
        }
        if not self.required:
            # Schema requires `default` present iff `required is false`. We
            # carry None through verbatim (e.g. ``flange_dia: float | None
            # = None`` -> default="None").
            out["default"] = self.default
        out["units"] = self.units
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


def extract_classes(roots: list[Path]) -> list[ClassRecord]:
    """Walk *roots* and return discovered class records.

    Each root is treated as a directory; ``*.py`` files beneath it are
    parsed with ``ast.parse``. The repo root (used to compute the dotted
    module path) is inferred as the parent of the first root — for the
    standard call ``extract_classes([Path("models")])`` this resolves to
    the current working directory, which the CLI sets to the repo root.

    Records are returned in deterministic order (FQN ascending) so the
    JSON output is stable across runs and platforms.
    """
    records: list[ClassRecord] = []
    seen_fqns: set[str] = set()

    for root in roots:
        root = root.resolve()
        repo_root = root.parent
        for py_path in sorted(root.rglob("*.py")):
            if "__pycache__" in py_path.parts:
                continue
            module = _module_path(py_path, repo_root)
            try:
                tree = ast.parse(py_path.read_text(encoding="utf-8"))
            except SyntaxError:
                # Skip files that don't parse — they would also fail at
                # import time, which is a separate problem to fix in the
                # offending file rather than in the extractor.
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
    for base in node.bases:
        if _base_is_abc(base):
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
) -> ClassRecord:
    fqn = f"{module}.{node.name}"
    constructors = _collect_constructors(node, local_classes=local_classes or {})

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
            constructors.append(_build_constructor(child, kind="init"))
            has_explicit_init = True
            continue
        if child.name.startswith("_"):
            continue
        if _has_decorator(child, "classmethod"):
            constructors.append(_build_constructor(child, kind="classmethod"))

    # Synthesize an init for ``@dataclass`` decorated classes that do not
    # define one explicitly. The dataclass decorator generates
    # ``__init__`` at class-creation time from the annotated class-body
    # fields; the extractor mirrors that here so the JSON artifact still
    # describes a callable signature. The synthesized record is prepended
    # so "init first" ordering holds.
    if not has_explicit_init and _is_dataclass(node):
        synthetic = _synthesize_dataclass_init(node)
        if synthetic is not None:
            constructors.insert(0, synthetic)
            has_explicit_init = True

    if constructors:
        return constructors

    # Inherit from a same-module ancestor when no own constructors. We
    # look up bases by bare name; ``ast.Attribute`` bases (e.g.
    # ``foo.BaseClass``) are not resolved — that requires import graph
    # walking which v1 does not implement.
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in local_classes:
            ancestor = local_classes[base.id]
            inherited = _collect_constructors(
                ancestor, local_classes=local_classes,
            )
            if inherited:
                return inherited
    return []


def _build_constructor(func: ast.FunctionDef, *, kind: str) -> Constructor:
    return Constructor(
        kind=kind,
        name=func.name,
        doc=ast.get_docstring(func),
        params=_extract_params(func, kind=kind),
    )


def _extract_params(func: ast.FunctionDef, *, kind: str) -> list[Param]:
    """Extract positional-or-keyword parameters from *func*.

    Skips the leading ``self`` (init) or ``cls`` (classmethod). Defaults
    are right-aligned per Python semantics: an N-arg function with K
    defaults has them apply to the last K args.

    ``*args`` / ``**kwargs`` are intentionally ignored — the schema
    targets concrete user-facing parameters, and no current model uses
    var-args in a public constructor.
    """
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
        type_str = ast.unparse(arg.annotation) if arg.annotation is not None else "Any"
        if default is None:
            out.append(
                Param(
                    name=arg.arg,
                    type=type_str,
                    required=True,
                    default=None,
                    units=_units_for_param(arg.arg),
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


def _synthesize_dataclass_init(node: ast.ClassDef) -> Constructor | None:
    """Build a synthetic ``__init__`` constructor from dataclass fields.

    Reads class-body ``AnnAssign`` nodes (annotated assignments) which is
    how ``@dataclass`` collects fields. ``ClassVar`` and assignments
    without annotations are ignored. A field with a default value (RHS of
    the AnnAssign) is emitted as optional; one without becomes required.
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
        type_str = ast.unparse(child.annotation) if child.annotation is not None else "Any"
        if child.value is None:
            params.append(
                Param(
                    name=name,
                    type=type_str,
                    required=True,
                    default=None,
                    units=_units_for_param(name),
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


def _units_for_param(name: str) -> str | None:
    """Suffix-inferred unit per brief §9.1."""
    if name.endswith("_angle"):
        return "deg"
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
