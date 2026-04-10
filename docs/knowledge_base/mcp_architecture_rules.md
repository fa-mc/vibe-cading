# MCP Integration & Architectural Boundaries

Based on the finalized MCP Integration Plan, the following architectural rules are strictly enforced for the `vibe-cading` repository and its interaction with the SaaS platform:

- **Two-Repository Strategy:** `vibe-cading` remains a pure, read-only AGPLv3 CAD generation engine. The MCP server, ASGI FastAPI transport, and Docker sandboxing live strictly in the private SaaS repository (`vibe-cading-platform`).
- **Dependency Isolation:** Do NOT add `mcp` or server-side web dependencies to the engine's `pyproject.toml`. They belong in the platform's `requirements.txt`.
- **Execution Isolation:** Never execute LLM-generated CadQuery code via raw local subprocesses. All execution must be routed through the platform's Docker-in-Docker `sandbox.py` to mitigate security risks, keeping the engine pure.
- **Path Abstraction:** Tools and CAD analysis scripts must return `workspace://` relative URIs (e.g., `workspace://tmp/model.step`) rather than absolute OS paths to prevent container leakage and facilitate HTTP downloads.
- **Async Design:** All MCP tool handlers wrapping the engine's scripts must be `async` to prevent blocking the platform's FastAPI event loop during heavy geometric rendering.
