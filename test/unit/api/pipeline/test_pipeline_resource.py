from typing import Any

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineServiceLevel, PipelineValidationResult
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.pipeline.handle import PipelineHandle
from deepset_mcp.api.protocols import PipelineResourceProtocol
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
        assert len(result) == 2
        assert isinstance(result[0], PipelineHandle)
        assert result[0].id == "1"
        assert result[0].name == "Pipeline 1"
        assert isinstance(result[0].pipeline, DeepsetPipeline)

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
        assert len(result) == 2
        assert result[0].id == "3"
        assert result[1].id == "4"

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
        assert len(result) == 0

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
        assert len(result) == 0

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
        assert isinstance(result, PipelineHandle)
        assert result.id == "test-pipeline-id"
        assert result.name == pipeline_name
        assert result.yaml_config == yaml_config
        assert isinstance(result.pipeline, DeepsetPipeline)

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
