#!/usr/bin/env bash
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

# Pre-mount guard for the dev container.  Runs ON THE HOST, before any bind
# mount exists, from .devcontainer/devcontainer.json's array-form
# `initializeCommand` entry `checkWorkspaceSetup`.  The opened folder arrives
# as argv[1] -- as DATA, never interpolated into a shell command string.
#
# Exits non-zero (which aborts container creation) unless ALL THREE hold:
#
#   1. the git-derived project root and the directory Docker will ACTUALLY
#      bind-mount are the same directory.  A marker alone cannot establish
#      this: a worktree created outside its project directory, or a symlink
#      named `main` planted in $HOME, is git-valid and would otherwise mount
#      $HOME read-write while a perfectly genuine marker sits at the real root;
#   2. that live mount source is not $HOME, an ancestor of $HOME, or `/` --
#      re-checked NOW, not merely at the time the marker was written;
#   3. the `.vibe-cading-project-root` marker is present -- i.e. a human ran
#      vibe_cading/tools/setup-workspace.sh once and accepted this layout.
#
# Requires git >= 2.31 (--path-format), via the shared lib.  The lib
# distinguishes a GIT FAILURE (too old, not a repo, permission error -- all
# reported with git's own message) from a git success whose primary checkout
# simply is NOT NAMED `main`.  It does not distinguish "too old" from "not a
# repo" from each other; neither this script nor its reader needs to.
#
# Supported hosts: Linux, macOS, WSL2.  Not native Windows PowerShell/cmd.
#
# The shebang is documentation: `initializeCommand` invokes this as
# ["bash", "<abs path>", "<opened folder>"], so bash is selected there.

set -u

. "$(dirname "$0")/lib/workspace_root.sh" || exit 1

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <opened-folder-path>" >&2
    exit 1
fi

opened="$1"

# literal_mount_source's correctness rests on Docker/the devcontainer CLI
# collapsing "component/.." lexically before resolving any symlink -- verified
# for the CLI/Docker versions this design was reviewed against (see the
# design doc), but not something CI can pin (it does not drive real Docker).
# Refusing outright when the OPENED checkout itself is a symlink closes that
# whole class independently of anyone's normalization semantics: no
# legitimate layout needs the checkout itself to be a symlink (a symlinked
# ANCESTOR directory -- e.g. the project directory reached via a symlink --
# is unaffected by this check and stays supported).
if [ -L "$opened" ]; then
    echo "REFUSE: $opened is a symlink. Open the real checkout directly, not a" >&2
    echo "symlink to it." >&2
    exit 1
fi

git_root="$(resolve_project_root "$opened")" || exit 1
mount_src="$(literal_mount_source "$opened")" || {
    echo "ERROR: could not resolve the parent of $opened." >&2
    exit 1
}

if [ "$mount_src" != "$git_root" ]; then
    echo "REFUSE: this checkout's git-resolved project root ($git_root) does not" >&2
    echo "match what would actually be mounted ($mount_src)." >&2
    echo "This happens when a worktree (or the opened folder itself) is not" >&2
    echo "exactly a sibling of main inside its project directory -- e.g. a" >&2
    echo "worktree created elsewhere, a subdirectory of main opened directly," >&2
    echo "or a worktree nested more than one level deep." >&2
    exit 1
fi

if [ "$mount_src" = "/" ] || home_is_at_or_under "$mount_src"; then
    echo "REFUSE: would bind-mount $mount_src, which is \$HOME or an ancestor of it." >&2
    exit 1
fi

if [ ! -f "$mount_src/.vibe-cading-project-root" ]; then
    echo "ERROR: no project-root marker at $mount_src." >&2
    echo "Run vibe_cading/tools/setup-workspace.sh once after cloning." >&2
    exit 1
fi
