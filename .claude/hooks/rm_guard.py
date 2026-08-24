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

Why a hook rather than permission rules: those match text with `*` as a
wildcard, so the single pattern `rm -rf tmp/*` means BOTH "delete the scratch
directory I created" and "delete everything under tmp/". Those need opposite
answers and a pattern cannot separate them. This hook reads the real command.

Policy:
  ALLOW  only when the ENTIRE command is one `rm` whose every operand is a
         literal, non-escaping path under tmp/ (`rm -rf tmp/probe-run`).
  DENY   any fragment that would empty tmp/ wholesale, or that targets a glob,
         `.`, `..`, `/`, `~`, or $HOME.
  SILENT everything else — no decision, so the user is asked.

THE ALLOW IS DELIBERATELY NARROW, and the reason is the important part: a
PreToolUse `allow` approves the WHOLE tool call, not the fragment that earned
it. Judging only the `rm` pieces of a compound command turns this guard into an
auto-approver — `rm -rf tmp/x && curl … | sh` would run unprompted. So a
command containing anything other than one safe `rm` is never allowed; at most
it is denied, otherwise it falls through to a prompt.

Everything uncertain resolves toward "ask": unbalanced quotes, shell
metacharacters that could expand ($, backtick, braces, ~, globs), paths that
normalize outside tmp/, unparseable input, or any error. This fails to "ask",
never to "allow".

tmp/ accumulates scratch state across sessions and sibling worktrees, so a bulk
wipe destroys work the deleting agent did not create. That accident is what this
prevents. It is NOT a security boundary — `python3 -c`, `find -delete`, `xargs`
and friends are untouched.
"""
from __future__ import annotations

import json
import os
import posixpath
import re
import shlex
import sys

# Globs select an unknown set of victims. Rooted at tmp/ that IS the bulk wipe,
# so they are denied rather than merely disqualified from ALLOW.
_GLOB_CHARS = set("*?[]")

# Shell expansions whose value is unknowable here. These never ALLOW, but they
# are not denied either — `tmp/$DIR` may be perfectly legitimate, so ask.
_EXPAND_CHARS = set("$`{}\\!\"'")

# Operands never acceptable to a delete, whatever the flags.
_FORBIDDEN = {"/", ".", "..", "~", "*", ""}

_SPLIT = re.compile(r"&&|\|\||;|\||\n")

_ALLOW, _DENY = "allow", "deny"


def _classify_operand(raw: str) -> str:
    """Return 'safe' (a literal path strictly inside tmp/), 'bulk', or 'unknown'."""
    p = raw[2:] if raw.startswith("./") else raw
    p = p.rstrip("/")

    # Checked FIRST: `~` and friends carry metacharacters, so a
    # metacharacter test placed earlier would divert them away from DENY.
    if raw in _FORBIDDEN or p in _FORBIDDEN or p.startswith("~"):
        return "bulk"

    if set(raw) & _GLOB_CHARS:
        # A glob rooted at tmp/ (or bare) can match everything under it.
        return "bulk" if p == "tmp" or p.startswith("tmp/") else "unknown"

    if set(raw) & _EXPAND_CHARS:
        return "unknown"

    # Normalize `..` BEFORE deciding containment: `tmp/../tmp` is tmp/, and
    # `tmp/../../main` is not under tmp/ at all.
    norm = posixpath.normpath(p)
    if norm in (".", "..", "/") or norm.startswith("../") or norm.startswith("/"):
        return "bulk" if norm in (".", "..", "/") else "unknown"
    if norm in ("tmp",):
        return "bulk"
    if norm.startswith("tmp/") and len(norm) > len("tmp/"):
        return "safe"
    return "unknown"


def _decide(fragment: str) -> tuple[str, str] | None:
    """Classify one subcommand. None = no opinion."""
    try:
        tokens = shlex.split(fragment)
    except ValueError:
        return None

    # Look past leading env assignments and privilege/wrapper prefixes, so
    # `sudo rm -rf /` is judged as the `rm` it is rather than skipped.
    while tokens and (
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0])
        or os.path.basename(tokens[0]) in ("sudo", "command", "env", "nice", "time")
    ):
        tokens = tokens[1:]
    if not tokens:
        return None

    if os.path.basename(tokens[0]) != "rm":
        return None

    operands: list[str] = []
    end_of_flags = False
    for arg in tokens[1:]:
        if not end_of_flags and arg == "--":
            end_of_flags = True
            continue
        if not end_of_flags and arg.startswith("-") and len(arg) > 1:
            continue
        operands.append(arg)

    if not operands:
        return None

    kinds = [_classify_operand(o) for o in operands]
    if "bulk" in kinds:
        return (_DENY,
                "Refused: this would empty tmp/ wholesale (or target /, ., .., ~). "
                "tmp/ holds scratch state from other sessions and sibling "
                "worktrees. Delete the specific directory you created, e.g. "
                "`rm -rf tmp/<your-dir>`.")
    if all(k == "safe" for k in kinds):
        return (_ALLOW, "Delete confined to named path(s) under tmp/: "
                + ", ".join(operands))
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command.strip():
        return

    fragments = [f for f in _SPLIT.split(command) if f.strip()]
    verdicts = [_decide(f) for f in fragments]

    # A single dangerous fragment condemns the whole line.
    for v in verdicts:
        if v and v[0] == _DENY:
            _emit(_DENY, v[1])
            return

    # ALLOW only if the command is exactly ONE fragment and that fragment is a
    # safe rm. An `allow` blesses the entire tool call, so anything unexamined
    # riding alongside would be approved with it.
    if len(fragments) == 1 and verdicts[0] and verdicts[0][0] == _ALLOW:
        _emit(_ALLOW, verdicts[0][1])
    # else: stay silent -> normal permission flow asks.


def _emit(decision: str, reason: str) -> None:
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)


if __name__ == "__main__":
    main()
