import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource

pytestmark = pytest.mark.integration


@pytest.fixture
async def template_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> PipelineTemplateResource:
    """Create a PipelineTemplateResource instance for testing."""
    return PipelineTemplateResource(client=client, workspace=test_workspace)


@pytest.mark.asyncio
async def test_get_template(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test getting a single pipeline template by name.

    First lists all templates, then gets the first one by name.
    """
    # Get all templates to find an existing one
    templates = await template_resource.list_templates()

    # Skip if no templates are available
    if not templates:
        pytest.skip("No templates available in the test environment")

    # Get the first template's name
    template_name = templates[0].template_name

    # Now get that specific template
    template = await template_resource.get_template(template_name=template_name)

    # Verify the template was retrieved correctly
    assert template.template_name == template_name
    assert template.pipeline_template_id is not None
    assert isinstance(template.best_for, list)
    assert isinstance(template.potential_applications, list)
    assert isinstance(template.tags, list)


@pytest.mark.asyncio
async def test_get_nonexistent_template(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test error handling when getting a non-existent template."""
    non_existent_name = "non-existent-template-xyz-123"

    # Trying to get a non-existent template should raise an exception
    with pytest.raises(ResourceNotFoundError):
        await template_resource.get_template(template_name=non_existent_name)


@pytest.mark.asyncio
async def test_list_templates(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates."""
    # Test listing templates with default limit
    templates = await template_resource.list_templates()

    # Verify that the templates are returned as a list
    assert isinstance(templates, list)

    # Skip further checks if no templates are available
    if not templates:
        pytest.skip("No templates available in the test environment")

    # Verify the first template has the expected structure
    template = templates[0]
    assert isinstance(template, PipelineTemplate)
    assert template.template_name is not None
    assert template.author is not None
    assert template.description is not None
    assert template.pipeline_template_id is not None


@pytest.mark.asyncio
async def test_list_templates_with_limit(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with a specific limit."""
    # Test with a small limit
    limit = 1
    templates = await template_resource.list_templates(limit=limit)

    # Verify that the number of templates is not more than the limit
    assert len(templates) <= limit


@pytest.mark.asyncio
async def test_list_templates_with_filter(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with a pipeline type filter."""
    # Test filtering by QUERY pipeline type
    query_templates = await template_resource.list_templates(filter="pipeline_type eq 'QUERY'")

    # Verify that all returned templates are QUERY type
    assert isinstance(query_templates, list)

    # If templates are available, verify they are all QUERY type
    for template in query_templates:
        assert isinstance(template, PipelineTemplate)
        assert template.pipeline_type == "query"

    # Test filtering by INDEXING pipeline type
    indexing_templates = await template_resource.list_templates(filter="pipeline_type eq 'INDEXING'")

    # Verify that all returned templates are INDEXING type
    assert isinstance(indexing_templates, list)

    # If templates are available, verify they are all INDEXING type
    for template in indexing_templates:
        assert isinstance(template, PipelineTemplate)
        assert template.pipeline_type == "indexing"


@pytest.mark.asyncio
async def test_list_templates_with_custom_sorting(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with custom sorting."""
    # Test sorting by name in ascending order
    templates = await template_resource.list_templates(field="name", order="ASC", limit=5)

    # Verify that the templates are returned as a list
    assert isinstance(templates, list)

    # If we have multiple templates, verify they are sorted correctly
    if len(templates) > 1:
        for i in range(len(templates) - 1):
            assert templates[i].display_name <= templates[i + 1].display_name
