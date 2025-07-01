from pathlib import Path

from haystack.components.agents.agent import Agent
from haystack.utils.auth import Secret
from haystack_integrations.components.generators.anthropic.chat.chat_generator import AnthropicChatGenerator
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo

from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.interactive import wrap_toolset_interactive


def get_agent(
    benchmark_config: BenchmarkConfig,
    interactive: bool = False,
) -> Agent:
    """Get an instance of the Generalist agent."""
    server_info = StdioServerInfo(
        command="uv",
        args=["run", "deepset-mcp"],
        env={
            "DEEPSET_WORKSPACE": benchmark_config.deepset_workspace,
            "DEEPSET_API_KEY": benchmark_config.deepset_api_key,
        },
    )

    tools = MCPToolset(server_info=server_info, invocation_timeout=300.0)

    if interactive:
        tools = wrap_toolset_interactive(tools).toolset

    prompt = (Path(__file__).parent / "system_prompt.md").read_text()
    generator = AnthropicChatGenerator(
        model="claude-sonnet-4-20250514",
        generation_kwargs={"max_tokens": 8000},
        api_key=Secret.from_token(benchmark_config.get_env_var("ANTHROPIC_API_KEY")),
    )

    return Agent(tools=tools, system_prompt=prompt, chat_generator=generator)
