import json
from typing import Any

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.indexes.resource import IndexResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


@pytest.fixture()
def fake_client() -> BaseFakeClient:
    return BaseFakeClient()


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
        "created_by": {"given_name": "Test", "family_name": "User", "user_id": "test-id"},
        "last_edited_by": {"given_name": "Test", "family_name": "User", "user_id": "test-id"},
        "status": {
            "pending_file_count": 0,
            "failed_file_count": 0,
            "indexed_no_documents_file_count": 0,
            "indexed_file_count": 0,
            "total_file_count": 0,
        },
    }


@pytest.fixture
def index_list_response(index_response: dict[str, Any]) -> dict[str, Any]:
    """Sample response for listing indexes."""
    return {"data": [index_response], "has_more": False, "total": 1}


@pytest.fixture
def workspace() -> str:
    """Sample workspace ID."""
    return "test-workspace"


@pytest.fixture()
def fake_list_successful_response(
    fake_client: BaseFakeClient, index_list_response: dict[str, Any], workspace: str
) -> None:
    """Configure the fake client to return a successful response."""
    fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes"] = TransportResponse(
        status_code=200,
        json=index_list_response,
        text=json.dumps(index_list_response),
    )


@pytest.fixture()
def fake_get_successful_response(fake_client: BaseFakeClient, index_response: dict[str, Any], workspace: str) -> None:
    """Configure the fake client to return a successful response."""
    fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes/test-index"] = TransportResponse(
        status_code=200,
        json=index_response,
        text=json.dumps(index_response),
    )


@pytest.fixture()
def fake_get_404_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 404 response."""
    fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes/nonexistent-index"] = TransportResponse(
        status_code=404,
        json={"detail": "Resource not found"},
        text=json.dumps({"detail": "Resource not found"}),
    )


@pytest.fixture()
def fake_get_500_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 500 response."""
    fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes/server-error-index"] = TransportResponse(
        status_code=500,
        json={"detail": "Internal server error"},
        text=json.dumps({"detail": "Internal server error"}),
    )


class TestIndexResource:
    """Test the IndexResource."""

    async def test_get_index_returns_index(
        self, fake_client: BaseFakeClient, workspace: str, fake_get_successful_response: None
    ) -> None:
        """Test that getting an index returns an Index instance."""
        resource = IndexResource(fake_client, workspace)
        result = await resource.get("test-index")
        assert isinstance(result, Index)
        assert result.name == "test-index"

    async def test_list_indexes_returns_list(
        self, fake_client: BaseFakeClient, workspace: str, fake_list_successful_response: None
    ) -> None:
        """Test that listing indexes returns an IndexList instance."""
        resource = IndexResource(fake_client, workspace)
        result = await resource.list()
        assert isinstance(result, IndexList)
        assert len(result.data) == 1
        assert isinstance(result.data[0], Index)
        assert result.total == 1
        assert result.has_more is False

    async def test_get_nonexistent_index_raises_404(
        self, fake_client: BaseFakeClient, workspace: str, fake_get_404_response: None
    ) -> None:
        """Test that getting a nonexistent index raises ResourceNotFoundError."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(ResourceNotFoundError):
            await resource.get("nonexistent-index")

    async def test_get_server_error_raises_500(
        self, fake_client: BaseFakeClient, workspace: str, fake_get_500_response: None
    ) -> None:
        """Test that server error raises UnexpectedAPIError."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(UnexpectedAPIError):
            await resource.get("server-error-index")

    async def test_list_indexes_passes_params(
        self, fake_client: BaseFakeClient, workspace: str, fake_list_successful_response: None
    ) -> None:
        """Test that parameters are passed to the client in list method."""
        resource = IndexResource(fake_client, workspace)
        await resource.list(limit=20, page_number=2)

        # Check the last request's parameters
        last_request = fake_client.requests[-1]
        assert last_request["params"] == {"limit": 20, "page_number": 2}

    async def test_create_index_successful(
        self, fake_client: BaseFakeClient, workspace: str, index_response: dict[str, Any]
    ) -> None:
        """Test creating a new index."""
        fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes"] = TransportResponse(
            status_code=201,
            json=index_response,
            text=json.dumps(index_response)
        )

        resource = IndexResource(fake_client, workspace)
        result = await resource.create(
            name="test-index",
            config_yaml="yaml: content",
            description="Test description"
        )

        assert isinstance(result, Index)
        assert result.name == "test-index"

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["method"] == "POST"
        assert last_request["data"] == {
            "name": "test-index",
            "config_yaml": "yaml: content",
            "description": "Test description"
        }

    async def test_update_index_successful(
        self, fake_client: BaseFakeClient, workspace: str, index_response: dict[str, Any]
    ) -> None:
        """Test updating an existing index."""
        fake_client.responses[f"/api/v1/workspaces/{workspace}/indexes/test-index"] = TransportResponse(
            status_code=200,
            json=index_response,
            text=json.dumps(index_response)
        )

        resource = IndexResource(fake_client, workspace)
        result = await resource.update(
            index_name="test-index",
            updated_index_name="new-name",
            config_yaml="new: config"
        )

        assert isinstance(result, Index)
        assert result.name == "test-index"

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["method"] == "PATCH"
        assert last_request["data"] == {
            "name": "new-name",
            "config_yaml": "new: config"
        }

    async def test_update_index_without_changes_fails(
        self, fake_client: BaseFakeClient, workspace: str
    ) -> None:
        """Test that updating an index without any changes raises ValueError."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(ValueError, match="At least one of updated_index_name or config_yaml must be provided"):
            await resource.update(index_name="test-index")
