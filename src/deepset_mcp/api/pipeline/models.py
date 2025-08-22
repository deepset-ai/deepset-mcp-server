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
    "Unique identifier for the pipeline"
    name: str
    "Human-readable name of the pipeline"
    status: str
    "Current operational status of the pipeline"
    service_level: PipelineServiceLevel
    "Service level indicating the deployment stage"

    created_at: datetime
    "Timestamp when the pipeline was created"
    last_updated_at: datetime | None = Field(None, alias="last_edited_at")  # Map API's last_edited_at
    "Timestamp when the pipeline was last modified"

    created_by: DeepsetUser
    "User who created the pipeline"
    last_updated_by: DeepsetUser | None = Field(None, alias="last_edited_by")  # Map API's last_edited_by
    "User who last modified the pipeline"

    yaml_config: str | None = None
    "YAML configuration defining the pipeline structure"

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
    "Error code identifying the type of validation error"
    message: str
    "Human-readable description of the validation error"


class PipelineValidationResult(BaseModel):
    """Result of validating a pipeline configuration."""

    valid: bool
    "Whether the pipeline configuration is valid"
    errors: list[ValidationError] = []
    "List of validation errors if the pipeline is invalid"

    def __rich_repr__(self) -> Result:
        """Used to display the model in an LLM friendly way."""
        yield "valid", self.valid
        yield "errors", [f"{e.message} ({e.code})" for e in self.errors]


class TraceFrame(BaseModel):
    """Model representing a single frame in a stack trace."""

    filename: str
    "Name of the file where the trace frame occurred"
    line_number: int
    "Line number in the file where the trace frame occurred"
    name: str
    "Function or method name where the trace frame occurred"


class ExceptionInfo(BaseModel):
    """Model representing exception information."""

    type: str
    "Exception class name"
    value: str
    "Exception message or string representation"
    trace: list[TraceFrame]
    "Stack trace frames leading to the exception"


class PipelineLog(BaseModel):
    """Model representing a single log entry from a pipeline."""

    log_id: str
    "Unique identifier for the log entry"
    message: str
    "Log message content"
    logged_at: datetime
    "Timestamp when the log entry was created"
    level: str
    "Log level (e.g., INFO, WARNING, ERROR)"
    origin: str
    "Source component or service that generated the log"
    exceptions: list[ExceptionInfo] | None = None
    "Exception information if the log contains error details"
    extra_fields: dict[str, Any] = Field(default_factory=dict)
    "Additional metadata fields associated with the log entry"


# Search-related models


class OffsetRange(BaseModel):
    """Model representing an offset range."""

    start: int
    "Starting position of the offset range"
    end: int
    "Ending position of the offset range"


class DeepsetAnswer(BaseModel):
    """Model representing a search answer."""

    answer: str  # Required field
    "The generated answer text"
    context: str | None = None
    "Context text used to generate the answer"
    document_id: str | None = None
    "Identifier of the source document"
    document_ids: list[str] | None = None
    "List of source document identifiers"
    file: dict[str, Any] | None = None
    "File metadata associated with the answer"
    files: list[dict[str, Any]] | None = None
    "List of file metadata associated with the answer"
    meta: dict[str, Any] | None = None
    "Additional metadata about the answer"
    offsets_in_context: list[OffsetRange] | None = None
    "Character offset ranges within the context text"
    offsets_in_document: list[OffsetRange] | None = None
    "Character offset ranges within the source document"
    prompt: str | None = None
    "Prompt used to generate the answer"
    result_id: UUID | None = None
    "Unique identifier for this result"
    score: float | None = None
    "Confidence or relevance score for the answer"
    type: str | None = None
    "Type classification of the answer"


class DeepsetDocument(BaseModel):
    """Model representing a search document."""

    content: str  # Required field
    "Text content of the document"
    meta: dict[str, Any]  # Required field - can hold any value
    "Metadata dictionary containing document properties"
    embedding: list[float] | None = None
    "Vector embedding representation of the document"
    file: dict[str, Any] | None = None
    "File metadata if the document originated from a file"
    id: str | None = None
    "Unique identifier for the document"
    result_id: UUID | None = None
    "Unique identifier for this search result"
    score: float | None = None
    "Relevance or similarity score for the document"


class DeepsetSearchResponse(BaseModel):
    """Model representing a single search result."""

    debug: dict[str, Any] | None = Field(default=None, alias="_debug")
    "Debug information for the search operation"
    answers: list[DeepsetAnswer] = Field(default_factory=list)
    "List of generated answers from the search"
    documents: list[DeepsetDocument] = Field(default_factory=list)
    "List of retrieved documents from the search"
    prompts: dict[str, str] | None = None
    "Prompts used during the search operation"
    query: str | None = None
    "Original search query text"
    query_id: UUID | None = None
    "Unique identifier for the search query"

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
    "Incremental text content for streaming responses"
    meta: dict[str, Any] | None = None
    "Metadata associated with the streaming delta"


class DeepsetStreamEvent(BaseModel):
    """Model representing a stream event."""

    query_id: str | UUID | None = None
    "Unique identifier for the associated query"
    type: str  # "delta", "result", or "error"
    "Event type: 'delta', 'result', or 'error'"
    delta: StreamDelta | None = None
    "Streaming text delta if type is 'delta'"
    result: DeepsetSearchResponse | None = None
    "Complete search result if type is 'result'"
    error: str | None = None
    "Error message if type is 'error'"


class LogLevel(StrEnum):
    """Log level filter options for pipeline logs."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
