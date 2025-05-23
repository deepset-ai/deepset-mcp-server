from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineType(StrEnum):
    """Enum representing the type of a pipeline template."""

    QUERY = "query"
    INDEXING = "indexing"


class PipelineTemplateTag(BaseModel):
    """Model representing a tag on a pipeline template."""

    name: str
    tag_id: UUID


class PipelineTemplate(BaseModel):
    """Model representing a pipeline template."""

    author: str
    best_for: list[str]
    description: str
    template_name: str = Field(alias="pipeline_name")
    display_name: str = Field(alias="name")
    pipeline_template_id: UUID = Field(alias="pipeline_template_id")
    potential_applications: list[str] = Field(alias="potential_applications")
    yaml_config: str | None = Field(None, alias="query_yaml")
    tags: list[PipelineTemplateTag]
    pipeline_type: PipelineType
