"""Pytest test-collection scaffolding.

Ensures the repo root is on ``sys.path`` so tests can import
``vibe_cading.*`` and ``parts.*`` regardless of pytest invocation cwd.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
