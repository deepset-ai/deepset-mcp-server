from collections.abc import Callable
from typing import Any

from haystack.tools import Tool, Toolset
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

TOOL_CONFIRMATION_CHAR = "y"
TOOL_REJECTED_CHAR = "n"
TOOL_AUTO_CONFIRM_CHAR = "a"


class InteractiveToolsetWrapper:
    """Simple wrapper that adds interactive confirmation to any toolset."""

    def __init__(self, toolset: Toolset):
        """
        Initialize the wrapper.

        Args:
            toolset: The base toolset to wrap
        """
        self.base_toolset = toolset
        self.auto_confirm_tools: set[str] = set()
        self.console = Console()

        # Create wrapped toolset
        self._wrapped_toolset = self._create_wrapped_toolset()

    def _create_wrapped_toolset(self) -> Toolset:
        """Create a new toolset with wrapped tools."""
        wrapped_tools = []

        for tool in self.base_toolset.tools:
            wrapped_tool = Tool(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                function=self._wrap_function(tool),
            )
            wrapped_tools.append(wrapped_tool)

        return Toolset(tools=wrapped_tools)

    def _wrap_function(self, tool: Tool) -> Callable[..., Any]:
        """Wrap a tool function with confirmation logic."""
        original_function = tool.function
        tool_name = tool.name

        def wrapped_function(**kwargs: Any) -> Any:
            # Check if auto-confirmed
            if tool_name in self.auto_confirm_tools:
                self.console.print(f"[green]✓ Auto-executing '{tool_name}'[/green]")
                return original_function(**kwargs)

            # Ask for confirmation
            action = self._ask_confirmation(tool_name, kwargs)

            if action == "reject":
                # Get feedback message
                feedback = Prompt.ask("Feedback message (optional)", default="")
                return {
                    "status": "rejected",
                    "tool": tool_name,
                    "feedback": feedback or "Tool execution rejected by user",
                }
            elif action == "confirm_auto":
                # Add to auto-confirm and execute
                self.auto_confirm_tools.add(tool_name)
                self.console.print(f"[green]✓ '{tool_name}' added to auto-confirm list[/green]")

            # Execute tool (for both "confirm" and "confirm_auto")
            return original_function(**kwargs)

        return wrapped_function

    def _ask_confirmation(self, tool_name: str, params: dict[str, Any]) -> str:
        """Ask user for confirmation with Rich formatting."""
        # Build tool call display
        lines = [f"[bold yellow]Tool:[/bold yellow] {tool_name}"]

        if params:
            lines.append("\n[bold yellow]Arguments:[/bold yellow]")
            for key, value in params.items():
                lines.append(f"\n[cyan]{key}:[/cyan]")
                # Format the value with proper indentation
                value_str = str(value)
                if "\n" in value_str:
                    # Multi-line value - indent each line
                    for line in value_str.split("\n"):
                        lines.append(f"  {line}")
                else:
                    lines.append(f"  {value_str}")

        # Create panel with tool information
        panel = Panel("\n".join(lines), title="🔧 Tool Execution Request", border_style="blue")
        self.console.print(panel)

        # Show options
        self.console.print("\n[bold]Options:[/bold]")
        self.console.print(f"  [green]{TOOL_CONFIRMATION_CHAR}[/green]  - Confirm execution")
        self.console.print(f"  [yellow]{TOOL_AUTO_CONFIRM_CHAR}[/yellow]  - Confirm and auto-confirm this tool")
        self.console.print(f"  [red]{TOOL_REJECTED_CHAR}[/red]  - Reject execution")

        # Get user choice
        while True:
            choice = Prompt.ask(
                "\nYour choice", choices=[TOOL_CONFIRMATION_CHAR, TOOL_AUTO_CONFIRM_CHAR, TOOL_REJECTED_CHAR]
            )

            if choice == TOOL_CONFIRMATION_CHAR:
                return "confirm"
            elif choice == TOOL_AUTO_CONFIRM_CHAR:
                return "confirm_auto"
            elif choice == TOOL_REJECTED_CHAR:
                return "reject"

    @property
    def toolset(self) -> Toolset:
        """Get the wrapped toolset."""
        return self._wrapped_toolset

    def close(self) -> None:
        """Close the underlying toolset if it has a close method."""
        if hasattr(self.base_toolset, "close"):
            self.base_toolset.close()


def wrap_toolset_interactive(toolset: Toolset) -> InteractiveToolsetWrapper:
    """
    Wrap any toolset with interactive confirmation.

    Args:
        toolset: The toolset to wrap

    Returns:
        InteractiveToolsetWrapper instance
    """
    return InteractiveToolsetWrapper(toolset)
