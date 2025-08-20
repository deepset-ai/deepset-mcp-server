# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.resource import IndexResource
from deepset_mcp.api.pipeline.models import PipelineValidationResult
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class DummyIndexClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        super().__init__(responses)
        self.response_queue: list[TransportResponse[Any]] = []
        self.response_index = 0
        # Store all available index data for cursor-based pagination
        self.all_index_data: list[dict[str, Any]] = []

    def set_responses(self, responses: list[TransportResponse[Any]]) -> None:
        """Set a queue of responses for sequential requests."""
        self.response_queue = responses
        self.response_index = 0

    def set_index_data(self, all_indexes: list[dict[str, Any]]) -> None:
        """Set all index data for cursor-based pagination testing."""
        self.all_index_data = all_indexes

    async def request(self, endpoint: str, **kwargs: Any) -> TransportResponse[Any]:
        """Override to use queued responses when available, or handle pagination logic for indexes."""

        if self.response_queue and self.response_index < len(self.response_queue):
            # Always record the request like the parent class
            self.requests.append({"endpoint": endpoint, **kwargs})
            response = self.response_queue[self.response_index]
            self.response_index += 1
            return response

        # Handle cursor-based pagination for index listing (only when no static response is available)
        if (
            endpoint.endswith("/indexes")
            and kwargs.get("method", "GET") == "GET"
            and self.all_index_data
            and not self._has_static_response(endpoint)
        ):
            # Always record the request like the parent class
            self.requests.append({"endpoint": endpoint, **kwargs})
            return await self._handle_paginated_indexes(**kwargs)

        # Let parent handle the request and recording
        return await super().request(endpoint, **kwargs)

    def _has_static_response(self, endpoint: str) -> bool:
        """Check if there's a static response configured for this endpoint."""
        # Check if there's a response in the responses dict for this endpoint
        if self.responses:
            for key in self.responses.keys():
                if endpoint.endswith(key):
                    return True
        return False

    async def _handle_paginated_indexes(self, **kwargs: Any) -> TransportResponse[Any]:
        """Handle pagination logic for index listing."""
        params = kwargs.get("params", {})
        limit = params.get("limit", 10)
        before_cursor = params.get("before")

        # Find start index based on cursor
        start_index = 0
        if before_cursor:
            # Find the index with this ID and start after it
            for i, index in enumerate(self.all_index_data):
                if index["pipeline_index_id"] == before_cursor:
                    start_index = i + 1
                    break

        # Get the slice of data
        end_index = start_index + limit
        page_data = self.all_index_data[start_index:end_index]
        has_more = end_index < len(self.all_index_data)

        response_data = {
            "data": page_data,
            "has_more": has_more,
            "total": len(self.all_index_data),
        }

        return TransportResponse(status_code=200, json=response_data, text="")


@pytest.fixture()
def fake_client() -> BaseFakeClient:
    return BaseFakeClient()


@pytest.fixture()
def dummy_index_client() -> DummyIndexClient:
    return DummyIndexClient()


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
    fake_client.responses[f"v1/workspaces/{workspace}/indexes"] = TransportResponse(
        status_code=200,
        json=index_list_response,
        text=json.dumps(index_list_response),
    )


@pytest.fixture()
def fake_get_successful_response(fake_client: BaseFakeClient, index_response: dict[str, Any], workspace: str) -> None:
    """Configure the fake client to return a successful response."""
    fake_client.responses[f"v1/workspaces/{workspace}/indexes/test-index"] = TransportResponse(
        status_code=200,
        json=index_response,
        text=json.dumps(index_response),
    )


@pytest.fixture()
def fake_get_404_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 404 response."""
    fake_client.responses[f"/v1/workspaces/{workspace}/indexes/nonexistent-index"] = TransportResponse(
        status_code=404,
        json={"detail": "Resource not found"},
        text=json.dumps({"detail": "Resource not found"}),
    )


@pytest.fixture()
def fake_get_500_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 500 response."""
    fake_client.responses[f"/v1/workspaces/{workspace}/indexes/server-error-index"] = TransportResponse(
        status_code=500,
        json={"detail": "Internal server error"},
        text=json.dumps({"detail": "Internal server error"}),
    )


@pytest.fixture()
def fake_create_400_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 400 response for invalid create request."""
    fake_client.responses[f"v1/workspaces/{workspace}/indexes"] = TransportResponse(
        status_code=400,
        json={"detail": "Invalid request parameters"},
        text=json.dumps({"detail": "Invalid request parameters"}),
    )


@pytest.fixture()
def fake_update_404_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 404 response for nonexistent index update."""
    fake_client.responses[f"/v1/workspaces/{workspace}/indexes/nonexistent-index"] = TransportResponse(
        status_code=404,
        json={"detail": "Index not found"},
        text=json.dumps({"detail": "Index not found"}),
    )


@pytest.fixture()
def fake_update_400_response(fake_client: BaseFakeClient, workspace: str) -> None:
    """Configure fake client to return a 400 response for invalid update request."""
    fake_client.responses[f"/v1/workspaces/{workspace}/indexes/invalid-index"] = TransportResponse(
        status_code=400,
        json={"detail": "Invalid configuration format"},
        text=json.dumps({"detail": "Invalid configuration format"}),
    )


def create_sample_index(
    pipeline_index_id: str = "test-index-id",
    name: str = "test-index",
    description: str | None = None,
) -> dict[str, Any]:
    """Create a sample index response dictionary for testing."""
    return {
        "pipeline_index_id": pipeline_index_id,
        "name": name,
        "description": description,
        "config_yaml": "yaml: content",
        "workspace_id": "test-workspace",
        "settings": {},
        "desired_status": "DEPLOYED",
        "deployed_at": "2025-01-01T00:00:00Z",
        "last_edited_at": "2025-01-01T00:00:00Z",
        "max_index_replica_count": 10,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "created_by": {
            "user_id": "test-user",
            "given_name": "Test",
            "family_name": "User",
            "email": "test@example.com",
        },
        "last_edited_by": {
            "user_id": "test-user",
            "given_name": "Test",
            "family_name": "User",
            "email": "test@example.com",
        },
        "status": {
            "pending_file_count": 0,
            "failed_file_count": 0,
            "indexed_no_documents_file_count": 0,
            "indexed_file_count": 10,
            "total_file_count": 10,
        },
    }


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

    async def test_list_indexes_returns_paginated_response(
        self, fake_client: BaseFakeClient, workspace: str, fake_list_successful_response: None
    ) -> None:
        """Test that listing indexes returns a PaginatedResponse instance."""
        resource = IndexResource(fake_client, workspace)
        result = await resource.list()
        assert isinstance(result, PaginatedResponse)
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
        await resource.list(limit=20, after="cursor123")

        # Check the last request's parameters
        last_request = fake_client.requests[-1]
        assert last_request["params"] == {"limit": 20, "before": "cursor123"}

    async def test_create_index_successful(
        self, fake_client: BaseFakeClient, workspace: str, index_response: dict[str, Any]
    ) -> None:
        """Test creating a new index."""
        fake_client.responses[f"v1/workspaces/{workspace}/indexes"] = TransportResponse(
            status_code=201, json=index_response, text=json.dumps(index_response)
        )

        resource = IndexResource(fake_client, workspace)
        result = await resource.create(
            index_name="test-index", yaml_config="yaml: content", description="Test description"
        )

        assert isinstance(result, Index)
        assert result.name == "test-index"

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["method"] == "POST"
        assert last_request["data"] == {
            "name": "test-index",
            "config_yaml": "yaml: content",
            "description": "Test description",
        }

    async def test_update_index_successful(
        self, fake_client: BaseFakeClient, workspace: str, index_response: dict[str, Any]
    ) -> None:
        """Test updating an existing index."""
        fake_client.responses[f"/v1/workspaces/{workspace}/indexes/test-index"] = TransportResponse(
            status_code=200, json=index_response, text=json.dumps(index_response)
        )

        resource = IndexResource(fake_client, workspace)
        result = await resource.update(
            index_name="test-index", updated_index_name="new-name", yaml_config="new: config"
        )

        assert isinstance(result, Index)
        assert result.name == "test-index"

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["method"] == "PATCH"
        assert last_request["data"] == {"name": "new-name", "config_yaml": "new: config"}

    async def test_update_index_without_changes_fails(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test that updating an index without any changes raises ValueError."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(ValueError, match="At least one of updated_index_name or yaml_config must be provided"):
            await resource.update(index_name="test-index")

    async def test_create_index_invalid_request(
        self, fake_client: BaseFakeClient, workspace: str, fake_create_400_response: None
    ) -> None:
        """Test that creating an index with invalid parameters raises an error."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(BadRequestError):
            await resource.create(index_name="invalid-index", yaml_config="invalid: yaml")

    async def test_update_nonexistent_index(
        self, fake_client: BaseFakeClient, workspace: str, fake_update_404_response: None
    ) -> None:
        """Test that updating a nonexistent index raises ResourceNotFoundError."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(ResourceNotFoundError):
            await resource.update(index_name="nonexistent-index", updated_index_name="new-name")

    async def test_update_index_invalid_config(
        self, fake_client: BaseFakeClient, workspace: str, fake_update_400_response: None
    ) -> None:
        """Test that updating an index with invalid configuration raises an error."""
        resource = IndexResource(fake_client, workspace)
        with pytest.raises(BadRequestError):
            await resource.update(index_name="invalid-index", yaml_config="invalid: yaml")

    async def test_delete_index_successful(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deleting an index successfully."""
        fake_client.responses[f"/v1/workspaces/{workspace}/indexes/test-index"] = TransportResponse(
            status_code=204, json={}, text=""
        )

        resource = IndexResource(fake_client, workspace)
        await resource.delete("test-index")

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["method"] == "DELETE"
        assert last_request["endpoint"] == f"/v1/workspaces/{workspace}/indexes/test-index"

    async def test_delete_nonexistent_index_raises_404(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test that deleting a nonexistent index raises ResourceNotFoundError."""
        fake_client.responses[f"/v1/workspaces/{workspace}/indexes/nonexistent-index"] = TransportResponse(
            status_code=404,
            json={"detail": "Index not found"},
            text=json.dumps({"detail": "Index not found"}),
        )

        resource = IndexResource(fake_client, workspace)
        with pytest.raises(ResourceNotFoundError):
            await resource.delete("nonexistent-index")

    async def test_delete_server_error_raises_500(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test that server error during delete raises UnexpectedAPIError."""
        fake_client.responses[f"/v1/workspaces/{workspace}/indexes/server-error-index"] = TransportResponse(
            status_code=500,
            json={"detail": "Internal server error"},
            text=json.dumps({"detail": "Internal server error"}),
        )

        resource = IndexResource(fake_client, workspace)
        with pytest.raises(UnexpectedAPIError):
            await resource.delete("server-error-index")

    async def test_deploy_index_success(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test successful index deployment."""
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = TransportResponse(
            status_code=200, json={"status": "success"}, text='{"status": "success"}'
        )

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="test-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

        # Verify request
        last_request = fake_client.requests[-1]
        assert last_request["endpoint"] == f"v1/workspaces/{workspace}/indexes/test-index/deploy"
        assert last_request["method"] == "POST"

    async def test_deploy_index_with_validation_errors(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with validation errors (422)."""
        validation_errors = {
            "details": [
                {"code": "invalid_config", "message": "Index configuration is invalid"},
                {"code": "missing_dependency", "message": "Required dependency not found"},
            ]
        }

        transport_response = TransportResponse(text="", status_code=422, json=validation_errors)
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = transport_response

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="test-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 2
        assert result.errors[0].code == "invalid_config"
        assert result.errors[0].message == "Index configuration is invalid"
        assert result.errors[1].code == "missing_dependency"
        assert result.errors[1].message == "Required dependency not found"

    async def test_deploy_index_with_400_error(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with 400 error."""
        error_response = TransportResponse(
            text="Bad request: invalid parameters", status_code=400, json={"detail": "Bad request"}
        )
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = error_response

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="test-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "Bad request: invalid parameters"

    async def test_deploy_index_with_404_error(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with 404 error (index not found)."""
        error_response = TransportResponse(text="Index not found", status_code=404, json={"detail": "Index not found"})
        fake_client.responses[f"{workspace}/indexes/nonexistent-index/deploy"] = error_response

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="nonexistent-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "Index not found"

    async def test_deploy_index_with_424_error(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with 424 error (failed dependency)."""
        error_response = TransportResponse(
            text="Failed dependency", status_code=424, json={"detail": "Failed dependency"}
        )
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = error_response

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="test-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "Failed dependency"

    async def test_deploy_index_with_500_error(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with 500 error (unexpected error)."""
        error_response = TransportResponse(
            text="Internal server error", status_code=500, json={"detail": "Internal server error"}
        )
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = error_response

        resource = IndexResource(fake_client, workspace)

        # Run the deployment and expect an exception
        with pytest.raises(UnexpectedAPIError):
            await resource.deploy(index_name="test-index")

    async def test_deploy_index_with_empty_error_text(self, fake_client: BaseFakeClient, workspace: str) -> None:
        """Test deployment with error response but empty text."""
        error_response = TransportResponse(text="", status_code=400, json={"detail": "Bad request"})
        fake_client.responses[f"{workspace}/indexes/test-index/deploy"] = error_response

        resource = IndexResource(fake_client, workspace)
        result = await resource.deploy(index_name="test-index")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "HTTP 400 error"

    async def test_list_indexes_default_params(self) -> None:
        """Test listing indexes with default parameters."""
        # Create sample data
        sample_indexes = [
            create_sample_index(pipeline_index_id="1", name="Index 1"),
            create_sample_index(pipeline_index_id="2", name="Index 2"),
        ]

        # Create client with predefined response
        client = DummyIndexClient(
            responses={
                "test-workspace/indexes": {
                    "data": sample_indexes,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Create resource and call list method
        resource = IndexResource(client=client, workspace="test-workspace")
        result = await resource.list()

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert isinstance(result.data[0], Index)
        assert result.data[0].pipeline_index_id == "1"
        assert result.data[0].name == "Index 1"

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/indexes"
        assert client.requests[0]["method"] == "GET"
        assert client.requests[0]["params"] == {"limit": 10}

    async def test_list_indexes_with_pagination(self) -> None:
        """Test listing indexes with custom pagination parameters."""
        # Create sample data
        sample_indexes = [
            create_sample_index(pipeline_index_id="3", name="Index 3"),
            create_sample_index(pipeline_index_id="4", name="Index 4"),
        ]

        # Create client with predefined response
        client = DummyIndexClient(
            responses={
                "test-workspace/indexes": {
                    "data": sample_indexes,
                    "has_more": False,
                    "total": 10,
                }
            }
        )

        # Create resource and call list method with pagination
        resource = IndexResource(client=client, workspace="test-workspace")
        result = await resource.list(limit=5, after="some_cursor")

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.data[0].pipeline_index_id == "3"
        assert result.data[1].pipeline_index_id == "4"

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/indexes"
        # TODO: change to after when problem with deepset API pagination is fixed
        assert client.requests[0]["params"] == {"limit": 5, "before": "some_cursor"}

    async def test_list_indexes_empty_result(self) -> None:
        """Test listing indexes when there are no indexes."""
        # Create client with empty response
        client = DummyIndexClient(responses={"test-workspace/indexes": {"data": [], "has_more": False, "total": 0}})

        # Create resource and call list method
        resource = IndexResource(client=client, workspace="test-workspace")
        result = await resource.list()

        # Verify empty results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0

    async def test_list_indexes_cursor_population(self) -> None:
        """Test that cursors are properly populated from index IDs."""
        # Create sample data
        all_indexes = [create_sample_index(pipeline_index_id=f"index-{i}", name=f"Index {i}") for i in range(3)]

        # Create a client with index data
        client = DummyIndexClient()
        client.set_index_data(all_indexes)

        # Create resource and test different scenarios
        resource = IndexResource(client=client, workspace="test-workspace")

        # Test first page with more data available
        first_page = await resource.list(limit=2)
        assert first_page.next_cursor == "index-1"  # Last element, since has_more=True
        assert first_page.has_more is True

        # Test last page (no more data)
        last_page = await resource.list(limit=5)  # Request more than available
        assert last_page.next_cursor is None  # No next cursor since has_more=False
        assert last_page.has_more is False

        # Test single item page
        client.set_index_data([all_indexes[0]])  # Only one index
        single_page = await resource.list(limit=10)
        assert single_page.next_cursor is None  # No next cursor since has_more=False
        assert single_page.has_more is False
