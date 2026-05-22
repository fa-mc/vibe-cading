# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# vibe-cading is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Private workspace `.env` loader.

Centralizes the trivial single-line ``KEY=value`` parser previously duplicated
inside ``vibe_cading.print_settings`` and ``vibe_cading.lego.constants``.  Kept
inside the package (underscored, not re-exported from ``__init__.py``) because
no external consumer should depend on this format — it exists solely so a
developer can override tuning constants without editing tracked source or
pulling in a third-party dependency like ``python-dotenv``.

Semantics (matches the previous inline parsers exactly):

* Searches for ``.env`` at the workspace root (``REPO_ROOT/.env``).
* Reads the file once at import time of the caller (idempotent — uses
  ``os.environ.setdefault`` so already-set OS-level env vars win).
* One ``KEY=value`` per line.  Whitespace around ``KEY`` and ``value`` is
  stripped.  Lines beginning with ``#`` are treated as comments and skipped.
  Blank lines and lines without ``=`` are skipped.
* A pair of *matched* surrounding quotes (``"..."`` or ``'...'``) around the
  value is stripped — standard ``.env`` behaviour, matching python-dotenv and
  docker-compose.  ``KEY=""`` yields an empty string.  Mismatched or
  unbalanced quotes (e.g. ``KEY="val'``) are left untouched.
* No escaping / multi-line / variable-interpolation support.  This is
  intentional — anything fancier should live in a real config system.

This module exposes a single callable, :func:`load_env_file`, which both call
sites invoke at import time.
"""

from __future__ import annotations

import os
from pathlib import Path


# Workspace root — two levels up from this file (``vibe_cading/_env.py``).
_REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path | str | None = None) -> None:
    """Parse a ``.env`` file and seed unset environment variables.

    Parameters
    ----------
    path:
        Override the file location.  ``None`` (the default) resolves to
        ``REPO_ROOT/.env``.  Missing files are silently ignored — the
        ``.env`` file is optional by design.

    Behaviour
    ---------
    Each parsed ``KEY=value`` pair is applied via :func:`os.environ.setdefault`
    so that any variable already present in the process environment (e.g. set
    by the shell or CI) wins over the file.  This matches the inline parsers
    that previously lived in ``print_settings.py`` and ``lego/constants.py``.
    """
    env_path = Path(path) if path is not None else _REPO_ROOT / ".env"
    if not env_path.exists():
        return

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            # Strip a pair of matched surrounding quotes ("..." or '...').
            # Standard .env semantics: project .env / .env.example write
            # quoted values (VIBE_MACHINE_PROFILE="bambu_p1s"), and the raw
            # quote chars would otherwise leak into the env var — breaking
            # profile-name lookups and float() casts on numeric constants.
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("\"", "'"):
                v = v[1:-1]
            os.environ.setdefault(k.strip(), v)
