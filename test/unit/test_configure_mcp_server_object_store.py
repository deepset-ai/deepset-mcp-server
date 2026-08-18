# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for 'enable_object_store' in 'configure_mcp_server'."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from deepset_mcp.mcp.server import configure_mcp_server


@pytest.fixture(autouse=True)
def mock_fetch_shared_prototype_details() -> Generator[MagicMock, None, None]:
    """Avoid a real network call to fetch shared prototype details."""
    with patch("deepset_mcp.mcp.server.fetch_shared_prototype_details") as mock_fetch:
        mock_fetch.return_value = ("workspace", "pipeline", "docs-api-key")
        yield mock_fetch


class TestConfigureMcpServerObjectStore:
    """Test 'configure_mcp_server' with 'enable_object_store'."""

    @patch("deepset_mcp.mcp.server.initialize_or_get_initialized_store")
    @patch("deepset_mcp.mcp.server.register_tools")
    @pytest.mark.asyncio
    async def test_object_store_enabled_initializes_store(
        self, mock_register_tools: MagicMock, mock_initialize_store: MagicMock
    ) -> None:
        """By default, the object store must be initialized and passed to 'register_tools'."""
        mock_server = MagicMock()
        mock_initialize_store.return_value = "the-store"

        await configure_mcp_server(mcp_server_instance=mock_server, deepset_api_key="test-key")

        mock_initialize_store.assert_called_once()
        call_args = mock_register_tools.call_args
        assert call_args[1]["object_store"] == "the-store"
        assert call_args[1]["enable_object_store"] is True

    @patch("deepset_mcp.mcp.server.initialize_or_get_initialized_store")
    @patch("deepset_mcp.mcp.server.register_tools")
    @pytest.mark.asyncio
    async def test_object_store_disabled_skips_store_initialization(
        self, mock_register_tools: MagicMock, mock_initialize_store: MagicMock
    ) -> None:
        """When disabled, the object store must never be initialized and 'None' is passed to 'register_tools'."""
        mock_server = MagicMock()

        await configure_mcp_server(
            mcp_server_instance=mock_server, deepset_api_key="test-key", enable_object_store=False
        )

        mock_initialize_store.assert_not_called()
        call_args = mock_register_tools.call_args
        assert call_args[1]["object_store"] is None
        assert call_args[1]["enable_object_store"] is False

    @patch("deepset_mcp.mcp.server.initialize_or_get_initialized_store")
    @patch("deepset_mcp.mcp.server.register_tools")
    @pytest.mark.asyncio
    async def test_object_store_disabled_and_no_tools_specified_forwards_none(
        self, mock_register_tools: MagicMock, mock_initialize_store: MagicMock
    ) -> None:
        """'tools_to_register=None' must be forwarded as 'None', not expanded into every tool name.

        Regression test: 'configure_mcp_server' used to eagerly expand 'tools_to_register=None' into the full
        'TOOL_REGISTRY' key set (including object-store tools) before calling 'register_tools'. That made
        'register_tools' think the object-store tools had been explicitly requested, so it raised
        'ValueError: Cannot register object-store tools ...' whenever 'enable_object_store=False' was combined
        with the default 'tools_to_register=None'.
        """
        mock_server = MagicMock()

        await configure_mcp_server(
            mcp_server_instance=mock_server, deepset_api_key="test-key", enable_object_store=False
        )

        call_args = mock_register_tools.call_args
        assert call_args[1]["tool_names"] is None
