"""Object/blob store port (L3)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStore(Protocol):
    """Stores page images and raw artefacts by key."""

    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        """Store ``data`` and return its key."""
        ...

    def get(self, key: str) -> bytes:
        """Return bytes for ``key``."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at ``key``."""
        ...
