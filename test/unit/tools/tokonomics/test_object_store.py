# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import time
from unittest.mock import patch

from deepset_mcp.tools.tokonomics.object_store import ObjectStore


class TestObjectStore:
    """Test ObjectStore class."""

    def test_init_default_ttl(self) -> None:
        """Test ObjectStore initialization with default TTL."""
        store = ObjectStore()
        assert store._ttl == 3600.0
        assert store._objects == {}
        assert store._counter == 0

    def test_init_custom_ttl(self) -> None:
        """Test ObjectStore initialization with custom TTL."""
        store = ObjectStore(ttl=7200.0)
        assert store._ttl == 7200.0

    def test_init_zero_ttl(self) -> None:
        """Test ObjectStore initialization with zero TTL (no expiry)."""
        store = ObjectStore(ttl=0)
        assert store._ttl == 0.0

    def test_put_single_object(self) -> None:
        """Test storing a single object."""
        store = ObjectStore()
        test_obj = {"test": "data"}

        obj_id = store.put(test_obj)

        assert obj_id == "obj_001"
        assert store._counter == 1
        assert len(store._objects) == 1
        assert store._objects[obj_id][0] == test_obj

    def test_put_multiple_objects(self) -> None:
        """Test storing multiple objects."""
        store = ObjectStore()
        obj1 = {"first": "object"}
        obj2 = {"second": "object"}
        obj3 = [1, 2, 3]

        id1 = store.put(obj1)
        id2 = store.put(obj2)
        id3 = store.put(obj3)

        assert id1 == "obj_001"
        assert id2 == "obj_002"
        assert id3 == "obj_003"
        assert store._counter == 3
        assert len(store._objects) == 3

    def test_get_existing_object(self) -> None:
        """Test retrieving an existing object."""
        store = ObjectStore()
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        retrieved = store.get(obj_id)

        assert retrieved == test_obj

    def test_get_nonexistent_object(self) -> None:
        """Test retrieving a non-existent object."""
        store = ObjectStore()

        result = store.get("obj_999")

        assert result is None

    def test_get_with_zero_ttl(self) -> None:
        """Test that objects don't expire with zero TTL."""
        store = ObjectStore(ttl=0)
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        # Even after time passes, object should still exist
        with patch("time.time", return_value=time.time() + 10000):
            retrieved = store.get(obj_id)
            assert retrieved == test_obj

    def test_delete_existing_object(self) -> None:
        """Test deleting an existing object."""
        store = ObjectStore()
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        result = store.delete(obj_id)

        assert result is True
        assert store.get(obj_id) is None
        assert obj_id not in store._objects

    def test_delete_nonexistent_object(self) -> None:
        """Test deleting a non-existent object."""
        store = ObjectStore()

        result = store.delete("obj_999")

        assert result is False

    def test_ttl_expiration(self) -> None:
        """Test that objects expire after TTL."""
        store = ObjectStore(ttl=1.0)  # 1 second TTL
        test_obj = {"test": "data"}
        obj_id = store.put(test_obj)

        # Object should exist immediately
        assert store.get(obj_id) == test_obj

        # Mock time to be after TTL expiration
        with patch("time.time", return_value=time.time() + 2.0):
            result = store.get(obj_id)
            assert result is None
            assert obj_id not in store._objects

    def test_evict_expired_on_put(self) -> None:
        """Test that expired objects are evicted on put."""
        store = ObjectStore(ttl=1.0)
        old_obj = {"old": "data"}
        new_obj = {"new": "data"}

        # Put old object
        old_id = store.put(old_obj)

        # Mock time to be after TTL expiration and put new object
        with patch("time.time", return_value=time.time() + 2.0):
            new_id = store.put(new_obj)

            # Old object should be evicted
            assert store.get(old_id) is None
            assert old_id not in store._objects
            # New object should exist
            assert store.get(new_id) == new_obj

    def test_evict_expired_on_delete(self) -> None:
        """Test that expired objects are evicted on delete."""
        store = ObjectStore(ttl=1.0)
        old_obj = {"old": "data"}
        target_obj = {"target": "data"}

        # Put old object
        with patch("time.time", return_value=1000.0):
            old_id = store.put(old_obj)

        # Put target object slightly later
        with patch("time.time", return_value=1000.5):
            target_id = store.put(target_obj)

        # Mock time to be after old object's TTL but before target's TTL
        with patch("time.time", return_value=1001.2):
            result = store.delete(target_id)

            # Target deletion should succeed
            assert result is True
            # Old object should be expired and gone
            assert store.get(old_id) is None
            assert old_id not in store._objects
            # Target object should be deleted
            assert store.get(target_id) is None
            assert target_id not in store._objects

    def test_partial_expiration(self) -> None:
        """Test that only expired objects are evicted."""
        store = ObjectStore(ttl=2.0)

        # Put first object
        obj1 = {"first": "object"}
        id1 = store.put(obj1)

        # Wait 1 second and put second object
        with patch("time.time", return_value=time.time() + 1.0):
            obj2 = {"second": "object"}
            id2 = store.put(obj2)

        # Wait another 1.5 seconds (total 2.5) - only first object should expire
        with patch("time.time", return_value=time.time() + 2.5):
            # Trigger eviction
            obj3 = {"third": "object"}
            id3 = store.put(obj3)

            # First object should be expired
            assert store.get(id1) is None
            # Second and third objects should exist
            assert store.get(id2) == obj2
            assert store.get(id3) == obj3

    def test_now_method(self) -> None:
        """Test the _now method."""
        store = ObjectStore()

        # Mock time.time to return a specific value
        mock_time = 1234567890.0
        with patch("time.time", return_value=mock_time):
            assert store._now() == mock_time

    def test_object_id_format(self) -> None:
        """Test that object IDs are formatted correctly."""
        store = ObjectStore()

        # Test first 10 objects to check zero-padding
        expected_ids = [f"obj_{i:03d}" for i in range(1, 11)]
        actual_ids = []

        for i in range(10):
            obj_id = store.put(f"object_{i}")
            actual_ids.append(obj_id)

        assert actual_ids == expected_ids

    def test_object_id_large_numbers(self) -> None:
        """Test object ID format with large numbers."""
        store = ObjectStore()
        store._counter = 999  # Start at 999

        obj_id = store.put("test")
        assert obj_id == "obj_1000"  # Should handle numbers > 999
