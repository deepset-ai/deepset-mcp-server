from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineTemplateTag, PipelineType
from deepset_mcp.tools.pipeline_template import get_pipeline_template, list_pipeline_templates
from test.unit.conftest import BaseFakeClient


class FakePipelineTemplateResource:
    def __init__(
        self,
        list_response: list[PipelineTemplate] | None = None,
        get_response: PipelineTemplate | None = None,
        list_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self._list_response = list_response
        self._get_response = get_response
        self._list_exception = list_exception
        self._get_exception = get_exception
        self.last_list_call_params: dict[str, Any] = {}

    async def list_templates(
        self,
        limit: int = 100,
        field: str = "created_at",
        order: str = "DESC",
        filter: str | None = None
    ) -> list[PipelineTemplate]:
        # Store the parameters for verification
        self.last_list_call_params = {
            "limit": limit,
            "field": field,
            "order": order,
            "filter": filter
        }
        
        if self._list_exception:
            raise self._list_exception
        if self._list_response is not None:
            return self._list_response
        raise NotImplementedError

    async def get_template(self, template_name: str) -> PipelineTemplate:
        if self._get_exception:
            raise self._get_exception
        if self._get_response is not None:
            return self._get_response
        raise NotImplementedError


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakePipelineTemplateResource) -> None:
        self._resource = resource
        super().__init__()

    def pipeline_templates(self, workspace: str) -> FakePipelineTemplateResource:
        return self._resource


@pytest.mark.asyncio
async def test_list_pipeline_templates_returns_formatted_string() -> None:
    template1 = PipelineTemplate(
        pipeline_name="template1",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Alice Smith",
        description="First template",
        best_for=["use case 1", "use case 2"],
        potential_applications=["app 1", "app 2"],
        query_yaml="config1: value1",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    template2 = PipelineTemplate(
        pipeline_name="template2",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000002"),
        author="Bob Jones",
        description="Second template",
        best_for=["use case 3"],
        potential_applications=["app 3"],
        query_yaml="config2: value2",
        tags=[PipelineTemplateTag(name="tag2", tag_id=UUID("20000000-0000-0000-0000-000000000002"))],
        pipeline_type=PipelineType.INDEXING,
    )
    resource = FakePipelineTemplateResource(list_response=[template1, template2])
    client = FakeClient(resource)
    result = await list_pipeline_templates(client, workspace="ws1")

    assert result.count("<pipeline_template name=") == 2
    assert "template1" in result
    assert "template2" in result
    assert "Alice Smith" in result
    assert "Bob Jones" in result


@pytest.mark.asyncio
async def test_list_pipeline_templates_handles_resource_not_found() -> None:
    resource = FakePipelineTemplateResource(list_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await list_pipeline_templates(client, workspace="invalid_ws")

    assert "no workspace named 'invalid_ws'" in result.lower()


@pytest.mark.asyncio
async def test_list_pipeline_templates_handles_unexpected_error() -> None:
    resource = FakePipelineTemplateResource(list_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)
    result = await list_pipeline_templates(client, workspace="ws1")

    assert "Failed to list pipeline templates" in result
    assert "Server error" in result


@pytest.mark.asyncio
async def test_get_pipeline_template_returns_formatted_string() -> None:
    template = PipelineTemplate(
        pipeline_name="test_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Eve Brown",
        description="Test template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(get_response=template)
    client = FakeClient(resource)
    result = await get_pipeline_template(client, workspace="ws1", template_name="test_template")

    assert "test_template" in result
    assert "Eve Brown" in result
    assert "Test template" in result
    assert "config: value" in result
    assert "tag1" in result


@pytest.mark.asyncio
async def test_get_pipeline_template_handles_resource_not_found() -> None:
    resource = FakePipelineTemplateResource(get_exception=ResourceNotFoundError())
    client = FakeClient(resource)
    result = await get_pipeline_template(client, workspace="ws1", template_name="invalid_template")

    assert "no pipeline template named 'invalid_template'" in result.lower()


@pytest.mark.asyncio
async def test_get_pipeline_template_handles_unexpected_error() -> None:
    resource = FakePipelineTemplateResource(get_exception=UnexpectedAPIError(status_code=500, message="Server error"))
    client = FakeClient(resource)
    result = await get_pipeline_template(client, workspace="ws1", template_name="test_template")

    assert "Failed to fetch pipeline template 'test_template'" in result
    assert "Server error" in result


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_filter() -> None:
    """Test that filter parameter is passed correctly to the resource."""
    template = PipelineTemplate(
        pipeline_name="query_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A query template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)
    
    filter_value = "pipeline_type eq 'QUERY'"
    await list_pipeline_templates(
        client, 
        workspace="ws1", 
        filter=filter_value
    )
    
    # Verify the filter was passed to the resource
    assert resource.last_list_call_params["filter"] == filter_value


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_custom_sorting() -> None:
    """Test that custom sorting parameters are passed correctly."""
    template = PipelineTemplate(
        pipeline_name="test_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A test template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)
    
    await list_pipeline_templates(
        client,
        workspace="ws1",
        limit=50,
        field="name",
        order="ASC"
    )
    
    # Verify parameters were passed correctly
    assert resource.last_list_call_params["limit"] == 50
    assert resource.last_list_call_params["field"] == "name"
    assert resource.last_list_call_params["order"] == "ASC"
    assert resource.last_list_call_params["filter"] is None


@pytest.mark.asyncio
async def test_list_pipeline_templates_with_filter_and_sorting() -> None:
    """Test that both filter and sorting parameters work together."""
    template = PipelineTemplate(
        pipeline_name="query_template",
        pipeline_template_id=UUID("00000000-0000-0000-0000-000000000001"),
        author="Test Author",
        description="A query template",
        best_for=["use case 1"],
        potential_applications=["app 1"],
        query_yaml="config: value",
        tags=[PipelineTemplateTag(name="tag1", tag_id=UUID("10000000-0000-0000-0000-000000000001"))],
        pipeline_type=PipelineType.QUERY,
    )
    resource = FakePipelineTemplateResource(list_response=[template])
    client = FakeClient(resource)
    
    filter_value = "tags/any(tag: tag/name eq 'category:basic qa') and pipeline_type eq 'QUERY'"
    
    await list_pipeline_templates(
        client,
        workspace="ws1",
        limit=25,
        field="name",
        order="ASC",
        filter=filter_value
    )
    
    # Verify all parameters were passed correctly
    assert resource.last_list_call_params["limit"] == 25
    assert resource.last_list_call_params["field"] == "name"
    assert resource.last_list_call_params["order"] == "ASC"
    assert resource.last_list_call_params["filter"] == filter_value
