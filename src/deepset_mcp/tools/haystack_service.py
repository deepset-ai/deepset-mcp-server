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

        # Add Input Schema
        parts.append("\nInput Schema:")
        if "input" in io_info:
            input_props = io_info["input"].get("properties", {})
            if not input_props:
                parts.append("  No input parameters")
            else:
                required = io_info["input"].get("required", [])
                for param_name, param_info in input_props.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_type = param_info.get("_annotation", param_info.get("type", "Unknown"))
                    param_desc = param_info.get("description", "No description available.")
                    default = f" (default: {param_info['default']})" if "default" in param_info else ""
                    parts.append(f"  {param_name}: {param_type}{req_marker}{default}\n    {param_desc}")
        else:
            parts.append("  Input schema not available")

        # Add Output Schema
        parts.append("\nOutput Schema:")
        if "output" in io_info and isinstance(io_info["output"], dict):
            output_info = io_info["output"]
            if "properties" in output_info:
                output_props = output_info.get("properties", {})
                if not output_props:
                    parts.append("  No output parameters")
                else:
                    required = output_info.get("required", [])
                    for param_name, param_info in output_props.items():
                        req_marker = " (required)" if param_name in required else ""
                        param_type = param_info.get("_annotation", param_info.get("type", "Unknown"))
                        param_desc = param_info.get("description", "No description available.")
                        default = f" (default: {param_info['default']})" if "default" in param_info else ""
                        parts.append(f"  {param_name}: {param_type}{req_marker}{default}\n    {param_desc}")

                    # Include any definitions if they exist
                    if "definitions" in output_info:
                        parts.append("\n  Definitions:")
                        for def_name, def_info in output_info["definitions"].items():
                            parts.append(f"\n    {def_name}:")
                            if "properties" in def_info:
                                def_required = def_info.get("required", [])
                                for prop_name, prop_info in def_info["properties"].items():
                                    req_marker = " (required)" if prop_name in def_required else ""
                                    prop_type = prop_info.get("_annotation", prop_info.get("type", "Unknown"))
                                    prop_desc = prop_info.get("description", "No description available.")
                                    default = f" (default: {prop_info['default']})" if "default" in prop_info else ""
                                    parts.append(
                                        f"      {prop_name}: {prop_type}{req_marker}{default}\n        {prop_desc}"
                                    )
            else:
                # Simple output schema
                desc = output_info.get("description", "No description available.")
                output_type = output_info.get("type", "Unknown")
                parts.append(f"  Type: {output_type}\n  {desc}")
        else:
            parts.append("  Output schema not available")
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
