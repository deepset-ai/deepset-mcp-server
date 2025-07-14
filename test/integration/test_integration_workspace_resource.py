# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for WorkspaceResource."""

import uuid

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList

pytestmark = pytest.mark.integration


class TestWorkspaceResourceIntegration:
    """Integration tests for WorkspaceResource."""

    @pytest.mark.asyncio
    async def test_list_workspaces(self) -> None:
        """Test listing workspaces."""
        async with AsyncDeepsetClient() as client:
            workspaces = await client.workspaces().list()
            assert isinstance(workspaces, WorkspaceList)
            assert isinstance(workspaces.data, list)
            assert workspaces.total >= 0

            # If we have workspaces, verify their structure
            if workspaces.data:
                workspace = workspaces.data[0]
                assert isinstance(workspace, Workspace)
                assert isinstance(workspace.name, str)
                assert isinstance(workspace.workspace_id, uuid.UUID)
                assert isinstance(workspace.languages, dict)
                assert isinstance(workspace.default_idle_timeout_in_seconds, int)

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self) -> None:
        """Test getting a non-existent workspace."""
        async with AsyncDeepsetClient() as client:
            with pytest.raises(ResourceNotFoundError):
                await client.workspaces().get("definitely-does-not-exist-workspace")

    @pytest.mark.asyncio
    async def test_create_get_and_delete_workspace(self) -> None:
        """Tests creating, getting and deleting a workspace."""
        workspace_name = f"test-workspace-{uuid.uuid4()}"
        async with AsyncDeepsetClient() as client:
            # Create a new workspace
            create_response = await client.workspaces().create(workspace_name)
            assert create_response.success is True
            assert create_response.message == "Workspace created successfully."

            # Get the workspace
            workspace = await client.workspaces().get(workspace_name)
            assert isinstance(workspace, Workspace)
            assert workspace.name == workspace_name

            # Delete the workspace
            delete_response = await client.workspaces().delete(workspace_name)
            assert delete_response.success is True
            assert delete_response.message == "Workspace deleted successfully."

            # Verify the workspace is deleted
            with pytest.raises(ResourceNotFoundError):
                await client.workspaces().get(workspace_name)
