# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.pipeline_template.resource import PipelineTemplateResource
from deepset_mcp.api.shared_models import PaginatedResponse

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
    templates_list = await template_resource.list()

    # Skip if no templates are available
    if not templates_list.data:
        pytest.skip("No templates available in the test environment")

    # Get the first template's name
    template_name = templates_list.data[0].template_name

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
    templates_list = await template_resource.list()

    assert isinstance(templates_list, PaginatedResponse)
    assert isinstance(templates_list.data, list)

    # Skip further checks if no templates are available
    if not templates_list.data:
        pytest.skip("No templates available in the test environment")

    # Verify the first template has the expected structure
    template = templates_list.data[0]
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
    templates_list = await template_resource.list(limit=limit)

    # Verify that the number of templates is not more than the limit
    assert isinstance(templates_list, PaginatedResponse)
    assert len(templates_list.data) <= limit


@pytest.mark.asyncio
async def test_list_templates_with_filter(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with a pipeline type filter."""
    # Test filtering by QUERY pipeline type
    query_templates_list = await template_resource.list(filter="pipeline_type eq 'QUERY'")

    # Verify that all returned templates are QUERY type
    assert isinstance(query_templates_list, PaginatedResponse)
    assert isinstance(query_templates_list.data, list)

    # If templates are available, verify they are all QUERY type
    for template in query_templates_list.data:
        assert isinstance(template, PipelineTemplate)
        assert template.pipeline_type == "query"

    # Test filtering by INDEXING pipeline type
    indexing_templates_list = await template_resource.list(filter="pipeline_type eq 'INDEXING'")

    # Verify that all returned templates are INDEXING type
    assert isinstance(indexing_templates_list, PaginatedResponse)
    assert isinstance(indexing_templates_list.data, list)

    # If templates are available, verify they are all INDEXING type
    for template in indexing_templates_list.data:
        assert isinstance(template, PipelineTemplate)
        assert template.pipeline_type == "indexing"


@pytest.mark.asyncio
async def test_list_templates_with_custom_sorting(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with custom sorting."""
    # Test sorting by name in ascending order
    templates_list = await template_resource.list(field="name", order="ASC", limit=5)

    assert isinstance(templates_list, PaginatedResponse)
    assert isinstance(templates_list.data, list)

    # If we have multiple templates, verify they are sorted correctly
    if len(templates_list.data) > 1:
        for i in range(len(templates_list.data) - 1):
            assert templates_list.data[i].display_name <= templates_list.data[i + 1].display_name


@pytest.mark.asyncio
async def test_get_indexing_template(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test getting a single indexing template by name.

    First lists all indexing templates, then gets the first one by name.
    """
    # Get all indexing templates
    indexing_templates_list = await template_resource.list(filter="pipeline_type eq 'INDEXING'")

    # Skip if no indexing templates are available
    if not indexing_templates_list.data:
        pytest.skip("No indexing templates available in the test environment")

    # Get the first indexing template's name
    template_name = indexing_templates_list.data[0].template_name

    # Now get that specific template
    template = await template_resource.get_template(template_name=template_name)

    # Verify the template was retrieved correctly
    assert template.template_name == template_name
    assert template.pipeline_type == "indexing"
    assert template.pipeline_template_id is not None
    assert template.yaml_config is not None  # Should have indexing_yaml content
    assert isinstance(template.best_for, list)
    assert isinstance(template.potential_applications, list)
    assert isinstance(template.tags, list)


@pytest.mark.asyncio
async def test_list_indexing_templates_with_filter(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test listing templates with an indexing pipeline type filter."""
    # Test filtering by INDEXING pipeline type
    indexing_templates_list = await template_resource.list(filter="pipeline_type eq 'INDEXING'")

    # Verify that all returned templates are INDEXING type
    assert isinstance(indexing_templates_list, PaginatedResponse)
    assert isinstance(indexing_templates_list.data, list)

    # If templates are available, verify they are all INDEXING type
    for template in indexing_templates_list.data:
        assert isinstance(template, PipelineTemplate)
        assert template.pipeline_type == "indexing"
        assert template.yaml_config is not None  # Should have indexing_yaml content


@pytest.mark.asyncio
async def test_mixed_pipeline_types_integration(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test that query and indexing templates can be retrieved together."""
    # Get all templates
    all_templates = await template_resource.list()

    # Skip if no templates are available
    if not all_templates.data:
        pytest.skip("No templates available in the test environment")

    # Separate templates by type
    query_templates = [t for t in all_templates.data if t.pipeline_type == "query"]
    indexing_templates = [t for t in all_templates.data if t.pipeline_type == "indexing"]

    # Verify that both types can exist and have proper yaml_config
    for template in query_templates:
        assert template.pipeline_type == "query"
        if template.yaml_config is not None:
            # Query templates should have query_yaml content
            assert isinstance(template.yaml_config, str)

    for template in indexing_templates:
        assert template.pipeline_type == "indexing"
        if template.yaml_config is not None:
            # Indexing templates should have indexing_yaml content
            assert isinstance(template.yaml_config, str)

    # Verify that the total matches the sum of individual types
    assert len(query_templates) + len(indexing_templates) == len(all_templates.data)


@pytest.mark.skip("Cursor-based pagination for pipeline templates needs to be fixed on deepset platform.")
@pytest.mark.asyncio
async def test_list_pagination_integration(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test pagination with real API responses."""
    # Test with a very small limit to force pagination
    first_page = await template_resource.list(limit=1)

    # Verify that the first page is returned as a PaginatedResponse
    assert isinstance(first_page, PaginatedResponse)
    assert isinstance(first_page.data, list)

    # Skip further pagination tests if no templates are available
    if not first_page.data:
        pytest.skip("No templates available in the test environment")

    # Verify the first template has the expected structure
    template = first_page.data[0]
    assert isinstance(template, PipelineTemplate)
    assert template.template_name is not None

    # If there are more results, test pagination
    if first_page.has_more:
        # Get next page using cursor
        assert first_page.next_cursor is not None
        second_page = await template_resource.list(limit=1, after=first_page.next_cursor)

        assert isinstance(second_page, PaginatedResponse)
        assert len(second_page.data) <= 1

        # Verify we got different results
        if second_page.data:
            assert second_page.data[0].template_name != first_page.data[0].template_name


@pytest.mark.skip("Cursor-based pagination for pipeline templates needs to be fixed on deepset platform.")
@pytest.mark.asyncio
async def test_list_all_templates_with_pagination(
    template_resource: PipelineTemplateResource,
) -> None:
    """Test collecting all templates through pagination."""
    all_templates = []
    current_cursor = None

    # Collect all templates using pagination
    while True:
        page = await template_resource.list(limit=2, after=current_cursor)
        assert isinstance(page, PaginatedResponse)

        all_templates.extend(page.data)

        if not page.has_more:
            break

        current_cursor = page.next_cursor
        assert current_cursor is not None

        # Safety check to prevent infinite loops
        if len(all_templates) > 100:
            break

    # Verify we collected templates
    assert isinstance(all_templates, list)
    for template in all_templates:
        assert isinstance(template, PipelineTemplate)
        assert template.template_name is not None
