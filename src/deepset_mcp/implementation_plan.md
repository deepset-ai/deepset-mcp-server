# Implementation Plan for Redis backed ObjectStore

## Overview

We want to implement a Redis backed ObjectStore. The ObjectStore should work with the Redis backend, as well as the
existing InMemory backend. We want to make this change clean and as simple as possible.

## Relevant Implementations

- Object Store implementation: `src/deepset_mcp/tools/tokonomics/object_store.py`
- Explorer using ObjectStore: `src/deepset_mcp/tools/tokonomics/explorer.py`
- Decorators extending tools with Explorer / ObjectStore functionality: `src/deepset_mcp/tools/tokonomics/decorators.py`

- Tools working directly with the ObjectStore: `src/deepset_mcp/tools/object_store.py`
- Explorer / ObjectStore configuration for other tools: `src/deepset_mcp/tool_factory.py`

- Global ObjectStore initialization: `src/deepset_mcp/store.py`

- Server configuration: `src/deepset_mcp/server.py`
- Main entrypoint: `src/deepset_mcp/main.py`


## ObjectStoreBackend

- create a Protocol for `ObjectStoreBackend`

```python
# src/deepset_mcp/tools/tokonomics/object_store.py
# Add these imports at the top of the file
import time
import uuid
from typing import Protocol

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
```

- create an in-memory and a redis backend

```python
class InMemoryBackend:
    """In-memory backend with counter-based IDs."""
    
    def __init__(self):
        self._data: dict[str, tuple[bytes, float | None]] = {}
        self._counter = 0
    
    def generate_id(self) -> str:
        """Generate sequential ID."""
        self._counter += 1
        return f"obj_{self._counter:03d}"
    
    def set(self, key: str, value: bytes, ttl_seconds: int | None) -> None:
        expiry = None if ttl_seconds is None else time.time() + ttl_seconds
        self._data[key] = (value, expiry)
    
    def get(self, key: str) -> bytes | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry and time.time() > expiry:
            del self._data[key]
            return None
        return value
    
    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None


class RedisBackend:
    """Redis backend with UUID-based IDs."""
    
    def __init__(self, redis_url: str):
        import redis  # Import here to make it optional
        
        self._client = redis.from_url(redis_url, decode_responses=False)
        # Test connection immediately
        self._client.ping()
        
    def generate_id(self) -> str:
        """Generate UUID for distributed uniqueness."""
        # Using UUID4 for Redis to ensure uniqueness across instances
        return f"obj_{uuid.uuid4()}"
    
    def set(self, key: str, value: bytes, ttl_seconds: int | None) -> None:
        if ttl_seconds:
            self._client.setex(key, ttl_seconds, value)
        else:
            self._client.set(key, value)
    
    def get(self, key: str) -> bytes | None:
        return self._client.get(key)
    
    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))
```


Then we need to adapt the ObjectStore to accept a Backend. One challenge here is that we also need to account for serde.
We are proposing an ObjectStore serializing to and from json. It is OK to lose some type information.

```python
import orjson
from typing import Any
from pydantic import BaseModel

class ObjectStore:
    """JSON-based object store with pluggable backends."""
    
    def __init__(self, backend: ObjectStoreBackend, ttl: float = 3600.0):
        self._backend = backend
        self._ttl = ttl
    
    def put(self, obj: Any) -> str:
        """Store any object as JSON using backend-generated ID."""
        obj_id = self._backend.generate_id()
        
        def default(obj: Any) -> Any:
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, BaseModel):
                return obj.model_dump(mode='json')
            raise TypeError
        
        # Serialize with orjson
        json_bytes = orjson.dumps(
            obj,
            default=default
        )
        
        ttl_seconds = int(self._ttl) if self._ttl > 0 else None
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
```

## ObjectStore Configuration

We need to update store.py so that we can initialize the required backend on demand.

```python
# src/deepset_mcp/store.py
import functools
import logging
import os
from typing import Optional

from .tools.tokonomics.object_store import ObjectStore, InMemoryBackend, ObjectStoreBackend

logger = logging.getLogger(__name__)

def create_redis_backend(url: str) -> ObjectStoreBackend:
    """Create Redis backend, failing if connection fails.
    
    :param url: Redis connection URL
    :raises ImportError: If redis package is not installed
    :raises Exception: If Redis connection fails
    """
    try:
        import redis
    except ImportError as e:
        logger.error("Redis package not installed. Install with: pip install redis")
        raise ImportError("Redis package not installed. Install with: pip install deepset-mcp[redis]") from e

    try:
        from .tools.tokonomics.object_store import RedisBackend
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
        ttl: float = 3600.0,
) -> None:
    """Initialize the object store.
    
    :param backend: Backend type ('memory' or 'redis')
    :param redis_url: Redis connection URL (required if backend='redis')
    :param ttl: Time-to-live in seconds for stored objects
    :raises ValueError: If Redis backend selected but no URL provided
    :raises Exception: If Redis connection fails
    """

    if backend == "redis":
        if not redis_url:
            raise ValueError("Need redis url")
        backend_instance = create_redis_backend(redis_url)

    else:  # memory or any other value
        logger.info("Using in-memory backend")
        backend_instance = InMemoryBackend()

    store = ObjectStore(backend=backend_instance, ttl=ttl)
    logger.info(f"Initialized ObjectStore with {backend} backend and TTL={ttl}s")
    
    return store
```

Then we need to allow users to configure the store at the entrypoint.

```python
# src/deepset_mcp/main.py

# Add these new options to the main command:

@app.command()
def main(
    # ... existing options ...
    
    object_store_backend: Annotated[
        str,
        typer.Option(
            "--object-store-backend",
            help="Object store backend type: 'memory' or 'redis'. "
                 "Can also be set via DEEPSET_OBJECT_STORE_BACKEND environment variable.",
        ),
    ] = "memory",
    
    redis_url: Annotated[
        str | None,
        typer.Option(
            "--redis-url",
            help="Redis connection URL (e.g., redis://localhost:6379). "
                 "Can also be set via DEEPSET_REDIS_URL environment variable.",
        ),
    ] = None,

    
    object_store_ttl: Annotated[
        float,
        typer.Option(
            "--object-store-ttl",
            help="TTL in seconds for stored objects. Default: 3600 (1 hour). "
                 "Can also be set via DEEPSET_OBJECT_STORE_TTL environment variable.",
        ),
    ] = 3600.0,
    
) -> None:
    """Run the Deepset MCP server."""
    
    # ... existing validation ...

    # Prefer CLI args over env vars
    backend = object_store_backend or os.getenv("DEEPSET_OBJECT_STORE_BACKEND", "memory")
    redis_url = redis_url or os.getenv("DEEPSET_REDIS_URL")
    ttl = object_store_ttl
    
    
    # Then configure MCP server
    mcp = FastMCP("deepset AI platform MCP server")
    configure_mcp_server(
        # ... existing parameters ...
        # ... add configuration params for ObjectStore
    )
    
    mcp.run(transport=transport.value)
```


### 1. Update `configure_mcp_server` to accept ObjectStore parameters

```python
# src/deepset_mcp/server.py
def configure_mcp_server(
    mcp_server_instance: FastMCP,
    tools_to_register: set[str],
    workspace_mode: WorkspaceMode,
    deepset_api_key: str | None = None,
    deepset_api_url: str | None = None,
    deepset_workspace: str | None = None,
    deepset_docs_shareable_prototype_url: str | None = None,
    get_api_key_from_authorization_header: bool = False,
    # New ObjectStore parameters
    object_store_backend: str = "memory",
    redis_url: str | None = None,
    object_store_ttl: float = 3600.0,
) -> None:
    """Configure the MCP server with the specified tools and settings."""
    
    # Initialize the store before registering tools
    from .store import initialize_store
    store = initialize_store(
        backend=object_store_backend,
        redis_url=redis_url,
        ttl=object_store_ttl
    )
    
    # ... rest of the function remains the same, but pass store to register_tools
    register_tools(
        mcp_server_instance=mcp_server_instance,
        workspace_mode=workspace_mode,
        workspace=deepset_workspace,
        tool_names=tools_to_register,
        docs_config=docs_config,
        get_api_key_from_authorization_header=get_api_key_from_authorization_header,
        api_key=deepset_api_key,
        base_url=deepset_api_url,
        object_store=store,  # Pass the store instance
    )
```

### 2. Update `tool_factory.py` to accept store instance

```python
# src/deepset_mcp/tool_factory.py
def apply_memory(base_func: Callable[..., Any], config: ToolConfig, store: ObjectStore | None = None) -> Callable[..., Any]:
    """
    Applies memory decorators to a function if requested in the ToolConfig.
    
    :param base_func: The function to apply memory decorator to.
    :param config: The ToolConfig for the function.
    :param store: The ObjectStore instance to use
    :returns: Function with memory decorators applied.
    """
    if config.memory_type == MemoryType.NO_MEMORY:
        return base_func
    
    explorer = RichExplorer(store)
    
    if config.memory_type == MemoryType.EXPLORABLE:
        return explorable(object_store=store, explorer=explorer)(base_func)
    elif config.memory_type == MemoryType.REFERENCEABLE:
        return referenceable(object_store=store, explorer=explorer)(base_func)
    elif config.memory_type == MemoryType.BOTH:
        return explorable_and_referenceable(object_store=store, explorer=explorer)(base_func)
    else:
        raise ValueError(f"Invalid memory type: {config.memory_type}")

def build_tool(
    base_func: Callable[..., Any],
    config: ToolConfig,
    workspace_mode: WorkspaceMode,
    workspace: str | None = None,
    use_request_context: bool = True,
    base_url: str | None = None,
    object_store: ObjectStore | None = None,  # New parameter
) -> Callable[..., Awaitable[Any]]:
    """Universal tool creator that handles client injection, workspace, and decorators."""
    
    enhanced_func = base_func
    
    # Apply custom arguments first
    enhanced_func = apply_custom_args(enhanced_func, config)
    
    # Apply memory decorators with the provided store
    enhanced_func = apply_memory(enhanced_func, config, object_store)
    
    # Apply workspace handling
    enhanced_func = apply_workspace(enhanced_func, config, workspace_mode, workspace)
    
    # Apply client injection (adds ctx parameter if needed)
    enhanced_func = apply_client(enhanced_func, config, use_request_context=use_request_context, base_url=base_url)
    
    # ... rest of the function (async wrapper if needed)

def register_tools(
    mcp_server_instance: FastMCP,
    workspace_mode: WorkspaceMode,
    api_key: str | None = None,
    workspace: str | None = None,
    tool_names: set[str] | None = None,
    get_api_key_from_authorization_header: bool = True,
    docs_config: DeepsetDocsConfig | None = None,
    base_url: str | None = None,
    object_store: ObjectStore | None = None,  # New parameter
) -> None:
    """Register tools with the MCP server."""
    
    # Pass store to build_tool
    for tool_name in tool_names:
        enhanced_func = build_tool(
            base_func=base_func,
            config=config,
            workspace_mode=workspace_mode,
            workspace=workspace,
            use_request_context=use_request_context,
            base_url=base_url,
            object_store=object_store,
        )
```

### 3. Update `store.py` to return the store instance

```python
# src/deepset_mcp/store.py
# Remove the global STORE variable
# STORE = ObjectStore()  # DELETE THIS LINE

# Update the initialize_store function to return the store
def initialize_store(
        backend: str = "memory",
        redis_url: str | None = None,
        ttl: float = 3600.0,
) -> ObjectStore:  # Change return type from None to ObjectStore
    """Initialize and return the object store."""
    # ... existing implementation ...
    
    store = ObjectStore(backend=backend_instance, ttl=ttl)
    logger.info(f"Initialized ObjectStore with {backend} backend and TTL={ttl}s")
    
    return store  # Return the store instance
```

### 4. Update direct ObjectStore tool usage

```python
# src/deepset_mcp/tools/object_store.py
# These tools need to be updated to accept the store as a parameter
# instead of importing the global STORE

# Example update for one of the tools:
async def object_store_put(obj: Any, store: ObjectStore) -> str:
    """Put an object into the store."""
    return store.put(obj)

# Similar updates for object_store_get, object_store_delete, etc.
```

### 5. Update main.py to pass ObjectStore parameters

```python
# src/deepset_mcp/main.py
# In the main() function, pass the new parameters to configure_mcp_server:

configure_mcp_server(
    mcp_server_instance=mcp,
    workspace_mode=workspace_mode,
    deepset_api_key=api_key,
    deepset_api_url=api_url,
    deepset_workspace=workspace,
    tools_to_register=tool_names,
    deepset_docs_shareable_prototype_url=docs_share_url,
    get_api_key_from_authorization_header=api_key_from_auth_header,
    # New ObjectStore parameters
    object_store_backend=backend,
    redis_url=redis_url,
    object_store_ttl=ttl,
)
```

### 6. Testing Plan

1. **Unit Tests for Backends**:
   ```python
   # tests/test_object_store_backends.py
   - Test InMemoryBackend (ID generation, set/get/delete, TTL expiration)
   - Test RedisBackend (ID generation, set/get/delete, TTL, connection failures)
   - Test Protocol compliance for both backends
   ```

2. **Integration Tests for ObjectStore**:
   ```python
   # tests/test_object_store.py
   - Test JSON serialization (including sets, Pydantic models)
   - Test with both backends (parametrized tests)
   - Test TTL behavior
   - Test error handling
   ```

3. **End-to-End Tests**:
   ```python
   # tests/test_server_with_store.py
   - Test server initialization with different backends
   - Test tool execution with memory features
   - Test Redis connection failure handling
   - Test environment variable configuration
   ```

### 7. Additional Considerations

1. **Redis Connection Pooling**: The Redis client should use connection pooling by default
2. **Error Handling**: Need graceful degradation if Redis is unavailable after initial connection
3. **Monitoring**: Consider adding metrics for store operations (hits/misses, latency)
4. **Security**: Ensure Redis connection uses proper authentication and SSL if needed
5. **Key Namespacing**: Consider adding a key prefix for multi-tenant environments
7. **Dependencies**: Add `redis` as an optional dependency in pyproject.toml:
   ```toml
   [project.optional-dependencies]
   redis = ["redis>=4.0.0"]
   ```

