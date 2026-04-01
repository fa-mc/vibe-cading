#!/usr/bin/env python3
import os
import glob
import sys

HEADER_SNIPPET = "vibe-cading is free software: you can redistribute it and/or modify"

def check_headers():
    missing = []
    for file_path in glob.glob("models/**/*.py", recursive=True):
        if file_path.endswith("__init__.py"):
            with open(file_path, "r", encoding="utf-8") as f:
                if not f.read().strip():
                    continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if HEADER_SNIPPET not in content:
                missing.append(file_path)

    for file_path in glob.glob("tools/**/*.py", recursive=True):
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
