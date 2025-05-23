import pytest
from typing import Any

from deepset_mcp.api.pipeline.log_models import PipelineLog, PipelineLogList
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineServiceLevel
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.protocols import PipelineResourceProtocol
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        return PipelineResource(client=self, workspace=workspace)


def create_sample_log(
    log_id: str = "UHG0_JYBbpf1V-YKI8YQ",
    message: str = "Will use search history type: SNS",
    level: str = "info",
    origin: str = "querypipeline",
) -> dict[str, Any]:
    """Create a sample log entry for testing."""
    return {
        "log_id": log_id,
        "message": message,
        "logged_at": "2025-05-23T10:33:04.157182Z",
        "level": level,
        "origin": origin,
        "exceptions": None,
        "extra_fields": {
            "_logger": "<_FixedFindCallerLogger dc_query_api.search_history_publisher (INFO)>",
            "_name": "info",
            "dd.env": "prod",
            "dd.service": "dc-pipeline-query",
            "dd.span_id": "3571883701824836030",
            "dd.trace_id": "17110374009324833748",
            "dd.version": "",
            "organization_id": "4aa28dd0-f68b-4416-9a4c-6928cdadc02a",
            "organization_name": "agents-template",
            "pipeline_id": "30b45de7-7336-4c90-8750-a6f0f3dad6c8",
            "token_origin": "API",
            "user_id": "debd1c5b-8c41-434e-99d1-94443e402c10",
            "workspace_id": "91ee7798-004d-4808-906a-1777ea262d1c"
        }
    }


def create_sample_pipeline() -> DeepsetPipeline:
    """Create a sample pipeline for testing."""
    return DeepsetPipeline(
        id="test-pipeline-id",
        name="test-pipeline",
        status="DEPLOYED",
        service_level=PipelineServiceLevel.PRODUCTION,
        created_at="2023-01-01T00:00:00Z",
        last_updated_at="2023-01-02T00:00:00Z",
        created_by={"user_id": "user-123", "given_name": "Test", "family_name": "User", "email": "test@example.com"},
        last_updated_by={"user_id": "user-456", "given_name": "Editor", "family_name": "User", "email": "editor@example.com"},
    )


class TestPipelineLogsResource:
    """Tests for the get_logs method on PipelineResource."""

    @pytest.mark.asyncio
    async def test_get_logs_default_params(self) -> None:
        """Test getting logs with default parameters."""
        # Create sample logs
        sample_logs = [
            create_sample_log(log_id="log1", message="First log entry"),
            create_sample_log(log_id="log2", message="Second log entry"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Create resource and call get_logs method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline")

        # Verify results
        assert isinstance(result, PipelineLogList)
        assert len(result.data) == 2
        assert isinstance(result.data[0], PipelineLog)
        assert result.data[0].log_id == "log1"
        assert result.data[0].message == "First log entry"
        assert result.data[0].level == "info"
        assert result.data[0].origin == "querypipeline"
        assert result.has_more is False
        assert result.total == 2

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/test-pipeline/logs"
        assert client.requests[0]["method"] == "GET"
        assert client.requests[0]["params"] == {"limit": 30, "filter": "origin eq 'querypipeline'"}

    @pytest.mark.asyncio
    async def test_get_logs_with_limit(self) -> None:
        """Test getting logs with custom limit."""
        # Create sample logs
        sample_logs = [create_sample_log(log_id=f"log{i}", message=f"Log entry {i}") for i in range(10)]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": True,
                    "total": 100,
                }
            }
        )

        # Create resource and call get_logs method with custom limit
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline", limit=10)

        # Verify results
        assert len(result.data) == 10
        assert result.has_more is True
        assert result.total == 100

        # Verify request
        assert client.requests[0]["params"] == {"limit": 10, "filter": "origin eq 'querypipeline'"}

    @pytest.mark.asyncio
    async def test_get_logs_with_level_filter(self) -> None:
        """Test getting logs with level filter."""
        # Create sample error logs
        sample_logs = [
            create_sample_log(log_id="error1", message="First error", level="error"),
            create_sample_log(log_id="error2", message="Second error", level="error"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Create resource and call get_logs method with level filter
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline", level="error")

        # Verify results
        assert len(result.data) == 2
        assert all(log.level == "error" for log in result.data)

        # Verify request with level filter
        assert client.requests[0]["params"] == {"limit": 30, "filter": "level eq 'error' and origin eq 'querypipeline'"}

    @pytest.mark.asyncio
    async def test_get_logs_with_warning_level(self) -> None:
        """Test getting logs with warning level filter."""
        # Create sample warning logs
        sample_logs = [
            create_sample_log(log_id="warn1", message="First warning", level="warning"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Create resource and call get_logs method with warning level
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline", level="warning")

        # Verify results
        assert len(result.data) == 1
        assert result.data[0].level == "warning"

        # Verify request with warning level filter
        assert client.requests[0]["params"] == {"limit": 30, "filter": "level eq 'warning' and origin eq 'querypipeline'"}

    @pytest.mark.asyncio
    async def test_get_logs_empty_result(self) -> None:
        """Test getting logs when there are no logs."""
        # Create client with empty response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": [],
                    "has_more": False,
                    "total": 0,
                }
            }
        )

        # Create resource and call get_logs method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline")

        # Verify empty results
        assert len(result.data) == 0
        assert result.has_more is False
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_logs_with_null_response(self) -> None:
        """Test getting logs when response is null."""
        # Create client with null response
        client = DummyClient()
        client.responses = {"test-workspace/pipelines/test-pipeline/logs": TransportResponse(text="", status_code=200, json=None)}

        # Create resource and call get_logs method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline")

        # Verify empty results
        assert len(result.data) == 0
        assert result.has_more is False
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_logs_error(self) -> None:
        """Test handling of errors when getting logs."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/logs": ValueError("API Error")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="API Error"):
            await resource.get_logs(pipeline_name="test-pipeline")

    @pytest.mark.asyncio
    async def test_get_logs_with_edge_case_limit(self) -> None:
        """Test getting logs with edge case limits."""
        # Create client with empty response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": [],
                    "has_more": False,
                    "total": 0,
                }
            }
        )

        # Create resource and call get_logs method with limit=0
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline", limit=0)

        # Verify results
        assert len(result.data) == 0

        # Verify request
        assert client.requests[0]["params"] == {"limit": 0, "filter": "origin eq 'querypipeline'"}

    @pytest.mark.asyncio
    async def test_get_logs_with_special_characters_in_pipeline_name(self) -> None:
        """Test getting logs for a pipeline with special characters in name."""
        # Create sample logs
        sample_logs = [create_sample_log()]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/pipeline with spaces/logs": {
                    "data": sample_logs,
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Create resource and call get_logs method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="pipeline with spaces")

        # Verify results
        assert len(result.data) == 1

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/pipeline with spaces/logs"

    @pytest.mark.asyncio
    async def test_get_logs_preserves_extra_fields(self) -> None:
        """Test that extra fields in logs are preserved."""
        # Create sample log with extra fields
        sample_log = create_sample_log()
        sample_log["extra_fields"]["custom_field"] = "custom_value"

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines/test-pipeline/logs": {
                    "data": [sample_log],
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Create resource and call get_logs method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get_logs(pipeline_name="test-pipeline")

        # Verify extra fields are preserved
        assert "custom_field" in result.data[0].extra_fields
        assert result.data[0].extra_fields["custom_field"] == "custom_value"
