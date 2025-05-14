from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineTemplateTag(BaseModel):
    """Model representing a tag on a pipeline template."""

    name: str
    tag_id: UUID


class PipelineTemplate(BaseModel):
    """Model representing a pipeline template."""

    author: str
    available_to_all_organization_types: bool = Field(alias="available_to_all_organization_types")
    best_for: list[str]
    deepset_cloud_version: str = Field(alias="deepset_cloud_version")
    description: str
    expected_output: list[str] = Field(alias="expected_output")
    template_name: str = Field(alias="pipeline_name")
    pipeline_template_id: UUID = Field(alias="pipeline_template_id")
    pipeline_type: Literal["indexing", "query"]
    potential_applications: list[str] = Field(alias="potential_applications")
    query_yaml: Optional[str] = Field(alias="query_yaml")
    recommended_dataset: list[str] = Field(alias="recommended_dataset")
    tags: list[PipelineTemplateTag]