from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.haystack_service.resource import HaystackServiceResource


async def list_component_families(client: AsyncClientProtocol) -> str:
    """Lists all Haystack component families that are available on deepset."""
    try:
        haystack_service = HaystackServiceResource(client)
        response = await haystack_service.get_component_schemas()

        # Check if we have the expected response structure
        if (
            not response 
            or "component_schema" not in response
            or "definitions" not in response["component_schema"]
            or "Components" not in response["component_schema"]["definitions"]
        ):
            return "Failed to retrieve component families: unexpected response structure"

        components = response["component_schema"]["definitions"]["Components"]
        
        # Extract unique families and their descriptions
        families = {}
        for component_def in components.values():
            if (
                isinstance(component_def, dict)
                and "properties" in component_def
                and "type" in component_def["properties"]
                and "family" in component_def["properties"]["type"]
            ):
                component_type = component_def["properties"]["type"]
                family = component_type.get("family")
                description = component_type.get("family_description")
                
                if family and description and family not in families:
                    families[family] = description

        if not families:
            return "No component families found in the response"

        # Format the families into a readable string
        parts = ["Available Haystack component families:\n"]
        for family, description in sorted(families.items()):
            parts.append(f"\n**{family}**\n{description}\n")

        return "\n".join(parts)

    except UnexpectedAPIError as e:
        return f"Failed to retrieve component families: {e}"
    except Exception as e:
        return f"An unexpected error occurred while retrieving component families: {e}"
