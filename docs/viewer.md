# Live 3D Viewer — VS Code panel or plain browser tab

`vibe_cading/tools/view.py` pushes a model class (or assembly) to the **OCP CAD
Viewer** for live 3D inspection. This document covers both ways to run that
viewer — including the **standalone browser** mode, which needs no VS Code.

For the SVG-based validation workflow (`preview.py`, `section_slicer.py`), see
the *Asset Validation* section of [`vibe/INSTRUCTIONS.md`](../vibe/INSTRUCTIONS.md).
Those are static orthographic exports; this page is about the interactive viewer.

---

## The client/server split (read this first)

`view.py` is only a **client**. It tessellates geometry and pushes it over a
websocket to a viewer that must *already be listening* (default port **3939**).
It never starts a viewer itself.

Two back-ends serve that port. They speak the same protocol, so `view.py` works
against either with no flags and no code change:

| Back-end | How it runs | Needs VS Code? |
|---|---|---|
| VS Code panel | `bernhard-42.ocp-cad-viewer` extension (preinstalled in the dev container) | Yes |
| **Standalone server** | `python3 -m ocp_vscode` — ships inside the `ocp_vscode` package | **No** |

---

## Standalone browser viewing

### 1. Start the server

```bash
python3 -m ocp_vscode --host 0.0.0.0 --port 3939
```

It runs in the foreground and prints its URL. Use a second terminal for
`view.py`, or append `&` to background it.

> **Use `--host 0.0.0.0`, not the default `127.0.0.1`.** The default binds to
> the container's loopback interface only, which a `docker run -p` port mapping
> cannot reach. VS Code's own port forwarding can still reach loopback, so
> `127.0.0.1` may appear to work under Remote-Containers and then fail under a
> bare `docker run` — bind `0.0.0.0` and both work.

### 2. Open the viewer tab

<http://localhost:3939/viewer>

`/` redirects to `/viewer`. **Leave this tab open** — see the gotcha below.

### 3. Push a model

```bash
python3 vibe_cading/tools/view.py vibe_cading.mechanical.gears.spur.SpurGear \
    --params module=1.0 teeth=20 face_width=5.0
```

The model appears in the browser tab. `--demo` and `--assembly` work identically.

---

## Reaching the viewer — localhost vs. another device

Where you can open the viewer from depends on **how the container exposes the
port**, and the two mechanisms are not equivalent.

### Under VS Code — `localhost` only

Port 3939 is declared in
[`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json)
(`forwardPorts`), so under **VS Code Remote-Containers or Codespaces nothing
further is required** — open <http://localhost:3939/viewer>.

But `forwardPorts` is **not** a Docker port publish: it is VS Code's own
tunnel, bound to `localhost` on the machine running the VS Code UI. The
container itself publishes nothing (`docker inspect` reports
`PortBindings: {}`), so **another device on your network cannot reach it** this
way, and neither can a browser outside VS Code's forwarding.

### Running the image directly — reachable from any device

Use [`docker/compose.yaml`](../docker/compose.yaml), which publishes 3939 for
real (binds `0.0.0.0` on the host) instead of tunnelling it:

```bash
docker compose -f docker/compose.yaml up -d --build
docker compose -f docker/compose.yaml exec dev bash
```

Run the server and `view.py` in the **same** container — `view.py` connects to
`ws://127.0.0.1` and `OCP_PORT` overrides only the port, not the host, so a
split setup is awkward to wire up. Run `exec` twice for two shells in the one
container, which is what you want here.

Then inside that container start the server (`python3 -m ocp_vscode --host
0.0.0.0 --port 3939`) and push with `view.py` as usual. The viewer is now
reachable at `http://<host-lan-ip>:3939/viewer` from a phone, tablet, or second
machine — not just `localhost`.

> `--host 0.0.0.0` on the server **and** `-p` on the container are both
> required. Either one alone leaves the viewer unreachable from outside.

---

## Gotchas

**The browser tab must be open *before* you push.** The server does not buffer
models for a client that is not connected yet. If no browser is registered it
drops the payload and logs:

```
No browser registered. Please open the viewer in a browser or refresh the viewer page
```

Meanwhile `view.py` still reports `Showing <Class>` and exits 0 — it confirms
the *server* accepted the model, and cannot see whether a browser was attached.
**If a push seems to vanish, open or refresh the viewer tab and re-run.**

**Only one viewer per port.** The standalone server refuses to start if the port
is taken (`Port 3939 is already in use.`, exit 1) — including when the VS Code
panel already holds it. Stop one, or run the second on another port and point
the client at it with `OCP_PORT`:

```bash
python3 -m ocp_vscode --host 0.0.0.0 --port 3940
OCP_PORT=3940 python3 vibe_cading/tools/view.py <module.path.ClassName>
```

**No viewer at all** → `view.py` aborts with exit 1 and a message telling you
how to start one. It deliberately does *not* proceed silently; before this guard
existed it printed `Showing <Class>` and exited 0 having transmitted nothing.
This holds for a dead `OCP_PORT` too: the port is probed, not just resolved.

**`--export` is exempt.** The STEP file is written before the viewer is needed,
so with no viewer the export still succeeds and exits 0 — it only warns on
stderr that nothing was displayed. Headless export therefore stays usable in
scripts and `&&` chains (e.g. the calibration-gauge step in
[print-tolerances.md](print-tolerances.md)).

---

## Reference

`python3 -m ocp_vscode --help` lists every option — camera/control mode, theme,
grid, axes, tessellation tolerances, default colors. To persist preferences,
`python3 -m ocp_vscode --create_configfile` writes `~/.ocpvscode_standalone`.

Model class files must never import `ocp_vscode` or carry a `__main__` viewer
block — `vibe_cading/tools/view.py` is the only sanctioned consumer, and this is
CI-enforced. See the *OCP Viewer — Dedicated Entry Point* section of
[`vibe/INSTRUCTIONS.md`](../vibe/INSTRUCTIONS.md).
