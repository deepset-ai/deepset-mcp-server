# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for search history API."""

from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
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

    async def list(
        self, limit: int = 10, after: str | None = None, query_filter: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries in the workspace.

        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {"limit": limit}
        if after is not None:
            params["after"] = after
        if query_filter is not None:
            params["filter"] = query_filter

        resp = await self._client.request(
            endpoint=self._base_path(),
            method="GET",
            params=params,
            timeout=70.0,
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

    async def list_pipeline_traces(
        self,
        pipeline_name: str,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[PipelineTraceEntry]:
        """List Haystack pipeline run traces with pagination, filtering, and sorting.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of trace entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of pipeline trace entries.
        """
        params: dict[str, str | int] = {
            "limit": limit,
            "sort_field": sort_field,
            "sort_order": sort_order,
        }
        if after is not None:
            params["after"] = after
        if query_filter is not None:
            params["filter"] = query_filter

        resp = await self._client.request(
            endpoint=f"{self._pipeline_path(pipeline_name)}/traces",
            method="GET",
            params=params,
            timeout=70.0,
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

        return PaginatedResponse[PipelineTraceEntry].create_with_cursor_field(
            {
                "data": items,
                "has_more": data.get("has_more", False),
                "total": data.get("total"),
            },
            "created_at",
        )

    async def get_pipeline_trace(
        self,
        pipeline_name: str,
        query_id: str,
    ) -> PipelineTraceEntry | None:
        """Get the Haystack pipeline run trace for a single search history record.

        :param pipeline_name: Name of the pipeline.
        :param query_id: UUID of the search history query.
        :returns: The trace entry, or None if not found.
        """
        resp = await self._client.request(
            endpoint=f"{self._pipeline_path(pipeline_name)}/search_history/{quote(query_id, safe='')}/trace",
            method="GET",
            timeout=70.0,
        )

        raise_for_status(resp)

        if resp.json is None:
            return None

        return PipelineTraceEntry.model_validate(resp.json)

    async def list_pipeline(
        self, pipeline_name: str, limit: int = 10, after: str | None = None, query_filter: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries for a specific pipeline with pagination.

        Uses the pipeline search history archive endpoint (full history, most recent first).

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {"limit": limit}
        if after is not None:
            params["after"] = after
        if query_filter is not None:
            params["filter"] = query_filter

        resp = await self._client.request(
            endpoint=f"{self._pipeline_path(pipeline_name)}_archive",
            method="GET",
            params=params,
            timeout=70.0,
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
