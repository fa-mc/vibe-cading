# MCP Integration Project & Migration Plan

## 1. Project Overview

This project aims to introduce a Model Context Protocol (MCP) service to the `vibe-cading` repository. The MCP server will expose our CAD evaluation scripts (`preview.py`, `hole_finder.py`, generation logic, etc.) as standardized tools. This enables local AI assistants (like Claude Desktop, Cursor, and VS Code Copilot) to directly interact with our CadQuery logic and validation tools, significantly boosting developer productivity and laying the groundwork for the future SaaS platform.

## 2. Architecture & Design Principles

*   **Strict Separation of Concerns:**
    *   **The Client (LLM/Agent):** The existing agent instructions (Admin, Designer, Developer in `.github/prompts/`) will continue to dictate reasoning, goals, and workflow.
    *   **The Tool Provider (MCP Server):** The MCP server focuses solely on securely executing Python/CadQuery logic and analyzing artifacts. It holds no business logic or conversational memory.
*   **Actionable Toolset:** The initial server will expose domain-specific tools, bypassing the need for standard terminal execution for the agent's most common actions.

### Proposed Core Tools
1.  **`analyze_reference_step`**: Wraps `tools/hole_finder.py`, `face_catalog.py`, and `step_summary.py` to allow the LLM to inspect reference models autonomously.
2.  **`compile_cadquery_model`**: Safely executes a generated unit of CadQuery code and returns either success or the exact stack trace for self-correction.
3.  **`generate_orthographic_preview`**: Exposes `tools/preview.py` to generate SVG blueprints for multimodal validation.
4.  **`query_lego_constants`**: Provides read access to `constants.py` and `lego-technic.md` specifics to ground the model physically.

## 3. Migration & Implementation Plan

### Phase 1: MVP Scaffolding
*   **Objective:** Establish the MCP server baseline and implement the first read-only tool.
*   **Tasks:**
    *   Set up a new module `tools/mcp/` containing the MCP server skeleton.
    *   Select an MCP SDK (e.g., the official `mcp` Python package).
    *   Implement `query_lego_constants` as the first, safe "Hello World" tool.
    *   Document how developers can attach their local assistants to the new server.

### Phase 2: Read-Only Analysis Tools
*   **Objective:** Give the LLM "eyes" into the CAD workspace.
*   **Tasks:**
    *   Implement the `analyze_reference_step` tool, wiring it up to our existing STEP analysis scripts.
    *   Implement the `generate_orthographic_preview` tool.
    *   Ensure the MCP server properly formats and returns the stdout/stderr or JSON outputs of these tools.

### Phase 3: The Execution Engine (Write Access)
*   **Objective:** Allow the LLM to compile CAD geometry dynamically.
*   **Tasks:**
    *   Implement `compile_cadquery_model`.
    *   *Crucial Step:* Establish boundary checks and explicit user warnings, as this tool executes arbitrary Python on the host/container.
    *   Implement error-catching logic so CadQuery geometric faults are returned cleanly to the LLM.

### Phase 4: Agent Refactoring & Dogfooding
*   **Objective:** Transition our internal workflows to use the MCP service exclusively.
*   **Tasks:**
    *   Update `.github/prompts/#developer` and `#designer` to prioritize using the MCP tools over requesting human terminal intervention.
    *   Run test design tasks (e.g., creating a new RC adapter) using only the MCP tools to validate the loop.

## 4. Future SaaS Considerations

Once this local implementation is battle-tested, the server logic will be containerized and isolated. The SaaS platform (`vibe-cading-platform`) will utilize this exact same codebase, running user prompts against sandboxed instances of this server.