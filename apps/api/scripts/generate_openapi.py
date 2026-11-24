"""Regenerate the committed OpenAPI artifact consumed by Lane H (L12)."""

import json
from pathlib import Path

from uni_rag_api.app import create_app

ARTIFACT = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    """Write the served schema as byte-stable UTF-8 JSON."""
    schema = create_app().openapi()
    ARTIFACT.write_text(
        json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
