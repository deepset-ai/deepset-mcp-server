# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for search history API."""

from typing import TYPE_CHECKING
from urllib.parse import quote

from deepset_mcp.api.search_history.models import SearchHistoryEntry
from deepset_mcp.api.search_history.protocols import SearchHistoryResourceProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


class SearchHistoryResource(SearchHistoryResourceProtocol):
    """Manages interactions with the deepset search history API."""

    def __init__(self, client: "AsyncClientProtocol", workspace: str) -> None:
        """Initialize the search history resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    def _base_path(self) -> str:
        return f"v1/workspaces/{quote(self._workspace, safe='')}/search_history"

    def _pipeline_path(self, pipeline_name: str) -> str:
        return (
            f"v1/workspaces/{quote(self._workspace, safe='')}/pipelines/{quote(pipeline_name, safe='')}/search_history"
        )

    async def list(self, limit: int = 10, after: str | None = None) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries in the workspace.

        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {"limit": limit}
        if after is not None:
            params["after"] = after

        resp = await self._client.request(
            endpoint=self._base_path(),
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        if resp.json is None:
            return PaginatedResponse(
                data=[],
                has_more=False,
                total=0,
                next_cursor=None,
            )

        # API may return paginated shape: { "data": [...], "has_more": bool, "total": int }
        data = resp.json if isinstance(resp.json, dict) else {"data": resp.json}
        items = data.get("data", [])
        if not isinstance(items, list):
            items = []

        return PaginatedResponse[SearchHistoryEntry].create_with_cursor_field(
            {
                "data": items,
                "has_more": data.get("has_more", False),
                "total": data.get("total"),
            },
            "created_at",
        )

    async def list_pipeline(
        self, pipeline_name: str, limit: int = 10, after: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries for a specific pipeline with pagination.

        Uses the pipeline search history archive endpoint (full history, most recent first).

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {"limit": limit}
        if after is not None:
            params["after"] = after

        resp = await self._client.request(
            endpoint=f"{self._pipeline_path(pipeline_name)}_archive",
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        if resp.json is None:
            return PaginatedResponse(
                data=[],
                has_more=False,
                total=0,
                next_cursor=None,
            )

        data = resp.json if isinstance(resp.json, dict) else {"data": resp.json}
        items = data.get("data", [])
        if not isinstance(items, list):
            items = []

        return PaginatedResponse[SearchHistoryEntry].create_with_cursor_field(
            {
                "data": items,
                "has_more": data.get("has_more", False),
                "total": data.get("total"),
            },
            "created_at",
        )
