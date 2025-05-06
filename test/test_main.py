import os
from typing import Any
from unittest import mock

import pytest
import httpx
import requests

# Import from main.py with async client support
from deepset_mcp.client import DeepsetClient, MockHttpClient
from deepset_mcp.main import DEEPSET_API_BASE_URL, update_pipeline_yaml

# --- Test Data ---
TEST_WORKSPACE = "test-workspace"
TEST_API_KEY = "test-api-key"
TEST_PIPELINE_NAME = "hack-test"
VALID_YAML_CONTENT = """
components:
  retriever:
    type: SomeRetriever
connections: []
inputs: {}
outputs: {}
"""
INVALID_YAML_CONTENT_NO_COMPONENTS = """
name: test
connections: []
"""
EXPECTED_ENDPOINT = f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml"
EXPECTED_URL = f"{DEEPSET_API_BASE_URL}{EXPECTED_ENDPOINT}"


# --- Helper Function to Mock Response ---
def create_mock_response(
    status_code: int, json_data: dict[str, Any] | None = None, text_data: str | None = None
) -> requests.Response:
    """Creates a mock requests.Response object."""
    mock_resp = mock.Mock(spec=requests.Response)
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json.return_value = json_data
        mock_resp.text = str(json_data)  # Simulate text attribute
    else:
        mock_resp.text = text_data
        # Make json() raise an error if no json_data is provided
        mock_resp.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)
    return mock_resp


# --- Test Cases ---


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_success_json_response() -> None:
    """Tests successful update with JSON response."""
    # Create a mock client with the expected responses
    mock_responses = {}
    update_response = mock.Mock(spec=httpx.Response)
    update_response.status_code = 200
    update_response.text = '{"status": "success", "message": "Updated"}'
    update_response.json.return_value = {"status": "success", "message": "Updated"}
    
    endpoint = f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml"
    url = f"{DEEPSET_API_BASE_URL}{endpoint}"
    mock_responses[f"PUT {url}"] = update_response
    
    mock_client = MockHttpClient(mock_responses)
    
    # Since update_pipeline_yaml is async, we need to test it differently
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        # Setup the mock client instance
        mock_client_instance = mock.MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.workspace = TEST_WORKSPACE
        mock_client_instance.request.return_value = {"status": "success", "message": "Updated"}
        mock_client_class.return_value = mock_client_instance
        
        # Call the function
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
        
        # Verify the call was made correctly
        mock_client_instance.request.assert_called_once_with(
            f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml", 
            method="PUT", 
            data={"query_yaml": VALID_YAML_CONTENT}
        )
        assert result == {"status": "success", "message": "Updated"}


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_success_empty_response() -> None:
    """Tests successful update with empty response body."""
    # Since update_pipeline_yaml is async, we need to test it differently
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        # Setup the mock client instance
        mock_client_instance = mock.MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.workspace = TEST_WORKSPACE
        mock_client_instance.request.return_value = {"status": "success", "message": "API returned empty response body"}
        mock_client_class.return_value = mock_client_instance
        
        # Call the function
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
        
        # Verify the call was made correctly
        mock_client_instance.request.assert_called_once_with(
            f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml", 
            method="PUT", 
            data={"query_yaml": VALID_YAML_CONTENT}
        )
        assert result == {"status": "success", "message": "API returned empty response body"}


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_api_error_422_json() -> None:
    """Tests API error (422) with JSON details."""
    error_details = {"detail": [{"type": "validation_error", "msg": "Something is wrong"}]}
    error_response = {"error": "API Error: 422", "details": error_details}
    
    # Since update_pipeline_yaml is async, we need to test it differently
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        # Setup the mock client instance
        mock_client_instance = mock.MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.workspace = TEST_WORKSPACE
        mock_client_instance.request.return_value = error_response
        mock_client_class.return_value = mock_client_instance
        
        # Call the function
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
        
        # Verify the call was made correctly
        mock_client_instance.request.assert_called_once_with(
            f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml", 
            method="PUT", 
            data={"query_yaml": VALID_YAML_CONTENT}
        )
        assert result == error_response


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_api_error_500_text() -> None:
    """Tests API error (500) with non-JSON text details."""
    error_text = "Internal Server Error"
    error_response = {"error": "API Error: 500", "details": error_text}
    
    # Since update_pipeline_yaml is async, we need to test it differently
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        # Setup the mock client instance
        mock_client_instance = mock.MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.workspace = TEST_WORKSPACE
        mock_client_instance.request.return_value = error_response
        mock_client_class.return_value = mock_client_instance
        
        # Call the function
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
        
        # Verify the call was made correctly
        mock_client_instance.request.assert_called_once_with(
            f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml", 
            method="PUT", 
            data={"query_yaml": VALID_YAML_CONTENT}
        )
        assert result == error_response


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_request_exception() -> None:
    """Tests network request failure."""
    error_response = {"error": "Request failed: Connection timed out"}
    
    # Since update_pipeline_yaml is async, we need to test it differently
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        # Setup the mock client instance
        mock_client_instance = mock.MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.workspace = TEST_WORKSPACE
        mock_client_instance.request.return_value = error_response
        mock_client_class.return_value = mock_client_instance
        
        # Call the function
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
        
        # Verify the call was made correctly
        mock_client_instance.request.assert_called_once_with(
            f"/workspaces/{TEST_WORKSPACE}/pipelines/{TEST_PIPELINE_NAME}/yaml", 
            method="PUT", 
            data={"query_yaml": VALID_YAML_CONTENT}
        )
        assert "error" in result
        assert "Request failed: Connection timed out" in result["error"]


@pytest.mark.asyncio
@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
async def test_update_pipeline_yaml_empty_content() -> None:
    """Tests the function's validation for empty YAML content."""
    # For this test, we're testing client validation which happens before the API call
    with mock.patch("deepset_mcp.main.DeepsetClient") as mock_client_class:
        mock_client_instance = mock.MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        # Call the function with empty content
        result = await update_pipeline_yaml(TEST_PIPELINE_NAME, "")
        
        # Verify validation failed and client was not used
        assert result == {"error": "Empty YAML content provided"}
        # The context manager should not have been entered
        mock_client_instance.__aenter__.assert_not_called()


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_invalid_structure(mock_update: mock.Mock) -> None:
    """Tests the function's validation for missing 'components:'."""
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, INVALID_YAML_CONTENT_NO_COMPONENTS)
    assert result == {"error": "Invalid YAML content - missing 'components:' section"}
    mock_update.assert_not_called()  # Ensure client method wasn't called
