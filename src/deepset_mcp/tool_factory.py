# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Factory for creating workspace-aware MCP tools."""

import functools
import inspect
import os
import re
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

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
    custom_args: dict[str, Any] = field(default_factory=dict)


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


def apply_custom_args(base_func: Callable[..., Any], config: ToolConfig) -> Callable[..., Any]:
    """
    Applies custom keyword arguments defined in the ToolConfig to a function.

    Removes the partially applied keyword arguments from the function's signature and docstring.

    :param base_func: The function to apply custom keyword arguments to.
    :param config: The ToolConfig for the function.
    :returns: Function with custom arguments applied and updated signature/docstring.
    """
    if not config.custom_args:
        return base_func

    @functools.wraps(base_func)
    async def func_with_custom_args(*args: Any, **kwargs: Any) -> Any:
        # Create a partial function with the custom arguments bound.
        partial_func = functools.partial(base_func, **(config.custom_args or {}))
        # Await the result of the partial function call.
        return await partial_func(**kwargs)

    # Remove custom args from signature
    original_sig = inspect.signature(base_func)
    new_params = [p for name, p in original_sig.parameters.items() if name not in config.custom_args]
    func_with_custom_args.__signature__ = original_sig.replace(parameters=new_params)  # type: ignore

    # Remove custom args from docstring.
    func_with_custom_args.__doc__ = remove_params_from_docstring(base_func.__doc__, set(config.custom_args.keys()))

    return func_with_custom_args


def remove_params_from_docstring(docstring: str | None, params_to_remove: set[str]) -> str:
    """Removes specified parameters from a function's docstring.

    :param docstring: The docstring to remove the parameters from.
    :param params_to_remove: The set of parameters to remove.
    :returns: The changed docstring.
    """
    if docstring is None:
        return ""

    for param_name in params_to_remove:
        docstring = re.sub(
            rf"^\s*:param\s+{re.escape(param_name)}.*?(?=^\s*:|^\s*$|\Z)",
            "",
            docstring,
            flags=re.MULTILINE | re.DOTALL,
        )

    return "\n".join([line.rstrip() for line in docstring.strip().split("\n")])


def apply_workspace(
    base_func: Callable[..., Any], config: ToolConfig, workspace_mode: WorkspaceMode, workspace: str | None = None
) -> Callable[..., Any]:
    """
    Applies a deepset workspace to the function depending on the workspace mode and the ToolConfig.

    Removes the workspace argument from the function's signature and docstring if applied.

    :param base_func: The function to apply workspace to.
    :param config: The ToolConfig for the function.
    :param workspace_mode: The WorkspaceMode for the function.
    :param workspace: The workspace to use for static mode.
    :returns: Function with workspace handling applied and updated signature/docstring.
    :raises ValueError: If workspace is required but not available.
    """
    if not config.needs_workspace:
        return base_func

    if workspace_mode == WorkspaceMode.STATIC:

        @functools.wraps(base_func)
        async def workspace_wrapper(*args: Any, **kwargs: Any) -> Any:
            ws = workspace or get_workspace_from_env()
            return await base_func(*args, workspace=ws, **kwargs)

        # Remove workspace from signature
        original_sig = inspect.signature(base_func)
        new_params = [p for name, p in original_sig.parameters.items() if name != "workspace"]
        workspace_wrapper.__signature__ = original_sig.replace(parameters=new_params)  # type: ignore

        # Remove workspace from docstring
        workspace_wrapper.__doc__ = remove_params_from_docstring(base_func.__doc__, {"workspace"})

        return workspace_wrapper
    else:
        # For dynamic mode, workspace is passed as parameter
        return base_func


def apply_memory(base_func: Callable[..., Any], config: ToolConfig) -> Callable[..., Any]:
    """
    Applies memory decorators to a function if requested in the ToolConfig.

    :param base_func: The function to apply memory decorator to.
    :param config: The ToolConfig for the function.
    :returns: Function with memory decorators applied.
    :raises ValueError: If an invalid memory type is specified.
    """
    if config.memory_type == MemoryType.NO_MEMORY:
        return base_func

    store = STORE
    explorer = RichExplorer(store)

    if config.memory_type == MemoryType.EXPLORABLE:
        return explorable(object_store=store, explorer=explorer)(base_func)
    elif config.memory_type == MemoryType.REFERENCEABLE:
        return referenceable(object_store=store, explorer=explorer)(base_func)
    elif config.memory_type == MemoryType.BOTH:
        return explorable_and_referenceable(object_store=store, explorer=explorer)(base_func)
    else:
        raise ValueError(f"Invalid memory type: {config.memory_type}")


def apply_client(
    base_func: Callable[..., Any], config: ToolConfig, use_request_context: bool = True
) -> Callable[..., Any]:
    """
    Applies the deepset API client to a function.

    Optionally collects the API key from the request context, when use_request_context is True.
    Modifies the function's signature and docstring to remove the client argument.
    Adds a 'ctx' argument to the signature if the request context is used.

    :param base_func: The function to apply the client to.
    :param config: The ToolConfig for the function.
    :param use_request_context: Whether to collect the API key from the request context.
    :returns: Function with client injection applied and updated signature/docstring.
    :raises ValueError: If API key cannot be extracted from request context.
    """
    if not config.needs_client:
        return base_func

    if use_request_context:

        @functools.wraps(base_func)
        async def client_wrapper_with_context(*args: Any, **kwargs: Any) -> Any:
            ctx = kwargs.pop("ctx", None)
            if not ctx:
                raise ValueError("Context is required for client authentication")

            api_key = ctx.request_context.request.headers.get("Authorization")
            if not api_key:
                raise ValueError("No Authorization header found in request context")

            api_key = api_key.replace("Bearer ", "")

            if not api_key:
                raise ValueError("API key cannot be empty")

            async with AsyncDeepsetClient(transport_config=DEFAULT_CLIENT_HEADER, api_key=api_key) as client:
                return await base_func(*args, client=client, **kwargs)

        # Remove client from signature and add ctx
        original_sig = inspect.signature(base_func)
        new_params = [p for name, p in original_sig.parameters.items() if name != "client"]
        ctx_param = inspect.Parameter(name="ctx", kind=inspect.Parameter.KEYWORD_ONLY, annotation=Context)
        new_params.append(ctx_param)
        client_wrapper_with_context.__signature__ = original_sig.replace(parameters=new_params)  # type: ignore

        # Remove client from docstring
        if base_func.__doc__:
            import re

            doc = base_func.__doc__
            doc = re.sub(
                r"^\s*:param\s+client.*?(?=^\s*:|^\s*$|\Z)",
                "",
                doc,
                flags=re.MULTILINE | re.DOTALL,
            )
            client_wrapper_with_context.__doc__ = "\n".join([line.rstrip() for line in doc.strip().split("\n")])

        return client_wrapper_with_context
    else:

        @functools.wraps(base_func)
        async def client_wrapper_without_context(*args: Any, **kwargs: Any) -> Any:
            async with AsyncDeepsetClient(transport_config=DEFAULT_CLIENT_HEADER) as client:
                return await base_func(*args, client=client, **kwargs)

        # Remove client from signature
        original_sig = inspect.signature(base_func)
        new_params = [p for name, p in original_sig.parameters.items() if name != "client"]
        client_wrapper_without_context.__signature__ = original_sig.replace(parameters=new_params)  # type: ignore

        # Remove client from docstring
        client_wrapper_without_context.__doc__ = remove_params_from_docstring(base_func.__doc__, {"client"})

        return client_wrapper_without_context


def build_tool(
    base_func: Callable[..., Any],
    config: ToolConfig,
    workspace_mode: WorkspaceMode,
    workspace: str | None = None,
    use_request_context: bool = True,
) -> Callable[..., Awaitable[Any]]:
    """
    Universal tool creator that handles client injection, workspace, and decorators.

    This function takes a base tool function and enhances it based on the tool's configuration.

    :param base_func: The base tool function.
    :param config: Tool configuration specifying dependencies and custom arguments.
    :param workspace_mode: How the workspace should be handled.
    :param workspace: The workspace to use when using a static workspace.
    :param use_request_context: Whether to collect the API key from the request context.
    :returns: An enhanced, awaitable tool function with an updated signature and docstring.
    """
    enhanced_func = base_func

    # Apply custom arguments first
    enhanced_func = apply_custom_args(enhanced_func, config)

    # Apply memory decorators
    enhanced_func = apply_memory(enhanced_func, config)

    # Apply workspace handling
    enhanced_func = apply_workspace(enhanced_func, config, workspace_mode, workspace)

    # Apply client injection (adds ctx parameter if needed)
    enhanced_func = apply_client(enhanced_func, config, use_request_context=use_request_context)

    # Create final async wrapper if needed
    if not inspect.iscoroutinefunction(enhanced_func):

        @functools.wraps(enhanced_func)
        async def async_wrapper(**kwargs: Any) -> Any:
            return enhanced_func(**kwargs)

        # Copy over the signature from the enhanced function
        async_wrapper.__signature__ = inspect.signature(enhanced_func)  # type: ignore
        return async_wrapper

    enhanced_func.__name__ = base_func.__name__

    return enhanced_func


def register_tools(
    mcp: FastMCP,
    workspace_mode: WorkspaceMode,
    workspace: str | None = None,
    tool_names: set[str] | None = None,
    use_request_context: bool = True,
) -> None:
    """Register tools with unified configuration.

    Args:
        mcp: FastMCP server instance
        workspace_mode: How workspace should be handled
        workspace: Workspace to use for environment mode (if None, reads from env)
        tool_names: Set of tool names to register (if None, registers all tools)
        use_request_context: Whether to use request context to retrieve an API key for tool execution.
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
        enhanced_tool = build_tool(base_func, config, workspace_mode, workspace, use_request_context)

        mcp.add_tool(enhanced_tool, name=tool_name, structured_output=False)
