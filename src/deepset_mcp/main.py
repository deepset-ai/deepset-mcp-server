# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt
from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DEEPSET_DOCS_DEFAULT_SHARE_URL
from deepset_mcp.tool_factory import WorkspaceMode, register_tools

# Initialize MCP Server
mcp = FastMCP("Deepset Cloud MCP", settings={"log_level": "ERROR"})

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)


@mcp.prompt()
async def deepset_copilot() -> str:
    """System prompt for the deepset copilot."""
    prompt_path = Path(__file__).parent / "prompts/deepset_copilot_prompt.md"

    return prompt_path.read_text()


@mcp.prompt()
async def deepset_recommended_prompt() -> str:
    """Recommended system prompt for the deepset copilot."""
    prompt_path = Path(__file__).parent / "prompts/deepset_debugging_agent.md"

    return prompt_path.read_text()


async def fetch_shared_prototype_details(share_url: str) -> tuple[str, str, str]:
    """Gets the pipeline name, workspace name and an API token for a shared prototype url.

    :param share_url: The URL of a shared prototype on the deepset platform.

    :returns: A tuple containing the pipeline name, workspace name and an API token.
    """
    parsed_url = urlparse(share_url)
    query_params = parse_qs(parsed_url.query)
    share_token = query_params.get("share_token", [None])[0]
    if not share_token:
        raise ValueError("Invalid share URL: missing share_token parameter.")

    jwt_token = share_token.replace("prototype_", "")

    decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
    workspace_name = decoded_token.get("workspace_name")
    if not workspace_name:
        raise ValueError("Invalid JWT in share_token: missing 'workspace_name'.")

    share_id = decoded_token.get("share_id")
    if not share_id:
        raise ValueError("Invalid JWT in share_token: missing 'share_id'.")

    # For shared prototypes, we need to:
    # 1. Fetch prototype details (pipeline name) using the information encoded in the JWT
    # 2. Create a shared prototype user
    async with AsyncDeepsetClient(api_key=share_token) as client:
        response = await client.request(f"/v1/workspaces/{workspace_name}/shared_prototypes/{share_id}")
        if not response.success:
            raise ValueError(f"Failed to fetch shared prototype details: {response.status_code} {response.json}")

        data = response.json or {}
        pipeline_names: list[str] = data.get("pipeline_names", [])
        if not pipeline_names:
            raise ValueError("No pipeline names found in shared prototype response.")

        user_info = await client.request("/v1/workspaces/dc-docs-content/shared_prototype_users", method="POST")

        if not user_info.success:
            raise ValueError("Failed to fetch user information from shared prototype response.")

        user_data = user_info.json or {}

        try:
            api_key = user_data["user_token"]
        except KeyError:
            raise ValueError("No user token in shared prototype response.") from None

    return workspace_name, pipeline_names[0], api_key


def main() -> None:
    """Entrypoint for the deepset MCP server."""
    parser = argparse.ArgumentParser(description="Run the Deepset MCP server.")
    parser.add_argument(
        "--workspace",
        "-w",
        help="Deepset workspace (env DEEPSET_WORKSPACE)",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        help="Deepset API key (env DEEPSET_API_KEY)",
    )
    parser.add_argument(
        "--docs-share-url",
        "-d",
        default=DEEPSET_DOCS_DEFAULT_SHARE_URL,
        help="Deepset docs search share URL (env DEEPSET_DOCS_SHARE_URL)",
    )
    parser.add_argument(
        "--workspace-mode",
        "-m",
        choices=[WorkspaceMode.STATIC, WorkspaceMode.DYNAMIC],
        default=WorkspaceMode.STATIC,
        help=(
            "Whether workspace should be set statically or dynamically provided during a tool call. "
            f"Default: '{WorkspaceMode.STATIC}'"
        ),
    )
    parser.add_argument(
        "--tools",
        "-t",
        nargs="*",
        help="Space-separated list of tools to register (default: all)",
    )
    parser.add_argument(
        "--list-tools",
        "-l",
        action="store_true",
        help="List all available tools and exit",
    )
    args = parser.parse_args()

    # Handle --list-tools flag early
    if args.list_tools:
        from deepset_mcp.tool_factory import TOOL_REGISTRY

        print("Available tools:")
        for tool_name in sorted(TOOL_REGISTRY.keys()):
            print(f"  {tool_name}")
        return

    # prefer flags, fallback to env
    workspace = args.workspace or os.getenv("DEEPSET_WORKSPACE")
    api_key = args.api_key or os.getenv("DEEPSET_API_KEY")
    docs_share_url = args.docs_share_url or os.getenv("DEEPSET_DOCS_SHARE_URL")

    if docs_share_url:
        try:
            workspace_name, pipeline_name, api_key_docs = asyncio.run(fetch_shared_prototype_details(docs_share_url))
            os.environ["DEEPSET_DOCS_WORKSPACE"] = workspace_name
            os.environ["DEEPSET_DOCS_PIPELINE_NAME"] = pipeline_name
            os.environ["DEEPSET_DOCS_API_KEY"] = api_key_docs
        except (ValueError, jwt.DecodeError) as e:
            parser.error(f"Error processing --docs-share-url: {e}")

    # Create server configuration
    workspace_mode = WorkspaceMode(args.workspace_mode)

    if workspace_mode == WorkspaceMode.STATIC:
        if not workspace:
            parser.error("Missing workspace: set --workspace or DEEPSET_WORKSPACE")

    if not api_key:
        parser.error("Missing API key: set --api-key or DEEPSET_API_KEY")

    # make sure downstream tools see them (for implicit mode)
    if workspace:
        os.environ["DEEPSET_WORKSPACE"] = workspace
    os.environ["DEEPSET_API_KEY"] = api_key

    # Parse tool names if provided
    tool_names = None
    if args.tools:
        tool_names = set(args.tools)

    # Register tools based on configuration
    register_tools(mcp, workspace_mode, workspace, tool_names)

    # run with SSE transport (HTTP+Server-Sent Events)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
