import numpy as np

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.formatting_utils import pipeline_template_to_llm_readable_string
from deepset_mcp.tools.model_protocol import ModelProtocol


async def list_pipeline_templates(
    client: AsyncClientProtocol,
    workspace: str,
    limit: int = 100,
    field: str = "created_at",
    order: str = "DESC",
    filter: str | None = None,
) -> str:
    """Retrieves a list of all available pipeline templates.

    :param client: The async client for API requests.
    :param workspace: The workspace to list templates from.
    :param limit: Maximum number of templates to return (default: 100).
    :param field: Field to sort by (default: "created_at").
    :param order: Sort order, either "ASC" or "DESC" (default: "DESC").
    :param filter: OData filter expression to filter templates by criteria.

    :returns: Formatted string with template information.
    """
    try:
        response = await client.pipeline_templates(workspace=workspace).list_templates(
            limit=limit, field=field, order=order, filter=filter
        )
        formatted_templates = [pipeline_template_to_llm_readable_string(t) for t in response]
        return "\n\n".join(formatted_templates)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except UnexpectedAPIError as e:
        return f"Failed to list pipeline templates: {e}"


async def get_pipeline_template(client: AsyncClientProtocol, workspace: str, template_name: str) -> str:
    """Fetches detailed information for a specific pipeline template, identified by its `template_name`."""
    try:
        response = await client.pipeline_templates(workspace=workspace).get_template(template_name)
        return pipeline_template_to_llm_readable_string(response)
    except ResourceNotFoundError:
        return f"There is no pipeline template named '{template_name}' in workspace '{workspace}'."
    except UnexpectedAPIError as e:
        return f"Failed to fetch pipeline template '{template_name}': {e}"
