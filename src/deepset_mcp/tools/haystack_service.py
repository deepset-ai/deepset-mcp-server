from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


async def get_component_definition(client: AsyncClientProtocol, component_type: str) -> str:
    """Returns the definition of a specific Haystack component.

    Args:
        client: The API client to use
        component_type: Fully qualified component type (e.g. haystack.components.routers.conditional_router.ConditionalRouter)

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

    # Extract relevant information
    component_type_info = component_def["properties"]["type"]
    init_params = component_def["properties"].get("init_parameters", {}).get("properties", {})
    
    # Format the output
    parts = [
        f"Component: {component_type}",
        f"Name: {component_def.get('title', 'Unknown')}",
        f"Family: {component_type_info.get('family', 'Unknown')}",
        f"Family Description: {component_type_info.get('family_description', 'No description available.')}",
        f"\nDescription:\n{component_def.get('description', 'No description available.')}\n",
        "\nInitialization Parameters:"
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
