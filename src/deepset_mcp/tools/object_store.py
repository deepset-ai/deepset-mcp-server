# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import Any

from deepset_mcp.tools.tokonomics import RichExplorer


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
