"""Pure, content-addressed object key derivation (L4)."""

from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath


def content_addressed_key(key: str, data: bytes) -> str:
    """Return a stable key derived from ``data``, preserving the extension.

    Re-putting identical bytes always yields the same key; changing one byte
    yields a different key, so old page images are never silently overwritten.
    """
    digest = sha256(data).hexdigest()
    path = PurePosixPath(key.strip("/"))
    suffix = path.suffix
    parent = "" if str(path.parent) == "." else f"{path.parent.as_posix()}/"
    return f"{parent}{digest}{suffix}"
