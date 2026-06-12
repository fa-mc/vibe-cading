# Design: Convert devcontainer from root to a non-root user (OSS-portable)

- **Date:** 2026-06-02
- **Role:** TL (Technical Lead / Architect)
- **Status:** DESIGN ONLY — no `.devcontainer/` files edited yet; awaiting human gate.
- **Scope:** `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`. No `build.toml`,
  no model code. Touches the dev-environment contract every contributor (and both IDEs) inherits.

> This is an architecturally-significant change to a **shared, contributor-facing surface**
> (the dev environment), so it goes through a design artifact rather than a direct edit. It is
> OSS-bound: the chosen user model must carry no personal identity and must onboard an arbitrary
> external contributor on an arbitrary Linux host.

---

## 1. Problem statement (verified container-side, 2026-06-02)

The container runs as `root` (`remoteUser: "root"`). Two IDEs attach:

1. **VS Code Dev Containers** — honors `devcontainer.json`, attaches as `remoteUser` (today: `root`).
2. **Google Antigravity** — execs into the *same already-running* container as the **host UID 1000**
   (`mchen` on the host), and does **not** necessarily honor `remoteUser`.

Antigravity-as-UID-1000 currently breaks with an SSH permission error. Root causes (all verified
by inspection this session):

- **No passwd entry for UID 1000.** `/etc/passwd` contains only `root` + system accounts (18 lines,
  highest real user is `root`). UID 1000 has no entry → `$HOME` / `~` does not resolve → tools that
  derive `~/.ssh` (git over SSH, `ssh`) cannot locate config.
- **SSH keys pinned to `/root/.ssh`, group-unreadable.** `postCreateCommand` provisions keys into
  `~/.ssh` *as root* → `/root/.ssh` is `drwx------ root:1000`, key files `-rw------- root:1000`.
  Mode `600`/`700` grants the group nothing, so UID 1000 cannot read `git`, `config`, `known_hosts`
  → permission denied. (The `root:1000` group ownership is incidental, from the host mount's GID; the
  `------` group bits make it irrelevant.)
- **SSH logic is `/root`-pinned.** The provisioning copies to `~/.ssh`, but because it runs as root,
  `~` = `/root`. Any non-root user gets nothing.
- **Workspace ownership is mostly root.** Files under `/workspaces/vibe-cading` created by the root
  container process are `root:root` (≈458 of them at depth ≤3); only `.git/`, `.devcontainer/`, and
  the workspace-root dir are `1000:1000`. A non-root user cannot write the root-owned files.

### Additional hard facts that shape the design (verified this session)

- **`sudo` is NOT installed** in the container (`which sudo` → not found). The base is
  `python:3.11-slim`, which ships **no** non-root user and **no** sudo. Any postCreate fixup that
  needs to chown root-owned files must either (a) install sudo + a NOPASSWD rule, or (b) run as root
  via a hook that is not subject to `remoteUser`.
- **`postCreateCommand` runs as `remoteUser`.** Once we set `remoteUser` to the non-root user, the
  postCreate hook can no longer chown root-owned files directly — it needs elevation. (Confirmed
  against devcontainer semantics: `remoteUser` governs `devcontainer exec`, which is what both the
  postCreate hook and VS Code's in-container commands use.)
- **`pip install` target is world-readable.** `/usr/local/lib/python3.11/site-packages` is
  `drwxr-xr-x root:root`; `cadquery/` likewise. A non-root runtime user can import these fine →
  the root-time `pip install` build step needs **no** change.
- **Host `~/.ssh` mount preserves host UID numerically.** `/tmp/host-ssh` shows files owned by
  `1000:1000` (the host user's numeric UID). This is why aligning the container user to UID 1000
  makes the read-only mount directly readable without a copy-and-chown dance — though we still copy
  (the mount is read-only and `known_hosts` must be writable).
- **The "bashrc SSH setup" is `postCreateCommand`, not `.bashrc`.** `/root/.bashrc` has no SSH block;
  the SSH provisioning lives entirely in `devcontainer.json`'s `postCreateCommand`. The redesign
  therefore targets that command, not a shell rc file.

---

## 2. Design goals (restated as acceptance criteria)

| # | Goal | Acceptance test |
|---|------|-----------------|
| G1 | OSS-portable: no personal identity baked in | `grep -ri mchen .devcontainer/` returns nothing; username/UID are `ARG`-configurable |
| G2 | Works from BOTH IDEs | A real non-root user exists at UID 1000 with a valid `$HOME`, independent of whether the IDE reads `remoteUser` |
| G3 | SSH is user-correct & `$HOME`-relative | Keys land in `$HOME/.ssh` owned by the running user; never `/root`-pinned; host mount read-only at a neutral path |
| G4 | `.claude` mount moves to the new user's home | Mount target is `/home/<user>/.claude`, not `/root/.claude` |
| G5 | Workspace ownership fixup for root-owned files | Non-root user can write all workspace files after first start; idempotent across rebuilds |
| G6 | pip-as-root decision is explicit | Documented: keep root-time install (site-packages world-readable) |

---

## 3. Target user model

### Decision: conventional `vscode` user, fixed at **UID 1000 / GID 1000**, configurable via `ARG`

```dockerfile
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000
```

Rationale:

- **`vscode` is the conventional devcontainer username** (the `common-utils` "automatic" search order
  is `vscode → node → codespace → UID 1000 → root`). Choosing `vscode` maximizes interop with the
  broader devcontainer ecosystem and carries no personal identity (satisfies **G1**).
- **UID/GID 1000 is the default first-user UID on Debian/Ubuntu hosts** and is exactly the host UID
  Antigravity execs as (`mchen` = 1000). Baking the container user at 1000 means the Antigravity exec
  lands *on a real, fully-provisioned account* — this is the linchpin of **G2** (see §4).
- **`ARG`-configurable** so a contributor whose host UID is not 1000 can override at build time
  (`"build": { "args": { "USER_UID": "1001", "USER_GID": "1001" } }`), and so VS Code's
  `updateRemoteUserUID` (§4) can re-stamp the UID on the rare non-1000 host without us hardcoding it.

> **Open decision for the human (D1):** `vscode` vs reusing the host's literal name. We deliberately
> do **not** reuse `mchen` (violates G1). `vscode` is the recommendation. The only cost: a contributor
> who *likes* their prompt to show their own username won't see it — cosmetic, and overridable via the
> `USERNAME` build arg in a personal (untracked) `devcontainer` override if they care.

### Why explicit `useradd` in the Dockerfile, NOT the `common-utils` Feature

We evaluated both standard mechanisms (the brief asks for the rationale):

| Aspect | `common-utils` Feature | Explicit `useradd` in Dockerfile (CHOSEN) |
|--------|------------------------|-------------------------------------------|
| User creation | Yes (`username: automatic`) | Yes (explicit, pinned UID/GID) |
| Extra payload | Installs Oh-My-Zsh, a suite of CLI utils, optionally zsh — **unwanted bloat** for a lean CAD image | None — one `RUN` block |
| Determinism | `automatic` picks whatever it finds; behavior varies by base image | Fully explicit; reproducible byte-for-byte |
| Network dependency at build | Pulls the Feature from the registry | None beyond existing apt/pip |
| sudo setup | Feature can add it | We add it explicitly (needed for §5 fixup), scoped & visible |
| Transparency for OSS contributors | Behavior hidden behind a Feature version | Plain Dockerfile any contributor can read |

**Decision: explicit `useradd`.** This is a single-purpose, lean Python image; the Feature's value
(searching for an existing user, installing shells/utilities) is bloat we don't want, and its
`automatic` username resolution is *less* deterministic than pinning `vscode`/1000 ourselves. The
`useradd` block is ~6 lines, fully readable, and gives us exact control over the sudo rule that the
ownership fixup (§5) depends on. We are NOT trying to be image-base-agnostic here — we control the
base (`python:3.11-slim`), so explicit is strictly better than magic.

---

## 4. UID-alignment strategy (the both-IDEs linchpin)

Two independent mechanisms, layered defense:

1. **Bake the user at UID 1000 in the image (primary, IDE-agnostic).**
   Because the user is created at UID 1000 *inside the image*, **any** process execing in as host
   UID 1000 — VS Code via `remoteUser`, **or Antigravity execing as the raw host UID** — lands on the
   `vscode` account with a real `$HOME=/home/vscode`, a passwd entry, and shell. This does **not**
   depend on the IDE reading `devcontainer.json` at all. This is what fixes the Antigravity break:
   UID 1000 stops being a homeless, passwd-less UID and becomes a real user.

2. **`updateRemoteUserUID: true` (secondary, VS Code-only, for non-1000 hosts).**
   Left at its default `true`. When VS Code *builds/starts* the container on a host whose user UID
   ≠ 1000, it rewrites the container user's UID/GID in `/etc/passwd` + chowns `$HOME` to match the
   host, so bind-mounted files stay writable. Caveats we accept:
   - It only fires on the **VS Code build/start path** — Antigravity's bare exec does not trigger it.
     That is fine: on the *common* host (UID 1000) no re-stamp is needed, and on a non-1000 host the
     contributor is expected to use VS Code to build (or set the `USER_UID` build arg). We document
     this in the migration note (§8).
   - It is skipped if the target UID is 0 or already taken — neither applies (we're non-root, and
     1000 is our own user).

> **Why this matters architecturally:** the brief's hardest constraint is "an IDE that execs as an
> arbitrary host UID." We cannot make an arbitrary UID resolve to a real home *in general* without
> creating that account. We solve the *actual* case (host UID 1000) by pinning the baked user to
> 1000, and we solve the *non-1000 VS Code* case via `updateRemoteUserUID`. The residual uncovered
> case — **Antigravity on a non-1000 host** — is called out as **D2** below; it needs the `USER_UID`
> build arg set to that host's UID and a VS Code (or `devcontainer` CLI) rebuild. We judge this an
> acceptable, documented edge, not a blocker, because Antigravity execs into a container someone
> *first built* — and that build can carry the right `USER_UID`.

**Open decision (D2):** do we want to support Antigravity-on-a-non-1000-host as a first-class path?
If yes, the only robust answer is a startup hook that creates/renames the user to the execing UID —
heavier and out of scope for this pass. Recommendation: document the `USER_UID` build-arg workaround,
defer the dynamic-UID startup hook unless a real non-1000 contributor appears.

---

## 5. Workspace ownership fixup hook

### The two distinct ownership problems

1. **Pre-existing root-owned files (migration).** ≈458 files already on the host workspace, owned
   `root:root` from the *current* root container. These persist on disk across a rebuild (bind mount).
2. **Steady-state.** After the switch, files created by the non-root container are `1000:1000` — no
   problem. So the fixup is fundamentally a **one-time migration** that must also be **idempotent**
   (safe to re-run, cheap when already correct).

### Mechanism: `postCreateCommand` calling `sudo chown`, with a NOPASSWD sudoers rule baked in the image

We need elevation because `postCreateCommand` runs as the (now non-root) `remoteUser` and the files
are `root:root`. The clean, conventional devcontainer answer is passwordless sudo for the dev user:

**In the Dockerfile** (part of the `useradd` block):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends sudo \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd  --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}
```

**In `postCreateCommand`** (ownership fixup, idempotent):

```bash
sudo chown -R ${USER_UID}:${USER_GID} /workspaces/vibe-cading
```

- **Idempotent:** chown to an already-correct owner is a no-op write; re-running is harmless. On a
  clean rebuild where files are already `1000:1000`, it's effectively free.
- **Per-rebuild story:** runs every `postCreate`. After the first migration it's a fast no-op. We
  scope it to the workspace path only (not `/` — never broad-sweep a chown).
- **Why not chown in the Dockerfile:** the workspace is a **runtime bind mount**; it does not exist
  at image-build time. Dockerfile chown cannot touch it. The fixup *must* be a runtime hook. ✓ (G5)

> **Trade-off — passwordless sudo for the dev user.** This is the standard devcontainer posture
> (MS's own base images ship exactly this for `vscode`). The container is a single-developer dev
> sandbox, not a multi-tenant prod host, so NOPASSWD sudo is an accepted convenience, not a security
> regression relative to today — *today the user is literally root*. Granting `vscode` NOPASSWD sudo
> is strictly **less** privileged than the status quo (root-by-default) while restoring the principle
> that the interactive identity is non-root. We make the grant **explicit and visible** in a
> `/etc/sudoers.d/` drop-in rather than hidden in a Feature.

**Open decision (D3):** scope of the sudo grant. Options, least→most restrictive:
  - (a) `NOPASSWD:ALL` (recommended — matches MS devcontainer convention, lowest friction; the box is
    already root today so this is a net privilege *reduction*).
  - (b) `NOPASSWD: /usr/bin/chown, /usr/bin/apt-get` (minimal — only what hooks need; higher friction
    when a contributor needs to apt-install something interactively).
  Recommendation: (a). Surface to human; trivially tightened later.

### Alternative considered and rejected: `onCreateCommand`/`initializeCommand` as root

`initializeCommand` runs on the **host**, not the container — wrong layer. `onCreateCommand` runs in
the container but under the same `remoteUser` as postCreate, so it has the same elevation problem.
There is no `devcontainer.json` hook that is guaranteed to run as root once `remoteUser` is non-root
**except** by re-elevating via sudo. Hence the sudo route is the correct, conventional answer.

---

## 6. SSH provisioning redesign (`$HOME`-relative, user-correct)

### Principles

- Host `~/.ssh` mounts **read-only** at a **neutral path** (keep `/tmp/host-ssh`, IDE-agnostic, not
  tied to any user's home).
- postCreate copies into **`$HOME/.ssh`** (relative — `$HOME` now resolves correctly because the user
  has a passwd entry), owned by the **running user**, never `/root`-pinned.
- `known_hosts` must be **writable** by the user (SSH appends to it) → copy, don't symlink the mount.

### Revised `postCreateCommand` (full, ordered)

```bash
sudo chown -R ${USER_UID}:${USER_GID} /workspaces/vibe-cading \
 && mkdir -p "$HOME/.ssh" \
 && cp -a /tmp/host-ssh/. "$HOME/.ssh/" \
 && chmod 700 "$HOME/.ssh" \
 && chmod 600 "$HOME/.ssh"/* \
 && find "$HOME/.ssh" -name '*.pub' -exec chmod 644 {} + \
 && git config --global --add safe.directory /workspaces/vibe-cading
```

Changes vs today:

| Today | Revised | Why |
|-------|---------|-----|
| `chown -R $(whoami) ~/.ssh` | (dropped — files land owned by the running user already) | We `cp` as the non-root user into our own `$HOME`; no cross-ownership to repair. `$(whoami)` is fine but redundant. |
| `~` (= `/root`) | `"$HOME/.ssh"` (= `/home/vscode/.ssh`) | `$HOME`-relative; works for any user (G3) |
| no `.pub` handling | `chmod 644` on `*.pub` | public keys want 644, not 600 (matches host mount which already has `.pub` as 644) |
| `chmod 600 ~/.ssh/*` | unchanged, but now correctly scoped to the user's own home | private keys `600` |
| n/a | leading `sudo chown` of workspace | §5 fixup, run first |

Because the baked user is UID 1000 and the host mount is UID 1000, the `cp -a` reads the read-only
mount cleanly (same numeric owner) and writes into the user's own home (G2 + G3 reinforce each other).

> **Note:** `SSH_AUTH_SOCK=/ssh-agent` and the agent-forwarding posture are unchanged — they are
> `$HOME`-independent. No `.bashrc` edit is required (there is no SSH block in `.bashrc` today).

> **Open decision (D4):** if a contributor has **no** `~/.ssh` on their host, the
> `source=${localEnv:HOME}/.ssh` mount fails the container start. This is *pre-existing* behavior
> (true today too), not introduced here. Recommend a follow-up to make the mount tolerant of a
> missing source (devcontainer mounts can't be conditional in pure JSON; would need an
> `initializeCommand` to `mkdir -p ~/.ssh` on the host). Flagged, deferred — out of scope for the
> root→non-root conversion.

---

## 7. `.claude` mount relocation

Change the mount target from `/root/.claude` to the new user's home:

| Today | Revised |
|-------|---------|
| `target=/root/.claude` | `target=/home/vscode/.claude` |

- Source unchanged: `${localEnv:HOME}${localEnv:USERPROFILE}/.claude` (the `USERPROFILE` concat is a
  cross-platform host-home trick; leave it).
- `consistency=cached` unchanged.

> **Orchestrator-facing consequence (G4):** Claude Code's in-container memory dir moves from
> `/root/.claude` to `/home/vscode/.claude`. Any tooling, docs, or `settings.json` path that
> references the in-container `.claude` absolute path must be updated. The tracked
> `.claude/settings.json` lives under the **workspace** (`/workspaces/vibe-cading/.claude/…`), which
> is unaffected — only the **home** `~/.claude` mount target moves. `tools/init-claude-runtime.sh`
> operates on the workspace `.claude/`, also unaffected.

> **Open decision (D5):** the mount target hardcodes `/home/vscode`. If `USERNAME` is overridden via
> build arg, this mount path won't follow (devcontainer JSON mount targets can't interpolate build
> ARGs). Options: (a) accept the coupling and document "if you change USERNAME, also change the mount
> target" (recommended — both live in the same file, one-line edit); (b) move the `.claude` provision
> into `postCreateCommand` via a `$HOME`-relative `cp`/symlink instead of a static mount (loses the
> live-sync `consistency=cached` benefit). Recommend (a).

---

## 8. pip-install decision

**Keep the root-time `pip install` into system site-packages — no change.** Verified:
`/usr/local/lib/python3.11/site-packages` and `cadquery/` are `drwxr-xr-x root:root` → world-readable.
The non-root runtime user imports them fine. Installing as root at build time is the simplest,
most cache-friendly posture; making it a per-user install would bloat the image and break the
shared-interpreter model. (G6 satisfied: explicit decision, documented rationale.)

> One forward-looking note: if a contributor later needs `pip install --user` packages at runtime,
> those land in `$HOME/.local` (writable, fine). The base scientific stack stays system-wide.

---

## 9. Proposed concrete changes

### 9a. `.devcontainer/Dockerfile` — full revised file

```dockerfile
FROM python:3.11-slim

# Non-root user model (OSS-portable; UID/GID overridable per host).
# Pinned to 1000 by default — the conventional first-user UID on Debian/Ubuntu
# hosts and the UID an exec-based IDE (e.g. Antigravity) lands on. Override via
# build args on a host whose user UID differs.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

# Install system dependencies required by OpenCASCADE/CadQuery
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    libxrender1 \
    fontconfig \
    fonts-liberation \
    curl \
    gnupg \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh) from the official apt repository
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install CadQuery and the VS Code viewer integration (system site-packages,
# world-readable — usable by the non-root runtime user).
RUN pip install --no-cache-dir cadquery ocp_vscode

# Create the non-root dev user with passwordless sudo. Passwordless sudo is the
# standard devcontainer posture for the dev user and is strictly LESS privileged
# than the previous root-by-default setup; it is required by postCreateCommand to
# chown the runtime-mounted workspace (which does not exist at build time).
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd  --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

USER ${USERNAME}
```

Notes:
- `sudo` moved into the first apt block.
- The `useradd` block is **last** so the image's default `USER` is the non-root user (defense in
  depth: even an IDE ignoring `remoteUser` and not specifying a user gets `vscode`).
- `-m` creates `/home/vscode`; `-s /bin/bash` matches the existing root shell.
- If a host collides on GID 1000 (rare), `updateRemoteUserUID`/the build arg handle it; document in D2.

### 9b. `.devcontainer/devcontainer.json` — full revised file

```jsonc
{
    "name": "CadQuery Dev",
    "build": {
        "dockerfile": "Dockerfile"
        // To override the user on a non-1000 host, add:
        // "args": { "USER_UID": "1001", "USER_GID": "1001" }
    },
    "customizations": {
        "vscode": {
            "extensions": [
                "bernhard-42.ocp-cad-viewer",
                "Anthropic.claude-code"
            ]
        }
    },
    "forwardPorts": [
        3939
    ],
    "remoteUser": "vscode",
    "updateRemoteUserUID": true,
    "mounts": [
        "source=${localEnv:HOME}/.ssh,target=/tmp/host-ssh,type=bind,readonly",
        "source=${localEnv:HOME}${localEnv:USERPROFILE}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached"
    ],
    "remoteEnv": {
        "SSH_AUTH_SOCK": "/ssh-agent",
        "PYTHONPATH": "/workspaces/vibe-cading"
    },
    "postCreateCommand": "sudo chown -R 1000:1000 /workspaces/vibe-cading && mkdir -p \"$HOME/.ssh\" && cp -a /tmp/host-ssh/. \"$HOME/.ssh/\" && chmod 700 \"$HOME/.ssh\" && chmod 600 \"$HOME/.ssh\"/* && find \"$HOME/.ssh\" -name '*.pub' -exec chmod 644 {} + && git config --global --add safe.directory /workspaces/vibe-cading"
}
```

Changes vs today:
- `remoteUser`: `"root"` → `"vscode"`.
- `updateRemoteUserUID: true` added explicitly (it's the default, but making it explicit documents
  intent for the non-1000-host case).
- `.claude` mount target: `/root/.claude` → `/home/vscode/.claude`.
- `postCreateCommand`: prepend `sudo chown` workspace fixup; make SSH block `$HOME`-relative; add
  `.pub` mode handling.

> **Note on the `chown 1000:1000` literal in postCreate:** JSON `postCreateCommand` can't read the
> Dockerfile `ARG`s. We hardcode `1000:1000` to match the default user. If `USER_UID`/`USER_GID` are
> overridden, this literal must be updated too — same one-file edit as D5. Alternatively `sudo chown
> -R "$(id -u):$(id -g)" /workspaces/vibe-cading` makes it self-adjusting to the running user; this
> is **the more robust form** and I recommend it over the literal. (Open decision D6.)

**D6 recommendation:** use `sudo chown -R "$(id -u):$(id -g)" /workspaces/vibe-cading` so the fixup
auto-targets whatever UID the user actually is — eliminates the literal-1000 coupling and is correct
even after `updateRemoteUserUID` re-stamps a non-1000 UID. Final postCreate becomes:

```bash
sudo chown -R "$(id -u):$(id -g)" /workspaces/vibe-cading && mkdir -p "$HOME/.ssh" && cp -a /tmp/host-ssh/. "$HOME/.ssh/" && chmod 700 "$HOME/.ssh" && chmod 600 "$HOME/.ssh"/* && find "$HOME/.ssh" -name '*.pub' -exec chmod 644 {} + && git config --global --add safe.directory /workspaces/vibe-cading
```

---

## 10. Migration / rebuild note (for the orchestrator + human)

1. **This requires a container rebuild**, not just a reattach. After merging, the human runs
   *Dev Containers: Rebuild Container* in VS Code (or `devcontainer up --build`). The image gains the
   `vscode` user; the running container switches identity.
2. **First-start ownership migration is automatic** via the postCreate `sudo chown` — the ≈458
   pre-existing `root:root` workspace files get re-owned to `1000:1000` on the first non-root start.
   This is a one-time cost (a few seconds); subsequent starts no-op.
3. **`.claude` memory path moves** in-container from `/root/.claude` → `/home/vscode/.claude`.
   The host source dir is unchanged; only the in-container mount point differs. No data migration on
   the host side. (G4 — flagged to orchestrator above.)
4. **SSH keys re-provision** into `/home/vscode/.ssh` on first start. The old `/root/.ssh` becomes
   irrelevant (root is no longer the interactive user). No manual key move needed — postCreate copies
   from the read-only host mount.
5. **Antigravity** should now work: it execs as host UID 1000, which is the real `vscode` user with a
   home and readable `~/.ssh`. **Verification step for the human:** after rebuild, from Antigravity
   run `whoami && echo $HOME && ls -l ~/.ssh && ssh -T git@github.com` — expect `vscode`,
   `/home/vscode`, readable keys, and a successful GitHub auth handshake.
6. **Non-1000 hosts (D2):** a contributor whose host UID ≠ 1000 should either let VS Code's
   `updateRemoteUserUID` re-stamp (VS Code path) or set `build.args.USER_UID/USER_GID` to their host
   UID before building (required for the Antigravity-on-non-1000 path).

---

## 11. Open decisions for the human (consolidated)

| ID | Decision | TL recommendation |
|----|----------|-------------------|
| D1 | Username: `vscode` vs other | **`vscode`** — conventional, identity-free, `ARG`-overridable |
| D2 | Support Antigravity on a non-1000 host as first-class? | **Defer** — document `USER_UID` build-arg workaround; add a dynamic-UID startup hook only if a real non-1000 contributor appears |
| D3 | sudo scope: `NOPASSWD:ALL` vs minimal command list | **`NOPASSWD:ALL`** — matches MS devcontainer convention, net privilege *reduction* vs today's root; tighten later if desired |
| D4 | Missing host `~/.ssh` makes container start fail (pre-existing) | **Defer** — out of scope for root→non-root; follow-up `initializeCommand` to `mkdir -p` on host |
| D5 | `.claude` mount target hardcodes `/home/vscode` | **Accept coupling** — document "change USERNAME → change mount target too"; both in one file |
| D6 | postCreate chown: literal `1000:1000` vs `$(id -u):$(id -g)` | **`$(id -u):$(id -g)`** — self-adjusting, survives `updateRemoteUserUID` re-stamp |

---

## 12. Trade-offs summary

- **+ Restores non-root interactive identity** (security hygiene) while being *less* privileged than
  today's root default; sudo is the only elevation, explicit and scoped.
- **+ Fixes both IDEs** by making UID 1000 a real account — the Antigravity break disappears without
  Antigravity needing to honor `remoteUser`.
- **+ OSS-portable** — no personal identity; UID/GID configurable; conventional `vscode` user.
- **− Requires a one-time rebuild + ownership migration** (seconds, automated, idempotent).
- **− Mount targets and the postCreate chown carry a soft coupling to `USERNAME`/UID** (mitigated by
  the `$(id -u)` form for chown and a one-line doc note for the mount).
- **− Non-1000-host + Antigravity remains a documented manual step** (build-arg), not fully automatic.

---

## 13. Handoff

- **Next role:** Developer applies §9a/§9b verbatim (adopting D6's `$(id -u)` chown form) once the
  human signs off the open decisions in §11. No model code, no `build.toml`.
- **No CI impact expected** — CI runs in GitHub Actions, not this devcontainer. Confirm the CI
  workflow does not assume a root container (it does not — it uses `ubuntu-latest` runners).
- **Verification gate (post-apply, human-run):** the §10.5 Antigravity check + a VS Code rebuild that
  lands on `vscode` with a writable workspace and working git-over-SSH.
```
