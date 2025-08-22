# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the integrations API."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class IntegrationProvider(StrEnum):
    """Supported integration providers."""

    AWS_BEDROCK = "aws-bedrock"
    AZURE_DOCUMENT_INTELLIGENCE = "azure-document-intelligence"
    AZURE_OPENAI = "azure-openai"
    COHERE = "cohere"
    DEEPL = "deepl"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    NVIDIA = "nvidia"
    OPENAI = "openai"
    SEARCHAPI = "searchapi"
    SNOWFLAKE = "snowflake"
    UNSTRUCTURED = "unstructured"
    VOYAGE_AI = "voyage-ai"
    WANDB_AI = "wandb-ai"
    MONGODB = "mongodb"
    TOGETHER_AI = "together-ai"


class Integration(BaseModel):
    """Model representing an integration."""

    invalid: bool
    "Whether the integration configuration is invalid or misconfigured"
    model_registry_token_id: UUID
    "Unique identifier for the model registry token"
    provider: IntegrationProvider
    "The integration provider type (e.g., OpenAI, Azure, etc.)"
    provider_domain: str
    "Domain or endpoint URL for the integration provider"
