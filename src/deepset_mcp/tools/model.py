# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with models."""

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.model.models import ModelList
from deepset_mcp.api.protocols import AsyncClientProtocol


async def get_models(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    limit: int = 100,
    page_number: int = 1,
    connected: bool | None = None,
) -> ModelList | str:
    """Lists the models including their configuration options available for use in a workspace's pipelines and indexes.

    This includes predefined models offered by deepset as well as custom models configured
    at the workspace or organization level. Use this tool to discover which model names and
    providers can be used, which configuration options are available, and which default 
    configuration is offered when configuring chat generators.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param limit: Maximum number of models to return per page.
    :param page_number: The page to fetch, starting at 1.
    :param connected: If set, only return models for which the workspace does (True) or
        does not (False) have a working integration configured.
    :returns: A page of models including their configuration options or an error message.
    """
    try:
        return await client.models(workspace=workspace).list(limit=limit, page_number=page_number, connected=connected)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace}'. Did you mean to configure it?"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list models: {e}"
