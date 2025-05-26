import numpy as np

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.component_helper import (
    extract_component_info,
    extract_component_texts,
    format_io_info,
)
from deepset_mcp.tools.formatting_utils import pipeline_template_to_llm_readable_string
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
    component_texts: list[tuple[str, str]] = [extract_component_texts(comp) for comp in components.values()]
    component_types: list[str] = [c[0] for c in component_texts]

    if not component_texts:
        return "No components found"

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
    results = []
    for component_type, sim in top_components:
        definition = await get_component_definition(client, component_type)
        results.append(f"Similarity Score: {sim:.3f}\n{definition}\n{'-' * 80}\n")

    return "\n".join(results)


async def search_pipeline_templates(
    client: AsyncClientProtocol, query: str, model: ModelProtocol, workspace: str, top_k: int = 5
) -> str:
    """Searches for pipeline templates based on name or description using semantic similarity.

    Args:
        client: The API client to use
        query: The search query
        model: The model to use for computing embeddings
        workspace: The workspace to search templates from
        top_k: Maximum number of results to return (default: 5)

    Returns:
        A formatted string containing the matched pipeline template definitions
    """
    try:
        response = await client.pipeline_templates(workspace=workspace).list_templates(
            limit=100, field="created_at", order="DESC", filter='pipeline_type eq "QUERY"'
        )
    except UnexpectedAPIError as e:
        return f"Failed to retrieve pipeline templates: {e}"

    if not response:
        return "No pipeline templates found"

    # Extract text for embedding from all templates
    template_texts: list[tuple[str, str]] = [
        (template.template_name, f"{template.template_name} {template.description}")
        for template in response
    ]
    template_names: list[str] = [t[0] for t in template_texts]

    # Compute embeddings
    query_embedding = model.encode(query)
    template_embeddings = model.encode([text for _, text in template_texts])

    query_embedding_reshaped = query_embedding.reshape(1, -1)

    # Calculate dot product between target and all templates
    # This gives us a similarity score for each template
    similarities = np.dot(template_embeddings, query_embedding_reshaped.T).flatten()

    # Create (template_name, similarity) pairs
    template_similarities = list(zip(template_names, similarities, strict=False))

    # Sort by similarity score in descending order
    template_similarities.sort(key=lambda x: x[1], reverse=True)

    top_templates = template_similarities[:top_k]
    results = []
    for template_name, sim in top_templates:
        # Find the template object by name
        template = next((t for t in response if t.template_name == template_name), None)
        if template:
            template_str = pipeline_template_to_llm_readable_string(template)
            results.append(f"Similarity Score: {sim:.3f}\n{template_str}\n{'-' * 80}\n")

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
