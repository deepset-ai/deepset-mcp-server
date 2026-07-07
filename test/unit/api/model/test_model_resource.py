# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from typing import Any

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import ModelList, ModelOrigin
from deepset_mcp.api.model.resource import ModelResource
from deepset_mcp.api.workspace.models import Workspace
from deepset_mcp.api.workspace.protocols import WorkspaceResourceProtocol
from test.unit.conftest import BaseFakeClient

WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MODEL_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class FakeWorkspaceResource(WorkspaceResourceProtocol):
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def list(self) -> list[Workspace]:
        return [self._workspace]

    async def get(self, workspace_name: str) -> Workspace:
        return self._workspace

    async def create(self, name: str) -> Any:
        raise NotImplementedError

    async def delete(self, workspace_name: str) -> Any:
        raise NotImplementedError


class FakeModelClient(BaseFakeClient):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        super().__init__(responses)
        self._workspace = Workspace(
            name="my-workspace",
            workspace_id=WORKSPACE_ID,
            languages={},
            default_idle_timeout_in_seconds=300,
        )

    def workspaces(self) -> WorkspaceResourceProtocol:
        return FakeWorkspaceResource(self._workspace)


def _model_data() -> dict[str, Any]:
    return {
        "model_id": str(MODEL_ID),
        "name": "gpt-4o",
        "provider": "openai",
        "connected": True,
        "origin": ModelOrigin.PLATFORM.value,
        "chat_generator_config": {"type": "OpenAIChatGenerator"},
        "generation_kwargs": {},
    }


@pytest.mark.asyncio
async def test_list_models() -> None:
    """Test listing models for a workspace."""
    mock_data = {"data": [_model_data()], "has_more": False, "total": 1}
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": mock_data})

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list()

    assert isinstance(result, ModelList)
    assert len(result.data) == 1
    assert result.data[0].name == "gpt-4o"
    assert result.data[0].provider == "openai"
    assert result.data[0].model_id == MODEL_ID
    assert result.has_more is False
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_models_with_params() -> None:
    """Test listing models forwards limit, page_number, and connected as query params."""
    mock_data = {"data": [], "has_more": False, "total": 0}
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": mock_data})

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    await resource.list(limit=5, page_number=2, connected=True)

    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request["endpoint"] == f"v2/workspaces/{WORKSPACE_ID}/models"
    assert request["method"] == "GET"
    assert request["params"] == {"limit": 5, "page_number": 2, "connected": True}


@pytest.mark.asyncio
async def test_list_models_empty() -> None:
    """Test listing models when none exist."""
    mock_data = {"data": [], "has_more": False, "total": 0}
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": mock_data})

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list()

    assert isinstance(result, ModelList)
    assert result.data == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_models_empty_response_raises() -> None:
    """Test that an empty response body raises UnexpectedAPIError."""
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": None})

    resource = ModelResource(client=fake_client, workspace="my-workspace")

    with pytest.raises(UnexpectedAPIError):
        await resource.list()


@pytest.mark.asyncio
async def test_list_models_workspace_not_found() -> None:
    """Test that a missing workspace propagates as ResourceNotFoundError."""

    class NotFoundWorkspaceClient(BaseFakeClient):
        def workspaces(self) -> WorkspaceResourceProtocol:
            class _Raiser(WorkspaceResourceProtocol):
                async def list(self) -> list[Workspace]:
                    raise NotImplementedError

                async def get(self, workspace_name: str) -> Workspace:
                    raise ResourceNotFoundError(f"There is no workspace named '{workspace_name}'.")

                async def create(self, name: str) -> Any:
                    raise NotImplementedError

                async def delete(self, workspace_name: str) -> Any:
                    raise NotImplementedError

            return _Raiser()

    fake_client = NotFoundWorkspaceClient()
    resource = ModelResource(client=fake_client, workspace="missing-workspace")

    with pytest.raises(ResourceNotFoundError):
        await resource.list()
