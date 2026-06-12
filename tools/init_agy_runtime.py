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

#!/usr/bin/env python3
"""
Initialize runtime commands and skills for the Antigravity CLI (agy).
"""

import os
import sys
import glob
import re

DRY_RUN = "--check" in sys.argv or "-n" in sys.argv


def extract_frontmatter_and_body(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 2)
    if len(parts) >= 3:
        fm_text = parts[1]
        body = parts[2]
        fm = {}
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip().strip("'").strip('"')
        return fm, body
    return {}, content



def generate_agy_skill(name, fm, body):
    title = name.replace("-", " ").replace("_", " ").title()
    description = fm.get("description", "")
    arg_hint = fm.get("argument-hint", "")

    # Construct frontmatter
    fm_lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f'argument-hint: "{arg_hint}"',
        "---",
    ]
    frontmatter_part = "\n".join(fm_lines)

    # Search for code block with python3/bash run
    code_block_pattern = re.compile(r"```\n(.*?)\n```", re.DOTALL)
    match = code_block_pattern.search(body)
    if match:
        before = body[: match.start()].strip()
        code_content = match.group(1).strip()
        after = body[match.end() :].strip()

        body_parts = []
        body_parts.append(f"# {title}\n")
        body_parts.append("## Overview")
        body_parts.append(before)
        body_parts.append("\n## Utility Scripts (Optional)")
        body_parts.append(
            "If your slash command triggers a Python/shell script (the standard CLI pattern for `agy` skills), you can document and invoke it here:"
        )
        body_parts.append(f"```bash\n{code_content}\n```")
        if after:
            body_parts.append("\n" + after)
        new_body = "\n".join(body_parts)
    else:
        new_body = f"# {title}\n\n## Overview\n{body.strip()}"

    return f"{frontmatter_part}\n\n{new_body}\n"


def write_or_diff(target, content):
    if DRY_RUN:
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                existing = f.read()
            if existing == content:
                print(f"  unchanged: {target}")
            else:
                print(f"  would write: {target}")
        else:
            print(f"  would write: {target}")
    else:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  wrote: {target}")


def main():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    commands_dir = os.path.join(repo_root, "vibe", "commands")

    if not os.path.isdir(commands_dir):
        print(f"Error: {commands_dir} is not a directory.")
        sys.exit(1)

    print("Generating agy skills from vibe/commands:")
    for canonical in glob.glob(os.path.join(commands_dir, "*.md")):
        name = os.path.splitext(os.path.basename(canonical))[0]
        target = os.path.join(repo_root, ".agents", "skills", name, "SKILL.md")

        fm, body = extract_frontmatter_and_body(canonical)
        content = generate_agy_skill(name, fm, body)
        write_or_diff(target, content)

    if DRY_RUN:
        print("\n(dry-run) no changes written. Re-run without --check to apply.")
    else:
        print("\nDone. Skills under .agents/skills/ now reflect canonical content under vibe/.")


if __name__ == "__main__":
    main()
