# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.search_history.models import SearchHistoryEntry
from deepset_mcp.api.search_history.protocols import SearchHistoryResourceProtocol
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.tools.search_history import list_pipeline_search_history, list_search_history
from test.unit.conftest import BaseFakeClient


class FakeSearchHistoryResource(SearchHistoryResourceProtocol):
    def __init__(
        self,
        list_response: PaginatedResponse[SearchHistoryEntry] | None = None,
        list_pipeline_response: PaginatedResponse[SearchHistoryEntry] | None = None,
        list_exception: Exception | None = None,
        list_pipeline_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._list_pipeline_response = list_pipeline_response
        self._list_exception = list_exception
        self._list_pipeline_exception = list_pipeline_exception

    async def list(self, limit: int = 10, after: str | None = None) -> PaginatedResponse[SearchHistoryEntry]:
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return self._list_response
        return PaginatedResponse(data=[], has_more=False, total=0)

    async def list_pipeline(
        self, pipeline_name: str, limit: int = 10, after: str | None = None
    ) -> PaginatedResponse[SearchHistoryEntry]:
        if self._list_pipeline_exception:
            raise self._list_pipeline_exception
        if self._list_pipeline_response is not None:
            return self._list_pipeline_response
        return PaginatedResponse(data=[], has_more=False, total=0)


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeSearchHistoryResource) -> None:
        self._resource = resource
        super().__init__()

    def search_history(self, workspace: str) -> FakeSearchHistoryResource:
        return self._resource


def create_search_history_entry(
    query: str = "test query",
    answer: str | None = "test answer",
    created_at: str | None = "2023-01-01T12:00:00Z",
    pipeline_name: str | None = "test-pipeline",
    feedback: list[dict] | None = None,
) -> SearchHistoryEntry:
    """Helper to create a SearchHistoryEntry for tests."""
    return SearchHistoryEntry(
        query=query,
        answer=answer,
        created_at=created_at,
        pipeline_name=pipeline_name,
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
    assert result.data[0].pipeline_name == "my-pipeline"
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
