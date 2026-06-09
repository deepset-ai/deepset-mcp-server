# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from rich.repr import Result


class PipelineType(StrEnum):
    """Enum representing the type of a pipeline template."""

    QUERY = "query"
    INDEXING = "indexing"


class PipelineTemplateTag(BaseModel):
    """Model representing a tag on a pipeline template."""

    name: str
    "Human-readable name of the tag"
    tag_id: UUID
    "Unique identifier for the tag"


class PipelineTemplate(BaseModel):
    """Model representing a pipeline template."""

    author: str
    "Name of the template author or creator"
    best_for: list[str]
    "List of use cases this template is best suited for"
    description: str
    "Detailed description of the pipeline template"
    template_name: str = Field(alias="pipeline_name")
    "Internal name identifier for the template"
    display_name: str = Field(alias="name")
    "User-friendly display name for the template"
    pipeline_template_id: UUID = Field(alias="pipeline_template_id")
    "Unique identifier for the pipeline template"
    potential_applications: list[str] = Field(alias="potential_applications")
    "List of potential applications and scenarios for this template"
    yaml_config: str | None = None
    "YAML configuration defining the pipeline structure"
    tags: list[PipelineTemplateTag]
    "List of tags associated with the template for categorization"
    pipeline_type: PipelineType
    "Type of pipeline (query or indexing)"

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

    def __rich_repr__(self) -> Result:
        """Used to display the model in an LLM friendly way."""
        yield "template_name", self.template_name
        yield "display_name", self.display_name
        yield "pipeline_template_id", str(self.pipeline_template_id)
        yield "description", self.description
        yield "best_for", self.best_for
        yield "potential_applications", self.potential_applications
        yield "pipeline_type", self.pipeline_type
        yield "tags", [tag.name for tag in self.tags]
        yield "author", self.author
        yield "yaml_config", self.yaml_config if self.yaml_config is not None else "Get full template to see config."
