from pathlib import Path

from haystack.components.agents import Agent
from haystack.utils import Secret

from haystack_integrations.components.generators.anthropic.chat.chat_generator import AnthropicChatGenerator
from haystack_integrations.tools.mcp import MCPToolset, StdioServerInfo


def get_agent(dp_api_key: str, workspace: str, anthropic_api_key) -> Agent:
    """Get an instance of the Generalist agent."""
    tools = MCPToolset(
        server_info=StdioServerInfo(
            command="uv",
            args=["run", "deepset-mcp"],
            env={"DEEPSET_API_KEY": dp_api_key, "DEEPSET_WORKSPACE": workspace},
        )
    )
    prompt = (Path(__file__).parent / "system_prompt.md").read_text()
    generator = AnthropicChatGenerator(model="claude-sonnet-4-20250514", api_key=Secret.from_token(anthropic_api_key))

    return Agent(tools=tools, system_prompt=prompt, chat_generator=generator)
