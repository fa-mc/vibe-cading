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

# One-time host-side workspace setup.  Run once after cloning, BEFORE the first
# "Reopen in Container":
#
#     cd vibe-cading/main && vibe_cading/tools/setup-workspace.sh
#
# What it does, in order:
#
#   1. locates the primary checkout from git (not from $PWD's name, so running
#      it from a sibling worktree still finds the one real checkout);
#   2. if the clone is FLAT (checkout not named `main`), offers the mandatory
#      migration into the nested `<project>/main` layout -- refusing first if
#      any other worktree exists (the mv would break every absolute gitdir
#      pointer) or if the prospective project root would be $HOME or `/`;
#   3. refuses outright if the project root is $HOME, an ancestor of $HOME,
#      or `/`;
#   4. writes (or validates) the gitignored docker/.env Compose reads;
#   5. writes the `.vibe-cading-project-root` marker the dev container's
#      pre-mount guard requires.
#
# The judgment this script exists to make is made ONCE, explicitly, by a human
# looking at one real invocation with real error messages -- rather than being
# re-derived from directory-content heuristics on every container start.  The
# container-start guard (vibe_cading/tools/check-workspace-setup.sh) then
# re-validates, live, that the directory about to be mounted really is the one
# validated here.
#
# Options:
#   --yes     accept the flat -> nested migration non-interactively
#   --force   overwrite a docker/.env whose VIBE_WORKDIR disagrees
#   -h        this help
#
# Supported hosts: Linux, macOS, WSL2.  Not native Windows PowerShell/cmd.
# Requires git >= 2.31 (--path-format), via the shared lib.

set -u

. "$(dirname "$0")/lib/workspace_root.sh" || exit 1

MARKER_NAME=".vibe-cading-project-root"

assume_yes=0
force=0
for arg in "$@"; do
    case "$arg" in
        --yes) assume_yes=1 ;;
        --force) force=1 ;;
        -h|--help)
            echo "usage: setup-workspace.sh [--yes] [--force]"
            echo
            echo "One-time host-side workspace setup; run once after cloning, from"
            echo "inside the checkout, BEFORE the first \"Reopen in Container\"."
            echo
            echo "  --yes     accept the flat -> nested migration non-interactively"
            echo "  --force   overwrite a docker/.env whose VIBE_WORKDIR disagrees"
            echo "  -h        this help"
            exit 0
            ;;
        *)
            echo "ERROR: unknown option: $arg (try --help)" >&2
            exit 1
            ;;
    esac
done

# refuse_unsafe_root <candidate-root> -- shared by the pre-migration check
# (against the PROSPECTIVE root) and the post-migration check (against the
# real one).  The `== "/"` clause is deliberately separate from
# home_is_at_or_under's glob, not folded into it.
refuse_unsafe_root() {
    _root="$1"
    if [ "$_root" = "/" ]; then
        echo "REFUSE: the project root would be / -- refusing to set up a workspace there." >&2
        return 1
    fi
    if home_is_at_or_under "$_root"; then
        echo "REFUSE: the project root would be $_root, which is \$HOME or an ancestor" >&2
        echo "of it (or \$HOME is unset/empty/relative, which fails closed)." >&2
        echo "Move the clone into a directory of its own and re-run." >&2
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# 1. Locate the primary checkout
# ---------------------------------------------------------------------------
# A git failure here is NOT "flat clone, offer to migrate" -- it is fatal, with
# git's own message already on stderr from the lib.
checkout="$(resolve_primary_checkout "$PWD")" || exit 1

# ---------------------------------------------------------------------------
# 2. Flat -> nested migration (mandatory; a flat clone is a waypoint, never an
#    end state)
# ---------------------------------------------------------------------------
if [ "$(basename "$checkout")" != "main" ]; then
    name="$(basename "$checkout")"
    parent="$(dirname "$checkout")"

    echo "This clone is FLAT: the checkout is at"
    echo "    $checkout"
    echo
    echo "vibe-cading requires the nested layout, where the checkout is named"
    echo "\`main\` inside a project directory that also holds sibling worktrees:"
    echo "    $checkout/main"
    echo
    echo "The migration moves the checkout one level down (two renames, via a"
    echo "temporary name).  Nothing outside $checkout is touched."
    echo

    # (a) Refuse if any worktree besides the primary checkout exists.  Every
    #     worktree's .git file and every entry under main/.git/worktrees/ holds
    #     an ABSOLUTE path into the checkout being moved; the mv silently breaks
    #     all of them.  A stale/prunable entry also counts here -- that fails
    #     closed, which is right, but the remedy differs, so name both.
    wt_count="$(git -C "$checkout" worktree list --porcelain | grep -c '^worktree ')"
    if [ "$wt_count" -gt 1 ]; then
        echo "REFUSE: $((wt_count - 1)) worktree(s) besides the primary checkout exist." >&2
        echo "Moving the checkout would break their absolute gitdir pointers." >&2
        echo "Remove unwanted worktrees with \`git worktree remove <path>\`, or if one" >&2
        echo "was deleted outside git, \`git worktree prune\`, then re-run." >&2
        exit 1
    fi

    # (b) The migration nests the checkout one level deeper, so $checkout ITSELF
    #     becomes the project root -- not dirname("$checkout").  A flat clone at
    #     $HOME/vibe-cading (the mainstream case) is therefore fine; a checkout
    #     that IS $HOME is refused before any mv.
    refuse_unsafe_root "$checkout" || exit 1

    if [ "$assume_yes" -ne 1 ]; then
        printf 'Migrate now? [y/N] '
        if ! read -r reply; then
            echo >&2
            echo "REFUSE: no answer (not an interactive terminal). Re-run with --yes to accept." >&2
            exit 1
        fi
        case "$reply" in
            y|Y|yes|YES) : ;;
            *) echo "Declined -- nothing moved, no marker written." >&2; exit 1 ;;
        esac
    fi

    cd "$parent" || exit 1
    if ! mkdir "$name.tmp"; then
        echo "ERROR: $name.tmp already exists at $parent -- remove or rename it and re-run." >&2
        exit 1
    fi
    mv "$name" "$name.tmp/main" && mv "$name.tmp" "$name" || {
        echo "ERROR: migration failed part-way. Inspect $parent/$name and $parent/$name.tmp." >&2
        exit 1
    }

    # Deliberately do NOT continue in this process: the mv just invalidated
    # $0, $PWD and the sourced lib's path.
    echo
    echo "Layout migrated. Re-run this script from:"
    echo "    $checkout/main"
    exit 0
fi

# ---------------------------------------------------------------------------
# 3. Resolve the project root (guaranteed nested past step 2)
# ---------------------------------------------------------------------------
root="$(dirname "$checkout")"

# ---------------------------------------------------------------------------
# 4. Refuse an unsafe root
# ---------------------------------------------------------------------------
refuse_unsafe_root "$root" || exit 1

# ---------------------------------------------------------------------------
# 5. Write / validate docker/.env
# ---------------------------------------------------------------------------
# Always the MAIN checkout's docker/, never the worktree this script may have
# been invoked from -- every worktree has its own docker/, so "inside the repo"
# alone would be ambiguous.  Gitignored (.gitignore's unanchored `.env`).
env_file="$checkout/docker/.env"
workdir="$root/main"

if [ -f "$env_file" ]; then
    existing="$(sed -n 's/^VIBE_WORKDIR=//p' "$env_file" | tail -n 1)"
    if [ "$existing" = "$workdir" ]; then
        echo "docker/.env already correct (VIBE_WORKDIR=$workdir)."
    elif [ "$force" -eq 1 ]; then
        existing_note="$existing"
        [ -n "$existing_note" ] || existing_note="(no VIBE_WORKDIR line)"
        echo "Overwriting docker/.env: $existing_note -> $workdir"
        existing=""
    else
        echo "REFUSE: $env_file already sets" >&2
        echo "    VIBE_WORKDIR=${existing:-(no VIBE_WORKDIR line)}" >&2
        echo "but this workspace resolves to" >&2
        echo "    VIBE_WORKDIR=$workdir" >&2
        echo "Re-run with --force to overwrite it (the file is rewritten ENTIRELY;" >&2
        echo "any hand-added VIBE_PROJECT / VIBE_VIEWER_PORT lines are lost)." >&2
        exit 1
    fi
fi

if [ ! -f "$env_file" ] || [ "$force" -eq 1 ]; then
    mkdir -p "$(dirname "$env_file")" || exit 1
    {
        echo "# Generated by vibe_cading/tools/setup-workspace.sh — safe to edit or delete."
        echo "# A --force re-run REWRITES THIS FILE ENTIRELY: if you hand-added"
        echo "# VIBE_PROJECT / VIBE_VIEWER_PORT to run a second checkout concurrently,"
        echo "# re-add them after a --force re-run; they are not preserved across it."
        echo "VIBE_WORKDIR=$workdir"
    } > "$env_file" || exit 1
    echo "Wrote $env_file"
fi

# ---------------------------------------------------------------------------
# 6. Write the marker
# ---------------------------------------------------------------------------
# At the PROJECT ROOT -- always outside the git repository, so it never needs a
# .gitignore entry.  The guard checks existence only; the date is informational.
marker="$root/$MARKER_NAME"
date -u +%Y-%m-%d > "$marker" || exit 1
echo "Wrote $marker"

echo
echo "Workspace ready:"
echo "    project root : $root"
echo "    checkout     : $checkout"
echo "You can now open $checkout (or any sibling worktree) and Reopen in Container."
