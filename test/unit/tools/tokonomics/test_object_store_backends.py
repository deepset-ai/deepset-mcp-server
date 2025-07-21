# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import time
from unittest.mock import MagicMock, patch

import pytest

from deepset_mcp.tools.tokonomics.object_store import (
    InMemoryBackend,
    RedisBackend,
)


class TestInMemoryBackend:
    """Test InMemoryBackend class."""

    def test_init(self) -> None:
        """Test InMemoryBackend initialization."""
        backend = InMemoryBackend()
        assert backend._data == {}
        assert backend._counter == 0

    def test_generate_id(self) -> None:
        """Test ID generation."""
        backend = InMemoryBackend()

        id1 = backend.generate_id()
        id2 = backend.generate_id()
        id3 = backend.generate_id()

        assert id1 == "obj_001"
        assert id2 == "obj_002"
        assert id3 == "obj_003"
        assert backend._counter == 3

    def test_set_get_no_ttl(self) -> None:
        """Test storing and retrieving data without TTL."""
        backend = InMemoryBackend()
        test_data = b"test data"

        backend.set("key1", test_data, None)
        retrieved = backend.get("key1")

        assert retrieved == test_data

    def test_set_get_with_ttl(self) -> None:
        """Test storing and retrieving data with TTL."""
        backend = InMemoryBackend()
        test_data = b"test data"

        backend.set("key1", test_data, 1)  # 1 second TTL

        # Should be retrievable immediately
        assert backend.get("key1") == test_data

        # Mock time to be after expiration
        with patch("time.time", return_value=time.time() + 2):
            assert backend.get("key1") is None
            assert "key1" not in backend._data

    def test_delete_existing(self) -> None:
        """Test deleting existing key."""
        backend = InMemoryBackend()
        test_data = b"test data"

        backend.set("key1", test_data, None)
        result = backend.delete("key1")

        assert result is True
        assert backend.get("key1") is None

    def test_delete_nonexistent(self) -> None:
        """Test deleting non-existent key."""
        backend = InMemoryBackend()

        result = backend.delete("nonexistent")

        assert result is False

    def test_get_nonexistent(self) -> None:
        """Test retrieving non-existent key."""
        backend = InMemoryBackend()

        result = backend.get("nonexistent")

        assert result is None

    def test_ttl_cleanup_on_get(self) -> None:
        """Test that expired keys are cleaned up when accessed."""
        backend = InMemoryBackend()
        test_data = b"test data"

        backend.set("key1", test_data, 1)
        backend.set("key2", test_data, None)  # No TTL

        # Verify both keys exist
        assert backend.get("key1") == test_data
        assert backend.get("key2") == test_data
        assert len(backend._data) == 2

        # Mock time to be after TTL expiration
        with patch("time.time", return_value=time.time() + 2):
            # Accessing expired key should clean it up
            assert backend.get("key1") is None
            assert "key1" not in backend._data

            # Non-expired key should still exist
            assert backend.get("key2") == test_data
            assert len(backend._data) == 1


class TestRedisBackend:
    """Test RedisBackend class."""

    def test_init_success(self) -> None:
        """Test successful Redis connection."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        with patch("redis.from_url", return_value=mock_redis_client) as mock_from_url:
            RedisBackend("redis://localhost:6379")

            mock_from_url.assert_called_once_with("redis://localhost:6379", decode_responses=False)
            mock_redis_client.ping.assert_called_once()

    def test_init_connection_failure(self) -> None:
        """Test Redis connection failure."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch("redis.from_url", return_value=mock_redis):
            with pytest.raises(Exception, match="Connection failed"):
                RedisBackend("redis://localhost:6379")

    def test_init_redis_not_installed(self) -> None:
        """Test Redis backend when redis package is not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'redis'")):
            with pytest.raises(ImportError):
                RedisBackend("redis://localhost:6379")

    def test_generate_id(self) -> None:
        """Test UUID-based ID generation."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            id1 = backend.generate_id()
            id2 = backend.generate_id()

            assert id1.startswith("obj_")
            assert id2.startswith("obj_")
            assert id1 != id2  # Should be different UUIDs

    def test_set_get_no_ttl(self) -> None:
        """Test storing and retrieving data without TTL."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        test_data = b"test data"
        mock_redis.get.return_value = test_data

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            backend.set("key1", test_data, None)
            retrieved = backend.get("key1")

            mock_redis.set.assert_called_once_with("key1", test_data)
            mock_redis.get.assert_called_once_with("key1")
            assert retrieved == test_data

    def test_set_get_with_ttl(self) -> None:
        """Test storing and retrieving data with TTL."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        test_data = b"test data"
        mock_redis.get.return_value = test_data

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            backend.set("key1", test_data, 60)
            retrieved = backend.get("key1")

            mock_redis.setex.assert_called_once_with("key1", 60, test_data)
            mock_redis.get.assert_called_once_with("key1")
            assert retrieved == test_data

    def test_delete_existing(self) -> None:
        """Test deleting existing key."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        mock_redis.delete.return_value = 1  # Redis returns count of deleted keys

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            result = backend.delete("key1")

            mock_redis.delete.assert_called_once_with("key1")
            assert result is True

    def test_delete_nonexistent(self) -> None:
        """Test deleting non-existent key."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        mock_redis.delete.return_value = 0  # Redis returns 0 when key doesn't exist

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            result = backend.delete("nonexistent")

            mock_redis.delete.assert_called_once_with("nonexistent")
            assert result is False

    def test_get_nonexistent(self) -> None:
        """Test retrieving non-existent key."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        mock_redis.get.return_value = None

        with patch("redis.from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            result = backend.get("nonexistent")

            mock_redis.get.assert_called_once_with("nonexistent")
            assert result is None

    def test_connection_url_variations(self) -> None:
        """Test different Redis URL formats."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis

        urls = [
            "redis://localhost:6379",
            "redis://localhost:6379/0",
            "redis://user:pass@localhost:6379",
            "rediss://localhost:6380",
        ]

        for url in urls:
            with patch("redis.from_url", return_value=mock_redis) as mock_from_url:
                RedisBackend(url)
                mock_from_url.assert_called_with(url, decode_responses=False)
