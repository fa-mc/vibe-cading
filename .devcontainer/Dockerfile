FROM python:3.11-slim

# Non-root user model (OSS-portable; UID/GID overridable per host).
# Pinned to 1000 by default — the conventional first-user UID on Debian/Ubuntu
# hosts and the UID an exec-based IDE (e.g. Antigravity) lands on. Override via
# build args on a host whose user UID differs. VS Code's updateRemoteUserUID
# (set in devcontainer.json) re-stamps these to the host UID automatically on
# the VS Code build/start path, so this default is a fallback, not a hardcode.
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
    xdg-utils \
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

# Install the Antigravity CLI (`agy`) — Antigravity's terminal coding agent.
# This container is driven from both VS Code and Antigravity (see the
# updateRemoteUserUID / UID-1000 notes above; the VS Code Claude Code
# extension is likewise baked into this image via devcontainer.json), so
# `agy` is installed for the non-root user to be usable from Antigravity's
# terminal.
#
# Runs AFTER the USER switch, on purpose: `agy` self-updates in place during
# normal runs, so the binary must live in a user-writable location
# (~/.local/bin) rather than a root-owned system path, or self-update breaks.
# `--dir` pins the install location so it never depends on $HOME resolution.
#
# Intentionally NOT version-pinned: the installer always fetches the latest
# build from its release manifest, and `agy` self-updates at runtime — so the
# exact version is not reproducible from this Dockerfile alone. The installer
# SHA512-checks the download against that same manifest, which guards against
# a corrupted/truncated download but NOT against a compromised release
# endpoint (manifest, URL, and hash share one origin — there is no
# independent signature). The installer also runs the freshly-downloaded
# binary once at build time to configure the shell env (a soft-failed step).
#
# ENV HOME makes the build-time user home deterministic (Docker does not
# reliably derive $HOME from the USER instruction, and the installer stages
# downloads under $HOME) and matches the image's runtime user. ENV PATH
# surfaces ~/.local/bin in every shell and in Antigravity's exec context —
# not just interactive bash, which is all the installer's own .bashrc edit
# would cover.
ENV HOME=/home/${USERNAME}
ENV PATH=/home/${USERNAME}/.local/bin:${PATH}
RUN curl -fsSL https://antigravity.google/cli/install.sh \
        | bash -s -- --dir /home/${USERNAME}/.local/bin
