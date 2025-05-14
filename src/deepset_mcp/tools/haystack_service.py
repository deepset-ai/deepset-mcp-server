from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from numpy.typing import NDArray
from typing import Dict, List, Any, Optional, Tuple

from deepset_mcp.tools.component_helper import (
    extract_component_info,
    format_io_info,
    extract_component_texts,
)
from deepset_mcp.tools.model_protocol import ModelProtocol


async def get_component_definition(client: AsyncClientProtocol, component_type: str) -> str:
    """Returns the definition of a specific Haystack component.

    Args:
        client: The API client to use
        component_type: Fully qualified component type
            (e.g. haystack.components.routers.conditional_router.ConditionalRouter)

    Returns:
        A formatted string containing the component definition
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

    # Get component information
    parts = [extract_component_info(components, component_def)]

    # Fetch and add input/output information
    try:
        # Extract component name from the full path
        component_name = component_type.split(".")[-1]
        io_info = await haystack_service.get_component_input_output(component_name)
        parts.append(format_io_info(io_info))
    except Exception as e:
        parts.append(f"\nFailed to fetch input/output schema: {str(e)}")

    return "\n".join(parts)


async def list_component_families(client: AsyncClientProtocol) -> str:
    """Lists all Haystack component families that are available on deepset."""
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

    # Format the families into a readable string
    parts = ["Available Haystack component families:\n"]
    for family, description in sorted(families.items()):
        parts.append(f"\n**{family}**\n{description}\n")

    return "\n".join(parts)
