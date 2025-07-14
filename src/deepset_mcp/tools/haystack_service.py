# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
from typing import Any

import numpy as np

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.haystack_service_models import (
    ComponentDefinition,
    ComponentDefinitionList,
    ComponentFamily,
    ComponentFamilyList,
    ComponentInitParameter,
    ComponentIODefinition,
    ComponentIOProperty,
    ComponentIOSchema,
    ComponentSearchResult,
    ComponentSearchResults,
)
from deepset_mcp.tools.model_protocol import ModelProtocol


def extract_component_texts(*, component_def: dict[str, Any]) -> tuple[str, str]:
    """Extracts the component name and description for embedding.

    Args:
        component_def: The component definition

    Returns:
        A tuple containing the component name and description
    """
    component_type = component_def["properties"]["type"]["const"]
    name = component_def.get("title", "")
    description = component_def.get("description", "")
    return component_type, f"{name} {description}"


async def _build_component_definition(
    *, component_def: dict[str, Any], component_type: str, haystack_service: Any, schema: dict[str, Any] | None = None
) -> ComponentDefinition | str:
    """Build a ComponentDefinition from component schema data."""
    try:
        # Extract basic info
        component_type_info = component_def["properties"]["type"]
        init_params_schema = component_def["properties"].get("init_parameters", {}).get("properties", {})
        required_params = component_def["properties"].get("init_parameters", {}).get("required", [])

        # Build init parameters
        init_params = [
            ComponentInitParameter(
                name=param_name,
                annotation=param_info.get("_annotation", param_info.get("type", "Unknown")),
                description=param_info.get("description", "No description available."),
                default=param_info.get("default"),
                required=param_name in required_params,
            )
            for param_name, param_info in init_params_schema.items()
        ]

        # Try to get I/O schema
        input_schema = None
        output_schema = None
        error_message = None

        try:
            component_name = component_type.split(".")[-1]
            io_info = await haystack_service.get_component_input_output(component_name)

            # Build input schema
            if "input" in io_info:
                input_props = io_info["input"].get("properties", {})
                input_required = io_info["input"].get("required", [])
                input_properties = {
                    prop_name: ComponentIOProperty(
                        name=prop_name,
                        annotation=prop_info.get("_annotation", prop_info.get("type", "Unknown")),
                        description=prop_info.get("description", "No description available."),
                        type=prop_info.get("type", "Unknown"),
                        required=prop_name in input_required,
                    )
                    for prop_name, prop_info in input_props.items()
                }
                input_schema = ComponentIOSchema(properties=input_properties, required=input_required)

            # Build output schema
            if "output" in io_info and isinstance(io_info["output"], dict):
                output_info = io_info["output"]
                if "properties" in output_info:
                    output_props = output_info.get("properties", {})
                    output_required = output_info.get("required", [])
                    output_properties = {
                        prop_name: ComponentIOProperty(
                            name=prop_name,
                            annotation=prop_info.get("_annotation", prop_info.get("type", "Unknown")),
                            description=prop_info.get("description", "No description available."),
                            type=prop_info.get("type", "Unknown"),
                            required=prop_name in output_required,
                        )
                        for prop_name, prop_info in output_props.items()
                    }

                    # Build definitions
                    definitions = {}
                    if "definitions" in output_info:
                        for def_name, def_info in output_info["definitions"].items():
                            if "properties" in def_info:
                                def_required = def_info.get("required", [])
                                def_properties = {
                                    prop_name: ComponentIOProperty(
                                        name=prop_name,
                                        annotation=prop_info.get("_annotation", prop_info.get("type", "Unknown")),
                                        description=prop_info.get("description", "No description available."),
                                        type=prop_info.get("type", "Unknown"),
                                        required=prop_name in def_required,
                                    )
                                    for prop_name, prop_info in def_info["properties"].items()
                                }
                                definitions[def_name] = ComponentIODefinition(
                                    name=def_name,
                                    type=def_info.get("type", "object"),
                                    properties=def_properties,
                                    required=def_required,
                                )

                    output_schema = ComponentIOSchema(
                        properties=output_properties, required=output_required, definitions=definitions
                    )
        except Exception as e:
            error_message = f"Failed to fetch input/output schema: {str(e)}"

        # Check if this is a custom component
        is_custom = schema is not None and "package_version" in schema
        package_version = schema.get("package_version") if schema else None
        dynamic_params = schema.get("dynamic_params", False) if schema else False

        return ComponentDefinition(
            component_type=component_type,
            title=component_def.get("title", "Unknown"),
            description=component_def.get("description", "No description available."),
            family=component_type_info.get("family", "Unknown"),
            family_description=component_type_info.get("family_description", "No description available."),
            init_parameters=init_params,
            input_schema=input_schema,
            output_schema=output_schema,
            error_message=error_message,
            is_custom=is_custom,
            package_version=package_version,
            dynamic_params=dynamic_params,
        )
    except Exception as e:
        return f"Failed to build component definition: {str(e)}"


async def get_component_definition(*, client: AsyncClientProtocol, component_type: str) -> ComponentDefinition | str:
    """Returns the definition of a specific Haystack component.

    Args:
        client: The API client to use
        component_type: Fully qualified component type
            (e.g. haystack.components.routers.conditional_router.ConditionalRouter)

    Returns:
        ComponentDefinition model or error message string
    """
    haystack_service = client.haystack_service()

    try:
        response = await haystack_service.get_component_schemas()
    except UnexpectedAPIError as e:
        return f"Failed to retrieve component definition: {e}"

    components = response["component_schema"]["definitions"]["Components"]

    # Find the component by its type
    component_def = None
    for comp in components.values():
        if comp["properties"]["type"].get("const") == component_type:
            component_def = comp
            break

    if not component_def:
        return f"Component not found: {component_type}"

    return await _build_component_definition(
        component_def=component_def, component_type=component_type, haystack_service=haystack_service
    )


async def search_component_definition(
    *, client: AsyncClientProtocol, query: str, model: ModelProtocol, top_k: int = 5
) -> ComponentSearchResults | str:
    """Searches for components based on name or description using semantic similarity.

    Args:
        client: The API client to use
        query: The search query
        model: The model to use for computing embeddings
        top_k: Maximum number of results to return (default: 5)

    Returns:
        ComponentSearchResults model or error message string
    """
    haystack_service = client.haystack_service()

    try:
        response = await haystack_service.get_component_schemas()
    except UnexpectedAPIError as e:
        return f"Failed to retrieve component schemas: {e}"

    components = response["component_schema"]["definitions"]["Components"]

    # Extract text for embedding from all components
    component_texts: list[tuple[str, str]] = [
        extract_component_texts(component_def=comp) for comp in components.values()
    ]
    component_types: list[str] = [c[0] for c in component_texts]

    if not component_texts:
        return ComponentSearchResults(results=[], query=query, total_found=0)

    # Compute embeddings
    query_embedding = model.encode(query)
    component_embeddings = model.encode([text for _, text in component_texts])

    query_embedding_reshaped = query_embedding.reshape(1, -1)

    # Calculate dot product between target and all paths
    # This gives us a similarity score for each path
    similarities = np.dot(component_embeddings, query_embedding_reshaped.T).flatten()

    # Create (path, similarity) pairs
    component_similarities = list(zip(component_types, similarities, strict=False))

    # Sort by similarity score in descending order
    component_similarities.sort(key=lambda x: x[1], reverse=True)

    top_components = component_similarities[:top_k]
    search_results = []
    for component_type, sim in top_components:
        # Find the component definition by type
        component_def = None
        for comp in components.values():
            if comp["properties"]["type"].get("const") == component_type:
                component_def = comp
                break

        if component_def:
            definition = await _build_component_definition(
                component_def=component_def, component_type=component_type, haystack_service=haystack_service
            )
            if isinstance(definition, ComponentDefinition):
                search_results.append(ComponentSearchResult(component=definition, similarity_score=float(sim)))

    return ComponentSearchResults(results=search_results, query=query, total_found=len(search_results))


async def list_component_families(*, client: AsyncClientProtocol) -> ComponentFamilyList | str:
    """Lists all Haystack component families that are available on deepset.

    Args:
        client: The API client to use

    Returns:
        ComponentFamilyList model or error message string
    """
    haystack_service = client.haystack_service()

    try:
        response = await haystack_service.get_component_schemas()
    except UnexpectedAPIError as e:
        return f"Failed to retrieve component families: {e}"

    components = response["component_schema"]["definitions"]["Components"]

    families = {}
    for component_def in components.values():
        component_type = component_def["properties"]["type"]
        family = component_type["family"]
        description = component_type.get("family_description", "No description available.")
        families[family] = description

    if not families:
        return "No component families found in the response"

    # Convert to ComponentFamily objects
    family_objects = [
        ComponentFamily(name=family, description=description) for family, description in sorted(families.items())
    ]

    return ComponentFamilyList(families=family_objects, total_count=len(family_objects))


async def get_custom_components(*, client: AsyncClientProtocol) -> ComponentDefinitionList | str:
    """Get a list of all installed custom components.

    :param client: The API client to use.

    :returns: ComponentDefinitionList model or error message string.
    """
    haystack_service = client.haystack_service()

    try:
        response = await haystack_service.get_component_schemas()
    except UnexpectedAPIError as e:
        return f"Error retrieving component schemas: {e}"

    # Navigate to the components definition section
    # Typically structured as {definitions: {Components: {<component_name>: <schema>}}}
    schemas = response.get("component_schema", {})
    all_schemas = schemas.get("definitions", {}).get("Components", {})
    components = response["component_schema"]["definitions"]["Components"]

    if not all_schemas:
        return "No component schemas found or unexpected schema format."

    # Filter for custom components (those with package_version key)
    custom_component_schemas = {}
    for component_name, schema in all_schemas.items():
        if "package_version" in schema:
            custom_component_schemas[component_name] = schema

    if not custom_component_schemas:
        return "No custom components found."

    # Build ComponentDefinition objects for each custom component in parallel
    async def build_single_component(schema: dict[str, Any]) -> ComponentDefinition | None:
        """Build a single component definition with concurrency control."""
        async with semaphore:  # Limit to 5 concurrent builds
            # Find the component definition by its type
            component_type = schema.get("properties", {}).get("type", {}).get("const", "Unknown")
            component_def = None
            for comp in components.values():
                if comp["properties"]["type"].get("const") == component_type:
                    component_def = comp
                    break

            if component_def:
                definition = await _build_component_definition(
                    component_def=component_def,
                    component_type=component_type,
                    haystack_service=haystack_service,
                    schema=schema,
                )
                if isinstance(definition, ComponentDefinition):
                    return definition
            return None

    # Create semaphore to limit concurrent builds to 5
    semaphore = asyncio.Semaphore(5)

    # Build all components in parallel
    tasks = [build_single_component(schema) for schema in custom_component_schemas.values()]
    results = await asyncio.gather(*tasks)

    # Filter out None results
    component_definitions = [comp for comp in results if comp is not None]

    return ComponentDefinitionList(components=component_definitions, total_count=len(component_definitions))
