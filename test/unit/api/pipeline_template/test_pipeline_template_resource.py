# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.pipeline_template.protocols import PipelineTemplateResourceProtocol
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.shared_models import PaginatedResponse
from test.unit.conftest import BaseFakeClient


def create_sample_template(
    name: str = "test-template",
    author: str = "deepset-ai",
    description: str = "A test template",
    template_id: str = "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    pipeline_type: str = "query",
) -> dict[str, Any]:
    """Create a sample pipeline template response dictionary for testing."""
    template_data = {
        "pipeline_template_id": template_id,
        "author": author,
        "description": description,
        "pipeline_name": name,
        "name": name,
        "available_to_all_organization_types": True,
        "best_for": ["quick-start", "testing"],
        "expected_output": ["answers", "documents"],
        "potential_applications": ["testing", "development"],
        "recommended_dataset": ["sample-data"],
        "tags": [{"name": "test", "tag_id": "d4a85f64-5717-4562-b3fc-2c963f66afa6"}],
        "pipeline_type": pipeline_type,
    }

    # Add appropriate YAML config based on pipeline type
    if pipeline_type == "indexing":
        template_data["indexing_yaml"] = "version: '1.0'\ncomponents:\n  - name: indexer\n    type: DocumentWriter"
    else:
        template_data["query_yaml"] = "version: '1.0'\ncomponents: []\npipeline:\n  name: test"

    return template_data


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        super().__init__(responses)
        self.response_queue: list[Any] = []
        self.response_index = 0
        # Store all available pipeline template data for cursor-based pagination
        self.all_template_data: list[dict[str, Any]] = []

    def set_responses(self, responses: list[Any]) -> None:
        """Set a queue of responses for sequential requests."""
        self.response_queue = responses
        self.response_index = 0

    def set_template_data(self, all_templates: list[dict[str, Any]]) -> None:
        """Set all pipeline template data for cursor-based pagination testing."""
        self.all_template_data = all_templates

    async def request(self, endpoint: str, **kwargs: Any) -> Any:
        """Override to use queued responses when available, or handle pagination logic for templates."""
        if self.response_queue and self.response_index < len(self.response_queue):
            # Always record the request like the parent class
            self.requests.append({"endpoint": endpoint, **kwargs})
            response = self.response_queue[self.response_index]
            self.response_index += 1
            return response

        # Handle cursor-based pagination for pipeline template listing (only when no static response is available)
        if (
            endpoint.endswith("/pipeline_templates")
            and kwargs.get("method", "GET") == "GET"
            and self.all_template_data
            and not self._has_static_response(endpoint)
        ):
            # Always record the request like the parent class
            self.requests.append({"endpoint": endpoint, **kwargs})
            return await self._handle_paginated_templates(**kwargs)

        # Let parent handle the request and recording
        return await super().request(endpoint, **kwargs)

    def _has_static_response(self, endpoint: str) -> bool:
        """Check if there's a static response configured for this endpoint."""
        # Check if there's a response in the responses dict for this endpoint
        if self.responses:
            for key in self.responses.keys():
                if endpoint.endswith(key):
                    return True
        return False

    async def _handle_paginated_templates(self, **kwargs: Any) -> Any:
        """Handle pagination logic for pipeline template listing."""
        params = kwargs.get("params", {})
        limit = params.get("limit", 10)
        after_cursor = params.get("before")

        # Find start index based on cursor
        start_index = 0
        if after_cursor:
            # Find the template with this ID and start after it
            for i, template in enumerate(self.all_template_data):
                if template["pipeline_template_id"] == after_cursor:
                    start_index = i + 1
                    break

        # Get the slice of data
        end_index = start_index + limit
        page_data = self.all_template_data[start_index:end_index]
        has_more = end_index < len(self.all_template_data)

        from deepset_mcp.api.transport import TransportResponse

        response_data = {
            "data": page_data,
            "has_more": has_more,
        }

        return TransportResponse(status_code=200, json=response_data, text="")

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
    async def test_list_default_params(self) -> None:
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
        result = await resource.list()

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.has_more is False
        assert isinstance(result.data[0], PipelineTemplate)
        assert result.data[0].template_name == "Template 1"
        assert result.data[1].template_name == "Template 2"

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipeline_templates"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.skip("Cursor-based pagination for pipeline templates needs to be fixed on deepset platform.")
    @pytest.mark.asyncio
    async def test_list_with_pagination(self) -> None:
        """Test listing templates with pagination parameters."""
        # Create sample data
        sample_templates = [
            create_sample_template(name="Template 3", template_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"),
            create_sample_template(name="Template 4", template_id="4fa85f64-5717-4562-b3fc-2c963f66afa6"),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": sample_templates,
                    "has_more": False,
                    "total": 10,
                }
            }
        )

        # Create resource and call list method with pagination
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list(limit=5, after="some_cursor")

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.data[0].template_name == "Template 3"
        assert result.data[1].template_name == "Template 4"

        # Verify request
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipeline_templates"
        # TODO: change to after when problem with deepset API pagination is fixed
        assert client.requests[0]["params"] == {
            "limit": 5,
            "before": "some_cursor",
            "field": "created_at",
            "order": "DESC",
        }

    @pytest.mark.asyncio
    async def test_list_empty_result(self) -> None:
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
        result = await resource.list()

        # Verify empty results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_templates_with_filter(self) -> None:
        """Test listing templates with a filter."""
        # Create sample data
        sample_templates = [
            create_sample_template(
                name="Query Template", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6", pipeline_type="query"
            ),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": sample_templates,
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Create resource and call list method with filter
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list(filter="pipeline_type eq 'QUERY'")

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 1
        assert result.has_more is False
        assert isinstance(result.data[0], PipelineTemplate)
        assert result.data[0].template_name == "Query Template"
        assert result.data[0].pipeline_type == "query"

        # Verify request includes filter
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipeline_templates"
        assert "filter" in client.requests[0]["params"]
        assert client.requests[0]["params"]["filter"] == "pipeline_type eq 'QUERY'"

    @pytest.mark.asyncio
    async def test_list_templates_with_custom_sorting(self) -> None:
        """Test listing templates with custom field and order."""
        # Create sample data
        sample_templates = [
            create_sample_template(name="Template A", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6"),
            create_sample_template(name="Template B", template_id="2fa85f64-5717-4562-b3fc-2c963f66afa6"),
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

        # Create resource and call list method with custom sorting
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list(field="name", order="ASC")

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.has_more is False
        assert isinstance(result.data[0], PipelineTemplate)
        assert result.data[0].template_name == "Template A"
        assert result.data[1].template_name == "Template B"

        # Verify request includes custom sorting
        assert len(client.requests) == 1
        assert client.requests[0]["params"]["field"] == "name"
        assert client.requests[0]["params"]["order"] == "ASC"

    @pytest.mark.asyncio
    async def test_get_indexing_template_success(self) -> None:
        """Test getting an indexing template by name successfully."""
        # Create sample indexing template data
        template_name = "test-indexing-template"
        sample_template = create_sample_template(name=template_name, pipeline_type="indexing")

        # Create client with predefined response
        client = DummyClient(responses={f"test-workspace/pipeline_templates/{template_name}": sample_template})

        # Create resource and call get method
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.get_template(template_name=template_name)

        # Verify results
        assert isinstance(result, PipelineTemplate)
        assert result.template_name == template_name
        assert result.yaml_config == sample_template["indexing_yaml"]
        assert result.pipeline_type == "indexing"
        assert result.description == "A test template"
        assert len(result.tags) == 1

        # Verify request
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == f"/v1/workspaces/test-workspace/pipeline_templates/{template_name}"
        assert client.requests[0]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_list_indexing_templates_with_filter(self) -> None:
        """Test listing indexing templates with a filter."""
        # Create sample data with indexing templates
        sample_templates = [
            create_sample_template(
                name="Indexing Template", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6", pipeline_type="indexing"
            ),
        ]

        # Create client with predefined response
        client = DummyClient(
            responses={
                "test-workspace/pipeline_templates": {
                    "data": sample_templates,
                    "has_more": False,
                    "total": 1,
                }
            }
        )

        # Create resource and call list method with indexing filter
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")
        result = await resource.list(filter="pipeline_type eq 'INDEXING'")

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 1
        assert result.has_more is False
        assert isinstance(result.data[0], PipelineTemplate)
        assert result.data[0].template_name == "Indexing Template"
        assert result.data[0].pipeline_type == "indexing"
        assert result.data[0].yaml_config == sample_templates[0]["indexing_yaml"]

        # Verify request includes filter
        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/pipeline_templates"
        assert "filter" in client.requests[0]["params"]
        assert client.requests[0]["params"]["filter"] == "pipeline_type eq 'INDEXING'"

    @pytest.mark.asyncio
    async def test_mixed_pipeline_types(self) -> None:
        """Test that query and indexing templates work correctly together."""
        # Create sample data with mixed pipeline types
        sample_templates = [
            create_sample_template(
                name="Query Template", template_id="1fa85f64-5717-4562-b3fc-2c963f66afa6", pipeline_type="query"
            ),
            create_sample_template(
                name="Indexing Template", template_id="2fa85f64-5717-4562-b3fc-2c963f66afa6", pipeline_type="indexing"
            ),
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
        result = await resource.list()

        # Verify results
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.has_more is False

        # Verify query template
        query_template = result.data[0]
        assert isinstance(query_template, PipelineTemplate)
        assert query_template.template_name == "Query Template"
        assert query_template.pipeline_type == "query"
        assert query_template.yaml_config == sample_templates[0]["query_yaml"]

        # Verify indexing template
        indexing_template = result.data[1]
        assert isinstance(indexing_template, PipelineTemplate)
        assert indexing_template.template_name == "Indexing Template"
        assert indexing_template.pipeline_type == "indexing"
        assert indexing_template.yaml_config == sample_templates[1]["indexing_yaml"]

    @pytest.mark.skip("Cursor-based pagination for pipeline templates needs to be fixed on deepset platform.")
    @pytest.mark.asyncio
    async def test_list_iteration(self) -> None:
        """Test iterating through paginated template results."""
        # Create sample data for multiple pages
        all_templates = [
            create_sample_template(name=f"Template {i}", template_id=f"{i}fa85f64-5717-4562-b3fc-2c963f66afa6")
            for i in range(1, 6)  # Create 5 templates
        ]

        # Create client with paginated data
        client = DummyClient()
        client.set_template_data(all_templates)

        # Create resource
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")

        # Get first page with limit of 2
        result = await resource.list(limit=2)

        # Verify first page
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.has_more is True
        assert result.data[0].template_name == "Template 1"
        assert result.data[1].template_name == "Template 2"

        # Get next page
        next_page = await result._get_next_page()
        assert next_page is not None
        assert len(next_page.data) == 2
        assert next_page.data[0].template_name == "Template 3"
        assert next_page.data[1].template_name == "Template 4"

    @pytest.mark.skip("Cursor-based pagination for pipeline templates needs to be fixed on deepset platform.")
    @pytest.mark.asyncio
    async def test_list_cursor_population(self) -> None:
        """Test that cursors are properly populated in paginated responses."""
        # Create sample templates
        all_templates = [
            create_sample_template(name=f"Template {i}", template_id=f"{i}fa85f64-5717-4562-b3fc-2c963f66afa6")
            for i in range(1, 4)  # Create 3 templates
        ]

        # Create client with paginated data
        client = DummyClient()
        client.set_template_data(all_templates)

        # Create resource
        resource = PipelineTemplateResource(client=client, workspace="test-workspace")

        # Get first page with limit of 2
        result = await resource.list(limit=2)

        # Verify cursor is populated
        assert result.has_more is True
        assert result.next_cursor == "2fa85f64-5717-4562-b3fc-2c963f66afa6"  # ID of last item on page
