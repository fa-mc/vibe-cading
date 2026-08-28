---
description: Serve the OCP CAD viewer in a plain browser tab (no VS Code) and push a model to it
argument-hint: <module.path.ClassName> [--params key=value ...]  OR  --assembly <module.path>
---

View a model in a **browser tab** instead of the VS Code panel. Full guide:
[`docs/viewer.md`](../../docs/viewer.md).

`vibe_cading/tools/view.py` is only a client — it needs a viewer already
listening on port 3939. The `ocp_vscode` package ships a standalone server that
provides one without VS Code. Three steps, in this order:

**1. Is a viewer already up?** If `curl -s -o /dev/null -w '%{http_code}'
http://localhost:3939/viewer` returns `200`, skip to step 3 — only one process
may hold the port.

**2. Start the server** (background it; it runs in the foreground otherwise):

```
python3 -m ocp_vscode --host 0.0.0.0 --port 3939
```

Use `--host 0.0.0.0`, not the default `127.0.0.1` — loopback is unreachable
through a `docker run -p` mapping. Then tell the user to open
<http://localhost:3939/viewer> and **leave the tab open**. Port 3939 is already
in `forwardPorts`, so VS Code / Codespaces forwarding needs no further setup.

**3. Push the model:**

```
python3 vibe_cading/tools/view.py $ARGUMENTS
```

## Interpreting the result

- **`No OCP CAD Viewer is listening`, exit 1** — step 2 was skipped or the
  server died. Start it and re-run.
- **`Showing <Class>`, exit 0, but the user sees nothing** — the *server* got
  the model but no browser was registered to receive it. The server log says
  `No browser registered`. Ask the user to open or refresh
  <http://localhost:3939/viewer>, then push again. The model is not buffered,
  so it must be re-sent after the tab connects.
- **`Port 3939 is already in use`** — another viewer (often the VS Code panel)
  holds it. Either use that one, or serve on another port and point the client
  at it with `OCP_PORT=<port>`.

Never add `ocp_vscode` imports or `if __name__ == "__main__":` viewer blocks to
model class files to work around a viewer problem — that is CI-enforced, and
`vibe_cading/tools/view.py` is the only sanctioned entry point. For multi-part
assemblies the target module must expose a top-level `assemble()` returning
`(solid, name, color)` tuples and the user must pass `--assembly`; propose the
assembly module and wait for approval before creating one.
