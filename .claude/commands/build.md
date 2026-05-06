---
description: Run python build.py to regenerate every STEP file in build.toml
argument-hint: [--list] [--config build.toml]
---

Run the project build:

```
python3 build.py $ARGUMENTS
```

After it completes:

1. Report which `[[build]]` entries succeeded / failed (one line each).
2. For any failure, surface the relevant traceback and propose a root-cause hypothesis — but do **not** modify model code without explicit user approval.
3. Output STEP files land in `output/` (git-ignored). Do not commit them.
