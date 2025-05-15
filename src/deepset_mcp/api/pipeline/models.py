from datetime import datetime
from enum import StrEnum

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
