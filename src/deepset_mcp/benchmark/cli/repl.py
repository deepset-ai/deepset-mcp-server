import asyncio
from typing import Any

import typer
from haystack.dataclasses.chat_message import ChatMessage
from haystack.dataclasses.streaming_chunk import StreamingChunk

from deepset_mcp.benchmark.core.agent_loader import load_agent
from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig
from deepset_mcp.benchmark.ui.streaming import StreamingCallbackManager


class REPLSession:
    """Clean, focused REPL session with an agent."""

    def __init__(self, agent_config: AgentConfig, benchmark_config: BenchmarkConfig):
        """
        Initialize the REPL session.

        Args:
            agent_config: Agent configuration
            benchmark_config: Benchmark configuration
        """
        self.agent_config = agent_config
        self.benchmark_config = benchmark_config
        self.history: list[ChatMessage] = []

        # Load agent directly - REPL doesn't need service layer complexity
        self.agent, self.commit_hash = load_agent(
            config=agent_config,
            benchmark_config=benchmark_config,
            interactive=agent_config.interactive,
        )

    async def run_async(self) -> None:
        """Run the interactive REPL session."""
        typer.secho(f"Starting interactive session with '{self.agent_config.display_name}'.", fg=typer.colors.CYAN)
        typer.secho("Type 'exit' or 'quit' to end the session.", fg=typer.colors.CYAN)

        while True:
            try:
                user_input = typer.prompt("\n👤 You")
                if user_input.lower() in ["exit", "quit"]:
                    typer.secho("Ending session. Goodbye!", fg=typer.colors.MAGENTA)
                    break

                # Add user message to history
                self.history.append(ChatMessage.from_user(user_input))

                # Setup streaming callback
                streaming_callback_manager = StreamingCallbackManager()

                async def streaming_callback(
                    chunk: StreamingChunk, manager: StreamingCallbackManager = streaming_callback_manager
                ) -> Any:
                    return await manager(chunk)

                # Run the agent
                typer.secho("\n🤖 Agent\n\n", fg=typer.colors.BLUE, nl=False)
                agent_output = await self.agent.run_async(messages=self.history, streaming_callback=streaming_callback)

                # Update history with agent response
                if agent_output and "messages" in agent_output:
                    self.history = agent_output["messages"]

            except (KeyboardInterrupt, EOFError):
                typer.secho("\nEnding session. Goodbye!", fg=typer.colors.MAGENTA)
                break


def run_repl_session(agent_config: AgentConfig, benchmark_config: BenchmarkConfig) -> None:
    """
    Run an interactive REPL session with an agent.

    Args:
        agent_config: Agent configuration
        benchmark_config: Benchmark configuration
    """
    session = REPLSession(agent_config, benchmark_config)
    asyncio.run(session.run_async())
