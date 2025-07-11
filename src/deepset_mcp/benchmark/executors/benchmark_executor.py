import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from deepset_mcp.benchmark.core.config import AgentConfig, BenchmarkConfig, TestCaseConfig
from deepset_mcp.benchmark.core.exceptions import (
    AgentExecutionError,
    ResourceSetupError,
)
from deepset_mcp.benchmark.core.repository import BenchmarkRepositoryProtocol, FileSystemBenchmarkRepository
from deepset_mcp.benchmark.core.services import ResourceServiceProtocol, get_deepset_resource_service
from deepset_mcp.benchmark.executors.agent_executor import AgentExecutor, HaystackAgentExecutor
from deepset_mcp.benchmark.logging.logging_config import get_benchmark_logger
from deepset_mcp.benchmark.ui.output_handler import OutputHandler, create_output_handler


class BenchmarkExecutor:
    """Benchmarks an agent against a set of test cases."""

    def __init__(
        self,
        agent_executor: AgentExecutor,
        resource_manager: ResourceServiceProtocol,
        benchmark_repository: BenchmarkRepositoryProtocol,
        output_handler: OutputHandler,
        workspace: str,
        run_id: str | None = None,
        debug: bool = False,
    ):
        """
        Initialize the benchmark executor.

        Args:
            agent_executor: Agent execution interface
            resource_manager: Resource management interface
            test_case_repository: Test case loading interface
            result_repository: Result persistence interface
            output_handler: Output handling interface
            workspace: Deepset workspace name
            run_id: Unique run identifier (generated if not provided)
            debug: Enable debug logging
        """
        self.agent_executor = agent_executor
        self.resource_manager = resource_manager
        self.benchmark_repository = benchmark_repository
        self.output_handler = output_handler
        self.workspace = workspace

        # Generate run ID if not provided
        if run_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            agent_info = self.agent_executor.get_agent_info()
            agent_name = agent_info.get("name", "unknown")
            commit_hash = agent_info.get("commit_hash", "unknown")
            run_id = f"{agent_name}_{commit_hash}_{timestamp}"

        self.run_id = run_id
        self.logger = get_benchmark_logger(__name__, debug)

        self.logger.info(
            "Benchmark executor initialized",
            {
                "run_id": self.run_id,
                "workspace": self.workspace,
                "agent": self.agent_executor.get_agent_info(),
            },
        )

    async def run_single_test(
        self,
        test_case_name: str,
        streaming_enabled: bool = False,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Execute a single test case.

        Args:
            test_case_name: Name of the test case to run
            streaming_enabled: Enable streaming output
            output_dir: Directory to save results

        Returns:
            Test execution result
        """
        self.logger.info(
            "Starting test case execution",
            {
                "test_case": test_case_name,
                "run_id": self.run_id,
                "streaming": streaming_enabled,
            },
        )

        try:
            test_case = self.benchmark_repository.load_test_case(test_case_name)

            agent_info = self.agent_executor.get_agent_info()
            self.output_handler.show_test_start(test_case_name, agent_info.get("name", "Unknown"))

            result = await self._execute_test_case(test_case, streaming_enabled)

            if output_dir:
                result_path = self.benchmark_repository.save_test_result(
                    test_case_name=test_case_name,
                    run_id=self.run_id,
                    result_data=result,
                    output_dir=output_dir,
                )
                result["output_path"] = str(result_path)

            self.output_handler.show_test_complete(test_case_name, True)
            self.output_handler.show_results(result)
            self.output_handler.cleanup_streaming_callback(test_case_name)

            self.logger.info(
                "Test case completed successfully",
                {
                    "test_case": test_case_name,
                    "run_id": self.run_id,
                },
            )

            return {
                "status": "success",
                "test_case": test_case_name,
                "run_id": self.run_id,
                "result": result,
            }

        except Exception as e:
            self.logger.error(
                "Test case execution failed",
                {
                    "test_case": test_case_name,
                    "run_id": self.run_id,
                    "error": str(e),
                },
                exc_info=True,
            )

            self.output_handler.show_test_complete(test_case_name, False)
            self.output_handler.show_error(e, {"test_case": test_case_name})
            self.output_handler.cleanup_streaming_callback(test_case_name)

            return {
                "status": "error",
                "test_case": test_case_name,
                "run_id": self.run_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def run_single_test_with_cleanup(
        self,
        test_case_name: str,
        streaming_enabled: bool = False,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Execute a single test case with automatic resource cleanup.

        Args:
            test_case_name: Name of the test case to run
            streaming_enabled: Enable streaming output
            output_dir: Directory to save results

        Returns:
            Test execution result with cleanup status
        """
        result = await self.run_single_test(test_case_name, streaming_enabled, output_dir)

        # Perform cleanup regardless of test result
        cleanup_result = await self._cleanup_test_case(test_case_name)
        result.update(cleanup_result)

        return result

    async def run_multiple_tests(
        self,
        test_case_names: list[str],
        streaming_enabled: bool = False,
        output_dir: Path | None = None,
        concurrency: int = 1,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Execute multiple test cases.

        Args:
            test_case_names: List of test case names to run
            streaming_enabled: Enable streaming output
            output_dir: Directory to save results
            concurrency: Number of concurrent executions

        Returns:
            Tuple of (test results, summary statistics)
        """
        self.logger.info(
            "Starting multiple test execution",
            {
                "test_count": len(test_case_names),
                "run_id": self.run_id,
                "concurrency": concurrency,
            },
        )

        results = []

        if concurrency == 1:
            # Sequential execution
            for test_case_name in test_case_names:
                result = await self.run_single_test_with_cleanup(test_case_name, streaming_enabled, output_dir)
                results.append(result)
        else:
            # Concurrent execution
            results = await self._run_concurrent_tests(test_case_names, streaming_enabled, output_dir, concurrency)

        # Generate summary
        summary = self._generate_summary(results)

        # Save summary
        if output_dir:
            self.benchmark_repository.save_run_summary(
                run_id=self.run_id,
                summary_data=summary,
                output_dir=output_dir,
            )

        self.output_handler.show_summary(summary)

        self.logger.info(
            "Multiple test execution completed",
            {
                "test_count": len(test_case_names),
                "run_id": self.run_id,
                "summary": summary,
            },
        )

        return results, summary

    async def _run_concurrent_tests(
        self,
        test_case_names: list[str],
        streaming_enabled: bool,
        output_dir: Path | None,
        concurrency: int,
    ) -> list[dict[str, Any]]:
        """
        Run test cases concurrently with controlled concurrency.

        Args:
            test_case_names: List of test case names to run
            streaming_enabled: Enable streaming output
            output_dir: Directory to save results
            concurrency: Maximum number of concurrent executions

        Returns:
            List of test results
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def run_with_semaphore(test_case_name: str) -> dict[str, Any]:
            """Run single test with semaphore control."""
            async with semaphore:
                # Note: Streaming might be problematic with concurrent execution
                # Consider disabling streaming for concurrent runs
                actual_streaming = streaming_enabled if concurrency == 1 else False

                return await self.run_single_test_with_cleanup(test_case_name, actual_streaming, output_dir)

        # Create tasks for all test cases
        tasks = [asyncio.create_task(run_with_semaphore(test_case_name)) for test_case_name in test_case_names]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_results: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_name = test_case_names[i]
                self.logger.error(
                    "Exception in concurrent test",
                    {
                        "test_case": test_name,
                        "error": str(result),
                    },
                    exc_info=True,
                )

                processed_results.append(
                    {
                        "status": "error",
                        "test_case": test_name,
                        "run_id": self.run_id,
                        "error": str(result),
                        "error_type": type(result).__name__,
                    }
                )
            else:
                processed_results.append(result)  # type: ignore

        return processed_results

    async def _execute_test_case(
        self,
        test_case: TestCaseConfig,
        streaming_enabled: bool,
    ) -> dict[str, Any]:
        """Execute a single test case with proper resource management."""
        test_case_name = test_case.name

        try:
            # Set up resources
            self.output_handler.show_progress(f"Setting up resources for {test_case_name}")
            setup_result = await self.resource_manager.setup_test_resources(test_case, self.workspace)

            # Pre-validation if applicable
            pre_validation = None
            if test_case.query_name:
                pre_validation = await self.resource_manager.validate_pipeline(test_case.query_name, self.workspace)

            # Start agent execution
            self.output_handler.show_progress(f"Executing agent for {test_case_name}")

            streaming_callback = None
            if streaming_enabled:
                streaming_callback = self.output_handler.create_streaming_callback(test_case_name)

            agent_result = await self.agent_executor.execute_agent(test_case, streaming_enabled, streaming_callback)

            # Post-validation if applicable
            post_validation = None
            post_pipeline_yaml = None
            if test_case.query_name:
                post_validation = await self.resource_manager.validate_pipeline(test_case.query_name, self.workspace)
                updated_pipeline = await self.resource_manager.get_updated_pipeline(
                    test_case.query_name, self.workspace
                )
                if updated_pipeline:
                    post_pipeline_yaml = updated_pipeline.get("yaml_config")

            # Format result
            return self._format_test_result(
                test_case=test_case,
                agent_result=agent_result,
                setup_result=setup_result,
                pre_validation=pre_validation,
                post_validation=post_validation,
                post_pipeline_yaml=post_pipeline_yaml,
            )

        except Exception as e:
            if isinstance(e, ResourceSetupError | AgentExecutionError):
                raise
            else:
                raise AgentExecutionError(
                    test_case_name, self.agent_executor.get_agent_info().get("name", "Unknown"), e
                ) from e

    async def _cleanup_test_case(self, test_case_name: str) -> dict[str, Any]:
        """Clean up resources for a test case."""
        try:
            test_case = self.benchmark_repository.load_test_case(test_case_name)
            await self.resource_manager.cleanup_test_resources(test_case, self.workspace)

            self.logger.info(
                "Cleanup completed for test case",
                {
                    "test_case": test_case_name,
                    "run_id": self.run_id,
                },
            )

            return {"cleanup_status": "success"}

        except Exception as e:
            self.logger.error(
                "Cleanup failed for test case",
                {
                    "test_case": test_case_name,
                    "run_id": self.run_id,
                    "error": str(e),
                },
                exc_info=True,
            )

            return {
                "cleanup_status": "error",
                "cleanup_error": str(e),
            }

    def _format_test_result(
        self,
        test_case: TestCaseConfig,
        agent_result: dict[str, Any],
        setup_result: dict[str, Any],
        pre_validation: dict[str, Any] | None,
        post_validation: dict[str, Any] | None,
        post_pipeline_yaml: str | None,
    ) -> dict[str, Any]:
        """Format test execution result."""
        return {
            "metadata": {
                "test_case_name": test_case.name,
                "run_id": self.run_id,
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_executor.get_agent_info(),
            },
            "test_case": {
                "name": test_case.name,
                "objective": test_case.objective,
                "prompt": test_case.prompt,
                "tags": test_case.tags,
            },
            "setup": setup_result,
            "agent_execution": agent_result,
            "validation": {
                "pre_validation": pre_validation,
                "post_validation": post_validation,
            },
            "post_pipeline_yaml": post_pipeline_yaml,
        }

    def _generate_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate summary statistics from test results."""
        total_tests = len(results)
        completed_tests = len([r for r in results if r["status"] == "success"])
        failed_tests = total_tests - completed_tests

        # Extract metrics from successful tests
        total_tokens = 0
        total_tool_calls = 0
        validation_passes = 0
        validation_total = 0

        for result in results:
            if result["status"] == "success" and "result" in result:
                agent_execution = result["result"].get("agent_execution", {})
                if "usage" in agent_execution:
                    usage = agent_execution["usage"]
                    total_tokens += usage.get("total_tokens", 0)

                if "tool_calls" in agent_execution:
                    total_tool_calls += len(agent_execution["tool_calls"])

                # Check validation results
                validation = result["result"].get("validation", {})
                pre_val = validation.get("pre_validation")
                post_val = validation.get("post_validation")

                if pre_val and post_val:
                    validation_total += 1
                    # Expected: pre fails, post passes (agent fixed the issue)
                    if not pre_val.get("valid", True) and post_val.get("valid", False):
                        validation_passes += 1

        validation_rate = (validation_passes / validation_total * 100) if validation_total > 0 else 0

        return {
            "run_id": self.run_id,
            "total_tests": total_tests,
            "completed_tests": completed_tests,
            "failed_tests": failed_tests,
            "validation_passes": validation_passes,
            "validation_total": validation_total,
            "validation_rate_percent": round(validation_rate, 2),
            "total_tokens": total_tokens,
            "total_tool_calls": total_tool_calls,
            "avg_tool_calls": round(total_tool_calls / completed_tests, 2) if completed_tests > 0 else 0,
        }


def create_benchmark_executor_from_config(
    agent_config_path: str | Path,
    benchmark_config: BenchmarkConfig,
    streaming_enabled: bool = False,
    quiet: bool = False,
    debug: bool = False,
    run_id: str | None = None,
) -> BenchmarkExecutor:
    """
    Create a benchmark executor from configuration file path.

    Args:
        agent_config_path: Path to agent configuration file
        benchmark_config: Benchmark configuration
        streaming_enabled: Whether streaming is enabled
        quiet: Use quiet mode (minimal output)
        debug: Enable debug logging
        run_id: Custom run ID (generated if not provided)

    Returns:
        Configured benchmark executor
    """
    agent_config = AgentConfig.from_file(Path(agent_config_path))

    agent_executor = HaystackAgentExecutor(agent_config, benchmark_config, debug)
    resource_manager = get_deepset_resource_service(api_key=benchmark_config.deepset_api_key, debug=debug)
    benchmark_repository = FileSystemBenchmarkRepository(debug)
    output_handler = create_output_handler(streaming_enabled, quiet, debug)

    return BenchmarkExecutor(
        agent_executor=agent_executor,
        resource_manager=resource_manager,
        benchmark_repository=benchmark_repository,
        output_handler=output_handler,
        workspace=benchmark_config.deepset_workspace,
        run_id=run_id,
        debug=debug,
    )
