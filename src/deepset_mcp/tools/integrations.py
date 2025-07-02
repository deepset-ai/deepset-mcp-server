"""Tools for managing integrations."""

import logging
from typing import Union

from deepset_mcp.api.exceptions import DeepsetAPIError
from deepset_mcp.api.integrations.models import IntegrationProvider
from deepset_mcp.api.protocols import AsyncClientProtocol

logger = logging.getLogger(__name__)


async def list_integrations(client: AsyncClientProtocol) -> str:
    """List all available integrations in the deepset platform.

    Use this tool to see all configured integrations and their status.
    This shows which third-party services (like AWS Bedrock, OpenAI, etc.) are
    configured and available for use.

    Returns a formatted list showing:
    - Provider name and type
    - Integration status (valid/invalid)
    - Provider domain information
    - Unique identifier for each integration

    Use this when you need to:
    - Check which integrations are available
    - Verify integration status
    - Get an overview of configured external services

    :param client: The async client for API communication.
    :returns: Formatted string listing all integrations with their details.
    """
    try:
        integrations = await client.integrations().list()

        if not integrations:
            return "No integrations found."

        result = "Available Integrations:\n\n"
        for integration in integrations:
            status = "✅ Valid" if not integration.invalid else "❌ Invalid"
            result += (
                f"• Provider: {integration.provider.value}\n"
                f"  Status: {status}\n"
                f"  Domain: {integration.provider_domain}\n"
                f"  ID: {integration.model_registry_token_id}\n\n"
            )

        return result.strip()

    except DeepsetAPIError as e:
        logger.error(f"API error listing integrations: {e}")
        return f"Error listing integrations: {e}"
    except Exception as e:
        logger.error(f"Unexpected error listing integrations: {e}")
        return f"Unexpected error occurred: {e}"


async def get_integration(
    client: AsyncClientProtocol,
    provider: str,
) -> str:
    """Get details for a specific integration by provider name.

    Use this tool to get detailed information about a specific integration.
    This is useful when you need to check the status or configuration of
    a particular service integration.

    Supported providers:
    - aws-bedrock: Amazon Bedrock AI models
    - azure-document-intelligence: Azure Form Recognizer/Document Intelligence
    - azure-openai: Azure OpenAI Service
    - cohere: Cohere AI models
    - deepl: DeepL translation service
    - google: Google AI services
    - huggingface: Hugging Face models
    - nvidia: NVIDIA AI models
    - openai: OpenAI models
    - searchapi: Search API services
    - snowflake: Snowflake data platform
    - unstructured: Unstructured.io document processing
    - voyage-ai: Voyage AI embedding models
    - wandb-ai: Weights & Biases AI
    - mongodb: MongoDB database
    - together-ai: Together AI models

    Returns detailed information including:
    - Provider name and status
    - Validity of the integration
    - Provider domain
    - Unique integration identifier

    :param client: The async client for API communication.
    :param provider: The provider name to look up (e.g., 'openai', 'aws-bedrock').
    :returns: Formatted string with integration details or error message.
    """
    try:
        # Validate provider
        try:
            provider_enum = IntegrationProvider(provider)
        except ValueError:
            valid_providers = [p.value for p in IntegrationProvider]
            return (
                f"Invalid provider '{provider}'. "
                f"Supported providers: {', '.join(valid_providers)}"
            )

        integration = await client.integrations().get(provider_enum)

        status = "✅ Valid" if not integration.invalid else "❌ Invalid"
        result = (
            f"Integration Details for {integration.provider.value}:\n\n"
            f"Status: {status}\n"
            f"Provider: {integration.provider.value}\n"
            f"Domain: {integration.provider_domain}\n"
            f"ID: {integration.model_registry_token_id}\n"
        )

        if integration.invalid:
            result += "\n⚠️  This integration is currently invalid and may not work properly."

        return result

    except DeepsetAPIError as e:
        logger.error(f"API error getting integration for provider {provider}: {e}")
        return f"Error getting integration for '{provider}': {e}"
    except Exception as e:
        logger.error(f"Unexpected error getting integration for provider {provider}: {e}")
        return f"Unexpected error occurred: {e}"
