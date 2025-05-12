from datetime import datetime
from enum import StrEnum
from typing import List

from pydantic import BaseModel, Field


class PipelineServiceLevel(StrEnum):
    """Describes the service level of a pipeline."""

    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    DRAFT = "DRAFT"


class DeepsetUser(BaseModel):
    """Model representing a user on the deepset platform."""

    id: str = Field(alias="user_id")
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None


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
    errors: List[ValidationError] = []
