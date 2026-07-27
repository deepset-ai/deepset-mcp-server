# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json

import pytest
import yaml
from glom import Path

from deepset_mcp.tokonomics import InMemoryBackend, ObjectStore, RichExplorer


class TestRichExplorer:
    """Test RichExplorer class."""

    @pytest.fixture
    def store(self) -> ObjectStore:
        """Create an ObjectStore for testing."""
        return ObjectStore(backend=InMemoryBackend(), ttl=0)  # No expiry for tests

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

        assert "List slice [2:6]" in result
        assert "showing 4 of 10 items" in result

    def test_slice_tuple(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test slicing a tuple object."""
        test_tuple = (1, 2, 3, 4, 5)
        obj_id = store.put(test_tuple)

        result = explorer.slice(obj_id, 1, 4)

        assert "List slice [1:4]" in result

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

    def test_replace_basic(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test basic regex replacement creates a new object."""
        obj_id = store.put("The quick brown fox")

        result = explorer.replace(obj_id, "fox", "cat")

        assert "Replaced 1 occurrence(s)" in result
        assert "Result stored as @" in result
        assert "cat" in result

    def test_replace_stores_new_object(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that replace stores the result and the original is unchanged."""
        original = "hello world"
        obj_id = store.put(original)

        result = explorer.replace(obj_id, "world", "there")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "hello there"
        assert store.get(obj_id) == original

    def test_replace_all_occurrences(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that count=0 replaces all occurrences."""
        obj_id = store.put("cat cat cat")

        result = explorer.replace(obj_id, "cat", "dog")

        assert "Replaced 3 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "dog dog dog"

    def test_replace_limited_count(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that count limits the number of replacements."""
        obj_id = store.put("cat cat cat")

        result = explorer.replace(obj_id, "cat", "dog", count=2)

        assert "Replaced 2 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "dog dog cat"

    def test_replace_no_match(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test replace with no matches returns unchanged message."""
        obj_id = store.put("hello world")

        result = explorer.replace(obj_id, "xyz", "abc")

        assert "No matches found" in result
        assert "Object unchanged" in result

    def test_replace_case_insensitive(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test case-insensitive replacement."""
        obj_id = store.put("The Quick Brown FOX")

        result = explorer.replace(obj_id, "fox", "cat", case_sensitive=False)

        assert "Replaced 1 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "The Quick Brown cat"

    def test_replace_case_sensitive_no_match(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that case-sensitive replacement respects case."""
        obj_id = store.put("The Quick Brown FOX")

        result = explorer.replace(obj_id, "fox", "cat", case_sensitive=True)

        assert "No matches found" in result

    def test_replace_with_backreference(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test replacement with regex backreferences."""
        obj_id = store.put("2024-01-15")

        result = explorer.replace(obj_id, r"(\d{4})-(\d{2})-(\d{2})", r"\3/\2/\1", case_sensitive=True)

        assert "Replaced 1 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "15/01/2024"

    def test_replace_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test replacement navigates to nested string via path."""
        obj_id = store.put({"content": "hello world"})

        result = explorer.replace(obj_id, "world", "there", path="content")

        assert "Replaced 1 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "hello there"

    def test_replace_on_non_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test replace on non-string object returns error."""
        obj_id = store.put({"key": "value"})

        result = explorer.replace(obj_id, "key", "new")

        assert "Replace is only supported on string objects" in result
        assert "Found dict" in result

    def test_replace_invalid_regex(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test replace with invalid regex pattern."""
        obj_id = store.put("test string")

        result = explorer.replace(obj_id, "[invalid", "x")

        assert "Invalid regex pattern" in result

    def test_query_single_result(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a jq filter that produces a single scalar result."""
        obj_id = store.put({"name": "Alice", "age": 30})

        result = explorer.query(obj_id, ".name")

        assert "matched 1 value(s)" in result
        assert "Result stored as @" in result
        assert "Alice" in result

    def test_query_stores_scalar_result(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a scalar query result is stored as a new object."""
        obj_id = store.put({"name": "Alice", "age": 30})

        result = explorer.query(obj_id, ".name")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "Alice"
        # Original object is unchanged
        assert store.get(obj_id) == {"name": "Alice", "age": 30}

    def test_query_multiple_results(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a jq filter that produces a stream of results."""
        obj_id = store.put({"items": [{"name": "a", "active": True}, {"name": "b", "active": False}]})

        result = explorer.query(obj_id, ".items[] | select(.active) | .name")

        assert "matched 1 value(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "a"

    def test_query_returns_multiple_matches(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a jq filter that matches multiple items, stored as a list."""
        obj_id = store.put({"items": [{"name": "a"}, {"name": "b"}]})

        result = explorer.query(obj_id, ".items[].name")

        assert "matched 2 value(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == ["a", "b"]

    def test_query_no_results(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a jq filter that produces no results."""
        obj_id = store.put({"items": []})

        result = explorer.query(obj_id, ".items[]")

        assert "No results for filter" in result

    def test_query_invalid_filter(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test an invalid jq filter returns an error message."""
        obj_id = store.put({"a": 1})

        result = explorer.query(obj_id, ".[invalid")

        assert "Invalid jq filter" in result

    def test_query_runtime_error(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test a jq filter that fails at evaluation time returns an error message."""
        obj_id = store.put([1, 2, 3])

        result = explorer.query(obj_id, ".foo")

        assert "Error evaluating filter" in result

    def test_query_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that query navigates to a nested object via path before applying the filter."""
        obj_id = store.put({"data": {"items": [{"name": "a"}, {"name": "b"}]}})

        result = explorer.query(obj_id, ".items[].name", path="data")

        assert "matched 2 value(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == ["a", "b"]

    def test_query_transforms_structured_object(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a jq write-filter transforms the whole document, not just a leaf value."""
        obj_id = store.put({"config": {"timeout": 10}})

        result = explorer.query(obj_id, ".config.timeout = 30")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == {"config": {"timeout": 30}}
        # Original object is unchanged
        assert store.get(obj_id) == {"config": {"timeout": 10}}

    def test_query_parses_yaml_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a YAML-string object is parsed before the filter is applied."""
        obj_id = store.put("config:\n  timeout: 10\n  retries: 3\n")

        result = explorer.query(obj_id, ".config.timeout")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == 10

    def test_query_transform_reserializes_to_yaml(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a transform on a YAML-string object is stored back as a YAML string."""
        obj_id = store.put("config:\n  timeout: 10\n")

        result = explorer.query(obj_id, ".config.timeout = 30")

        new_id = result.split("@")[1].split(".")[0].strip()
        new_value = store.get(new_id)
        assert isinstance(new_value, str)
        assert yaml.safe_load(new_value) == {"config": {"timeout": 30}}

    def test_query_plain_string_not_treated_as_yaml(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a plain (non-structured) string is queried as an opaque string, not parsed."""
        obj_id = store.put("The quick brown fox")

        result = explorer.query(obj_id, ".")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "The quick brown fox"

    def test_query_invalid_yaml_string_used_as_is(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a string which fails to parse as YAML is queried as an opaque string."""
        obj_id = store.put("not: valid: yaml: at: all:")

        result = explorer.query(obj_id, ".")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "not: valid: yaml: at: all:"

    def test_query_parses_json_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a JSON-string object is parsed before the filter is applied."""
        obj_id = store.put('{"config": {"timeout": 10, "retries": 3}}')

        result = explorer.query(obj_id, ".config.timeout")

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == 10

    def test_query_transform_reserializes_to_json(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that a transform on a JSON-string object is stored back as a JSON string, not YAML."""
        obj_id = store.put('{"config": {"timeout": 10}}')

        result = explorer.query(obj_id, ".config.timeout = 30")

        new_id = result.split("@")[1].split(".")[0].strip()
        new_value = store.get(new_id)
        assert isinstance(new_value, str)
        assert json.loads(new_value) == {"config": {"timeout": 30}}
        # Round-trips as JSON syntax, not YAML block style
        assert new_value.strip().startswith("{")

    def test_query_no_store_does_not_write_to_store(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that store=False does not create a new object."""
        obj_id = store.put({"name": "Alice"})

        result = explorer.query(obj_id, ".name", store=False)

        assert "matched 1 value(s)" in result
        assert "Result stored as @" not in result
        assert "@" not in result

    def test_query_no_store_returns_full_string(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that store=False returns the full string result, not a truncated preview."""
        long_string = "x" * (explorer.max_string_length + 50)
        obj_id = store.put({"text": long_string})

        result = explorer.query(obj_id, ".text", store=False)

        assert long_string in result
        assert "truncated" not in result
        assert "Preview" not in result

    def test_query_no_store_returns_structured_result(self, store: ObjectStore, explorer: RichExplorer) -> None:
        """Test that store=False still renders structured (non-string) results."""
        obj_id = store.put({"items": [{"name": "a"}, {"name": "b"}]})

        result = explorer.query(obj_id, ".items[].name", store=False)

        assert "matched 2 value(s)" in result
        assert "'a'" in result
        assert "'b'" in result
