# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the model API."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, SerializerFunctionWrapHandler, model_serializer, model_validator

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


class ModelCategory(StrEnum):
    """What a model does. Without a category, the API lists only LLMs."""

    LLM = "LLM"
    EMBEDDER = "EMBEDDER"
    RANKER = "RANKER"


class ModelStage(StrEnum):
    """How far a hosted model is from general use. A model without a stage is offered to everyone."""

    EXPERIMENTAL = "EXPERIMENTAL"
    LEGACY = "LEGACY"


class ModelComponent(BaseModel):
    """A pipeline component that runs the model, as it goes into a pipeline YAML."""

    type: str
    "The component type, as in a pipeline YAML"
    init_parameters: dict[str, Any]
    "The component's init parameters, as in a pipeline YAML"


class ModelDetails(BaseModel):
    """What users compare embedders and rerankers on. Every field is optional: a model may not have it."""

    embedding_dimension: int | None = None
    "The length of the vectors the embedder returns"
    max_input_tokens: int | None = None
    "The longest input the model reads, in tokens. Longer input is truncated."
    modalities: list[str] | None = None
    "The kinds of input the model accepts, e.g. 'text'"
    languages: list[str] | None = None
    "ISO 639-1 codes such as 'en', or 'multilingual' for a model trained on about 100 languages"
    mteb_score: float | None = None
    "Retrieval score on the MTEB leaderboard, benchmark MTEB(Multilingual, v2), as a percentage"
    mteb_url: str | None = None
    "The MTEB leaderboard view the score comes from"


class ModelPrice(BaseModel):
    """The effective price of a model, in USD per 1,000 tokens, with custom prices applied."""

    input_price_per_1k_tokens: float
    "Price per 1,000 input tokens"
    output_price_per_1k_tokens: float
    "Price per 1,000 output tokens"
    cache_read_price_per_1k_tokens: float | None = None
    "Price per 1,000 cache-read tokens, if the model has one"
    cache_write_price_per_1k_tokens: float | None = None
    "Price per 1,000 cache-write tokens, if the model has one"
    cache_write_1h_price_per_1k_tokens: float | None = None
    "Price per 1,000 one-hour cache-write tokens, if the model has one"
    source: str
    'How the price entry was created, e.g. "workspace-override" or "org-override" for a custom price'


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
    price: ModelPrice | None = None
    "The effective price of the model. Only set when prices were requested and the model has a known price."
    category: ModelCategory | None = None
    "EMBEDDER or RANKER for the models deepset hosts. Not set for LLMs."
    components: dict[str, ModelComponent] | None = None
    "The pipeline components that run the model, by role: `text_embedder` (query pipeline) and "
    "`document_embedder` (indexing pipeline) for an embedder, `ranker` (query pipeline) for a ranker."
    stage: ModelStage | None = None
    "EXPERIMENTAL for a model still being tried out, LEGACY for one to move away from. Not set otherwise."
    details: ModelDetails | None = None
    "Properties to compare embedders and rerankers on. Only set when known."

    @model_serializer(mode="wrap")
    def _omit_missing_optional_fields(self, handler: SerializerFunctionWrapHandler):  # type: ignore[no-untyped-def]
        """Leave the optional fields out unless set, so an LLM's output looks as before.

        Deliberately unannotated: a return annotation would replace the model's serialization JSON schema.
        """
        data = handler(self)
        for key in ("price", "category", "components", "stage", "details"):
            if data.get(key) is None:
                data.pop(key, None)
        return data

    @model_validator(mode="before")
    @classmethod
    def _infer_model(cls, data: Any) -> Any:
        """Populate `model` if not set explicitly.

        From chat_generator_config.init_parameters.model for an LLM, else from the first component's
        init_parameters.model (an embedder or ranker has an empty chat_generator_config).
        """
        if not isinstance(data, dict) or data.get("model") is not None:
            return data

        configs = [data.get("chat_generator_config")]
        components = data.get("components")
        if isinstance(components, dict):
            configs.extend(components.values())
        for config in configs:
            init_parameters = config.get("init_parameters") if isinstance(config, dict) else None
            if isinstance(init_parameters, dict) and isinstance(init_parameters.get("model"), str):
                data["model"] = init_parameters["model"]
                break

        return data


class ModelList(BaseModel):
    """A page of models returned by the workspace models listing endpoint."""

    data: list[Model]
    "Models on the current page"
    has_more: bool
    "Whether there are more models available beyond this page"
    total: int
    "Total number of models across all pages"
