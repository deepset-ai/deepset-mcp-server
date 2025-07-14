# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.tools.tokonomics.object_store import Explorable


class TestExplorable:
    """Test Explorable wrapper class."""

    def test_init(self) -> None:
        """Test Explorable initialization."""
        obj_id = "obj_001"
        value = {"test": "data"}
        preview = "Preview text"

        explorable = Explorable(obj_id, value, preview)

        assert explorable.obj_id == obj_id
        assert explorable.value == value
        assert explorable._preview == preview

    def test_str_representation(self) -> None:
        """Test string representation returns preview."""
        obj_id = "obj_001"
        value = {"test": "data"}
        preview = "This is the preview text"

        explorable = Explorable(obj_id, value, preview)

        assert str(explorable) == preview

    def test_repr_representation(self) -> None:
        """Test repr representation returns preview."""
        obj_id = "obj_001"
        value = {"test": "data"}
        preview = "This is the preview text"

        explorable = Explorable(obj_id, value, preview)

        assert repr(explorable) == preview

    def test_str_and_repr_are_same(self) -> None:
        """Test that str and repr return the same value."""
        obj_id = "obj_001"
        value = [1, 2, 3, 4, 5]
        preview = "List with 5 items"

        explorable = Explorable(obj_id, value, preview)

        assert str(explorable) == repr(explorable)

    def test_ipython_display(self) -> None:
        """Test Jupyter notebook display support."""
        obj_id = "obj_001"
        value = {"jupyter": "friendly"}
        preview = "Jupyter display text"

        explorable = Explorable(obj_id, value, preview)

        # _ipython_display_ should point to __str__ method
        assert explorable._ipython_display_ == explorable.__str__
        assert explorable._ipython_display_() == preview

    def test_value_preservation(self) -> None:
        """Test that original value is preserved unchanged."""
        original_dict = {"key": "value", "nested": {"data": [1, 2, 3]}}
        obj_id = "obj_001"
        preview = "Dict preview"

        explorable = Explorable(obj_id, original_dict, preview)

        # Value should be exactly the same object
        assert explorable.value is original_dict
        assert explorable.value == original_dict

        # Modifying the original should affect the stored value
        original_dict["new_key"] = "new_value"
        assert explorable.value["new_key"] == "new_value"

    def test_different_value_types(self) -> None:
        """Test Explorable with different value types."""
        test_cases = [
            ("obj_001", "string value", "String preview"),
            ("obj_002", 42, "Number preview"),
            ("obj_003", [1, 2, 3], "List preview"),
            ("obj_004", {"key": "value"}, "Dict preview"),
            ("obj_005", None, "None preview"),
            ("obj_006", True, "Boolean preview"),
        ]

        for obj_id, value, preview in test_cases:
            explorable = Explorable(obj_id, value, preview)
            assert explorable.obj_id == obj_id
            assert explorable.value == value
            assert str(explorable) == preview

    def test_empty_preview(self) -> None:
        """Test Explorable with empty preview."""
        obj_id = "obj_001"
        value = {"test": "data"}
        preview = ""

        explorable = Explorable(obj_id, value, preview)

        assert str(explorable) == ""
        assert repr(explorable) == ""

    def test_multiline_preview(self) -> None:
        """Test Explorable with multiline preview."""
        obj_id = "obj_001"
        value = {"complex": "object"}
        preview = "Line 1\nLine 2\nLine 3"

        explorable = Explorable(obj_id, value, preview)

        assert str(explorable) == preview
        assert "\n" in str(explorable)

    def test_unicode_preview(self) -> None:
        """Test Explorable with unicode characters in preview."""
        obj_id = "obj_001"
        value = {"unicode": "test"}
        preview = "Unicode: 🚀 ñoño café résumé"

        explorable = Explorable(obj_id, value, preview)

        assert str(explorable) == preview
        assert "🚀" in str(explorable)

    def test_slots_attribute(self) -> None:
        """Test that __slots__ is properly defined."""
        assert hasattr(Explorable, "__slots__")
        assert Explorable.__slots__ == ("obj_id", "value", "_preview")

    def test_no_dict_attribute(self) -> None:
        """Test that instances don't have __dict__ due to __slots__."""
        explorable = Explorable("obj_001", {"test": "data"}, "preview")

        with pytest.raises(AttributeError):
            _ = explorable.__dict__

    def test_only_defined_attributes_allowed(self) -> None:
        """Test that only slotted attributes can be set."""
        explorable = Explorable("obj_001", {"test": "data"}, "preview")

        # These should work (defined in __slots__)
        explorable.obj_id = "new_id"
        explorable.value = "new_value"
        explorable._preview = "new_preview"

        # This should fail (not in __slots__)
        with pytest.raises(AttributeError):
            explorable.new_attribute = "value"

    def test_generic_type_hint_preservation(self) -> None:
        """Test that generic type information is preserved."""
        # This is more of a static type checking test
        # but we can verify the class works with different types

        string_explorable: Explorable[str] = Explorable("obj_001", "test", "preview")
        dict_explorable: Explorable[dict[str, str]] = Explorable("obj_002", {"key": "value"}, "preview")
        list_explorable: Explorable[list[int]] = Explorable("obj_003", [1, 2, 3], "preview")

        assert isinstance(string_explorable.value, str)
        assert isinstance(dict_explorable.value, dict)
        assert isinstance(list_explorable.value, list)
