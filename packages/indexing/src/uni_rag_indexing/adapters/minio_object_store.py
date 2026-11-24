"""MinIO implementation of the frozen ObjectStore port (L3/L8/L10).

Page-image bytes are stored under content-addressed keys. The MinIO client is
created only in :meth:`from_settings`; tests inject a small client double, so
no network is touched in unit tests.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, NoReturn
from urllib.parse import urlsplit

from minio import Minio

from uni_rag_core import Settings, StorageError, get_logger
from uni_rag_indexing.domain.object_keys import content_addressed_key
from uni_rag_indexing.domain.store_types import (
    StorageConnectionError,
    StorageNotFoundError,
)

_logger = get_logger("uni_rag_indexing.adapters.minio")


class MinioObjectStore:
    """Synchronous ObjectStore adapter backed by an S3-compatible MinIO client."""

    def __init__(
        self,
        client: Minio,
        *,
        bucket: str,
        host: str,
        ensure_bucket: bool = True,
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._host = host
        if ensure_bucket:
            try:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
            except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
                self._raise_typed(exc, "ensure_bucket")
        _logger.info("minio_ready", bucket=bucket, host=host)

    @classmethod
    def from_settings(cls, settings: Settings) -> MinioObjectStore:
        """Build a MinIO client from typed settings; never read ``os.environ`` (L8)."""
        parsed = urlsplit(settings.minio_endpoint)
        endpoint = parsed.netloc or parsed.path
        client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=parsed.scheme == "https",
        )
        return cls(
            client,
            bucket=settings.minio_bucket,
            host=parsed.hostname or settings.minio_endpoint,
        )

    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        """Store bytes under a content-addressed key and return that key."""
        object_name = content_addressed_key(key, data)
        try:
            self._client.put_object(
                self._bucket,
                object_name,
                BytesIO(data),
                len(data),
                content_type=content_type,
            )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "put")
        _logger.info(
            "minio_put",
            bucket=self._bucket,
            host=self._host,
            size=len(data),
            content_type=content_type,
        )
        return object_name

    def get(self, key: str) -> bytes:
        """Return stored bytes; missing keys raise a typed StorageError."""
        try:
            response = self._client.get_object(self._bucket, key)
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "get", key=key)
        try:
            data = response.read()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "get", key=key)
        finally:
            response.close()
            release = getattr(response, "release_conn", None)
            if callable(release):
                release()
        _logger.debug("minio_get", bucket=self._bucket, host=self._host, size=len(data))
        return data

    def delete(self, key: str) -> None:
        """Remove an object; removing a missing key is a no-op (port semantics)."""
        try:
            self._client.remove_object(self._bucket, key)
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            if self._is_missing(exc):
                _logger.debug("minio_delete_missing", host=self._host, key=key)
                return
            self._raise_typed(exc, "delete", key=key)
        _logger.info("minio_delete", bucket=self._bucket, host=self._host)

    def _raise_typed(self, exc: Exception, operation: str, *, key: str | None = None) -> NoReturn:
        text = f"{type(exc).__name__}: {exc}".lower()
        context: dict[str, Any] = {
            "operation": operation,
            "host": self._host,
            "bucket": self._bucket,
        }
        if key is not None:
            context["key"] = key
        _logger.error("minio_error", operation=operation, host=self._host, error=text[:300])
        if self._is_missing(exc):
            raise StorageNotFoundError(
                f"object not found during {operation}: {exc}", context=context
            ) from exc
        if any(
            token in text for token in ("connect", "refused", "unreachable", "timeout", "endpoint")
        ):
            raise StorageConnectionError(
                f"minio connection failed during {operation}: {exc}", context=context
            ) from exc
        raise StorageError(f"minio {operation} failed: {exc}", context=context) from exc

    @staticmethod
    def _is_missing(exc: Exception) -> bool:
        name = type(exc).__name__.lower()
        code = str(getattr(exc, "code", "")).lower()
        text = str(exc).lower()
        return (
            "nosuchkey" in name
            or code == "nosuchkey"
            or "nosuchkey" in text
            or "not found" in text
            or "404" in text
        )
