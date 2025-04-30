import pytest
import requests
from unittest import mock
import os

# Assuming your main code is in main.py
from main import update_pipeline_yaml, DEEPSET_API_BASE_URL

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
def create_mock_response(status_code, json_data=None, text_data=None):
    """Creates a mock requests.Response object."""
    mock_resp = mock.Mock(spec=requests.Response)
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json.return_value = json_data
        mock_resp.text = str(json_data) # Simulate text attribute
    else:
        mock_resp.text = text_data
        # Make json() raise an error if no json_data is provided
        mock_resp.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)
    return mock_resp

# --- Test Cases ---

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put') # Mock requests.put used in update_pipeline_yaml
def test_update_pipeline_yaml_success_json_response(mock_put):
    """Tests successful update with JSON response."""
    mock_response = create_mock_response(200, json_data={"status": "success", "message": "Updated"})
    mock_put.return_value = mock_response

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    expected_payload = {"query_yaml": VALID_YAML_CONTENT}
    expected_headers = {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json,text/plain,*/*"
    }
    mock_put.assert_called_once_with(
        EXPECTED_URL,
        headers=expected_headers,
        json=expected_payload
    )
    assert result == {"status": "success", "message": "Updated"}

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put')
def test_update_pipeline_yaml_success_empty_response(mock_put):
    """Tests successful update with empty response body."""
    mock_response = create_mock_response(200, text_data="") # Empty body
    mock_put.return_value = mock_response

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    expected_payload = {"query_yaml": VALID_YAML_CONTENT}
    # ... assertions for call arguments are the same as above ...
    mock_put.assert_called_once()
    assert result == {"status": "success", "message": "Pipeline YAML updated successfully (empty response body)"}

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put')
def test_update_pipeline_yaml_api_error_422_json(mock_put):
    """Tests API error (422) with JSON details."""
    error_details = {"detail": [{"type": "validation_error", "msg": "Something is wrong"}]}
    mock_response = create_mock_response(422, json_data=error_details)
    mock_put.return_value = mock_response

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_put.assert_called_once() # Check call args if needed
    assert result == {
        "error": "API Error: 422",
        "details": error_details
    }

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put')
def test_update_pipeline_yaml_api_error_500_text(mock_put):
    """Tests API error (500) with non-JSON text details."""
    error_text = "Internal Server Error"
    mock_response = create_mock_response(500, text_data=error_text)
    mock_put.return_value = mock_response

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_put.assert_called_once() # Check call args if needed
    assert result == {
        "error": "API Error: 500",
        "details": error_text
    }

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put')
def test_update_pipeline_yaml_request_exception(mock_put):
    """Tests network request failure."""
    mock_put.side_effect = requests.exceptions.RequestException("Connection timed out")

    result = update_pipeline_yaml(TEST_PIPELINE_NAME, VALID_YAML_CONTENT)

    mock_put.assert_called_once() # Check call args if needed
    assert "error" in result
    assert "Request failed: Connection timed out" in result["error"]

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put') # Still need to mock put, even if not called
def test_update_pipeline_yaml_empty_content(mock_put):
    """Tests the function's validation for empty YAML content."""
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, "")
    assert result == {"error": "Empty YAML content provided"}
    mock_put.assert_not_called() # Ensure API wasn't called

@mock.patch.dict(os.environ, {"DEEPSET_WORKSPACE": TEST_WORKSPACE, "DEEPSET_API_KEY": TEST_API_KEY})
@mock.patch('main.requests.put')
def test_update_pipeline_yaml_invalid_structure(mock_put):
    """Tests the function's validation for missing 'components:'."""
    result = update_pipeline_yaml(TEST_PIPELINE_NAME, INVALID_YAML_CONTENT_NO_COMPONENTS)
    assert result == {"error": "Invalid YAML content - missing 'components:' section"}
    mock_put.assert_not_called() # Ensure API wasn't called