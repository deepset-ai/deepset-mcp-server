# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import time
import uuid
from typing import (
    Any,
    Protocol,
)

import orjson

logger = logging.getLogger(__name__)


class ObjectStoreBackend(Protocol):
    """Backend protocol with ID generation."""

    def generate_id(self) -> str:
        """Generate a unique ID for this backend."""
        ...

    def set(self, key: str, value: bytes, ttl_seconds: int | None) -> None:
        """Store bytes value with optional TTL."""
        ...

    def get(self, key: str) -> bytes | None:
        """Retrieve bytes value or None if not found/expired."""
        ...

    def delete(self, key: str) -> bool:
        """Delete and return True if existed."""
        ...


class InMemoryBackend:
    """In-memory backend with counter-based IDs."""

    def __init__(self) -> None:
        """Initialize an instance of InMemoryBackend."""
        self._data: dict[str, tuple[bytes, float | None]] = {}
        self._counter = 0

    def generate_id(self) -> str:
        """Generate sequential ID."""
        self._counter += 1
        return f"obj_{self._counter:03d}"

    def set(self, key: str, value: bytes, ttl_seconds: int | None) -> None:
        """Set a value at key."""
        expiry = None if ttl_seconds is None else time.time() + ttl_seconds
        self._data[key] = (value, expiry)

    def get(self, key: str) -> bytes | None:
        """Get a value at key."""
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry and time.time() > expiry:
            self.delete(key)
            return None
        return value

    def delete(self, key: str) -> bool:
        """Delete a value at key."""
        return self._data.pop(key, None) is not None


class RedisBackend:
    """Redis backend with UUID-based IDs."""

    def __init__(self, redis_url: str) -> None:
        """Initialize the redis backend."""
        try:
            import redis
        except ImportError as e:
            logger.error(
                "Redis package not installed. Install with: pip install deepset-mcp[redis] to use the RedisBackend."
            )
            raise ImportError(
                "Redis package not installed. Install with: pip install deepset-mcp[redis] to use the RedisBackend."
            ) from e

        self._client = redis.from_url(redis_url, decode_responses=False)  # type: ignore[no-untyped-call]
        # Test connection immediately
        self._client.ping()

    def generate_id(self) -> str:
        """Generate UUID."""
        # Using UUID4 for Redis to ensure uniqueness across instances
        return f"obj_{uuid.uuid4()}"

    def set(self, key: str, value: bytes, ttl_seconds: int | None) -> None:
        """Set a value at key."""
        if ttl_seconds:
            self._client.setex(key, ttl_seconds, value)
        else:
            self._client.set(key, value)

    def get(self, key: str) -> bytes | None:
        """Get a value at key."""
        return self._client.get(key)  # type: ignore[no-any-return]

    def delete(self, key: str) -> bool:
        """Delete a value at key."""
        return bool(self._client.delete(key))


class ObjectStore:
    """JSON-based object store with pluggable backends."""

    def __init__(self, backend: ObjectStoreBackend, ttl: int = 600) -> None:
        """Initialize ObjectStore with backend and TTL.

        Parameters
        ----------
        backend :
            Backend implementation for storage
        ttl :
            Time-to-live in seconds for stored objects. The TTL is managed by the backend.
        """
        self._backend = backend
        self._ttl = ttl

    def put(self, obj: Any) -> str:
        """Store any object as JSON using backend-generated ID."""
        obj_id = self._backend.generate_id()

        def default(obj: Any) -> Any:
            if isinstance(obj, set | tuple):
                return list(obj)
            # Check if it's a Pydantic model
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            raise TypeError

        json_bytes = orjson.dumps(obj, default=default)

        ttl_seconds = self._ttl if self._ttl > 0 else None
        self._backend.set(obj_id, json_bytes, ttl_seconds)
        return obj_id

    def get(self, obj_id: str) -> Any | None:
        """Get object as JSON-decoded data."""
        json_bytes = self._backend.get(obj_id)
        if json_bytes is None:
            return None

        return orjson.loads(json_bytes)

    def delete(self, obj_id: str) -> bool:
        """Delete object."""
        return self._backend.delete(obj_id)
