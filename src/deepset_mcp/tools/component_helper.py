from typing import Any


def extract_component_info(components: dict[str, Any], component_def: dict[str, Any]) -> str:
    """Extracts and formats component information from its definition.

    Args:
        components: The components dictionary from the schema
        component_def: The specific component definition

    Returns:
        A formatted string containing the component information
    """
    component_type_info = component_def["properties"]["type"]
    init_params = component_def["properties"].get("init_parameters", {}).get("properties", {})
    component_type = component_type_info["const"]

    # Format the basic component information
    parts = [
        f"Component: {component_type}",
        f"Name: {component_def.get('title', 'Unknown')}",
        f"Family: {component_type_info.get('family', 'Unknown')}",
        f"Family Description: {component_type_info.get('family_description', 'No description available.')}",
        f"\nDescription:\n{component_def.get('description', 'No description available.')}\n",
        "\nInitialization Parameters:",
    ]

    if not init_params:
        parts.append("  No initialization parameters")
    else:
        for param_name, param_info in init_params.items():
            param_type = param_info.get("_annotation", param_info.get("type", "Unknown"))
            param_desc = param_info.get("description", "No description available.")
            default = f" (default: {param_info['default']})" if "default" in param_info else ""
            parts.append(f"  {param_name}: {param_type}{default}\n    {param_desc}")

    return "\n".join(parts)


def format_io_info(io_info: dict[str, Any]) -> str:
    """Formats the input/output information for a component.

    Args:
        io_info: The input/output information dictionary

    Returns:
        A formatted string containing the IO information
    """
    parts = []

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

    return "\n".join(parts)


def extract_component_texts(component_def: dict[str, Any]) -> tuple[str, str]:
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
