# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    yaml_config: str | None = None
    tags: list[PipelineTemplateTag]
    pipeline_type: PipelineType

    @model_validator(mode="before")
    @classmethod
    def populate_yaml_config(cls, values: Any) -> Any:
        """Populate yaml_config from query_yaml or indexing_yaml based on pipeline_type."""
        if not isinstance(values, dict):
            return values

        # Skip if yaml_config is already set
        if values.get("yaml_config") is not None:
            return values

        # Get pipeline_type from the model data
        pipeline_type = values.get("pipeline_type")

        if pipeline_type == PipelineType.INDEXING or pipeline_type == "indexing":
            yaml_config = values.get("indexing_yaml")
        elif pipeline_type == PipelineType.QUERY or pipeline_type == "query":
            yaml_config = values.get("query_yaml")
        else:
            yaml_config = None

        if yaml_config is not None:
            values["yaml_config"] = yaml_config

        return values


class PipelineTemplateList(BaseModel):
    """Response model for listing pipeline templates."""

    data: list[PipelineTemplate]
    has_more: bool
    total: int


class PipelineTemplateSearchResult(BaseModel):
    """Model representing a search result for pipeline templates."""

    template: PipelineTemplate
    similarity_score: float


class PipelineTemplateSearchResults(BaseModel):
    """Response model for pipeline template search results."""

    results: list[PipelineTemplateSearchResult]
    query: str
    total_found: int
