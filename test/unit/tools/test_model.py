# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import Model, ModelList, ModelOrigin
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
    ) -> ModelList:
        self.last_call_kwargs = {"limit": limit, "page_number": page_number, "connected": connected}
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
    """Test that limit, page_number, and connected are forwarded to the resource."""
    fake_resource = FakeModelResource(list_response=ModelList(data=[], has_more=False, total=0))
    client = FakeClient(model_resource=fake_resource)

    await get_models(client=client, workspace="my-workspace", limit=5, page_number=2, connected=False)

    assert fake_resource.last_call_kwargs == {"limit": 5, "page_number": 2, "connected": False}


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
