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

# Shared workspace-layout resolution for vibe-cading's host-side setup scripts.
#
# Sourced (never executed) by BOTH vibe_cading/tools/setup-workspace.sh and
# vibe_cading/tools/check-workspace-setup.sh.  One implementation on purpose:
# the two prior attempts at this mechanism (PRs #81 / #83) each shipped a
# separate copy of "find the project root", and the copies disagreeing is what
# produced the security findings those PRs were closed over.
#
# POSIX sh compatible; exercised under BOTH bash and sh in CI
# (tests/tools/test_workspace_root.py).  Requires git >= 2.31 (--path-format).
#
# Supported hosts: Linux, macOS, WSL2.  Not native Windows PowerShell/cmd.
#
# Locals are `_wr_`-prefixed rather than declared with `local`, which is not
# POSIX; the prefix avoids clobbering a caller's variables in any shell.

# resolve_primary_checkout <opened-folder-path>
# Prints the absolute path of the PRIMARY checkout (the one holding the real
# .git) on stdout -- invariant to whether <opened-folder-path> IS that
# checkout or any worktree of it, because --git-common-dir always resolves
# to the ONE real .git no matter which worktree you ask from (unlike
# --show-toplevel, which returns the ASKING worktree's own top level).
# This is the single source of truth for "where is the checkout," used by
# BOTH scripts and by every step of setup-workspace.sh's own migration logic
# (a caller that instead used --show-toplevel from its own $PWD would migrate
# the WORKTREE it happened to be invoked from, not the primary checkout, when
# run from a worktree of a flat clone).
# Requires git >= 2.31 (--path-format). Distinguishes a git failure (wrong
# git version, not a repo at all, permission error -- whatever git itself
# reported, captured via 2>&1) from a git SUCCESS that simply isn't named
# `main` -- that second case is resolve_project_root's job below, not this
# function's; this function has no opinion on naming.
# Residual gap (known limitation, not defended): this assumes the toplevel's
# .git is reached normally. A checkout using `git --separate-git-dir` (an
# uncommon, deliberate choice, not this repo's convention) could make
# dirname(--git-common-dir) resolve somewhere other than the toplevel. That
# fails CLOSED today (the result's basename is then unlikely to be `main`,
# so resolve_project_root refuses) rather than silently misresolving.
resolve_primary_checkout() {
    _wr_opened="$1"
    if ! _wr_common="$(cd "$_wr_opened" 2>&1 && git rev-parse --path-format=absolute --git-common-dir 2>&1)"; then
        echo "git could not resolve a checkout at $_wr_opened (requires git >= 2.31 for --path-format): $_wr_common" >&2
        return 1
    fi
    ( cd "$(dirname "$_wr_common")" && pwd -P )
}

# resolve_project_root <opened-folder-path>
# Prints the project root on stdout (git-derived, via resolve_primary_checkout
# above); exits 1 with a message on stderr if the primary checkout is not
# named `main`.
resolve_project_root() {
    _wr_opened="$1"
    _wr_main="$(resolve_primary_checkout "$_wr_opened")" || return 1
    case "$(basename "$_wr_main")" in
        main) : ;;
        *) echo "primary checkout is not named 'main': $_wr_main" >&2; return 1 ;;
    esac
    dirname "$_wr_main"
}

# literal_mount_source <opened-folder-path>
# Prints the directory Docker will actually bind-mount for
# source=${localWorkspaceFolder}/... Verified to agree with Docker's real
# resolution, including through a symlinked ancestor OR a symlinked checkout
# itself: both a LOGICAL `cd "$opened/.."` (note: NOT `cd -P`) followed by
# `pwd -P`, and Docker's own /.. handling, collapse the trailing
# "component/.." pair lexically before resolving any remaining symlink,
# rather than resolving `component` first. This is a DIFFERENT (and for this
# purpose, the CORRECT) result than either (a) fully realpath-ing $opened
# first and then taking dirname, or (b) using `cd -P` for this step --
# `cd -P` resolves `component` as a symlink BEFORE applying `..`, which
# diverges from Docker: `cd -P` here mounts $HOME through a symlink named
# `main` placed inside it, a real exploit reproduced with a live `docker run`
# during design review (a planted ~/.ssh/id_rsa was read from inside the
# container).
# Do NOT add `-P` to the `cd` below.
literal_mount_source() {
    ( cd "$1/.." && pwd -P )
}

# home_is_at_or_under <candidate-root>
# TRUE (return 0) means UNSAFE -- the caller must refuse. Fails closed on
# unset/empty/non-absolute $HOME, and on any path that cannot be resolved.
# Both sides physically resolved (so a symlinked /home cannot sneak past),
# trailing-slash-safe.
home_is_at_or_under() {
    _wr_root="$1"
    case "${HOME:-}" in
        /*) : ;;
        *) return 0 ;;   # unset, empty, or relative -> unsafe -> caller refuses
    esac
    _wr_home_p="$(cd "$HOME" && pwd -P)" || return 0
    _wr_root_p="$(cd "$_wr_root" && pwd -P)" || return 0
    case "$_wr_home_p" in
        "$_wr_root_p") return 0 ;;
        # The "/" MUST be inside the quotes -- "${x%/}"/* left bare fails to
        # match anything in bash (though not dash) when $_wr_root_p is "/"
        # (the stripped value is empty, and a quoted empty prefix followed by
        # an UNQUOTED /* is not the same case pattern as one quoted string
        # "empty/*"). Verified under both bash and dash before relying on it --
        # the explicit `root == "/"` clause at both call sites is ALSO kept
        # regardless (belt-and-suspenders, not redundant).
        "${_wr_root_p%/}/"*) return 0 ;;
        *) return 1 ;;
    esac
}
