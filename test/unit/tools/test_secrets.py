import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.tools.secrets import get_secret, list_secrets
from test.unit.conftest import BaseFakeClient


class FakeSecretResource(SecretResourceProtocol):
    def __init__(
        self,
        list_response: SecretList | None = None,
        get_response: Secret | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self.list_response = list_response
        self.get_response = get_response
        self.list_exception = list_exception
        self.get_exception = get_exception

    async def list(self, limit: int = 10, field: str = "created_at", order: str = "DESC") -> SecretList:
        if self.list_exception:
            raise self.list_exception
        if self.list_response is None:
            raise ValueError("No list response configured")
        return self.list_response

    async def get(self, secret_id: str) -> Secret:
        if self.get_exception:
            raise self.get_exception
        if self.get_response is None:
            raise ValueError("No get response configured")
        return self.get_response

    async def create(self, name: str, secret: str) -> NoContentResponse:
        """Not used in tests, but required by protocol."""
        return NoContentResponse(message="Created")

    async def delete(self, secret_id: str) -> NoContentResponse:
        """Not used in tests, but required by protocol."""
        return NoContentResponse(message="Deleted")


class FakeClientWithSecrets(BaseFakeClient):
    def __init__(self, secret_resource: FakeSecretResource) -> None:
        super().__init__()
        self._secret_resource = secret_resource

    def secrets(self) -> FakeSecretResource:
        return self._secret_resource


@pytest.mark.asyncio
async def test_list_secrets_success() -> None:
    """Test successful listing of secrets."""
    secrets_data = [
        Secret(name="api-key", secret_id="secret-1"),
        Secret(name="database-password", secret_id="secret-2"),
    ]
    secret_list = SecretList(data=secrets_data, has_more=False, total=2)
    fake_resource = FakeSecretResource(list_response=secret_list)
    client = FakeClientWithSecrets(fake_resource)

    result = await list_secrets(client=client, limit=10)

    assert isinstance(result, SecretList)
    assert len(result.data) == 2
    assert result.total == 2
    assert result.has_more is False
    assert result.data[0].name == "api-key"
    assert result.data[0].secret_id == "secret-1"
    assert result.data[1].name == "database-password"
    assert result.data[1].secret_id == "secret-2"


@pytest.mark.asyncio
async def test_list_secrets_with_pagination() -> None:
    """Test listing secrets with pagination info."""
    secrets_data = [
        Secret(name="api-key", secret_id="secret-1"),
    ]
    secret_list = SecretList(data=secrets_data, has_more=True, total=5)
    fake_resource = FakeSecretResource(list_response=secret_list)
    client = FakeClientWithSecrets(fake_resource)

    result = await list_secrets(client=client, limit=1)

    assert isinstance(result, SecretList)
    assert len(result.data) == 1
    assert result.total == 5
    assert result.has_more is True
    assert result.data[0].name == "api-key"
    assert result.data[0].secret_id == "secret-1"


@pytest.mark.asyncio
async def test_list_secrets_empty() -> None:
    """Test listing when no secrets exist."""
    secret_list = SecretList(data=[], has_more=False, total=0)
    fake_resource = FakeSecretResource(list_response=secret_list)
    client = FakeClientWithSecrets(fake_resource)

    result = await list_secrets(client=client)

    assert isinstance(result, SecretList)
    assert len(result.data) == 0
    assert result.total == 0
    assert result.has_more is False


@pytest.mark.asyncio
async def test_list_secrets_unexpected_api_error() -> None:
    """Test handling of UnexpectedAPIError during list."""
    fake_resource = FakeSecretResource(list_exception=UnexpectedAPIError(500, "Internal server error"))
    client = FakeClientWithSecrets(fake_resource)

    result = await list_secrets(client=client)

    assert result == "API Error: Internal server error (Status Code: 500)"


@pytest.mark.asyncio
async def test_list_secrets_generic_exception() -> None:
    """Test handling of generic exceptions during list."""
    fake_resource = FakeSecretResource(list_exception=ValueError("Generic error"))
    client = FakeClientWithSecrets(fake_resource)

    result = await list_secrets(client=client)

    assert result == "Unexpected error: Generic error"


@pytest.mark.asyncio
async def test_get_secret_success() -> None:
    """Test successful retrieval of a specific secret."""
    secret = Secret(name="api-key", secret_id="secret-1")
    fake_resource = FakeSecretResource(get_response=secret)
    client = FakeClientWithSecrets(fake_resource)

    result = await get_secret(client=client, secret_id="secret-1")

    assert isinstance(result, Secret)
    assert result.name == "api-key"
    assert result.secret_id == "secret-1"


@pytest.mark.asyncio
async def test_get_secret_not_found() -> None:
    """Test handling when secret is not found."""
    fake_resource = FakeSecretResource(get_exception=ResourceNotFoundError("Secret 'nonexistent' not found."))
    client = FakeClientWithSecrets(fake_resource)

    result = await get_secret(client=client, secret_id="nonexistent")

    assert result == "Error: Secret 'nonexistent' not found. (Status Code: 404)"


@pytest.mark.asyncio
async def test_get_secret_unexpected_api_error() -> None:
    """Test handling of UnexpectedAPIError during get."""
    fake_resource = FakeSecretResource(get_exception=UnexpectedAPIError(500, "Server error"))
    client = FakeClientWithSecrets(fake_resource)

    result = await get_secret(client=client, secret_id="secret-1")

    assert result == "API Error: Server error (Status Code: 500)"


@pytest.mark.asyncio
async def test_get_secret_generic_exception() -> None:
    """Test handling of generic exceptions during get."""
    fake_resource = FakeSecretResource(get_exception=ValueError("Something went wrong"))
    client = FakeClientWithSecrets(fake_resource)

    result = await get_secret(client=client, secret_id="secret-1")

    assert result == "Unexpected error: Something went wrong"
