FROM python:3.11-slim

# Install system dependencies required by OpenCASCADE/CadQuery
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install CadQuery and the VS Code viewer integration
RUN pip install --no-cache-dir cadquery ocp_vscode