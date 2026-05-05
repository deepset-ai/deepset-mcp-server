# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocols for search history resources."""

from typing import Protocol

from deepset_mcp.api.search_history.models import SearchHistoryEntry
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
