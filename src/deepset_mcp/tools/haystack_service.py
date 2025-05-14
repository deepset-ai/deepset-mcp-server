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


async def search_component_definition(
    client: AsyncClientProtocol, query: str, model: ModelProtocol, top_k: int = 5
) -> str:
    """Searches for components based on name or description using semantic similarity.

    Args:
        client: The API client to use
        query: The search query
        model: The model to use for computing embeddings
        top_k: Maximum number of results to return (default: 5)

    Returns:
        A formatted string containing the matched component definitions
    """
    haystack_service = client.haystack_service()

    try:
        response = await haystack_service.get_component_schemas()
    except UnexpectedAPIError as e:
        return f"Failed to retrieve component schemas: {e}"

    components = response["component_schema"]["definitions"]["Components"]

    # Extract text for embedding from all components
    component_texts: List[Tuple[str, str]] = [
        extract_component_texts(comp) for comp in components.values()
    ]
    
    if not component_texts:
        return "No components found"

    # Compute embeddings
    query_embedding = model.encode(query)
    component_embeddings = model.encode([text for _, text in component_texts])

    # Compute similarities
    similarities = query_embedding @ component_embeddings.T

    # Get indices of top_k most similar components
    top_indices = similarities.argsort()[-top_k:][::-1]

    # Format results
    results = []
    for idx in top_indices:
        component_type = component_texts[idx][0]
        # Get full component definition
        definition = await get_component_definition(client, component_type)
        results.append(f"Similarity Score: {similarities[idx]:.3f}\n{definition}\n{'-' * 80}\n")

    return "\n".join(results)


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
