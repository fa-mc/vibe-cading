import json
import os
from dataclasses import dataclass

@dataclass
class ToleranceProfile:
    name: str
    radial_clearance: float
    depth_clearance: float
    screw_radial_allowance: float
    screw_head_recess: float
    
    @classmethod
    def default_fdm(cls) -> "ToleranceProfile":
        return cls(
            name="fdm_standard",
            radial_clearance=0.15,
            depth_clearance=0.20,
            screw_radial_allowance=0.10,
            screw_head_recess=0.15,
        )
        
    @classmethod
    def default_resin(cls) -> "ToleranceProfile":
        return cls(
            name="resin_precise",
            radial_clearance=0.05,
            depth_clearance=0.05,
            screw_radial_allowance=0.02,
            screw_head_recess=0.05,
        )
        
    @classmethod
    def default_cnc(cls) -> "ToleranceProfile":
        return cls(
            name="cnc",
            radial_clearance=0.02,
            depth_clearance=0.0,
            screw_radial_allowance=0.0,
            screw_head_recess=0.0,
        )

# Legacy support for screws
def get_screw_allowances(material_or_profile: str) -> dict:
    """Return clearance adjustments for screw holes based on material or machine profile."""
    # First check predefined profiles
    if material_or_profile.lower() in ("resin", "resin_precise"):
        prof = ToleranceProfile.default_resin()
    elif material_or_profile.lower() in ("cnc", "machined"):
        prof = ToleranceProfile.default_cnc()
    elif material_or_profile.lower() in ("pla", "petg", "abs", "fdm", "fdm_standard"):
        prof = ToleranceProfile.default_fdm()
    else:
        prof = ToleranceProfile.default_fdm()
        
    return {
        "radial_allowance": prof.screw_radial_allowance,
        "head_recess_depth": prof.screw_head_recess
    }

def get_profile(name: str = "fdm_standard") -> ToleranceProfile:
    """Load a specific manufacturing tolerance profile."""
    # First, attempt to load from a custom local JSON file if it exists
    if os.path.exists("machine_profiles.json"):
        try:
            with open("machine_profiles.json", "r") as f:
                custom_profiles = json.load(f)
                if name in custom_profiles:
                    data = custom_profiles[name]
                    return ToleranceProfile(
                        name=name,
                        radial_clearance=data.get("radial_clearance", 0.15),
                        depth_clearance=data.get("depth_clearance", 0.2),
                        screw_radial_allowance=data.get("screw_radial_allowance", 0.1),
                        screw_head_recess=data.get("screw_head_recess", 0.15),
                    )
        except Exception as e:
            print(f"Warning: Could not parse machine_profiles.json - {e}")

    # Fallback to internal defaults
    name_lower = name.lower()
    if "resin" in name_lower:
        return ToleranceProfile.default_resin()
    if "cnc" in name_lower or "machin" in name_lower:
        return ToleranceProfile.default_cnc()
    return ToleranceProfile.default_fdm()
