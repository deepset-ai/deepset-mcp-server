# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Data models for Haystack service tool outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComponentInitParameter(BaseModel):
    """Represents an initialization parameter for a Haystack component."""

    name: str
    annotation: str
    description: str
    default: Any | None = None
    required: bool = False


class ComponentIOProperty(BaseModel):
    """Represents an input/output property schema."""

    name: str
    annotation: str
    description: str
    type: str
    required: bool = False


class ComponentIODefinition(BaseModel):
    """Represents a definition referenced in I/O schema."""

    name: str
    type: str
    properties: dict[str, ComponentIOProperty]
    required: list[str]


class ComponentIOSchema(BaseModel):
    """Represents the input/output schema for a component."""

    properties: dict[str, ComponentIOProperty]
    required: list[str]
    definitions: dict[str, ComponentIODefinition] = Field(default_factory=dict)


class ComponentDefinition(BaseModel):
    """Represents a complete Haystack component definition."""

    component_type: str
    title: str
    description: str
    family: str
    family_description: str
    init_parameters: list[ComponentInitParameter] = Field(default_factory=list)
    input_schema: ComponentIOSchema | None = None
    output_schema: ComponentIOSchema | None = None
    error_message: str | None = None
    is_custom: bool = False
    package_version: str | None = None
    dynamic_params: bool = False


class ComponentSearchResult(BaseModel):
    """Represents a search result for a component."""

    component: ComponentDefinition
    similarity_score: float


class ComponentSearchResults(BaseModel):
    """Response model for component search results."""

    results: list[ComponentSearchResult]
    query: str
    total_found: int


class ComponentFamily(BaseModel):
    """Represents a Haystack component family."""

    name: str
    description: str


class ComponentFamilyList(BaseModel):
    """Response model for listing component families."""

    families: list[ComponentFamily]
    total_count: int


class ComponentDefinitionList(BaseModel):
    """Response model for listing component definitions."""

    components: list[ComponentDefinition]
    total_count: int
