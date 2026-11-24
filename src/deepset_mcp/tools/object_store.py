# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import Any

from deepset_mcp.tokonomics import RichExplorer


def create_get_from_object_store(explorer: RichExplorer) -> Callable[..., Any]:
    """Creates the `get_from_object_store` tool."""

    def get_from_object_store(object_id: str, path: str = "") -> str:
        """Use this tool to fetch an object from the object store.

        You can fetch a specific object by using the object's id (e.g. `@obj_001`).
        You can also fetch any nested path by using the path-parameter
            (e.g. `{"object_id": "@obj_001", "path": "user_info.given_name"}`
            -> returns the content at obj.user_info.given_name).

        :param object_id: The id of the object to fetch in the format `@obj_001`.
        :param path: The path of the object to fetch in the format of `access.to.attr` or `["access"]["to"]["attr"]`.
        :return: String representation of the object or of the value at `path`.
        """
        return explorer.explore(obj_id=object_id, path=path)

    return get_from_object_store


def create_get_slice_from_object_store(explorer: RichExplorer) -> Callable[..., Any]:
    """Creates the `get_slice_from_object_store` tool."""

    def get_slice_from_object_store(
        object_id: str,
        start: int = 0,
        end: int | None = None,
        path: str = "",
    ) -> str:
        """Extract a slice from a string or list object that is stored in the object store.

        :param object_id: Identifier of the object.
        :param start: Start index for slicing.
        :param end: End index for slicing (optional - leave empty to get slice from start to end of sequence).
        :param path: Navigation path to object to slice (optional).
        :return: String representation of the slice.
        """
        return explorer.slice(obj_id=object_id, start=start, end=end, path=path)

    return get_slice_from_object_store


def create_grep_object_store(explorer: RichExplorer) -> Callable[..., Any]:
    """Creates the `grep_object_store` tool."""

    def grep_object_store(
        object_id: str,
        pattern: str,
        path: str = "",
        case_sensitive: bool = False,
    ) -> str:
        """Search for a regex pattern in a string stored in the object store.

        Returns matches with surrounding context, similar to grep.

        :param object_id: The id of the object to search in the format `@obj_001`.
        :param pattern: Regular expression pattern to search for.
        :param path: Navigation path to a nested string attribute (optional).
        :param case_sensitive: Whether the search should be case sensitive (default: False).
        :return: Matches with context, or a message if no matches found.
        """
        return explorer.search(obj_id=object_id, pattern=pattern, path=path, case_sensitive=case_sensitive)

    return grep_object_store


def create_sed_object_store(explorer: RichExplorer) -> Callable[..., Any]:
    """Creates the `sed_object_store` tool."""

    def sed_object_store(
        object_id: str,
        pattern: str,
        replacement: str,
        path: str = "",
        count: int = 0,
        case_sensitive: bool = False,
    ) -> str:
        r"""Find and replace text in a string stored in the object store using regex.

        Applies substitution (like `sed s/pattern/replacement/`) and stores the result
        as a new object, returning its ID. The original object is not modified.

        :param object_id: The id of the object to modify in the format `@obj_001`.
        :param pattern: Regular expression pattern to find.
        :param replacement: Replacement string. Supports backreferences like `\1`, `\2`.
        :param path: Navigation path to a nested string attribute (optional).
        :param count: Maximum number of replacements (0 = replace all, default: 0).
        :param case_sensitive: Whether the pattern match should be case sensitive (default: False).
        :return: New object ID with the modified string and a preview of the result.
        """
        return explorer.replace(
            obj_id=object_id,
            pattern=pattern,
            replacement=replacement,
            path=path,
            count=count,
            case_sensitive=case_sensitive,
        )

    return sed_object_store


def create_yq_object_store(explorer: RichExplorer) -> Callable[..., Any]:
    """Creates the `yq_object_store` tool."""

    def yq_object_store(object_id: str, filter: str, path: str = "", store: bool = True) -> str:
        """Query or transform structured data stored in the object store using a jq filter expression.

        Use this to filter, map, select, or rewrite nested data without pulling the whole object into
        context, e.g. `{"object_id": "@obj_001", "filter": ".items[] | select(.active) | .name"}`.
        Transforming filters work the same way, e.g. `.config.timeout = 30`.

        If the targeted value is a JSON or YAML string (e.g. a pipeline's YAML config), it is parsed before
        the filter runs so you can navigate into its fields; a transformed result is re-serialized back to
        that same format.

        By default, the result is stored as a new object and returned with a preview, so you can reference
        it further (e.g. `get_from_object_store`) or feed it back into another `yq_object_store` call. Set
        `store=False` if you just want the full result inline and don't need it stored, e.g. for a small
        lookup you'll act on immediately.

        :param object_id: The id of the object to query in the format `@obj_001`.
        :param filter: jq filter expression to apply, e.g. `.field`, `.items[]`, `.[] | select(.status=="done")`,
            or a transformation like `.field = "value"`.
        :param path: Navigation path to a nested attribute to query instead of the whole object (optional).
        :param store: Whether to store the result as a new object (default: True). Set to False to get the
            full result inline instead of a preview, without writing anything to the object store.
        :return: New object ID and a preview of the result, the full result if `store` is False, or a message
            if the filter is invalid or produced no results.
        """
        return explorer.query(obj_id=object_id, filter=filter, path=path, store=store)

    return yq_object_store
