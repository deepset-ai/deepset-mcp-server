# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.tokonomics import InMemoryBackend, ObjectStore, RichExplorer
from deepset_mcp.tools.object_store import create_grep_object_store, create_sed_object_store


@pytest.fixture
def store() -> ObjectStore:
    return ObjectStore(backend=InMemoryBackend(), ttl=0)


@pytest.fixture
def explorer(store: ObjectStore) -> RichExplorer:
    return RichExplorer(store)


class TestGrepObjectStore:
    def test_returns_matches(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("The quick brown fox jumps over the lazy dog")
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "fox")

        assert "Found 1 matches" in result
        assert "[fox]" in result

    def test_no_matches(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("hello world")
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "xyz")

        assert "No matches found" in result

    def test_case_insensitive_by_default(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("The Quick Brown FOX")
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "fox")

        assert "Found 1 matches" in result

    def test_case_sensitive(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("The Quick Brown FOX")
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "fox", case_sensitive=True)

        assert "No matches found" in result

    def test_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put({"text": "hello world"})
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "world", path="text")

        assert "Found 1 matches" in result

    def test_invalid_regex(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("test string")
        grep = create_grep_object_store(explorer)

        result = grep(f"@{obj_id}", "[invalid")

        assert "Invalid regex pattern" in result


class TestSedObjectStore:
    def test_replaces_and_returns_new_id(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("hello world")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "world", "there")

        assert "Replaced 1 occurrence(s)" in result
        assert "Result stored as @" in result
        assert "hello there" in result

    def test_original_unchanged(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("hello world")
        sed = create_sed_object_store(explorer)

        sed(f"@{obj_id}", "world", "there")

        assert store.get(obj_id) == "hello world"

    def test_replace_all_by_default(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("cat cat cat")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "cat", "dog")

        assert "Replaced 3 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "dog dog dog"

    def test_count_limits_replacements(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("cat cat cat")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "cat", "dog", count=1)

        assert "Replaced 1 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "dog cat cat"

    def test_no_match(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("hello world")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "xyz", "abc")

        assert "No matches found" in result

    def test_with_path(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put({"content": "hello world"})
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "world", "there", path="content")

        assert "Replaced 1 occurrence(s)" in result
        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "hello there"

    def test_case_sensitive(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("Hello WORLD")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", "world", "there", case_sensitive=True)

        assert "No matches found" in result

    def test_backreference_in_replacement(self, store: ObjectStore, explorer: RichExplorer) -> None:
        obj_id = store.put("2024-01-15")
        sed = create_sed_object_store(explorer)

        result = sed(f"@{obj_id}", r"(\d{4})-(\d{2})-(\d{2})", r"\3/\2/\1", case_sensitive=True)

        new_id = result.split("@")[1].split(".")[0].strip()
        assert store.get(new_id) == "15/01/2024"
