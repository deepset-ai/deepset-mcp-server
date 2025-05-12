import pytest

from deepset_mcp.api.pipeline.models import PipelineValidationResult, ValidationError
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.pipeline.test_pipeline_resource import DummyClient


class TestPipelineValidation:
    """Tests for the pipeline validation functionality."""

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
        client = DummyClient(
            responses={
                "test-workspace/pipeline_validations": {
                    "status": "success"
                }
            }
        )

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
        assert client.requests[0]["data"] == {
            "deepset_cloud_version": "v2",
            "query_yaml": valid_yaml
        }

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
            "errors": [
                {"code": "required_field_missing", "message": "Field 'type' is required for node 'missing_type'"}
            ]
        }

        # Create mock client with 400 response containing validation errors
        client = DummyClient()

        # Manually prepare the TransportResponse for validation errors
        transport_response = TransportResponse(
            text="",
            status_code=400,
            json=validation_errors
        )

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
        invalid_yaml_response = TransportResponse(
            text="",
            status_code=422,
            json={"detail": "Invalid YAML syntax"}
        )

        client = DummyClient(responses={"test-workspace/pipeline_validations": invalid_yaml_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        with pytest.raises(ValueError, match="Pipeline validation failed: Invalid YAML syntax"):
            await resource.validate(yaml_config=invalid_yaml)

    @pytest.mark.asyncio
    async def test_validation_with_empty_yaml(self) -> None:
        """Test validation with empty YAML string."""
        empty_yaml = ""

        # Create response for empty YAML error
        empty_yaml_response = TransportResponse(
            text="",
            status_code=422,
            json={"detail": "YAML cannot be empty"}
        )

        client = DummyClient(responses={"test-workspace/pipeline_validations": empty_yaml_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        with pytest.raises(ValueError, match="Pipeline validation failed: YAML cannot be empty"):
            await resource.validate(yaml_config=empty_yaml)

    @pytest.mark.asyncio
    async def test_validation_with_unknown_error(self) -> None:
        """Test validation with unknown error response."""
        yaml_config = "version: '1.0'"

        # Create response for unknown error
        unknown_error_response = TransportResponse(
            text="",
            status_code=500,
            json=None
        )

        client = DummyClient(responses={"test-workspace/pipeline_validations": unknown_error_response})

        # Run the validation and expect an exception
        resource = PipelineResource(client=client, workspace="test-workspace")
        with pytest.raises(ValueError, match="Pipeline validation failed with status 500"):
            await resource.validate(yaml_config=yaml_config)
