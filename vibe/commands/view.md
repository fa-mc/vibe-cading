---
description: Open a model in the OCP CAD viewer (port 3939) via tools/view.py
argument-hint: <module.path.ClassName> [--params key=value ...]  OR  --assembly <module.path>
---

Launch the model in the OCP viewer:

```
python3 tools/view.py $ARGUMENTS
```

Per `CLAUDE.md` ("OCP Viewer — Dedicated Entry Point"), model class files must remain pure declarations — never add `ocp_vscode` imports or `if __name__ == "__main__":` viewer blocks to them. `tools/view.py` is the only supported entry point.

For multi-part assemblies, the target module must expose a top-level `assemble()` returning a list of `(solid, name, color)` tuples, and the user must pass `--assembly`. If the user has not yet created an assembly module for the parts they want to view together, propose the assembly module and wait for approval before creating it.
