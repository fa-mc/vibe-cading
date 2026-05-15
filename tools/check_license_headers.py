#!/usr/bin/env python3
"""License-header gate for ``vibe_cading/`` and ``tools/``.

Per ``CLAUDE.md`` § "Licensing & Open Source", every new Python file
in ``vibe_cading/`` or ``tools/`` must carry the AGPLv3 header at the
top of the file.  Empty ``__init__.py`` files are exempt.

``parts/`` is intentionally NOT walked — project-specific end-products
under ``parts/`` are not the OSS library distribution surface.
Contributors are still welcome to add the header on a per-file basis
for clarity, but it is not enforced.

``experiments/`` is intentionally NOT walked — R&D code carries no
release contract.
"""
import glob
import sys

HEADER_SNIPPET = "vibe-cading is free software: you can redistribute it and/or modify"


def check_headers():
    missing = []
    for pattern in ("vibe_cading/**/*.py", "tools/**/*.py"):
        for file_path in glob.glob(pattern, recursive=True):
            if file_path.endswith("__init__.py"):
                with open(file_path, "r", encoding="utf-8") as f:
                    if not f.read().strip():
                        continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if HEADER_SNIPPET not in content:
                    missing.append(file_path)

    if missing:
        print("The following files are missing the AGPLv3 license header:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    else:
        print("All Python files have the AGPLv3 license header.")
        sys.exit(0)


if __name__ == "__main__":
    check_headers()
