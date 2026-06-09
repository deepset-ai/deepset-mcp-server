# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Literal

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
from deepset_mcp.api.search_history.protocols import SearchHistoryResourceProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.tools.search_history import (
    get_pipeline_trace,
    list_pipeline_search_history,
    list_pipeline_traces,
    list_search_history,
)
from test.unit.conftest import BaseFakeClient


def make_pipeline_trace_entry(
    query_id: str = "qid-001",
    query: str = "test trace query",
    status: str = "success",
    duration_s: float = 1.0,
    created_at: str = "2024-03-01T12:00:00Z",
) -> PipelineTraceEntry:
    from deepset_mcp.api.search_history.models import HaystackTraceV1

    return PipelineTraceEntry(
        query_id=query_id,
        query=query,
        status=status,
        duration_s=duration_s,
        created_at=created_at,
        haystack_trace=HaystackTraceV1(
            schema_version="haystack-trace/v1",
            run_id=f"run-{query_id}",
            started_at=created_at,
            status=status,
            traces=[],
            logs=[],
        ),
    )


class FakeSearchHistoryResource(SearchHistoryResourceProtocol):
    def __init__(
        self,
        list_response: PaginatedResponse[SearchHistoryEntry] | None = None,
        list_pipeline_response: PaginatedResponse[SearchHistoryEntry] | None = None,
        list_exception: Exception | None = None,
        list_pipeline_exception: Exception | None = None,
        list_traces_response: PaginatedResponse[PipelineTraceEntry] | None = None,
        list_traces_exception: Exception | None = None,
        get_trace_response: PipelineTraceEntry | None = None,
        get_trace_exception: Exception | None = None,
        get_trace_returns_none: bool = False,
    ) -> None:
        self._list_response = list_response
        self._list_pipeline_response = list_pipeline_response
        self._list_exception = list_exception
        self._list_pipeline_exception = list_pipeline_exception
        self._list_traces_response = list_traces_response
        self._list_traces_exception = list_traces_exception
        self._get_trace_response = get_trace_response
        self._get_trace_exception = get_trace_exception
        self._get_trace_returns_none = get_trace_returns_none

    async def list(
        self,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[SearchHistoryEntry]:
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return self._list_response
        return PaginatedResponse(data=[], has_more=False, total=0)

    async def list_pipeline(
        self,
        pipeline_name: str,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[SearchHistoryEntry]:
        if self._list_pipeline_exception:
            raise self._list_pipeline_exception
        if self._list_pipeline_response is not None:
            return self._list_pipeline_response
        return PaginatedResponse(data=[], has_more=False, total=0)

    async def list_pipeline_traces(
        self,
        pipeline_name: str,
        limit: int = 10,
        after: str | None = None,
        query_filter: str | None = None,
        sort_field: Literal["created_at", "query", "duration", "feedbacks/score"] = "created_at",
        sort_order: Literal["ASC", "DESC"] = "DESC",
    ) -> PaginatedResponse[PipelineTraceEntry]:
        if self._list_traces_exception:
            raise self._list_traces_exception
        if self._list_traces_response is not None:
            return self._list_traces_response
        return PaginatedResponse(data=[], has_more=False, total=0)

    async def get_pipeline_trace(
        self,
        pipeline_name: str,
        query_id: str,
    ) -> PipelineTraceEntry | None:
        if self._get_trace_exception:
            raise self._get_trace_exception
        if self._get_trace_returns_none:
            return None
        return self._get_trace_response


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeSearchHistoryResource) -> None:
        self._resource = resource
        super().__init__()

    def search_history(self, workspace: str) -> FakeSearchHistoryResource:
        return self._resource


def create_search_history_entry(
    query: str = "test query",
    time: str = "2023-01-01T12:00:00Z",
    pipeline_name: str = "test-pipeline",
    duration: float = 0.5,
    status: str = "success",
    feedback: list[dict[str, Any]] | None = None,
) -> SearchHistoryEntry:
    """Helper to create a SearchHistoryEntry matching the v1 API response structure."""
    return SearchHistoryEntry(
        search_history_id="00000000-0000-0000-0000-000000000001",
        request={"query": query, "filters": None, "params": {}},
        time=time,
        duration=duration,
        status=status,
        pipeline={"name": pipeline_name},
        feedback=feedback,
    )


# list_search_history tests


@pytest.mark.asyncio
async def test_list_search_history_returns_entries() -> None:
    """Test successful workspace search history list."""
    entry1 = create_search_history_entry(query="query one", pipeline_name="p1")
    entry2 = create_search_history_entry(query="query two", pipeline_name="p2")
    response = PaginatedResponse(data=[entry1, entry2], has_more=False, total=2)

    resource = FakeSearchHistoryResource(list_response=response)
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="ws1")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 2
    # query is extracted from request.query via model_validator
    assert result.data[0].query == "query one"
    assert result.data[1].query == "query two"
    assert result.total == 2


@pytest.mark.asyncio
async def test_list_search_history_empty() -> None:
    """Test list search history with no entries."""
    resource = FakeSearchHistoryResource(list_response=PaginatedResponse(data=[], has_more=False, total=0))
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="ws1")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 0
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_search_history_with_pagination() -> None:
    """Test list search history with limit and after cursor."""
    entry = create_search_history_entry(query="paged query")
    response = PaginatedResponse(data=[entry], has_more=True, total=10, next_cursor="cursor_abc")

    resource = FakeSearchHistoryResource(list_response=response)
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="ws1", limit=5, after="cursor_prev")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 1
    assert result.data[0].query == "paged query"
    assert result.has_more is True
    assert result.next_cursor == "cursor_abc"


@pytest.mark.asyncio
async def test_list_search_history_workspace_not_found() -> None:
    """Test list search history when workspace does not exist."""
    resource = FakeSearchHistoryResource(list_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="nonexistent")

    assert isinstance(result, str)
    assert "There is no workspace named 'nonexistent'" in result
    assert "Did you mean to configure it?" in result


@pytest.mark.asyncio
async def test_list_search_history_bad_request() -> None:
    """Test list search history with bad request error."""
    resource = FakeSearchHistoryResource(list_exception=BadRequestError(message="Invalid parameters"))
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="ws1")

    assert isinstance(result, str)
    assert "Failed to list search history" in result
    assert "Invalid parameters" in result


@pytest.mark.asyncio
async def test_list_search_history_unexpected_error() -> None:
    """Test list search history with unexpected API error."""
    resource = FakeSearchHistoryResource(
        list_exception=UnexpectedAPIError(status_code=500, message="Internal server error")
    )
    client = FakeClient(resource)

    result = await list_search_history(client=client, workspace="ws1")

    assert isinstance(result, str)
    assert "Failed to list search history" in result
    assert "Internal server error" in result


# list_pipeline_search_history tests


@pytest.mark.asyncio
async def test_list_pipeline_search_history_returns_entries() -> None:
    """Test successful pipeline search history list."""
    entry1 = create_search_history_entry(query="pipeline query 1", pipeline_name="my-pipeline")
    entry2 = create_search_history_entry(query="pipeline query 2", pipeline_name="my-pipeline")
    response = PaginatedResponse(data=[entry1, entry2], has_more=False, total=2)

    resource = FakeSearchHistoryResource(list_pipeline_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_search_history(client=client, workspace="ws1", pipeline_name="my-pipeline")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 2
    # pipeline name is at pipeline.name in the v1 API response
    assert result.data[0].pipeline == {"name": "my-pipeline"}
    assert result.data[1].query == "pipeline query 2"


@pytest.mark.asyncio
async def test_list_pipeline_search_history_empty() -> None:
    """Test list pipeline search history with no entries."""
    resource = FakeSearchHistoryResource(list_pipeline_response=PaginatedResponse(data=[], has_more=False, total=0))
    client = FakeClient(resource)

    result = await list_pipeline_search_history(client=client, workspace="ws1", pipeline_name="empty-pipeline")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 0
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_pipeline_search_history_with_pagination() -> None:
    """Test list pipeline search history with limit and after cursor."""
    entry = create_search_history_entry(query="paged pipeline query", pipeline_name="p")
    response = PaginatedResponse(data=[entry], has_more=True, total=5, next_cursor="next_page")

    resource = FakeSearchHistoryResource(list_pipeline_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_search_history(
        client=client,
        workspace="ws1",
        pipeline_name="p",
        limit=3,
        after="prev_cursor",
    )

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 1
    assert result.has_more is True
    assert result.next_cursor == "next_page"


@pytest.mark.asyncio
async def test_list_pipeline_search_history_pipeline_not_found() -> None:
    """Test list pipeline search history when pipeline does not exist."""
    resource = FakeSearchHistoryResource(list_pipeline_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await list_pipeline_search_history(client=client, workspace="ws1", pipeline_name="missing-pipeline")

    assert isinstance(result, str)
    assert "There is no pipeline named 'missing-pipeline' in workspace 'ws1'" in result
    assert "or the pipeline has no search history yet" in result


@pytest.mark.asyncio
async def test_list_pipeline_search_history_bad_request() -> None:
    """Test list pipeline search history with bad request error."""
    resource = FakeSearchHistoryResource(list_pipeline_exception=BadRequestError(message="Invalid filter"))
    client = FakeClient(resource)

    result = await list_pipeline_search_history(client=client, workspace="ws1", pipeline_name="my-pipeline")

    assert isinstance(result, str)
    assert "Failed to list search history for pipeline 'my-pipeline'" in result
    assert "Invalid filter" in result


@pytest.mark.asyncio
async def test_list_pipeline_search_history_unexpected_error() -> None:
    """Test list pipeline search history with unexpected API error."""
    resource = FakeSearchHistoryResource(
        list_pipeline_exception=UnexpectedAPIError(status_code=503, message="Service unavailable")
    )
    client = FakeClient(resource)

    result = await list_pipeline_search_history(client=client, workspace="ws1", pipeline_name="my-pipeline")

    assert isinstance(result, str)
    assert "Failed to list search history for pipeline 'my-pipeline'" in result
    assert "Service unavailable" in result


# ---------------------------------------------------------------------------
# list_pipeline_traces tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pipeline_traces_returns_paginated_response() -> None:
    entry = make_pipeline_trace_entry(query_id="qid-1", query="trace query")
    response = PaginatedResponse(data=[entry], has_more=False, total=1)

    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="my-pipeline")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 1
    assert result.data[0].query == "trace query"
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_pipeline_traces_returns_multiple_entries() -> None:
    entries = [
        make_pipeline_trace_entry("qid-1", "first"),
        make_pipeline_trace_entry("qid-2", "second"),
        make_pipeline_trace_entry("qid-3", "third"),
    ]
    response = PaginatedResponse(data=entries, has_more=False, total=3)

    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 3
    assert result.data[0].query_id == "qid-1"
    assert result.data[2].query == "third"


@pytest.mark.asyncio
async def test_list_pipeline_traces_empty_result() -> None:
    resource = FakeSearchHistoryResource(list_traces_response=PaginatedResponse(data=[], has_more=False, total=0))
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p")

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 0
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_pipeline_traces_pagination_cursor() -> None:
    entry = make_pipeline_trace_entry("qid-1")
    response = PaginatedResponse(data=[entry], has_more=True, total=50, next_cursor="2024-03-01T09:00:00Z")

    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p", after="2024-03-01T12:00:00Z")

    assert isinstance(result, PaginatedResponse)
    assert result.has_more is True
    assert result.next_cursor == "2024-03-01T09:00:00Z"


@pytest.mark.asyncio
async def test_list_pipeline_traces_with_sort_params() -> None:
    response: PaginatedResponse[PipelineTraceEntry] = PaginatedResponse(data=[], has_more=False, total=0)
    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    # Should not raise — tool accepts these params
    result = await list_pipeline_traces(
        client=client,
        workspace="ws1",
        pipeline_name="p",
        sort_field="duration",
        sort_order="ASC",
    )

    assert isinstance(result, PaginatedResponse)


@pytest.mark.asyncio
async def test_list_pipeline_traces_with_query_filter() -> None:
    response: PaginatedResponse[PipelineTraceEntry] = PaginatedResponse(data=[], has_more=False, total=0)
    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_traces(
        client=client,
        workspace="ws1",
        pipeline_name="p",
        query_filter="status eq 'failed'",
    )

    assert isinstance(result, PaginatedResponse)


@pytest.mark.asyncio
async def test_list_pipeline_traces_pipeline_not_found() -> None:
    resource = FakeSearchHistoryResource(list_traces_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="gone")

    assert isinstance(result, str)
    assert "There is no pipeline named 'gone' in workspace 'ws1'" in result


@pytest.mark.asyncio
async def test_list_pipeline_traces_bad_request_error() -> None:
    resource = FakeSearchHistoryResource(list_traces_exception=BadRequestError(message="bad filter"))
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p")

    assert isinstance(result, str)
    assert "Failed to list traces for pipeline 'p'" in result
    assert "bad filter" in result


@pytest.mark.asyncio
async def test_list_pipeline_traces_unexpected_api_error() -> None:
    resource = FakeSearchHistoryResource(list_traces_exception=UnexpectedAPIError(status_code=500, message="boom"))
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p")

    assert isinstance(result, str)
    assert "Failed to list traces for pipeline 'p'" in result
    assert "boom" in result


@pytest.mark.asyncio
async def test_list_pipeline_traces_entry_has_haystack_trace() -> None:
    entry = make_pipeline_trace_entry("qid-x", "trace check", status="failed")
    response = PaginatedResponse(data=[entry], has_more=False, total=1)

    resource = FakeSearchHistoryResource(list_traces_response=response)
    client = FakeClient(resource)

    result = await list_pipeline_traces(client=client, workspace="ws1", pipeline_name="p")

    assert isinstance(result, PaginatedResponse)
    trace = result.data[0]
    assert trace.status == "failed"
    assert trace.haystack_trace is not None
    assert trace.haystack_trace.run_id == "run-qid-x"


# ---------------------------------------------------------------------------
# get_pipeline_trace tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pipeline_trace_returns_entry() -> None:
    entry = make_pipeline_trace_entry("qid-001", "deep dive query", duration_s=2.5)
    resource = FakeSearchHistoryResource(get_trace_response=entry)
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="qid-001")

    assert isinstance(result, PipelineTraceEntry)
    assert result.query_id == "qid-001"
    assert result.query == "deep dive query"
    assert result.duration_s == 2.5


@pytest.mark.asyncio
async def test_get_pipeline_trace_entry_has_nested_trace() -> None:
    entry = make_pipeline_trace_entry("qid-abc", status="success")
    resource = FakeSearchHistoryResource(get_trace_response=entry)
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="qid-abc")

    assert isinstance(result, PipelineTraceEntry)
    assert result.haystack_trace is not None
    assert result.haystack_trace.schema_version == "haystack-trace/v1"


@pytest.mark.asyncio
async def test_get_pipeline_trace_none_response_returns_error_string() -> None:
    resource = FakeSearchHistoryResource(get_trace_returns_none=True)
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="missing-qid")

    assert isinstance(result, str)
    assert "missing-qid" in result
    assert "p" in result


@pytest.mark.asyncio
async def test_get_pipeline_trace_resource_not_found_error() -> None:
    resource = FakeSearchHistoryResource(get_trace_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="qid-404")

    assert isinstance(result, str)
    assert "qid-404" in result
    assert "p" in result
    assert "ws1" in result


@pytest.mark.asyncio
async def test_get_pipeline_trace_bad_request_error() -> None:
    resource = FakeSearchHistoryResource(get_trace_exception=BadRequestError(message="malformed id"))
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="bad-id")

    assert isinstance(result, str)
    assert "bad-id" in result
    assert "malformed id" in result


@pytest.mark.asyncio
async def test_get_pipeline_trace_unexpected_api_error() -> None:
    resource = FakeSearchHistoryResource(
        get_trace_exception=UnexpectedAPIError(status_code=503, message="service down")
    )
    client = FakeClient(resource)

    result = await get_pipeline_trace(client=client, workspace="ws1", pipeline_name="p", query_id="qid-err")

    assert isinstance(result, str)
    assert "qid-err" in result
    assert "service down" in result
