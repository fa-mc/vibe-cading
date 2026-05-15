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

"""Protocol structural-typing + default-arg-callable regression tests.

Design reference: §Tests T4, §Success Criteria 6 in
``.agents/plans/2026-05-13-pre-oss-models-structure_design.md``.

For every concrete class that claims to implement one of the family
protocols (``CutterProtocol`` / ``ScrewProtocol`` / ``NutProtocol`` /
``JointProtocol``), this test module asserts two invariants:

1. **Structural typing** — ``isinstance(instance, <Protocol>)`` is True.
   This catches missing methods on the contract surface.
2. **Default-arg callable** — ``instance.to_cutter()`` (no profile
   argument) returns a non-None ``cq.Workplane``.  This is the regression
   gate that would have caught the Phase-5 ``MetricMachineScrew`` bug
   (B1 in the TL review): the protocol advertises ``profile=None`` as
   the default, so concrete classes MUST actually function with the
   documented default.

The case list is intentionally exhaustive across the directories
enumerated in the TL review's B3 (screws/, nuts/, joints/, holes/,
drives/, ventilation/, gears/, lego/cutters/, lego_adapters/servos/,
rc/servo/, mechanical/inserts.py, mechanical/standoffs.py).  A class
absent from this list is either: (a) not a cutter producer (no
``to_cutter`` method — e.g. ``Bearing`` uses ``outer_pocket`` /
``shaft_cutter``; magnets use ``pocket``); or (b) a pure positive solid
(``EscMount``, ``FreespinHexHub``, etc.).
"""

from __future__ import annotations

import importlib

import cadquery as cq
import pytest

from vibe_cading.mechanical.joints.protocol import JointProtocol
from vibe_cading.mechanical.nuts.protocol import NutProtocol
from vibe_cading.mechanical.protocols import CutterProtocol
from vibe_cading.mechanical.screws.protocol import ScrewProtocol


def _instantiate(module_path: str, class_name: str, ctor):
    """Resolve ``module.Class`` and instantiate it via direct kwargs or factory."""
    cls = getattr(importlib.import_module(module_path), class_name)
    if isinstance(ctor, tuple) and ctor and ctor[0] == "from_size":
        return cls.from_size(**ctor[1])
    return cls(**ctor)


# Case spec: (module, name, ctor_kwargs_or_factory_spec, family, xfail_reason)
# ``family`` is one of {"cutter", "screw", "nut", "joint"} and selects
# which family protocol to additionally check on top of CutterProtocol.
# ``xfail_reason`` is None when the class is healthy, or a string when a
# known pre-existing bug prevents ``.to_cutter()`` from succeeding with
# defaults — see the TeardropHole / Keyhole notes below.
_CUTTER_CASES: list[tuple[str, str, object, str, str | None]] = [
    # Holes — CutterProtocol
    ("vibe_cading.mechanical.holes", "ClearanceHole",
     {"diameter": 3.2, "depth": 5.0}, "cutter", None),
    ("vibe_cading.mechanical.holes", "CounterboreHole",
     {"shaft_diameter": 3.2, "shaft_depth": 5.0,
      "head_diameter": 5.5, "head_depth": 3.0}, "cutter", None),
    # TeardropHole / Keyhole have a pre-existing latent bug in their 2D
    # wire helper (``polyline().close().union(circle)``) that pre-dates
    # the Phase 1-7 refactor.  Neither class is consumed by build.toml,
    # so the bug never trips at build time.  Tracked as a separate
    # follow-up (B1-class regression in TeardropHole / Keyhole); xfail
    # here so the structural-typing assertion still runs and so a future
    # fix flips the case green automatically (strict=True).
    ("vibe_cading.mechanical.holes", "TeardropHole",
     {"diameter": 3.2, "depth": 5.0}, "cutter",
     "Pre-existing bug: _get_teardrop_wire calls .union() on a Wire-only "
     "Workplane (cq.Workplane raises). Not consumed by build.toml; "
     "tracked as separate follow-up."),
    ("vibe_cading.mechanical.holes", "SlottedHole",
     {"diameter": 3.2, "length": 10.0, "depth": 5.0}, "cutter", None),
    ("vibe_cading.mechanical.holes", "TaperedHole",
     {"top_diameter": 5.5, "bottom_diameter": 3.2, "depth": 5.0},
     "cutter", None),
    ("vibe_cading.mechanical.holes", "Keyhole",
     {"head_diameter": 5.5, "shaft_diameter": 3.2,
      "length": 4.0, "depth": 5.0}, "cutter",
     "Pre-existing bug: _get_keyhole_wire calls .union() on a Wire-only "
     "Workplane (cq.Workplane raises). Not consumed by build.toml; "
     "tracked as separate follow-up."),
    ("vibe_cading.mechanical.holes", "CaptiveNutPocket",
     {"width_across_flats": 5.5, "thickness": 2.4}, "cutter", None),
    # Drives — CutterProtocol
    ("vibe_cading.mechanical.screws.drives", "HexDrive",
     {"across_flats": 2.5, "depth": 1.5}, "cutter", None),
    ("vibe_cading.mechanical.screws.drives", "SlottedDrive",
     {"length": 4.0, "width": 1.0, "depth": 1.0}, "cutter", None),
    ("vibe_cading.mechanical.screws.drives", "PhillipsDrive",
     {"diameter": 4.5, "width": 1.0, "depth": 1.0}, "cutter", None),
    ("vibe_cading.mechanical.screws.drives", "TorxDrive",
     {"point_to_point_diameter": 2.8, "depth": 1.5}, "cutter", None),
    # Ventilation — CutterProtocol (dataclasses, all defaults work)
    ("vibe_cading.mechanical.enclosures.ventilation",
     "HexVentilationGrille", {}, "cutter", None),
    ("vibe_cading.mechanical.enclosures.ventilation",
     "SlottedVentilationGrille", {}, "cutter", None),
    # Lego cutters — CutterProtocol
    ("vibe_cading.lego.cutters.technic_pin_hole", "TechnicPinHole",
     {"depth": 7.2}, "cutter", None),
    ("vibe_cading.lego.cutters.technic_axle_hole", "TechnicAxleHole",
     {"depth": 7.2}, "cutter", None),
    # Inserts — CutterProtocol
    ("vibe_cading.mechanical.inserts", "HeatSetInsert",
     {"top_diameter": 4.4, "bot_diameter": 4.0, "depth": 5.5},
     "cutter", None),
    # Standoffs — CutterProtocol
    ("vibe_cading.mechanical.standoffs", "HexStandoff",
     {"width_flats": 5.5, "length": 10.0, "nominal_diameter": 3.0},
     "cutter", None),
    # Lego-adapter servo Shaft (cutter has a custom signature with
    # ``clearance``/``extend_up``/``extend_down`` rather than ``profile``,
    # but ``to_cutter()`` with NO args satisfies the protocol contract
    # and the no-args call shape that B1's regression gate exercises).
    ("vibe_cading.lego_adapters.servos.shaft", "Shaft", {}, "cutter", None),
    # RC servo wrapper — CutterProtocol
    ("vibe_cading.rc.servo.sg90", "Sg90Servo", {}, "cutter", None),
    # Screws — ScrewProtocol + CutterProtocol.  The metric case is the
    # B1 regression gate: this exact call (``MetricMachineScrew.from_size
    # ('M3', length=15).to_cutter(fit='clearance')``) was the failing
    # repro in the TL review.
    ("vibe_cading.mechanical.screws.metric", "MetricMachineScrew",
     ("from_size", {"size": "M3", "length": 10}), "screw", None),
    ("vibe_cading.mechanical.screws.wood", "WoodScrew",
     {"size": "#6", "length": 16.0}, "screw", None),
    ("vibe_cading.mechanical.screws.plastics", "PlasticsScrew",
     ("from_size", {"size": "M3", "length": 10}), "screw", None),
    ("vibe_cading.mechanical.screws.setscrew", "SetScrew",
     ("from_size", {"size": "M3", "length": 6}), "screw", None),
    ("vibe_cading.mechanical.screws.imperial", "ImperialMachineScrew",
     ("from_size", {"size": "4-40", "length": 0.5}), "screw", None),
    # Nuts — NutProtocol + CutterProtocol
    ("vibe_cading.mechanical.nuts.metric", "MetricHexNut",
     {"width_flats": 5.5, "thickness": 2.4}, "nut", None),
    ("vibe_cading.mechanical.nuts.metric", "MetricNylocNut",
     {"width_flats": 5.5, "thickness": 2.4}, "nut", None),
    ("vibe_cading.mechanical.nuts.metric", "MetricSquareNut",
     {"width_flats": 5.5, "thickness": 2.4}, "nut", None),
    ("vibe_cading.mechanical.nuts.tnut", "TNut",
     {"length": 16.0, "width": 11.0, "thickness": 3.0,
      "step_width": 7.5, "step_height": 1.5}, "nut", None),
    # Joints — JointProtocol + CutterProtocol
    ("vibe_cading.mechanical.joints.dovetail", "DovetailJoint",
     {"neck_width": 4.0, "tail_width": 6.0,
      "depth": 4.0, "length": 10.0}, "joint", None),
    ("vibe_cading.mechanical.joints.snap_fit", "CantileverSnapFit",
     {}, "joint", None),
]


def _case_id(case):
    """pytest test-id helper — show just the class name."""
    return case[1]


@pytest.mark.parametrize("case", _CUTTER_CASES, ids=_case_id)
def test_isinstance_cutter_protocol(case):
    """Every concrete cutter-producing class satisfies ``CutterProtocol``.

    ``isinstance`` with a ``@runtime_checkable`` Protocol only checks
    method *presence* (PEP 544); signature drift is caught by static
    type-checkers, not this test.  But presence alone is sufficient to
    catch a forgotten ``to_cutter`` method on a new family member.
    """
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    assert isinstance(inst, CutterProtocol), (
        f"{class_name} does not satisfy CutterProtocol — "
        "missing or wrongly-named ``to_cutter`` method?"
    )


@pytest.mark.parametrize("case", _CUTTER_CASES, ids=_case_id)
def test_to_cutter_default_args(case, request):
    """``to_cutter()`` with NO arguments returns a non-None ``cq.Workplane``.

    This is the **B1 regression gate**.  The protocol documents
    ``profile=None`` as the default; concrete implementations MUST
    function on that default, not crash inside an unwrapped
    ``profile.free.radial`` lookup.  Phase 5's ``MetricMachineScrew``
    bug was exactly this failure mode — caught by hand-probe, missed by
    CI because this test did not exist.
    """
    module_path, class_name, ctor, _family, xfail_reason = case
    if xfail_reason is not None:
        request.node.add_marker(
            pytest.mark.xfail(strict=True, reason=xfail_reason)
        )
    inst = _instantiate(module_path, class_name, ctor)
    cutter = inst.to_cutter()
    assert cutter is not None, f"{class_name}.to_cutter() returned None"
    assert isinstance(cutter, cq.Workplane), (
        f"{class_name}.to_cutter() returned "
        f"{type(cutter).__name__}, expected cq.Workplane"
    )


# --------------------------------------------------------------------------
# Family-specific protocol checks
# --------------------------------------------------------------------------

_SCREW_CASES = [c for c in _CUTTER_CASES if c[3] == "screw"]
_NUT_CASES = [c for c in _CUTTER_CASES if c[3] == "nut"]
_JOINT_CASES = [c for c in _CUTTER_CASES if c[3] == "joint"]


@pytest.mark.parametrize("case", _SCREW_CASES, ids=_case_id)
def test_isinstance_screw_protocol(case):
    """Every concrete screw class satisfies ``ScrewProtocol``."""
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    assert isinstance(inst, ScrewProtocol), (
        f"{class_name} does not satisfy ScrewProtocol — "
        "missing ``.solid`` property or ``.to_cutter(profile, fit)`` method?"
    )


@pytest.mark.parametrize("case", _NUT_CASES, ids=_case_id)
def test_isinstance_nut_protocol(case):
    """Every concrete nut class satisfies ``NutProtocol``."""
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    assert isinstance(inst, NutProtocol), (
        f"{class_name} does not satisfy NutProtocol — "
        "missing ``.solid`` property or ``.to_cutter(profile)`` method?"
    )


@pytest.mark.parametrize("case", _JOINT_CASES, ids=_case_id)
def test_isinstance_joint_protocol(case):
    """Every concrete joint class satisfies ``JointProtocol``."""
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    assert isinstance(inst, JointProtocol), (
        f"{class_name} does not satisfy JointProtocol — "
        "missing ``.male(overlap)`` or ``.to_cutter(profile)`` method?"
    )


# --------------------------------------------------------------------------
# Family ``.solid`` accessor check (positive-side contract)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("case", _SCREW_CASES + _NUT_CASES, ids=_case_id)
def test_family_solid_accessor(case):
    """Every screw / nut exposes a non-None ``.solid`` workplane.

    Joints expose ``.male()`` instead of ``.solid`` per the joint
    convention, so they are excluded from this check.
    """
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    solid = inst.solid
    assert solid is not None, f"{class_name}.solid returned None"
    assert isinstance(solid, cq.Workplane), (
        f"{class_name}.solid returned {type(solid).__name__}, "
        "expected cq.Workplane"
    )


@pytest.mark.parametrize("case", _JOINT_CASES, ids=_case_id)
def test_joint_male_accessor(case):
    """Every joint exposes a non-None ``.male(overlap=1.0)`` workplane."""
    module_path, class_name, ctor, _family, _xfail = case
    inst = _instantiate(module_path, class_name, ctor)
    male = inst.male()
    assert male is not None, f"{class_name}.male() returned None"
    assert isinstance(male, cq.Workplane), (
        f"{class_name}.male() returned {type(male).__name__}, "
        "expected cq.Workplane"
    )
