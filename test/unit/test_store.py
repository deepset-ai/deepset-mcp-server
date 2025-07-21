# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

import pytest

from deepset_mcp.store import create_redis_backend, initialize_store
from deepset_mcp.tools.tokonomics.object_store import InMemoryBackend, ObjectStore


class TestStoreInitialization:
    """Test store initialization functions."""

    def test_initialize_store_memory_backend(self) -> None:
        """Test initializing store with memory backend."""
        store = initialize_store(backend="memory", ttl=1800)

        assert isinstance(store, ObjectStore)
        assert isinstance(store._backend, InMemoryBackend)
        assert store._ttl == 1800

    def test_initialize_store_default_backend(self) -> None:
        """Test initializing store with default backend."""
        store = initialize_store()

        assert isinstance(store, ObjectStore)
        assert isinstance(store._backend, InMemoryBackend)
        assert store._ttl == 600

    def test_initialize_store_redis_backend_success(self) -> None:
        """Test initializing store with Redis backend successfully."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        with patch("redis.from_url", return_value=mock_redis_client):
            store = initialize_store(backend="redis", redis_url="redis://localhost:6379", ttl=7200)

            assert isinstance(store, ObjectStore)
            assert store._ttl == 7200
            mock_redis_client.ping.assert_called_once()

    def test_initialize_store_redis_backend_no_url(self) -> None:
        """Test initializing store with Redis backend but no URL."""
        with pytest.raises(ValueError, match="redis_url.*is None"):
            initialize_store(backend="redis", redis_url=None)

    def test_initialize_store_redis_backend_connection_failure(self) -> None:
        """Test initializing store with Redis backend connection failure."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.side_effect = Exception("Connection failed")

        with patch("redis.from_url", return_value=mock_redis_client):
            with pytest.raises(Exception, match="Connection failed"):
                initialize_store(backend="redis", redis_url="redis://localhost:6379")

    def test_create_redis_backend_success(self) -> None:
        """Test creating Redis backend successfully."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        with patch("redis.from_url", return_value=mock_redis_client):
            backend = create_redis_backend("redis://localhost:6379")

            assert backend is not None
            mock_redis_client.ping.assert_called_once()

    def test_create_redis_backend_redis_not_installed(self) -> None:
        """Test creating Redis backend when redis package is not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'redis'")):
            with pytest.raises(ImportError, match="Redis package not installed"):
                create_redis_backend("redis://localhost:6379")

    def test_create_redis_backend_connection_failure(self) -> None:
        """Test creating Redis backend with connection failure."""
        mock_redis = MagicMock()
        mock_redis.from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch("redis.from_url", return_value=mock_redis):
            with pytest.raises(Exception, match="Connection failed"):
                create_redis_backend("redis://localhost:6379")

    def test_initialize_store_caching(self) -> None:
        """Test that initialize_store uses caching."""
        # Clear any existing cache
        initialize_store.cache_clear()

        store1 = initialize_store(backend="memory", ttl=1800)
        store2 = initialize_store(backend="memory", ttl=1800)

        # Should return the same instance due to caching
        assert store1 is store2

    def test_initialize_store_different_params_different_instances(self) -> None:
        """Test that different parameters create different instances."""
        # Clear any existing cache
        initialize_store.cache_clear()

        store1 = initialize_store(backend="memory", ttl=1800)
        store2 = initialize_store(backend="memory", ttl=3600)

        # Should return different instances due to different parameters
        assert store1 is not store2
        assert store1._ttl == 1800
        assert store2._ttl == 3600

    def test_initialize_store_unknown_backend(self) -> None:
        """Test initializing store with unknown backend defaults to memory."""
        store = initialize_store(backend="unknown", ttl=1800)

        assert isinstance(store, ObjectStore)
        assert isinstance(store._backend, InMemoryBackend)
        assert store._ttl == 1800
