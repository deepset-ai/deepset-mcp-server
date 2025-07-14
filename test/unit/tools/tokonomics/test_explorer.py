# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from glom import Path

from deepset_mcp.tools.tokonomics.explorer import RichExplorer
from deepset_mcp.tools.tokonomics.object_store import ObjectStore


class TestRichExplorer:
    """Test RichExplorer class."""

    @pytest.fixture
    def store(self) -> ObjectStore:
        """Create an ObjectStore for testing."""
        return ObjectStore(ttl=0)  # No expiry for tests

    @pytest.fixture
    def explorer(self, store: ObjectStore) -> RichExplorer:
        """Create a RichExplorer for testing."""
        return RichExplorer(store)

    def test_init_default_params(self, store: ObjectStore) -> None:
        """Test RichExplorer initialization with default parameters."""
        explorer = RichExplorer(store)

        assert explorer.store is store
        assert explorer.max_items == 25
        assert explorer.max_string_length == 300
        assert explorer.max_depth == 4
        assert explorer.max_search_matches == 10
        assert explorer.search_context_length == 150
        assert explorer.console.options.is_terminal is False
        assert explorer.console.options.max_width == 120

    def test_init_custom_params(self, store: ObjectStore) -> None:
        """Test RichExplorer initialization with custom parameters."""
        explorer = RichExplorer(
            store,
            max_items=5,
            max_string_length=100,
            max_depth=2,
            max_search_matches=3,
            search_context_length=50,
        )

        assert explorer.max_items == 5
        assert explorer.max_string_length == 100
        assert explorer.max_depth == 2
        assert explorer.max_search_matches == 3
        assert explorer.search_context_length == 50

    def test_explore_nonexistent_object(self, explorer: RichExplorer) -> None:
        """Test exploring a non-existent object."""
        with pytest.raises(ValueError, match="Object obj_999 not found or expired"):
            explorer.explore("obj_999")

    def test_explore_simple_object(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test exploring a simple object."""
        test_data = {"key": "value", "number": 42}
        obj_id = store.put(test_data)

        result = explorer.explore(obj_id)

        assert f"@{obj_id} → dict" in result
        assert "(length: 2)" in result
        assert "key" in result
        assert "value" in result
        assert "number" in result
        assert "42" in result

    def test_explore_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test exploring object with path navigation."""
        test_data = {"users": [{"name": "Alice", "age": 30}]}
        obj_id = store.put(test_data)

        result = explorer.explore(obj_id, "users.0.name")

        assert f"@{obj_id}.users.0.name → str" in result
        assert "Alice" in result

    def test_explore_invalid_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test exploring with invalid path."""
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        with pytest.raises(ValueError, match="does not have a value at path"):
            explorer.explore(obj_id, "nonexistent.path")

    def test_explore_disallowed_attribute(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test exploring with disallowed attribute name."""
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        with pytest.raises(ValueError, match="Access to attribute '__private__' is not permitted"):
            explorer.explore(obj_id, "__private__")

    def test_search_on_string_object(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test searching within a string object."""
        test_string = "The quick brown fox jumps over the lazy dog"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "fox")

        assert f"@{obj_id} → str" in result
        assert "Found 1 matches" in result
        assert "[fox]" in result

    def test_search_case_insensitive(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test case-insensitive search."""
        test_string = "The Quick Brown Fox"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "fox", case_sensitive=False)

        assert "Found 1 matches" in result
        assert "[Fox]" in result

    def test_search_case_sensitive(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test case-sensitive search."""
        test_string = "The Quick Brown Fox"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "fox", case_sensitive=True)

        assert "No matches found" in result

    def test_search_multiple_matches(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test search with multiple matches."""
        test_string = "cat dog cat bird cat"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "cat")

        assert "Found 3 matches" in result
        assert "Match 1:" in result
        assert "Match 2:" in result
        assert "Match 3:" in result

    def test_search_on_non_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test search on non-string object."""
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        result = explorer.search(obj_id, "pattern")

        assert "Search is only supported on string objects" in result
        assert "Found dict" in result

    def test_search_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test search with path navigation."""
        test_data = {"content": "The quick brown fox"}
        obj_id = store.put(test_data)

        result = explorer.search(obj_id, "fox", path="content")

        assert f"@{obj_id}.content → str" in result
        assert "Found 1 matches" in result

    def test_search_invalid_regex(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test search with invalid regex pattern."""
        test_string = "test string"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "[invalid")

        assert "Invalid regex pattern" in result

    def test_slice_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing a string object."""
        test_string = "Hello, World!"
        obj_id = store.put(test_string)

        result = explorer.slice(obj_id, 0, 5)

        assert f"@{obj_id} → str" in result
        assert "String slice [0:5]" in result
        assert "Hello" in result

    def test_slice_string_no_end(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing string without end parameter."""
        test_string = "Hello, World!"
        obj_id = store.put(test_string)

        result = explorer.slice(obj_id, 7)

        assert "String slice [7:13]" in result
        assert "World!" in result

    def test_slice_list(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing a list object."""
        test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        obj_id = store.put(test_list)

        result = explorer.slice(obj_id, 2, 6)

        assert f"@{obj_id} → list" in result
        assert "List slice [2:6]" in result
        assert "showing 4 of 10 items" in result

    def test_slice_tuple(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing a tuple object."""
        test_tuple = (1, 2, 3, 4, 5)
        obj_id = store.put(test_tuple)

        result = explorer.slice(obj_id, 1, 4)

        assert f"@{obj_id} → tuple" in result
        assert "Tuple slice [1:4]" in result

    def test_slice_non_sliceable(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing non-sliceable object."""
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        result = explorer.slice(obj_id, 0, 2)

        assert "does not support slicing" in result

    def test_slice_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing with path navigation."""
        test_data = {"items": [1, 2, 3, 4, 5]}
        obj_id = store.put(test_data)

        result = explorer.slice(obj_id, 1, 3, path="items")

        assert f"@{obj_id}.items → list" in result
        assert "List slice [1:3]" in result

    def test_validate_path_valid_attributes(self, explorer: RichExplorer) -> None:
        """Test path validation with valid attributes."""
        valid_paths = [
            "attr",
            "attr1.attr2",
            "attr.0.name",
            "data.items.0",
            "valid_name",
            "CamelCase",
        ]

        for path in valid_paths:
            # Should not raise an exception
            explorer._validate_path(path)

    def test_validate_path_invalid_attributes(self, explorer: RichExplorer) -> None:
        """Test path validation with invalid attributes."""
        invalid_paths = [
            "__private__",
            "attr.__dict__",
            "123invalid",
            "attr-name",
            "attr@name",
        ]

        for path in invalid_paths:
            with pytest.raises(ValueError, match="Access to attribute .* is not permitted"):
                explorer._validate_path(path)

    def test_validate_path_with_brackets(self, explorer: RichExplorer) -> None:
        """Test path validation with bracket notation."""
        valid_paths = [
            "attr[0]",
            "attr['key']",
            'attr["key"]',
            "attr[123]",
        ]

        for path in valid_paths:
            # Should not raise an exception
            explorer._validate_path(path)

    def test_parse_path_simple(self, explorer: RichExplorer) -> None:
        """Test parsing simple paths."""
        path_spec = explorer._parse_path("attr")
        assert path_spec == "attr"

    def test_parse_path_dot_notation(self, explorer: RichExplorer) -> None:
        """Test parsing dot notation paths."""
        path_spec = explorer._parse_path("attr1.attr2.attr3")
        assert isinstance(path_spec, Path)

    def test_parse_path_bracket_notation(self, explorer: RichExplorer) -> None:
        """Test parsing bracket notation paths."""
        path_spec = explorer._parse_path("attr[0]")
        assert isinstance(path_spec, Path)

    def test_parse_path_mixed_notation(self, explorer: RichExplorer) -> None:
        """Test parsing mixed notation paths."""
        path_spec = explorer._parse_path("attr.items[0].name")
        assert isinstance(path_spec, Path)

    def test_make_header_simple_type(self, explorer: RichExplorer) -> None:
        """Test header creation for simple types."""
        header = explorer._make_header("obj_001", "", "test string")

        assert header == "@obj_001 → str (length: 11)"

    def test_make_header_with_path(self, explorer: RichExplorer) -> None:
        """Test header creation with path."""
        header = explorer._make_header("obj_001", "items.0", [1, 2, 3])

        assert header == "@obj_001.items.0 → list (length: 3)"

    def test_make_header_custom_type(self, explorer: RichExplorer) -> None:
        """Test header creation for custom type."""

        class CustomClass:
            pass

        obj = CustomClass()
        header = explorer._make_header("obj_001", "", obj)

        expected = f"@obj_001 → {__name__}.CustomClass"
        assert header == expected

    def test_make_header_no_length(self, explorer: RichExplorer) -> None:
        """Test header creation for object without __len__."""
        header = explorer._make_header("obj_001", "", 42)

        assert header == "@obj_001 → int"

    def test_get_pretty_repr_empty_dict(self, explorer: RichExplorer) -> None:
        """Test pretty representation of empty dict."""
        result = explorer._get_pretty_repr({})

        assert result == "{}"

    def test_get_pretty_repr_simple_dict(self, explorer: RichExplorer) -> None:
        """Test pretty representation of simple dict."""
        test_dict = {"key": "value", "number": 42}
        result = explorer._get_pretty_repr(test_dict)

        assert "key" in result
        assert "value" in result
        assert "number" in result
        assert "42" in result
        assert result.startswith("{")
        assert result.endswith("}")

    def test_get_pretty_repr_non_dict(self, explorer: RichExplorer) -> None:
        """Test pretty representation of non-dict objects."""
        test_cases = [
            [1, 2, 3],
            "test string",
            42,
            True,
            None,
        ]

        for obj in test_cases:
            result = explorer._get_pretty_repr(obj)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_allowed_attr_regex(self, explorer: RichExplorer) -> None:
        """Test the allowed attribute regex pattern."""
        regex = explorer.allowed_attr_regex

        # Valid patterns
        valid_attrs = ["attr", "attr1", "Attr", "CamelCase", "snake_case", "a", "A1", "valid_name123"]
        for attr in valid_attrs:
            assert regex.match(attr) is not None, f"{attr} should be valid"

        # Invalid patterns
        invalid_attrs = ["1attr", "_attr", "__attr__", "attr-name", "attr@name", "attr.name", ""]
        for attr in invalid_attrs:
            assert regex.match(attr) is None, f"{attr} should be invalid"

    def test_get_object_at_path_success(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test successful object retrieval with path."""
        test_data = {"users": [{"name": "Alice"}]}
        obj_id = store.put(test_data)

        result = explorer._get_object_at_path(obj_id, "users.0.name")

        assert result == "Alice"

    def test_get_object_at_path_nonexistent(self, explorer: RichExplorer) -> None:
        """Test object retrieval for non-existent object."""
        with pytest.raises(ValueError, match="Object obj_999 not found or expired"):
            explorer._get_object_at_path("obj_999", "")

    def test_get_object_at_path_invalid_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test object retrieval with invalid path."""
        test_data = {"key": "value"}
        obj_id = store.put(test_data)

        with pytest.raises(ValueError, match="does not have a value at path"):
            explorer._get_object_at_path(obj_id, "nonexistent")

    def test_search_context_length(self, store: ObjectStore) -> None:
        """Test search context length configuration."""
        explorer = RichExplorer(store, search_context_length=10)
        test_string = "The quick brown fox jumps over the lazy dog"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "fox")

        # Should show limited context around the match
        assert "Found 1 matches" in result
        # Context should be limited
        assert len(result) < len(test_string) + 100  # Rough check

    def test_max_search_matches(self, store: ObjectStore) -> None:
        """Test maximum search matches limit."""
        explorer = RichExplorer(store, max_search_matches=2)
        test_string = "cat dog cat bird cat fish cat"
        obj_id = store.put(test_string)

        result = explorer.search(obj_id, "cat")

        assert "Found 4 matches" in result  # Total found
        assert "Match 1:" in result
        assert "Match 2:" in result
        assert "Match 3:" not in result  # Should be limited
        assert "and 2 more matches" in result

    def test_explore_string_returns_full_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that exploring a string object returns the full string without pretty formatting."""
        test_string = "This is a test string with special characters: \n\t quotes 'single' and double"
        obj_id = store.put(test_string)

        result = explorer.explore(obj_id)

        # Should contain the header
        assert f"@{obj_id} → str" in result
        # Should contain the full original string without quotes or escaping
        assert test_string in result
        # The body should be exactly the string (after the header)
        lines = result.split("\n\n", 1)
        body = lines[1] if len(lines) > 1 else ""
        assert body == test_string

    def test_explore_nested_string_returns_full_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that exploring a nested string object returns the full string without pretty formatting."""
        test_string = "Nested string with newlines\nand tabs\tand quotes 'test'"
        test_data = {"content": test_string}
        obj_id = store.put(test_data)

        result = explorer.explore(obj_id, "content")

        # Should contain the header for the nested path
        assert f"@{obj_id}.content → str" in result
        # Should contain the full original string
        assert test_string in result
        # Should not be wrapped in quotes like Rich Pretty would do
        lines = result.split("\n\n", 1)
        body = lines[1] if len(lines) > 1 else ""
        assert body == test_string
