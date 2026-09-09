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

"""Tests for ``vibe_cading/tools/lib/workspace_root.sh``.

The four shared predicates behind the dev container's pre-mount guard, exercised
in isolation by shelling out to them under **both** ``bash`` and ``sh``.  Running
both shells is the point, not thoroughness theatre: design review found one of
these predicates correct under ``dash`` and *wrong* under ``bash`` — the shell the
guard actually runs under — so a single-shell suite would have passed while the
guard accepted a ``$HOME`` mount.

Scope is deliberately the lib functions only.  These tests cannot distinguish
"the script called the function with the right argument" from "with the wrong
one"; that class lives in ``test_workspace_scripts.py``.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "vibe_cading" / "tools" / "lib" / "workspace_root.sh"

SHELLS = ["bash", "sh"]


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

def call(shell: str, snippet: str, *args: str, env: dict | None = None):
    """Source the lib under *shell* and run *snippet* with *args* as ``$1``…"""
    full_env = dict(os.environ) if env is None else env
    full_env.setdefault("LIBPATH", str(LIB))
    script = '. "$LIBPATH" || exit 1\n' + snippet
    return subprocess.run(
        [shell, "-c", script, "sh", *args],
        capture_output=True,
        text=True,
        env=full_env,
    )


def out(proc) -> str:
    return proc.stdout.strip()


def git(*args: str, cwd: pathlib.Path) -> None:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
    )
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env
    )


def make_nested_project(base: pathlib.Path, project: str = "vibe-cading") -> pathlib.Path:
    """``base/<project>/main`` as a real repo with one commit.  Returns ``main``."""
    checkout = base / project / "main"
    checkout.mkdir(parents=True)
    git("init", "-q", cwd=checkout)
    git("commit", "-q", "--allow-empty", "-m", "seed", cwd=checkout)
    return checkout


# --------------------------------------------------------------------------
# resolve_primary_checkout
# --------------------------------------------------------------------------

@pytest.mark.parametrize("shell", SHELLS)
def test_primary_checkout_from_the_checkout_itself(shell, tmp_path):
    checkout = make_nested_project(tmp_path)
    assert out(call(shell, 'resolve_primary_checkout "$1"', str(checkout))) == str(
        checkout.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_primary_checkout_from_a_sibling_worktree(shell, tmp_path):
    """The whole reason for ``--git-common-dir`` over ``--show-toplevel``."""
    checkout = make_nested_project(tmp_path)
    wt = checkout.parent / "feature-x"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=checkout)
    assert out(call(shell, 'resolve_primary_checkout "$1"', str(wt))) == str(
        checkout.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_primary_checkout_from_a_subdirectory_of_main(shell, tmp_path):
    checkout = make_nested_project(tmp_path)
    sub = checkout / "vibe_cading" / "tools"
    sub.mkdir(parents=True)
    assert out(call(shell, 'resolve_primary_checkout "$1"', str(sub))) == str(
        checkout.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_primary_checkout_surfaces_gits_own_error_for_a_non_repo(shell, tmp_path):
    """A git failure must be loud and distinguishable — never swallowed, and
    never misread by a caller as "flat clone, offer to migrate"."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    proc = call(shell, 'resolve_primary_checkout "$1"', str(plain))
    assert proc.returncode != 0
    assert str(plain) in proc.stderr
    # git's own message is carried through (2>&1), not discarded.
    assert "git" in proc.stderr.lower()
    assert proc.stderr.strip() != ""


# --------------------------------------------------------------------------
# resolve_project_root
# --------------------------------------------------------------------------

@pytest.mark.parametrize("shell", SHELLS)
def test_project_root_is_the_parent_of_main(shell, tmp_path):
    checkout = make_nested_project(tmp_path)
    assert out(call(shell, 'resolve_project_root "$1"', str(checkout))) == str(
        checkout.parent.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_project_root_from_a_sibling_worktree_is_the_same_root(shell, tmp_path):
    checkout = make_nested_project(tmp_path)
    wt = checkout.parent / "feature-x"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=checkout)
    assert out(call(shell, 'resolve_project_root "$1"', str(wt))) == str(
        checkout.parent.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_project_root_refuses_a_flat_clone(shell, tmp_path):
    flat = tmp_path / "vibe-cading"
    flat.mkdir()
    git("init", "-q", cwd=flat)
    proc = call(shell, 'resolve_project_root "$1"', str(flat))
    assert proc.returncode != 0
    assert "not named 'main'" in proc.stderr


# --------------------------------------------------------------------------
# literal_mount_source — what Docker will ACTUALLY bind-mount
# --------------------------------------------------------------------------

@pytest.mark.parametrize("shell", SHELLS)
def test_mount_source_is_the_parent(shell, tmp_path):
    checkout = make_nested_project(tmp_path)
    assert out(call(shell, 'literal_mount_source "$1"', str(checkout))) == str(
        checkout.parent.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_mount_source_resolves_through_a_symlinked_ancestor(shell, tmp_path):
    checkout = make_nested_project(tmp_path, project="real-proj")
    link = tmp_path / "sym-proj"
    link.symlink_to(checkout.parent)
    assert out(call(shell, 'literal_mount_source "$1"', str(link / "main"))) == str(
        checkout.parent.resolve()
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_mount_source_cancels_a_symlinked_checkout_lexically(shell, tmp_path):
    """The non-obvious half: when ``main`` ITSELF is a symlink, the trailing
    ``main/..`` pair is cancelled before the symlink is followed — matching what
    Docker does.  Using ``cd -P`` here instead would resolve the symlink first
    and mount its target's parent, which is the exploit path a design-review
    round reproduced live (a ``main`` symlink planted in ``$HOME``)."""
    real = make_nested_project(tmp_path, project="elsewhere")
    proj2 = tmp_path / "proj2"
    proj2.mkdir()
    (proj2 / "main").symlink_to(real)

    got = out(call(shell, 'literal_mount_source "$1"', str(proj2 / "main")))
    assert got == str(proj2.resolve())
    assert got != str(real.parent.resolve())


# --------------------------------------------------------------------------
# home_is_at_or_under — return 0 means UNSAFE (caller refuses)
# --------------------------------------------------------------------------

def home_env(home: str | None, tmp_path: pathlib.Path) -> dict:
    env = dict(os.environ)
    env["LIBPATH"] = str(LIB)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    if home is None:
        env.pop("HOME", None)
    else:
        env["HOME"] = home
    return env


@pytest.mark.parametrize("shell", SHELLS)
def test_home_equal_to_root_is_unsafe(shell, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    proc = call(shell, 'home_is_at_or_under "$1"', str(home), env=home_env(str(home), tmp_path))
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
def test_root_as_ancestor_of_home_is_unsafe(shell, tmp_path):
    home = tmp_path / "homes" / "alice"
    home.mkdir(parents=True)
    proc = call(
        shell, 'home_is_at_or_under "$1"', str(home.parent), env=home_env(str(home), tmp_path)
    )
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
def test_root_reached_through_a_symlinked_home_is_unsafe(shell, tmp_path):
    real = tmp_path / "real-home"
    real.mkdir()
    link = tmp_path / "link-home"
    link.symlink_to(real)
    proc = call(shell, 'home_is_at_or_under "$1"', str(real), env=home_env(str(link), tmp_path))
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
def test_unrelated_root_is_safe(shell, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    other = tmp_path / "projects"
    other.mkdir()
    proc = call(shell, 'home_is_at_or_under "$1"', str(other), env=home_env(str(home), tmp_path))
    assert proc.returncode == 1


@pytest.mark.parametrize("shell", SHELLS)
def test_sibling_sharing_a_name_prefix_is_safe(shell, tmp_path):
    """``/x/proj`` must not swallow ``/x/project`` — the separator matters."""
    home = tmp_path / "project"
    home.mkdir()
    root = tmp_path / "proj"
    root.mkdir()
    proc = call(shell, 'home_is_at_or_under "$1"', str(root), env=home_env(str(home), tmp_path))
    assert proc.returncode == 1


@pytest.mark.parametrize("shell", SHELLS)
def test_root_slash_is_unsafe_under_every_shell(shell, tmp_path):
    """The regression guard for the pattern that was correct under ``dash`` and
    wrong under ``bash``: with root ``/``, the stripped prefix is empty, so the
    ``/`` must sit INSIDE the quotes of the case pattern."""
    home = tmp_path / "home"
    home.mkdir()
    proc = call(shell, 'home_is_at_or_under "$1"', "/", env=home_env(str(home), tmp_path))
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("home", [None, "", "relative/path"])
def test_broken_home_fails_closed(shell, tmp_path, home):
    other = tmp_path / "projects"
    other.mkdir()
    proc = call(shell, 'home_is_at_or_under "$1"', str(other), env=home_env(home, tmp_path))
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
def test_nonexistent_root_fails_closed(shell, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    proc = call(
        shell,
        'home_is_at_or_under "$1"',
        str(tmp_path / "does-not-exist"),
        env=home_env(str(home), tmp_path),
    )
    assert proc.returncode == 0


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("odd", ["with space", "glob[star]*", "quote'and$dollar"])
def test_odd_characters_in_paths_are_handled(shell, tmp_path, odd):
    home = tmp_path / "home"
    home.mkdir()
    root = tmp_path / odd
    root.mkdir()
    assert call(
        shell, 'home_is_at_or_under "$1"', str(root), env=home_env(str(home), tmp_path)
    ).returncode == 1
    assert call(
        shell, 'home_is_at_or_under "$1"', str(root), env=home_env(str(root), tmp_path)
    ).returncode == 0
    assert out(call(shell, 'literal_mount_source "$1"', str(root))) == str(tmp_path.resolve())
