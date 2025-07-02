"""Unit tests for integration tools."""

import pytest
from uuid import UUID

from deepset_mcp.api.exceptions import DeepsetAPIError
from deepset_mcp.api.integrations.models import Integration, IntegrationList, IntegrationProvider
from deepset_mcp.api.integrations.resource import IntegrationResource
from deepset_mcp.tools.integrations import get_integration, list_integrations
from test.unit.conftest import BaseFakeClient


class FakeIntegrationResource(IntegrationResource):
    """Fake integration resource for testing."""

    def __init__(self, integrations: list[Integration] | None = None, get_integration_result: Integration | None = None):
        """Initialize with test data.
        
        :param integrations: List of integrations to return from list().
        :param get_integration_result: Integration to return from get().
        """
        # Don't call super().__init__ as we don't need a real client
        self._integrations = integrations or []
        self._get_integration_result = get_integration_result

    async def list(self) -> IntegrationList:
        """Return predefined integrations list."""
        return IntegrationList(integrations=self._integrations)

    async def get(self, provider: IntegrationProvider) -> Integration:
        """Return predefined integration."""
        if self._get_integration_result is None:
            raise DeepsetAPIError("Integration not found", status_code=404)
        return self._get_integration_result


class FakeClientForIntegrationTools(BaseFakeClient):
    """Fake client for testing integration tools."""

    def __init__(self, integration_resource: FakeIntegrationResource):
        """Initialize with fake integration resource.
        
        :param integration_resource: The fake integration resource to use.
        """
        super().__init__()
        self._integration_resource = integration_resource

    def integrations(self) -> FakeIntegrationResource:
        """Return the fake integration resource."""
        return self._integration_resource


@pytest.mark.asyncio
class TestListIntegrations:
    """Test cases for list_integrations tool."""

    async def test_list_integrations_with_data(self) -> None:
        """Test listing integrations with sample data."""
        # Arrange
        integrations = [
            Integration(
                invalid=False,
                model_registry_token_id=UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
                provider=IntegrationProvider.AWS_BEDROCK,
                provider_domain="us-east-1",
            ),
            Integration(
                invalid=True,
                model_registry_token_id=UUID("4fa85f64-5717-4562-b3fc-2c963f66afa7"),
                provider=IntegrationProvider.OPENAI,
                provider_domain="api.openai.com",
            ),
        ]
        
        fake_resource = FakeIntegrationResource(integrations=integrations)
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await list_integrations(client)

        # Assert
        assert "Available Integrations:" in result
        assert "aws-bedrock" in result
        assert "openai" in result
        assert "✅ Valid" in result
        assert "❌ Invalid" in result
        assert "us-east-1" in result
        assert "api.openai.com" in result
        assert "3fa85f64-5717-4562-b3fc-2c963f66afa6" in result
        assert "4fa85f64-5717-4562-b3fc-2c963f66afa7" in result

    async def test_list_integrations_empty(self) -> None:
        """Test listing integrations with no data."""
        # Arrange
        fake_resource = FakeIntegrationResource(integrations=[])
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await list_integrations(client)

        # Assert
        assert result == "No integrations found."

    async def test_list_integrations_api_error(self) -> None:
        """Test listing integrations with API error."""
        # Arrange
        class FailingResource(FakeIntegrationResource):
            async def list(self) -> IntegrationList:
                raise DeepsetAPIError("API Error", status_code=500)

        fake_resource = FailingResource()
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await list_integrations(client)

        # Assert
        assert "Error listing integrations:" in result
        assert "API Error" in result

    async def test_list_integrations_unexpected_error(self) -> None:
        """Test listing integrations with unexpected error."""
        # Arrange
        class FailingResource(FakeIntegrationResource):
            async def list(self) -> IntegrationList:
                raise ValueError("Unexpected error")

        fake_resource = FailingResource()
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await list_integrations(client)

        # Assert
        assert "Unexpected error occurred:" in result
        assert "Unexpected error" in result


@pytest.mark.asyncio
class TestGetIntegration:
    """Test cases for get_integration tool."""

    async def test_get_integration_valid(self) -> None:
        """Test getting a valid integration."""
        # Arrange
        integration = Integration(
            invalid=False,
            model_registry_token_id=UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
            provider=IntegrationProvider.AWS_BEDROCK,
            provider_domain="us-east-1",
        )
        
        fake_resource = FakeIntegrationResource(get_integration_result=integration)
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await get_integration(client, "aws-bedrock")

        # Assert
        assert "Integration Details for aws-bedrock:" in result
        assert "✅ Valid" in result
        assert "us-east-1" in result
        assert "3fa85f64-5717-4562-b3fc-2c963f66afa6" in result
        assert "invalid and may not work properly" not in result

    async def test_get_integration_invalid(self) -> None:
        """Test getting an invalid integration."""
        # Arrange
        integration = Integration(
            invalid=True,
            model_registry_token_id=UUID("4fa85f64-5717-4562-b3fc-2c963f66afa7"),
            provider=IntegrationProvider.OPENAI,
            provider_domain="api.openai.com",
        )
        
        fake_resource = FakeIntegrationResource(get_integration_result=integration)
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await get_integration(client, "openai")

        # Assert
        assert "Integration Details for openai:" in result
        assert "❌ Invalid" in result
        assert "api.openai.com" in result
        assert "4fa85f64-5717-4562-b3fc-2c963f66afa7" in result
        assert "invalid and may not work properly" in result

    async def test_get_integration_invalid_provider(self) -> None:
        """Test getting integration with invalid provider name."""
        # Arrange
        fake_resource = FakeIntegrationResource()
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await get_integration(client, "invalid-provider")

        # Assert
        assert "Invalid provider 'invalid-provider'" in result
        assert "Supported providers:" in result
        assert "aws-bedrock" in result
        assert "openai" in result

    async def test_get_integration_api_error(self) -> None:
        """Test getting integration with API error."""
        # Arrange
        class FailingResource(FakeIntegrationResource):
            async def get(self, provider: IntegrationProvider) -> Integration:
                raise DeepsetAPIError("Not Found", status_code=404)

        fake_resource = FailingResource()
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await get_integration(client, "aws-bedrock")

        # Assert
        assert "Error getting integration for 'aws-bedrock':" in result
        assert "Not Found" in result

    async def test_get_integration_unexpected_error(self) -> None:
        """Test getting integration with unexpected error."""
        # Arrange
        class FailingResource(FakeIntegrationResource):
            async def get(self, provider: IntegrationProvider) -> Integration:
                raise ValueError("Unexpected error")

        fake_resource = FailingResource()
        client = FakeClientForIntegrationTools(fake_resource)

        # Act
        result = await get_integration(client, "aws-bedrock")

        # Assert
        assert "Unexpected error occurred:" in result
        assert "Unexpected error" in result

    async def test_get_integration_all_valid_providers(self) -> None:
        """Test that all valid provider names work."""
        # Arrange
        integration = Integration(
            invalid=False,
            model_registry_token_id=UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
            provider=IntegrationProvider.AWS_BEDROCK,  # This will be overridden by the enum
            provider_domain="example.com",
        )
        
        fake_resource = FakeIntegrationResource(get_integration_result=integration)
        client = FakeClientForIntegrationTools(fake_resource)

        # Test a few key providers
        valid_providers = [
            "aws-bedrock",
            "azure-openai",
            "openai",
            "cohere",
            "huggingface",
            "together-ai",
        ]

        # Act & Assert
        for provider in valid_providers:
            result = await get_integration(client, provider)
            assert "Integration Details for" in result
            assert "Invalid provider" not in result
