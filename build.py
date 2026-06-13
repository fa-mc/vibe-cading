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
import tomllib
from pathlib import Path

import cadquery as cq

# Shared model-class loader.  ``ensure_models_on_path`` inserts the repo root
# on ``sys.path`` so that fully-qualified dotted paths in ``build.toml``
# (e.g. ``vibe_cading.mechanical.hinge.PrintInPlaceHinge`` or
# ``parts.arrma_vorteks_223s.esc_mount.EscMount``) resolve.  See
# ``vibe_cading/tools/model_loader.py`` for the full sys.path contract.
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for vibe_cading.* import
from vibe_cading.tools.model_loader import ensure_models_on_path, load_solid  # noqa: E402

REPO_ROOT  = Path(__file__).parent
OUTPUT_DIR = REPO_ROOT / "output"

ensure_models_on_path()


def _load_config(config_path: Path) -> list[dict]:
    with open(config_path, "rb") as f:
        return tomllib.load(f).get("build", [])


def build_all(config_path: Path) -> None:
    entries = _load_config(config_path)
    OUTPUT_DIR.mkdir(exist_ok=True)

    for entry in entries:
        output_rel = entry["output"]
        params     = entry.get("params", {})

        output_path = OUTPUT_DIR / output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  building  {output_rel} ...", end=" ", flush=True)

        _, solid = load_solid(entry["model"], params)

        cq.exporters.export(solid, str(output_path))
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
    res = subprocess.run(["python3", "vibe_cading/tools/check_license_headers.py"])
    if res.returncode != 0:
        sys.exit(res.returncode)
    main()
