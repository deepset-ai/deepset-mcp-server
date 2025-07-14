# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from uuid import UUID

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList
from deepset_mcp.api.workspace.protocols import WorkspaceResourceProtocol
from deepset_mcp.tools.workspace import create_workspace, get_workspace, list_workspaces
from test.unit.conftest import BaseFakeClient


class FakeWorkspaceResource(WorkspaceResourceProtocol):
    """Fake workspace resource for testing."""

    def __init__(
        self,
        list_response: list[Workspace] | None = None,
        get_response: Workspace | None = None,
        create_response: NoContentResponse | None = None,
        delete_response: NoContentResponse | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
        create_exception: Exception | None = None,
        delete_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._create_response = create_response
        self._delete_response = delete_response
        self._list_exception = list_exception
        self._get_exception = get_exception
        self._create_exception = create_exception
        self._delete_exception = delete_exception

    async def list(self) -> WorkspaceList:
        """List all workspaces."""
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return WorkspaceList(data=self._list_response, has_more=False, total=len(self._list_response))
        raise NotImplementedError

    async def get(self, workspace_name: str) -> Workspace:
        """Get a specific workspace by name."""
        if self._get_exception:
            raise self._get_exception
        if self._get_response is not None:
            return self._get_response
        raise NotImplementedError

    async def create(self, name: str) -> NoContentResponse:
        """Create a new workspace."""
        if self._create_exception:
            raise self._create_exception
        if self._create_response is not None:
            return self._create_response
        raise NotImplementedError

    async def delete(self, workspace_name: str) -> NoContentResponse:
        """Delete a workspace."""
        if self._delete_exception:
            raise self._delete_exception
        if self._delete_response is not None:
            return self._delete_response
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    """Fake client for testing workspace tools."""

    def __init__(self, resource: FakeWorkspaceResource) -> None:
        self._resource = resource
        super().__init__()

    def workspaces(self) -> WorkspaceResourceProtocol:
        return self._resource


@pytest.mark.asyncio
async def test_list_workspaces_returns_workspace_list() -> None:
    """Test that list_workspaces returns a list of workspaces."""
    workspace1 = Workspace(
        name="workspace1",
        workspace_id=UUID("11111111-1111-1111-1111-111111111111"),
        languages={"en": "English"},
        default_idle_timeout_in_seconds=3600,
    )
    workspace2 = Workspace(
        name="workspace2",
        workspace_id=UUID("22222222-2222-2222-2222-222222222222"),
        languages={"en": "English", "de": "German"},
        default_idle_timeout_in_seconds=7200,
    )
    resource = FakeWorkspaceResource(list_response=[workspace1, workspace2])
    client = FakeClient(resource)

    result = await list_workspaces(client=client)

    assert isinstance(result, WorkspaceList)
    assert len(result.data) == 2
    assert result.data[0].name == "workspace1"
    assert result.data[1].name == "workspace2"
    assert result.total == 2
    assert result.has_more is False


@pytest.mark.asyncio
async def test_list_workspaces_handles_bad_request_error() -> None:
    """Test that list_workspaces handles BadRequestError."""
    resource = FakeWorkspaceResource(list_exception=BadRequestError("Invalid request"))
    client = FakeClient(resource)

    result = await list_workspaces(client=client)

    assert isinstance(result, str)
    assert "Failed to list workspaces: Invalid request" in result


@pytest.mark.asyncio
async def test_list_workspaces_handles_unexpected_api_error() -> None:
    """Test that list_workspaces handles UnexpectedAPIError."""
    resource = FakeWorkspaceResource(
        list_exception=UnexpectedAPIError(status_code=500, message="Internal server error")
    )
    client = FakeClient(resource)

    result = await list_workspaces(client=client)

    assert isinstance(result, str)
    assert "Failed to list workspaces: Internal server error" in result


@pytest.mark.asyncio
async def test_get_workspace_returns_workspace() -> None:
    """Test that get_workspace returns a workspace object."""
    workspace = Workspace(
        name="test-workspace",
        workspace_id=UUID("12345678-1234-1234-1234-123456789012"),
        languages={"en": "English", "fr": "French"},
        default_idle_timeout_in_seconds=1800,
    )
    resource = FakeWorkspaceResource(get_response=workspace)
    client = FakeClient(resource)

    result = await get_workspace(client=client, workspace_name="test-workspace")

    assert isinstance(result, Workspace)
    assert result.name == "test-workspace"
    assert result.workspace_id == UUID("12345678-1234-1234-1234-123456789012")
    assert result.languages == {"en": "English", "fr": "French"}
    assert result.default_idle_timeout_in_seconds == 1800


@pytest.mark.asyncio
async def test_get_workspace_handles_resource_not_found() -> None:
    """Test that get_workspace handles ResourceNotFoundError."""
    resource = FakeWorkspaceResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)

    result = await get_workspace(client=client, workspace_name="missing-workspace")

    assert isinstance(result, str)
    assert result == "There is no workspace named 'missing-workspace'."


@pytest.mark.asyncio
async def test_get_workspace_handles_bad_request_error() -> None:
    """Test that get_workspace handles BadRequestError."""
    resource = FakeWorkspaceResource(get_exception=BadRequestError("Invalid workspace name"))
    client = FakeClient(resource)

    result = await get_workspace(client=client, workspace_name="invalid-name")

    assert isinstance(result, str)
    assert "Failed to fetch workspace 'invalid-name': Invalid workspace name" in result


@pytest.mark.asyncio
async def test_get_workspace_handles_unexpected_api_error() -> None:
    """Test that get_workspace handles UnexpectedAPIError."""
    resource = FakeWorkspaceResource(get_exception=UnexpectedAPIError(status_code=503, message="Service unavailable"))
    client = FakeClient(resource)

    result = await get_workspace(client=client, workspace_name="test-workspace")

    assert isinstance(result, str)
    assert "Failed to fetch workspace 'test-workspace': Service unavailable" in result


@pytest.mark.asyncio
async def test_create_workspace_returns_success_response() -> None:
    """Test that create_workspace returns a success response."""
    success_response = NoContentResponse(message="Workspace created successfully.")
    resource = FakeWorkspaceResource(create_response=success_response)
    client = FakeClient(resource)

    result = await create_workspace(client=client, name="new-workspace")

    assert isinstance(result, NoContentResponse)
    assert result.message == "Workspace created successfully."


@pytest.mark.asyncio
async def test_create_workspace_handles_bad_request_error() -> None:
    """Test that create_workspace handles BadRequestError."""
    resource = FakeWorkspaceResource(create_exception=BadRequestError("Workspace name already exists"))
    client = FakeClient(resource)

    result = await create_workspace(client=client, name="existing-workspace")

    assert isinstance(result, str)
    assert "Failed to create workspace 'existing-workspace': Workspace name already exists" in result


@pytest.mark.asyncio
async def test_create_workspace_handles_unexpected_api_error() -> None:
    """Test that create_workspace handles UnexpectedAPIError."""
    resource = FakeWorkspaceResource(create_exception=UnexpectedAPIError(status_code=500, message="Database error"))
    client = FakeClient(resource)

    result = await create_workspace(client=client, name="test-workspace")

    assert isinstance(result, str)
    assert "Failed to create workspace 'test-workspace': Database error" in result


@pytest.mark.asyncio
async def test_list_workspaces_empty_response() -> None:
    """Test that list_workspaces handles empty workspace list."""
    resource = FakeWorkspaceResource(list_response=[])
    client = FakeClient(resource)

    result = await list_workspaces(client=client)

    assert isinstance(result, WorkspaceList)
    assert len(result.data) == 0
    assert result.total == 0
    assert result.has_more is False
