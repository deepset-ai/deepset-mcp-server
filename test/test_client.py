import os
from typing import Any, AsyncIterator
from unittest import mock

import httpx
import pytest
from pytest import MonkeyPatch

from deepset_mcp.client import DeepsetClient, HttpClient, HttpxClient

# Test data
TEST_API_KEY = "test-api-key"
TEST_WORKSPACE = "test-workspace"
TEST_BASE_URL = "https://test-api.cloud.deepset.ai/api/v1"


# Custom mock HTTP client for testing moved to the client.py file
class MockHttpClient(HttpClient):
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        self.requests.append({"method": "GET", "url": url, "headers": headers, "params": params})
        key = f"GET {url}"
        if key in self.responses:
            return self.responses[key]
        # Default mock response
        mock_response = mock.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "{}"
        mock_response.json.return_value = {}
        return mock_response

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        self.requests.append({"method": "POST", "url": url, "headers": headers, "json": json, "data": data})
        key = f"POST {url}"
        if key in self.responses:
            return self.responses[key]
        # Default mock response
        mock_response = mock.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "{}"
        mock_response.json.return_value = {}
        return mock_response

    async def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        self.requests.append({"method": "PUT", "url": url, "headers": headers, "json": json, "data": data})
        key = f"PUT {url}"
        if key in self.responses:
            return self.responses[key]
        # Default mock response
        mock_response = mock.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "{}"
        mock_response.json.return_value = {}
        return mock_response


@pytest.fixture
def mock_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSET_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("DEEPSET_WORKSPACE", TEST_WORKSPACE)


@pytest.fixture
def mock_http_client() -> MockHttpClient:
    # Create custom responses for specific endpoints
    mock_responses = {}
    
    # Mock GET pipelines response
    pipelines_response = mock.Mock(spec=httpx.Response)
    pipelines_response.status_code = 200
    pipelines_response.text = '{"data": [{"id": "test-pipeline", "name": "Test Pipeline"}]}'
    pipelines_response.json.return_value = {"data": [{"id": "test-pipeline", "name": "Test Pipeline"}]}
    mock_responses[f"GET {TEST_BASE_URL}/workspaces/{TEST_WORKSPACE}/pipelines"] = pipelines_response
    
    return MockHttpClient(mock_responses)


@pytest.fixture
async def client(mock_env: None, mock_http_client: MockHttpClient) -> AsyncIterator[DeepsetClient]:
    client = DeepsetClient(
        api_key=TEST_API_KEY,
        workspace=TEST_WORKSPACE,
        base_url=TEST_BASE_URL,
        http_client=mock_http_client,
    )
    yield client


@pytest.mark.asyncio
async def test_client_initialization(mock_env: None) -> None:
    """Test that the client initializes correctly from environment variables."""
    client = DeepsetClient()
    assert client.api_key == TEST_API_KEY
    assert client.workspace == TEST_WORKSPACE
    assert client.base_url == "https://api.cloud.deepset.ai/api/v1"


@pytest.mark.asyncio
async def test_client_custom_initialization() -> None:
    """Test that the client can be initialized with custom values."""
    client = DeepsetClient(
        api_key="custom-key",
        workspace="custom-workspace",
        base_url="https://custom-url.com",
    )
    assert client.api_key == "custom-key"
    assert client.workspace == "custom-workspace"
    assert client.base_url == "https://custom-url.com"


@pytest.mark.asyncio
async def test_client_missing_api_key(monkeypatch: MonkeyPatch) -> None:
    """Test that the client raises an error when API key is missing."""
    monkeypatch.delenv("DEEPSET_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSET_WORKSPACE", "test-workspace")
    
    with pytest.raises(ValueError, match="API key not provided"):
        DeepsetClient()


@pytest.mark.asyncio
async def test_client_missing_workspace(monkeypatch: MonkeyPatch) -> None:
    """Test that the client raises an error when workspace is missing."""
    monkeypatch.setenv("DEEPSET_API_KEY", "test-key")
    monkeypatch.delenv("DEEPSET_WORKSPACE", raising=False)
    
    with pytest.raises(ValueError, match="Workspace not provided"):
        DeepsetClient()


@pytest.mark.asyncio
async def test_request_get(client: DeepsetClient, mock_http_client: MockHttpClient) -> None:
    """Test basic GET request."""
    endpoint = f"/workspaces/{TEST_WORKSPACE}/pipelines"
    result = await client.request(endpoint)
    
    # Check the result
    assert "data" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["id"] == "test-pipeline"
    
    # Check that the correct request was made
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "GET"
    assert request["url"] == f"{TEST_BASE_URL}{endpoint}"
    assert "Authorization" in request["headers"]


@pytest.mark.asyncio
async def test_request_post(client: DeepsetClient, mock_http_client: MockHttpClient) -> None:
    """Test POST request with data."""
    endpoint = f"/workspaces/{TEST_WORKSPACE}/pipeline_validations"
    data = {"query_yaml": "components:\n  retriever:\n    type: SomeRetriever"}
    await client.request(endpoint, method="POST", data=data)
    
    # Check that the correct request was made
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == f"{TEST_BASE_URL}{endpoint}"
    assert request["json"] == data
    assert "Content-Type" in request["headers"]
    assert request["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_request_put(client: DeepsetClient, mock_http_client: MockHttpClient) -> None:
    """Test PUT request with data."""
    pipeline_name = "test-pipeline"
    endpoint = f"/workspaces/{TEST_WORKSPACE}/pipelines/{pipeline_name}/yaml"
    data = {"query_yaml": "components:\n  retriever:\n    type: SomeRetriever"}
    await client.request(endpoint, method="PUT", data=data)
    
    # Check that the correct request was made
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "PUT"
    assert request["url"] == f"{TEST_BASE_URL}{endpoint}"
    assert request["json"] == data


@pytest.mark.asyncio
async def test_request_with_custom_headers(client: DeepsetClient, mock_http_client: MockHttpClient) -> None:
    """Test request with custom headers."""
    endpoint = "/custom/endpoint"
    custom_headers = {"Accept": "text/plain", "X-Custom-Header": "test-value"}
    await client.request_with_custom_headers(endpoint, headers=custom_headers)
    
    # Check that the correct request was made
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "GET"
    assert request["url"] == f"{TEST_BASE_URL}{endpoint}"
    assert "Authorization" in request["headers"]
    assert request["headers"]["Accept"] == "text/plain"
    assert request["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.asyncio
async def test_request_v2_api(client: DeepsetClient, mock_http_client: MockHttpClient) -> None:
    """Test request to v2 API endpoint."""
    endpoint = "/custom_components"
    await client.request_v2_api(endpoint)
    
    # Check that the correct request was made with v2 API URL
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "GET"
    # URL should use v2 API
    expected_url = TEST_BASE_URL.replace("/api/v1", "/api/v2") + endpoint
    assert request["url"] == expected_url
