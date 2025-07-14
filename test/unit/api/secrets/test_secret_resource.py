# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.secrets.resource import SecretResource
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


@pytest.mark.asyncio
async def test_list_secrets() -> None:
    """Test listing secrets with pagination."""
    mock_secrets_data = {
        "data": [
            {"name": "secret-1", "secret_id": "id-1"},
            {"name": "secret-2", "secret_id": "id-2"},
        ],
        "has_more": False,
        "total": 2,
    }

    fake_client = BaseFakeClient(responses={"v2/secrets": mock_secrets_data})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.list()

    assert isinstance(result, SecretList)
    assert len(result.data) == 2
    assert result.has_more is False
    assert result.total == 2
    assert result.data[0].name == "secret-1"
    assert result.data[0].secret_id == "id-1"


@pytest.mark.asyncio
async def test_list_secrets_with_params() -> None:
    """Test listing secrets with custom parameters."""
    mock_secrets_data = {
        "data": [{"name": "secret-1", "secret_id": "id-1"}],
        "has_more": True,
        "total": 5,
    }

    fake_client = BaseFakeClient(responses={"v2/secrets": mock_secrets_data})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.list(limit=1, field="name", order="ASC")

    assert isinstance(result, SecretList)
    assert len(result.data) == 1
    assert result.has_more is True
    assert result.total == 5

    # Verify request was made with correct parameters
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request["endpoint"] == "v2/secrets"
    assert request["method"] == "GET"
    assert request["params"]["limit"] == "1"
    assert request["params"]["field"] == "name"
    assert request["params"]["order"] == "ASC"


@pytest.mark.asyncio
async def test_list_secrets_empty() -> None:
    """Test listing secrets when none exist."""
    mock_secrets_data = {"data": [], "has_more": False, "total": 0}

    fake_client = BaseFakeClient(responses={"v2/secrets": mock_secrets_data})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.list()

    assert isinstance(result, SecretList)
    assert len(result.data) == 0
    assert result.has_more is False
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_secrets_not_found() -> None:
    """Test listing secrets when response is None."""
    fake_client = BaseFakeClient(responses={"v2/secrets": None})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()

    with pytest.raises(ResourceNotFoundError, match="Failed to retrieve secrets."):
        await resource.list()


@pytest.mark.asyncio
async def test_create_secret() -> None:
    """Test creating a secret."""
    # Create endpoint returns 201 with no content
    fake_response: TransportResponse[None] = TransportResponse(text="", status_code=201, json=None)
    fake_client = BaseFakeClient(responses={"v2/secrets": fake_response})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.create("my-secret", "secret-value")

    # Verify the response is a NoContentResponse
    assert isinstance(result, NoContentResponse)
    assert result.success is True
    assert result.message == "Secret created successfully."

    # Verify request was made correctly
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request["endpoint"] == "v2/secrets"
    assert request["method"] == "POST"
    assert request["data"] == {"name": "my-secret", "secret": "secret-value"}


@pytest.mark.asyncio
async def test_get_secret() -> None:
    """Test getting a specific secret."""
    mock_secret_data = {"name": "my-secret", "secret_id": "secret-123"}

    fake_client = BaseFakeClient(responses={"v2/secrets/secret-123": mock_secret_data})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.get("secret-123")

    assert isinstance(result, Secret)
    assert result.name == "my-secret"
    assert result.secret_id == "secret-123"

    # Verify request was made correctly
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request["endpoint"] == "v2/secrets/secret-123"
    assert request["method"] == "GET"


@pytest.mark.asyncio
async def test_get_secret_not_found() -> None:
    """Test getting a secret that doesn't exist."""
    fake_client = BaseFakeClient(responses={"v2/secrets/nonexistent": None})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()

    with pytest.raises(ResourceNotFoundError, match="Secret 'nonexistent' not found."):
        await resource.get("nonexistent")


@pytest.mark.asyncio
async def test_delete_secret() -> None:
    """Test deleting a secret."""
    # Delete endpoint returns 202 with no content
    fake_response: TransportResponse[None] = TransportResponse(text="", status_code=202, json=None)
    fake_client = BaseFakeClient(responses={"v2/secrets/secret-123": fake_response})

    def secrets() -> SecretResource:
        return SecretResource(client=fake_client)

    fake_client.secrets = secrets  # type: ignore[method-assign]

    resource = fake_client.secrets()
    result = await resource.delete("secret-123")

    # Verify the response is a NoContentResponse
    assert isinstance(result, NoContentResponse)
    assert result.success is True
    assert result.message == "Secret deleted successfully."

    # Verify request was made correctly
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request["endpoint"] == "v2/secrets/secret-123"
    assert request["method"] == "DELETE"
