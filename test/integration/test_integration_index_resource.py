import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.resource import IndexResource

pytestmark = pytest.mark.integration


@pytest.fixture
async def index_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> IndexResource:
    """Create an IndexResource instance for testing."""
    return IndexResource(client=client, workspace=test_workspace)


@pytest.fixture
def sample_yaml_config() -> str:
    """Return a sample YAML configuration for testing."""
    return """
name: my_index
type: DocumentIndex
description: Test index for integration tests.
component:
  type: BM25Retriever
  init_parameters:
    columns: ["content"]
    top_k: 10
"""


@pytest.mark.asyncio
async def test_create_index(
    index_resource: IndexResource,
    sample_yaml_config: str,
) -> None:
    """Test creating a new index."""
    index_name = "test-index"

    # Create a new index
    await index_resource.create(name=index_name, yaml_config=sample_yaml_config)

    # Verify the index was created by retrieving it
    index: Index = await index_resource.get(index_name=index_name)

    assert index.name == index_name
    assert index.config_yaml == sample_yaml_config


@pytest.mark.asyncio
async def test_list_indexes(
    index_resource: IndexResource,
    sample_yaml_config: str,
) -> None:
    """Test listing indexes with pagination."""
    # Create multiple test indexes
    index_names = []
    for i in range(3):
        index_name = f"test-list-index-{i}"
        index_names.append(index_name)
        await index_resource.create(name=index_name, yaml_config=sample_yaml_config)

    # Test listing without pagination
    indexes = await index_resource.list(limit=10)
    assert len(indexes.data) >= 3  # Could be more if other tests left indexes

    # Verify our created indexes are in the list
    retrieved_names = [idx.name for idx in indexes.data]
    for name in index_names:
        assert name in retrieved_names

    # Test pagination
    if len(indexes.data) > 1:
        # Get the first page with 1 item
        first_page = await index_resource.list(limit=1)
        assert len(first_page.data) == 1

        # Get the second page
        second_page = await index_resource.list(page_number=2, limit=1)
        assert len(second_page.data) == 1

        # Verify they're different indexes
        assert first_page.data[0].pipeline_index_id != second_page.data[0].pipeline_index_id


@pytest.mark.asyncio
async def test_get_index(
    index_resource: IndexResource,
    sample_yaml_config: str,
) -> None:
    """Test getting a single index by name."""
    index_name = "test-get-index"

    # Create an index to retrieve
    await index_resource.create(name=index_name, yaml_config=sample_yaml_config)

    # Test getting the index
    index: Index = await index_resource.get(index_name=index_name)
    assert index.name == index_name
    assert index.config_yaml == sample_yaml_config


@pytest.mark.asyncio
async def test_update_index(
    index_resource: IndexResource,
    sample_yaml_config: str,
) -> None:
    """Test updating an existing index's name and config."""
    original_name = "test-update-index-original"
    updated_name = "test-update-index-updated"

    # Create an index to update
    await index_resource.create(name=original_name, yaml_config=sample_yaml_config)

    # Update the index name
    await index_resource.update(
        index_name=original_name,
        updated_index_name=updated_name,
    )

    # Verify the name was updated
    updated_index: Index = await index_resource.get(index_name=updated_name)
    assert updated_index.name == updated_name

    # Update the index config
    modified_yaml = sample_yaml_config.replace("top_k: 10", "top_k: 20")
    await index_resource.update(
        index_name=updated_name,
        yaml_config=modified_yaml,
    )

    # Verify the config was updated
    updated_index = await index_resource.get(index_name=updated_name)
    assert updated_index.config_yaml == modified_yaml


@pytest.mark.asyncio
async def test_get_nonexistent_index(
    index_resource: IndexResource,
) -> None:
    """Test error handling when getting a non-existent index."""
    non_existent_name = "non-existent-index"

    # Trying to get a non-existent index should raise an exception
    with pytest.raises(ResourceNotFoundError):
        await index_resource.get(index_name=non_existent_name)