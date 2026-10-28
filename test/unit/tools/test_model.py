# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import Model, ModelList, ModelOrigin, ModelProvider
from deepset_mcp.api.model.protocols import ModelResourceProtocol
from deepset_mcp.tools.model import get_models
from test.unit.conftest import BaseFakeClient


class FakeModelResource(ModelResourceProtocol):
    def __init__(
        self,
        list_response: ModelList | None = None,
        list_exception: Exception | None = None,
    ) -> None:
        self.list_response = list_response
        self.list_exception = list_exception
        self.last_call_kwargs: dict[str, object] = {}

    async def list(
        self,
        limit: int = 100,
        page_number: int = 1,
        connected: bool | None = None,
        provider: ModelProvider | str | None = None,
        model: str | None = None,
        include_price: bool = False,
    ) -> ModelList:
        self.last_call_kwargs = {
            "limit": limit,
            "page_number": page_number,
            "connected": connected,
            "provider": provider,
            "model": model,
            "include_price": include_price,
        }
        if self.list_exception:
            raise self.list_exception
        if self.list_response is None:
            return ModelList(data=[], has_more=False, total=0)
        return self.list_response


class FakeClient(BaseFakeClient):
    def __init__(self, model_resource: FakeModelResource | None = None) -> None:
        super().__init__()
        self._model_resource = model_resource or FakeModelResource()

    def models(self, workspace: str) -> ModelResourceProtocol:
        return self._model_resource


def _model() -> Model:
    return Model(
        model_id=uuid.uuid4(),
        name="gpt-4o",
        provider="openai",
        connected=True,
        origin=ModelOrigin.PLATFORM,
        chat_generator_config={"type": "OpenAIChatGenerator"},
        generation_kwargs={},
    )


@pytest.mark.asyncio
async def test_get_models_success() -> None:
    """Test successful retrieval of models for a workspace."""
    model_list = ModelList(data=[_model()], has_more=False, total=1)
    client = FakeClient(model_resource=FakeModelResource(list_response=model_list))

    result = await get_models(client=client, workspace="my-workspace")

    assert isinstance(result, ModelList)
    assert len(result.data) == 1
    assert result.data[0].name == "gpt-4o"


@pytest.mark.asyncio
async def test_get_models_forwards_params() -> None:
    """Test that limit, page_number, connected, provider, and model are forwarded to the resource."""
    fake_resource = FakeModelResource(list_response=ModelList(data=[], has_more=False, total=0))
    client = FakeClient(model_resource=fake_resource)

    await get_models(
        client=client,
        workspace="my-workspace",
        limit=5,
        page_number=2,
        connected=False,
        provider="openai",
        model="gpt-4o",
        include_price=True,
    )

    assert fake_resource.last_call_kwargs == {
        "limit": 5,
        "page_number": 2,
        "connected": False,
        "provider": "openai",
        "model": "gpt-4o",
        "include_price": True,
    }


@pytest.mark.asyncio
async def test_get_models_does_not_request_prices_by_default() -> None:
    """Test that prices are only requested when asked for."""
    fake_resource = FakeModelResource(list_response=ModelList(data=[], has_more=False, total=0))

    await get_models(client=FakeClient(model_resource=fake_resource), workspace="my-workspace")

    assert fake_resource.last_call_kwargs["include_price"] is False


@pytest.mark.asyncio
async def test_get_models_include_price_forbidden_explains_missing_costs_access() -> None:
    """Test that a 403 on prices points to the missing costs access and to the call without prices."""
    client = FakeClient(model_resource=FakeModelResource(list_exception=UnexpectedAPIError(403, "Forbidden")))

    result = await get_models(client=client, workspace="my-workspace", include_price=True)

    assert isinstance(result, str)
    assert "read access to costs" in result
    assert "without include_price" in result


@pytest.mark.asyncio
async def test_get_models_forbidden_without_prices_is_a_plain_failure() -> None:
    """Test that a 403 that is not about prices keeps the generic message."""
    client = FakeClient(model_resource=FakeModelResource(list_exception=UnexpectedAPIError(403, "Forbidden")))

    result = await get_models(client=client, workspace="my-workspace")

    assert result == "Failed to list models: Forbidden (Status Code: 403)"


@pytest.mark.asyncio
async def test_get_models_forwards_provider_enum() -> None:
    """Test that a ModelProvider enum value is forwarded to the resource as-is."""
    fake_resource = FakeModelResource(list_response=ModelList(data=[], has_more=False, total=0))
    client = FakeClient(model_resource=fake_resource)

    await get_models(client=client, workspace="my-workspace", provider=ModelProvider.ANTHROPIC)

    assert fake_resource.last_call_kwargs["provider"] == ModelProvider.ANTHROPIC


@pytest.mark.asyncio
async def test_get_models_workspace_not_found() -> None:
    """Test that a missing workspace returns a friendly error message."""
    client = FakeClient(model_resource=FakeModelResource(list_exception=ResourceNotFoundError("Workspace not found")))

    result = await get_models(client=client, workspace="missing-workspace")

    assert result == "There is no workspace named 'missing-workspace'. Did you mean to configure it?"


@pytest.mark.asyncio
async def test_get_models_bad_request() -> None:
    """Test that a bad request error is surfaced as a string message."""
    client = FakeClient(model_resource=FakeModelResource(list_exception=BadRequestError("Invalid params")))

    result = await get_models(client=client, workspace="my-workspace")

    assert result == "Failed to list models: Invalid params (Status Code: 400)"


@pytest.mark.asyncio
async def test_get_models_unexpected_api_error() -> None:
    """Test that an unexpected API error is surfaced as a string message."""
    client = FakeClient(model_resource=FakeModelResource(list_exception=UnexpectedAPIError(500, "Server error")))

    result = await get_models(client=client, workspace="my-workspace")

    assert result == "Failed to list models: Server error (Status Code: 500)"
