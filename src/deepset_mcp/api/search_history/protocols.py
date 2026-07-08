# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocols for search history resources."""

import builtins
from typing import Any, Literal, Protocol

from deepset_mcp.api.search_history.models import (
    HaystackTraceLog,
    PipelineTraceEntry,
    PipelineTraceSummary,
    SearchHistoryEntry,
)
from deepset_mcp.api.shared_models import PaginatedResponse


class SearchHistoryResourceProtocol(Protocol):
    """Protocol defining the interface for search history resources."""

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
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of search history entries.
        """
        ...

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

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
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
    ) -> PaginatedResponse[PipelineTraceSummary]:
        """List Haystack pipeline run trace summaries with pagination, filtering, and sorting.

        Summaries exclude spans and logs; use ``get_pipeline_trace`` for the full trace.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of trace entries to return per page.
        :param after: Cursor to fetch the next page of results.
        :param query_filter: OData filter expression to narrow results.
        :param sort_field: Field to sort by.
        :param sort_order: Sort direction (ASC or DESC).
        :returns: Paginated response of pipeline trace summaries.
        """
        ...

    async def get_pipeline_trace(
        self,
        pipeline_name: str,
        query_id: str,
    ) -> PipelineTraceEntry | None:
        """Get the full Haystack pipeline run trace for a single search history record.

        Includes every span with full tags (component input/output) and the run logs.

        :param pipeline_name: Name of the pipeline.
        :param query_id: UUID of the search history query.
        :returns: The full trace entry, or None if not found.
        """
        ...

    async def get_pipeline_trace_span_tags(
        self,
        pipeline_name: str,
        query_id: str,
        span_id: str,
    ) -> dict[str, Any] | None:
        """Get all tags (including input/output) for a single span in a trace.

        :param pipeline_name: Name of the pipeline.
        :param query_id: UUID of the search history query.
        :param span_id: UUID of the span within the trace.
        :returns: The span's tag dictionary, or None if not found.
        """
        ...

    async def get_pipeline_trace_logs(
        self,
        pipeline_name: str,
        query_id: str,
    ) -> builtins.list[HaystackTraceLog]:
        """Get all log entries for a Haystack pipeline run trace.

        :param pipeline_name: Name of the pipeline.
        :param query_id: UUID of the search history query.
        :returns: List of log entries (empty if the trace has none).
        """
        ...
