import os
from typing import Any
from unittest import mock

import pytest
import requests

# Import from main.py with async client support
from deepset_mcp.client import DeepsetClient
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


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_success_json_response(mock_update: mock.Mock) -> None:
    """Tests successful update with JSON response."""
    mock_update.return_value = {"status": "success", "message": "Updated"}

    # Since update_pipeline_yaml is now an async function wrapped with async_to_sync,
    # we need to mock the async method but test the sync wrapper
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    # Check that the DeepsetClient's update_pipeline_yaml method was called with the right args
    mock_update.assert_called_once_with(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
    assert result == {"status": "success", "message": "Updated"}


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_success_empty_response(mock_update: mock.Mock) -> None:
    """Tests successful update with empty response body."""
    mock_update.return_value = {"status": "success", "message": "Pipeline YAML updated successfully (empty response body)"}

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_update.assert_called_once_with(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
    assert result == {"status": "success", "message": "Pipeline YAML updated successfully (empty response body)"}


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_api_error_422_json(mock_update: mock.Mock) -> None:
    """Tests API error (422) with JSON details."""
    error_details = {"detail": [{"type": "validation_error", "msg": "Something is wrong"}]}
    mock_update.return_value = {"error": "API Error: 422", "details": error_details}

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_update.assert_called_once_with(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
    assert result == {"error": "API Error: 422", "details": error_details}


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_api_error_500_text(mock_update: mock.Mock) -> None:
    """Tests API error (500) with non-JSON text details."""
    error_text = "Internal Server Error"
    mock_update.return_value = {"error": "API Error: 500", "details": error_text}

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_update.assert_called_once_with(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
    assert result == {"error": "API Error: 500", "details": error_text}


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_request_exception(mock_update: mock.Mock) -> None:
    """Tests network request failure."""
    mock_update.return_value = {"error": "Request failed: Connection timed out"}

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_update.assert_called_once_with(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)
    assert "error" in result
    assert "Request failed: Connection timed out" in result["error"]


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")  # Still need to mock, even if not called
def test_update_pipeline_yaml_empty_content(mock_update: mock.Mock) -> None:
    """Tests the function's validation for empty YAML content."""
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, "")
    assert result == {"error": "Empty YAML content provided"}
    mock_update.assert_not_called()  # Ensure client method wasn't called


@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch("deepset_mcp.client.DeepsetClient.update_pipeline_yaml")
def test_update_pipeline_yaml_invalid_structure(mock_update: mock.Mock) -> None:
    """Tests the function's validation for missing 'components:'."""
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, INVALID_YAML_CONTENT_NO_COMPONENTS)
    assert result == {"error": "Invalid YAML content - missing 'components:' section"}
    mock_update.assert_not_called()  # Ensure client method wasn't called
