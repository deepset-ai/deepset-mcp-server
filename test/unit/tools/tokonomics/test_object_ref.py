# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from deepset_mcp.tools.tokonomics.object_store import ObjectRef


class TestObjectRef:
    """Test ObjectRef class."""

    def test_init_with_id_only(self) -> None:
        """Test ObjectRef initialization with just object ID."""
        ref = ObjectRef("obj_001")
        assert ref.obj_id == "obj_001"
        assert ref.path == ""

    def test_init_with_id_and_path(self) -> None:
        """Test ObjectRef initialization with object ID and path."""
        ref = ObjectRef("obj_001", "users.0.name")
        assert ref.obj_id == "obj_001"
        assert ref.path == "users.0.name"

    def test_parse_simple_reference(self) -> None:
        """Test parsing a simple object reference."""
        ref = ObjectRef.parse("@obj_001")

        assert ref is not None
        assert ref.obj_id == "obj_001"
        assert ref.path == ""

    def test_parse_reference_with_dot_path(self) -> None:
        """Test parsing reference with dot notation path."""
        ref = ObjectRef.parse("@obj_042.settings.theme")

        assert ref is not None
        assert ref.obj_id == "obj_042"
        assert ref.path == "settings.theme"

    def test_parse_reference_with_bracket_path(self) -> None:
        """Test parsing reference with bracket notation path."""
        ref = ObjectRef.parse("@obj_123['settings']['theme']")

        assert ref is not None
        assert ref.obj_id == "obj_123"
        assert ref.path == "['settings']['theme']"

    def test_parse_reference_with_mixed_path(self) -> None:
        """Test parsing reference with mixed dot and bracket notation."""
        ref = ObjectRef.parse("@obj_456.users[0].name")

        assert ref is not None
        assert ref.obj_id == "obj_456"
        assert ref.path == "users[0].name"

    def test_parse_reference_with_numeric_id(self) -> None:
        """Test parsing reference with numeric characters in ID."""
        ref = ObjectRef.parse("@obj_999")

        assert ref is not None
        assert ref.obj_id == "obj_999"
        assert ref.path == ""

    def test_parse_reference_with_underscore_id(self) -> None:
        """Test parsing reference with underscore in ID."""
        ref = ObjectRef.parse("@test_obj_123")

        assert ref is not None
        assert ref.obj_id == "test_obj_123"
        assert ref.path == ""

    def test_parse_invalid_reference_no_at(self) -> None:
        """Test parsing invalid reference without @ symbol."""
        ref = ObjectRef.parse("obj_001")

        assert ref is None

    def test_parse_invalid_reference_empty_string(self) -> None:
        """Test parsing empty string."""
        ref = ObjectRef.parse("")

        assert ref is None

    def test_parse_invalid_reference_just_at(self) -> None:
        """Test parsing reference with just @ symbol."""
        ref = ObjectRef.parse("@")

        assert ref is None

    def test_parse_invalid_reference_special_chars_in_id(self) -> None:
        """Test parsing reference with invalid characters in ID."""
        ref = ObjectRef.parse("@obj-001")  # Dash not allowed in \w+, stops at 'obj'

        assert ref is not None
        assert ref.obj_id == "obj"
        assert ref.path == "-001"

    def test_parse_non_string_input(self) -> None:
        """Test parsing non-string input."""
        assert ObjectRef.parse(123) is None
        assert ObjectRef.parse(None) is None
        assert ObjectRef.parse([]) is None
        assert ObjectRef.parse({}) is None

    def test_parse_reference_with_leading_dot_path(self) -> None:
        """Test parsing reference where path starts with dot (should be stripped)."""
        ref = ObjectRef.parse("@obj_001.path.to.value")

        assert ref is not None
        assert ref.obj_id == "obj_001"
        assert ref.path == "path.to.value"

    def test_parse_reference_complex_path(self) -> None:
        """Test parsing reference with complex path."""
        ref = ObjectRef.parse("@data_123.results[0].metadata.tags[1].name")

        assert ref is not None
        assert ref.obj_id == "data_123"
        assert ref.path == "results[0].metadata.tags[1].name"

    def test_parse_reference_with_quotes_in_path(self) -> None:
        """Test parsing reference with quoted keys in path."""
        ref = ObjectRef.parse('@obj_001["key with spaces"]["another key"]')

        assert ref is not None
        assert ref.obj_id == "obj_001"
        assert ref.path == '["key with spaces"]["another key"]'

    def test_parse_reference_alphanumeric_id(self) -> None:
        """Test parsing reference with alphanumeric ID."""
        ref = ObjectRef.parse("@myObject123")

        assert ref is not None
        assert ref.obj_id == "myObject123"
        assert ref.path == ""

    def test_parse_edge_cases(self) -> None:
        """Test parsing edge cases."""
        # Valid minimal reference
        ref = ObjectRef.parse("@a")
        assert ref is not None
        assert ref.obj_id == "a"
        assert ref.path == ""

        # Valid with single character and path
        ref = ObjectRef.parse("@a.b")
        assert ref is not None
        assert ref.obj_id == "a"
        assert ref.path == "b"

        # Path with just numbers
        ref = ObjectRef.parse("@obj_001.123.456")
        assert ref is not None
        assert ref.obj_id == "obj_001"
        assert ref.path == "123.456"

    def test_pattern_attribute(self) -> None:
        """Test that the pattern attribute exists and is compiled."""
        assert hasattr(ObjectRef, "_PATTERN")
        assert ObjectRef._PATTERN.pattern == r"^@(\w+)(.*)$"

        # Test pattern directly
        match = ObjectRef._PATTERN.match("@obj_001.path")
        assert match is not None
        assert match.group(1) == "obj_001"
        assert match.group(2) == ".path"
