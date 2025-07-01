"""
Async-compatible practical streaming callback for deepset agent responses.

Handles text streaming, tool calls, and tool results with nice console formatting.
"""

import json
from typing import Any

from haystack.dataclasses.streaming_chunk import StreamingChunk
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown


class StreamingCallbackManager:
    """
    Async-compatible callback tailored to your exact streaming structure.

    Handles the specific patterns from your deepset agent.
    """

    def __init__(self) -> None:
        """Initialize the streaming callback."""
        self.console = Console()
        self.active_tools: dict[int, dict[str, Any]] = {}
        self.accumulated_text = ""
        self.live_display: Live | None = None
        self.text_started = False

    async def __call__(self, chunk: StreamingChunk) -> None:
        """Process each streaming chunk asynchronously."""
        await self._handle_chunk(chunk)

    async def _handle_chunk(self, chunk: StreamingChunk) -> None:
        """Handle different types of chunks based on your data structure."""
        meta = chunk.meta

        # 1. Handle text streaming (like "I'll help you troubleshoot...")
        if self._is_text_delta(meta):
            text = meta["delta"]["text"]
            self.accumulated_text += text
            await self._render_markdown_optimistic()

        # 2. Handle tool call start (like list_pipelines, get_pipeline)
        elif self._is_tool_start(meta):
            await self._handle_tool_start(meta)

        # 3. Handle tool arguments streaming (partial JSON)
        elif self._is_tool_args(meta):
            await self._handle_tool_args(meta)

        # 4. Handle tool results
        elif self._is_tool_result(meta):
            await self._handle_tool_result(meta)

        # 5. Handle message deltas (usage info, etc.)
        elif self._is_message_delta(meta):
            await self._handle_message_delta(meta)

        if self._is_finish_event(meta):
            await self._handle_finish_event(meta)

    async def _render_markdown_optimistic(self) -> None:
        """Render accumulated text as markdown optimistically."""
        if not self.accumulated_text.strip():
            return

        try:
            # Attempt to render as markdown
            markdown = Markdown(self.accumulated_text)

            # Start live display if not already started
            if not self.live_display:
                self.live_display = Live(markdown, console=self.console, refresh_per_second=10)
                self.live_display.start()
                self.text_started = True
            else:
                # Update the live display
                self.live_display.update(markdown)

        except Exception:
            # Fallback to plain text if markdown parsing fails
            if not self.live_display:
                self.live_display = Live(self.accumulated_text, console=self.console, refresh_per_second=10)
                self.live_display.start()
                self.text_started = True
            else:
                self.live_display.update(self.accumulated_text)

    def _is_text_delta(self, meta: dict[str, Any]) -> bool:
        """Check if this is a text streaming chunk."""
        return meta.get("type") == "content_block_delta" and meta.get("delta", {}).get("type") == "text_delta"

    def _is_tool_start(self, meta: dict[str, Any]) -> bool:
        """Check if this is the start of a tool call."""
        return meta.get("type") == "content_block_start" and meta.get("content_block", {}).get("type") == "tool_use"

    def _is_tool_args(self, meta: dict[str, Any]) -> bool:
        """Check if this is tool arguments streaming."""
        return meta.get("type") == "content_block_delta" and meta.get("delta", {}).get("type") == "input_json_delta"

    def _is_tool_result(self, meta: dict[str, Any]) -> bool:
        """Check if this is a tool result."""
        return "tool_result" in meta and "tool_call" in meta

    def _is_message_delta(self, meta: dict[str, Any]) -> bool:
        """Check if this is a message-level delta."""
        return meta.get("type") == "message_delta"

    def _is_finish_event(self, meta: dict[str, Any]) -> bool:
        """Check if this is a finish event."""
        return "stop_reason" in meta.get("delta", {})

    async def _handle_tool_start(self, meta: dict[str, Any]) -> None:
        """Handle the start of a tool call."""
        content_block = meta["content_block"]
        tool_name = content_block["name"]
        tool_id = content_block["id"]
        index = meta["index"]

        # Stop live display if active
        if self.live_display:
            self.live_display.stop()
            self.live_display = None

        # Store tool state
        self.active_tools[index] = {
            "name": tool_name,
            "id": tool_id,
            "args_json": "",
            "started": True,
            "args_displayed": False,
        }

        # Display tool call header (text accumulation continues after tools)
        self.console.print()  # New line
        self.console.print("┌─ 🔧 Tool Call", style="bold cyan")
        self.console.print(f"│ Name: {tool_name}", style="cyan")

    async def _handle_tool_args(self, meta: dict[str, Any]) -> None:
        """Handle streaming tool arguments."""
        index = meta["index"]
        if index not in self.active_tools:
            return

        partial_json = meta["delta"]["partial_json"]
        self.active_tools[index]["args_json"] += partial_json

        # Try to show current args when we have complete JSON
        await self._try_display_complete_args(index)

    async def _try_display_complete_args(self, index: int) -> None:
        """Try to display complete arguments when JSON is valid."""
        tool = self.active_tools[index]

        try:
            # Try to parse the current JSON
            if tool["args_json"].strip() and not tool["args_displayed"]:
                args = json.loads(tool["args_json"])

                # Display arguments in multi-line format
                await self._display_tool_arguments(args)
                tool["args_displayed"] = True

        except json.JSONDecodeError:
            # Still accumulating JSON, wait for more
            pass

    async def _display_tool_arguments(self, args: dict[str, Any]) -> None:
        """Display tool arguments in a pretty multi-line format."""
        if not args:
            self.console.print("│ (no arguments)", style="dim")
            return

        self.console.print("│ Arguments:", style="cyan")

        for arg_name, arg_value in args.items():
            self.console.print(f"│   {arg_name}:", style="yellow")

            # Format the argument value with line limit
            formatted_value = await self._format_argument_value(arg_value, max_lines=5)

            # Display each line of the value with proper indentation
            for line in formatted_value:
                self.console.print(f"│     {line}", style="white")

    async def _format_argument_value(self, value: Any, max_lines: int = 5) -> list[str]:
        """Format an argument value with line limits."""
        if value is None:
            return ["null"]

        if isinstance(value, bool):
            return [str(value).lower()]

        if isinstance(value, int | float):
            return [str(value)]

        if isinstance(value, str):
            # Handle multi-line strings
            lines = value.split("\n")

            # Limit lines
            display_lines = lines[:max_lines]
            result = []

            for line in display_lines:
                # Wrap long lines at 60 characters for readability
                if len(line) <= 60:
                    result.append(f'"{line}"' if line else '""')
                else:
                    result.append(f'"{line[:57]}..."')

            # Add truncation indicator if needed
            if len(lines) > max_lines:
                result.append(f"... ({len(lines) - max_lines} more lines)")

            return result

        if isinstance(value, list | dict):
            # Pretty print complex objects
            try:
                json_str = json.dumps(value, indent=2)
                lines = json_str.split("\n")

                display_lines = lines[:max_lines]
                if len(lines) > max_lines:
                    display_lines.append(f"... ({len(lines) - max_lines} more lines)")

                return display_lines
            except Exception:
                return [str(value)[:100] + "..." if len(str(value)) > 100 else str(value)]

        # Fallback for other types
        str_value = str(value)
        if len(str_value) > 60:
            return [str_value[:57] + "..."]
        return [str_value]

    async def _handle_tool_result(self, meta: dict[str, Any]) -> None:
        """Handle tool execution results."""
        tool_result = meta["tool_result"]

        # Close the tool call display
        self.console.print("└─ ✅ Completed", style="green")

        # Display tool result content (max 10 lines)
        if tool_result:
            await self._display_tool_result(tool_result)

    async def _display_tool_result(self, tool_result: str, max_lines: int = 10) -> None:
        """Display tool result with a maximum number of lines."""
        try:
            # Parse the tool result JSON
            if isinstance(tool_result, str):
                result_data = json.loads(tool_result)

                # Extract the actual content
                content_text = await self._extract_result_content(result_data)

                if content_text:
                    # Split into lines and limit to max_lines
                    lines = content_text.split("\n")
                    display_lines = lines[:max_lines]

                    # Show the result with indentation
                    self.console.print("  ┌─ Result:", style="dim cyan")
                    for line in display_lines:
                        if line.strip():  # Only show non-empty lines
                            self.console.print(f"  │ {line}", style="dim")

                    # Show truncation indicator if needed
                    if len(lines) > max_lines:
                        remaining = len(lines) - max_lines
                        self.console.print(f"  │ ... ({remaining} more lines)", style="dim yellow")

                    self.console.print("  └─", style="dim cyan")
                else:
                    self.console.print("  → Result received", style="dim green")

        except Exception:
            # Fallback for unparseable results
            self.console.print("  → Result received", style="dim green")

    async def _extract_result_content(self, result_data: dict[str, Any]) -> str | None:
        """Extract meaningful content from tool result data."""
        try:
            # Handle the specific structure from your deepset results
            if isinstance(result_data, dict):
                content = result_data.get("content", [])

                if isinstance(content, list) and content:
                    # Get the first content item
                    first_content = content[0]

                    if isinstance(first_content, dict):
                        text_content = first_content.get("text", "")

                        # Handle nested JSON strings (like "@obj_001 → deepset_mcp...")
                        if text_content.startswith('"') and text_content.endswith('"'):
                            # Parse the inner JSON string
                            inner_content = json.loads(text_content)
                            formatted = await self._format_deepset_content(str(inner_content))
                            return formatted
                        else:
                            return str(text_content) if text_content else None

            return str(result_data) if result_data else None

        except Exception:
            return str(result_data) if result_data else None

    async def _format_deepset_content(self, content: str) -> str:
        """Format deepset-specific content for better readability."""
        try:
            # Handle content like "@obj_001 → deepset_mcp.api.pipeline.models.PipelineList..."
            if " → " in content:
                parts = content.split(" → ", 1)
                if len(parts) == 2:
                    obj_id, obj_content = parts

                    # Clean up the object content for better display
                    formatted = obj_content.replace("\\n", "\n").replace("\\\\", "\\")

                    # Add object ID as header
                    return f"Object: {obj_id}\n{formatted}"

            # Fallback: clean up escape sequences
            return content.replace("\\n", "\n").replace("\\\\", "\\")

        except Exception:
            return content

    async def _handle_message_delta(self, meta: dict[str, Any]) -> None:
        """Handle message-level information."""
        delta = meta.get("delta", {})

        # Could show usage info if desired
        if "usage" in delta:
            usage = delta["usage"]
            if usage.get("output_tokens"):
                # Optionally show token usage
                pass

    async def _handle_finish_event(self, meta: dict[str, Any]) -> None:
        """Handle finish events."""
        finish_reason = meta.get("delta", {}).get("stop_reason")
        if finish_reason == "tool_call_results":
            # Clean up after tool calls
            self.active_tools.clear()
            self.console.print()  # Extra line after tools
        elif finish_reason == "end_turn":
            # Stop live display and reset for next interaction
            if self.live_display:
                self.live_display.stop()
                self.live_display = None
                # Ensure cursor is on a new line for the next prompt
                self.console.print()
            self.accumulated_text = ""
            self.text_started = False
