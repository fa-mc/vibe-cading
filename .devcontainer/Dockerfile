FROM python:3.11-slim

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
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh) from the official apt repository
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install CadQuery and the VS Code viewer integration
RUN pip install --no-cache-dir cadquery ocp_vscode