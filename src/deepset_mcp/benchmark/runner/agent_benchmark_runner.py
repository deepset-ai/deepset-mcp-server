import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from haystack.dataclasses.chat_message import ChatMessage

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.benchmark.runner.agent_loader import load_agent
from deepset_mcp.benchmark.runner.config import BenchmarkConfig
from deepset_mcp.benchmark.runner.config_loader import (
    find_all_test_case_paths,
    load_test_case_by_name,
)
from deepset_mcp.benchmark.runner.models import AgentConfig, TestCaseConfig
from deepset_mcp.benchmark.runner.teardown_actions import teardown_test_case_async
from deepset_mcp.benchmark.runner.tracing import enable_tracing

logger = logging.getLogger(__name__)


class AgentBenchmarkRunner:
    """Main class for running agent benchmarks against test cases."""

    def __init__(
            self,
            agent_config: AgentConfig,
            benchmark_config: BenchmarkConfig,
    ):
        """
        Initialize the benchmark runner.

        Args:
            agent_config: Configuration for the agent to test.
            benchmark_config: Benchmark configuration.
        """
        self.agent_config = agent_config
        self.benchmark_config = benchmark_config

        # Create a single timestamp for this benchmark run
        self.run_timestamp = datetime.now()

        try:
            secret_key = self.benchmark_config.get_env_var("LANGFUSE_SECRET_KEY")
            public_key = self.benchmark_config.get_env_var("LANGFUSE_PUBLIC_KEY")
            logger.info("Langfuse environment variables detected. Enabling tracing with Langfuse.")
            enable_tracing(secret_key=secret_key, public_key=public_key, name="deepset-mcp")
        except KeyError:
            pass

        agent, commit_hash = load_agent(config=agent_config, benchmark_config=benchmark_config)

        self.agent = agent
        self.commit_hash = commit_hash

        # Create the run ID once for all test cases
        self.run_id = f"{self.agent_config.display_name}-{self.commit_hash}_{self.run_timestamp.strftime('%Y%m%d_%H%M%S')}"

    async def run_single_test(self, test_case_name: str) -> dict[str, Any]:
        """
        Run the agent against a single test case.

        Args:
            test_case_name: Name of the test case to run

        Returns:
            Dictionary containing run results and metadata
        """
        logger.info(f"Running test case: {test_case_name}")

        try:
            # Load test case configuration
            test_config = load_test_case_by_name(
                name=test_case_name,
                task_dir=str(self.benchmark_config.test_case_base_dir)
                if self.benchmark_config.test_case_base_dir
                else None,
            )

            index_yaml_config = test_config.get_index_yaml_text()
            index_name = test_config.index_name
            if index_yaml_config and index_name:
                async with AsyncDeepsetClient(api_key=self.benchmark_config.deepset_api_key) as client:
                    await client.indexes(workspace=self.benchmark_config.deepset_workspace).create(
                        name=index_name, yaml_config=index_yaml_config
                    )

            pre_agent_validation = None
            query_yaml_config = test_config.get_query_yaml_text()
            query_name = test_config.query_name
            if query_yaml_config and query_name:
                async with AsyncDeepsetClient(api_key=self.benchmark_config.deepset_api_key) as client:
                    await client.pipelines(workspace=self.benchmark_config.deepset_workspace).create(
                        name=query_name, yaml_config=query_yaml_config
                    )
                    pre_agent_validation = await client.pipelines(
                        workspace=self.benchmark_config.deepset_workspace
                    ).validate(yaml_config=query_yaml_config)

            agent_output = await self.agent.run_async(messages=[ChatMessage.from_user(test_config.prompt)])

            post_agent_validation = None
            if query_name:
                async with AsyncDeepsetClient(api_key=self.benchmark_config.deepset_api_key) as client:
                    pipeline_resource = client.pipelines(workspace=self.benchmark_config.deepset_workspace)
                    updated_pipeline = await pipeline_resource.get(pipeline_name=query_name)
                    assert updated_pipeline.yaml_config, "Pipeline YAML config not found"
                    post_agent_validation = await pipeline_resource.validate(yaml_config=updated_pipeline.yaml_config)

            # Process the results
            processed_data = self._format_results(
                agent_output=agent_output,
                test_config=test_config,
                is_pre_agent_valid=pre_agent_validation.valid if pre_agent_validation else None,
                is_post_agent_valid=post_agent_validation.valid if post_agent_validation else None,
                post_yaml=updated_pipeline.yaml_config if post_agent_validation else None,
            )

            # Save results to filesystem
            test_dir = self._save_run_results(
                processed_data=processed_data,
                test_case_name=test_case_name,
                output_base_dir=self.benchmark_config.output_dir,
            )

            logger.info(f"Test case {test_case_name} completed. Results saved to: {test_dir}")

            return {
                "status": "success",
                "test_case": test_case_name,
                "output_dir": str(test_dir),
                "processed_data": processed_data,
            }

        except Exception as e:
            logger.error(f"Error running test case {test_case_name}: {e}")
            return {"status": "error", "test_case": test_case_name, "error": str(e)}

    async def run_single_test_with_cleanup(self, test_case_name: str) -> dict[str, Any]:
        """
        Run a single test case with automatic cleanup of created resources.

        Args:
            test_case_name: Name of the test case to run

        Returns:
            Dictionary containing run results and metadata
        """
        result = await self.run_single_test(test_case_name)

        # Perform cleanup regardless of test result
        try:
            # Load test config for cleanup
            test_config = load_test_case_by_name(
                name=test_case_name,
                task_dir=self.benchmark_config.test_case_base_dir if self.benchmark_config.test_case_base_dir else None,
            )

            # Cleanup resources
            await teardown_test_case_async(
                test_cfg=test_config,
                workspace_name=self.benchmark_config.deepset_workspace,
                api_key=self.benchmark_config.deepset_api_key,
            )

            logger.info(f"Cleanup completed for test case: {test_case_name}")
            result["cleanup_status"] = "success"

        except Exception as e:
            logger.error(f"Error during cleanup for {test_case_name}: {e}")
            result["cleanup_status"] = "error"
            result["cleanup_error"] = str(e)

        return result

    def run_all_tests(self, test_case_path: Path) -> list[dict[str, Any]]:
        """
        Run the agent against all available test cases.

        Args:
            test_case_path: Directory containing test case files

        Returns:
            List of results for each test case
        """
        # Find all test case files
        test_paths = find_all_test_case_paths(test_case_path)

        if not test_paths:
            logger.warning(f"No test cases found in {test_case_path}")
            return []

        logger.info(f"Found {len(test_paths)} test cases to run")

        # Run tests sequentially with cleanup
        results = []
        for test_path in test_paths:
            test_name = test_path.stem
            result = asyncio.run(self.run_single_test_with_cleanup(test_name))
            results.append(result)

        return results

    async def run_all_tests_async(
            self,
            test_case_path: Path,
            concurrency: int = 1,  # Keep concurrency low to avoid resource conflicts
    ) -> list[dict[str, Any]]:
        """
        Run all test cases asynchronously with controlled concurrency.

        Args:
            test_case_path: Directory containing test case files
            concurrency: Number of concurrent test runs (default: 1 for safety)

        Returns:
            List of results for each test case
        """
        # Find all test case files
        test_paths = find_all_test_case_paths(test_case_path)

        if not test_paths:
            logger.warning(f"No test cases found in {test_case_path}")
            return []

        logger.info(f"Found {len(test_paths)} test cases to run with concurrency={concurrency}")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def run_with_semaphore(test_name: str) -> dict[str, Any]:
            async with semaphore:
                return await self.run_single_test_with_cleanup(test_name)

        # Create tasks for all test cases
        tasks = [asyncio.create_task(run_with_semaphore(test_path.stem)) for test_path in test_paths]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_name = test_paths[i].stem
                logger.error(f"Exception in test {test_name}: {result}")
                processed_results.append({"status": "error", "test_case": test_name, "error": str(result)})
            else:
                processed_results.append(result)  # type: ignore

        return processed_results

    def _format_results(
            self,
            agent_output: dict[str, Any],
            test_config: TestCaseConfig,
            is_pre_agent_valid: bool | None = None,
            is_post_agent_valid: bool | None = None,
            post_yaml: str | None = None,
    ) -> dict[str, Any]:
        """Format the agent output and metadata for saving to file."""
        return {
            "metadata": {
                "commit_hash": self.commit_hash,
                "agent_display_name": self.agent_config.display_name,
                "test_case_name": test_config.name,
                "timestamp": self.run_timestamp.isoformat(),
                "run_id": self.run_id,
            },
            "validation": {
                "pre_validation": "PASS" if is_pre_agent_valid else "FAIL",
                "post_validation": "PASS" if is_post_agent_valid else "FAIL",
            },
            "messages": {
                "serialized": [message.to_dict() for message in agent_output["messages"]],
                "stats": self._extract_assistant_message_stats(agent_output["messages"]),
            },
            "pipeline_yaml": post_yaml,
        }

    @staticmethod
    def _extract_assistant_message_stats(messages: list[ChatMessage]) -> dict[str, str | int]:
        """
        Extract statistics from ChatMessage objects with role=assistant.

        Args:
            messages: List of ChatMessage objects

        Returns:
            Dict containing aggregated statistics and model info
        """
        total_tool_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        model = None

        for message in messages:
            # Only process assistant messages
            if not message.is_from("assistant"):
                continue

            # Count tool calls
            tool_calls = message.tool_calls
            total_tool_calls += len(tool_calls)

            # Extract token counts and model from meta
            meta = message.meta
            if "usage" in meta:
                usage = meta["usage"]
                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_completion_tokens += usage.get("completion_tokens", 0)

            # Extract model (should be consistent across messages)
            if "model" in meta and model is None:
                model = meta["model"]

        return {
            "total_tool_calls": total_tool_calls,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "model": model or "unknown",
        }

    @staticmethod
    def _save_run_results(processed_data: dict[str, Any], test_case_name: str, output_base_dir: Path) -> Path:
        """
        Save the processed run results to the filesystem.

        Args:
            processed_data: Output from process_pipeline_result
            test_case_name: Name of the test case
            output_base_dir: Base directory for saving results

        Returns:
            Path to the created test case directory
        """
        metadata = processed_data["metadata"]
        run_dir = output_base_dir / "agent_runs" / metadata["run_id"]
        test_case_dir: Path = run_dir / test_case_name
        test_case_dir.mkdir(exist_ok=True, parents=True)

        # Save messages.json
        messages_file = test_case_dir / "messages.json"
        with open(messages_file, "w", encoding="utf-8") as f:
            json.dump(processed_data["messages"]["serialized"], f, indent=2, ensure_ascii=False)

        # Save test_results.csv
        csv_file = test_case_dir / "test_results.csv"
        csv_data = [
            "commit,test_case,agent,prompt_tokens,completion_tokens,tool_calls,model,pre_validation,post_validation",
            f"{metadata['commit_hash']},{test_case_name},{metadata['agent_display_name']},"
            f"{processed_data['messages']['stats']['total_prompt_tokens']},"
            f"{processed_data['messages']['stats']['total_completion_tokens']},"
            f"{processed_data['messages']['stats']['total_tool_calls']},"
            f"{processed_data['messages']['stats']['model']},"
            f"{processed_data['validation']['pre_validation']},"
            f"{processed_data['validation']['post_validation']}",
        ]

        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("\n".join(csv_data))

        # Save post_run_pipeline.yml
        if processed_data["pipeline_yaml"]:
            pipeline_file = test_case_dir / "post_run_pipeline.yml"
            with open(pipeline_file, "w", encoding="utf-8") as f:
                f.write(processed_data["pipeline_yaml"])

        return test_case_dir


def run_agent_benchmark(
        agent_config: AgentConfig,
        benchmark_config: BenchmarkConfig,
        test_case_name: str | None = None,
        concurrency: int = 1,
) -> list[dict[str, Any]]:
    """
    Convenience function to run agent benchmarks.

    Args:
        agent_config_path: Path to agent configuration file
        benchmark_config: Benchmark configuration.
        test_case_name: Specific test case to run (if None, runs all)
        concurrency: Number of concurrent test runs

    Returns:
        List of test results
    """
    # Create runner
    runner = AgentBenchmarkRunner(
        agent_config=agent_config,
        benchmark_config=benchmark_config,
    )

    if test_case_name:
        # Run single test case
        result = asyncio.run(runner.run_single_test_with_cleanup(test_case_name))
        return [result]
    else:
        # Run all test cases
        if concurrency == 1:
            return runner.run_all_tests(benchmark_config.test_case_base_dir)
        else:
            return asyncio.run(runner.run_all_tests_async(benchmark_config.test_case_base_dir, concurrency))