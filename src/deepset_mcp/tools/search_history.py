# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with search history in a deepset workspace."""

from typing import Literal

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
from deepset_mcp.api.shared_models import PaginatedResponse


async def list_search_history(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    limit: int = 10,
    after: str | None = None,
    query_filter: str | None = None,
    sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
    sort_order: Literal["ASC", "DESC"] = "DESC",
) -> PaginatedResponse[SearchHistoryEntry] | str:
    """Retrieves search history for the configured deepset workspace.

    Returns past searches run in the workspace, including queries, answers,
    prompts, feedback, and metadata. Use this to inspect what users have
    searched for, analyze usage, or debug pipeline behavior.

    Each entry includes:
    - ``request.query`` — the search query text
    - ``time`` / ``created_at`` — when the search ran
    - ``duration`` — how long it took (seconds)
    - ``status`` — 'success' or 'failed'
    - ``pipeline.name`` — which pipeline handled the query
    - ``response`` — the list of search results
    - ``feedback``, ``labels``, ``note`` — user annotations

    Use the ``after`` parameter with the ``next_cursor`` value from the
    previous response to fetch the next page.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param limit: Maximum number of entries to return per page (default 10, max 1000).
    :param after: ISO-8601 timestamp cursor to fetch entries older than this point.
        Pass the value from ``next_cursor`` on the previous response.
    :param query_filter: An OData filter expression to narrow down results.
        Supported fields: query, client_source_path, pipeline_version_id, answer,
        api_key, created_at, created_by, tags/tag_id, feedbacks, feedbacks/score,
        feedbacks/comment, feedbacks/bookmarked, session_id, search_session_id,
        feedbacks/result_id, request/filters, request/params, duration, labels,
        status, note.
        Example: "created_at ge 2024-01-01T00:00:00Z" or "query eq 'my search'".
    :param sort_field: Field to sort results by. One of: created_at, query,
        duration, feedbacks/score. Defaults to created_at.
    :param sort_order: Sort direction — ASC (oldest first) or DESC (newest first).
        Defaults to DESC.
    :returns: Paginated list of search history entries or error message.
    """
    try:
        return await client.search_history(workspace=workspace).list(
            limit=limit,
            after=after,
            query_filter=query_filter,
            sort_field=sort_field,
            sort_order=sort_order,
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
    sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
    sort_order: Literal["ASC", "DESC"] = "DESC",
) -> PaginatedResponse[SearchHistoryEntry] | str:
    """Retrieves search history for a specific pipeline with pagination.

    Returns past searches run with the given pipeline. Each entry includes the
    search query (``request.query``), results (``response``), timing
    (``time``/``duration``), status, user info, feedback, labels, and note.

    Search history is archived ~30 minutes after a search runs and is then
    available via this endpoint.

    Use the ``after`` parameter with ``next_cursor`` from the response to
    fetch the next page.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to get search history for.
    :param limit: Maximum number of entries to return per page (default 10, max 1000).
    :param after: ISO-8601 timestamp cursor to fetch entries older than this point.
        Pass the value from ``next_cursor`` on the previous response.
    :param query_filter: An OData filter expression to narrow down results.
        Supported fields: query, client_source_path, pipeline_version_id, answer,
        api_key, created_at, created_by, tags/tag_id, feedbacks, feedbacks/score,
        feedbacks/comment, feedbacks/bookmarked, session_id, search_session_id,
        feedbacks/result_id, request/filters, request/params, duration, labels,
        status, note.
        Example: "created_at ge 2024-01-01T00:00:00Z" or "status eq 'failed'".
    :param sort_field: Field to sort results by. One of: created_at, query,
        duration, feedbacks/score. Defaults to created_at.
    :param sort_order: Sort direction — ASC (oldest first) or DESC (newest first).
        Defaults to DESC.
    :returns: Paginated list of search history entries or error message.
    """
    try:
        return await client.search_history(workspace=workspace).list_pipeline(
            pipeline_name=pipeline_name,
            limit=limit,
            after=after,
            query_filter=query_filter,
            sort_field=sort_field,
            sort_order=sort_order,
        )
    except ResourceNotFoundError:
        return (
            f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}', "
            "or the pipeline has no search history yet (archive is available ~30 min after search)."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list search history for pipeline '{pipeline_name}': {e}"


async def list_pipeline_traces(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    limit: int = 10,
    after: str | None = None,
    query_filter: str | None = None,
    sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
    sort_order: Literal["ASC", "DESC"] = "DESC",
) -> PaginatedResponse[PipelineTraceEntry] | str:
    """Retrieves Haystack pipeline run traces for a specific pipeline.

    Each trace contains the full execution breakdown of a search query: spans per
    component, timing, logs, and failure details if the run failed. Use this to
    debug slow or failing pipeline runs, inspect component-level behaviour, or
    audit query execution history.

    This tool resolves the pipeline and workspace IDs automatically and calls
    the v2 traces endpoint under the hood.

    Use the ``after`` parameter with ``next_cursor`` from the response to fetch
    the next page.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to retrieve traces for.
    :param limit: Maximum number of trace entries to return per page (default 10).
    :param after: ISO-8601 timestamp cursor from ``next_cursor`` on the previous response.
    :param query_filter: An OData filter expression to narrow down results.
        Supported fields: query, client_source_path, pipeline_version_id, answer,
        api_key, created_at, created_by, tags/tag_id, feedbacks, feedbacks/score,
        feedbacks/comment, feedbacks/bookmarked, session_id, search_session_id,
        feedbacks/result_id, request/filters, request/params, duration, labels,
        status, note.
        Example: "status eq 'failed'" or "created_at ge 2024-01-01T00:00:00Z".
    :param sort_field: Field to sort results by. One of: created_at, query,
        duration, feedbacks/score. Defaults to created_at.
    :param sort_order: Sort direction — ASC (oldest first) or DESC (newest first).
        Defaults to DESC.
    :returns: Paginated list of pipeline trace entries or an error message.
    """
    try:
        return await client.search_history(workspace=workspace).list_pipeline_traces(
            pipeline_name=pipeline_name,
            limit=limit,
            after=after,
            query_filter=query_filter,
            sort_field=sort_field,
            sort_order=sort_order,
        )
    except ResourceNotFoundError:
        return (
            f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}', "
            "or it has no traces yet."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list traces for pipeline '{pipeline_name}': {e}"


async def get_pipeline_trace(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    query_id: str,
) -> PipelineTraceEntry | str:
    """Retrieves the Haystack pipeline run trace for a single search history record.

    Returns the full execution trace for one query: all component spans with
    timing, log entries, and failure details. Use this to deep-dive into a
    specific query run identified by its ``query_id`` (obtainable from
    ``list_pipeline_traces`` or ``list_pipeline_search_history``).

    This tool resolves the pipeline and workspace IDs automatically and calls
    the v2 single-trace endpoint under the hood.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param query_id: UUID of the search history query whose trace to retrieve.
        Obtain this from the ``query_id`` / ``search_history_id`` field of a
        ``list_pipeline_traces`` or ``list_pipeline_search_history`` response.
    :returns: The pipeline trace entry or an error message.
    """
    try:
        result = await client.search_history(workspace=workspace).get_pipeline_trace(
            pipeline_name=pipeline_name,
            query_id=query_id,
        )
        if result is None:
            return f"No trace found for query_id '{query_id}' in pipeline '{pipeline_name}'."
        return result
    except ResourceNotFoundError:
        return (
            f"No trace found for query_id '{query_id}' in pipeline '{pipeline_name}' "
            f"(workspace '{workspace}'). The query may not exist or may not have a stored trace."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to get trace for query_id '{query_id}': {e}"
