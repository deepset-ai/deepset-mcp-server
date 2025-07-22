# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for the tokonomics sub-package."""

import asyncio
import time
from collections.abc import Generator
from typing import Any

import pytest
from glom import glom

try:
    import docker  # type: ignore[import-untyped]
    from docker.errors import NotFound  # type: ignore[import-untyped]
except ImportError:
    docker = None
    NotFound = Exception

from deepset_mcp.tools.tokonomics.decorators import explorable, explorable_and_referenceable, referenceable
from deepset_mcp.tools.tokonomics.explorer import RichExplorer
from deepset_mcp.tools.tokonomics.object_store import InMemoryBackend, ObjectStore, RedisBackend

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def docker_client() -> Any:
    """Create a Docker client for the test session."""
    if docker is None:
        pytest.skip("Docker not available")
    try:
        return docker.from_env()
    except Exception:
        pytest.skip("Docker not available")


@pytest.fixture(scope="session")
def redis_container(docker_client: Any) -> Generator[Any, None, None]:
    """Start a Redis container for the test session."""

    container_name = "test-redis-tokonomics-session"

    # Clean up any existing container
    try:
        old_container = docker_client.containers.get(container_name)
        old_container.stop()
        old_container.remove()
    except NotFound:
        pass

    # Start Redis container
    container = docker_client.containers.run(
        "redis:7.4.5-alpine",
        name=container_name,
        ports={"6379/tcp": 16379},
        detach=True,
        remove=True,
    )

    # Wait for Redis to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            # Try to connect
            from deepset_mcp.tools.tokonomics.object_store import RedisBackend

            RedisBackend("redis://localhost:16379/0")
            break
        except Exception as e:
            if i == max_retries - 1:
                container.stop()
                raise e
            time.sleep(0.5)

    yield container

    # Cleanup
    container.stop()


@pytest.fixture
def redis_backend(redis_container: Any) -> RedisBackend:
    """Create a RedisBackend instance using the session Redis container."""
    backend = RedisBackend("redis://localhost:16379/0")

    # Clear all keys before each test for isolation
    try:
        import redis

        r = redis.from_url("redis://localhost:16379/0")  # type: ignore[no-untyped-call]
        r.flushall()
    except ImportError:
        pass

    return backend


@pytest.fixture
def in_memory_backend() -> InMemoryBackend:
    """Create an InMemoryBackend instance."""
    return InMemoryBackend()


@pytest.fixture(params=["memory", "redis"], ids=["memory", "redis"])
def backend(
    request: Any, in_memory_backend: InMemoryBackend, redis_backend: RedisBackend
) -> InMemoryBackend | RedisBackend:
    """Parametrized fixture providing both backend types."""
    if request.param == "memory":
        return in_memory_backend
    else:
        return redis_backend


@pytest.fixture
def object_store(backend: InMemoryBackend | RedisBackend) -> ObjectStore:
    """Create an ObjectStore with the given backend."""
    return ObjectStore(backend=backend, ttl=60)


@pytest.fixture
def explorer(object_store: ObjectStore) -> RichExplorer:
    """Create a RichExplorer instance."""
    return RichExplorer(store=object_store)


class TestObjectStore:
    """Integration tests for ObjectStore functionality."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_basic_types(self, object_store: ObjectStore) -> None:
        """Test storing and retrieving basic Python types."""
        test_data = [
            ("string", "Hello, World!"),
            ("int", 42),
            ("float", 3.14159),
            ("bool", True),
            ("list", [1, 2, 3, "four"]),
            ("dict", {"name": "Alice", "age": 30, "hobbies": ["reading", "coding"]}),
            ("tuple", (1, 2, 3)),
            ("set", {1, 2, 3, 4}),
            ("none", None),
        ]

        obj_ids = {}

        # Store all objects
        for name, value in test_data:
            obj_id = object_store.put(value)
            obj_ids[name] = obj_id
            assert obj_id.startswith("obj_")

        # Retrieve and verify
        for name, expected_value in test_data:
            obj_id = obj_ids[name]
            retrieved = object_store.get(obj_id)

            # Handle set/tuple conversion to list
            if isinstance(expected_value, set | tuple):
                assert retrieved == list(expected_value)
            else:
                assert retrieved == expected_value

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, backend: InMemoryBackend | RedisBackend) -> None:
        """Test that objects expire after TTL."""
        # Create store with 1 second TTL
        store = ObjectStore(backend=backend, ttl=1)

        # Store object
        obj_id = store.put({"data": "test"})

        # Should be retrievable immediately
        assert store.get(obj_id) == {"data": "test"}

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be None after expiration
        assert store.get(obj_id) is None

    @pytest.mark.asyncio
    async def test_delete_object(self, object_store: ObjectStore) -> None:
        """Test deleting objects from store."""
        # Store object
        obj_id = object_store.put({"key": "value"})

        # Verify it exists
        assert object_store.get(obj_id) == {"key": "value"}

        # Delete it
        assert object_store.delete(obj_id) is True

        # Verify it's gone
        assert object_store.get(obj_id) is None

        # Deleting again should return False
        assert object_store.delete(obj_id) is False

    @pytest.mark.asyncio
    async def test_pydantic_model_serialization(self, object_store: ObjectStore) -> None:
        """Test storing Pydantic models."""
        from pydantic import BaseModel

        class Role(BaseModel):
            id: int
            name: str

        class User(BaseModel):
            name: str
            age: int
            email: str
            role: Role

        user = User(name="Bob", age=25, email="bob@example.com", role=Role(id=1, name="admin"))
        obj_id = object_store.put(user)

        # Retrieved as dict, not Pydantic model
        retrieved = object_store.get(obj_id)
        assert retrieved == {"name": "Bob", "age": 25, "email": "bob@example.com", "role": {"id": 1, "name": "admin"}}

    @pytest.mark.asyncio
    async def test_explorer_with_non_json_types(self, object_store: ObjectStore) -> None:
        """Test explorer with objects that have custom representations."""
        from datetime import date, datetime

        # These will be converted to JSON-compatible types
        data = {
            "date": date(2024, 1, 15),
            "datetime": datetime(2024, 1, 15, 10, 30),
            "bytes": b"binary data",
        }

        # Will raise TypeError for bytes
        with pytest.raises(TypeError):
            object_store.put(data)

        # Without bytes, should work
        data_without_bytes = {k: v for k, v in data.items() if k != "bytes"}
        obj_id = object_store.put(data_without_bytes)

        # Dates become strings in JSON
        retrieved = object_store.get(obj_id)
        assert retrieved is not None
        assert isinstance(retrieved["date"], str)
        assert isinstance(retrieved["datetime"], str)


class TestRichExplorer:
    """Integration tests for RichExplorer functionality."""

    @pytest.mark.asyncio
    async def test_explore_basic_objects(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test exploring various object types."""
        test_objects = {
            "string": "Hello, World!",
            "list": ["apple", "banana", "cherry"],
            "dict": {"name": "Alice", "scores": [95, 87, 92]},
            "nested": {"level1": {"level2": {"level3": "deep value"}}},
        }

        for _name, obj in test_objects.items():
            obj_id = object_store.put(obj)
            preview = explorer.explore(obj_id)

            # Verify preview contains object ID and type
            assert f"@{obj_id}" in preview
            assert type(obj).__name__ in preview

    @pytest.mark.asyncio
    async def test_explore_with_path_navigation(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test navigating object paths."""
        data = {
            "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "config": {"debug": True, "timeout": 30},
        }

        obj_id = object_store.put(data)

        # Test various path navigations
        paths_and_expected = [
            ("users", list),
            ("users[0]", dict),
            ("users[0].name", str),
            ("config.debug", bool),
            ("config.timeout", int),
        ]

        for path, expected_type in paths_and_expected:
            preview = explorer.explore(obj_id, path)
            assert f"@{obj_id}.{path}" in preview
            assert expected_type.__name__ in preview

    @pytest.mark.asyncio
    async def test_search_in_strings(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test search functionality within string objects."""
        text = """
        Python is a high-level programming language.
        Python is known for its simplicity and readability.
        Many developers love Python for data science and web development.
        """

        obj_id = object_store.put(text)

        # Search for "Python"
        results = explorer.search(obj_id, "Python")
        assert "Found 3 matches" in results
        assert "[Python]" in results

        # Case-insensitive search
        results = explorer.search(obj_id, "python", case_sensitive=False)
        assert "Found 3 matches" in results

        # No matches
        results = explorer.search(obj_id, "Java")
        assert "No matches found" in results

    @pytest.mark.asyncio
    async def test_slice_strings_and_lists(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing functionality."""
        # Test string slicing
        text = "The quick brown fox jumps over the lazy dog"
        obj_id = object_store.put(text)

        slice_result = explorer.slice(obj_id, 0, 10)
        assert "String slice [0:10]" in slice_result
        assert "The quick " in slice_result

        # Test list slicing
        numbers = list(range(20))
        obj_id = object_store.put(numbers)

        slice_result = explorer.slice(obj_id, 5, 10)
        assert "List slice [5:10]" in slice_result
        assert "[5, 6, 7, 8, 9]" in slice_result

    @pytest.mark.asyncio
    async def test_invalid_paths(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test error handling for invalid paths."""
        data = {"key": "value"}
        obj_id = object_store.put(data)

        # Non-existent path
        with pytest.raises(ValueError, match="does not have a value at path"):
            explorer.explore(obj_id, "nonexistent.path")

        # Invalid attribute access
        with pytest.raises(ValueError, match="Access to attribute .* is not permitted"):
            explorer.explore(obj_id, "__class__")

    @pytest.mark.asyncio
    async def test_unicode_and_special_chars(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test handling of Unicode and special characters."""
        data = {
            "emoji": "🐍🔥💻",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "Tab\tNewline\nCarriage\rReturn",
            "quotes": 'He said "Hello"',
        }

        obj_id = object_store.put(data)
        retrieved = object_store.get(obj_id)

        # All Unicode should be preserved
        assert retrieved == data

        # Search should work with Unicode
        text_id = object_store.put(data["chinese"])
        results = explorer.search(text_id, "世界")
        assert "Found 1 matches" in results


class TestDecoratorsFunctionality:
    """Integration tests for decorator functionality."""

    @pytest.mark.asyncio
    async def test_explorable_decorator(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test @explorable decorator functionality."""

        @explorable(object_store=object_store, explorer=explorer)
        def process_data(x: int, y: int) -> dict[str, int]:
            """Process two integers."""
            return {"sum": x + y, "product": x * y}

        # Call the decorated function
        result: str = process_data(5, 3)  # type: ignore[assignment]

        # Verify result is a string (preview)
        assert isinstance(result, str)
        assert "@" in result
        assert "dict" in result

        # Verify object is stored (should be obj_001)
        stored = object_store.get("obj_001")
        assert stored == {"sum": 8, "product": 15}

    @pytest.mark.asyncio
    async def test_explorable_decorator_async(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test @explorable decorator with async functions."""

        @explorable(object_store=object_store, explorer=explorer)
        async def async_fetch_data(item_id: int) -> dict[str, Any]:
            """Fetch data asynchronously."""
            await asyncio.sleep(0.1)  # Simulate async operation
            return {"id": item_id, "data": f"Item {item_id}"}

        # Call the decorated async function
        result: str = await async_fetch_data(42)  # type: ignore[assignment]

        # Verify result is a string (preview)
        assert isinstance(result, str)
        assert "@" in result
        # Verify object is stored (should be obj_001)
        assert object_store.get("obj_001") == {"id": 42, "data": "Item 42"}

    @pytest.mark.asyncio
    async def test_referenceable_decorator(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test @referenceable decorator functionality."""

        @referenceable(object_store=object_store, explorer=explorer)
        def merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
            """Merge two dictionaries."""
            return {**dict1, **dict2}

        # Store some test data
        data1 = {"a": 1, "b": 2}
        data2 = {"c": 3, "d": 4}
        obj_id1 = object_store.put(data1)
        obj_id2 = object_store.put(data2)

        # Call with references
        result = merge_dicts(f"@{obj_id1}", f"@{obj_id2}")  # type: ignore[arg-type]
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

        # Call with mixed references and values
        result = merge_dicts(f"@{obj_id1}", {"e": 5})  # type: ignore[arg-type]
        assert result == {"a": 1, "b": 2, "e": 5}

        # Call with actual values
        result = merge_dicts({"x": 10}, {"y": 20})
        assert result == {"x": 10, "y": 20}

    @pytest.mark.asyncio
    async def test_referenceable_with_paths(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test @referenceable decorator with path navigation."""

        @referenceable(object_store=object_store, explorer=explorer)
        def calculate_total(prices: list[float], tax_rate: float) -> float:
            """Calculate total with tax."""
            subtotal = sum(prices)
            return subtotal * (1 + tax_rate)

        # Store complex data
        data = {
            "order": {
                "items": [
                    {"name": "Widget", "price": 10.00},
                    {"name": "Gadget", "price": 15.50},
                    {"name": "Doohickey", "price": 7.25},
                ]
            },
            "config": {"tax_rate": 0.08},
        }
        obj_id = object_store.put(data)

        # Extract prices using glom to match the path syntax
        prices = glom(data, "order.items.*.price")

        # Call with path references - note we need to store the intermediate results
        prices_id = object_store.put(prices)
        result = calculate_total(f"@{prices_id}", f"@{obj_id}.config.tax_rate")  # type: ignore[arg-type]

        expected = sum(prices) * 1.08
        assert abs(result - expected) < 0.01

    @pytest.mark.asyncio
    async def test_explorable_and_referenceable(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test @explorable_and_referenceable decorator."""

        @explorable_and_referenceable(object_store=object_store, explorer=explorer)
        def transform_data(input_data: dict[str, Any], multiplier: int) -> dict[str, Any]:
            """Transform data by multiplying numeric values."""
            result = {}
            for key, value in input_data.items():
                if isinstance(value, int | float):
                    result[key] = value * multiplier
                else:
                    result[key] = value
            return result

        # Store input data
        data = {"a": 10, "b": 20, "c": "text"}
        data_id = object_store.put(data)

        # Call with reference
        result: str = transform_data(f"@{data_id}", 3)  # type: ignore[assignment,arg-type]

        # Verify it returns string (preview)
        assert isinstance(result, str)
        assert "@" in result

        # Verify stored and can be referenced (should be obj_002 since data_id is obj_001)
        assert object_store.get("obj_002") == {"a": 30, "b": 60, "c": "text"}

        # Use the result as input to another call
        result2: str = transform_data("@obj_002", 2)  # type: ignore[assignment,arg-type]
        assert isinstance(result2, str)
        assert "@" in result2
        assert object_store.get("obj_003") == {"a": 60, "b": 120, "c": "text"}

    @pytest.mark.asyncio
    async def test_error_handling_invalid_references(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test error handling for invalid references."""

        @referenceable(object_store=object_store, explorer=explorer)
        def process(data: dict[str, Any]) -> str:
            return str(data)

        # Non-existent object
        with pytest.raises(ValueError, match="Object @nonexistent not found"):
            process("@nonexistent")  # type: ignore[arg-type]

        # Invalid path
        obj_id = object_store.put({"key": "value"})
        with pytest.raises(ValueError, match="Navigation error"):
            process(f"@{obj_id}.invalid.path")  # type: ignore[arg-type]

        # Invalid string (not a reference) for non-string parameter
        @referenceable(object_store=object_store, explorer=explorer)
        def needs_int(x: int) -> int:
            return x * 2

        with pytest.raises(TypeError, match="Use '@obj_id' for references"):
            needs_int("not_a_reference")  # type: ignore[arg-type]


class TestEndToEndScenarios:
    """Integration tests for end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_data_pipeline_scenario(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a realistic data processing pipeline scenario."""

        @explorable(object_store=object_store, explorer=explorer)
        def load_data() -> list[dict[str, Any]]:
            """Load sample data."""
            return [
                {"id": 1, "name": "Alice", "score": 85},
                {"id": 2, "name": "Bob", "score": 92},
                {"id": 3, "name": "Charlie", "score": 78},
                {"id": 4, "name": "Diana", "score": 95},
            ]

        @explorable_and_referenceable(object_store=object_store, explorer=explorer)
        def filter_high_scores(data: list[dict[str, Any]], threshold: int) -> list[dict[str, Any]]:
            """Filter records with scores above threshold."""
            return [record for record in data if record["score"] > threshold]

        @explorable_and_referenceable(object_store=object_store, explorer=explorer)
        def calculate_average(data: list[dict[str, Any]]) -> float:
            """Calculate average score."""
            if not data:
                return 0.0
            total: float = sum(record["score"] for record in data)
            return total / len(data)

        # Execute pipeline
        raw_data: str = load_data()  # type: ignore[assignment]
        assert isinstance(raw_data, str)
        assert "@" in raw_data

        # Filter high scores using reference (raw_data should be obj_001)
        high_scores: str = filter_high_scores("@obj_001", 80)  # type: ignore[assignment,arg-type]
        assert isinstance(high_scores, str)
        assert "@" in high_scores

        # Calculate average using reference (high_scores should be obj_002)
        avg_score: str = calculate_average("@obj_002")  # type: ignore[assignment,arg-type]
        assert isinstance(avg_score, str)
        assert "@" in avg_score

        # Verify results by checking stored objects
        high_scores_data = object_store.get("obj_002")
        avg_score_data = object_store.get("obj_003")
        assert high_scores_data is not None
        assert len(high_scores_data) == 3
        assert avg_score_data == (85 + 92 + 95) / 3

        # Explore the results
        preview = explorer.explore("obj_002")
        assert "list" in preview
        assert "length: 3" in preview

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test concurrent operations on the object store."""

        @explorable(object_store=object_store, explorer=explorer)
        async def async_process(n: int) -> dict[str, int]:
            """Async processing function."""
            await asyncio.sleep(0.1)
            return {"input": n, "output": n * n}

        # Run multiple concurrent operations
        tasks = [async_process(i) for i in range(10)]
        results: list[str] = await asyncio.gather(*tasks)  # type: ignore[assignment]

        # Verify all results are strings and objects are stored
        for i, result in enumerate(results):
            assert isinstance(result, str)
            assert "@" in result
            # Objects should be stored as obj_001, obj_002, etc.
            obj_id = f"obj_{i + 1:03d}"
            stored = object_store.get(obj_id)
            assert stored == {"input": i, "output": i * i}

    @pytest.mark.asyncio
    async def test_complex_object_navigation(self, object_store: ObjectStore, explorer: RichExplorer) -> None:
        """Test navigation through complex nested structures."""

        complex_data = {
            "company": {
                "name": "TechCorp",
                "departments": [
                    {
                        "name": "Engineering",
                        "teams": [
                            {"name": "Backend", "size": 5},
                            {"name": "Frontend", "size": 4},
                            {"name": "DevOps", "size": 3},
                        ],
                    },
                    {"name": "Sales", "teams": [{"name": "Enterprise", "size": 6}, {"name": "SMB", "size": 8}]},
                ],
            }
        }

        obj_id = object_store.put(complex_data)

        # Test various navigations
        test_paths = [
            "company.name",
            "company.departments[0].name",
            "company.departments[0].teams[1].name",
            "company.departments[1].teams",
        ]

        for path in test_paths:
            preview = explorer.explore(obj_id, path)
            assert f"@{obj_id}.{path}" in preview

            # Verify we can navigate to the same path via reference
            @referenceable(object_store=object_store, explorer=explorer)
            def get_value(data: Any) -> Any:
                return data

            value = get_value(f"@{obj_id}.{path}")
            assert value is not None
