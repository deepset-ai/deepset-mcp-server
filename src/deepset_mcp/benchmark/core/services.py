"""Concrete implementations of service layer interfaces."""

import asyncio
from typing import Any, Protocol

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.benchmark.core.config import TestCaseConfig
from deepset_mcp.benchmark.core.exceptions import (
    ResourceCleanupError,
    ResourceSetupError,
)
from deepset_mcp.benchmark.logging.logging_config import get_benchmark_logger


class ResourceServiceProtocol(Protocol):
    """Interface for managing external resources (pipelines, indexes)."""

    async def setup_test_resources(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Set up required resources for a test case."""
        ...

    async def validate_pipeline(self, pipeline_name: str, workspace: str) -> dict[str, Any]:
        """Validate a pipeline configuration."""
        ...

    async def get_updated_pipeline(self, pipeline_name: str, workspace: str) -> dict[str, Any] | None:
        """Get updated pipeline configuration after agent execution."""
        ...

    async def cleanup_test_resources(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Clean up resources created for a test case."""
        ...

    def create_index(self, workspace: str, name: str, yaml_config: str) -> None:
        """Create an index synchronously."""
        ...

    def delete_index(self, workspace: str, name: str) -> None:
        """Delete an index synchronously."""
        ...

    def create_pipeline(self, workspace: str, name: str, yaml_config: str) -> None:
        """Create a pipeline synchronously."""
        ...

    def delete_pipeline(self, workspace: str, name: str) -> None:
        """Delete a pipeline synchronously."""
        ...

    def setup_test_resources_sync(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Set up required resources for a test case synchronously."""
        ...

    def cleanup_test_resources_sync(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Clean up resources created for a test case synchronously."""
        ...

    async def setup_multiple_test_resources(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Set up resources for multiple test cases with configurable concurrency."""
        ...

    async def cleanup_multiple_test_resources(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Clean up resources for multiple test cases with configurable concurrency."""
        ...

    def setup_multiple_test_resources_sync(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Set up resources for multiple test cases synchronously."""
        ...

    def cleanup_multiple_test_resources_sync(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Clean up resources for multiple test cases synchronously."""
        ...


class DeepsetResourceService(ResourceServiceProtocol):
    """Resource service using Deepset API client."""

    def __init__(self, client: AsyncClientProtocol, debug: bool = False):
        """
        Initialize the resource service.

        Args:
            client: Deepset API client
            debug: Enable debug logging
        """
        self.client = client
        self.logger = get_benchmark_logger(__name__, debug)

    async def setup_test_resources(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Set up required resources for a test case."""
        setup_result: dict[str, list[str]] = {"indexes": [], "pipelines": []}

        try:
            # Set up index if specified
            if test_case.index_yaml and test_case.index_name:
                self.logger.info(f"Creating index '{test_case.index_name}'")

                index_config = test_case.get_index_yaml_text()
                if not index_config:
                    raise ResourceSetupError(
                        test_case.name, "index", test_case.index_name, Exception("Index YAML content not available")
                    )

                await self.client.indexes(workspace).create(name=test_case.index_name, yaml_config=index_config)
                setup_result["indexes"].append(test_case.index_name)

            # Set up pipeline if specified
            if test_case.query_yaml and test_case.query_name:
                self.logger.info(f"Creating pipeline '{test_case.query_name}'")

                query_config = test_case.get_query_yaml_text()
                if not query_config:
                    raise ResourceSetupError(
                        test_case.name,
                        "pipeline",
                        test_case.query_name,
                        Exception("Pipeline YAML content not available"),
                    )

                await self.client.pipelines(workspace).create(name=test_case.query_name, yaml_config=query_config)
                setup_result["pipelines"].append(test_case.query_name)

            self.logger.info(
                "Resource setup completed",
                {
                    "test_case": test_case.name,
                    "setup_result": setup_result,
                },
            )

            return setup_result

        except Exception as e:
            resource_type = "index" if test_case.index_name else "pipeline"
            resource_name = test_case.index_name or test_case.query_name or "unknown"
            raise ResourceSetupError(test_case.name, resource_type, resource_name, e) from e

    async def validate_pipeline(self, pipeline_name: str, workspace: str) -> dict[str, Any]:
        """Validate a pipeline configuration."""
        try:
            pipeline = await self.client.pipelines(workspace).get(pipeline_name=pipeline_name)
            if not pipeline.yaml_config:
                raise Exception("Pipeline YAML config not found")

            validation_result = await self.client.pipelines(workspace).validate(yaml_config=pipeline.yaml_config)

            return {
                "valid": validation_result.valid,
                "errors": validation_result.errors or [],
                "pipeline_name": pipeline_name,
            }

        except Exception as e:
            self.logger.error(
                "Pipeline validation failed",
                {
                    "pipeline_name": pipeline_name,
                    "workspace": workspace,
                    "error": str(e),
                },
            )
            return {
                "valid": False,
                "errors": [str(e)],
                "pipeline_name": pipeline_name,
            }

    async def get_updated_pipeline(self, pipeline_name: str, workspace: str) -> dict[str, Any] | None:
        """Get updated pipeline configuration after agent execution."""
        try:
            pipeline = await self.client.pipelines(workspace).get(pipeline_name=pipeline_name)
            return {
                "name": pipeline.name,
                "yaml_config": pipeline.yaml_config,
                "status": pipeline.status,
                "updated_at": pipeline.last_updated_at,
            }
        except Exception as e:
            self.logger.error(
                "Failed to get updated pipeline",
                {
                    "pipeline_name": pipeline_name,
                    "workspace": workspace,
                    "error": str(e),
                },
            )
            return None

    async def cleanup_test_resources(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Clean up resources created for a test case."""
        cleanup_result: dict[str, Any] = {"deleted_indexes": [], "deleted_pipelines": [], "errors": []}

        # Clean up pipeline
        if test_case.query_name:
            try:
                pipeline_resource = self.client.pipelines(workspace)
                await pipeline_resource.delete(pipeline_name=test_case.query_name)
                cleanup_result["deleted_pipelines"].append(test_case.query_name)
                self.logger.info(f"Deleted pipeline '{test_case.query_name}'")
            except Exception as e:
                error_msg = f"Failed to delete pipeline '{test_case.query_name}': {e}"
                cleanup_result["errors"].append(error_msg)
                self.logger.error(error_msg)

        # Clean up index
        if test_case.index_name:
            try:
                # Call delete method - assuming it exists on the resource
                index_resource = self.client.indexes(workspace)
                await index_resource.delete(index_name=test_case.index_name)

                cleanup_result["deleted_indexes"].append(test_case.index_name)
                self.logger.info(f"Deleted index '{test_case.index_name}'")

            except Exception as e:
                error_msg = f"Failed to delete index '{test_case.index_name}': {e}"
                cleanup_result["errors"].append(error_msg)
                self.logger.error(error_msg)

        if cleanup_result["errors"]:
            raise ResourceCleanupError(
                test_case.name, "multiple", "various", Exception("; ".join(cleanup_result["errors"]))
            )

        return cleanup_result

    def create_index(self, workspace: str, name: str, yaml_config: str) -> None:
        """Create an index synchronously."""
        asyncio.run(self.client.indexes(workspace).create(name=name, yaml_config=yaml_config))

    def delete_index(self, workspace: str, name: str) -> None:
        """Delete an index synchronously."""
        asyncio.run(self.client.indexes(workspace).delete(index_name=name))

    def create_pipeline(self, workspace: str, name: str, yaml_config: str) -> None:
        """Create a pipeline synchronously."""
        asyncio.run(self.client.pipelines(workspace).create(name=name, yaml_config=yaml_config))

    def delete_pipeline(self, workspace: str, name: str) -> None:
        """Delete a pipeline synchronously."""
        asyncio.run(self.client.pipelines(workspace).delete(pipeline_name=name))

    def setup_test_resources_sync(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Set up required resources for a test case synchronously."""
        return asyncio.run(self.setup_test_resources(test_case, workspace))

    def cleanup_test_resources_sync(self, test_case: TestCaseConfig, workspace: str) -> dict[str, Any]:
        """Clean up resources created for a test case synchronously."""
        return asyncio.run(self.cleanup_test_resources(test_case, workspace))

    async def setup_multiple_test_resources(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """
        Set up resources for multiple test cases with configurable concurrency.

        Args:
            test_cases: List of test case configurations
            workspace: Deepset workspace name
            concurrency: Maximum number of concurrent operations (default: 1)

        Returns:
            Dictionary containing setup results and any errors
        """
        if concurrency < 1:
            raise ValueError("Concurrency must be at least 1")

        self.logger.info(f"Setting up resources for {len(test_cases)} test cases with concurrency {concurrency}")

        results: dict[str, Any] = {
            "successful_setups": [],
            "failed_setups": [],
            "total_indexes": [],
            "total_pipelines": [],
            "errors": [],
        }

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def setup_single_with_semaphore(test_case: TestCaseConfig) -> dict[str, Any]:
            """Set up a single test case with semaphore control."""
            async with semaphore:
                try:
                    setup_result = await self.setup_test_resources(test_case, workspace)
                    return {"status": "success", "test_case": test_case.name, "result": setup_result}
                except Exception as e:
                    self.logger.error(f"Failed to setup resources for test case '{test_case.name}': {e}")
                    return {"status": "error", "test_case": test_case.name, "error": str(e)}

        # Create tasks for all test cases
        tasks = [asyncio.create_task(setup_single_with_semaphore(test_case)) for test_case in test_cases]

        # Wait for all tasks to complete
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for task_result in task_results:
            if isinstance(task_result, Exception):
                error_msg = f"Task failed with exception: {task_result}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
            elif isinstance(task_result, dict) and task_result["status"] == "success":
                results["successful_setups"].append(task_result["test_case"])
                setup_result = task_result["result"]
                results["total_indexes"].extend(setup_result.get("indexes", []))
                results["total_pipelines"].extend(setup_result.get("pipelines", []))
            elif isinstance(task_result, dict):
                results["failed_setups"].append({"test_case": task_result["test_case"], "error": task_result["error"]})
                results["errors"].append(f"Setup failed for {task_result['test_case']}: {task_result['error']}")

        self.logger.info(
            f"Batch setup completed: {len(results['successful_setups'])} successful, "
            f"{len(results['failed_setups'])} failed"
        )

        return results

    async def cleanup_multiple_test_resources(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """
        Clean up resources for multiple test cases with configurable concurrency.

        Args:
            test_cases: List of test case configurations
            workspace: Deepset workspace name
            concurrency: Maximum number of concurrent operations (default: 1)

        Returns:
            Dictionary containing cleanup results and any errors
        """
        if concurrency < 1:
            raise ValueError("Concurrency must be at least 1")

        self.logger.info(f"Cleaning up resources for {len(test_cases)} test cases with concurrency {concurrency}")

        results: dict[str, Any] = {
            "successful_cleanups": [],
            "failed_cleanups": [],
            "total_deleted_indexes": [],
            "total_deleted_pipelines": [],
            "errors": [],
        }

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def cleanup_single_with_semaphore(test_case: TestCaseConfig) -> dict[str, Any]:
            """Clean up a single test case with semaphore control."""
            async with semaphore:
                try:
                    cleanup_result = await self.cleanup_test_resources(test_case, workspace)
                    return {"status": "success", "test_case": test_case.name, "result": cleanup_result}
                except Exception as e:
                    self.logger.error(f"Failed to cleanup resources for test case '{test_case.name}': {e}")
                    return {"status": "error", "test_case": test_case.name, "error": str(e)}

        # Create tasks for all test cases
        tasks = [asyncio.create_task(cleanup_single_with_semaphore(test_case)) for test_case in test_cases]

        # Wait for all tasks to complete
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for task_result in task_results:
            if isinstance(task_result, Exception):
                error_msg = f"Task failed with exception: {task_result}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
            elif isinstance(task_result, dict) and task_result["status"] == "success":
                results["successful_cleanups"].append(task_result["test_case"])
                cleanup_result = task_result["result"]
                results["total_deleted_indexes"].extend(cleanup_result.get("deleted_indexes", []))
                results["total_deleted_pipelines"].extend(cleanup_result.get("deleted_pipelines", []))
                # Also collect any errors from individual cleanup operations
                if cleanup_result.get("errors"):
                    results["errors"].extend(cleanup_result["errors"])
            elif isinstance(task_result, dict):
                results["failed_cleanups"].append(
                    {"test_case": task_result["test_case"], "error": task_result["error"]}
                )
                results["errors"].append(f"Cleanup failed for {task_result['test_case']}: {task_result['error']}")

        self.logger.info(
            f"Batch cleanup completed: {len(results['successful_cleanups'])} successful, "
            f"{len(results['failed_cleanups'])} failed"
        )

        return results

    def setup_multiple_test_resources_sync(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Set up resources for multiple test cases synchronously."""
        return asyncio.run(self.setup_multiple_test_resources(test_cases, workspace, concurrency))

    def cleanup_multiple_test_resources_sync(
        self, test_cases: list[TestCaseConfig], workspace: str, concurrency: int = 1
    ) -> dict[str, Any]:
        """Clean up resources for multiple test cases synchronously."""
        return asyncio.run(self.cleanup_multiple_test_resources(test_cases, workspace, concurrency))


def get_deepset_resource_service(api_key: str, debug: bool = False) -> DeepsetResourceService:
    """Gets an instance of the DeepsetResourceService."""
    client = AsyncDeepsetClient(api_key=api_key)

    return DeepsetResourceService(client=client, debug=debug)
