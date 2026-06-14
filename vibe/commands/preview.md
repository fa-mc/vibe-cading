---
description: Run vibe_cading/tools/preview.py for a model class and inspect the resulting SVGs
argument-hint: <module.path.ClassName> [--views top front left ...] [--params key=value ...]
---

Run the orthographic preview pipeline for the model `$ARGUMENTS` exactly as documented in `vibe/INSTRUCTIONS.md` under "Asset Validation":

```
python3 vibe_cading/tools/preview.py $ARGUMENTS
```

Then:

1. List the SVG files that landed in `tmp/preview/`.
2. If a reference image or drawing has been attached or referenced in the conversation, follow the **Step 0 — establish orientation** procedure from `vibe/INSTRUCTIONS.md` ("Asset Validation") *before* extracting any dimensions, then read each SVG file and compare against the reference.
3. If no reference is attached, report the bounding-box dimensions extracted from each SVG and stop — do not invent acceptance criteria.

Never use the SVG output as a "code correctness" check on its own — it is a visual comparison tool only.
