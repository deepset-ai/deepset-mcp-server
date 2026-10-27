# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Every client the MCP server builds labels its traffic with `X-Client-Source: mcp`."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from deepset_mcp.mcp.server import fetch_shared_prototype_details
from deepset_mcp.mcp.tool_factory import apply_client
from deepset_mcp.mcp.tool_models import DeepsetDocsConfig, ToolConfig
from deepset_mcp.mcp.tool_registry import get_docs_search_tool


def _client_class(client: Any = None) -> MagicMock:
    cls = MagicMock()
    cls.return_value.__aenter__.return_value = client or AsyncMock()
    return cls


@pytest.mark.asyncio
async def test_tool_factory_clients_send_mcp_source() -> None:
    async def tool(client: Any) -> str:
        return "ok"

    ctx = MagicMock()
    ctx.request_context.request.headers.get.return_value = "Bearer token"

    with patch("deepset_mcp.mcp.tool_factory.AsyncDeepsetClient", _client_class()) as cls:
        await apply_client(tool, ToolConfig(needs_client=True), use_request_context=True)(ctx=ctx)
        await apply_client(tool, ToolConfig(needs_client=True), use_request_context=False, api_key="token")()

    assert [call.kwargs["client_source"] for call in cls.call_args_list] == ["mcp", "mcp"]


@pytest.mark.asyncio
async def test_docs_search_tool_client_sends_mcp_source() -> None:
    config = DeepsetDocsConfig(api_key="key", workspace_name="ws", pipeline_name="pipe")

    with (
        patch("deepset_mcp.mcp.tool_registry.AsyncDeepsetClient", _client_class()) as cls,
        patch("deepset_mcp.mcp.tool_registry.search_docs_tool", AsyncMock(return_value="")),
    ):
        await get_docs_search_tool(config)("query")

    assert cls.call_args.kwargs["client_source"] == "mcp"


@pytest.mark.asyncio
async def test_shared_prototype_client_sends_mcp_source() -> None:
    token = jwt.encode({"workspace_name": "ws", "share_id": "sid"}, "secret", algorithm="HS256")
    responses = [
        MagicMock(success=True, json={"pipeline_names": ["pipe"]}),
        MagicMock(success=True, json={"user_token": "user-token"}),
    ]
    client = AsyncMock()
    client.request.side_effect = responses

    with patch("deepset_mcp.mcp.server.AsyncDeepsetClient", _client_class(client)) as cls:
        await fetch_shared_prototype_details(f"https://cloud.deepset.ai/shared_prototypes?share_token={token}")

    assert cls.call_args.kwargs["client_source"] == "mcp"
