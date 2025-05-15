from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.formatting_utils import pipeline_template_to_llm_readable_string


async def list_pipeline_templates(client: AsyncClientProtocol, workspace: str) -> str:
    """Retrieves a list of all pipeline templates available within the currently configured deepset workspace."""
    try:
        response = await client.pipeline_templates(workspace=workspace).list_templates()
        formatted_templates = [pipeline_template_to_llm_readable_string(t) for t in response]
        return "\n\n".join(formatted_templates)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except UnexpectedAPIError as e:
        return f"Failed to list pipeline templates: {e}"


async def get_pipeline_template(client: AsyncClientProtocol, workspace: str, template_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline template, identified by its unique `template_name`."""
    try:
        response = await client.pipeline_templates(workspace=workspace).get_template(template_name)
        return pipeline_template_to_llm_readable_string(response)
    except ResourceNotFoundError:
        return f"There is no pipeline template named '{template_name}' in workspace '{workspace}'."
    except UnexpectedAPIError as e:
        return f"Failed to fetch pipeline template '{template_name}': {e}"
