from typing import Any

import pytest

from deepset_mcp.api.haystack_service.resource import HaystackServiceResource
from deepset_mcp.api.transport import TransportResponse
from tests.unit.api.conftest import MockAsyncClient


def make_component_schema_response() -> dict[str, Any]:
    return {
        "Crawler": {
            "type": "Crawler",
            "Base": "BaseComponent",
            "Description": "A component that crawls websites and creates Documents from them.",
            "Parameters": {
                "urls": {
                    "type": "list[str]",
                    "required": True,
                    "description": "List of URLs to crawl."
                }
            }
        }
    }


@pytest.fixture
def mock_successful_response(mock_client: MockAsyncClient) -> None:
    """Configure the mock client to return a successful response."""
    mock_client.responses.append(
        TransportResponse(
            status_code=200,
            json=make_component_schema_response(),
            text="",
            success=True,
        )
    )


@pytest.fixture
def mock_error_response(mock_client: MockAsyncClient) -> None:
    """Configure the mock client to return an error response."""
    mock_client.responses.append(
        TransportResponse(
            status_code=500,
            json={"message": "Internal server error"},
            text="Internal server error",
            success=False,
        )
    )


def test_initialization(mock_client: MockAsyncClient) -> None:
    """Test HaystackServiceResource initialization."""
    resource = HaystackServiceResource(client=mock_client)
    assert resource._client == mock_client


async def test_get_component_schema_success(
    mock_client: MockAsyncClient,
    mock_successful_response: None,
) -> None:
    """Test successful component schema retrieval."""
    resource = HaystackServiceResource(client=mock_client)
    result = await resource.get_component_schema()

    assert result == make_component_schema_response()
    assert mock_client.last_request == {
        "method": "GET",
        "endpoint": "v1/haystack/components",
        "headers": {"accept": "application/json"},
        "data": {"domain": "deepset-cloud"},
    }


async def test_get_component_schema_error(
    mock_client: MockAsyncClient,
    mock_error_response: None,
) -> None:
    """Test error handling in component schema retrieval."""
    resource = HaystackServiceResource(client=mock_client)
    with pytest.raises(Exception, match="Internal server error"):
        await resource.get_component_schema()
