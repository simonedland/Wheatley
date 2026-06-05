"""Pytest configuration for Wheatley V2 tests.

Inserts the repo root onto ``sys.path`` so the tests can import
``wheatley_V2.*`` whether pytest is launched from the repo root or from inside
the ``wheatley_V2`` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# wheatley_V2/tests/conftest.py -> repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parents[2]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
