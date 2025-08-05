# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Factory for creating workspace-aware MCP tools."""

import functools
import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DEFAULT_CLIENT_HEADER, DOCS_SEARCH_TOOL_NAME
from deepset_mcp.tool_models import DeepsetDocsConfig, MemoryType, ToolConfig, WorkspaceMode
from deepset_mcp.tool_registry import TOOL_REGISTRY
from deepset_mcp.tools.tokonomics import (
    ObjectStore,
    RichExplorer,
    explorable,
    explorable_and_referenceable,
    referenceable,
)


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
            return await base_func(*args, workspace=workspace, **kwargs)

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


def apply_memory(
    base_func: Callable[..., Any], config: ToolConfig, store: ObjectStore | None = None
) -> Callable[..., Any]:
    """
    Applies memory decorators to a function if requested in the ToolConfig.

    :param base_func: The function to apply memory decorator to.
    :param config: The ToolConfig for the function.
    :param store: The ObjectStore instance to use
    :returns: Function with memory decorators applied.
    :raises ValueError: If an invalid memory type is specified.
    """
    if config.memory_type == MemoryType.NO_MEMORY:
        return base_func

    if store is None:
        raise ValueError("ObjectStore instance is required for memory decorators")

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
    base_func: Callable[..., Any],
    config: ToolConfig,
    use_request_context: bool = True,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Callable[..., Any]:
    """
    Applies the deepset API client to a function.

    Optionally collects the API key from the request context, when use_request_context is True.
    Modifies the function's signature and docstring to remove the client argument.
    Adds a 'ctx' argument to the signature if the request context is used.

    :param base_func: The function to apply the client to.
    :param config: The ToolConfig for the function.
    :param use_request_context: Whether to collect the API key from the request context.
    :param base_url: Base URL for the deepset API.
    :param api_key: The API key to use.
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

            client_kwargs: dict[str, Any] = {"transport_config": DEFAULT_CLIENT_HEADER, "api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            async with AsyncDeepsetClient(**client_kwargs) as client:
                return await base_func(*args, client=client, **kwargs)

        # Remove client from signature and add ctx
        original_sig = inspect.signature(base_func)
        new_params = [p for name, p in original_sig.parameters.items() if name != "client"]
        ctx_param = inspect.Parameter(name="ctx", kind=inspect.Parameter.KEYWORD_ONLY, annotation=Context)
        new_params.append(ctx_param)
        client_wrapper_with_context.__signature__ = original_sig.replace(parameters=new_params)  # type: ignore
        client_wrapper_with_context.__doc__ = remove_params_from_docstring(base_func.__doc__, {"client"})

        return client_wrapper_with_context
    else:

        @functools.wraps(base_func)
        async def client_wrapper_without_context(*args: Any, **kwargs: Any) -> Any:
            client_kwargs: dict[str, Any] = {"transport_config": DEFAULT_CLIENT_HEADER, "api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            async with AsyncDeepsetClient(**client_kwargs) as client:
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
    api_key: str | None = None,
    workspace: str | None = None,
    use_request_context: bool = True,
    base_url: str | None = None,
    object_store: ObjectStore | None = None,
) -> Callable[..., Awaitable[Any]]:
    """
    Universal tool creator that handles client injection, workspace, and decorators.

    This function takes a base tool function and enhances it based on the tool's configuration.

    :param base_func: The base tool function.
    :param config: Tool configuration specifying dependencies and custom arguments.
    :param workspace_mode: How the workspace should be handled.
    :param api_key: The deepset API key to use.
    :param workspace: The workspace to use when using a static workspace.
    :param use_request_context: Whether to collect the API key from the request context.
    :param base_url: Base URL for the deepset API.
    :param object_store: The ObjectStore instance to use for memory decorators.
    :returns: An enhanced, awaitable tool function with an updated signature and docstring.
    """
    enhanced_func = base_func

    # Apply custom arguments first
    enhanced_func = apply_custom_args(enhanced_func, config)

    # Apply memory decorators with the provided store
    enhanced_func = apply_memory(enhanced_func, config, object_store)

    # Apply workspace handling
    enhanced_func = apply_workspace(enhanced_func, config, workspace_mode, workspace)

    # Apply client injection (adds ctx parameter if needed)
    enhanced_func = apply_client(
        enhanced_func, config, use_request_context=use_request_context, base_url=base_url, api_key=api_key
    )

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
    mcp_server_instance: FastMCP,
    workspace_mode: WorkspaceMode,
    api_key: str | None = None,
    workspace: str | None = None,
    tool_names: set[str] | None = None,
    get_api_key_from_authorization_header: bool = True,
    docs_config: DeepsetDocsConfig | None = None,
    base_url: str | None = None,
    object_store: ObjectStore | None = None,
) -> None:
    """Register tools with unified configuration.

    Args:
        mcp_server_instance: FastMCP server instance
        workspace_mode: How workspace should be handled
        api_key: An api key for the deepset AI platform; only needs to be provided when not read from request context.
        workspace: Workspace to use; only needs to be provided if using a static workspace.
        tool_names: Set of tool names to register (if None, registers all tools)
        get_api_key_from_authorization_header: Whether to use request context to retrieve an API key for tool execution.
        docs_config: Configuration for the deepset documentation search tool.
        base_url: Base URL for the deepset API.
        object_store: The ObjectStore instance to use for memory decorators.
    """
    if api_key is None and not get_api_key_from_authorization_header:
        raise ValueError(
            "'api_key' cannot be 'None' when 'use_request_context' is False. "
            "Either pass 'api_key' or 'use_request_context'."
        )

    if workspace_mode == WorkspaceMode.STATIC and workspace is None:
        raise ValueError(
            "'workspace_mode' set to 'static' but no workspace provided. "
            "You need to set a deepset workspace name as 'workspace'."
        )

    if docs_config is None and tool_names is None:
        raise ValueError(
            f"'docs_config' cannot be None when requesting to register all tools. "
            f"Either pass 'docs_config' or disable the '{DOCS_SEARCH_TOOL_NAME}' tool."
        )

    if docs_config is None and tool_names is not None and DOCS_SEARCH_TOOL_NAME in tool_names:
        raise ValueError(
            f"Requested to register '{DOCS_SEARCH_TOOL_NAME}' tool but 'docs_config' is 'None'. "
            f"Provide a valid 'docs_config' to register this tool."
        )

    # Validate tool names if provided
    if tool_names is not None:
        all_tools = set(TOOL_REGISTRY.keys())
        invalid_tools = tool_names - all_tools
        if invalid_tools:
            sorted_invalid = sorted(invalid_tools)
            sorted_all = sorted(all_tools)
            raise ValueError(f"Unknown tools: {', '.join(sorted_invalid)}\nAvailable tools: {', '.join(sorted_all)}")

        tools_to_register = tool_names.copy()
    else:
        tools_to_register = set(TOOL_REGISTRY.keys())

    for tool_name in tools_to_register:
        base_func, config = TOOL_REGISTRY[tool_name]

        if tool_name == DOCS_SEARCH_TOOL_NAME:
            # search_docs is a special tool.
            # base_func is a factory function.
            # We configure with the docs_config to get the actual tool function.
            enhanced_tool = base_func(config=docs_config)
        elif tool_name in ("get_from_object_store", "get_slice_from_object_store"):
            # ObjectStore tools are factory functions that need an explorer created from the store
            if object_store is None:
                raise ValueError(f"ObjectStore instance is required for {tool_name}")

            explorer = RichExplorer(store=object_store)
            enhanced_tool = base_func(explorer=explorer)
        else:
            enhanced_tool = build_tool(
                base_func=base_func,
                config=config,
                workspace_mode=workspace_mode,
                workspace=workspace,
                use_request_context=get_api_key_from_authorization_header,
                base_url=base_url,
                object_store=object_store,
                api_key=api_key,
            )

        mcp_server_instance.add_tool(enhanced_tool, name=tool_name, structured_output=False)
