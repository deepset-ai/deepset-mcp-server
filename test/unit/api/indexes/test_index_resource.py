from typing import Any, AsyncGenerator

import pytest
from deepset_mcp.api.clients import AsyncRestClient
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.indexes.resource import IndexResource


class FakeRestClient(AsyncRestClient):
    """A fake REST client for testing."""

    def __init__(self, response: dict[str, Any]) -> None:
        """Initialize the fake client."""
        self.response = response

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Mock a GET request."""
        return self.response


@pytest.fixture
def index_response() -> dict[str, Any]:
    """Sample response for an index."""
    return {
        "pipeline_index_id": "my-id",
        "name": "test-index",
        "description": None,
        "config_yaml": "yaml: content",
        "workspace_id": "my-workspace",
        "settings": {},
        "desired_status": "DEPLOYED",
        "deployed_at": "2025-01-01T00:00:00Z",
        "last_edited_at": "2025-01-01T00:00:00Z",
        "max_index_replica_count": 10,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "created_by": {
            "given_name": "Test",
            "family_name": "User",
            "user_id": "test-id"
        },
        "last_edited_by": {
            "given_name": "Test",
            "family_name": "User",
            "user_id": "test-id"
        },
        "status": {
            "pending_file_count": 0,
            "failed_file_count": 0,
            "indexed_no_documents_file_count": 0,
            "indexed_file_count": 0,
            "total_file_count": 0
        }
    }


@pytest.fixture
def index_list_response(index_response: dict[str, Any]) -> dict[str, Any]:
    """Sample response for listing indexes."""
    return {
        "data": [index_response],
        "has_more": False,
        "total": 1
    }


@pytest.fixture
def workspace() -> str:
    """Sample workspace ID."""
    return "test-workspace"


@pytest.fixture
async def client(index_response: dict[str, Any]) -> AsyncGenerator[AsyncRestClient, None]:
    """Create a fake client with the sample response."""
    yield FakeRestClient(index_response)


@pytest.fixture
async def list_client(index_list_response: dict[str, Any]) -> AsyncGenerator[AsyncRestClient, None]:
    """Create a fake client with the sample list response."""
    yield FakeRestClient(index_list_response)


class TestIndexResource:
    """Test the IndexResource."""

    async def test_get_index_returns_index(self, client: AsyncRestClient, workspace: str) -> None:
        """Test that getting an index returns an Index instance."""
        resource = IndexResource(client, workspace)
        result = await resource.get("test-index")
        assert isinstance(result, Index)
        assert result.name == "test-index"

    async def test_list_indexes_returns_list(self, list_client: AsyncRestClient, workspace: str) -> None:
        """Test that listing indexes returns an IndexList instance."""
        resource = IndexResource(list_client, workspace)
        result = await resource.list()
        assert isinstance(result, IndexList)
        assert len(result.data) == 1
        assert isinstance(result.data[0], Index)
        assert result.total == 1
        assert result.has_more is False

    async def test_list_indexes_with_params(self, list_client: AsyncRestClient, workspace: str) -> None:
        """Test that listing indexes with parameters works."""
        resource = IndexResource(list_client, workspace)
        result = await resource.list(limit=5, page_number=1)
        assert isinstance(result, IndexList)
        assert len(result.data) == 1