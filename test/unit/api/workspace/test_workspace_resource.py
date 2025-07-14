# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for WorkspaceResource."""

from uuid import UUID

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList
from deepset_mcp.api.workspace.resource import WorkspaceResource
from test.unit.conftest import BaseFakeClient


class TestWorkspaceResourceList:
    """Test cases for WorkspaceResource.list method."""

    @pytest.mark.asyncio
    async def test_list_success(self) -> None:
        """Test successful workspace listing."""
        # Arrange
        mock_response = [
            {
                "name": "copilot-testing",
                "workspace_id": "76d361b5-a551-40e3-a5c9-fdbc20028021",
                "languages": {},
                "default_idle_timeout_in_seconds": 43200,
            },
            {
                "name": "default",
                "workspace_id": "91ee7798-004d-4808-906a-1777ea262d1c",
                "languages": {},
                "default_idle_timeout_in_seconds": 43200,
            },
        ]

        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces": mock_response})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.list()

        # Assert
        assert isinstance(result, WorkspaceList)
        assert len(result.data) == 2
        assert result.total == 2
        assert not result.has_more

        # Check first workspace
        assert result.data[0].name == "copilot-testing"
        assert result.data[0].workspace_id == UUID("76d361b5-a551-40e3-a5c9-fdbc20028021")
        assert result.data[0].languages == {}
        assert result.data[0].default_idle_timeout_in_seconds == 43200

        # Check second workspace
        assert result.data[1].name == "default"
        assert result.data[1].workspace_id == UUID("91ee7798-004d-4808-906a-1777ea262d1c")
        assert result.data[1].languages == {}
        assert result.data[1].default_idle_timeout_in_seconds == 43200

        # Verify request was made correctly
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_list_empty_response(self) -> None:
        """Test handling of empty workspace list."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces": []})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.list()

        # Assert
        assert isinstance(result, WorkspaceList)
        assert len(result.data) == 0
        assert result.total == 0
        assert not result.has_more

    @pytest.mark.asyncio
    async def test_list_null_response(self) -> None:
        """Test handling of null JSON response."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces": TransportResponse(text="", status_code=200, json=None)})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.list()

        # Assert
        assert isinstance(result, WorkspaceList)
        assert len(result.data) == 0
        assert result.total == 0
        assert not result.has_more

    @pytest.mark.asyncio
    async def test_list_error_response(self) -> None:
        """Test handling of error response."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(
                    responses={"v1/workspaces": TransportResponse(text="Internal Server Error", status_code=500)}
                )

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act & Assert
        with pytest.raises(UnexpectedAPIError):
            await resource.list()


class TestWorkspaceResourceGet:
    """Test cases for WorkspaceResource.get method."""

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        """Test successful workspace retrieval."""
        # Arrange
        mock_response = {
            "name": "copilot-testing",
            "workspace_id": "76d361b5-a551-40e3-a5c9-fdbc20028021",
            "languages": {"en": {}},
            "default_idle_timeout_in_seconds": 43200,
        }

        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces/copilot-testing": mock_response})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.get("copilot-testing")

        # Assert
        assert isinstance(result, Workspace)
        assert result.name == "copilot-testing"
        assert result.workspace_id == UUID("76d361b5-a551-40e3-a5c9-fdbc20028021")
        assert result.languages == {"en": {}}
        assert result.default_idle_timeout_in_seconds == 43200

        # Verify request was made correctly
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/copilot-testing"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_get_not_found(self) -> None:
        """Test handling of workspace not found."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(
                    responses={"v1/workspaces/nonexistent": TransportResponse(text="Not Found", status_code=404)}
                )

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await resource.get("nonexistent")


class TestWorkspaceResourceCreate:
    """Test cases for WorkspaceResource.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self) -> None:
        """Test successful workspace creation."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces": TransportResponse(text="", status_code=201)})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.create("new-workspace")

        # Assert
        assert isinstance(result, NoContentResponse)
        assert result.success is True
        assert result.message == "Workspace created successfully."

        # Verify request was made correctly
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0]["data"] == {"name": "new-workspace"}

    @pytest.mark.asyncio
    async def test_create_error(self) -> None:
        """Test handling of creation error."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(responses={"v1/workspaces": TransportResponse(text="Bad Request", status_code=400)})

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act & Assert
        with pytest.raises(BadRequestError):
            await resource.create("invalid-workspace")


class TestWorkspaceResourceDelete:
    """Test cases for WorkspaceResource.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self) -> None:
        """Test successful workspace deletion."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(
                    responses={"v1/workspaces/test-workspace": TransportResponse(text="", status_code=204)}
                )

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act
        result = await resource.delete("test-workspace")

        # Assert
        assert isinstance(result, NoContentResponse)
        assert result.success is True
        assert result.message == "Workspace deleted successfully."

        # Verify request was made correctly
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace"
        assert client.requests[0]["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        """Test handling of workspace not found during deletion."""

        # Arrange
        class FakeWorkspaceClient(BaseFakeClient):
            def __init__(self) -> None:
                super().__init__(
                    responses={"v1/workspaces/nonexistent": TransportResponse(text="Not Found", status_code=404)}
                )

            def workspaces(self) -> WorkspaceResource:
                return WorkspaceResource(client=self)

        client = FakeWorkspaceClient()
        resource = client.workspaces()

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await resource.delete("nonexistent")
