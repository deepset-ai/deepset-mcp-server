from collections.abc import Awaitable, Callable
from typing import Any

from haystack.tools import Tool
from haystack_integrations.tools.mcp.mcp_tool import AsyncExecutor, MCPServerInfo
from haystack_integrations.tools.mcp import MCPToolset


class ConfirmationManager:
    """Manages which tools are auto-confirmed during a REPL session."""

    def __init__(self) -> None:
        """Initialize the confirmation manager."""
        self.auto_confirmed_tools: set[str] = set()

    def add(self, tool_name: str) -> None:
        """Add a tool to the auto-confirmation list."""
        self.auto_confirmed_tools.add(tool_name)

    def is_auto_confirmed(self, tool_name: str) -> bool:
        """Check if a tool is set for auto-confirmation."""
        return tool_name in self.auto_confirmed_tools


# Define the signature for the confirmation callback
ConfirmationCallback = Callable[[str, dict[str, Any]], Awaitable[tuple[bool, bool, str | None]]]


def create_interactive_tool(
    tool: Tool, confirmation_callback: ConfirmationCallback, manager: ConfirmationManager
) -> Tool:
    """Wraps an existing tool to add an interactive confirmation step before execution.

    This is achieved by replacing the tool's `function` with a new function that
    prompts for confirmation before calling the original function.
    """
    original_function = tool.function

    def interactive_function(**kwargs: Any) -> Any:
        """Wrapper function that adds confirmation logic before executing the tool."""
        tool_name = tool.name

        # 1. Check if the tool is already auto-confirmed
        if manager.is_auto_confirmed(tool_name):
            return original_function(**kwargs)

        # 2. If not, invoke the async confirmation callback from this sync method
        # using the shared AsyncExecutor instance.
        executor = AsyncExecutor.get_instance()
        should_run, should_auto_confirm, user_message = executor.run(confirmation_callback(tool_name, kwargs))

        # 3. Based on user feedback, either run the tool or return a message
        if should_run:
            if should_auto_confirm:
                manager.add(tool_name)
            return original_function(**kwargs)
        else:
            # The user rejected the tool call. Return a message to the agent.
            rejection_message = f"Tool call '{tool_name}' was rejected by the user."
            if user_message:
                rejection_message += f" User provided this feedback: \n{user_message}"
            return rejection_message

    tool.function = interactive_function

    return tool


class InteractiveMCPToolset(MCPToolset):
    """An MCPToolset that wraps each tool with an interactive confirmation layer."""

    tools: list[Tool]

    def __init__(
        self,
        server_info: MCPServerInfo,
        confirmation_callback: ConfirmationCallback,
        manager: ConfirmationManager,
        tool_names: list[str] | None = None,
        connection_timeout: float = 30.0,
        invocation_timeout: float = 30.0,
    ):
        """Initialize the interactive MCP toolset."""
        # First, initialize the parent MCPToolset. This will connect to the server
        # and populate self.tools with standard Haystack Tool instances.
        super().__init__(
            server_info=server_info,
            tool_names=tool_names,
            connection_timeout=connection_timeout,
            invocation_timeout=invocation_timeout,
        )

        # Now, wrap each of the newly created tools with our interactive layer.
        interactive_tools: list[Tool] = [
            create_interactive_tool(tool, confirmation_callback, manager) for tool in self.tools
        ]
        self.tools = interactive_tools
