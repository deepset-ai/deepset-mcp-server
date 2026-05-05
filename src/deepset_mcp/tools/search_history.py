# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with search history in a deepset workspace."""

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.search_history.models import SearchHistoryEntry
from deepset_mcp.api.shared_models import PaginatedResponse


async def list_search_history(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    limit: int = 10,
    after: str | None = None,
    query_filter: str | None = None,
) -> PaginatedResponse[SearchHistoryEntry] | str:
    """Retrieves search history for the configured deepset workspace.

    Returns past searches run in the workspace, including queries, answers,
    prompts, feedback, and metadata. Use this to inspect what users have
    searched for, analyze usage, or debug pipeline behavior.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param limit: Maximum number of entries to return per page.
    :param after: The cursor to fetch the next page of results.
        If there are more results to fetch, the cursor will appear as `next_cursor` on the response.
    :param query_filter: An OData filter expression to narrow down results.
        Supported fields: query, client_source_path, pipeline_version_id, answer, api_key,
        created_at, created_by, tags/tag_id, feedbacks, feedbacks/score, feedbacks/comment,
        feedbacks/bookmarked, session_id, search_session_id, feedbacks/result_id,
        request/filters, request/params, duration.
        Example: "created_at ge 2024-01-01T00:00:00Z" or "query eq 'my search'".
    :returns: Paginated list of search history entries or error message.
    """
    try:
        return await client.search_history(workspace=workspace).list(
            limit=limit, after=after, query_filter=query_filter
        )
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list search history: {e}"


async def list_pipeline_search_history(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    limit: int = 10,
    after: str | None = None,
    query_filter: str | None = None,
) -> PaginatedResponse[SearchHistoryEntry] | str:
    """Retrieves search history for a specific pipeline with pagination.

    Returns past searches run with the given pipeline (query, answer, pipeline used,
    and more). Use the `after` parameter with `next_cursor` from the response to
    fetch the next page.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to get search history for.
    :param limit: Maximum number of entries to return per page.
    :param after: The cursor to fetch the next page of results.
        If there are more results to fetch, the cursor will appear as `next_cursor` on the response.
    :param query_filter: An OData filter expression to narrow down results.
        Supported fields: query, client_source_path, pipeline_version_id, answer, api_key,
        created_at, created_by, tags/tag_id, feedbacks, feedbacks/score, feedbacks/comment,
        feedbacks/bookmarked, session_id, search_session_id, feedbacks/result_id,
        request/filters, request/params, duration.
        Example: "created_at ge 2024-01-01T00:00:00Z" or "query eq 'my search'".
    :returns: Paginated list of search history entries or error message.
    """
    try:
        return await client.search_history(workspace=workspace).list_pipeline(
            pipeline_name=pipeline_name, limit=limit, after=after, query_filter=query_filter
        )
    except ResourceNotFoundError:
        return (
            f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}', "
            "or the pipeline has no search history yet (archive is available ~30 min after search)."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list search history for pipeline '{pipeline_name}': {e}"
