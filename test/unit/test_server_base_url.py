# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for base_url functionality in server and main modules."""

from unittest.mock import MagicMock, patch

from deepset_mcp.server import configure_mcp_server
from deepset_mcp.tool_models import WorkspaceMode


class TestConfigureMcpServerBaseUrl:
    """Test the configure_mcp_server function with base_url parameter."""

    @patch("deepset_mcp.server.register_tools")
    def test_configure_mcp_server_passes_base_url(self, mock_register_tools: MagicMock) -> None:
        """Test that configure_mcp_server passes base_url to register_tools."""
        mock_server = MagicMock()
        custom_url = "https://custom.api.example.com"

        configure_mcp_server(
            mcp_server_instance=mock_server,
            tools_to_register={"list_pipelines"},
            workspace_mode=WorkspaceMode.STATIC,
            deepset_api_key="test-key",
            deepset_api_url=custom_url,
            deepset_workspace="test-workspace",
        )

        # Verify register_tools was called with base_url
        mock_register_tools.assert_called_once()
        call_args = mock_register_tools.call_args
        assert call_args[1]["base_url"] == custom_url

    @patch("deepset_mcp.server.register_tools")
    def test_configure_mcp_server_without_base_url(self, mock_register_tools: MagicMock) -> None:
        """Test that configure_mcp_server works without base_url."""
        mock_server = MagicMock()

        configure_mcp_server(
            mcp_server_instance=mock_server,
            tools_to_register={"list_pipelines"},
            workspace_mode=WorkspaceMode.STATIC,
            deepset_api_key="test-key",
            deepset_workspace="test-workspace",
        )

        # Verify register_tools was called with base_url=None
        mock_register_tools.assert_called_once()
        call_args = mock_register_tools.call_args
        assert call_args[1]["base_url"] is None
