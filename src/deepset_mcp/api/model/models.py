# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the model API."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, model_validator

from deepset_mcp.api.shared_models import DeepsetUser


class ModelOrigin(StrEnum):
    """Where a model definition comes from."""

    WORKSPACE = "WORKSPACE"
    ORGANIZATION = "ORGANIZATION"
    PLATFORM = "PLATFORM"


class ModelProvider(StrEnum):
    """Well-known providers of models.

    This is not an exhaustive list of all providers a model may report. Other provider values
    (e.g. from custom or newly added integrations) are still valid and accepted as plain strings.
    """

    AWS_BEDROCK = "aws-bedrock"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class Model(BaseModel):
    """A model that can be used to configure generator components in a pipeline."""

    model_id: UUID
    "Unique identifier for the model"
    name: str
    "Name of the model, e.g. 'gpt-4o'"
    provider: str
    "Provider of the model, e.g. 'openai'"
    model: str | None = None
    "The underlying model identifier used by the chat generator, e.g. 'gpt-4o'. Extracted from "
    "`chat_generator_config.init_parameters.model`."
    connected: bool | None = None
    "Whether the workspace has a valid integration to use this model. None if not evaluated."
    origin: ModelOrigin = ModelOrigin.PLATFORM
    "Whether the model is a workspace/organization-scoped custom model or a predefined platform model"
    chat_generator_config: dict[str, Any]
    "The default configuration for the chat generator as expected in a pipeline YAML"
    generation_kwargs: dict[str, Any]
    "The available configuration options for the model as OpenAPI schema"
    created_by: DeepsetUser | None = None
    "User who created the model, if it is a custom model"
    last_updated_by: DeepsetUser | None = None
    "User who last updated the model, if it is a custom model"
    created_at: datetime | None = None
    "Timestamp when the model was created, if it is a custom model"
    updated_at: datetime | None = None
    "Timestamp when the model was last updated, if it is a custom model"

    @model_validator(mode="before")
    @classmethod
    def _infer_model(cls, data: Any) -> Any:
        """Populate `model` from chat_generator_config.init_parameters.model if not set explicitly."""
        if not isinstance(data, dict) or data.get("model") is not None:
            return data

        chat_generator_config = data.get("chat_generator_config")
        if not isinstance(chat_generator_config, dict):
            return data

        init_parameters = chat_generator_config.get("init_parameters")
        if isinstance(init_parameters, dict) and isinstance(init_parameters.get("model"), str):
            data["model"] = init_parameters["model"]

        return data


class ModelList(BaseModel):
    """A page of models returned by the workspace models listing endpoint."""

    data: list[Model]
    "Models on the current page"
    has_more: bool
    "Whether there are more models available beyond this page"
    total: int
    "Total number of models across all pages"
