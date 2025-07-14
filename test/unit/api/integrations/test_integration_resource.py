# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for IntegrationResource."""

from uuid import UUID

import pytest

from deepset_mcp.api.exceptions import DeepsetAPIError, ResourceNotFoundError
from deepset_mcp.api.integrations.models import Integration, IntegrationList, IntegrationProvider
from deepset_mcp.api.integrations.resource import IntegrationResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class FakeClientForIntegrationResource(BaseFakeClient):
    """Fake client specifically for testing IntegrationResource."""

    def integrations(self) -> IntegrationResource:
        """Return a real IntegrationResource instance for testing."""
        return IntegrationResource(client=self)


@pytest.mark.asyncio
class TestIntegrationResource:
    """Test cases for IntegrationResource methods."""

    async def test_list_integrations_success(self) -> None:
        """Test successful listing of integrations."""
        # Arrange
        mock_response = [
            {
                "invalid": False,
                "model_registry_token_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "provider": "aws-bedrock",
                "provider_domain": "us-east-1",
            },
            {
                "invalid": True,
                "model_registry_token_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
                "provider": "openai",
                "provider_domain": "api.openai.com",
            },
        ]
        client = FakeClientForIntegrationResource(responses={"v1/model_registry_tokens": mock_response})

        # Act
        result = await client.integrations().list()

        # Assert
        assert isinstance(result, IntegrationList)
        assert len(result) == 2

        assert result.integrations[0].invalid is False
        assert result.integrations[0].model_registry_token_id == UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert result.integrations[0].provider == IntegrationProvider.AWS_BEDROCK
        assert result.integrations[0].provider_domain == "us-east-1"

        assert result.integrations[1].invalid is True
        assert result.integrations[1].model_registry_token_id == UUID("4fa85f64-5717-4562-b3fc-2c963f66afa7")
        assert result.integrations[1].provider == IntegrationProvider.OPENAI
        assert result.integrations[1].provider_domain == "api.openai.com"

    async def test_list_integrations_empty_response(self) -> None:
        """Test listing integrations with empty response."""
        # Arrange
        client = FakeClientForIntegrationResource(responses={"v1/model_registry_tokens": []})

        # Act
        result = await client.integrations().list()

        # Assert
        assert isinstance(result, IntegrationList)
        assert len(result) == 0
        assert result.integrations == []

    async def test_list_integrations_none_response(self) -> None:
        """Test listing integrations with None response."""
        # Arrange
        client = FakeClientForIntegrationResource(
            responses={"v1/model_registry_tokens": TransportResponse(text="", status_code=200, json=None)}
        )

        # Act
        result = await client.integrations().list()

        # Assert
        assert isinstance(result, IntegrationList)
        assert len(result) == 0
        assert result.integrations == []

    async def test_list_integrations_api_error(self) -> None:
        """Test listing integrations with API error."""
        # Arrange
        client = FakeClientForIntegrationResource(
            responses={"v1/model_registry_tokens": DeepsetAPIError(message="API Error", status_code=500)}
        )

        # Act & Assert
        with pytest.raises(DeepsetAPIError):
            await client.integrations().list()

    async def test_get_integration_success(self) -> None:
        """Test successful retrieval of a specific integration."""
        # Arrange
        mock_response = {
            "invalid": False,
            "model_registry_token_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "provider": "aws-bedrock",
            "provider_domain": "us-east-1",
        }
        client = FakeClientForIntegrationResource(responses={"v1/model_registry_tokens/aws-bedrock": mock_response})

        # Act
        result = await client.integrations().get(IntegrationProvider.AWS_BEDROCK)

        # Assert
        assert isinstance(result, Integration)
        assert result.invalid is False
        assert result.model_registry_token_id == UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert result.provider == IntegrationProvider.AWS_BEDROCK
        assert result.provider_domain == "us-east-1"

    async def test_get_integration_invalid_status(self) -> None:
        """Test retrieval of an integration with invalid status."""
        # Arrange
        mock_response = {
            "invalid": True,
            "model_registry_token_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
            "provider": "openai",
            "provider_domain": "api.openai.com",
        }
        client = FakeClientForIntegrationResource(responses={"v1/model_registry_tokens/openai": mock_response})

        # Act
        result = await client.integrations().get(IntegrationProvider.OPENAI)

        # Assert
        assert isinstance(result, Integration)
        assert result.invalid is True
        assert result.model_registry_token_id == UUID("4fa85f64-5717-4562-b3fc-2c963f66afa7")
        assert result.provider == IntegrationProvider.OPENAI
        assert result.provider_domain == "api.openai.com"

    async def test_get_integration_api_error(self) -> None:
        """Test getting integration with API error."""
        # Arrange
        client = FakeClientForIntegrationResource(
            responses={"v1/model_registry_tokens/aws-bedrock": ResourceNotFoundError("Not Found")}
        )

        # Act & Assert
        with pytest.raises(DeepsetAPIError):
            await client.integrations().get(IntegrationProvider.AWS_BEDROCK)

    async def test_get_integration_all_providers(self) -> None:
        """Test that all provider enum values work correctly."""
        # Arrange
        providers_to_test = [
            IntegrationProvider.AWS_BEDROCK,
            IntegrationProvider.AZURE_DOCUMENT_INTELLIGENCE,
            IntegrationProvider.AZURE_OPENAI,
            IntegrationProvider.COHERE,
            IntegrationProvider.DEEPL,
            IntegrationProvider.GOOGLE,
            IntegrationProvider.HUGGINGFACE,
            IntegrationProvider.NVIDIA,
            IntegrationProvider.OPENAI,
            IntegrationProvider.SEARCHAPI,
            IntegrationProvider.SNOWFLAKE,
            IntegrationProvider.UNSTRUCTURED,
            IntegrationProvider.VOYAGE_AI,
            IntegrationProvider.WANDB_AI,
            IntegrationProvider.MONGODB,
            IntegrationProvider.TOGETHER_AI,
        ]

        responses = {}
        for provider in providers_to_test:
            responses[f"v1/model_registry_tokens/{provider.value}"] = {
                "invalid": False,
                "model_registry_token_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "provider": provider.value,
                "provider_domain": "example.com",
            }

        client = FakeClientForIntegrationResource(responses=responses)

        # Act & Assert
        for provider in providers_to_test:
            result = await client.integrations().get(provider)
            assert isinstance(result, Integration)
            assert result.provider == provider
            assert result.provider_domain == "example.com"
