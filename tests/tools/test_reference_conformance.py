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

"""Tests for the reference-conformance manifest and its checker.

As with ``surface_diff``, the load-bearing behaviour is refusal: the manifest
must reject a deviation declared without a reason, and a missing reference must
SKIP LOUDLY rather than pass quietly.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from vibe_cading.tools.check_reference_conformance import (
    MANIFEST,
    SKIP,
    ManifestError,
    check_component,
    load_manifest,
    raise_floor,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shipped_manifest_parses_and_validates():
    comps = load_manifest()
    assert comps, "manifest registers no components"
    for c in comps:
        assert len(c["region"]) == 6
        assert 0.0 <= float(c["min_agreement"]) <= 100.0


def test_every_accepted_deviation_states_what_and_why():
    """A deviation without a reason is indistinguishable from abandoned drift."""
    data = tomllib.loads(MANIFEST.read_text())
    for comp in data.get("component", []):
        for dev in comp.get("accepted_deviation", []):
            assert dev.get("what", "").strip()
            assert dev.get("why", "").strip()


def test_deviation_without_a_reason_is_rejected(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text(
        '[[component]]\n'
        'name = "x"\nmodel = "m.C"\nreference = "r.stl"\n'
        'region = [0,1,0,1,0,1]\nmin_agreement = 50.0\n'
        '[[component.accepted_deviation]]\nwhat = "something"\nwhy = ""\n'
    )
    with pytest.raises(ManifestError, match="why"):
        load_manifest(bad)


def test_malformed_region_is_rejected(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text(
        '[[component]]\n'
        'name = "x"\nmodel = "m.C"\nreference = "r.stl"\n'
        'region = [0,1,0,1]\nmin_agreement = 50.0\n'
    )
    with pytest.raises(ManifestError, match="6 numbers"):
        load_manifest(bad)


def test_absent_reference_skips_loudly_rather_than_passing():
    """Third-party references are not committed, so the check cannot run in CI.

    It must say so. A silent pass would imply coverage that does not exist.
    """
    status, msg, got = check_component({
        "name": "synthetic",
        "model": "does.not.matter.Class",
        "reference": "tmp/definitely-absent-reference.stl",
        "region": [0, 1, 0, 1, 0, 1],
        "min_agreement": 90.0,
    })
    assert status == SKIP
    assert got is None
    assert "not present" in msg and "not a CI gate" in msg


def test_open_gaps_are_declared_without_being_excluded():
    """An open gap is recorded but must NOT be silenced.

    Accepted deviations may carry a `region` (excluded from scoring); open gaps
    must not, so a real shortfall keeps counting against the agreement figure
    instead of being defined away.
    """
    data = tomllib.loads(MANIFEST.read_text())
    for gap in data.get("component.open_gap", []) + data.get("open_gap", []):
        assert "region" not in gap, (
            "an open gap must not carry an exclusion region -- that would "
            "silence a real defect")


def test_raise_floor_rewrites_the_whole_literal_and_stays_parseable(tmp_path):
    """--update must never corrupt the manifest it maintains.

    Regression: the original implementation did
    ``text.replace(f"min_agreement = {old:g}", ...)``. ``{73.0:g}`` renders
    ``"73"``, which matched the ``73`` inside ``73.0`` and left the trailing
    ``.0``, writing ``min_agreement = 84.1.0`` -- unparseable TOML. The tool
    reported success and broke its own input.
    """
    text = (
        '[[component]]\n'
        'name = "alpha"\nmodel = "m.C"\nreference = "r.stl"\n'
        'region = [0,1,0,1,0,1]\nmin_agreement = 73.0\n'
        '[[component]]\n'
        'name = "beta"\nmodel = "m.D"\nreference = "r2.stl"\n'
        'region = [0,1,0,1,0,1]\nmin_agreement = 73.0\n'
    )
    out = raise_floor(text, "beta", 84.1)
    assert "84.1.0" not in out
    data = tomllib.loads(out)          # must still parse
    floors = {c["name"]: c["min_agreement"] for c in data["component"]}
    assert floors == {"alpha": 73.0, "beta": 84.1}, "wrong component rewritten"


def test_raise_floor_rejects_an_unknown_component():
    with pytest.raises(ManifestError, match="could not locate"):
        raise_floor('[[component]]\nname = "a"\nmin_agreement = 1.0\n',
                    "nope", 2.0)
