"""Make the workspace root importable for shared contracts and fixture modules.

Pytest may choose `packages/retrieval` as rootdir when tests are addressed by
path; this keeps both the root `tests.contracts` suite and the `packages.*`
fixture package importable in either invocation.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
