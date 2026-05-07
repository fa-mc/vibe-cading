---
description: Quantitative volume comparison between a CadQuery model and a reference STEP file
argument-hint: <reference.step> <module.path.ClassName> [--align-bbox] [--export]
---

Run the boolean-diff comparison:

```
python3 tools/boolean_diff.py $ARGUMENTS --model
```

Per `CLAUDE.md`, **do not run this until** the feature reconciliation checklist from `/step-analyze` is complete — running `boolean_diff.py` against an under-modelled part produces large, misleading volume deltas instead of pinpointing the missing features.

After it completes, report:

1. Volume delta (absolute and percentage). A delta < 1 % is a good dimensional match.
2. Intersection volume and Jaccard similarity.
3. Missing-material vs. extra-material residuals — call out which residual is larger and what physical feature is most likely responsible.
4. If `--export` was passed, list the residual STEP paths so the user can open them in the OCP viewer.

Remaining sub-1% delta is usually fillets / chamfers / small features that were intentionally simplified in the parametric model — flag this as the likely cause rather than chasing it.
