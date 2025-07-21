# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from deepset_mcp.tools.tokonomics.object_store import (
    InMemoryBackend,
    ObjectStore,
    RedisBackend,
)


@pytest.fixture(params=["memory", "redis"])
def backend(request: Any) -> InMemoryBackend | RedisBackend:
    """Fixture providing both InMemoryBackend and mocked RedisBackend."""
    if request.param == "memory":
        return InMemoryBackend()
    else:  # request.param == "redis"
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis

        # Mock Redis operations for consistent behavior
        stored_data: dict[str, bytes] = {}

        def mock_set(key: str, value: bytes) -> None:
            stored_data[key] = value

        def mock_setex(key: str, ttl: int, value: bytes) -> None:
            stored_data[key] = value

        def mock_get(key: str) -> bytes | None:
            return stored_data.get(key)

        def mock_delete(key: str) -> int:
            if key in stored_data:
                del stored_data[key]
                return 1
            return 0

        mock_redis.set.side_effect = mock_set
        mock_redis.setex.side_effect = mock_setex
        mock_redis.get.side_effect = mock_get
        mock_redis.delete.side_effect = mock_delete

        with patch("redis.from_url", return_value=mock_redis):
            return RedisBackend("redis://localhost:6379")


class TestObjectStore:
    """Test ObjectStore with parametrized backends."""

    def test_init_default_ttl(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test ObjectStore initialization with default TTL."""
        store = ObjectStore(backend=backend)
        assert store._ttl == 600
        assert store._backend == backend

    def test_init_custom_ttl(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test ObjectStore initialization with custom TTL."""
        store = ObjectStore(backend=backend, ttl=7200)
        assert store._ttl == 7200

    def test_init_zero_ttl(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test ObjectStore initialization with zero TTL (no expiry)."""
        store = ObjectStore(backend=backend, ttl=0)
        assert store._ttl == 0

    def test_put_get_single_object(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test storing and retrieving a single object."""
        store = ObjectStore(backend=backend)
        test_obj = {"test": "data"}

        obj_id = store.put(test_obj)
        retrieved_obj = store.get(obj_id)

        assert retrieved_obj == test_obj

    def test_put_get_multiple_objects(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test storing and retrieving multiple objects."""
        store = ObjectStore(backend=backend)
        obj1 = {"first": "object"}
        obj2 = {"second": "object"}
        obj3 = [1, 2, 3]

        id1 = store.put(obj1)
        id2 = store.put(obj2)
        id3 = store.put(obj3)

        # All IDs should be unique
        assert len({id1, id2, id3}) == 3

        assert store.get(id1) == obj1
        assert store.get(id2) == obj2
        assert store.get(id3) == obj3

    def test_get_nonexistent_object(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test retrieving a non-existent object."""
        store = ObjectStore(backend=backend)

        result = store.get("nonexistent_key")

        assert result is None

    def test_delete_existing_object(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test deleting an existing object."""
        store = ObjectStore(backend=backend)
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        result = store.delete(obj_id)

        assert result is True
        assert store.get(obj_id) is None

    def test_delete_nonexistent_object(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test deleting a non-existent object."""
        store = ObjectStore(backend=backend)

        result = store.delete("nonexistent_key")

        assert result is False

    def test_json_serialization_with_set(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test JSON serialization with set objects."""
        store = ObjectStore(backend=backend)
        test_obj = {"tags": {1, 2, 3}, "name": "test"}

        obj_id = store.put(test_obj)
        retrieved = store.get(obj_id)

        # Set should be converted to list
        assert retrieved is not None
        assert retrieved["name"] == "test"
        assert set(retrieved["tags"]) == {1, 2, 3}

    def test_json_serialization_with_pydantic(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test JSON serialization with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            age: int

        store = ObjectStore(backend=backend)
        model = TestModel(name="test", age=25)

        obj_id = store.put(model)
        retrieved = store.get(obj_id)

        assert retrieved == {"name": "test", "age": 25}

    def test_get_with_zero_ttl(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test that objects don't expire with zero TTL."""
        store = ObjectStore(backend=backend, ttl=0)
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        # Even after time passes, object should still exist
        with patch("time.time", return_value=time.time() + 10000):
            retrieved = store.get(obj_id)
            assert retrieved == test_obj

    @pytest.mark.parametrize("backend_name", ["memory"])
    def test_ttl_expiration_memory_only(self, backend_name: str) -> None:
        """Test that objects expire after TTL (InMemoryBackend only)."""
        # TTL expiration testing only works with InMemoryBackend due to time mocking
        backend = InMemoryBackend()
        store = ObjectStore(backend=backend, ttl=1)
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        # Object should exist immediately
        assert store.get(obj_id) == test_obj

        # Mock time to be after TTL expiration
        with patch("time.time", return_value=time.time() + 2.0):
            result = store.get(obj_id)
            assert result is None

    @pytest.mark.parametrize("backend_name", ["memory"])
    def test_partial_expiration_memory_only(self, backend_name: str) -> None:
        """Test that only expired objects are evicted (InMemoryBackend only)."""
        backend = InMemoryBackend()
        store = ObjectStore(backend=backend, ttl=2)

        # Put first object
        obj1 = {"first": "object"}
        id1 = store.put(obj1)

        # Wait 1 second and put second object
        with patch("time.time", return_value=time.time() + 1.0):
            obj2 = {"second": "object"}
            id2 = store.put(obj2)

        # Wait another 1.5 seconds (total 2.5) - only first object should expire
        with patch("time.time", return_value=time.time() + 2.5):
            obj3 = {"third": "object"}
            id3 = store.put(obj3)

            # First object should be expired
            assert store.get(id1) is None
            # Second and third objects should exist
            assert store.get(id2) == obj2
            assert store.get(id3) == obj3
