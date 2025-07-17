# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Factory for creating workspace-aware MCP tools."""

import functools
import inspect
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DEFAULT_CLIENT_HEADER
from deepset_mcp.store import STORE
from deepset_mcp.tool_models import MemoryType, ToolConfig, WorkspaceMode
from deepset_mcp.tool_registry import TOOL_REGISTRY
from deepset_mcp.tools.tokonomics import RichExplorer, explorable, explorable_and_referenceable, referenceable


def are_docs_available() -> bool:
    """Checks if documentation search is available."""
    return bool(
        os.environ.get("DEEPSET_DOCS_WORKSPACE", False)
        and os.environ.get("DEEPSET_DOCS_PIPELINE_NAME", False)
        and os.environ.get("DEEPSET_DOCS_API_KEY", False)
    )


def get_workspace_from_env() -> str:
    """Gets the workspace configured from environment variable."""
    workspace = os.environ.get("DEEPSET_WORKSPACE")
    if not workspace:
        raise ValueError("DEEPSET_WORKSPACE environment variable not set")
    return workspace


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
