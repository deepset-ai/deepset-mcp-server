import asyncio
import json
from typing import Any

import typer
from haystack.dataclasses.chat_message import ChatMessage
from haystack.dataclasses.streaming_chunk import StreamingChunk
from rich.console import Console
from rich.syntax import Syntax

from deepset_mcp.benchmark.runner.agent_loader import load_agent
from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.interactive import ConfirmationManager
from deepset_mcp.benchmark.runner.models import AgentConfig
from deepset_mcp.benchmark.runner.streaming import StreamingCallbackManager


async def get_user_confirmation(
    tool_name: str, tool_args: dict[str, Any], console: Console
) -> tuple[bool, bool, str | None]:
    """Prompt the user to confirm a tool call."""
    console.print(f"\n[bold yellow]Tool call proposed:[/] [cyan]{tool_name}[/]")
    if tool_args:
        console.print("[bold yellow]Arguments:[/]")
        # Pretty print the arguments as a JSON object
        json_str = json.dumps(tool_args, indent=2)
        console.print(Syntax(json_str, "json", theme="monokai", line_numbers=True))

    while True:
        response = typer.prompt(
            "Confirm? (y)es, (n)o, (a)uto-confirm for this tool",
            default="y",
            show_default=False,
        ).lower()

        if response in ["y", "yes"]:
            return True, False, None
        if response in ["a", "auto"]:
            return True, True, None
        if response in ["n", "no"]:
            feedback = typer.prompt("Provide feedback to the agent (optional)", default="", show_default=False)
            return False, False, feedback
        console.print("[bold red]Invalid input. Please try again.[/]")


async def run_repl_session_async(agent_config: AgentConfig, benchmark_config: BenchmarkConfig) -> None:
    """Starts an interactive REPL session with the specified agent."""
    console = Console()
    manager = ConfirmationManager()

    async def confirmation_callback(tool_name: str, tool_args: dict[str, Any]) -> tuple[bool, bool, str | None]:
        return await get_user_confirmation(tool_name, tool_args, console)

    agent, _ = load_agent(
        config=agent_config,
        benchmark_config=benchmark_config,
        interactive=agent_config.interactive,
        confirmation_callback=confirmation_callback,
        confirmation_manager=manager,
    )
    history: list[ChatMessage] = []

    typer.secho(f"Starting interactive session with '{agent_config.display_name}'.", fg=typer.colors.CYAN)
    typer.secho("Type 'exit' or 'quit' to end the session.", fg=typer.colors.CYAN)

    while True:
        try:
            user_input = typer.prompt("\n👤 You")
            if user_input.lower() in ["exit", "quit"]:
                typer.secho("Ending session. Goodbye!", fg=typer.colors.MAGENTA)
                break

            # Add user message to history
            history.append(ChatMessage.from_user(user_input))

            # Setup streaming
            streaming_callback_manager = StreamingCallbackManager()

            async def streaming_callback(
                chunk: StreamingChunk,
                manager: StreamingCallbackManager = streaming_callback_manager,
            ) -> Any:
                return await manager(chunk)

            # Run the agent
            typer.secho("\n🤖 Agent", fg=typer.colors.BLUE, nl=False)
            agent_output = await agent.run_async(messages=history, streaming_callback=streaming_callback)

            # The streaming callback handles printing the final text output.
            # We replace our local history with the full history from the agent
            # to preserve the tool calls and results.
            if agent_output and "messages" in agent_output:
                history = agent_output["messages"]

        except (KeyboardInterrupt, EOFError):
            typer.secho("\nEnding session. Goodbye!", fg=typer.colors.MAGENTA)
            break
        except Exception as e:
            typer.secho(f"\nAn error occurred: {e}", fg=typer.colors.RED)
            # Remove the user message that caused the error to prevent it from being re-processed
            if history and history[-1].is_from("user"):
                history.pop()


def run_repl_session(agent_config: AgentConfig, benchmark_config: BenchmarkConfig) -> None:
    """Synchronous wrapper for the REPL session."""
    asyncio.run(run_repl_session_async(agent_config, benchmark_config))
