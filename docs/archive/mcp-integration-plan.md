# MCP Server Architecture & Design Brief

## 1. System Overview & Component Boundaries

The Model Context Protocol (MCP) Server for Vibe-Cading acts as an execution bridge between the agent's LLM reasoning loop and the CadQuery engine. It exposes read-only artifact analysis and write-enabling compilation endpoints.

**Component Boundaries:**
- **Host (Runner):** Transport logic is decoupled from core tool definitions. The server supports `stdio` for local agentic workflows but will be wrapped in an SSE (Server-Sent Events) transport endpoint inside the platform's FastAPI backend (`main.py`) for the web UI.
- **Execution Sandbox:** The tools must be decoupled enough to inject the platform's existing Docker sandbox runner (`sandbox.py`). We cannot rely on raw local subprocesses (e.g. `python3 tmp/script.py`) for execution isolation.
- **Persistence (Artifacts):** The server writes to the temporary workspace directory (`tmp/`) but MUST return workspace-relative paths or a predictable URI scheme (e.g., `workspace://tmp/xyz.step`) instead of absolute OS paths, allowing the FastAPI backend to translate them into downloadable HTTP URLs.
- **Event Loop:** All MCP tool handlers MUST be `async`. Synchronous, CPU-bound generation will block the FastAPI web server's event loop when hosted via SSE.

## 2. API Contracts & Data Schemas

The MCP server will expose the following strict tool contracts. All handlers must be `async`.

### Tool: `query_lego_constants`
- **Description:** Returns the raw content of Lego Technic baseline dimensions and FDM/Resin machine printing profile defaults.
- **Parameters:** None.
- **Returns:** `{ "status": "success", "data": { "constants": "<python_source>", "profiles": "<json_source>" } }`

### Tool: `analyze_reference_step`
- **Description:** Analyzes an imported STEP file and returns bounding box, volumetric information, and a catalog of parametric features (holes, cylinders, bosses).
- **Parameters:** 
  - `file_path` (string) - Workspace-relative URI (e.g. `workspace://tmp/file.step`).
- **Returns:** JSON object aggregating outputs from `tools/step_summary.py` and `tools/hole_finder.py --json`.
  - `{ "status": "success", "summary": {...}, "holes": [...] }`

### Tool: `compile_cadquery_model`
- **Description:** Injects python CAD generation code into a scaffolding, executes it within the Docker sandbox to produce a localized STEP file, and returns the result or execution stack trace.
- **Parameters:**
  - `model_code` (string) - The complete CadQuery Python code (must include class definition).
  - `class_name` (string) - The target class to instantiate and extract the `.solid` property from.
- **Execution Logic:**
  1. Write `model_code` to `tmp/mcp_script_<uuid>.py`.
  2. Append an export block wrapping `class_name` to write `tmp/mcp_output_<uuid>.step`.
  3. Dispatch execution to the injected Docker sandbox runner (`sandbox.py`) asynchronously with a timeout to prevent boolean loops.
- **Returns:** 
  - On Success: `{ "status": "success", "step_file": "workspace://tmp/mcp_output_<uuid>.step" }`
  - On Failure: `{ "status": "error", "error_type": "<ExceptionName>", "traceback": "<full stack trace>" }`

### Tool: `generate_orthographic_preview`
- **Description:** Compiles orthographic SVGs (top, front, left) of a completed python model class for vision-based LLM verification.
- **Parameters:**
  - `model_code_path` (string) - Workspace-relative URI to the Python file containing the class.
  - `class_name` (string) - The CadQuery class name to render.
- **Returns:** `{ "status": "success", "files": ["workspace://tmp/preview/<class_name>_top.svg", ...] }`

## 3. Security & State Management
- **Anti-Duct-Tape Rule:** Do not catch arbitrary Python `SyntaxError`s inside the MCP server's main event loop. Docker sandbox isolation ensures a crash in the generated code affects only the child environment and does not crash the internal MCP server stream.
- **Cleanup:** The sandbox wrapper should ideally clean up intermediate scripts (`tmp/mcp_script_<uuid>.py`) upon successful export, but leave `.step` and `.svg` files intact for the LLM client to parse.

## 4. Dependency Management & Monorepo Boundaries
- **SDK:** Anthropic's official `mcp` SDK (`mcp>=1.0.0`).
- **Packaging:** The engine submodule is strictly out-of-band and read-only for the platform. We MUST NOT modify `pyproject.toml`. Instead, the MCP server wrapper should live in the backend directory (e.g., `backend/mcp_server.py`) and the `mcp` SDK must be added to the platform's `requirements.txt`.

## 5. Success Criteria & Testing Workflow

The implementation by the Developer is considered complete *only* when the following criteria and testing workflows are passed:
1.  **Unit Tests:** Create E2E tests for the MCP server. Programmatically invoke the server tools holding mock inputs and assert correct JSON return payloads and `workspace://` URIs.
2.  **End-to-End Test (E2E):** The `#developer` must run the server manually, pipe in a mock JSON-RPC payload triggering `compile_cadquery_model` with a simple box (`cq.Workplane("XY").box(10,10,10)`), and verify the output STEP file is correctly generated via the sandbox.
3.  **Dependency Verification:** Ensure the `mcp` SDK is added to `requirements.txt` and not `pyproject.toml`.

---
**Architectural Decision:** Finalized. Alignment with Platform TL pending execution.
