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
    model_registry_token_id: UUID
    provider: IntegrationProvider
    provider_domain: str


class IntegrationList(BaseModel):
    """Model representing a list of integrations."""

    integrations: list[Integration]

    def __len__(self) -> int:
        """Return the length of the list.

        :returns: Number of integrations.
        """
        return len(self.integrations)
