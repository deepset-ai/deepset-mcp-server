# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Factory for creating workspace-aware MCP tools."""

import functools
import inspect
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from mcp.server.fastmcp import FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DEFAULT_CLIENT_HEADER
from deepset_mcp.initialize_embedding_model import get_initialized_model
from deepset_mcp.store import STORE
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs as get_latest_custom_component_installation_logs_tool,
    list_custom_component_installations as list_custom_component_installations_tool,
)
from deepset_mcp.tools.doc_search import (
    search_docs as search_docs_tool,
)
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    get_custom_components as get_custom_components_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
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
    get_template as get_pipeline_template_tool,
    list_templates as list_pipeline_templates_tool,
    search_templates as search_pipeline_templates_tool,
)
from deepset_mcp.tools.secrets import (
    get_secret as get_secret_tool,
    list_secrets as list_secrets_tool,
)
from deepset_mcp.tools.tokonomics import RichExplorer, explorable, explorable_and_referenceable, referenceable
from deepset_mcp.tools.workspace import (
    create_workspace as create_workspace_tool,
    get_workspace as get_workspace_tool,
    list_workspaces as list_workspaces_tool,
)


def are_docs_available() -> bool:
    """Checks if documentation search is available."""
    return bool(
        os.environ.get("DEEPSET_DOCS_WORKSPACE", False)
        and os.environ.get("DEEPSET_DOCS_PIPELINE_NAME", False)
        and os.environ.get("DEEPSET_DOCS_API_KEY", False)
    )


EXPLORER = RichExplorer(store=STORE)


def get_from_object_store(object_id: str, path: str = "") -> str:
    """Use this tool to fetch an object from the object store.

    You can fetch a specific object by using the object's id (e.g. `@obj_001`).
    You can also fetch any nested path by using the path-parameter
        (e.g. `{"object_id": "@obj_001", "path": "user_info.given_name"}`
        -> returns the content at obj.user_info.given_name).

    :param object_id: The id of the object to fetch in the format `@obj_001`.
    :param path: The path of the object to fetch in the format of `access.to.attr` or `["access"]["to"]["attr"]`.
    """
    return EXPLORER.explore(obj_id=object_id, path=path)


def get_slice_from_object_store(
    object_id: str,
    start: int = 0,
    end: int | None = None,
    path: str = "",
) -> str:
    """Extract a slice from a string or list object that is stored in the object store.

    :param object_id: Identifier of the object.
    :param start: Start index for slicing.
    :param end: End index for slicing (optional - leave empty to get slice from start to end of sequence).
    :param path: Navigation path to object to slice (optional).
    :return: String representation of the slice.
    """
    return EXPLORER.slice(obj_id=object_id, start=start, end=end, path=path)


async def search_docs(query: str) -> str:
    """Search the deepset platform documentation.

    This tool allows you to search through deepset's official documentation to find
    information about features, API usage, best practices, and troubleshooting guides.
    Use this when you need to look up specific deepset functionality or help users
    understand how to use deepset features.

    :param query: The search query to execute against the documentation.
    :returns: The formatted search results from the documentation.
    """
    async with AsyncDeepsetClient(
        api_key=os.environ["DEEPSET_DOCS_API_KEY"], transport_config=DEFAULT_CLIENT_HEADER
    ) as client:
        response = await search_docs_tool(
            client=client,
            workspace=os.environ["DEEPSET_DOCS_WORKSPACE"],
            pipeline_name=os.environ["DEEPSET_DOCS_PIPELINE_NAME"],
            query=query,
        )
    return response


class WorkspaceMode(StrEnum):
    """Configuration for how workspace is provided to tools."""

    STATIC = "static"  # workspace from env, no parameter in tool signature
    DYNAMIC = "dynamic"  # workspace as required parameter in tool signature


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


TOOL_REGISTRY: dict[str, tuple[Callable[..., Any], ToolConfig]] = {
    # Workspace tools
    "list_pipelines": (
        list_pipelines_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "create_pipeline": (
        create_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.BOTH,
            custom_args={"skip_validation_errors": True},
        ),
    ),
    "update_pipeline": (
        update_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.BOTH,
            custom_args={"skip_validation_errors": True},
        ),
    ),
    "get_pipeline": (
        get_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "deploy_pipeline": (
        deploy_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"wait_for_deployment": True, "timeout_seconds": 600, "poll_interval": 5},
        ),
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
    "list_templates": (
        list_pipeline_templates_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"field": "created_at", "order": "DESC", "limit": 100},
        ),
    ),
    "get_template": (
        get_pipeline_template_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_templates": (
        search_pipeline_templates_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"model": get_initialized_model()},
        ),
    ),
    "list_custom_component_installations": (
        list_custom_component_installations_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_latest_custom_component_installation_logs": (
        get_latest_custom_component_installation_logs_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
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
        search_component_definition_tool,
        ToolConfig(
            needs_client=True, memory_type=MemoryType.EXPLORABLE, custom_args={"model": get_initialized_model()}
        ),
    ),
    "get_custom_components": (
        get_custom_components_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_secrets": (list_secrets_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_secret": (get_secret_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "list_workspaces": (list_workspaces_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_workspace": (get_workspace_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "create_workspace": (create_workspace_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_from_object_store": (get_from_object_store, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
    "get_slice_from_object_store": (get_slice_from_object_store, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
    "search_docs": (search_docs, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
}


def create_enhanced_tool(
    base_func: Callable[..., Any], config: ToolConfig, workspace_mode: WorkspaceMode, workspace: str | None = None
) -> Callable[..., Awaitable[Any]]:
    """Universal tool creator that handles client injection, workspace, and decorators.

    This function takes a base tool function and enhances it based on a configuration.
    It can inject a `client`, manage a `workspace` parameter (either explicitly required
    or implicitly provided from the environment), and apply memory-related decorators.

    It also supports partial application of custom arguments specified in the ToolConfig.
    These arguments are bound to the function, and both the function signature and the
    docstring are updated to hide these implementation details from the end user of the tool.

    All parameters in the final tool signature are converted to be keyword-only to enforce
    explicit naming of arguments in tool calls.

    Args:
        base_func: The base tool function.
        config: Tool configuration specifying dependencies and custom arguments.
        workspace_mode: How the workspace should be handled.
        workspace: The workspace to use when using a static workspace.

    Returns:
        An enhanced, awaitable tool function with an updated signature and docstring.
    """
    original_func = base_func

    # If custom arguments are provided, create a wrapper that applies them.
    # This wrapper preserves the original function's metadata so that decorators work correctly.
    func_to_decorate: Any
    if config.custom_args:

        @functools.wraps(original_func)
        async def func_with_custom_args(*args: Any, **kwargs: Any) -> Any:
            # Create a partial function with the custom arguments bound.
            partial_func = functools.partial(original_func, **(config.custom_args or {}))
            # Await the result of the partial function call.
            return await partial_func(**kwargs)

        func_to_decorate = func_with_custom_args
    else:
        func_to_decorate = original_func

    # Apply memory-related decorators to the (potentially wrapped) function
    decorated_func = func_to_decorate
    if config.memory_type != MemoryType.NO_MEMORY:
        store = STORE
        explorer = RichExplorer(store)

        if config.memory_type == MemoryType.EXPLORABLE:
            decorated_func = explorable(object_store=store, explorer=explorer)(decorated_func)
        elif config.memory_type == MemoryType.REFERENCEABLE:
            decorated_func = referenceable(object_store=store, explorer=explorer)(decorated_func)
        elif config.memory_type == MemoryType.BOTH:
            decorated_func = explorable_and_referenceable(object_store=store, explorer=explorer)(decorated_func)

    # Determine the parameters to remove from the original function's signature
    params_to_remove: set[str] = set()
    if config.custom_args:
        params_to_remove.update(config.custom_args.keys())
    if config.needs_client:
        params_to_remove.add("client")
    if config.needs_workspace and workspace_mode == WorkspaceMode.STATIC:
        params_to_remove.add("workspace")

    # Create the new signature from the original function
    original_sig = inspect.signature(original_func)
    final_params = [p for name, p in original_sig.parameters.items() if name not in params_to_remove]

    # Convert all positional-or-keyword parameters to be keyword-only
    keyword_only_params = [
        p.replace(kind=inspect.Parameter.KEYWORD_ONLY) if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD else p
        for p in final_params
    ]
    new_sig = original_sig.replace(parameters=keyword_only_params)

    # Create the final wrapper function that handles client/workspace injection
    if config.needs_client:
        if config.needs_workspace:
            if workspace_mode == WorkspaceMode.STATIC:

                async def workspace_environment_wrapper(**kwargs: Any) -> Any:
                    ws = workspace or get_workspace_from_env()
                    async with AsyncDeepsetClient(transport_config=DEFAULT_CLIENT_HEADER) as client:
                        return await decorated_func(client=client, workspace=ws, **kwargs)

                wrapper = workspace_environment_wrapper
            else:  # DYNAMIC mode

                async def workspace_explicit_wrapper(**kwargs: Any) -> Any:
                    async with AsyncDeepsetClient(transport_config=DEFAULT_CLIENT_HEADER) as client:
                        # The first argument is the workspace, which must be passed by keyword.
                        return await decorated_func(client=client, **kwargs)

                wrapper = workspace_explicit_wrapper
        else:  # Client-only tools

            async def client_only_wrapper(**kwargs: Any) -> Any:
                async with AsyncDeepsetClient(transport_config=DEFAULT_CLIENT_HEADER) as client:
                    return await decorated_func(client=client, **kwargs)

            wrapper = client_only_wrapper
    else:  # No injection needed
        if inspect.iscoroutinefunction(decorated_func):

            async def no_injection_wrapper(**kwargs: Any) -> Any:
                return await decorated_func(**kwargs)

            wrapper = no_injection_wrapper
        else:

            @functools.wraps(decorated_func)
            async def async_wrapper(**kwargs: Any) -> Any:
                return decorated_func(**kwargs)

            wrapper = async_wrapper

    # Set metadata on the final wrapper
    wrapper.__signature__ = new_sig  # type: ignore
    wrapper.__name__ = original_func.__name__

    # Process the docstring to remove injected and partially applied parameters
    if original_func.__doc__:
        import re

        doc = original_func.__doc__
        params_to_remove_from_doc = set()
        if config.needs_client:
            params_to_remove_from_doc.add("client")
        if config.needs_workspace and workspace_mode == WorkspaceMode.STATIC:
            params_to_remove_from_doc.add("workspace")
        if config.custom_args:
            params_to_remove_from_doc.update(config.custom_args.keys())

        for param_name in params_to_remove_from_doc:
            doc = re.sub(
                rf"^\s*:param\s+{re.escape(param_name)}.*?(?=^\s*:|^\s*$|\Z)",
                "",
                doc,
                flags=re.MULTILINE | re.DOTALL,
            )

        wrapper.__doc__ = "\n".join([line.rstrip() for line in doc.strip().split("\n")])
    else:
        wrapper.__doc__ = original_func.__doc__

    return wrapper


def register_tools(
    mcp: FastMCP, workspace_mode: WorkspaceMode, workspace: str | None = None, tool_names: set[str] | None = None
) -> None:
    """Register tools with unified configuration.

    Args:
        mcp: FastMCP server instance
        workspace_mode: How workspace should be handled
        workspace: Workspace to use for environment mode (if None, reads from env)
        tool_names: Set of tool names to register (if None, registers all tools)
    """
    # Check if docs search is available
    docs_available = are_docs_available()

    # Validate tool names if provided
    if tool_names is not None:
        all_tools = set(TOOL_REGISTRY.keys())
        invalid_tools = tool_names - all_tools
        if invalid_tools:
            sorted_invalid = sorted(invalid_tools)
            sorted_all = sorted(all_tools)
            raise ValueError(f"Unknown tools: {', '.join(sorted_invalid)}\nAvailable tools: {', '.join(sorted_all)}")

        # Warn if search_docs was requested but config is missing
        if "search_docs" in tool_names and not docs_available:
            logging.warning(
                "Documentation search tool requested but not available. To enable, set the DEEPSET_DOCS_SHARE_URL "
                "environment variable."
            )

        tools_to_register = tool_names.copy()
    else:
        tools_to_register = set(TOOL_REGISTRY.keys())

        # Warn if search_docs would be skipped in "all tools" mode
        if not docs_available:
            logging.warning(
                "Documentation search tool not enabled. To enable, set the DEEPSET_DOCS_SHARE_URL environment variable."
            )

    # Remove search_docs if config is not available
    if not docs_available:
        tools_to_register.discard("search_docs")

    for tool_name in tools_to_register:
        base_func, config = TOOL_REGISTRY[tool_name]
        # Create enhanced tool
        enhanced_tool = create_enhanced_tool(base_func, config, workspace_mode, workspace)

        mcp.add_tool(enhanced_tool, name=tool_name, structured_output=False)
