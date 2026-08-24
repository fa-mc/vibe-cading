#!/usr/bin/env python3
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
"""PreToolUse guard for `rm`, wired in .claude/settings.json.

Why a hook rather than permission rules: allow/deny patterns match text with `*`
as a wildcard, so the single pattern `rm -rf tmp/*` means BOTH "delete the
scratch directory I created" and "delete everything under tmp/". Those need
opposite answers, and a pattern cannot separate them. This hook reads the actual
command, so it can.

Policy:
  ALLOW  a delete confined to named paths under tmp/, recursive or not
         (`rm -rf tmp/probe-run`) — an agent clearing up after itself.
  DENY   a delete that would empty tmp/ wholesale (`rm -rf tmp`, `tmp/`,
         `tmp/*`), or that targets a glob / `.` / `..` / `/` / `~`.
  SILENT anything else — no decision, so the normal permission flow applies and
         the user is asked. Unparseable input is silent too: this fails to
         "ask", never to "allow".

tmp/ accumulates real working state across sessions and sibling worktrees, so a
bulk wipe destroys work the deleting agent did not create. That is the accident
this exists to stop; it is not a security boundary (see README note in the PR).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

# Operands that must never be handed to a recursive delete, whatever the flags.
_FORBIDDEN_OPERANDS = {
    "/", ".", "..", "~", "*", "-r", "-rf",
    "$HOME", "${HOME}", "~/", "/*",
}

# The wholesale-wipe spellings this guard exists to stop.
_BULK_TMP = {"tmp", "tmp/", "tmp/*", "./tmp", "./tmp/", "./tmp/*"}

_GLOB_CHARS = set("*?[]")

# Splits a command line into the pieces a shell would run separately, so a
# dangerous subcommand cannot hide behind a harmless one.
_SPLIT = re.compile(r"&&|\|\||;|\||\n")


def _decide(part: str) -> tuple[str, str] | None:
    """Return (decision, reason) for one subcommand, or None to stay silent."""
    try:
        tokens = shlex.split(part)
    except ValueError:
        return None  # unbalanced quotes — not ours to judge

    # Skip leading env assignments (FOO=bar rm ...), matching how the harness
    # itself looks past them.
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return None

    if os.path.basename(tokens[0]) != "rm":
        return None

    args = tokens[1:]
    operands: list[str] = []
    recursive = False
    end_of_flags = False

    for arg in args:
        if not end_of_flags and arg == "--":
            end_of_flags = True
            continue
        if not end_of_flags and arg.startswith("--"):
            if arg in ("--recursive", "--dir"):
                recursive = True
            continue
        if not end_of_flags and arg.startswith("-") and len(arg) > 1:
            # Combined short flags: -rf, -vrf, -fR …
            if "r" in arg[1:] or "R" in arg[1:] or "d" in arg[1:]:
                recursive = True
            continue
        operands.append(arg)

    if not operands:
        return None

    norm = [o.rstrip("/") + ("/" if o.endswith("/") else "") for o in operands]

    for o in norm:
        stripped = o.rstrip("/")
        if o in _FORBIDDEN_OPERANDS or stripped in _FORBIDDEN_OPERANDS:
            return ("deny", f"`rm` targeting {o!r} is refused outright.")
        if o in _BULK_TMP or stripped in ("tmp", "./tmp"):
            return (
                "deny",
                "This would empty tmp/ wholesale. tmp/ holds scratch state from "
                "other sessions and sibling worktrees. Delete the specific "
                "directory you created instead, e.g. `rm -rf tmp/<your-dir>`.",
            )

    # Every operand must sit under tmp/ and name something concrete.
    def _under_tmp(path: str) -> bool:
        p = path[2:] if path.startswith("./") else path
        if not p.startswith("tmp/"):
            return False
        rest = p[len("tmp/"):].strip("/")
        return bool(rest) and not (set(rest) & _GLOB_CHARS)

    if all(_under_tmp(o) for o in norm):
        return (
            "allow",
            "Delete confined to named path(s) under tmp/: "
            + ", ".join(norm),
        )

    if recursive:
        return None  # recursive outside tmp/ — let the user decide

    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # silent: normal permission flow applies

    command = (payload.get("tool_input") or {}).get("command") or ""
    if "rm" not in command:
        return

    decisions = [d for d in (_decide(p) for p in _SPLIT.split(command)) if d]
    if not decisions:
        return

    # A single dangerous piece condemns the whole command line.
    for decision, reason in decisions:
        if decision == "deny":
            break
    else:
        decision, reason = "allow", "; ".join(r for _, r in decisions)

    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)


if __name__ == "__main__":
    main()
