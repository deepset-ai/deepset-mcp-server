import yaml

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tools.formatting_utils import pipeline_to_llm_readable_string, validation_result_to_llm_readable_string


async def list_pipelines(client: AsyncClientProtocol, workspace: str) -> str:
    """Retrieves a list of all pipeline available within the currently configured deepset workspace."""
    response = await client.pipelines(workspace=workspace).list()
    formatted_pipelines = [pipeline_to_llm_readable_string(p) for p in response]

    return "\n\n".join(formatted_pipelines)


async def get_pipeline(client: AsyncClientProtocol, workspace: str, pipeline_name: str) -> str:
    """Fetches detailed configuration information for a specific pipeline, identified by its unique `pipeline_name`."""
    response = await client.pipelines(workspace=workspace).get(pipeline_name)
    return pipeline_to_llm_readable_string(response)


async def validate_pipeline(client: AsyncClientProtocol, workspace: str, yaml_configuration: str) -> str:
    """Validates the provided pipeline YAML configuration against the deepset API."""
    if not yaml_configuration or not yaml_configuration.strip():
        return "You need to provide a YAML configuration to validate."

    try:
        yaml.safe_load(yaml_configuration)
    except yaml.YAMLError as e:
        return f"Invalid YAML provided: {e}"

    response = await client.pipelines(workspace=workspace).validate(yaml_configuration)

    return validation_result_to_llm_readable_string(response)


async def create_pipeline(
    client: AsyncClientProtocol, workspace: str, pipeline_name: str, yaml_configuration: str
) -> str:
    """Creates a new pipeline within the currently configured deepset workspace."""
    validation_response = await client.pipelines(workspace=workspace).validate(yaml_configuration)

    if not validation_response.valid:
        return validation_result_to_llm_readable_string(validation_response)

    try:
        await client.pipelines(workspace=workspace).create(name=pipeline_name, yaml_config=yaml_configuration)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except BadRequestError as e:
        return f"Failed to create pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to create pipeline '{pipeline_name}': {e}"

    return f"Pipeline '{pipeline_name}' created successfully."


async def update_pipeline(
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    original_config_snippet: str,
    replacement_config_snippet: str,
) -> str:
    """
    Updates a pipeline configuration in the specified workspace with a replacement configuration snippet.

    This function validates the replacement configuration snippet before applying it to the pipeline.
    If the validation fails, it returns a readable string describing validation errors. Otherwise, the
    replacement snippet is used to update the pipeline's configuration in the target workspace.
    """
    try:
        original_pipeline = await client.pipelines(workspace=workspace).get(pipeline_name=pipeline_name)
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}'. Did you mean to create it?"

    if original_pipeline.yaml_config is None:
        raise ValueError("The pipeline does not have a YAML configuration.")

    occurrences = original_pipeline.yaml_config.count(original_config_snippet)

    if occurrences == 0:
        return f"No occurrences of the provided configuration snippet were found in the pipeline '{pipeline_name}'."

    if occurrences > 1:
        return (
            f"Multiple occurrences ({occurrences}) of the provided configuration snippet were found in the pipeline "
            f"'{pipeline_name}'. Specify a more precise snippet to proceed with the update."
        )

    updated_yaml_configuration = original_pipeline.yaml_config.replace(
        original_config_snippet, replacement_config_snippet, 1
    )

    validation_response = await client.pipelines(workspace=workspace).validate(updated_yaml_configuration)

    if not validation_response.valid:
        return validation_result_to_llm_readable_string(validation_response)

    try:
        await client.pipelines(workspace=workspace).update(
            pipeline_name=pipeline_name, yaml_config=updated_yaml_configuration
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}'. Did you mean to create it?"
    except BadRequestError as e:
        return f"Failed to update the pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to update the pipeline '{pipeline_name}': {e}"

    return f"The pipeline '{pipeline_name}' was successfully updated."


async def get_pipeline_logs(
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    limit: int = 30,
    level: str | None = None,
) -> str:
    """Fetches logs for a specific pipeline.
    
    Retrieves log entries for the specified pipeline, with optional filtering by log level.
    This is useful for debugging pipeline issues or monitoring pipeline execution.
    
    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline to fetch logs for.
    :param limit: Maximum number of log entries to return (default: 30).
    :param level: Filter logs by level (info, warning, error). If None, returns all levels.
    
    :returns: A formatted string containing the pipeline logs.
    """
    try:
        logs = await client.pipelines(workspace=workspace).get_logs(
            pipeline_name=pipeline_name,
            limit=limit,
            level=level
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}'."
    except BadRequestError as e:
        return f"Failed to fetch logs for pipeline '{pipeline_name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to fetch logs for pipeline '{pipeline_name}': {e}"
    
    from deepset_mcp.tools.formatting_utils import pipeline_logs_to_llm_readable_string
    
    return pipeline_logs_to_llm_readable_string(logs, pipeline_name, level)
