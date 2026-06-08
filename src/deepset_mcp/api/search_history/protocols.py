# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocols for search history resources."""

from typing import Literal, Protocol

from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
from deepset_mcp.api.shared_models import PaginatedResponse


class SearchHistoryResourceProtocol(Protocol):
    """Protocol defining the interface for search history resources."""

    async def list(
        self, limit: int = 10, after: str | None = None, query_filter: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries in the workspace.

        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :returns: Paginated response of search history entries.
        """
        ...

    async def list_pipeline(
        self, pipeline_name: str, limit: int = 10, after: str | None = None, query_filter: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        """List search history entries for a specific pipeline with pagination.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :returns: Paginated response of search history entries (most recent first).
        """
        ...

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
        :param sort_order: Sort direction.
        :returns: Paginated response of pipeline trace entries.
        """
        ...

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
        ...
