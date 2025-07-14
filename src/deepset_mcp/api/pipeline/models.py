# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from rich.repr import Result

from deepset_mcp.api.shared_models import DeepsetUser


class PipelineServiceLevel(StrEnum):
    """Describes the service level of a pipeline."""

    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    DRAFT = "DRAFT"


class DeepsetPipeline(BaseModel):
    """Model representing a pipeline on the deepset platform."""

    id: str = Field(alias="pipeline_id")
    name: str
    status: str
    service_level: PipelineServiceLevel

    created_at: datetime
    last_updated_at: datetime | None = Field(None, alias="last_edited_at")  # Map API's last_edited_at

    created_by: DeepsetUser
    last_updated_by: DeepsetUser | None = Field(None, alias="last_edited_by")  # Map API's last_edited_by

    yaml_config: str | None = None

    class Config:
        """Configuration for serialization and deserialization."""

        populate_by_name = True  # Allow both alias and model field names
        json_encoders = {
            # When serializing back to JSON, convert datetimes to ISO format
            datetime: lambda dt: dt.isoformat()
        }

    def __rich_repr__(self) -> Result:
        """Used to display the model in an LLM friendly way."""
        yield "name", self.name
        yield "service_level", self.service_level.value
        yield "status", self.status
        yield "created_by", f"{self.created_by.given_name} {self.created_by.family_name} ({self.created_by.id})"
        yield "created_at", self.created_at.strftime("%m/%d/%Y %I:%M:%S %p")
        yield (
            "last_updated_by",
            f"{self.last_updated_by.given_name} {self.last_updated_by.family_name} ({self.last_updated_by.id})"
            if self.last_updated_by
            else None,
        )
        yield "last_updated_at", self.last_updated_at.strftime("%m/%d/%Y %I:%M:%S %p") if self.last_updated_at else None
        yield "yaml_config", self.yaml_config if self.yaml_config is not None else "Get full pipeline to see config."


class ValidationError(BaseModel):
    """Model representing a validation error from the pipeline validation API."""

    code: str
    message: str


class PipelineValidationResult(BaseModel):
    """Result of validating a pipeline configuration."""

    valid: bool
    errors: list[ValidationError] = []

    def __rich_repr__(self) -> Result:
        """Used to display the model in an LLM friendly way."""
        yield "valid", self.valid
        yield "errors", [f"{e.message} ({e.code})" for e in self.errors]


class TraceFrame(BaseModel):
    """Model representing a single frame in a stack trace."""

    filename: str
    line_number: int
    name: str


class ExceptionInfo(BaseModel):
    """Model representing exception information."""

    type: str
    value: str
    trace: list[TraceFrame]


class PipelineLog(BaseModel):
    """Model representing a single log entry from a pipeline."""

    log_id: str
    message: str
    logged_at: datetime
    level: str
    origin: str
    exceptions: list[ExceptionInfo] | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)


class PipelineLogList(BaseModel):
    """Model representing a paginated list of pipeline logs."""

    data: list[PipelineLog]
    has_more: bool
    total: int


# Search-related models


class OffsetRange(BaseModel):
    """Model representing an offset range."""

    start: int
    end: int


class DeepsetAnswer(BaseModel):
    """Model representing a search answer."""

    answer: str  # Required field
    context: str | None = None
    document_id: str | None = None
    document_ids: list[str] | None = None
    file: dict[str, Any] | None = None
    files: list[dict[str, Any]] | None = None
    meta: dict[str, Any] | None = None
    offsets_in_context: list[OffsetRange] | None = None
    offsets_in_document: list[OffsetRange] | None = None
    prompt: str | None = None
    result_id: UUID | None = None
    score: float | None = None
    type: str | None = None


class DeepsetDocument(BaseModel):
    """Model representing a search document."""

    content: str  # Required field
    meta: dict[str, Any]  # Required field - can hold any value
    embedding: list[float] | None = None
    file: dict[str, Any] | None = None
    id: str | None = None
    result_id: UUID | None = None
    score: float | None = None


class DeepsetSearchResponse(BaseModel):
    """Model representing a single search result."""

    debug: dict[str, Any] | None = Field(default=None, alias="_debug")
    answers: list[DeepsetAnswer] = Field(default_factory=list)
    documents: list[DeepsetDocument] = Field(default_factory=list)
    prompts: dict[str, str] | None = None
    query: str | None = None
    query_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_response(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize the response from the search and search-stream endpoints.

        The search endpoint returns a list of results, but we only ever use the first result.
        We are not sending batch queries, so there will never be more than one result.
        We use this validator to transform the data so that we can use the same response model for search and
            search-stream endpoints.
        """
        # Handle non-stream format with 'results' array
        if "results" in data and isinstance(data["results"], list):
            if len(data["results"]) > 0:
                first_result = data["results"][
                    0
                ]  # we only ever care for the first result as we don't use batch queries
                normalized = {
                    "query_id": data.get("query_id", first_result.get("query_id")),
                    "query": first_result.get("query"),
                    "answers": first_result.get("answers", []),
                    "documents": first_result.get("documents", []),
                    "prompts": first_result.get("prompts"),
                    "_debug": first_result.get("_debug") or first_result.get("debug"),
                }
                return normalized
            else:
                return {}
        else:
            return data


class StreamDelta(BaseModel):
    """Model representing a streaming delta."""

    text: str
    meta: dict[str, Any] | None = None


class DeepsetStreamEvent(BaseModel):
    """Model representing a stream event."""

    query_id: str | UUID | None = None
    type: str  # "delta", "result", or "error"
    delta: StreamDelta | None = None
    result: DeepsetSearchResponse | None = None
    error: str | None = None


class PipelineList(BaseModel):
    """Response model for listing pipelines."""

    data: list[DeepsetPipeline]
    has_more: bool
    total: int


class PipelineValidationResultWithYaml(BaseModel):
    """Model for pipeline validation result that includes the original YAML."""

    validation_result: PipelineValidationResult
    yaml_config: str


class PipelineOperationWithErrors(BaseModel):
    """Model for pipeline operations that complete with validation errors."""

    message: str
    validation_result: PipelineValidationResult
    pipeline: DeepsetPipeline
