# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.integrations.models import Integration, IntegrationList, IntegrationProvider
from deepset_mcp.api.integrations.protocols import IntegrationResourceProtocol
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.secrets.protocols import SecretResourceProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.tools.secrets import EnvironmentSecret, EnvironmentSecretList, get_secret, list_secrets
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
        self.get_call_count = 0
        self.last_secret_id: str | None = None

    async def list(self, limit: int = 10, field: str = "created_at", order: str = "DESC") -> SecretList:
        if self.list_exception:
            raise self.list_exception
        if self.list_response is None:
            return SecretList(data=[], has_more=False, total=0)
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


class FakeIntegrationResource(IntegrationResourceProtocol):
    def __init__(
        self,
        list_response: IntegrationList | None = None,
        get_response: Integration | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self.list_response = list_response
        self.get_response = get_response
        self.list_exception = list_exception
        self.get_exception = get_exception

    async def list(self) -> IntegrationList:
        if self.list_exception:
            raise self.list_exception
        if self.list_response is None:
            return IntegrationList(integrations=[])
        return self.list_response

    async def get(self, provider: IntegrationProvider) -> Integration:
        if self.get_exception:
            raise self.get_exception
        if self.get_response is None:
            raise ResourceNotFoundError(f"Integration for provider '{provider}' not found.")
        return self.get_response


class FakeClient(BaseFakeClient):
    def __init__(
        self,
        secret_resource: FakeSecretResource | None = None,
        integration_resource: FakeIntegrationResource | None = None,
    ) -> None:
        super().__init__()
        self._secret_resource = secret_resource or FakeSecretResource()
        self._integration_resource = integration_resource or FakeIntegrationResource()

    def secrets(self) -> SecretResourceProtocol:
        return self._secret_resource

    def integrations(self) -> IntegrationResourceProtocol:
        return self._integration_resource


@pytest.mark.asyncio
async def test_list_secrets_and_integrations() -> None:
    """Test listing secrets and integrations successfully."""
    secrets_data = [Secret(name="api-key", secret_id="secret-1")]
    secret_list = SecretList(data=secrets_data, has_more=False, total=1)

    integration_id = uuid.uuid4()
    integrations_data = [
        Integration(
            invalid=False,
            model_registry_token_id=integration_id,
            provider=IntegrationProvider.OPENAI,
            provider_domain="api.openai.com",
        )
    ]
    integration_list = IntegrationList(integrations=integrations_data)

    client = FakeClient(
        secret_resource=FakeSecretResource(list_response=secret_list),
        integration_resource=FakeIntegrationResource(list_response=integration_list),
    )

    result = await list_secrets(client=client)

    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 2
    assert result.total == 2
    assert result.has_more is False

    # Check secret
    assert result.data[0].name == "api-key"
    assert result.data[0].id == "secret-1"
    assert result.data[0].invalid is None

    # Check integration
    assert result.data[1].name == "OPENAI_API_KEY"
    assert result.data[1].id == str(integration_id)
    assert result.data[1].invalid is False


@pytest.mark.asyncio
async def test_list_secrets_only() -> None:
    """Test listing only secrets when no integrations exist."""
    secrets_data = [
        Secret(name="api-key", secret_id="secret-1"),
        Secret(name="db-pass", secret_id="secret-2"),
    ]
    secret_list = SecretList(data=secrets_data, has_more=True, total=5)
    client = FakeClient(secret_resource=FakeSecretResource(list_response=secret_list))

    result = await list_secrets(client=client)

    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 2
    assert result.total == 2
    assert result.has_more is True
    assert result.data[0].name == "api-key"
    assert result.data[1].name == "db-pass"


@pytest.mark.asyncio
async def test_list_integrations_only() -> None:
    """Test listing only integrations when no secrets exist."""
    integration_id = uuid.uuid4()
    integrations_data = [
        Integration(
            invalid=True,
            model_registry_token_id=integration_id,
            provider=IntegrationProvider.COHERE,
            provider_domain="api.cohere.ai",
        )
    ]
    integration_list = IntegrationList(integrations=integrations_data)
    client = FakeClient(integration_resource=FakeIntegrationResource(list_response=integration_list))

    result = await list_secrets(client=client)

    assert isinstance(result, EnvironmentSecretList)
    assert len(result.data) == 1
    assert result.total == 1
    assert result.has_more is False
    assert result.data[0].name == "COHERE_API_KEY"
    assert result.data[0].id == str(integration_id)
    assert result.data[0].invalid is True


@pytest.mark.asyncio
async def test_list_empty() -> None:
    """Test listing when no secrets or integrations exist."""
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
async def test_list_integrations_api_error() -> None:
    """Test API error during integration listing."""
    client = FakeClient(
        integration_resource=FakeIntegrationResource(list_exception=UnexpectedAPIError(500, "Server error"))
    )
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
    assert result.invalid is None


@pytest.mark.asyncio
async def test_get_integration_by_id_success() -> None:
    """Test successful retrieval of an integration by its ID."""
    integration_id = uuid.uuid4()
    integrations_data = [
        Integration(
            invalid=False,
            model_registry_token_id=integration_id,
            provider=IntegrationProvider.OPENAI,
            provider_domain="api.openai.com",
        )
    ]
    integration_list = IntegrationList(integrations=integrations_data)

    client = FakeClient(
        secret_resource=FakeSecretResource(get_exception=ResourceNotFoundError("Not found")),
        integration_resource=FakeIntegrationResource(list_response=integration_list),
    )

    result = await get_secret(client=client, secret_id=str(integration_id))

    assert isinstance(result, EnvironmentSecret)
    assert result.name == "OPENAI_API_KEY"
    assert result.id == str(integration_id)
    assert result.invalid is False


@pytest.mark.asyncio
async def test_get_secret_not_found_anywhere() -> None:
    """Test when a secret ID is not found in secrets or integrations."""
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
async def test_get_integration_list_api_error() -> None:
    """Test API error when listing integrations after secret not found."""
    client = FakeClient(
        secret_resource=FakeSecretResource(get_exception=ResourceNotFoundError("Not found")),
        integration_resource=FakeIntegrationResource(list_exception=UnexpectedAPIError(500, "Server error")),
    )
    result = await get_secret(client=client, secret_id="any-id")
    assert result == "API Error: Server error (Status Code: 500)"


@pytest.mark.asyncio
async def test_get_secret_generic_exception() -> None:
    """Test generic exception during secret retrieval."""
    client = FakeClient(secret_resource=FakeSecretResource(get_exception=ValueError("Something went wrong")))
    result = await get_secret(client=client, secret_id="secret-1")
    assert result == "Unexpected error: Something went wrong"
