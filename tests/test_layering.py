"""Import-linter rejects a deliberately illegal import (L2)."""

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "packages/core/src/uni_rag_core/_illegal_probe.py"


def test_import_linter_rejects_core_importing_an_app() -> None:
    executable = shutil.which("lint-imports")
    assert executable is not None, "import-linter must be installed to run this gate"
    PROBE.write_text("from uni_rag_api.main import app  # noqa: F401\n", encoding="utf-8")
    try:
        result = subprocess.run(
            [executable, ".importlinter"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        PROBE.unlink(missing_ok=True)
    assert result.returncode != 0
    assert "core is independent" in result.stdout.lower() or "forbidden" in result.stdout.lower()
