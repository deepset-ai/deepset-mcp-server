# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.log_level import LogLevel
from deepset_mcp.api.pipeline.models import (
    DeepsetPipeline,
    PipelineList,
    PipelineLog,
    PipelineLogList,
    PipelineServiceLevel,
    PipelineValidationResult,
)
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        return PipelineResource(client=self, workspace=workspace)


def create_sample_pipeline(
    pipeline_id: str = "test-pipeline-id",
    name: str = "test-pipeline",
    status: str = "DEPLOYED",
    service_level: PipelineServiceLevel = PipelineServiceLevel.PRODUCTION,
) -> dict[str, Any]:
    """Create a sample pipeline response dictionary for testing."""
    return {
        "pipeline_id": pipeline_id,
        "name": name,
        "status": status,
        "service_level": service_level,
        "created_at": "2023-01-01T00:00:00Z",
        "last_edited_at": "2023-01-02T00:00:00Z",
        "created_by": {"user_id": "user-123", "given_name": "Test", "family_name": "User", "email": "test@example.com"},
        "last_edited_by": {
            "user_id": "user-456",
            "given_name": "Editor",
            "family_name": "User",
            "email": "editor@example.com",
        },
    }


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
            "workspace_id": "91ee7798-004d-4808-906a-1777ea262d1c",
        },
    }


@pytest.fixture
def dummy_client() -> DummyClient:
    """Return a basic DummyClient instance."""
    return DummyClient()


@pytest.fixture
def pipeline_resource(dummy_client: DummyClient) -> PipelineResource:
    """Return a PipelineResource instance with a dummy client."""
    return PipelineResource(client=dummy_client, workspace="test-workspace")


class TestPipelineResource:
    """Tests for the PipelineResource class."""

    @pytest.mark.asyncio
    async def test_list_pipelines_default_params(self) -> None:
        """Test listing pipelines with default parameters."""
        # Create sample data
        sample_pipelines = [
            create_sample_pipeline(pipeline_id="1", name="Pipeline 1"),
            create_sample_pipeline(pipeline_id="2", name="Pipeline 2"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines": {
                    "data": sample_pipelines,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Create resource and call list method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.list()

        # Verify results
        assert isinstance(result, PipelineList)
        assert len(result.data) == 2
        assert isinstance(result.data[0], DeepsetPipeline)
        assert result.data[0].id == "1"
        assert result.data[0].name == "Pipeline 1"

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines"
        assert client.requests[0]["method"] == "GET"
        assert client.requests[0]["params"] == {"page_number": 1, "limit": 10}

    @pytest.mark.asyncio
    async def test_list_pipelines_with_pagination(self) -> None:
        """Test listing pipelines with custom pagination parameters."""
        # Create sample data
        sample_pipelines = [
            create_sample_pipeline(pipeline_id="3", name="Pipeline 3"),
            create_sample_pipeline(pipeline_id="4", name="Pipeline 4"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipelines": {
                    "data": sample_pipelines,
                    "has_more": False,
                    "total": 10,
                }
            }
        )

        # Create resource and call list method with pagination
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.list(page_number=2, limit=5)

        # Verify results
        assert isinstance(result, PipelineList)
        assert len(result.data) == 2
        assert result.data[0].id == "3"
        assert result.data[1].id == "4"

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines"
        assert client.requests[0]["params"] == {"page_number": 2, "limit": 5}

    @pytest.mark.asyncio
    async def test_list_pipelines_empty_result(self) -> None:
        """Test listing pipelines when there are no pipelines."""
        # Create client with empty response
        client = DummyClient(responses={"test-workspace/pipelines": {"data": [], "has_more": False, "total": 0}})

        # Create resource and call list method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.list()

        # Verify empty results
        assert isinstance(result, PipelineList)
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_list_pipelines_error(self) -> None:
        """Test handling of errors when listing pipelines."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines": ValueError("API Error")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="API Error"):
            await resource.list()

    @pytest.mark.asyncio
    async def test_list_pipelines_with_zero_limit(self) -> None:
        """Test listing pipelines with a limit of zero (edge case)."""
        # Create client
        client = DummyClient(responses={"test-workspace/pipelines": {"data": [], "has_more": False, "total": 10}})

        # Create resource and call list method with limit=0
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.list(limit=0)

        # Verify empty results
        assert isinstance(result, PipelineList)
        assert len(result.data) == 0

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines"
        assert client.requests[0]["params"] == {"page_number": 1, "limit": 0}

    @pytest.mark.asyncio
    async def test_get_pipeline_with_yaml(self) -> None:
        """Test getting a pipeline with YAML config."""
        # Create sample pipeline data
        pipeline_name = "test-pipeline"
        sample_pipeline = create_sample_pipeline(name=pipeline_name)
        yaml_config = "version: '1.0'\npipeline:\n  name: test"

        # Create client with predefined responses
        client = DummyClient(
            responses={
                f"test-workspace/pipelines/{pipeline_name}": sample_pipeline,
                f"test-workspace/pipelines/{pipeline_name}/yaml": {"query_yaml": yaml_config},
            }
        )

        # Create resource and call get method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get(pipeline_name=pipeline_name)

        # Verify results
        assert isinstance(result, DeepsetPipeline)
        assert result.id == "test-pipeline-id"
        assert result.name == pipeline_name
        assert result.yaml_config == yaml_config

        # Verify requests
        assert len(client.requests) == 2
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{pipeline_name}"
        assert client.requests[1]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{pipeline_name}/yaml"

    @pytest.mark.asyncio
    async def test_get_pipeline_without_yaml(self) -> None:
        """Test getting a pipeline without YAML config."""
        # Create sample pipeline data
        pipeline_name = "test-pipeline"
        sample_pipeline = create_sample_pipeline(name=pipeline_name)

        # Create client with predefined response
        client = DummyClient(responses={f"test-workspace/pipelines/{pipeline_name}": sample_pipeline})

        # Create resource and call get method with include_yaml=False
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get(pipeline_name=pipeline_name, include_yaml=False)

        # Verify results
        assert isinstance(result, DeepsetPipeline)
        assert result.id == "test-pipeline-id"
        assert result.name == pipeline_name
        assert result.yaml_config is None

        # Verify only one request was made (no YAML request)
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{pipeline_name}"

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(self) -> None:
        """Test getting a non-existent pipeline."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines/nonexistent": ValueError("Pipeline not found")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Pipeline not found"):
            await resource.get(pipeline_name="nonexistent")

    @pytest.mark.asyncio
    async def test_get_pipeline_yaml_error(self) -> None:
        """Test error handling when getting YAML config."""
        # Create sample pipeline data
        pipeline_name = "test-pipeline"
        sample_pipeline = create_sample_pipeline(name=pipeline_name)

        # Create client with successful pipeline response but error for YAML
        client = DummyClient(
            responses={
                f"test-workspace/pipelines/{pipeline_name}": sample_pipeline,
                f"test-workspace/pipelines/{pipeline_name}/yaml": ValueError("YAML not available"),
            }
        )

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="YAML not available"):
            await resource.get(pipeline_name=pipeline_name)

    @pytest.mark.asyncio
    async def test_get_pipeline_with_special_characters(self) -> None:
        """Test getting a pipeline with a name containing special characters."""
        # Create sample pipeline data with special characters in name
        pipeline_name = "test/pipeline with spaces"
        sample_pipeline = create_sample_pipeline(name=pipeline_name)

        # Create client with predefined response
        client = DummyClient(responses={f"test-workspace/pipelines/{pipeline_name}": sample_pipeline})

        # Create resource and call get method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.get(pipeline_name=pipeline_name, include_yaml=False)

        # Verify results
        assert isinstance(result, DeepsetPipeline)
        assert result.name == pipeline_name

        # Verify request
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{pipeline_name}"

    @pytest.mark.asyncio
    async def test_create_pipeline(self) -> None:
        """Test creating a new pipeline."""
        # Setup test data
        pipeline_name = "new-pipeline"
        yaml_config = "version: '1.0'\npipeline:\n  name: new-test"

        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipelines": {"status": "success"}})

        # Create resource and call create method
        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.create(name=pipeline_name, yaml_config=yaml_config)

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0]["data"] == {"name": pipeline_name, "query_yaml": yaml_config}

    @pytest.mark.asyncio
    async def test_create_pipeline_with_empty_yaml(self) -> None:
        """Test creating a pipeline with empty YAML config."""
        # Setup test data
        pipeline_name = "empty-yaml-pipeline"
        yaml_config = ""

        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipelines": {"status": "success"}})

        # Create resource and call create method
        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.create(name=pipeline_name, yaml_config=yaml_config)

        # Verify request
        assert client.requests[0]["data"] == {"name": pipeline_name, "query_yaml": yaml_config}

    @pytest.mark.asyncio
    async def test_create_pipeline_error(self) -> None:
        """Test error handling when creating a pipeline."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines": ValueError("Pipeline name already exists")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Pipeline name already exists"):
            await resource.create(name="duplicate", yaml_config="version: '1.0'")

    @pytest.mark.asyncio
    async def test_update_pipeline_name_only(self) -> None:
        """Test updating only a pipeline's name."""
        # Setup test data
        old_name = "old-pipeline"
        new_name = "renamed-pipeline"

        # Create client with successful response
        client = DummyClient(responses={f"test-workspace/pipelines/{old_name}": {"status": "success"}})

        # Create resource and call update method
        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.update(pipeline_name=old_name, updated_pipeline_name=new_name)

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{old_name}"
        assert client.requests[0]["method"] == "PATCH"
        assert client.requests[0]["data"] == {"name": new_name}

    @pytest.mark.asyncio
    async def test_update_pipeline_yaml_only(self) -> None:
        """Test updating only a pipeline's YAML config."""
        # Setup test data
        pipeline_name = "test-pipeline"
        yaml_config = "version: '1.0'\npipeline:\n  name: updated-test"

        # Create client with successful response
        client = DummyClient(responses={f"test-workspace/pipelines/{pipeline_name}/yaml": {"status": "success"}})

        # Create resource and call update method
        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.update(pipeline_name=pipeline_name, yaml_config=yaml_config)

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{pipeline_name}/yaml"
        assert client.requests[0]["method"] == "PUT"
        assert client.requests[0]["data"] == {"query_yaml": yaml_config}

    @pytest.mark.asyncio
    async def test_update_pipeline_name_and_yaml(self) -> None:
        """Test updating both a pipeline's name and YAML config."""
        # Setup test data
        old_name = "old-pipeline"
        new_name = "renamed-pipeline"
        yaml_config = "version: '1.0'\npipeline:\n  name: updated-test"

        # Create client with successful responses
        client = DummyClient(
            responses={
                f"test-workspace/pipelines/{old_name}": {"status": "success"},
                f"test-workspace/pipelines/{new_name}/yaml": {"status": "success"},
            }
        )

        # Create resource and call update method
        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.update(pipeline_name=old_name, updated_pipeline_name=new_name, yaml_config=yaml_config)

        # Verify requests
        assert len(client.requests) == 2

        # First request should update the name
        assert client.requests[0]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{old_name}"
        assert client.requests[0]["method"] == "PATCH"
        assert client.requests[0]["data"] == {"name": new_name}

        # Second request should update the YAML using the new name
        assert client.requests[1]["endpoint"] == f"v1/workspaces/test-workspace/pipelines/{new_name}/yaml"
        assert client.requests[1]["method"] == "PUT"
        assert client.requests[1]["data"] == {"query_yaml": yaml_config}

    @pytest.mark.asyncio
    async def test_update_pipeline_no_changes(self) -> None:
        """Test updating a pipeline with no changes (edge case)."""
        # Setup test data
        pipeline_name = "test-pipeline"

        # Create client
        client = DummyClient()

        # Create resource and call update method with no changes
        resource = PipelineResource(client=client, workspace="test-workspace")

        with pytest.raises(ValueError):
            await resource.update(pipeline_name=pipeline_name)

    @pytest.mark.asyncio
    async def test_update_pipeline_name_error(self) -> None:
        """Test error handling when updating a pipeline's name."""
        # Create client that raises an exception
        client = DummyClient(
            responses={"test-workspace/pipelines/old-pipeline": ValueError("Pipeline name already exists")}
        )

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Pipeline name already exists"):
            await resource.update(pipeline_name="old-pipeline", updated_pipeline_name="duplicate")

    @pytest.mark.asyncio
    async def test_update_pipeline_yaml_error(self) -> None:
        """Test error handling when updating a pipeline's YAML config."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/yaml": ValueError("Invalid YAML")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Invalid YAML"):
            await resource.update(pipeline_name="test-pipeline", yaml_config="invalid: ")

    @pytest.mark.asyncio
    async def test_update_pipeline_name_then_yaml_error(self) -> None:
        """Test error handling when name update succeeds but YAML update fails."""
        # Create client with successful name update but error for YAML
        client = DummyClient(
            responses={
                "test-workspace/pipelines/old-pipeline": {"status": "success"},
                "test-workspace/pipelines/new-pipeline/yaml": ValueError("Invalid YAML"),
            }
        )

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Invalid YAML"):
            await resource.update(
                pipeline_name="old-pipeline", updated_pipeline_name="new-pipeline", yaml_config="invalid: "
            )

        # Verify both requests were attempted
        assert len(client.requests) == 2
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/old-pipeline"
        assert client.requests[1]["endpoint"] == "v1/workspaces/test-workspace/pipelines/new-pipeline/yaml"

    @pytest.mark.asyncio
    async def test_validation_success(self) -> None:
        """Test successful validation of valid YAML config."""
        # Create a valid YAML config
        valid_yaml = """version: '1.0'
    pipeline:
      name: test
      nodes:
        - name: example
          type: test"""

        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipeline_validations": {"status": "success"}})

        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.validate(yaml_config=valid_yaml)

        # Check the result
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipeline_validations"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0]["data"] == {"query_yaml": valid_yaml}

    @pytest.mark.asyncio
    async def test_validation_with_errors(self) -> None:
        """Test validation with config errors."""
        # Create a YAML config with errors
        invalid_yaml = """version: '1.0'
    pipeline:
      name: test
      nodes:
        - name: missing_type"""

        # Create a response with validation errors
        validation_errors = {
            "details": [
                {"code": "required_field_missing", "message": "Field 'type' is required for node 'missing_type'"}
            ]
        }

        # Create mock client with 400 response containing validation errors
        client = DummyClient()

        # Manually prepare the TransportResponse for validation errors
        transport_response = TransportResponse(text="", status_code=400, json=validation_errors)

        # Set the custom response
        client.responses = {"test-workspace/pipeline_validations": transport_response}

        # Run the validation
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.validate(yaml_config=invalid_yaml)

        # Check the result
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "required_field_missing"
        assert result.errors[0].message == "Field 'type' is required for node 'missing_type'"

    @pytest.mark.asyncio
    async def test_validation_with_invalid_yaml(self) -> None:
        """Test validation with syntactically invalid YAML."""
        # Create an invalid YAML string
        invalid_yaml = "invalid: yaml: :"

        # Create response for 422 invalid YAML error
        invalid_yaml_response = TransportResponse(text="", status_code=422, json={"detail": "Invalid YAML syntax"})

        client = DummyClient(responses={"test-workspace/pipeline_validations": invalid_yaml_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.validate(yaml_config=invalid_yaml)

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "YAML_ERROR"

    @pytest.mark.asyncio
    async def test_validation_with_empty_yaml(self) -> None:
        """Test validation with empty YAML string."""
        empty_yaml = ""

        # Create response for empty YAML error
        empty_yaml_response = TransportResponse(text="", status_code=422, json={"detail": "YAML cannot be empty"})

        client = DummyClient(responses={"test-workspace/pipeline_validations": empty_yaml_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.validate(yaml_config=empty_yaml)

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "YAML_ERROR"

    @pytest.mark.asyncio
    async def test_validation_with_unknown_error(self) -> None:
        """Test validation with unknown error response."""
        yaml_config = "version: '1.0'"

        # Create response for unknown error
        unknown_error_response: TransportResponse[None] = TransportResponse(text="", status_code=500, json=None)

        client = DummyClient(responses={"test-workspace/pipeline_validations": unknown_error_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        with pytest.raises(UnexpectedAPIError):
            await resource.validate(yaml_config=yaml_config)

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
        result = await resource.get_logs(pipeline_name="test-pipeline", level=LogLevel.ERROR)

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
        result = await resource.get_logs(pipeline_name="test-pipeline", level=LogLevel.WARNING)

        # Verify results
        assert len(result.data) == 1
        assert result.data[0].level == "warning"

        # Verify request with warning level filter
        assert client.requests[0]["params"] == {
            "limit": 30,
            "filter": "level eq 'warning' and origin eq 'querypipeline'",
        }

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
        client.responses = {
            "test-workspace/pipelines/test-pipeline/logs": TransportResponse(text="", status_code=200, json=None)
        }

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

    @pytest.mark.asyncio
    async def test_deploy_pipeline_success(self) -> None:
        """Test successful pipeline deployment."""
        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/deploy": {"status": "success"}})

        # Create resource and call deploy method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.deploy(pipeline_name="test-pipeline")

        # Verify results
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/test-pipeline/deploy"
        assert client.requests[0]["method"] == "POST"

    @pytest.mark.asyncio
    async def test_deploy_pipeline_with_validation_errors(self) -> None:
        """Test deployment with validation errors (422)."""
        # Create a response with validation errors
        validation_errors = {
            "details": [
                {"code": "invalid_component", "message": "Component 'invalid_reader' is not available"},
                {"code": "missing_field", "message": "Required field 'index' is missing"},
            ]
        }

        # Create mock client with 422 response containing validation errors
        client = DummyClient()
        transport_response = TransportResponse(text="", status_code=422, json=validation_errors)
        client.responses = {"test-workspace/pipelines/test-pipeline/deploy": transport_response}

        # Run the deployment
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.deploy(pipeline_name="test-pipeline")

        # Check the result
        assert isinstance(result, PipelineValidationResult)
        assert result.valid is False
        assert len(result.errors) == 2
        assert result.errors[0].code == "invalid_component"
        assert result.errors[0].message == "Component 'invalid_reader' is not available"
        assert result.errors[1].code == "missing_field"
        assert result.errors[1].message == "Required field 'index' is missing"

    @pytest.mark.asyncio
    async def test_deploy_pipeline_with_400_error(self) -> None:
        """Test deployment with 400 error."""
        # Create response for 400 error
        error_response: TransportResponse[None] = TransportResponse(text="Bad request", status_code=400, json=None)

        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/deploy": error_response})

        # Run the deployment
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.deploy(pipeline_name="test-pipeline")

        # Check the result
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "Bad request"

    @pytest.mark.asyncio
    async def test_deploy_pipeline_with_404_error(self) -> None:
        """Test deployment with 404 error (pipeline not found)."""
        # Create response for 404 error
        error_response: TransportResponse[None] = TransportResponse(
            text="Pipeline not found", status_code=404, json=None
        )

        client = DummyClient(responses={"test-workspace/pipelines/nonexistent-pipeline/deploy": error_response})

        # Run the deployment
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.deploy(pipeline_name="nonexistent-pipeline")

        # Check the result
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "Pipeline not found"

    @pytest.mark.asyncio
    async def test_deploy_pipeline_with_500_error(self) -> None:
        """Test deployment with 500 error (unexpected error)."""
        # Create response for 500 error
        error_response: TransportResponse[None] = TransportResponse(
            text="Internal server error", status_code=500, json=None
        )

        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/deploy": error_response})

        # Run the deployment and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        with pytest.raises(UnexpectedAPIError) as exc_info:
            await resource.deploy(pipeline_name="test-pipeline")

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_deploy_pipeline_with_empty_error_text(self) -> None:
        """Test deployment with error response but empty text."""
        # Create response for 400 error with empty text
        error_response: TransportResponse[None] = TransportResponse(text="", status_code=400, json=None)

        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline/deploy": error_response})

        # Run the deployment
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.deploy(pipeline_name="test-pipeline")

        # Check the result
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "DEPLOYMENT_ERROR"
        assert result.errors[0].message == "HTTP 400 error"

    @pytest.mark.asyncio
    async def test_delete_pipeline_success(self) -> None:
        """Test successfully deleting a pipeline."""
        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline": {"status": "success"}})

        # Create resource and call delete method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.delete(pipeline_name="test-pipeline")

        # Verify response
        assert result.success is True
        assert result.message == "Pipeline deleted successfully."

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/test-pipeline"
        assert client.requests[0]["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_delete_pipeline_not_found(self) -> None:
        """Test deleting a non-existent pipeline."""
        # Create client that raises an exception for 404
        client = DummyClient(responses={"test-workspace/pipelines/nonexistent": ValueError("Pipeline not found")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="Pipeline not found"):
            await resource.delete(pipeline_name="nonexistent")

    @pytest.mark.asyncio
    async def test_delete_pipeline_error(self) -> None:
        """Test error handling when deleting a pipeline."""
        # Create client that raises an exception
        client = DummyClient(responses={"test-workspace/pipelines/test-pipeline": ValueError("API Error")})

        # Create resource
        resource = PipelineResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ValueError, match="API Error"):
            await resource.delete(pipeline_name="test-pipeline")

    @pytest.mark.asyncio
    async def test_delete_pipeline_with_special_characters(self) -> None:
        """Test deleting a pipeline with special characters in name."""
        # Create client with successful response
        client = DummyClient(responses={"test-workspace/pipelines/pipeline with spaces": {"status": "success"}})

        # Create resource and call delete method
        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.delete(pipeline_name="pipeline with spaces")

        # Verify response
        assert result.success is True
        assert result.message == "Pipeline deleted successfully."

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipelines/pipeline with spaces"
