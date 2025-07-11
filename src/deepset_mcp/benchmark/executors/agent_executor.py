from typing import Any, Protocol

from haystack.dataclasses import ChatMessage

from deepset_mcp.benchmark.core.agent_loader import load_agent
from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig, TestCaseConfig
from deepset_mcp.benchmark.core.exceptions import AgentExecutionError
from deepset_mcp.benchmark.logging.logging_config import get_benchmark_logger
from deepset_mcp.benchmark.ui.streaming import StreamingCallbackManager


class AgentExecutor(Protocol):
    """Interface for executing agents against test cases."""

    async def execute_agent(
        self,
        test_case: TestCaseConfig,
        streaming_enabled: bool = False,
        streaming_callback: Any = None,
    ) -> dict[str, Any]:
        """Execute agent against a test case."""
        ...

    def get_agent_info(self) -> dict[str, str]:
        """Get agent information (name, version, etc.)."""
        ...


class HaystackAgentExecutor(AgentExecutor):
    """Agent executor for Haystack-based agents."""

    def __init__(
        self,
        agent_config: AgentConfig,
        benchmark_config: BenchmarkConfig,
        debug: bool = False,
    ) -> None:
        """
        Initialize the agent executor.

        Args:
            agent_config: Agent configuration
            benchmark_config: Benchmark configuration
            debug: Enable debug logging
        """
        self.agent_config = agent_config
        self.benchmark_config = benchmark_config
        self.logger = get_benchmark_logger(__name__, debug)

        # Load the agent
        self.agent, self.commit_hash = load_agent(config=agent_config, benchmark_config=benchmark_config)

        self.logger.info(
            "Agent executor initialized",
            {
                "agent_name": agent_config.display_name,
                "commit_hash": self.commit_hash,
            },
        )

    async def execute_agent(
        self,
        test_case: TestCaseConfig,
        streaming_enabled: bool = False,
        streaming_callback: Any = None,
    ) -> dict[str, Any]:
        """Execute agent against a test case."""
        try:
            self.logger.info(
                "Executing agent against test case",
                {
                    "test_case": test_case.name,
                    "agent": self.agent_config.display_name,
                    "streaming": streaming_enabled,
                },
            )

            # Create message from test case prompt
            messages = [ChatMessage.from_user(test_case.prompt)]

            # Set up streaming if enabled
            actual_callback = None
            if streaming_enabled and streaming_callback:
                actual_callback = streaming_callback
            elif streaming_enabled:
                # Create default streaming callback
                callback_manager = StreamingCallbackManager()

                async def default_callback(chunk: Any) -> Any:
                    return await callback_manager(chunk)

                actual_callback = default_callback

            # Execute agent
            agent_output = await self.agent.run_async(messages=messages, streaming_callback=actual_callback)

            # Extract statistics from messages
            stats = self._extract_message_stats(agent_output.get("messages", []))

            result = {
                "messages": [msg.to_dict() for msg in agent_output.get("messages", [])],
                "usage": stats.get("usage", {}),
                "tool_calls": stats.get("tool_calls", []),
                "model": stats.get("model", "unknown"),
            }

            self.logger.info(
                "Agent execution completed",
                {
                    "test_case": test_case.name,
                    "agent": self.agent_config.display_name,
                    "stats": stats,
                },
            )

            return result

        except Exception as e:
            raise AgentExecutionError(test_case.name, self.agent_config.display_name, e) from e

    def get_agent_info(self) -> dict[str, str]:
        """Get agent information."""
        return {
            "name": self.agent_config.display_name,
            "type": "function" if self.agent_config.agent_factory_function else "json",
            "factory_function": self.agent_config.agent_factory_function or "",
            "json_config": self.agent_config.agent_json or "",
            "commit_hash": getattr(self, "commit_hash", "unknown"),
        }

    def _extract_message_stats(self, messages: list[ChatMessage]) -> dict[str, Any]:
        """Extract statistics from agent messages."""
        total_tool_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        model = None
        tool_calls = []

        for message in messages:
            if not message.is_from("assistant"):
                continue

            # Count tool calls
            if message.tool_calls:
                total_tool_calls += len(message.tool_calls)
                # Handle tool calls (check if they have to_dict method)
                for tc in message.tool_calls:
                    if hasattr(tc, "to_dict"):
                        tool_calls.append(tc.to_dict())
                    else:
                        # Fallback for tool calls without to_dict method
                        tool_calls.append(
                            {
                                "tool_call_id": getattr(tc, "tool_call_id", ""),
                                "tool_name": getattr(tc, "tool_name", ""),
                                "arguments": getattr(tc, "arguments", {}),
                            }
                        )

            # Extract token counts and model from meta
            meta = message.meta
            if "usage" in meta:
                usage = meta["usage"]
                total_prompt_tokens += usage.get("prompt_tokens", 0) or 0
                total_completion_tokens += usage.get("completion_tokens", 0) or 0

            # Extract model
            if "model" in meta and model is None:
                model = meta["model"]

        return {
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            },
            "tool_calls": tool_calls,
            "model": model or "unknown",
        }
