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

import json
import os
from pathlib import Path
from dataclasses import dataclass

# Parse local .env file if it exists
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

def get_default_profile_name() -> str:
    """
    Returns the globally configured machine profile name.
    Defaults to 'fdm_standard' as it's the safest (loosest) tolerance fallback.
    """
    return os.getenv("VIBE_MACHINE_PROFILE", "fdm_standard")

@dataclass
class ToleranceProfile:
    name: str
    z_clearance: float
    press_fit: float
    slip_fit: float
    free_fit: float

def _load_json_profiles() -> dict:
    """Loads profiles from machine_profiles.json and machine_profiles_user.json."""
    profiles = {}

    # 1. Load repository defaults
    repo_file = Path(__file__).parent.parent / "machine_profiles.json"
    if repo_file.exists():
        try:
            with open(repo_file, "r") as f:
                profiles.update(json.load(f))
        except Exception as e:
            print(f"Warning: Could not parse machine_profiles.json - {e}")

    # 2. Load user overrides (takes precedence)
    user_file = Path(__file__).parent.parent / "machine_profiles_user.json"
    if user_file.exists():
        try:
            with open(user_file, "r") as f:
                user_profiles = json.load(f)
                for k, v in user_profiles.items():
                    if k in profiles and isinstance(profiles[k], dict) and isinstance(v, dict):
                        profiles[k].update(v)
                    else:
                        profiles[k] = v
        except Exception as e:
            print(f"Warning: Could not parse machine_profiles_user.json - {e}")

    return profiles

def get_profile(name: str | None = None) -> ToleranceProfile:
    """Load a specific manufacturing tolerance profile."""
    name = name or get_default_profile_name()

    profiles = _load_json_profiles()

    if name in profiles:
        data = profiles[name]
        return ToleranceProfile(
            name=name,
            z_clearance=data.get("z_clearance", data.get("z_clearance", 0.20)),
            press_fit=data.get("press_fit", 0.04),
            slip_fit=data.get("slip_fit", 0.05),
            free_fit=data.get("free_fit", data.get("radial_clearance", 0.15)),
        )
        
    # Hardcoded safety fallback if JSON is entirely broken
    fallback_data = {
        "z_clearance": 0.20,
        "press_fit": 0.04,
        "slip_fit": 0.05,
        "free_fit": 0.15
    }
    name_lower = name.lower()
    if "resin" in name_lower:
        fallback_data = {"z_clearance": 0.05, "press_fit": 0.02, "slip_fit": 0.03, "free_fit": 0.05}
    elif "cnc" in name_lower or "machined" in name_lower:
        fallback_data = {"z_clearance": 0.0, "press_fit": 0.0, "slip_fit": 0.01, "free_fit": 0.02}

    return ToleranceProfile(
        name=name,
        z_clearance=fallback_data["z_clearance"],
        press_fit=fallback_data["press_fit"],
        slip_fit=fallback_data["slip_fit"],
        free_fit=fallback_data["free_fit"]
    )

# Legacy support for screws wrapper
def get_screw_allowances(material_or_profile: str) -> dict:
    """Return clearance adjustments for screw holes based on material or machine profile."""
    prof = get_profile(material_or_profile)
    return {
        "radial_allowance": prof.free_fit,
        "head_recess_depth": prof.z_clearance
    }
