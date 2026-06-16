import os
import subprocess
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Resolve the build-provenance SHA. Git is authoritative for an in-tree
        # build (a developer's source checkout). But the CI release path builds
        # the wheel from the unpacked *sdist* in an isolated dir with no `.git`,
        # so `git rev-parse` fails there; fall back to the VIBE_BUILD_SHA env var
        # (the release workflow sets it to the tagged commit) before giving up.
        # The env name is host-neutral on purpose — the GitHub-specific mapping
        # (VIBE_BUILD_SHA=${{ github.sha }}) lives in .github/workflows/release.yml,
        # not here. See docs/releasing.md ("Two distinct identifiers").
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        except Exception:
            sha = os.environ.get("VIBE_BUILD_SHA", "").strip() or "unknown"
        header = """# This file is part of vibe-cading.
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

"""
        with open("vibe_cading/__commit__.py", "w") as f:
            f.write(header)
            f.write(f'__commit__ = "{sha}"\n')
