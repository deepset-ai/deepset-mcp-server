# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for workspace API."""

import logging
from typing import TYPE_CHECKING

from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.transport import raise_for_status
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList
from deepset_mcp.api.workspace.protocols import WorkspaceResourceProtocol

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


class WorkspaceResource(WorkspaceResourceProtocol):
    """Manages interactions with the deepset workspace API."""

    def __init__(self, client: "AsyncClientProtocol") -> None:
        """Initialize a WorkspaceResource instance.

        :param client: The async client protocol instance.
        """
        self._client = client

    async def list(self) -> WorkspaceList:
        """List all workspaces.

        :returns: A WorkspaceList containing all workspaces.
        """
        resp = await self._client.request(
            endpoint="v1/workspaces",
            method="GET",
        )

        raise_for_status(resp)

        if resp.json is not None and isinstance(resp.json, list):
            workspaces = [Workspace.model_validate(item) for item in resp.json]
            return WorkspaceList(
                data=workspaces,
                has_more=False,
                total=len(workspaces),
            )
        else:
            return WorkspaceList(data=[], has_more=False, total=0)

    async def get(self, workspace_name: str) -> Workspace:
        """Get a specific workspace by name.

        :param workspace_name: Name of the workspace to fetch.
        :returns: A Workspace instance.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{workspace_name}",
            method="GET",
        )

        raise_for_status(resp)

        return Workspace.model_validate(resp.json)

    async def create(self, name: str) -> NoContentResponse:
        """Create a new workspace.

        :param name: Name of the new workspace.
        :returns: NoContentResponse indicating successful creation.
        """
        data = {"name": name}
        resp = await self._client.request(
            endpoint="v1/workspaces",
            method="POST",
            data=data,
        )

        raise_for_status(resp)

        return NoContentResponse(message="Workspace created successfully.")

    async def delete(self, workspace_name: str) -> NoContentResponse:
        """Delete a workspace.

        :param workspace_name: Name of the workspace to delete.
        :returns: NoContentResponse indicating successful deletion.
        """
        resp = await self._client.request(
            endpoint=f"v1/workspaces/{workspace_name}",
            method="DELETE",
        )

        raise_for_status(resp)

        return NoContentResponse(message="Workspace deleted successfully.")
