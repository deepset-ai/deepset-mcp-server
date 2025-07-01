"""Integration tests for WorkspaceResource."""

import os
import uuid

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.workspace.models import Workspace, WorkspaceList


class TestWorkspaceResourceIntegration:
    """Integration tests for WorkspaceResource."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(os.getenv("DEEPSET_API_KEY") is None, reason="DEEPSET_API_KEY not set")
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
    @pytest.mark.skipif(os.getenv("DEEPSET_API_KEY") is None, reason="DEEPSET_API_KEY not set")
    async def test_get_workspace_not_found(self) -> None:
        """Test getting a non-existent workspace."""
        async with AsyncDeepsetClient() as client:
            with pytest.raises(UnexpectedAPIError):
                await client.workspaces().get("definitely-does-not-exist-workspace")