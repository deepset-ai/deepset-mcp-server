# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Rich Explorer for Object Exploration and Rendering.

Presents Python objects in various Rich formats and supports basic
navigation, searching, and slicing.
"""

from __future__ import annotations

import json
import re
from typing import Any

import jq
import yaml
from glom import GlomError, Path, T, glom
from rich.console import Console
from rich.pretty import Pretty

from deepset_mcp.tokonomics.object_store import ObjectStore


class RichExplorer:
    """Presents Python objects in various Rich formats with navigation support.

    :param store: Object store used for lookups.
    :param max_items: Maximum number of items to show for lists and nested collections (default: 20).
                      Note: All keys are shown for top-level dicts.
    :param max_string_length: Maximum string length before truncation (default: 300).
    :param max_depth: Maximum depth for object representation (default: 3).
    :param max_search_matches: Maximum number of search matches to display (default: 10).
    :param search_context_length: Number of characters to show around search matches (default: 150).
    """

    def __init__(
        self,
        store: ObjectStore,
        max_items: int = 25,
        max_string_length: int = 300,
        max_depth: int = 4,
        max_search_matches: int = 10,
        search_context_length: int = 150,
    ) -> None:
        """Initialize the RichExplorer with storage and configuration options."""
        self.store = store
        self.console = Console(force_terminal=False, width=120)

        # Display limits
        self.max_items = max_items
        self.max_string_length = max_string_length
        self.max_depth = max_depth

        # Search configuration
        self.max_search_matches = max_search_matches
        self.search_context_length = search_context_length

        # Validation pattern for allowed attributes
        self.allowed_attr_regex = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")

    def parse_reference(self, ref_str: str) -> tuple[str, str]:
        """Parse @obj_id.path into (obj_id, path).

        :param ref_str: Reference string like @obj_id.path or obj_id
        :return: Tuple of (obj_id, path)
        """
        if not ref_str.startswith("@"):
            return ref_str, ""  # Not a reference, return as-is

        ref_str = ref_str[1:]  # Remove @
        if "." in ref_str:
            obj_id, path = ref_str.split(".", 1)
            return obj_id, path
        return ref_str, ""

    def explore(self, obj_id: str, path: str = "") -> str:
        """Return a string preview of the requested object.

        :param obj_id: Identifier obtained from the store.
        :param path: Navigation path using ``.`` or ``[...]`` notation (e.g. ``@obj_id.path.to.attribute``).
        :return: String representation of the object.
        """
        obj = self._get_object_at_path(obj_id, path)

        # Generate header and body
        header = self._make_header(obj_id, path, obj)

        # We want the full length str if the (nested) object is a string
        if isinstance(obj, str):
            body = obj
        else:
            body = self._get_pretty_repr(obj)

        return f"{header}\n\n" + body

    def search(self, obj_id: str, pattern: str, path: str = "", case_sensitive: bool = False) -> str:
        """Search for a pattern within a string object.

        :param obj_id: Identifier obtained from the store.
        :param pattern: Regular expression pattern to search for.
        :param path: Navigation path to search within (optional).
        :param case_sensitive: Whether search should be case sensitive.
        :return: Search results as formatted string.
        """
        obj = self._get_object_at_path(obj_id, path)

        # Only allow search on strings
        if not isinstance(obj, str):
            return f"Search is only supported on string objects. Found {type(obj).__name__} at path '{path}'."

        # Search the string
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            matches = list(re.finditer(pattern, obj, flags))
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        if not matches:
            return f"No matches found for pattern '{pattern}'"

        # Format results
        result = [f"Found {len(matches)} matches for pattern '{pattern}':", ""]

        # Show limited number of matches
        for i, match in enumerate(matches):
            start, end = match.span()
            context_start = max(0, start - self.search_context_length)
            context_end = min(len(obj), end + self.search_context_length)
            context = obj[context_start:context_end]

            # Highlight the match
            match_in_context = start - context_start
            highlighted = (
                context[:match_in_context]
                + f"[{context[match_in_context : match_in_context + (end - start)]}]"
                + context[match_in_context + (end - start) :]
            )
            result.append(f"Match {i + 1}: ...{highlighted}...")

        return "\n".join(result)

    def replace(
        self,
        obj_id: str,
        pattern: str,
        replacement: str,
        path: str = "",
        count: int = 0,
        case_sensitive: bool = False,
    ) -> str:
        r"""Replace occurrences of a pattern in a string object, storing the result as a new object.

        :param obj_id: Identifier obtained from the store.
        :param pattern: Regular expression pattern to find.
        :param replacement: Replacement string (supports backreferences like \1, \2).
        :param path: Navigation path to the string to modify (optional).
        :param count: Maximum number of replacements (0 = replace all).
        :param case_sensitive: Whether the pattern match should be case sensitive.
        :return: New object ID and summary of replacements made.
        """
        obj = self._get_object_at_path(obj_id, path)

        if not isinstance(obj, str):
            return f"Replace is only supported on string objects. Found {type(obj).__name__} at path '{path}'."

        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            new_str, num_replacements = re.subn(pattern, replacement, obj, count=count, flags=flags)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        if num_replacements == 0:
            return f"No matches found for pattern '{pattern}'. Object unchanged."

        new_id = self.store.put(new_str)
        preview = new_str[: self.max_string_length]
        truncated = " (truncated)" if len(new_str) > self.max_string_length else ""

        return (
            f"Replaced {num_replacements} occurrence(s) of '{pattern}' → '{replacement}'.\n"
            f"Result stored as @{new_id}.\n\n"
            f"Preview{truncated}:\n{preview}"
        )

    def slice(self, obj_id: str, start: int = 0, end: int | None = None, path: str = "") -> str:
        """Extract a slice from a string or list object.

        :param obj_id: Identifier of the object.
        :param start: Start index for slicing.
        :param end: End index for slicing (None for end of sequence).
        :param path: Navigation path to object to slice (optional).
        :return: String representation of the slice.
        """
        obj = self._get_object_at_path(obj_id, path)

        # Handle string slicing
        if isinstance(obj, str):
            sliced_str: str = obj[start:end]
            actual_end = end if end is not None else len(obj)
            body = f"String slice [{start}:{actual_end}] of length {len(sliced_str)}:\n\n{sliced_str}"
            return body

        # Handle list/tuple slicing
        elif isinstance(obj, list | tuple):
            sliced_list = obj[start:end]
            actual_end = end if end is not None else len(obj)

            # Use Pretty to render the sliced list with current settings
            with self.console.capture() as cap:
                self.console.print(
                    Pretty(
                        sliced_list,
                        max_depth=self.max_depth,
                        max_length=None,  # Show all items in the slice
                        max_string=self.max_string_length,
                        overflow="ellipsis",
                    )
                )

            type_name = type(obj).__name__
            body = (
                f"{type_name.capitalize()} slice [{start}:{actual_end}] "
                f"(showing {len(sliced_list)} of {len(obj)} items):\n\n"
                f"{cap.get().rstrip()}"
            )
            return body

        else:
            return f"Object of type {type(obj).__name__} does not support slicing"

    def query(self, obj_id: str, filter: str, path: str = "", store: bool = True) -> str:
        """Query (or transform) structured data using a jq filter expression.

        If the targeted object is a string containing JSON or YAML, it is parsed before the filter is
        applied, so filters can navigate into its fields (e.g. a pipeline's YAML config). Filters that
        transform the document (e.g. ``.field = "value"``) work the same way as ones that only extract data
        (e.g. ``.field``), since both are plain jq filters. If the input was parsed from JSON or YAML, a
        non-string result is re-serialized back to that same format before being stored.

        :param obj_id: Identifier obtained from the store.
        :param filter: jq filter expression (e.g. ``.items[] | select(.active) | .name`` or ``.field = "value"``).
        :param path: Navigation path to the object to query (optional).
        :param store: Whether to store the result as a new object (default: True). When False, nothing is
            written to the object store and the full result is returned inline instead of a preview.
        :return: New object ID and a preview of the result, the full result if ``store`` is False, or an
            error message.
        """
        obj = self._get_object_at_path(obj_id, path)

        query_input = obj
        source_format: str | None = None
        if isinstance(obj, str):
            try:
                parsed = json.loads(obj)
            except ValueError:
                parsed = None
            if parsed is not None and not isinstance(parsed, str):
                query_input = parsed
                source_format = "json"
            else:
                try:
                    parsed = yaml.safe_load(obj)
                except yaml.YAMLError:
                    parsed = None
                if parsed is not None and not isinstance(parsed, str):
                    query_input = parsed
                    source_format = "yaml"

        try:
            program = jq.compile(filter)
        except ValueError as e:
            return f"Invalid jq filter '{filter}': {e}"

        try:
            results = program.input_value(query_input).all()
        except ValueError as e:
            return f"Error evaluating filter '{filter}': {e}"

        if not results:
            return f"No results for filter '{filter}'."

        result: Any = results[0] if len(results) == 1 else results

        if source_format == "json" and isinstance(result, dict | list):
            result = json.dumps(result, indent=2)
        elif source_format == "yaml" and isinstance(result, dict | list):
            result = yaml.safe_dump(result, sort_keys=False)

        if not store:
            body = result if isinstance(result, str) else self._get_pretty_repr(result)
            return f"Filter '{filter}' matched {len(results)} value(s):\n\n{body}"

        new_id = self.store.put(result)

        if isinstance(result, str):
            truncated = " (truncated)" if len(result) > self.max_string_length else ""
            preview = f"Preview{truncated}:\n{result[: self.max_string_length]}"
        else:
            preview = self._get_pretty_repr(result)

        return f"Filter '{filter}' matched {len(results)} value(s). Result stored as @{new_id}.\n\n{preview}"

    def _get_object_at_path(self, obj_id: str, path: str) -> Any:
        """Get object from store and navigate to path if provided.

        :param obj_id: Identifier obtained from the store.
        :param path: Navigation path (optional).
        :return: Object at path or error string.
        """
        resolved_obj_id, ref_path = self.parse_reference(obj_id)

        # If there's a path from the reference, combine it with the provided path
        if ref_path:
            path = f"{ref_path}.{path}" if path else ref_path

        obj = self.store.get(resolved_obj_id)
        if obj is None:
            raise ValueError(f"Object {obj_id} not found or expired.")

        if path:
            self._validate_path(path)
            try:
                obj = glom(obj, self._parse_path(path))
            except GlomError as e:
                raise ValueError(f"Object '{obj_id}' does not have a value at path '{path}'.") from e

        return obj

    def _validate_path(self, path: str) -> None:
        """Ensure every attribute component matches the allow-list regex.

        :param path: Path string to validate.
        :raises ValueError: If path contains disallowed attributes.
        """
        for part in re.split(r"[.\[\]]+", path):
            if not part or part.isdigit():
                continue
            # Strip quotes for string keys
            part = part.strip("\"'")
            if not self.allowed_attr_regex.match(part):
                raise ValueError(f"Access to attribute '{part}' is not permitted")

    def _parse_path(self, path: str) -> Any:
        """Parse a path string into a glom spec.

        :param path: Path string in dot/bracket notation.
        :return: Glom spec for navigation.
        """
        if not path:
            return T

        parts: list[Any] = []
        current = ""
        in_brackets = False

        for char in path:
            if char == "[":
                if current:
                    parts.append(current)
                    current = ""
                in_brackets = True
            elif char == "]":
                if current:
                    # Try to parse as int for list indices
                    try:
                        parts.append(int(current))
                    except ValueError:
                        # String key for dicts
                        parts.append(current.strip("\"'"))
                    current = ""
                in_brackets = False
            elif char == "." and not in_brackets:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return Path(*parts) if len(parts) > 1 else parts[0]

    def _make_header(self, obj_id: str, path: str, obj: Any) -> str:
        """Create a header showing object info.

        :param obj_id: Object identifier.
        :param path: Navigation path.
        :param obj: The object being displayed.
        :return: Formatted header string.
        """
        type_name = type(obj).__name__
        if hasattr(obj, "__module__") and obj.__module__ not in ("builtins", "__main__"):
            type_name = f"{obj.__module__}.{type_name}"

        location = "@" if not obj_id.startswith("@") else ""
        location += obj_id + (f".{path}" if path else "")

        # Add size info for sized objects
        size_info = ""
        if hasattr(obj, "__len__"):
            try:
                size_info = f" (length: {len(obj)})"
            except Exception:
                pass

        return f"{location} → {type_name}{size_info}"

    def _get_pretty_repr(self, obj: Any) -> str:
        """Get Rich pretty representation of object.

        :param obj: Object to represent.
        :return: String representation using Rich Pretty.
        """
        # Special handling for top-level dicts to show all keys
        if isinstance(obj, dict):
            if not obj:
                return "{}"

            # Pretty print each value separately with max_items applied
            result_parts = ["{"]

            for key, value in obj.items():
                # Pretty print the key
                with self.console.capture() as key_cap:
                    self.console.print(Pretty(key), end="")
                key_str = key_cap.get().rstrip()

                # Pretty print the value with limits applied
                with self.console.capture() as val_cap:
                    self.console.print(
                        Pretty(
                            value,
                            max_depth=self.max_depth - 1,  # Reduce depth since we're already one level in
                            max_length=self.max_items,
                            max_string=self.max_string_length,
                            expand_all=True,
                            overflow="ellipsis",
                        ),
                        end="",
                    )
                val_str = val_cap.get().rstrip()

                # Handle multiline values
                if "\n" in val_str:
                    # Indent continuation lines
                    lines = val_str.split("\n")
                    val_str = lines[0] + "\n" + "\n".join("        " + line for line in lines[1:])

                result_parts.append(f"    {key_str}: {val_str},")

            # Remove trailing comma from last item
            if result_parts[-1].endswith(","):
                result_parts[-1] = result_parts[-1][:-1]

            result_parts.append("}")
            return "\n".join(result_parts)

        # Regular pretty print for non-dict objects
        with self.console.capture() as cap:
            self.console.print(
                Pretty(
                    obj,
                    max_depth=self.max_depth,
                    max_length=self.max_items,
                    max_string=self.max_string_length,
                    expand_all=True,
                    overflow="ellipsis",
                )
            )
        return cap.get().rstrip()
