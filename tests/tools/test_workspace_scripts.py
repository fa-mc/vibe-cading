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

"""End-to-end tests for the workspace setup/guard scripts and the
``devcontainer.json`` fragment they depend on.

Three groups:

* **the scripts as scripts** — ``setup-workspace.sh`` and
  ``check-workspace-setup.sh`` driven as subprocesses against throwaway
  fixtures.  This is the layer ``test_workspace_root.py`` structurally cannot
  reach: the lib predicates behave identically whether the caller passed the
  right directory or the wrong one, and "passed the wrong directory" is exactly
  what two of the design's blocking review findings were.
* **static assertions on ``.devcontainer/devcontainer.json``** — no Docker
  needed.  The ``postCreateCommand`` / ``initializeCommand`` pair was wrong in
  three consecutive design-review rounds; these assertions are what stops a
  fourth recurrence during a future edit.
* **one execution-based assertion** on the shipped ``postCreateCommand``
  fragment, ``HOME``-scoped to a fixture.  A for-loop's exit status is not
  something a static check can see.

Nothing here starts a container, and nothing writes outside ``tmp_path``.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SETUP = REPO_ROOT / "vibe_cading" / "tools" / "setup-workspace.sh"
CHECK = REPO_ROOT / "vibe_cading" / "tools" / "check-workspace-setup.sh"
DEVCONTAINER = REPO_ROOT / ".devcontainer" / "devcontainer.json"

MARKER = ".vibe-cading-project-root"
SHELLS = ["bash", "sh"]


# --------------------------------------------------------------------------
# fixtures / harness
# --------------------------------------------------------------------------

def base_env(home: pathlib.Path | str | None, tmp_path: pathlib.Path) -> dict:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
        XDG_CONFIG_HOME=str(tmp_path / "xdg"),
    )
    if home is None:
        env.pop("HOME", None)
    else:
        env["HOME"] = str(home)
    return env


def git(*args: str, cwd: pathlib.Path, env: dict | None = None) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=env or base_env(None, cwd),
    )


def make_repo(path: pathlib.Path, env: dict) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", cwd=path, env=env)
    git("commit", "-q", "--allow-empty", "-m", "seed", cwd=path, env=env)
    return path


def run_setup(checkout: pathlib.Path, env: dict, *args: str, stdin: str = ""):
    return subprocess.run(
        [str(SETUP), *args],
        cwd=checkout,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def run_check(opened: pathlib.Path, env: dict):
    return subprocess.run(
        ["bash", str(CHECK), str(opened)], capture_output=True, text=True, env=env
    )


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home"
    h.mkdir()
    return h


# ==========================================================================
# setup-workspace.sh — refusals
# ==========================================================================

def test_refuses_when_the_project_root_is_home(tmp_path, home):
    """The ``~/main`` case: a checkout named ``main`` sitting directly in $HOME
    makes $HOME itself the project root, i.e. the whole home directory would be
    bind-mounted read-write."""
    env = base_env(home, tmp_path)
    checkout = make_repo(home / "main", env)

    proc = run_setup(checkout, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert not (home / MARKER).exists()
    assert not (checkout / "docker" / ".env").exists()


def test_refuses_when_home_is_reached_through_a_symlink(tmp_path):
    """$HOME given as a symlink must not defeat the check — both sides are
    physically resolved."""
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    link_home = tmp_path / "link-home"
    link_home.symlink_to(real_home)

    env = base_env(link_home, tmp_path)
    checkout = make_repo(real_home / "main", env)

    proc = run_setup(checkout, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert not (real_home / MARKER).exists()


def test_fails_closed_when_home_is_unset(tmp_path):
    env = base_env(None, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)

    proc = run_setup(checkout, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert not (checkout.parent / MARKER).exists()


@pytest.mark.skipif(
    not os.access("/", os.W_OK), reason="requires a writable / (root); the `/` clause is "
    "additionally covered at lib level by test_workspace_root.py's root-slash case"
)
def test_refuses_when_the_project_root_is_slash(tmp_path, home):  # pragma: no cover
    env = base_env(home, tmp_path)
    checkout = make_repo(pathlib.Path("/main"), env)
    try:
        proc = run_setup(checkout, env)
        assert proc.returncode == 1
        assert "REFUSE" in proc.stderr
    finally:
        subprocess.run(["rm", "-rf", "/main"], check=False)


# ==========================================================================
# setup-workspace.sh — happy path
# ==========================================================================

def test_nested_happy_path_writes_env_then_marker(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    root = checkout.parent

    proc = run_setup(checkout, env)
    assert proc.returncode == 0, proc.stderr

    env_file = checkout / "docker" / ".env"
    assert env_file.exists()
    # An exact line match, not a substring check: VIBE_WORKDIR must be the
    # CHECKOUT (root/main), and f"VIBE_WORKDIR={root}" is a strict PREFIX of
    # that correct value, so a substring assertion here cannot distinguish
    # "wrote the checkout" from "wrote the root" -- the bug this guards is
    # writing dirname(root) or otherwise dropping the /main.
    lines = env_file.read_text().splitlines()
    assert f"VIBE_WORKDIR={checkout}" in lines
    assert (root / MARKER).exists()


def test_rerunning_the_happy_path_is_idempotent(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)

    assert run_setup(checkout, env).returncode == 0
    second = run_setup(checkout, env)
    assert second.returncode == 0, second.stderr
    assert "already correct" in second.stdout


def test_marker_is_written_at_the_project_root_not_inside_the_repo(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)

    run_setup(checkout, env)
    assert (checkout.parent / MARKER).exists()
    assert not (checkout / MARKER).exists()


# ==========================================================================
# setup-workspace.sh — flat -> nested migration
# ==========================================================================

def test_flat_clone_migrates_under_yes(tmp_path, home):
    """The mainstream case: a flat clone at ``$HOME/vibe-cading``.  The migration
    makes THAT directory the project root, so it must be accepted — the
    prospective root is the checkout itself, not its parent."""
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)

    proc = run_setup(flat, env, "--yes")
    assert proc.returncode == 0, proc.stderr
    assert (flat / "main" / ".git").exists()
    assert "Re-run this script" in proc.stdout
    # Migration alone must not authorize anything.
    assert not (flat / MARKER).exists()
    assert not (flat / "main" / "docker" / ".env").exists()


def test_flat_clone_that_is_home_itself_is_refused_before_any_move(tmp_path, home):
    """The negative half of the same predicate: a ``git init``-ed home directory
    must never be migrated, because $HOME would become the project root."""
    env = base_env(home, tmp_path)
    make_repo(home, env)
    (home / "keepme").write_text("x", encoding="utf-8")

    proc = run_setup(home, env, "--yes")
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert not (home / "main").exists()
    assert (home / "keepme").exists()


def test_migration_is_declined_by_default(tmp_path, home):
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)

    proc = run_setup(flat, env, stdin="n\n")
    assert proc.returncode == 1
    assert not (flat / "main").exists()
    assert not (flat / MARKER).exists()


def test_migration_refuses_non_interactively_without_yes(tmp_path, home):
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)

    proc = run_setup(flat, env, stdin="")
    assert proc.returncode == 1
    assert not (flat / "main").exists()


def test_rerun_after_migration_completes_setup(tmp_path, home):
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)
    assert run_setup(flat, env, "--yes").returncode == 0

    checkout = flat / "main"
    proc = run_setup(checkout, env)
    assert proc.returncode == 0, proc.stderr
    assert (flat / MARKER).exists()
    assert f"VIBE_WORKDIR={flat}" in (checkout / "docker" / ".env").read_text()


def test_migration_refuses_when_another_worktree_exists(tmp_path, home):
    """Every worktree's ``.git`` holds an ABSOLUTE path into the checkout being
    moved; the ``mv`` would silently break all of them."""
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=flat, env=env)

    proc = run_setup(flat, env, "--yes")
    assert proc.returncode == 1
    assert "worktree" in proc.stderr
    assert not (flat / "main").exists()


def test_migration_refuses_on_a_stale_worktree_entry_and_names_prune(tmp_path, home):
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=flat, env=env)
    subprocess.run(["rm", "-rf", str(wt)], check=True)

    proc = run_setup(flat, env, "--yes")
    assert proc.returncode == 1
    assert "prune" in proc.stderr
    assert not (flat / "main").exists()


def test_run_from_a_worktree_targets_the_primary_checkout(tmp_path, home):
    """Invoked from a worktree of a flat clone, the script must act on the ONE
    real checkout — not on whichever worktree it happened to be started in.
    (It then refuses, because that worktree exists; the discriminator is which
    path it reports.)"""
    env = base_env(home, tmp_path)
    flat = make_repo(home / "vibe-cading", env)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=flat, env=env)

    proc = run_setup(wt, env, "--yes")
    assert str(flat) in proc.stdout
    assert str(wt) not in proc.stdout
    assert proc.returncode == 1
    assert not (wt / "main").exists()


# ==========================================================================
# setup-workspace.sh — docker/.env validation
# ==========================================================================

def test_stale_env_file_is_refused_without_force(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    env_file = checkout / "docker" / ".env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("VIBE_WORKDIR=/somewhere/else/main\n", encoding="utf-8")

    proc = run_setup(checkout, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert env_file.read_text() == "VIBE_WORKDIR=/somewhere/else/main\n"
    assert not (checkout.parent / MARKER).exists()


def test_force_overwrites_a_stale_env_file(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    env_file = checkout / "docker" / ".env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("VIBE_WORKDIR=/somewhere/else/main\n", encoding="utf-8")

    proc = run_setup(checkout, env, "--force")
    assert proc.returncode == 0, proc.stderr
    assert f"VIBE_WORKDIR={checkout}" in env_file.read_text()
    assert (checkout.parent / MARKER).exists()


# ==========================================================================
# check-workspace-setup.sh — the pre-mount guard
# ==========================================================================

def test_guard_accepts_a_set_up_project(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    assert run_setup(checkout, env).returncode == 0

    proc = run_check(checkout, env)
    assert proc.returncode == 0, proc.stderr


def test_guard_accepts_a_sibling_worktree(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    run_setup(checkout, env)
    wt = checkout.parent / "feature-x"
    git("worktree", "add", "-q", "-b", "feature-x", str(wt), cwd=checkout, env=env)

    proc = run_check(wt, env)
    assert proc.returncode == 0, proc.stderr


def test_guard_refuses_without_a_marker(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)

    proc = run_check(checkout, env)
    assert proc.returncode == 1
    assert "marker" in proc.stderr


def test_guard_refuses_a_worktree_created_outside_the_project(tmp_path, home):
    """Git-valid, needs no privilege, and a genuine marker sits at the real
    root — yet the directory Docker would mount is a different one entirely."""
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    run_setup(checkout, env)
    assert (checkout.parent / MARKER).exists()

    rogue_parent = home / "rogue"
    rogue_parent.mkdir()
    wt = rogue_parent / "main"
    git("worktree", "add", "-q", "-b", "rogue", str(wt), cwd=checkout, env=env)

    proc = run_check(wt, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert str(rogue_parent) in proc.stderr


def test_guard_refuses_a_main_symlink_planted_in_home(tmp_path, home):
    """No worktree involved: a symlink named ``main`` inside $HOME is git-valid
    and would bind-mount the whole home directory if the guard resolved the
    symlink before applying ``..``."""
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    run_setup(checkout, env)

    (home / "main").symlink_to(checkout)
    proc = run_check(home / "main", env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr


def test_guard_refuses_when_git_root_equals_home_even_with_a_valid_marker(tmp_path, home):
    """The ``$HOME/main`` case: git-root and mount-src AGREE (both resolve to
    $HOME), so the mismatch clause above cannot catch it -- only the live
    $HOME/``/`` re-check can. Deleting that clause leaves the rest of this
    suite fully green, so it needs its own regression guard. The marker here
    is hand-planted, not written by ``setup-workspace.sh`` (which already
    refuses to write one at $HOME) -- this is the Known-Risks scenario of a
    marker created without running the real checks, and a genuine marker must
    not be sufficient on its own."""
    env = base_env(home, tmp_path)
    checkout = make_repo(home / "main", env)
    (home / MARKER).write_text("2026-01-01\n", encoding="utf-8")

    proc = run_check(checkout, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr
    assert "$HOME" in proc.stderr


def test_guard_refuses_a_symlinked_checkout_even_when_nothing_else_would_catch_it(tmp_path, home):
    """Isolates the new symlink-leaf refusal from the pre-existing mismatch
    clause. A symlink placed OUTSIDE the project directory it points into (as
    in test_guard_refuses_a_main_symlink_planted_in_home) already trips the
    git-root-vs-mount-source mismatch on its own -- that does not exercise
    this check at all. Here the symlink is a SIBLING of the real checkout,
    inside the SAME project directory: "sibling/.." and "main/.." both
    lexically collapse to the same project root, so git_root == mount_src and
    the mismatch clause stays silent. Confirmed by mutation: deleting the new
    check turns this from REFUSE into ACCEPT, whereas the planted-in-$HOME
    variant above stays REFUSE regardless (it never depended on this check)."""
    env = base_env(home, tmp_path)
    project = tmp_path / "vibe-cading"
    checkout = make_repo(project / "main", env)
    run_setup(checkout, env)
    shortcut = project / "shortcut"
    shortcut.symlink_to(checkout)

    proc = run_check(shortcut, env)
    assert proc.returncode == 1
    assert "symlink" in proc.stderr


def test_guard_accepts_when_only_an_ancestor_is_symlinked(tmp_path, home):
    """The new symlinked-checkout refusal must not overreach: a symlinked
    ANCESTOR directory (the project directory itself, reached via a symlink)
    is a supported layout and must still be accepted end-to-end."""
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "real-proj" / "main", env)
    run_setup(checkout, env)
    sym_proj = tmp_path / "sym-proj"
    sym_proj.symlink_to(checkout.parent)

    proc = run_check(sym_proj / "main", env)
    assert proc.returncode == 0, proc.stderr


def test_guard_refuses_a_subdirectory_of_main(tmp_path, home):
    env = base_env(home, tmp_path)
    checkout = make_repo(tmp_path / "vibe-cading" / "main", env)
    run_setup(checkout, env)
    sub = checkout / "vibe_cading"
    sub.mkdir()

    proc = run_check(sub, env)
    assert proc.returncode == 1
    assert "REFUSE" in proc.stderr


def test_guard_refuses_a_flat_clone(tmp_path, home):
    env = base_env(home, tmp_path)
    flat = make_repo(tmp_path / "vibe-cading", env)

    proc = run_check(flat, env)
    assert proc.returncode == 1
    assert "not named 'main'" in proc.stderr


# ==========================================================================
# devcontainer.json — static contract
# ==========================================================================

def strip_jsonc(text: str) -> str:
    """Remove ``//`` comments outside string literals.

    Deliberately string-literal-aware: a naive stripper would corrupt any value
    containing ``//`` (a URL, a path).  There is no JSONC parser among this
    project's dependencies, and adding one for two fields is not worth it.
    """
    out = []
    in_string = False
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and text[i : i + 2] == "//":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


@pytest.fixture(scope="module")
def devcontainer() -> dict:
    return json.loads(strip_jsonc(DEVCONTAINER.read_text(encoding="utf-8")))


# The substitution tokens the devcontainer CLI expands *textually*.  Enumerated
# rather than a blanket "no ${...}" check, which would false-positive on the
# fragment's own ordinary shell expansions (${d}, ${d%/}, ${VIBE_OPENED:?...}).
SUBSTITUTION_TOKENS = re.compile(
    r"\$\{(?:local|container)WorkspaceFolder(?:Basename)?\}"
    r"|\$\{devcontainerId\}"
    r"|\$\{(?:local|container)Env:[^}]*\}"
)


def test_the_token_pattern_can_actually_fail():
    """Positive control for the check below: the pattern must match the known
    defective form it exists to reject, or it is not a check at all."""
    defective = 'git config --global --add safe.directory ${containerWorkspaceFolder}'
    assert len(SUBSTITUTION_TOKENS.findall(defective)) == 1


def test_post_create_command_interpolates_no_host_path(devcontainer):
    """A host directory named ``pr$(touch PWNED)oj`` must not be able to reach a
    shell.  ``postCreateCommand`` gets the opened path through ``remoteEnv``, as
    an environment variable, never as a textual substitution."""
    assert SUBSTITUTION_TOKENS.findall(devcontainer["postCreateCommand"]) == []


def test_post_create_command_is_wired_to_remote_env(devcontainer):
    """Catches the editing mistake — renaming one side of the pair — that would
    reintroduce a silently-unset ``VIBE_OPENED`` (``dirname ""`` → ``.``, whole
    chain exits 0 having provisioned nothing)."""
    assert "$VIBE_OPENED" in devcontainer["postCreateCommand"]
    assert "VIBE_OPENED" in devcontainer["remoteEnv"]
    assert ":?" in devcontainer["postCreateCommand"]


def test_initialize_command_keeps_both_entries_and_the_array_form(devcontainer):
    init = devcontainer["initializeCommand"]
    assert isinstance(init, dict)
    assert isinstance(init["seedClaudeCredentials"], str)
    assert isinstance(init["checkWorkspaceSetup"], list)
    assert init["checkWorkspaceSetup"][0] == "bash"
    assert init["checkWorkspaceSetup"][-1] == "${localWorkspaceFolder}"


def test_workspace_mount_is_not_hardcoded(devcontainer):
    assert devcontainer["workspaceMount"] == (
        "source=${localWorkspaceFolder}/..,target=${localWorkspaceFolder}/..,type=bind"
    )
    assert devcontainer["workspaceFolder"] == "${localWorkspaceFolder}"


# ==========================================================================
# devcontainer.json — the postCreateCommand fragment, actually executed
# ==========================================================================

def split_fragment(post_create: str) -> tuple[str, str]:
    """Return ``(shipped, buggy)`` — the guard + VIBE_ROOT + loop, ``&&``-joined
    exactly as shipped, and the pre-fix variant it must be distinguishable from.

    The ``sudo chown`` step and the SSH-key tail are dropped on purpose: running
    them here would either fail on any host without passwordless ``sudo`` (red
    regardless of which loop form is under test, i.e. not diagnostic) or, on a
    host that has it, mutate the invoking user's real ``~/.ssh`` permissions.
    """
    parts = post_create.split(" && ")
    assert parts[2].startswith("sudo chown"), parts[2]
    assert parts[3].startswith("for d in"), parts[3]
    shipped = " && ".join([parts[0], parts[1], parts[3]])
    buggy = " && ".join(
        [
            parts[0],
            parts[1],
            'for d in "$VIBE_ROOT"/*/; do [ -e "${d}.git" ] && '
            'git config --global --add safe.directory "${d%/}"; done',
        ]
    )
    return shipped, buggy


@pytest.mark.parametrize("shell", SHELLS)
def test_safe_directory_loop_survives_a_non_git_last_directory(shell, tmp_path, devcontainer):
    """A for-loop's exit status is its LAST command's.  With the ``&&`` body, a
    project root whose lexically-last directory has no ``.git`` makes the whole
    ``&&``-chained ``postCreateCommand`` exit 1 — silently aborting every step
    after it (the SSH-key copy, the chmods).  Both directions are asserted: a
    test that only ever saw one form pass could not tell the fixture from the
    fix."""
    shipped, buggy = split_fragment(devcontainer["postCreateCommand"])

    root = tmp_path / "proj"
    (root / "main" / ".git").mkdir(parents=True)
    (root / "zz-plain").mkdir()          # lexically last, not a checkout

    env = base_env(tmp_path / "fixture-home", tmp_path)
    (tmp_path / "fixture-home").mkdir()
    env["VIBE_OPENED"] = str(root / "main")

    ok = subprocess.run(
        [shell, "-c", shipped + " && echo SENTINEL"],
        capture_output=True, text=True, env=env,
    )
    assert ok.returncode == 0, ok.stderr
    assert "SENTINEL" in ok.stdout

    bad = subprocess.run(
        [shell, "-c", buggy + " && echo SENTINEL"],
        capture_output=True, text=True, env=env,
    )
    assert bad.returncode != 0
    assert "SENTINEL" not in bad.stdout

    # ...and the loop did the work it exists for, in the fixture HOME only.
    gitconfig = (tmp_path / "fixture-home" / ".gitconfig").read_text()
    assert str(root / "main") in gitconfig


@pytest.mark.parametrize("shell", SHELLS)
def test_fragment_aborts_loudly_when_vibe_opened_is_unset(shell, tmp_path, devcontainer):
    shipped, _ = split_fragment(devcontainer["postCreateCommand"])
    env = base_env(tmp_path / "fixture-home", tmp_path)
    (tmp_path / "fixture-home").mkdir()
    env.pop("VIBE_OPENED", None)

    proc = subprocess.run(
        [shell, "-c", shipped + " && echo SENTINEL"],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode != 0
    assert "SENTINEL" not in proc.stdout
    assert "VIBE_OPENED" in proc.stderr


@pytest.mark.parametrize("shell", SHELLS)
def test_fragment_does_not_execute_a_hostile_directory_name(shell, tmp_path, devcontainer):
    shipped, _ = split_fragment(devcontainer["postCreateCommand"])

    root = tmp_path / "pr$(touch PWNED)oj"
    (root / "main" / ".git").mkdir(parents=True)
    env = base_env(tmp_path / "fixture-home", tmp_path)
    (tmp_path / "fixture-home").mkdir()
    env["VIBE_OPENED"] = str(root / "main")

    proc = subprocess.run(
        [shell, "-c", shipped + " && echo SENTINEL"],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "SENTINEL" in proc.stdout
    assert not (tmp_path / "PWNED").exists()
    assert str(root / "main") in (tmp_path / "fixture-home" / ".gitconfig").read_text()
