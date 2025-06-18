"""Factory for creating workspace-aware MCP tools."""

import inspect
import os
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from mcp.server.fastmcp import FastMCP

from deepset_mcp.mcp import (
    create_index,
    create_pipeline,
    deploy_index,
    deploy_pipeline,
    get_index,
    get_latest_custom_component_installation_logs,
    get_pipeline,
    get_pipeline_logs,
    get_pipeline_template,
    list_custom_component_installations,
    list_indexes,
    list_pipeline_templates,
    list_pipelines,
    search_pipeline,
    search_pipeline_templates,
    update_index,
    update_pipeline,
    validate_pipeline,
)


class WorkspaceMode(StrEnum):
    """Configuration for how workspace is provided to tools."""

    IMPLICIT = "implicit"  # workspace from env, no parameter in tool signature
    EXPLICIT = "explicit"  # workspace as required parameter in tool signature


def get_workspace_from_env() -> str:
    """Gets the workspace configured from environment variable."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


def create_workspace_tool(
    base_func: Callable[..., Awaitable[str]], workspace_mode: WorkspaceMode, workspace: str | None = None
) -> Callable[..., Awaitable[str]]:
    """Transform a workspace-dependent tool based on configuration.

    Args:
        base_func: The base tool function (workspace as first parameter)
        workspace_mode: If LLMs should provide workspaces or workspace loaded from environment.
        workspace: Workspace to partially apply (for implicit mode)

    Returns:
        Configured tool function with appropriate signature
    """
    if workspace_mode == WorkspaceMode.IMPLICIT:
        # Partially apply workspace for implicit mode
        if workspace is None:
            workspace = get_workspace_from_env()

        # Get original signature without workspace parameter
        sig = inspect.signature(base_func)
        params = list(sig.parameters.values())[1:]  # Skip workspace parameter
        new_sig = sig.replace(parameters=params)

        # Create wrapper that injects workspace
        async def implicit_wrapper(*args: Any, **kwargs: Any) -> str:
            return await base_func(workspace, *args, **kwargs)

        # Set signature and metadata
        implicit_wrapper.__signature__ = new_sig  # type: ignore
        implicit_wrapper.__name__ = base_func.__name__

        # Process docstring to remove workspace parameter
        if base_func.__doc__:
            import re

            # Remove :param workspace: line (and any continuation lines)
            # This regex handles multi-line param descriptions
            pattern = r"^\s*:param\s+workspace:.*?(?=^\s*:|^\s*$|\Z)"
            implicit_wrapper.__doc__ = re.sub(pattern, "", base_func.__doc__, flags=re.MULTILINE | re.DOTALL)
        else:
            implicit_wrapper.__doc__ = base_func.__doc__

        return implicit_wrapper

    else:  # EXPLICIT mode
        # Return function as-is (workspace parameter exposed)
        return base_func


def register_workspace_tools(mcp: FastMCP, workspace_mode: WorkspaceMode, workspace: str | None = None) -> None:
    """Register all workspace-dependent tools with appropriate signatures.

    Args:
        mcp: FastMCP server instance
        workspace_mode: If LLMs should provide workspaces or workspace loaded from environment.
        workspace: Workspace to use for implicit mode (if None, reads from env)
    """
    workspace_tools: list[Callable[..., Awaitable[str]]] = [
        list_pipelines,
        create_pipeline,
        update_pipeline,
        get_pipeline,
        deploy_pipeline,
        validate_pipeline,
        get_pipeline_logs,
        search_pipeline,
        list_indexes,
        get_index,
        create_index,
        update_index,
        deploy_index,
        list_pipeline_templates,
        get_pipeline_template,
        search_pipeline_templates,
        list_custom_component_installations,
        get_latest_custom_component_installation_logs,
    ]

    # Transform and register each tool
    for original_func in workspace_tools:
        configured_tool = create_workspace_tool(original_func, workspace_mode, workspace)
        mcp.add_tool(configured_tool)
