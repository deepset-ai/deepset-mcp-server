"""Unified output handling for consistent benchmark user experience."""

from collections.abc import Callable
from typing import Any, Protocol

import typer
from haystack.dataclasses import StreamingChunk
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from deepset_mcp.benchmark.logging.logging_config import get_benchmark_logger
from deepset_mcp.benchmark.ui.streaming import StreamingCallbackManager


class OutputHandler(Protocol):
    """Interface for handling benchmark output and user interaction."""

    def show_progress(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Show progress message to user."""
        ...

    def show_test_start(self, test_case_name: str, agent_name: str) -> None:
        """Show test case start notification."""
        ...

    def show_test_complete(self, test_case_name: str, success: bool) -> None:
        """Show test case completion notification."""
        ...

    def show_results(self, results: dict[str, Any]) -> None:
        """Show test results."""
        ...

    def show_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Show error message to user."""
        ...

    def show_summary(self, summary: dict[str, Any]) -> None:
        """Show benchmark run summary."""
        ...

    def cleanup_streaming_callback(self, test_case_name: str) -> None:
        """Clean up streaming callback."""
        ...

    def create_streaming_callback(self, test_case_name: str) -> Callable[[StreamingChunk], Any]:
        """Create streaming callback."""
        ...


class ConsoleOutputHandler(OutputHandler):
    """Console-based output handler with consistent formatting."""

    def __init__(self, streaming_enabled: bool = False, debug: bool = False):
        """
        Initialize the output handler.

        Args:
            streaming_enabled: Whether streaming is enabled for this session
            debug: Enable debug output
        """
        self.streaming_enabled = streaming_enabled
        self.console = Console()
        self.logger = get_benchmark_logger(__name__, debug)

    def show_progress(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Show progress message to user."""
        if self.streaming_enabled:
            # In streaming mode, show minimal progress indicators
            self.console.print(f"⏳ {message}", style="dim cyan")
        else:
            # In non-streaming mode, show more detailed progress
            typer.secho(f"→ {message}", fg=typer.colors.BLUE)

        if context and self.logger.logger.isEnabledFor(10):  # DEBUG level
            self.logger.debug(f"Progress: {message}", context)

    def show_test_start(self, test_case_name: str, agent_name: str) -> None:
        """Show test case start notification."""
        if self.streaming_enabled:
            self.console.print(f"\n🤖 [{test_case_name}] Agent '{agent_name}' starting...\n")
        else:
            typer.secho(
                f"🚀 Running test case '{test_case_name}' with agent '{agent_name}'", fg=typer.colors.GREEN, bold=True
            )

    def show_test_complete(self, test_case_name: str, success: bool) -> None:
        """Show test case completion notification."""
        if success:
            if self.streaming_enabled:
                self.console.print(f"\n✅ [{test_case_name}] Test completed.\n")
            else:
                typer.secho(f"✅ Test '{test_case_name}' completed!", fg=typer.colors.GREEN)
        else:
            if self.streaming_enabled:
                self.console.print(f"\n❌ [{test_case_name}] Test failed.\n")
            else:
                typer.secho(f"❌ Test '{test_case_name}' failed!", fg=typer.colors.RED)

    def show_results(self, results: dict[str, Any]) -> None:
        """Show test results."""
        if "result" not in results:
            return

        result_data = results["result"]

        # Show basic metrics
        agent_execution = result_data.get("agent_execution", {})
        usage = agent_execution.get("usage", {})
        validation = result_data.get("validation", {})

        if not self.streaming_enabled:
            # In non-streaming mode, show detailed results
            self.console.print("\n📊 Test Results:")

            # Create results table
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            # Add metrics
            table.add_row("Tool Calls", str(len(agent_execution.get("tool_calls", []))))
            table.add_row("Prompt Tokens", str(usage.get("prompt_tokens", 0)))
            table.add_row("Completion Tokens", str(usage.get("completion_tokens", 0)))
            table.add_row("Total Tokens", str(usage.get("total_tokens", 0)))
            table.add_row("Model", agent_execution.get("model", "unknown"))

            # Add validation results
            pre_val = validation.get("pre_validation", {})
            post_val = validation.get("post_validation", {})

            pre_status = "PASS" if pre_val.get("valid") else "FAIL" if pre_val else "N/A"
            post_status = "PASS" if post_val.get("valid") else "FAIL" if post_val else "N/A"

            table.add_row("Pre-validation", pre_status)
            table.add_row("Post-validation", post_status)

            self.console.print(table)
        else:
            # In streaming mode, show compact summary
            tokens = usage.get("total_tokens", 0)
            tool_calls = len(agent_execution.get("tool_calls", []))
            self.console.print(f"  📈 {tokens} tokens, {tool_calls} tool calls")

    def show_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Show error message to user."""
        error_msg = str(error)

        if self.streaming_enabled:
            # Simple error display for streaming
            self.console.print(f"❌ Error: {error_msg}", style="red")
        else:
            # Detailed error panel for non-streaming
            error_panel = Panel(error_msg, title="❌ Error", border_style="red", padding=(1, 1))
            self.console.print(error_panel)

        # Log error with context
        self.logger.error(f"Error displayed to user: {error_msg}", context or {})

    def show_summary(self, summary: dict[str, Any]) -> None:
        """Show benchmark run summary."""
        self.console.print("\n📊 BENCHMARK SUMMARY", style="bold blue")
        self.console.print("=" * 50, style="blue")

        # Test counts
        total_tests = summary.get("total_tests", 0)
        completed_tests = summary.get("completed_tests", 0)
        failed_tests = summary.get("failed_tests", 0)

        self.console.print(f"Total Tests: {total_tests}")
        self.console.print(
            f"Completed: {completed_tests}", style="green" if completed_tests == total_tests else "yellow"
        )

        if failed_tests > 0:
            self.console.print(f"Failed: {failed_tests}", style="red")

        # Validation results
        validation_passes = summary.get("validation_passes", 0)
        validation_total = summary.get("validation_total", 0)
        validation_rate = summary.get("validation_rate_percent", 0)

        if validation_total > 0:
            self.console.print(
                f"Validation Rate: {validation_rate:.1f}% ({validation_passes}/{validation_total})",
                style=self._get_rate_color(validation_rate),
            )

        # Resource usage
        self.console.print("\nResource Usage:", style="cyan")
        self.console.print(f"  Total Tokens: {summary.get('total_tokens', 0):,}")
        self.console.print(f"  Total Tool Calls: {summary.get('total_tool_calls', 0)}")
        self.console.print(f"  Avg Tool Calls/Test: {summary.get('avg_tool_calls', 0):.1f}")

        # Run info
        self.console.print(f"\nRun ID: {summary.get('run_id', 'unknown')}", style="dim")

    def _get_rate_color(self, rate: float) -> str:
        """Get color for rate display based on value."""
        if rate >= 80:
            return "green"
        elif rate >= 50:
            return "yellow"
        else:
            return "red"

    def cleanup_streaming_callback(self, test_case_name: str) -> None:
        """Clean up streaming callback."""
        # ConsoleOutputHandler doesn't need cleanup
        pass

    def create_streaming_callback(self, test_case_name: str) -> Callable[[StreamingChunk], Any]:
        """Create streaming callback."""

        def callback(chunk: StreamingChunk) -> Any:
            if chunk.content:
                self.console.print(chunk.content, end="")
            return chunk

        return callback


class QuietOutputHandler(OutputHandler):
    """Minimal output handler for automated/scripted usage."""

    def __init__(self, debug: bool = False):
        """Initialize the quiet output handler."""
        self.logger = get_benchmark_logger(__name__, debug)

    def show_progress(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log progress without console output."""
        self.logger.debug(f"Progress: {message}", context or {})

    def show_test_start(self, test_case_name: str, agent_name: str) -> None:
        """Log test start without console output."""
        self.logger.info(
            "Starting test case",
            {
                "test_case": test_case_name,
                "agent": agent_name,
            },
        )

    def show_test_complete(self, test_case_name: str, success: bool) -> None:
        """Log test completion without console output."""
        self.logger.info(
            "Test case completed",
            {
                "test_case": test_case_name,
                "success": success,
            },
        )

    def show_results(self, results: dict[str, Any]) -> None:
        """Log results without console output."""
        if "result" in results:
            agent_execution = results["result"].get("agent_execution", {})
            usage = agent_execution.get("usage", {})
            self.logger.info(
                "Test results",
                {
                    "tokens": usage.get("total_tokens", 0),
                    "tool_calls": len(agent_execution.get("tool_calls", [])),
                    "model": agent_execution.get("model", "unknown"),
                },
            )

    def show_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Log error without console output."""
        self.logger.error(f"Error: {str(error)}", context or {})

    def show_summary(self, summary: dict[str, Any]) -> None:
        """Log summary without console output."""
        self.logger.info("Benchmark summary", summary)

    def cleanup_streaming_callback(self, test_case_name: str) -> None:
        """Clean up streaming callback."""
        # QuietOutputHandler doesn't need cleanup
        pass

    def create_streaming_callback(self, test_case_name: str) -> Callable[[StreamingChunk], Any]:
        """Create streaming callback."""

        def callback(chunk: StreamingChunk) -> Any:
            # In quiet mode, just return the chunk without output
            return chunk

        return callback


def create_output_handler(
    streaming_enabled: bool = False,
    quiet: bool = False,
    debug: bool = False,
) -> OutputHandler:
    """
    Create an output handler.

    Args:
        streaming_enabled: Whether streaming is enabled
        quiet: Use quiet mode (minimal output)
        debug: Enable debug logging

    Returns:
        Configured output handler
    """
    if quiet:
        return QuietOutputHandler(debug)
    elif streaming_enabled:
        return StreamingOutputHandler(debug)
    else:
        return NonStreamingOutputHandler(debug)


class StreamingOutputHandler(ConsoleOutputHandler):
    """Output handler with integrated streaming callback support."""

    def __init__(self, debug: bool = False):
        """
        Initialize the streaming output handler.

        Args:
            debug: Enable debug output
        """
        super().__init__(streaming_enabled=True, debug=debug)
        self.active_callbacks: dict[str, StreamingCallbackManager] = {}
        self.logger = get_benchmark_logger(__name__, debug)

    def create_streaming_callback(self, test_case_name: str) -> Callable[[StreamingChunk], Any]:
        """
        Create a streaming callback for a specific test case.

        Args:
            test_case_name: Name of the test case for context

        Returns:
            Streaming callback function
        """
        # Create callback manager
        callback_manager = StreamingCallbackManager()
        self.active_callbacks[test_case_name] = callback_manager

        async def streaming_callback(chunk: StreamingChunk) -> Any:
            """Handle streaming chunk with context."""
            try:
                return await callback_manager(chunk)
            except Exception as e:
                self.logger.error(
                    "Streaming callback error",
                    {
                        "test_case": test_case_name,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                # Don't re-raise to avoid breaking the agent execution

        return streaming_callback

    def cleanup_streaming_callback(self, test_case_name: str) -> None:
        """
        Clean up streaming callback for a test case.

        Args:
            test_case_name: Name of the test case
        """
        if test_case_name in self.active_callbacks:
            callback_manager = self.active_callbacks.pop(test_case_name)
            # Clean up any live displays
            if hasattr(callback_manager, "live_display") and callback_manager.live_display:
                try:
                    callback_manager.live_display.stop()
                except Exception as e:
                    self.logger.debug(
                        "Error stopping live display",
                        {
                            "test_case": test_case_name,
                            "error": str(e),
                        },
                    )

    def show_test_start(self, test_case_name: str, agent_name: str) -> None:
        """Show test case start notification."""
        # Clean up any existing callback
        self.cleanup_streaming_callback(test_case_name)

        # Show start message
        super().show_test_start(test_case_name, agent_name)

    def show_test_complete(self, test_case_name: str, success: bool) -> None:
        """Show test case completion notification."""
        # Clean up streaming callback
        self.cleanup_streaming_callback(test_case_name)

        # Show completion message
        super().show_test_complete(test_case_name, success)


class NonStreamingOutputHandler(ConsoleOutputHandler):
    """Output handler for non-streaming mode with consistent behavior."""

    def __init__(self, debug: bool = False):
        """
        Initialize the non-streaming output handler.

        Args:
            debug: Enable debug output
        """
        super().__init__(streaming_enabled=False, debug=debug)

    def create_streaming_callback(self, test_case_name: str) -> Callable[[StreamingChunk], Any]:
        """
        Non-streaming mode doesn't use callbacks.

        Args:
            test_case_name: Name of the test case (ignored)

        Returns:
            Dummy callback (no-op in non-streaming mode)
        """

        def dummy_callback(chunk: StreamingChunk) -> Any:
            return chunk

        return dummy_callback

    def cleanup_streaming_callback(self, test_case_name: str) -> None:
        """
        No cleanup needed in non-streaming mode.

        Args:
            test_case_name: Name of the test case (ignored)
        """
        pass
