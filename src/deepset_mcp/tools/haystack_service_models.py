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
    "Name of the initialization parameter"
    annotation: str
    "Type annotation string for the parameter"
    description: str
    "Human-readable description of the parameter"
    default: Any | None = None
    "Default value for the parameter, if any"
    required: bool = False
    "Whether this parameter is required for component initialization"


class ComponentIOProperty(BaseModel):
    """Represents an input/output property schema."""

    name: str
    "Name of the input/output property"
    annotation: str
    "Type annotation string for the property"
    description: str
    "Human-readable description of the property"
    type: str
    "Type classification of the property"
    required: bool = False
    "Whether this property is required"


class ComponentIODefinition(BaseModel):
    """Represents a definition referenced in I/O schema."""

    name: str
    "Name of the I/O definition"
    type: str
    "Type classification of the definition"
    properties: dict[str, ComponentIOProperty]
    "Dictionary of properties within this definition"
    required: list[str]
    "List of required property names"


class ComponentIOSchema(BaseModel):
    """Represents the input/output schema for a component."""

    properties: dict[str, ComponentIOProperty]
    "Dictionary of input/output properties"
    required: list[str]
    "List of required property names"
    definitions: dict[str, ComponentIODefinition] = Field(default_factory=dict)
    "Dictionary of type definitions referenced by properties"


class ComponentDefinition(BaseModel):
    """Represents a complete Haystack component definition."""

    component_type: str
    "Fully qualified class name of the component"
    title: str
    "Human-readable title of the component"
    description: str
    "Detailed description of the component's functionality"
    family: str
    "Component family name (e.g., 'retrievers', 'generators')"
    family_description: str
    "Description of the component family"
    init_parameters: list[ComponentInitParameter] = Field(default_factory=list)
    "List of parameters required for component initialization"
    input_schema: ComponentIOSchema | None = None
    "Schema defining the component's input requirements"
    output_schema: ComponentIOSchema | None = None
    "Schema defining the component's output format"
    error_message: str | None = None
    "Error message if component definition failed to load"
    is_custom: bool = False
    "Whether this is a custom user-defined component"
    package_version: str | None = None
    "Version of the package containing this component"
    dynamic_params: bool = False
    "Whether the component accepts dynamic parameters"


class ComponentSearchResult(BaseModel):
    """Represents a search result for a component."""

    component: ComponentDefinition
    "Component definition that matched the search criteria"
    similarity_score: float
    "Relevance score indicating how well the component matches the search"


class ComponentSearchResults(BaseModel):
    """Response model for component search results."""

    results: list[ComponentSearchResult]
    "List of components matching the search criteria"
    query: str
    "Original search query string"
    total_found: int
    "Total number of components found matching the search criteria"


class ComponentFamily(BaseModel):
    """Represents a Haystack component family."""

    name: str
    "Name of the component family"
    description: str
    "Description of the component family and its purpose"


class ComponentFamilyList(BaseModel):
    """Response model for listing component families."""

    families: list[ComponentFamily]
    "List of available component families"
    total_count: int
    "Total number of component families available"


class ComponentDefinitionList(BaseModel):
    """Response model for listing component definitions."""

    components: list[ComponentDefinition]
    "List of component definitions"
    total_count: int
    "Total number of components available"
