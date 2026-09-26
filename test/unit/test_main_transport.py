# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from deepset_mcp.main import app


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        # The stdio overload of MCPServer.run takes no host/port.
        (["--transport", "stdio"], {"transport": "stdio"}),
        (
            ["--transport", "streamable-http", "--host", "127.0.0.1", "--port", "9000"],
            {"transport": "streamable-http", "host": "127.0.0.1", "port": 9000},
        ),
        (["--transport", "sse"], {"transport": "sse", "host": "0.0.0.0"}),
    ],
)
def test_run_gets_host_and_port_only_for_network_transports(args: list[str], expected: dict[str, Any]) -> None:
    with (
        patch("deepset_mcp.main.configure_mcp_server", new=AsyncMock()),
        patch("deepset_mcp.main.MCPServer.run") as run,
    ):
        result = CliRunner().invoke(app, ["--api-key", "k", *args])

    assert result.exit_code == 0, result.output
    run.assert_called_once_with(**expected)
