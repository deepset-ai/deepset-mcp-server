from typing import Any

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.protocols import PipelineTemplateResourceProtocol
from test.unit.conftest import BaseFakeClient


def create_sample_template(
    name: str = "test-template",
    author: str = "deepset-ai",
    description: str = "A test template",
    template_id: str = "3fa85f64-5717-4562-b3fc-2c963f66afa6",
) -> dict[str, Any]:
    """Create a sample pipeline template response dictionary for testing."""
    return {
        "name": name,
        "pipeline_template_id": template_id,
        "author": author,
        "description": description,
        "pipeline_name": name,
        "query_yaml": "version: '1.0'\ncomponents: []\npipeline:\n  name: test",
        "available_to_all_organization_types": True,
        "best_for": ["quick-start", "testing"],
        "expected_output": ["answers", "documents"],
        "potential_applications": ["testing", "development"],
        "recommended_dataset": ["sample-data"],
        "tags": [{"name": "test", "tag_id": "d4a85f64-5717-4562-b3fc-2c963f66afa6"}],
    }


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def pipeline_templates(self, workspace: str) -> PipelineTemplateResourceProtocol:
        return PipelineTemplateResource(client=self, workspace=workspace)


class TestPipelineTemplateResource:
    """Tests for the PipelineTemplateResource class."""

    @pytest.fixture
    def dummy_client(self) -> DummyClient:
        """Return a basic DummyClient instance."""
        return DummyClient()

    @pytest.fixture
    def template_resource(self, dummy_client: DummyClient) -> PipelineTemplateResource:
        """Return a PipelineTemplateResource instance with a dummy client."""
        return PipelineTemplateResource(client=dummy_client, workspace="test-workspace")

    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        """Test getting a template by name successfully."""
        # Create sample template data
        template_name = "test-template"
        sample_template = create_sample_template(name=template_name)

        # Create client with predefined response
        client = DummyClient(responses={f"test-workspace/pipeline_templates/{template_name}": sample_template})

        # Create resource and call get method
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.get_template(template_name=template_name)

        # Verify results
        assert isinstance(result, PipelineTemplate)
        assert result.template_name == template_name
        assert result.yaml_config == sample_template["query_yaml"]
        assert result.description == "A test template"
        assert len(result.tags) == 1

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == f"/v1/workspaces/test-workspace/pipeline_templates/{template_name}"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        """Test getting a non-existent template."""
        # Create client that raises an exception
        client = DummyClient(
            responses={"test-workspace/pipeline_templates/nonexistent": ResourceNotFoundError("Template not found")}
        )

        # Create resource
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")

        # Verify exception is raised
        with pytest.raises(ResourceNotFoundError, match="Template not found"):
            await resource.get_template(template_name="nonexistent")

    @pytest.mark.asyncio
    async def test_list_templates_default_params(self) -> None:
        """Test listing templates with default parameters."""
        # Create sample data
        sample_templates = [
            create_sample_template(name="Template 1", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6"),
            create_sample_template(name="Template 2", template_id="2fa85f64-5717-4562-b3fc-2c963f66afa6"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": sample_templates,
                    "has_more": False,
                    "total": 2,
                }
            }
        )

        # Create resource and call list method
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list_templates()

        # Verify results
        assert len(result) == 2
        assert isinstance(result[0], PipelineTemplate)
        assert result[0].template_name == "Template 1"
        assert result[1].template_name == "Template 2"

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "/v1/workspaces/test-workspace/pipeline_templates"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_list_templates_custom_limit(self) -> None:
        """Test listing templates with custom limit."""
        # Create sample data
        sample_templates = [
            create_sample_template(name="Template 1", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": sample_templates,
                    "has_more": True,
                    "total": 2,
                }
            }
        )

        # Create resource and call list method with custom limit
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list_templates(limit=1)

        # Verify results
        assert len(result) == 1
        assert isinstance(result[0], PipelineTemplate)
        assert result[0].template_name == "Template 1"

        # Verify request
        assert client.requests[0]["endpoint"] == "/v1/workspaces/test-workspace/pipeline_templates"

    @pytest.mark.asyncio
    async def test_list_templates_empty_result(self) -> None:
        """Test listing templates when there are no templates."""
        # Create client with empty response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": [],
                    "has_more": False,
                    "total": 0,
                }
            }
        )

        # Create resource and call list method
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list_templates()

        # Verify empty results
        assert len(result) == 0
