# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for base_url functionality in server and main modules."""

import os
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from deepset_mcp.main import app
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


class TestMainCliBaseUrl:
    """Test the main CLI with base_url parameter."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.runner = CliRunner()
        # Clear environment variables that might interfere
        for key in ["DEEPSET_API_KEY", "DEEPSET_WORKSPACE", "DEEPSET_API_URL"]:
            if key in os.environ:
                del os.environ[key]

    @patch("deepset_mcp.main.configure_mcp_server")
    @patch("deepset_mcp.main.FastMCP")
    def test_main_with_api_url_option(self, mock_fastmcp: MagicMock, mock_configure: MagicMock) -> None:
        """Test main CLI with --api-url option."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        custom_url = "https://custom.api.example.com"

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--workspace",
                "test-workspace",
                "--api-url",
                custom_url,
            ],
        )

        assert result.exit_code == 0
        mock_configure.assert_called_once()
        call_args = mock_configure.call_args
        assert call_args[1]["deepset_api_url"] == custom_url

    @patch("deepset_mcp.main.configure_mcp_server")
    @patch("deepset_mcp.main.FastMCP")
    def test_main_with_api_url_env_var(self, mock_fastmcp: MagicMock, mock_configure: MagicMock) -> None:
        """Test main CLI with DEEPSET_API_URL environment variable."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        custom_url = "https://env.api.example.com"

        with patch.dict(
            os.environ,
            {
                "DEEPSET_API_KEY": "test-key",
                "DEEPSET_WORKSPACE": "test-workspace",
                "DEEPSET_API_URL": custom_url,
            },
        ):
            result = self.runner.invoke(app, [])

            assert result.exit_code == 0
            mock_configure.assert_called_once()
            call_args = mock_configure.call_args
            assert call_args[1]["deepset_api_url"] == custom_url

    @patch("deepset_mcp.main.configure_mcp_server")
    @patch("deepset_mcp.main.FastMCP")
    def test_main_cli_option_overrides_env_var(self, mock_fastmcp: MagicMock, mock_configure: MagicMock) -> None:
        """Test that CLI option overrides environment variable for api_url."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        cli_url = "https://cli.api.example.com"
        env_url = "https://env.api.example.com"

        with patch.dict(
            os.environ,
            {
                "DEEPSET_API_KEY": "test-key",
                "DEEPSET_WORKSPACE": "test-workspace",
                "DEEPSET_API_URL": env_url,
            },
        ):
            result = self.runner.invoke(
                app,
                ["--api-url", cli_url],
            )

            assert result.exit_code == 0
            mock_configure.assert_called_once()
            call_args = mock_configure.call_args
            assert call_args[1]["deepset_api_url"] == cli_url

    @patch("deepset_mcp.main.configure_mcp_server")
    @patch("deepset_mcp.main.FastMCP")
    def test_main_without_api_url(self, mock_fastmcp: MagicMock, mock_configure: MagicMock) -> None:
        """Test main CLI without api_url uses None."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--workspace",
                "test-workspace",
            ],
        )

        assert result.exit_code == 0
        mock_configure.assert_called_once()
        call_args = mock_configure.call_args
        assert call_args[1]["deepset_api_url"] is None

    def test_main_help_shows_api_url_option(self) -> None:
        """Test that help text shows the api-url option."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--api-url" in result.stdout
        assert "Deepset API base URL" in result.stdout
        assert "DEEPSET_API_URL" in result.stdout
