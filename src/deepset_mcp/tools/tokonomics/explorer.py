# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Rich Explorer for Object Exploration and Rendering.

Presents Python objects in various Rich formats and supports basic
navigation, searching, and slicing.
"""

from __future__ import annotations

import re
from typing import Any

from glom import GlomError, Path, T, glom
from rich.console import Console
from rich.pretty import Pretty

from .object_store import ObjectRef, ObjectStore


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

    def explore(self, obj_id: str, path: str = "") -> str:
        """Return a string preview of the requested object.

        :param obj_id: Identifier obtained from the store.
        :param path: Navigation path using ``.`` or ``[...]`` notation (e.g. ``@obj_001.path.to.attribute``).
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

        return f"{header}\n\n{body}"

    def search(self, obj_id: str, pattern: str, path: str = "", case_sensitive: bool = False) -> str:
        """Search for a pattern within a string object.

        :param obj_id: Identifier obtained from the store.
        :param pattern: Regular expression pattern to search for.
        :param path: Navigation path to search within (optional).
        :param case_sensitive: Whether search should be case sensitive.
        :return: Search results as formatted string.
        """
        obj = self._get_object_at_path(obj_id, path)

        # Generate header
        header = self._make_header(obj_id, path, obj)

        # Only allow search on strings
        if not isinstance(obj, str):
            return f"{header}\n\nSearch is only supported on string objects. Found {type(obj).__name__} at path."

        # Search the string
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            matches = list(re.finditer(pattern, obj, flags))
        except re.error as e:
            return f"{header}\n\nInvalid regex pattern: {e}"

        if not matches:
            return f"{header}\n\nNo matches found for pattern '{pattern}'"

        # Format results
        result = [f"Found {len(matches)} matches for pattern '{pattern}':", ""]

        # Show limited number of matches
        for i, match in enumerate(matches[: self.max_search_matches]):
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

        if len(matches) > self.max_search_matches:
            result.append(f"\n... and {len(matches) - self.max_search_matches} more matches")

        return f"{header}\n\n" + "\n".join(result)

    def slice(self, obj_id: str, start: int = 0, end: int | None = None, path: str = "") -> str:
        """Extract a slice from a string or list object.

        :param obj_id: Identifier of the object.
        :param start: Start index for slicing.
        :param end: End index for slicing (None for end of sequence).
        :param path: Navigation path to object to slice (optional).
        :return: String representation of the slice.
        """
        obj = self._get_object_at_path(obj_id, path)

        # Generate header
        header = self._make_header(obj_id, path, obj)

        # Handle string slicing
        if isinstance(obj, str):
            sliced: str | list[Any] | tuple[Any] = obj[start:end]
            actual_end = end if end is not None else len(obj)
            body = f"String slice [{start}:{actual_end}] of length {len(sliced)}:\n\n{sliced}"
            return f"{header}\n\n{body}"

        # Handle list/tuple slicing
        elif isinstance(obj, list | tuple):
            sliced = obj[start:end]
            actual_end = end if end is not None else len(obj)

            # Use Pretty to render the sliced list with current settings
            with self.console.capture() as cap:
                self.console.print(
                    Pretty(
                        sliced,
                        max_depth=self.max_depth,
                        max_length=None,  # Show all items in the slice
                        max_string=self.max_string_length,
                        overflow="ellipsis",
                    )
                )

            type_name = type(obj).__name__
            body = (
                f"{type_name.capitalize()} slice [{start}:{actual_end}] "
                f"(showing {len(sliced)} of {len(obj)} items):\n\n"
                f"{cap.get().rstrip()}"
            )
            return f"{header}\n\n{body}"

        else:
            return f"{header}\n\nObject of type {type(obj).__name__} does not support slicing"

    def _get_object_at_path(self, obj_id: str, path: str) -> Any:
        """Get object from store and navigate to path if provided.

        :param obj_id: Identifier obtained from the store.
        :param path: Navigation path (optional).
        :return: Object at path or error string.
        """
        ref = ObjectRef.parse(obj_id)
        # We accept @obj_001 as well as obj_001
        if ref is None:
            resolved_obj_id = obj_id
        else:
            resolved_obj_id = ref.obj_id

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

        location = f"@{obj_id}" + (f".{path}" if path else "")

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
