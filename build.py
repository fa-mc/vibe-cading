#!/usr/bin/env python3
"""
Central build script — generates STEP files from build.toml into output/.

Usage
-----
    python build.py              # build everything in build.toml
    python build.py --list       # list configured outputs without building
    python build.py --config path/to/other.toml
"""

import sys
import argparse
import importlib
import tomllib
from pathlib import Path

import cadquery as cq

REPO_ROOT  = Path(__file__).parent
MODELS_DIR = REPO_ROOT / "models"
OUTPUT_DIR = REPO_ROOT / "output"

# Make all model packages importable (e.g. "technic_ball_bearing.axle_sleeve")
sys.path.insert(0, str(MODELS_DIR))


def _load_config(config_path: Path) -> list[dict]:
    with open(config_path, "rb") as f:
        return tomllib.load(f).get("build", [])


def build_all(config_path: Path) -> None:
    entries = _load_config(config_path)
    OUTPUT_DIR.mkdir(exist_ok=True)

    for entry in entries:
        module_path, class_name = entry["model"].rsplit(".", 1)
        output_rel  = entry["output"]
        params      = entry.get("params", {})

        output_path = OUTPUT_DIR / output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  building  {output_rel} ...", end=" ", flush=True)

        module   = importlib.import_module(module_path)
        cls      = getattr(module, class_name)
        instance = cls(**params)

        cq.exporters.export(instance.solid, str(output_path))
        print("ok")


def list_outputs(config_path: Path) -> None:
    for entry in _load_config(config_path):
        params = entry.get("params", {})
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        print(f"  {entry['output']}")
        if param_str:
            print(f"    └─ {entry['model']}({param_str})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build STEP files from build.toml")
    parser.add_argument("--config", default=str(REPO_ROOT / "build.toml"),
                        help="Path to build config (default: build.toml)")
    parser.add_argument("--list", action="store_true",
                        help="List configured outputs without building")
    args = parser.parse_args()

    config_path = Path(args.config)

    if args.list:
        list_outputs(config_path)
        return

    entries = _load_config(config_path)
    print(f"Building {len(entries)} output(s) → {OUTPUT_DIR}/")
    build_all(config_path)
    print("Done.")


if __name__ == "__main__":
    import subprocess
    import sys
    print("Checking license headers...")
    res = subprocess.run(["python3", "tools/check_license_headers.py"])
    if res.returncode != 0:
        sys.exit(res.returncode)
    main()
