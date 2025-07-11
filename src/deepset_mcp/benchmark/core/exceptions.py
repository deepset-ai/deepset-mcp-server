"""Benchmark-specific exceptions for better error handling and debugging."""

from typing import Any


class BenchmarkException(Exception):
    """Base exception for benchmark operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        """
        Initialize the exception with message and optional context.

        Args:
            message: Human-readable error message
            context: Additional context information for debugging
        """
        super().__init__(message)
        self.context = context or {}


class TestCaseNotFoundError(BenchmarkException):
    """Test case file not found or invalid."""

    def __init__(self, test_case_name: str, search_path: str | None = None):
        """Initialize TestCaseNotFoundError."""
        message = f"Test case '{test_case_name}' not found"
        if search_path:
            message += f" in path: {search_path}"

        context = {
            "test_case_name": test_case_name,
            "search_path": search_path,
        }
        super().__init__(message, context)


class AgentExecutionError(BenchmarkException):
    """Agent execution failed during benchmark run."""

    def __init__(self, test_case_name: str, agent_name: str, original_error: Exception):
        """Initialize AgentExecutionError."""
        message = f"Agent '{agent_name}' failed on test case '{test_case_name}': {original_error}"
        context = {
            "test_case_name": test_case_name,
            "agent_name": agent_name,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
        }
        super().__init__(message, context)


class ResourceSetupError(BenchmarkException):
    """Failed to set up required resources (pipelines, indexes) for test case."""

    def __init__(self, test_case_name: str, resource_type: str, resource_name: str, original_error: Exception):
        """Initialize ResourceSetupError."""
        message = (
            f"Failed to set up {resource_type} '{resource_name}' for test case '{test_case_name}': {original_error}"
        )
        context = {
            "test_case_name": test_case_name,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
        }
        super().__init__(message, context)


class ResourceCleanupError(BenchmarkException):
    """Failed to clean up resources after test case execution."""

    def __init__(self, test_case_name: str, resource_type: str, resource_name: str, original_error: Exception):
        """Initialize ResourceCleanupError."""
        message = (
            f"Failed to clean up {resource_type} '{resource_name}' for test case '{test_case_name}': {original_error}"
        )
        context = {
            "test_case_name": test_case_name,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
        }
        super().__init__(message, context)
