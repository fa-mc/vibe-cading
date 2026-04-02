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
    radial_clearance: float
    depth_clearance: float
    screw_radial_allowance: float
    screw_head_recess: float

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
            radial_clearance=data.get("radial_clearance", 0.15),
            depth_clearance=data.get("depth_clearance", 0.20),
            screw_radial_allowance=data.get("screw_radial_allowance", 0.10),
            screw_head_recess=data.get("screw_head_recess", 0.15),
        )
        
    # Hardcoded safety fallback if JSON is entirely broken
    fallback_data = {
        "radial_clearance": 0.15,
        "depth_clearance": 0.20,
        "screw_radial_allowance": 0.10,
        "screw_head_recess": 0.15
    }
    name_lower = name.lower()
    if "resin" in name_lower:
        fallback_data = {"radial_clearance": 0.05, "depth_clearance": 0.05, "screw_radial_allowance": 0.02, "screw_head_recess": 0.05}
    elif "cnc" in name_lower or "machined" in name_lower:
        fallback_data = {"radial_clearance": 0.02, "depth_clearance": 0.0, "screw_radial_allowance": 0.0, "screw_head_recess": 0.0}

    return ToleranceProfile(
        name=name,
        radial_clearance=fallback_data["radial_clearance"],
        depth_clearance=fallback_data["depth_clearance"],
        screw_radial_allowance=fallback_data["screw_radial_allowance"],
        screw_head_recess=fallback_data["screw_head_recess"]
    )

# Legacy support for screws wrapper
def get_screw_allowances(material_or_profile: str) -> dict:
    """Return clearance adjustments for screw holes based on material or machine profile."""
    prof = get_profile(material_or_profile)
    return {
        "radial_allowance": prof.screw_radial_allowance,
        "head_recess_depth": prof.screw_head_recess
    }
