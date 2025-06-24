"""Factory for creating workspace-aware MCP tools."""

import inspect
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.initialize_embedding_model import get_initialized_model
from deepset_mcp.store import STORE
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs as get_latest_custom_component_installation_logs_tool,
    list_custom_component_installations as list_custom_component_installations_tool,
)
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    get_custom_components as get_custom_components_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
from deepset_mcp.tools.haystack_service_models import ComponentSearchResults
from deepset_mcp.tools.indexes import (
    create_index as create_index_tool,
    deploy_index as deploy_index_tool,
    get_index as get_index_tool,
    list_indexes as list_indexes_tool,
    update_index as update_index_tool,
)

# Import all tool functions
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    deploy_pipeline as deploy_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    get_pipeline_logs as get_pipeline_logs_tool,
    list_pipelines as list_pipelines_tool,
    search_pipeline as search_pipeline_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)
from deepset_mcp.tools.pipeline_template import (
    get_pipeline_template as get_pipeline_template_tool,
    list_pipeline_templates as list_pipeline_templates_tool,
    search_pipeline_templates as search_pipeline_templates_tool,
)
from deepset_mcp.tools.secrets import (
    get_secret as get_secret_tool,
    list_secrets as list_secrets_tool,
)
from deepset_mcp.tools.tokonomics import RichExplorer, explorable, explorable_and_referenceable, referenceable


# Special wrapper for search_component_definitions that needs the model
async def search_component_definitions_wrapper(client: Any, query: str, top_k: int = 5) -> ComponentSearchResults | str:
    """Use this to search for components in deepset.

    You can use full natural language queries to find components.
    You can also use simple keywords.
    Use this if you want to find the definition for a component,
    but you are not sure what the exact name of the component is.

    Args:
        client: The API client to use
        query: The search query
        top_k: Maximum number of results to return (default: 5)

    Returns:
        ComponentSearchResults model or error message string
    """
    model = get_initialized_model()
    return await search_component_definition_tool(client, query, model, top_k)


# Special wrapper for search_pipeline_templates that needs the model
async def search_pipeline_templates_wrapper(client: Any, workspace: str, query: str, top_k: int = 10) -> Any:
    """Searches for pipeline templates based on name or description using semantic similarity.

    Args:
        client: The API client to use
        workspace: The workspace to search templates from
        query: The search query
        top_k: Maximum number of results to return (default: 10)

    Returns:
        Search results with similarity scores or error message
    """
    model = get_initialized_model()
    return await search_pipeline_templates_tool(client, query, model, workspace, top_k)


class WorkspaceMode(StrEnum):
    """Configuration for how workspace is provided to tools."""

    IMPLICIT = "implicit"  # workspace from env, no parameter in tool signature
    EXPLICIT = "explicit"  # workspace as required parameter in tool signature


class MemoryType(StrEnum):
    """Configuration for how memory is provided to tools."""

    EXPLORABLE = "explorable"
    REFERENCEABLE = "referenceable"
    BOTH = "both"
    NO_MEMORY = "no_memory"


@dataclass
class ToolConfig:
    """Configuration for tool registration."""

    needs_client: bool = False
    needs_workspace: bool = False
    memory_type: MemoryType = MemoryType.NO_MEMORY
    custom_args: dict[str, Any] | None = None  # For special cases like search_component_definition


def get_workspace_from_env() -> str:
    """Gets the workspace configured from environment variable."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


# Tool registry with configurations
TOOL_REGISTRY = {
    # Workspace tools
    "list_pipelines": (
        list_pipelines_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "create_pipeline": (
        create_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "update_pipeline": (
        update_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "get_pipeline": (
        get_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "deploy_pipeline": (
        deploy_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "validate_pipeline": (
        validate_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "get_pipeline_logs": (
        get_pipeline_logs_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_pipeline": (
        search_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_indexes": (
        list_indexes_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_index": (
        get_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "create_index": (
        create_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "update_index": (
        update_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "deploy_index": (
        deploy_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_pipeline_templates": (
        list_pipeline_templates_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_pipeline_template": (
        get_pipeline_template_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_pipeline_templates": (
        search_pipeline_templates_wrapper,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_custom_component_installations": (
        list_custom_component_installations_tool,
        ToolConfig(needs_client=True, needs_workspace=True),
    ),
    "get_latest_custom_component_installation_logs": (
        get_latest_custom_component_installation_logs_tool,
        ToolConfig(needs_client=True, needs_workspace=True),
    ),
    # Non-workspace tools
    "list_component_families": (
        list_component_families_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_component_definition": (
        get_component_definition_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_component_definitions": (
        search_component_definitions_wrapper,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_custom_components": (
        get_custom_components_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_secrets": (list_secrets_tool, ToolConfig(needs_client=True)),
    "get_secret": (get_secret_tool, ToolConfig(needs_client=True)),
}


def create_enhanced_tool(
    base_func: Callable[..., Any], config: ToolConfig, workspace_mode: WorkspaceMode, workspace: str | None = None
) -> Callable[..., Awaitable[Any]]:
    """Universal tool creator that handles client injection, workspace, and decorators.

    Args:
        base_func: The base tool function
        config: Tool configuration specifying dependencies
        workspace_mode: How workspace should be handled
        workspace: Workspace to use for implicit mode

    Returns:
        Enhanced tool function with appropriate signature
    """
    # Apply decorators first (if needed)
    decorated_func = base_func
    if config.memory_type != "none":
        store = STORE
        explorer = RichExplorer(store)

        if config.memory_type == "explorable":
            decorated_func = explorable(object_store=store, explorer=explorer)(decorated_func)
        elif config.memory_type == "referenceable":
            decorated_func = referenceable(object_store=store, explorer=explorer)(decorated_func)
        elif config.memory_type == "both":
            decorated_func = explorable_and_referenceable(object_store=store, explorer=explorer)(decorated_func)

    # Handle client and workspace injection
    if config.needs_client:
        if config.needs_workspace:
            # Workspace + client tools
            if workspace_mode == WorkspaceMode.IMPLICIT:
                # Remove client and workspace from signature
                sig = inspect.signature(decorated_func)
                params = list(sig.parameters.values())[2:]  # Skip client and workspace
                new_sig = sig.replace(parameters=params)

                async def workspace_implicit_wrapper(*args: Any, **kwargs: Any) -> Any:
                    ws = workspace or get_workspace_from_env()
                    async with AsyncDeepsetClient() as client:
                        # Add custom args if specified
                        if config.custom_args:
                            kwargs.update(config.custom_args)
                        return await decorated_func(client, ws, *args, **kwargs)

                wrapper = workspace_implicit_wrapper
                wrapper.__signature__ = new_sig  # type: ignore
            else:
                # EXPLICIT mode - remove only client from signature
                sig = inspect.signature(decorated_func)
                params = list(sig.parameters.values())[1:]  # Skip client parameter
                new_sig = sig.replace(parameters=params)

                async def workspace_explicit_wrapper(*args: Any, **kwargs: Any) -> Any:
                    async with AsyncDeepsetClient() as client:
                        # Add custom args if specified
                        if config.custom_args:
                            kwargs.update(config.custom_args)
                        return await decorated_func(client, *args, **kwargs)

                wrapper = workspace_explicit_wrapper
                wrapper.__signature__ = new_sig  # type: ignore
        else:
            # Client-only tools (no workspace)
            sig = inspect.signature(decorated_func)
            params = list(sig.parameters.values())[1:]  # Skip client parameter
            new_sig = sig.replace(parameters=params)

            async def client_only_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with AsyncDeepsetClient() as client:
                    # Add custom args if specified
                    if config.custom_args:
                        kwargs.update(config.custom_args)
                    return await decorated_func(client, *args, **kwargs)

            wrapper = client_only_wrapper
            wrapper.__signature__ = new_sig  # type: ignore
    else:
        # No injection needed
        wrapper = decorated_func

    # Set metadata
    wrapper.__name__ = base_func.__name__

    # Process docstring to remove injected parameters
    if config.needs_client and base_func.__doc__:
        import re

        doc = base_func.__doc__

        # Remove :param client: line
        doc = re.sub(r"^\s*:param\s+client:.*?(?=^\s*:|^\s*$|\Z)", "", doc, flags=re.MULTILINE | re.DOTALL)

        # Remove :param workspace: line if implicit mode
        if config.needs_workspace and workspace_mode == WorkspaceMode.IMPLICIT:
            doc = re.sub(r"^\s*:param\s+workspace:.*?(?=^\s*:|^\s*$|\Z)", "", doc, flags=re.MULTILINE | re.DOTALL)

        wrapper.__doc__ = doc
    else:
        wrapper.__doc__ = base_func.__doc__

    return wrapper


def register_all_tools(mcp: FastMCP, workspace_mode: WorkspaceMode, workspace: str | None = None) -> None:
    """Register all tools with unified configuration.

    Args:
        mcp: FastMCP server instance
        workspace_mode: How workspace should be handled
        workspace: Workspace to use for implicit mode (if None, reads from env)
    """
    for _tool_name, (base_func, config) in TOOL_REGISTRY.items():
        # Create enhanced tool
        enhanced_tool = create_enhanced_tool(base_func, config, workspace_mode, workspace)  # type: ignore[arg-type]

        mcp.add_tool(enhanced_tool)
