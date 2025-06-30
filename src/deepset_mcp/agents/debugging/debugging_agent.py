from pathlib import Path

from haystack.components.agents.agent import Agent
from haystack.utils.auth import Secret
from haystack_integrations.components.generators.anthropic.chat.chat_generator import AnthropicChatGenerator
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo

from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.interactive import (
    ConfirmationCallback,
    ConfirmationManager,
    InteractiveMCPToolset,
)


def get_agent(
    benchmark_config: BenchmarkConfig,
    interactive: bool = False,
    confirmation_callback: ConfirmationCallback | None = None,
    confirmation_manager: ConfirmationManager | None = None,
) -> Agent:
    """Get an instance of the Debugging agent."""
    server_info = StdioServerInfo(
        command="uv",
        args=["run", "deepset-mcp"],
        env={
            "DEEPSET_WORKSPACE": benchmark_config.deepset_workspace,
            "DEEPSET_API_KEY": benchmark_config.deepset_api_key,
            "DEEPSET_DOCS_API_KEY": benchmark_config.get_env_var("DEEPSET_DOCS_API_KEY"),
            "DEEPSET_DOCS_WORKSPACE": benchmark_config.get_env_var("DEEPSET_DOCS_WORKSPACE"),
            "DEEPSET_DOCS_PIPELINE_NAME": benchmark_config.get_env_var("DEEPSET_DOCS_PIPELINE_NAME"),
        },
    )

    if interactive:
        if not confirmation_callback or not confirmation_manager:
            raise ValueError("Confirmation callback and manager are required for interactive mode.")
        tools = InteractiveMCPToolset(
            server_info=server_info, confirmation_callback=confirmation_callback, manager=confirmation_manager
        )
    else:
        tools = MCPToolset(server_info=server_info)

    prompt = (Path(__file__).parent / "system_prompt.md").read_text()
    generator = AnthropicChatGenerator(
        model="claude-sonnet-4-20250514",
        generation_kwargs={"max_tokens": 8000},
        api_key=Secret.from_token(benchmark_config.get_env_var("ANTHROPIC_API_KEY")),
    )

    return Agent(tools=tools, system_prompt=prompt, chat_generator=generator)
