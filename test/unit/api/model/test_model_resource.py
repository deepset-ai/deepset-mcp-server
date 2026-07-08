# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from typing import Any

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import ModelList, ModelOrigin, ModelProvider
from deepset_mcp.api.model.resource import ModelResource
from deepset_mcp.api.transport import TransportResponse
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


def _model_data(
    *,
    model_id: uuid.UUID = MODEL_ID,
    name: str = "gpt-4o",
    provider: str = "openai",
    chat_model_name: str | None = "gpt-4o",
) -> dict[str, Any]:
    init_parameters: dict[str, Any] = {"model": chat_model_name} if chat_model_name is not None else {}
    return {
        "model_id": str(model_id),
        "name": name,
        "provider": provider,
        "connected": True,
        "origin": ModelOrigin.PLATFORM.value,
        "chat_generator_config": {"type": "OpenAIChatGenerator", "init_parameters": init_parameters},
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
    assert result.data[0].model == "gpt-4o"
    assert result.data[0].model_id == MODEL_ID
    assert result.has_more is False
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_models_infers_model_from_chat_generator_config() -> None:
    """Test that Model.model is populated from chat_generator_config.init_parameters.model."""
    mock_data = {
        "data": [_model_data(chat_model_name="gpt-4o-mini")],
        "has_more": False,
        "total": 1,
    }
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": mock_data})

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list()

    assert result.data[0].model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_list_models_model_is_none_without_init_parameters() -> None:
    """Test that Model.model stays None when chat_generator_config has no matching init parameter."""
    mock_data = {
        "data": [_model_data(chat_model_name=None)],
        "has_more": False,
        "total": 1,
    }
    fake_client = FakeModelClient(responses={f"v2/workspaces/{WORKSPACE_ID}/models": mock_data})

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list()

    assert result.data[0].model is None


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


class PaginatedFakeModelClient(FakeModelClient):
    """Fake client that serves models from a fixed list, paginated by `page_number`."""

    def __init__(self, all_models: list[dict[str, Any]], page_size: int) -> None:
        super().__init__()
        self._all_models = all_models
        self._page_size = page_size

    async def request(self, endpoint: str, **kwargs: Any) -> TransportResponse[Any]:
        self.requests.append({"endpoint": endpoint, **kwargs})

        params = kwargs.get("params", {})
        page_number = params.get("page_number", 1)
        start = (page_number - 1) * self._page_size
        end = start + self._page_size
        page_data = self._all_models[start:end]

        payload = {"data": page_data, "has_more": end < len(self._all_models), "total": len(self._all_models)}
        return TransportResponse(text="", status_code=200, json=payload)


@pytest.mark.asyncio
async def test_list_models_filter_by_provider() -> None:
    """Test filtering models by provider (case-insensitive, exact match)."""
    all_models = [
        _model_data(model_id=uuid.uuid4(), provider="openai", name="gpt-4o"),
        _model_data(model_id=uuid.uuid4(), provider="cohere", name="command-r"),
    ]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(provider="OpenAI")

    assert [m.name for m in result.data] == ["gpt-4o"]
    assert result.total == 1
    assert result.has_more is False


@pytest.mark.asyncio
async def test_list_models_filter_by_provider_enum() -> None:
    """Test filtering models by provider using the ModelProvider enum."""
    all_models = [
        _model_data(model_id=uuid.uuid4(), provider="anthropic", name="claude-3-opus"),
        _model_data(model_id=uuid.uuid4(), provider="cohere", name="command-r"),
    ]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(provider=ModelProvider.ANTHROPIC)

    assert [m.name for m in result.data] == ["claude-3-opus"]
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_models_filter_by_provider_not_in_enum() -> None:
    """Test that provider filtering also accepts providers outside the ModelProvider enum."""
    all_models = [
        _model_data(model_id=uuid.uuid4(), provider="cohere", name="command-r"),
        _model_data(model_id=uuid.uuid4(), provider="openai", name="gpt-4o"),
    ]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(provider="cohere")

    assert [m.name for m in result.data] == ["command-r"]
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_models_filter_by_model_name() -> None:
    """Test filtering models by chat_generator_config.init_parameters.model substring."""
    all_models = [
        _model_data(model_id=uuid.uuid4(), name="gpt-4o", chat_model_name="gpt-4o"),
        _model_data(model_id=uuid.uuid4(), name="gpt-4o-mini", chat_model_name="gpt-4o-mini"),
        _model_data(model_id=uuid.uuid4(), name="command-r", provider="cohere", chat_model_name="command-r"),
    ]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(model="gpt-4o")

    assert {m.name for m in result.data} == {"gpt-4o", "gpt-4o-mini"}
    assert result.total == 2


@pytest.mark.asyncio
async def test_list_models_filter_ignores_models_without_model_name() -> None:
    """Test that models without an init_parameters.model value never match a model-name filter."""
    all_models = [
        _model_data(model_id=uuid.uuid4(), name="custom", chat_model_name=None),
    ]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(model="anything")

    assert result.data == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_models_filter_aggregates_across_api_pages() -> None:
    """Test that filtering fetches every API page before filtering, not just the first."""
    all_models = [_model_data(model_id=uuid.uuid4(), name=f"model-{i}", provider="openai") for i in range(5)]
    all_models.append(_model_data(model_id=uuid.uuid4(), name="command-r", provider="cohere"))
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=2)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(provider="cohere")

    assert len(fake_client.requests) == 3  # 6 models / page_size 2
    assert [m.name for m in result.data] == ["command-r"]
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_models_filter_paginates_filtered_results() -> None:
    """Test that limit/page_number slice the filtered result set, not the raw API pages."""
    all_models = [_model_data(model_id=uuid.uuid4(), name=f"gpt-{i}", provider="openai") for i in range(5)]
    fake_client = PaginatedFakeModelClient(all_models=all_models, page_size=100)

    resource = ModelResource(client=fake_client, workspace="my-workspace")
    result = await resource.list(provider="openai", limit=2, page_number=2)

    assert [m.name for m in result.data] == ["gpt-2", "gpt-3"]
    assert result.total == 5
    assert result.has_more is True
