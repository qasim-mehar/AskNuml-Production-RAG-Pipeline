"""Deterministic in-memory ObjectStore fake."""

from uni_rag_core.errors import StorageError


class FakeObjectStore:
    """Stores bytes in a dictionary keyed by object key."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}

    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        """Store ``data`` and return the key."""
        if not key:
            msg = "object key must not be empty"
            raise StorageError(msg)
        self._objects[key] = bytes(data)
        self._content_types[key] = content_type
        return key

    def get(self, key: str) -> bytes:
        """Return stored bytes, raising :class:`StorageError` for unknown keys."""
        if key not in self._objects:
            msg = f"object not found: {key}"
            raise StorageError(msg, context={"key": key})
        return self._objects[key]

    def delete(self, key: str) -> None:
        """Remove an object; unknown keys are a no-op."""
        self._objects.pop(key, None)
        self._content_types.pop(key, None)

    def content_type_of(self, key: str) -> str:
        """Return the recorded content type for a key (fake-specific helper)."""
        return self._content_types.get(key, "application/octet-stream")
