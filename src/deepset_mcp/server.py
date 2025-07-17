# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
from urllib.parse import parse_qs, urlparse

import jwt
from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DOCS_SEARCH_TOOL_NAME
from deepset_mcp.tool_factory import register_tools
from deepset_mcp.tool_models import DeepsetDocsConfig, WorkspaceMode


def configure_mcp_server(
    mcp_server_instance: FastMCP,
    tools_to_register: set[str],
    workspace_mode: WorkspaceMode,
    deepset_api_key: str | None = None,
    deepset_workspace: str | None = None,
    deepset_docs_shareable_prototype_url: str | None = None,
    get_api_key_from_authorization_header: bool = False,
) -> None:
    """Configure the MCP server with the specified tools and settings.

    :param mcp_server_instance: The FastMCP server instance to configure
    :param tools_to_register: Set of tool names to register with the server
    :param workspace_mode: The workspace mode (static or dynamic)
    :param deepset_api_key: Optional Deepset API key for authentication
    :param deepset_workspace: Optional workspace name for static mode
    :param deepset_docs_shareable_prototype_url: Optional URL for shared prototype
    :param get_api_key_from_authorization_header: Whether to extract API key from authorization header
    :raises ValueError: If required parameters are missing or invalid
    """
    if DOCS_SEARCH_TOOL_NAME in tools_to_register and deepset_docs_shareable_prototype_url is None:
        raise ValueError(
            f"The {DOCS_SEARCH_TOOL_NAME} tool requires a shareable prototype URL. "
            "Please provide 'deepset_docs_shareable_prototype_url' or remove the tool from registration."
        )

    if workspace_mode == WorkspaceMode.STATIC and deepset_workspace is None:
        raise ValueError(
            "Static workspace mode requires a workspace name. "
            "Please provide 'deepset_workspace' when using WorkspaceMode.STATIC."
        )

    if deepset_api_key is None and not get_api_key_from_authorization_header:
        raise ValueError(
            "API key is required for authentication. "
            "Please provide 'deepset_api_key' or enable 'get_api_key_from_authorization_header'."
        )

    if deepset_docs_shareable_prototype_url is not None:
        workspace_name, pipeline_name, api_key_docs = asyncio.run(
            fetch_shared_prototype_details(deepset_docs_shareable_prototype_url)
        )
        docs_config = DeepsetDocsConfig(
            api_key=api_key_docs, workspace_name=workspace_name, pipeline_name=pipeline_name
        )
    else:
        docs_config = None

    register_tools(
        mcp_server_instance=mcp_server_instance,
        workspace_mode=workspace_mode,
        workspace=deepset_workspace,
        tool_names=tools_to_register,
        docs_config=docs_config,
        get_api_key_from_authorization_header=get_api_key_from_authorization_header,
        api_key=deepset_api_key,
    )


async def fetch_shared_prototype_details(share_url: str) -> tuple[str, str, str]:
    """Extract pipeline name, workspace name and API token from a shared prototype URL.

    :param share_url: The URL of a shared prototype on the Deepset platform
    :returns: A tuple containing (workspace_name, pipeline_name, api_key)
    :raises ValueError: If the URL is invalid or missing required parameters
    """
    parsed_url = urlparse(share_url)
    query_params = parse_qs(parsed_url.query)
    share_token = query_params.get("share_token", [None])[0]
    if not share_token:
        raise ValueError(
            "Invalid share URL: missing 'share_token' parameter. Please provide a valid Deepset prototype share URL."
        )

    jwt_token = share_token.replace("prototype_", "")

    decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
    workspace_name = decoded_token.get("workspace_name")
    if not workspace_name:
        raise ValueError(
            "Invalid share token: missing 'workspace_name' in JWT. The provided share URL may be corrupted or expired."
        )

    share_id = decoded_token.get("share_id")
    if not share_id:
        raise ValueError(
            "Invalid share token: missing 'share_id' in JWT. The provided share URL may be corrupted or expired."
        )

    # For shared prototypes, we need to:
    # 1. Fetch prototype details (pipeline name) using the information encoded in the JWT
    # 2. Create a shared prototype user
    async with AsyncDeepsetClient(api_key=share_token) as client:
        response = await client.request(f"/v1/workspaces/{workspace_name}/shared_prototypes/{share_id}")
        if not response.success:
            raise ValueError(
                f"Failed to fetch shared prototype details: HTTP {response.status_code}. Response: {response.json}"
            )

        data = response.json or {}
        pipeline_names: list[str] = data.get("pipeline_names", [])
        if not pipeline_names:
            raise ValueError(
                "No pipeline names found in shared prototype. The prototype may not be properly configured."
            )

        user_info = await client.request("/v1/workspaces/dc-docs-content/shared_prototype_users", method="POST")

        if not user_info.success:
            raise ValueError(
                f"Failed to create user session for shared prototype. HTTP {user_info.status_code}: {user_info.json}"
            )

        user_data = user_info.json or {}

        try:
            api_key = user_data["user_token"]
        except KeyError:
            raise ValueError(
                "No user token found in shared prototype response. Unable to authenticate with the prototype."
            ) from None

    return workspace_name, pipeline_names[0], api_key
