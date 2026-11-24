# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.secrets.models import Secret
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
from deepset_mcp.tools.secrets import EnvironmentSecret, EnvironmentSecretList, get_secret, list_secrets
from test.unit.conftest import BaseFakeClient


class FakeSecretResource(SecretResourceProtocol):
    def __init__(
        self,
        list_response: PaginatedResponse[Secret] | None = None,
        get_response: Secret | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self.list_response = list_response
        self.get_response = get_response
        self.list_exception = list_exception
        self.get_exception = get_exception
        self.get_call_count = 0
        self.last_secret_id: str | None = None
        self.last_list_workspace: str | None = None

    async def list(
        self,
        limit: int = 10,
        field: str = "created_at",
        order: str = "DESC",
        after: str | None = None,
        workspace: str | None = None,
    ) -> PaginatedResponse[Secret]:
        self.last_list_workspace = workspace
        if self.list_exception:
            raise self.list_exception
        if self.list_response is None:
            return PaginatedResponse[Secret](data=[], has_more=False, total=0)
        return self.list_response

    async def get(self, secret_id: str) -> Secret:
        self.get_call_count += 1
        self.last_secret_id = secret_id
        if self.get_exception:
            raise self.get_exception
        if self.get_response is None:
            raise ResourceNotFoundError(f"Secret '{secret_id}' not found.")
        return self.get_response

    async def create(self, name: str, secret: str) -> NoContentResponse:
        return NoContentResponse(message="Created")

    async def delete(self, secret_id: str) -> NoContentResponse:
        return NoContentResponse(message="Deleted")


class FakeClient(BaseFakeClient):
    def __init__(self, secret_resource: FakeSecretResource | None = None) -> None:
        super().__init__()
        self._secret_resource = secret_resource or FakeSecretResource()

    def secrets(self) -> SecretResourceProtocol:
        return self._secret_resource


@pytest.mark.asyncio
async def test_list_secrets() -> None:
    """Test listing secrets successfully."""
    secrets_data = [
        Secret(name="api-key", secret_id="secret-1"),
        Secret(name="db-pass", secret_id="secret-2"),
    ]
    secret_list = PaginatedResponse[Secret](data=secrets_data, has_more=True, total=5)
    client = FakeClient(secret_resource=FakeSecretResource(list_response=secret_list))

    result = await list_secrets(client=client)

    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 2
    assert result.total == 2
    assert result.has_more is True
    assert result.data[0].name == "api-key"
    assert result.data[1].name == "db-pass"
    assert client._secret_resource.last_list_workspace is None


@pytest.mark.asyncio
async def test_list_secrets_in_workspace() -> None:
    """Test listing secrets of a specific workspace."""
    secret_list = PaginatedResponse[Secret](data=[Secret(name="ws-key", secret_id="secret-3")], has_more=False, total=1)
    client = FakeClient(secret_resource=FakeSecretResource(list_response=secret_list))

    result = await list_secrets(client=client, workspace="my-workspace")

    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 1
    assert result.data[0].name == "ws-key"
    assert client._secret_resource.last_list_workspace == "my-workspace"


@pytest.mark.asyncio
async def test_list_empty() -> None:
    """Test listing when no secrets exist."""
    client = FakeClient()
    result = await list_secrets(client=client)
    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 0
    assert result.total == 0
    assert result.has_more is False


@pytest.mark.asyncio
async def test_list_secrets_api_error() -> None:
    """Test API error during secret listing."""
    client = FakeClient(secret_resource=FakeSecretResource(list_exception=UnexpectedAPIError(500, "Server error")))
    result = await list_secrets(client=client)
    assert result == "API Error: Server error (Status Code: 500)"


@pytest.mark.asyncio
async def test_get_secret_by_id_success() -> None:
    """Test successful retrieval of a secret by its ID."""
    secret = Secret(name="api-key", secret_id="secret-1")
    client = FakeClient(secret_resource=FakeSecretResource(get_response=secret))

    result = await get_secret(client=client, secret_id="secret-1")

    assert isinstance(result, EnvironmentSecret)
    assert result.name == "api-key"
    assert result.id == "secret-1"


@pytest.mark.asyncio
async def test_get_secret_not_found_anywhere() -> None:
    """Test when a secret ID is not found."""
    client = FakeClient(secret_resource=FakeSecretResource(get_exception=ResourceNotFoundError("Not found")))
    result = await get_secret(client=client, secret_id="nonexistent")
    assert result == "Error: Secret with ID 'nonexistent' not found."


@pytest.mark.asyncio
async def test_get_secret_api_error() -> None:
    """Test API error during secret retrieval."""
    client = FakeClient(secret_resource=FakeSecretResource(get_exception=UnexpectedAPIError(500, "Server error")))
    result = await get_secret(client=client, secret_id="secret-1")
    assert result == "API Error: Server error (Status Code: 500)"


@pytest.mark.asyncio
async def test_get_secret_generic_exception() -> None:
    """Test generic exception during secret retrieval."""
    client = FakeClient(secret_resource=FakeSecretResource(get_exception=ValueError("Something went wrong")))
    result = await get_secret(client=client, secret_id="secret-1")
    assert result == "Unexpected error: Something went wrong"
