"""Tests for the pipeline logs functionality in pipeline tools."""

import pytest

from deepset_mcp.api.pipeline.models import LogLevel, PipelineLog, PipelineLogList
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.protocols import PipelineResourceProtocol
from deepset_mcp.tools.pipeline import get_pipeline_logs
from test.unit.conftest import BaseFakeClient


class FakeClient(BaseFakeClient):
    """Fake client for testing pipeline logs functionality."""

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        return PipelineResource(client=self, workspace=workspace)


def create_sample_log(
    log_id: str = "test-log-id",
    message: str = "Test log message",
    level: str = "info",
    origin: str = "querypipeline",
) -> dict[str, any]:
    """Create a sample log entry for testing."""
    return {
        "log_id": log_id,
        "message": message,
        "logged_at": "2023-01-01T12:00:00Z",
        "level": level,
        "origin": origin,
        "exceptions": None,
        "extra_fields": {},
    }


class TestPipelineLogsTools:
    """Tests for pipeline logs tools."""

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_success(self) -> None:
        """Test successful retrieval of pipeline logs."""
        # Create sample logs
        sample_logs = [
            create_sample_log(log_id="log1", message="First log entry", level="info"),
            create_sample_log(log_id="log2", message="Second log entry", level="warning"),
        ]

        # Create client with predefined response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Call the tool function
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
        )

        # Verify the result
        assert "# Logs for pipeline 'test-pipeline'" in result
        assert "Total logs returned: 2" in result
        assert "More logs available: False" in result
        assert "[INFO] 2023-01-01T12:00:00+00:00: First log entry" in result
        assert "[WARNING] 2023-01-01T12:00:00+00:00: Second log entry" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_with_level_filter(self) -> None:
        """Test retrieval of pipeline logs with level filter."""
        # Create sample error logs
        sample_logs = [
            create_sample_log(log_id="error1", message="First error", level="error"),
            create_sample_log(log_id="error2", message="Second error", level="error"),
        ]

        # Create client with predefined response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Call the tool function with error level filter
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
            level=LogLevel.ERROR,
        )

        # Verify the result
        assert "# Logs for pipeline 'test-pipeline'" in result
        assert "Filtered by level: error" in result
        assert "[ERROR] 2023-01-01T12:00:00+00:00: First error" in result
        assert "[ERROR] 2023-01-01T12:00:00+00:00: Second error" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_with_exceptions(self) -> None:
        """Test retrieval of logs that contain exceptions."""
        # Create sample logs with exceptions
        sample_logs = [
            {
                "log_id": "error-log",
                "message": "Pipeline failed",
                "logged_at": "2023-01-01T12:00:00Z",
                "level": "error",
                "origin": "querypipeline",
                "exceptions": "ValueError: Invalid input parameter",
                "extra_fields": {},
            }
        ]

        # Create client with predefined response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Call the tool function
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
        )

        # Verify the result includes exception information
        assert "[ERROR] 2023-01-01T12:00:00+00:00: Pipeline failed" in result
        assert "Exception: ValueError: Invalid input parameter" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_no_logs_found(self) -> None:
        """Test retrieval when no logs are found."""
        # Create client with empty response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": [],
                    "has_more": False,
                    "total": 0,
                }
            }
        )

        # Call the tool function
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
        )

        # Verify the result
        assert "No logs found for pipeline 'test-pipeline'" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_no_logs_found_with_level(self) -> None:
        """Test retrieval when no logs are found with level filter."""
        # Create client with empty response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": [],
                    "has_more": False,
                    "total": 0,
                }
            }
        )

        # Call the tool function with level filter
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
            level=LogLevel.ERROR,
        )

        # Verify the result
        assert "No logs found for pipeline 'test-pipeline' with level 'error'" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_pipeline_not_found(self) -> None:
        """Test handling when pipeline doesn't exist."""
        from deepset_mcp.api.exceptions import ResourceNotFoundError

        # Create client that raises ResourceNotFoundError
        client = FakeClient(
            responses={
                "test-workspace/pipelines/nonexistent-pipeline/logs": ResourceNotFoundError(
                    status_code=404, message="Pipeline not found", detail=None
                )
            }
        )

        # Call the tool function
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="nonexistent-pipeline",
        )

        # Verify the result
        assert "There is no pipeline named 'nonexistent-pipeline'" in result
        assert "Did you mean to create it?" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_api_error(self) -> None:
        """Test handling of unexpected API errors."""
        from deepset_mcp.api.exceptions import UnexpectedAPIError

        # Create client that raises UnexpectedAPIError
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": UnexpectedAPIError(
                    status_code=500, message="Internal server error", detail=None
                )
            }
        )

        # Call the tool function
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
        )

        # Verify the result
        assert "Failed to retrieve logs for pipeline 'test-pipeline'" in result
        assert "Internal server error" in result

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_with_custom_limit(self) -> None:
        """Test retrieval with custom limit parameter."""
        # Create sample logs
        sample_logs = [create_sample_log(log_id=f"log{i}", message=f"Log entry {i}") for i in range(5)]

        # Create client with predefined response
        client = FakeClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": True,
                    "total": 10,
                }
            }
        )

        # Call the tool function with custom limit
        result = await get_pipeline_logs(
            client=client,
            workspace="test-workspace",
            pipeline_name="test-pipeline",
            limit=5,
        )

        # Verify the result
        assert "Total logs returned: 5 (showing up to 5)" in result
        assert "More logs available: True" in result

        # Verify request was made with correct limit
        assert len(client.requests) == 1
        assert client.requests[0]["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_pipeline_logs_all_enum_levels(self) -> None:
        """Test that all LogLevel enum values work correctly."""
        for level in LogLevel:
            # Create sample log with the specific level
            sample_logs = [
                create_sample_log(log_id=f"{level.value}-log", message=f"{level.value} message", level=level.value)
            ]

            # Create client with predefined response
            client = FakeClient(
                responses={
                    "test-workspace/pipelines/test-pipeline/logs": {
                        "data": sample_logs,
                        "has_more": False,
                        "total": 1,
                    }
                }
            )

            # Call the tool function with the specific level
            result = await get_pipeline_logs(
                client=client,
                workspace="test-workspace",
                pipeline_name="test-pipeline",
                level=level,
            )

            # Verify the result
            assert f"Filtered by level: {level.value}" in result
            assert f"[{level.value.upper()}]" in result
            assert f"{level.value} message" in result
