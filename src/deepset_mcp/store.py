# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Global store for the MCP server."""

import functools
import logging

from deepset_mcp.tools.tokonomics.object_store import InMemoryBackend, ObjectStore, ObjectStoreBackend, RedisBackend

logger = logging.getLogger(__name__)


def create_redis_backend(url: str) -> ObjectStoreBackend:
    """Create Redis backend, failing if connection fails.

    :param url: Redis connection URL
    :raises Exception: If Redis connection fails
    """
    try:
        backend = RedisBackend(url)
        logger.info(f"Successfully connected to Redis at {url} (using UUIDs for IDs)")

        return backend

    except Exception as e:
        logger.error(f"Failed to connect to Redis at {url}: {e}")
        raise


@functools.lru_cache(maxsize=1)
def initialize_store(
    backend: str = "memory",
    redis_url: str | None = None,
    ttl: int = 600,
) -> ObjectStore:
    """Initialize the object store.

    :param backend: Backend type ('memory' or 'redis')
    :param redis_url: Redis connection URL (required if backend='redis')
    :param ttl: Time-to-live in seconds for stored objects
    :raises ValueError: If Redis backend selected but no URL provided
    :raises Exception: If Redis connection fails
    """
    if backend == "redis":
        if not redis_url:
            raise ValueError("'redis_url' is None. Provide a 'redis_url' to use the redis backend.")
        backend_instance = create_redis_backend(redis_url)

    else:
        logger.info("Using in-memory backend")
        backend_instance = InMemoryBackend()

    store = ObjectStore(backend=backend_instance, ttl=ttl)
    logger.info(f"Initialized ObjectStore with {backend} backend and TTL={ttl}s")

    return store
