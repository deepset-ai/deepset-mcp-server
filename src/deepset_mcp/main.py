# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from enum import StrEnum
from typing import Annotated

import typer
from mcp.server.fastmcp import FastMCP

from deepset_mcp.config import DEEPSET_DOCS_DEFAULT_SHARE_URL, DOCS_SEARCH_TOOL_NAME
from deepset_mcp.server import configure_mcp_server
from deepset_mcp.tool_models import WorkspaceMode
from deepset_mcp.tool_registry import TOOL_REGISTRY


class TransportEnum(StrEnum):
    """Transport mode for the MCP server."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


app = typer.Typer(
    name="deepset-mcp",
    help="Run the Deepset MCP server to interact with the deepset AI platform.",
    no_args_is_help=True,
)


@app.command()
def main(
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            help="Deepset workspace name. Can also be set via DEEPSET_WORKSPACE environment variable.",
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            help="Deepset API key for authentication. Can also be set via DEEPSET_API_KEY environment variable.",
        ),
    ] = None,
    api_url: Annotated[
        str | None,
        typer.Option(
            "--api-url",
            help="Deepset API base URL. Can also be set via DEEPSET_API_URL environment variable.",
        ),
    ] = None,
    docs_share_url: Annotated[
        str | None,
        typer.Option(
            "--docs-share-url",
            help="Deepset docs search share URL. Can also be set via DEEPSET_DOCS_SHARE_URL environment variable.",
        ),
    ] = None,
    workspace_mode: Annotated[
        WorkspaceMode,
        typer.Option(
            "--workspace-mode",
            help="Whether workspace should be set statically or dynamically provided during a tool call.",
        ),
    ] = WorkspaceMode.STATIC,
    tools: Annotated[
        list[str] | None,
        typer.Option(
            "--tools",
            help="Space-separated list of tools to register. If not specified, all available tools will be registered.",
        ),
    ] = None,
    list_tools: Annotated[
        bool,
        typer.Option(
            "--list-tools",
            help="List all available tools and exit.",
        ),
    ] = False,
    api_key_from_auth_header: Annotated[
        bool,
        typer.Option(
            "--api-key-from-auth-header/--no-api-key-from-auth-header",
            help="Get the deepset API key from the request's authorization header instead of using a static key.",
        ),
    ] = False,
    transport: Annotated[
        TransportEnum,
        typer.Option(
            "--transport",
            help="The type of transport to use for running the MCP server.",
        ),
    ] = TransportEnum.STDIO,
    object_store_backend: Annotated[
        str | None,
        typer.Option(
            "--object-store-backend",
            help="Object store backend type: 'memory' or 'redis'. "
            "Can also be set via OBJECT_STORE_BACKEND environment variable. Default is 'memory'.",
        ),
    ] = None,
    object_store_redis_url: Annotated[
        str | None,
        typer.Option(
            "--object-store-redis-url",
            help="Redis connection URL (e.g., redis://localhost:6379). "
            "Can also be set via OBJECT_STORE_REDIS_URL environment variable.",
        ),
    ] = None,
    object_store_ttl: Annotated[
        int,
        typer.Option(
            "--object-store-ttl",
            help="TTL in seconds for stored objects. Default: 600 (10 minutes). "
            "Can also be set via OBJECT_STORE_TTL environment variable.",
        ),
    ] = 600,
) -> None:
    """
    Run the Deepset MCP server.

    The Deepset MCP server provides tools to interact with the deepset AI platform,
    allowing you to create, debug, and learn about pipelines on the platform.

    :param workspace: Deepset workspace name
    :param api_key: Deepset API key for authentication
    :param api_url: Deepset API base URL
    :param docs_share_url: Deepset docs search share URL
    :param workspace_mode: Whether workspace should be set statically or dynamically
    :param tools: List of tools to register
    :param list_tools: List all available tools and exit
    :param api_key_from_auth_header: Get API key from authorization header
    :param transport: Type of transport to use for the MCP server
    :param object_store_backend: Object store backend type ('memory' or 'redis')
    :param object_store_redis_url: Redis connection URL (required if backend='redis')
    :param object_store_ttl: TTL in seconds for stored objects
    """
    # Handle --list-tools flag early
    if list_tools:
        typer.echo("Available tools:")
        for tool_name in sorted(TOOL_REGISTRY.keys()):
            typer.echo(f"  {tool_name}")
        raise typer.Exit()

    # Prefer command line arguments, fallback to environment variables
    workspace = workspace or os.getenv("DEEPSET_WORKSPACE")
    api_key = api_key or os.getenv("DEEPSET_API_KEY")
    api_url = api_url or os.getenv("DEEPSET_API_URL")
    docs_share_url = docs_share_url or os.getenv("DEEPSET_DOCS_SHARE_URL", DEEPSET_DOCS_DEFAULT_SHARE_URL)

    # ObjectStore configuration
    backend = str(object_store_backend or os.getenv("OBJECT_STORE_BACKEND", "memory"))
    redis_url = object_store_redis_url or os.getenv("OBJECT_STORE_REDIS_URL")
    ttl = int(os.getenv("OBJECT_STORE_TTL", str(object_store_ttl)))

    if tools:
        tool_names = set(tools)
    else:
        logging.info("Registering all available tools.")
        tool_names = set(TOOL_REGISTRY.keys())

    if api_key is None and not api_key_from_auth_header:
        typer.echo(
            "Error: API key is required. Either provide --api-key or use --api-key-from-auth-header "
            "to fetch the API key from the authorization header.",
            err=True,
        )
        raise typer.Exit(1)

    if workspace_mode == WorkspaceMode.STATIC and not workspace:
        typer.echo(
            "Error: Workspace is required when using static workspace mode. "
            "Set --workspace or DEEPSET_WORKSPACE environment variable.",
            err=True,
        )
        raise typer.Exit(1)

    if DOCS_SEARCH_TOOL_NAME in tool_names and docs_share_url is None:
        typer.echo(
            f"Error: {DOCS_SEARCH_TOOL_NAME} tool is requested but no docs share URL provided. "
            "Set --docs-share-url or DEEPSET_DOCS_SHARE_URL environment variable.",
            err=True,
        )
        raise typer.Exit(1)

    mcp = FastMCP("deepset AI platform MCP server")
    configure_mcp_server(
        mcp_server_instance=mcp,
        workspace_mode=workspace_mode,
        deepset_api_key=api_key,
        deepset_api_url=api_url,
        deepset_workspace=workspace,
        tools_to_register=tool_names,
        deepset_docs_shareable_prototype_url=docs_share_url,
        get_api_key_from_authorization_header=api_key_from_auth_header,
        object_store_backend=backend,
        object_store_redis_url=redis_url,
        object_store_ttl=ttl,
    )

    mcp.run(transport=transport.value)


if __name__ == "__main__":
    app()
