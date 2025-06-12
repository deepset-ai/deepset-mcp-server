from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

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


class ValidationError(BaseModel):
    """Model representing a validation error from the pipeline validation API."""

    code: str
    message: str


class PipelineValidationResult(BaseModel):
    """Result of validating a pipeline configuration."""

    valid: bool
    errors: list[ValidationError] = []


class NoContentResponse(BaseModel):
    """Response model for an empty response."""

    success: bool = True
    message: str = "No content"


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


class Answer(BaseModel):
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


class Document(BaseModel):
    """Model representing a search document."""

    content: str  # Required field
    meta: dict[str, Any]  # Required field - can hold any value
    embedding: list[float] | None = None
    file: dict[str, Any] | None = None
    id: str | None = None
    result_id: UUID | None = None
    score: float | None = None


class SearchResult(BaseModel):
    """Model representing a single search result."""

    _debug: dict[str, Any] | None = None
    answers: list[Answer] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    prompts: dict[str, str] | None = None
    query: str | None = None
    query_id: UUID | None = None


class SearchResponse(BaseModel):
    """Model representing the response from a pipeline search."""

    query_id: UUID | None = None
    results: list[SearchResult] = Field(default_factory=list)


class FilterCondition(BaseModel):
    """Model representing a single filter condition."""

    field: str
    value: Any
    operator: str | None = None


class SearchFilters(BaseModel):
    """Model representing search filters."""

    conditions: list[FilterCondition] = Field(default_factory=list)


class StreamDelta(BaseModel):
    """Model representing a streaming delta."""

    text: str
    meta: Optional[Dict[str, Any]] = None


class StreamEvent(BaseModel):
    """Model representing a stream event."""

    query_id: Optional[UUID] = None
    type: str  # "delta", "result", or "error"
    delta: Optional[StreamDelta] = None
    result: Optional[SearchResponse] = None
    error: Optional[str] = None
