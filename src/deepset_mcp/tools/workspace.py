# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for interacting with workspaces."""

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList


async def list_workspaces(*, client: AsyncClientProtocol) -> WorkspaceList | str:
    """Retrieves a list of all workspaces available to the user.

    This tool provides an overview of all workspaces that the user has access to.
    Each workspace contains information about its name, ID, supported languages,
    and default idle timeout settings.

    :param client: The async client for API communication.
    :returns: List of workspaces or error message.
    """
    try:
        return await client.workspaces().list()
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list workspaces: {e}"


async def get_workspace(*, client: AsyncClientProtocol, workspace_name: str) -> Workspace | str:
    """Fetches detailed information for a specific workspace by name.

    This tool retrieves comprehensive details about a specific workspace, including
    its unique ID, supported languages, and configuration settings. Use this when
    you need detailed information about a particular workspace.

    :param client: The async client for API communication.
    :param workspace_name: The name of the workspace to fetch details for.
    :returns: Workspace details or error message.
    """
    try:
        return await client.workspaces().get(workspace_name=workspace_name)
    except ResourceNotFoundError:
        return f"There is no workspace named '{workspace_name}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to fetch workspace '{workspace_name}': {e}"


async def create_workspace(*, client: AsyncClientProtocol, name: str) -> NoContentResponse | str:
    """Creates a new workspace with the specified name.

    This tool creates a new workspace that can be used to organize pipelines,
    indexes, and other resources. The workspace name must be unique across
    the platform. Once created, you can start deploying pipelines and other
    resources within this workspace.

    :param client: The async client for API communication.
    :param name: The name for the new workspace. Must be unique.
    :returns: Success confirmation or error message.
    """
    try:
        return await client.workspaces().create(name=name)
    except BadRequestError as e:
        return f"Failed to create workspace '{name}': {e}"
    except UnexpectedAPIError as e:
        return f"Failed to create workspace '{name}': {e}"
