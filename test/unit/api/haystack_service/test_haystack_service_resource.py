# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.haystack_service.resource import HaystackServiceResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


@pytest.fixture
def mock_client() -> BaseFakeClient:
    return BaseFakeClient()


def make_component_schema_response() -> dict[str, Any]:
    return {"component_schema": "Mock component schema"}


@pytest.fixture
def mock_successful_schema_response(mock_client: BaseFakeClient) -> None:
    """Configure the mock client to return a successful response."""
    mock_client.responses["haystack/components"] = TransportResponse(
        status_code=200,
        json=make_component_schema_response(),
        text=json.dumps(make_component_schema_response()),
    )


@pytest.fixture
def mock_schema_error_response(mock_client: BaseFakeClient) -> None:
    """Configure the mock client to return an error response."""
    mock_client.responses["haystack/components"] = TransportResponse(
        status_code=500,
        json={"message": "Internal server error"},
        text="Internal server error",
    )


@pytest.fixture
def mock_successful_io_response(mock_client: BaseFakeClient) -> None:
    mock_client.responses["v1/haystack/components/input-output"] = TransportResponse(
        status_code=200,
        json=[{"name": "Agent", "input": "Mock input", "output": "Mock output"}],
        text=json.dumps([{"name": "Agent", "input": "Mock input", "output": "Mock output"}]),
    )


@pytest.fixture
def mock_io_error_response(mock_client: BaseFakeClient) -> None:
    mock_client.responses["v1/haystack/components/input-output"] = TransportResponse(
        status_code=500,
        json={"message": "Internal server error"},
        text="Internal server error",
    )


def test_initialization(mock_client: BaseFakeClient) -> None:
    """Test HaystackServiceResource initialization."""
    resource = HaystackServiceResource(client=mock_client)
    assert resource._client == mock_client


@pytest.mark.asyncio
async def test_get_component_schema_success(
    mock_client: BaseFakeClient,
    mock_successful_schema_response: None,
) -> None:
    """Test successful component schema retrieval."""
    resource = HaystackServiceResource(client=mock_client)
    result = await resource.get_component_schemas()

    assert result == make_component_schema_response()
    assert mock_client.requests[-1] == {
        "method": "GET",
        "endpoint": "v1/haystack/components",
        "headers": {"accept": "application/json"},
        "data": {"domain": "deepset-cloud"},
    }


@pytest.mark.asyncio
async def test_get_component_schema_error(
    mock_client: BaseFakeClient,
    mock_schema_error_response: None,
) -> None:
    """Test error handling in component schema retrieval."""
    resource = HaystackServiceResource(client=mock_client)

    with pytest.raises(UnexpectedAPIError):
        await resource.get_component_schemas()


@pytest.mark.asyncio
async def test_get_component_input_output_success(
    mock_client: BaseFakeClient,
    mock_successful_io_response: None,
) -> None:
    resource = HaystackServiceResource(client=mock_client)
    result = await resource.get_component_input_output("Agent")

    assert result == {"name": "Agent", "input": "Mock input", "output": "Mock output"}


@pytest.mark.asyncio
async def test_get_component_input_output_error(
    mock_client: BaseFakeClient,
    mock_io_error_response: None,
) -> None:
    resource = HaystackServiceResource(client=mock_client)
    with pytest.raises(UnexpectedAPIError):
        await resource.get_component_input_output("Agent")
