# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import time
from typing import Any

import pytest

from deepset_mcp.tools.tokonomics import (
    Explorable,
    ObjectStore,
    RichExplorer,
    explorable,
    referenceable,
)
from deepset_mcp.tools.tokonomics.decorators import explorable_and_referenceable


class TestTokonomicsIntegration:
    """Integration tests for the tokonomics package."""

    @pytest.fixture
    def store(self) -> ObjectStore:
        """Create an ObjectStore for testing."""
        return ObjectStore(ttl=0)  # No expiry for tests

    @pytest.fixture
    def explorer(self, store: ObjectStore) -> RichExplorer:
        """Create a RichExplorer for testing."""
        return RichExplorer(store)

    def test_end_to_end_workflow(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test complete end-to-end workflow with multiple functions."""

        @explorable(object_store=store, explorer=explorer)
        def load_data() -> dict:
            """Load initial data."""
            return {
                "users": [
                    {"name": "Alice", "age": 30, "city": "New York"},
                    {"name": "Bob", "age": 25, "city": "San Francisco"},
                    {"name": "Charlie", "age": 35, "city": "Boston"},
                ],
                "metadata": {"total_users": 3, "last_updated": "2024-01-01"},
            }

        @referenceable(object_store=store, explorer=explorer)
        def filter_users_by_age(data: dict, min_age: int) -> list:
            """Filter users by minimum age."""
            return [user for user in data["users"] if user["age"] >= min_age]

        @explorable_and_referenceable(object_store=store, explorer=explorer)
        def get_user_cities(users: list) -> dict:
            """Get unique cities from user list."""
            cities = {user["city"] for user in users}
            return {"cities": list(cities), "count": len(cities)}

        # Step 1: Load data
        data_result = load_data()
        assert isinstance(data_result, Explorable)
        assert data_result.obj_id == "obj_001"

        # Step 2: Filter users (using reference)
        filtered_users = filter_users_by_age(f"@{data_result.obj_id}", 30)
        assert len(filtered_users) == 2  # Alice and Charlie
        assert all(user["age"] >= 30 for user in filtered_users)

        # Step 3: Get cities (using direct value, returns explorable)
        cities_result = get_user_cities(filtered_users)
        assert isinstance(cities_result, Explorable)
        assert cities_result.obj_id == "obj_002"
        assert set(cities_result.value["cities"]) == {"New York", "Boston"}
        assert cities_result.value["count"] == 2

    def test_complex_path_navigation(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test complex path navigation scenarios."""

        # Create complex nested data
        complex_data = {
            "api_response": {
                "status": "success",
                "data": {
                    "results": [
                        {
                            "id": 1,
                            "details": {"title": "First Item", "tags": ["important", "urgent"]},
                            "metrics": {"views": 100, "likes": 25},
                        },
                        {
                            "id": 2,
                            "details": {"title": "Second Item", "tags": ["normal"]},
                            "metrics": {"views": 50, "likes": 10},
                        },
                    ],
                    "pagination": {"total": 2, "page": 1, "per_page": 10},
                },
            }
        }

        obj_id = store.put(complex_data)

        @referenceable(object_store=store, explorer=explorer)
        def process_item_title(title: str, prefix: str = "Processed: ") -> str:
            """Process an item title."""
            return f"{prefix}{title}"

        @referenceable(object_store=store, explorer=explorer)
        def sum_metrics(metrics: dict) -> int:
            """Sum all values in metrics dict."""
            return sum(metrics.values())

        # Test various path navigation scenarios

        # Navigate to nested string
        result1 = process_item_title(f"@{obj_id}.api_response.data.results.0.details.title")
        assert result1 == "Processed: First Item"

        # Navigate to nested dict
        result2 = sum_metrics(f"@{obj_id}.api_response.data.results.1.metrics")
        assert result2 == 60  # 50 + 10

        # Navigate to array element
        result3 = process_item_title(f"@{obj_id}.api_response.data.results.0.details.tags.0", "Tag: ")
        assert result3 == "Tag: important"

    def test_error_handling_scenarios(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test various error handling scenarios."""

        @referenceable(object_store=store, explorer=explorer)
        def process_data(data: dict) -> str:
            return f"Processed {len(data)} items"

        # Test non-existent object reference
        with pytest.raises(ValueError, match="Object @obj_999 not found or expired"):
            process_data("@obj_999")

        # Test invalid reference format
        with pytest.raises(TypeError, match="Parameter 'data' expects"):
            process_data("invalid_ref")

        # Test invalid path navigation
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        with pytest.raises(ValueError, match="Navigation error"):
            process_data(f"@{obj_id}.nonexistent.path")

        # Test type mismatch for non-string parameters
        @referenceable(object_store=store, explorer=explorer)
        def numeric_only(num: int) -> int:
            return num * 2

        with pytest.raises(TypeError, match="Parameter 'num' expects"):
            numeric_only("not_a_reference_or_number")

    def test_explorer_functionality_with_stored_objects(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test explorer functionality with objects from decorated functions."""

        @explorable(object_store=store, explorer=explorer)
        def create_test_data() -> dict:
            """Create test data for exploration."""
            return {
                "users": [
                    {"name": "Alice", "bio": "Software engineer who loves hiking"},
                    {"name": "Bob", "bio": "Data scientist passionate about AI"},
                ],
                "settings": {"theme": "dark", "notifications": True},
                "content": "The quick brown fox jumps over the lazy dog. " * 10,
            }

        # Create and store data
        result = create_test_data()
        obj_id = result.obj_id

        # Test exploration
        explore_result = explorer.explore(obj_id)
        assert f"@{obj_id} → dict" in explore_result
        assert "users" in explore_result
        assert "settings" in explore_result

        # Test path navigation
        user_result = explorer.explore(obj_id, "users.0.name")
        assert "Alice" in user_result

        # Test search functionality
        search_result = explorer.search(obj_id, "fox", path="content")
        assert "Found" in search_result
        assert "[fox]" in search_result

        # Test slicing
        slice_result = explorer.slice(obj_id, 0, 50, path="content")
        assert "String slice [0:50]" in slice_result

    def test_async_function_integration(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test integration with async functions."""

        @explorable(object_store=store, explorer=explorer)
        async def async_data_loader() -> dict:
            """Async function that loads data."""
            # Simulate async operation
            await asyncio.sleep(0.01)
            return {"async_data": "loaded", "timestamp": "2024-01-01"}

        @referenceable(object_store=store, explorer=explorer)
        async def async_processor(data: dict, suffix: str) -> str:
            """Async function that processes data."""
            await asyncio.sleep(0.01)
            return f"{data['async_data']}_{suffix}"

        @explorable_and_referenceable(object_store=store, explorer=explorer)
        async def async_combined(data: dict) -> dict:
            """Async function with combined decorator."""
            await asyncio.sleep(0.01)
            return {"processed": data, "status": "complete"}

        async def run_async_test() -> None:
            # Test async explorable
            data_result = await async_data_loader()
            assert isinstance(data_result, Explorable)
            assert data_result.value["async_data"] == "loaded"

            # Test async referenceable
            processed = await async_processor(f"@{data_result.obj_id}", "processed")
            assert processed == "loaded_processed"

            # Test async combined
            final_result = await async_combined(f"@{data_result.obj_id}")
            assert isinstance(final_result, Explorable)
            assert final_result.value["status"] == "complete"

        asyncio.run(run_async_test())

    def test_ttl_expiration_integration(self, explorer: RichExplorer) -> None:
        """Test TTL expiration in integrated workflow."""
        # Create store with short TTL
        short_ttl_store = ObjectStore(ttl=0.1)  # 100ms TTL
        # Create explorer that uses the same store
        short_ttl_explorer = RichExplorer(short_ttl_store)

        @explorable(object_store=short_ttl_store, explorer=short_ttl_explorer)
        def create_data() -> dict:
            return {"data": "will_expire"}

        @referenceable(object_store=short_ttl_store, explorer=short_ttl_explorer)
        def use_data(data: dict) -> str:
            return data["data"]

        # Create data
        result = create_data()
        obj_id = result.obj_id

        # Should work immediately
        processed = use_data(f"@{obj_id}")
        assert processed == "will_expire"

        # Wait for expiration
        time.sleep(0.2)

        # Should fail after expiration
        with pytest.raises(ValueError, match="not found or expired"):
            use_data(f"@{obj_id}")

    def test_large_object_handling(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test handling of large objects with preview limits."""

        @explorable(object_store=store, explorer=explorer)
        def create_large_data() -> dict:
            """Create large data structure."""
            return {
                "large_list": list(range(1000)),
                "large_dict": {f"key_{i}": f"value_{i}" for i in range(100)},
                "long_string": "A" * 2000,
                "nested": {"deep": {"deeper": {"data": list(range(50))}}},
            }

        # Create large object
        result = create_large_data()

        # Preview should be truncated but accessible
        preview = str(result)
        assert len(preview) < 10000  # Should be truncated
        assert "large_list" in preview

        # Full object should be accessible via value
        full_data = result.value
        assert len(full_data["large_list"]) == 1000
        assert len(full_data["large_dict"]) == 100
        assert len(full_data["long_string"]) == 2000

        # Explorer should handle large objects gracefully
        explore_result = explorer.explore(result.obj_id)
        assert f"@{result.obj_id} → dict" in explore_result

        # Slicing should work on large structures
        slice_result = explorer.slice(result.obj_id, 0, 10, path="large_list")
        assert "List slice [0:10]" in slice_result

    def test_chained_operations_with_exploration(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test chained operations with intermediate exploration."""

        @explorable(object_store=store, explorer=explorer)
        def step1() -> dict:
            return {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}

        @explorable_and_referenceable(object_store=store, explorer=explorer)
        def step2(data: dict, threshold: int) -> dict:
            filtered = [n for n in data["numbers"] if n > threshold]
            return {"filtered": filtered, "count": len(filtered)}

        @explorable_and_referenceable(object_store=store, explorer=explorer)
        def step3(stats: dict) -> dict:
            return {
                "doubled": [n * 2 for n in stats["filtered"]],
                "original_count": stats["count"],
                "final_sum": sum(n * 2 for n in stats["filtered"]),
            }

        # Execute pipeline
        result1 = step1()

        # Explore intermediate result
        explore1 = explorer.explore(result1.obj_id, "numbers")
        assert "list" in explore1

        result2 = step2(f"@{result1.obj_id}", 5)

        # Explore filtered result
        explore2 = explorer.explore(result2.obj_id, "filtered")
        assert "6" in explore2 and "7" in explore2 and "10" in explore2

        result3 = step3(f"@{result2.obj_id}")

        # Verify final result
        assert result3.value["doubled"] == [12, 14, 16, 18, 20]
        assert result3.value["original_count"] == 5
        assert result3.value["final_sum"] == 80

        # Explore final result structure
        explore3 = explorer.explore(result3.obj_id)
        assert "doubled" in explore3
        assert "final_sum" in explore3

    def test_reference_validation_edge_cases(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test edge cases in reference validation."""

        # Create test data with edge case paths
        edge_case_data = {
            "normal_key": "value",
            "123numeric": "numeric_key",
            "nested": {
                "array": [{"deep": "value"}],
                "dict_with_nums": {"1": "one", "2": "two"},
            },
        }

        obj_id = store.put(edge_case_data)

        @referenceable(object_store=store, explorer=explorer)
        def access_data(value: Any) -> str:
            return str(value)

        # Test valid edge cases - skip 123numeric as it's not a valid identifier
        # result1 = access_data(f"@{obj_id}.123numeric")
        # assert result1 == "numeric_key"

        result2 = access_data(f"@{obj_id}.nested.array.0.deep")
        assert result2 == "value"

        # Test path validation with explorer
        try:
            # This should work - numeric keys are allowed
            explorer_result = explorer.explore(obj_id, "nested.dict_with_nums.1")
            assert "one" in explorer_result
        except ValueError:
            pytest.fail("Should allow numeric string keys")

        # Test disallowed paths
        with pytest.raises(ValueError, match="Access to attribute.*not permitted"):
            explorer.explore(obj_id, "__dict__")

    def test_documentation_enhancement_integration(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that documentation enhancement works in integrated scenarios."""

        @explorable(object_store=store, explorer=explorer)
        def documented_explorable(data: list) -> dict:
            """
            Process a list of items and return statistics.

            Parameters
            ----------
            data : list
                List of numeric items to process.

            Returns
            -------
            dict
                Dictionary with statistics.
            """
            return {
                "count": len(data),
                "sum": sum(data),
                "average": sum(data) / len(data) if data else 0,
            }

        @referenceable(object_store=store, explorer=explorer)
        def documented_referenceable(stats: dict, precision: int = 2) -> str:
            """
            Format statistics with specified precision.

            Parameters
            ----------
            stats : dict
                Statistics dictionary.
            precision : int, optional
                Number of decimal places (default: 2).

            Returns
            -------
            str
                Formatted statistics string.
            """
            avg = round(stats["average"], precision)
            return f"Count: {stats['count']}, Sum: {stats['sum']}, Avg: {avg}"

        # Check enhanced docstrings
        explorable_doc = documented_explorable.__doc__
        assert "Process a list of items" in explorable_doc
        assert "**Output Storage**" in explorable_doc
        assert "automatically stored" in explorable_doc

        referenceable_doc = documented_referenceable.__doc__
        assert "Format statistics" in referenceable_doc
        assert "**Reference Support**" in referenceable_doc
        assert "All parameters accept object references" in referenceable_doc
        assert "``stats``: <class 'dict'> → dict | str" in referenceable_doc

        # Test functionality with enhanced docs
        result1 = documented_explorable([10, 20, 30, 40, 50])
        result2 = documented_referenceable(f"@{result1.obj_id}", 1)

        assert "Count: 5, Sum: 150, Avg: 30.0" == result2
