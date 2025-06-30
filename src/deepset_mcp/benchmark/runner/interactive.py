import json
from collections.abc import Awaitable, Callable
from typing import Any

from haystack.core.component import component
from haystack.tools import Tool
from haystack_integrations.tools.mcp.mcp_tool import AsyncExecutor, MCPServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset


class ConfirmationManager:
    """Manages which tools are auto-confirmed during a REPL session."""

    def __init__(self) -> None:
        self.auto_confirmed_tools: set[str] = set()

    def add(self, tool_name: str) -> None:
        """Add a tool to the auto-confirmation list."""
        self.auto_confirmed_tools.add(tool_name)

    def is_auto_confirmed(self, tool_name: str) -> bool:
        """Check if a tool is set for auto-confirmation."""
        return tool_name in self.auto_confirmed_tools


# Define the signature for the confirmation callback
ConfirmationCallback = Callable[[str, dict[str, Any]], Awaitable[tuple[bool, bool, str | None]]]


def create_interactive_tool(tool: Tool, confirmation_callback: ConfirmationCallback, manager: ConfirmationManager) -> Tool:
    """
    Dynamically creates a new Haystack Component that wraps an existing tool
    to add an interactive confirmation step before execution.
    """

    @component
    class InteractiveToolWrapper:
        def __init__(self, original_tool: Tool):
            self.original_tool = original_tool
            # Copy metadata from the original tool to the wrapper
            component.set_input_types(self, **self.original_tool.__haystack_input__._sockets_dict)
            component.set_output_types(self, **self.original_tool.__haystack_output__._sockets_dict)

        def run(self, **kwargs: Any) -> dict[str, Any]:
            """Synchronously run the tool with interactive confirmation."""
            tool_name = self.original_tool.name

            # 1. Check if the tool is already auto-confirmed
            if manager.is_auto_confirmed(tool_name):
                return self.original_tool.run(**kwargs)

            # 2. If not, invoke the async confirmation callback from this sync method
            # using the shared AsyncExecutor instance.
            executor = AsyncExecutor.get_instance()
            should_run, should_auto_confirm, user_message = executor.run(
                confirmation_callback(tool_name, kwargs)
            )

            # 3. Based on user feedback, either run the tool or return a message
            if should_run:
                if should_auto_confirm:
                    manager.add(tool_name)
                return self.original_tool.run(**kwargs)
            else:
                # The user rejected the tool call. Return a message to the agent.
                output_socket_name = next(iter(self.original_tool.__haystack_output__._sockets_dict))
                rejection_message = f"Tool call '{tool_name}' was rejected by the user."
                if user_message:
                    rejection_message += f" User provided this feedback: \n{user_message}"
                return {output_socket_name: rejection_message}

    # Set the new component's name to match the original tool's name
    InteractiveToolWrapper.__name__ = tool.name
    InteractiveToolWrapper.__qualname__ = tool.name

    return InteractiveToolWrapper(original_tool=tool)


class InteractiveMCPToolset(MCPToolset):
    """
    An MCPToolset that wraps each tool with an interactive confirmation layer.
    """

    def __init__(
        self,
        server_info: MCPServerInfo,
        confirmation_callback: ConfirmationCallback,
        manager: ConfirmationManager,
        tool_names: list[str] | None = None,
        connection_timeout: float = 30.0,
        invocation_timeout: float = 30.0,
    ):
        # First, initialize the parent MCPToolset. This will connect to the server
        # and populate self.tools with standard Haystack Tool instances.
        super().__init__(
            server_info=server_info,
            tool_names=tool_names,
            connection_timeout=connection_timeout,
            invocation_timeout=invocation_timeout,
        )

        # Now, wrap each of the newly created tools with our interactive layer.
        interactive_tools = [
            create_interactive_tool(tool, confirmation_callback, manager) for tool in self.tools
        ]
        self.tools = interactive_tools