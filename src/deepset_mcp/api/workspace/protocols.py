# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocols for workspace resources."""

from typing import Protocol

from deepset_mcp.api.shared_models import NoContentResponse
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList


class WorkspaceResourceProtocol(Protocol):
    """Protocol defining the interface for workspace resources."""

    async def list(self) -> WorkspaceList:
        """List all workspaces.

        :returns: A WorkspaceList containing all workspaces.
        """
        ...

    async def get(self, workspace_name: str) -> Workspace:
        """Get a specific workspace by name.

        :param workspace_name: Name of the workspace to fetch.
        :returns: A Workspace instance.
        """
        ...

    async def create(self, name: str) -> NoContentResponse:
        """Create a new workspace.

        :param name: Name of the new workspace.
        :returns: NoContentResponse indicating successful creation.
        """
        ...

    async def delete(self, workspace_name: str) -> NoContentResponse:
        """Delete a workspace.

        :param workspace_name: Name of the workspace to delete.
        :returns: NoContentResponse indicating successful deletion.
        """
        ...
