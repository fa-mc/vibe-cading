def get_screw_allowances(material: str) -> dict:
    """Return clearance adjustments for screw holes based on print material."""
    profiles = {
        "PLA": {"radial_allowance": 0.05, "head_recess_depth": 0.1},
        "PETG": {"radial_allowance": 0.15, "head_recess_depth": 0.2},
        "ABS": {"radial_allowance": 0.1, "head_recess_depth": 0.1},
        "ASA": {"radial_allowance": 0.2, "head_recess_depth": 0.2},
    }
    return profiles.get(material.upper(), profiles["PLA"])
