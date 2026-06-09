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

    async def _resolve_ids(self, pipeline_name: str) -> tuple[str, str]:
        """Resolve workspace UUID and pipeline UUID needed for v2 endpoints.

        :param pipeline_name: Name of the pipeline to look up.
        :returns: Tuple of (workspace_id, pipeline_id) as strings.
        """
        workspace_obj = await self._client.workspaces().get(self._workspace)
        workspace_id = str(workspace_obj.workspace_id)

        pipeline_obj = await self._client.pipelines(self._workspace).get(pipeline_name, include_yaml=False)
        pipeline_id = pipeline_obj.id

        return workspace_id, pipeline_id

    async def list(
        self,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries in the workspace.

        :param limit: Maximum number of entries to return per page.
        :param after: Cursor (ISO-8601 timestamp of the last item) to fetch the next page.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {
            "limit": limit,
            "field": sort_field,
            "order": sort_order,
        }
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

        data = resp.json if isinstance(resp.json, dict) else {"data": resp.json}
        items = data.get("data", [])
        if not isinstance(items, list):
            items = []

        # The v1 search history API uses `time` as the timestamp field (not `created_at`).
        # The `after` query param accepts an ISO-8601 datetime for legacy cursor-based pagination.
        return PaginatedResponse[SearchHistoryEntry].create_with_cursor_field(
            {
                "data": items,
                "has_more": data.get("has_more", False),
                "total": data.get("total"),
            },
            "time",
        )

    async def list_pipeline(
        self,
        pipeline_name: str,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries for a specific pipeline with pagination.

        Uses the pipeline search history archive endpoint (full history, most recent first).

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of entries to return per page.
        :param after: Cursor (ISO-8601 timestamp of the last item) to fetch the next page.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of search history entries.
        """
        params: dict[str, str | int] = {
            "limit": limit,
            "field": sort_field,
            "order": sort_order,
        }
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
            "time",
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

        Resolves workspace and pipeline UUIDs automatically before calling the v2 endpoint.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of trace entries to return per page.
        :param after: Cursor (ISO-8601 timestamp from next_cursor) to fetch the next page.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of pipeline trace entries.
        """
        workspace_id, pipeline_id = await self._resolve_ids(pipeline_name)

        params: dict[str, str | int] = {
            "limit": limit,
            "field": sort_field,
            "order": sort_order,
        }
        if after is not None:
            params["after"] = after
        if query_filter is not None:
            params["filter"] = query_filter

        traces_endpoint = (
            f"v2/workspaces/{quote(workspace_id, safe='')}"
            f"/pipelines/{quote(pipeline_id, safe='')}/search_history/traces"
        )
        resp = await self._client.request(
            endpoint=traces_endpoint,
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

        # The v2 traces endpoint returns `created_at` as the timestamp field.
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

        Resolves workspace and pipeline UUIDs automatically before calling the v2 endpoint.

        :param pipeline_name: Name of the pipeline.
        :param query_id: UUID of the search history query.
        :returns: The trace entry, or None if not found.
        """
        workspace_id, pipeline_id = await self._resolve_ids(pipeline_name)

        resp = await self._client.request(
            endpoint=(
                f"v2/workspaces/{quote(workspace_id, safe='')}/pipelines/{quote(pipeline_id, safe='')}"
                f"/search_history/{quote(query_id, safe='')}/trace"
            ),
            method="GET",
            timeout=70.0,
        )

        raise_for_status(resp)

        if resp.json is None:
            return None

        return PipelineTraceEntry.model_validate(resp.json)
