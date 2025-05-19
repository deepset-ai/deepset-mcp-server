import json

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.resource import IndexResource

pytestmark = pytest.mark.integration


@pytest.fixture
def valid_index_config() -> str:
    """Return a valid index YAML configuration for testing."""
    return json.dumps({
        "name": "Standard-Index-German",
        "description": "This is the index description.",
        "config_yaml": "# If you need help with the YAML format, have a look at https://docs.cloud.deepset.ai/v2.0/docs/create-a-pipeline#create-a-pipeline-using-pipeline-editor.\n# This section defines components that you want to use in your pipelines. Each component must have a name and a type. You can also set the component's parameters here.\n# The name is up to you, you can give your component a friendly name. You then use components' names when specifying the connections in the pipeline.\n# Type is the class path of the component. You can check the type on the component's documentation page.\ncomponents:\n  file_classifier:\n    type: haystack.components.routers.file_type_router.FileTypeRouter\n    init_parameters:\n      mime_types:\n      - text/plain\n      - application/pdf\n      - text/markdown\n      - text/html\n      - application/vnd.openxmlformats-officedocument.wordprocessingml.document\n      - application/vnd.openxmlformats-officedocument.presentationml.presentation\n      - application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\n      - text/csv\n\n  text_converter:\n    type: haystack.components.converters.txt.TextFileToDocument\n    init_parameters:\n      encoding: utf-8\n\n  pdf_converter:\n    type: haystack.components.converters.pdfminer.PDFMinerToDocument\n    init_parameters:\n      line_overlap: 0.5\n      char_margin: 2\n      line_margin: 0.5\n      word_margin: 0.1\n      boxes_flow: 0.5\n      detect_vertical: true\n      all_texts: false\n      store_full_path: false\n\n  markdown_converter:\n    type: haystack.components.converters.txt.TextFileToDocument\n    init_parameters:\n      encoding: utf-8\n\n  html_converter:\n    type: haystack.components.converters.html.HTMLToDocument\n    init_parameters:\n      # A dictionary of keyword arguments to customize how you want to extract content from your HTML files.\n      # For the full list of available arguments, see\n      # the [Trafilatura documentation](https://trafilatura.readthedocs.io/en/latest/corefunctions.html#extract)\n      extraction_kwargs:\n        output_format: markdown # Extract text from HTML. You can also also choose \"txt\"\n        target_language: null  # You can define a language (using the ISO 639-1 format) to discard documents that don't match that language.\n        include_tables: true  # If true, includes tables in the output\n        include_links: true  # If true, keeps links along with their targets\n\n  docx_converter:\n    type: haystack.components.converters.docx.DOCXToDocument\n    init_parameters: {}\n\n  pptx_converter:\n    type: haystack.components.converters.pptx.PPTXToDocument\n    init_parameters: {}\n\n  xlsx_converter:\n    type: haystack.components.converters.xlsx.XLSXToDocument\n    init_parameters: {}\n\n  csv_converter:\n    type: haystack.components.converters.csv.CSVToDocument\n    init_parameters:\n      encoding: utf-8\n\n  joiner:\n    type: haystack.components.joiners.document_joiner.DocumentJoiner\n    init_parameters:\n      join_mode: concatenate\n      sort_by_score: false\n\n  joiner_xlsx:  # merge split documents with non-split xlsx documents\n    type: haystack.components.joiners.document_joiner.DocumentJoiner\n    init_parameters:\n      join_mode: concatenate\n      sort_by_score: false\n\n  splitter:\n    type: haystack.components.preprocessors.document_splitter.DocumentSplitter\n    init_parameters:\n      split_by: word\n      split_length: 250\n      split_overlap: 30\n      respect_sentence_boundary: true\n      language: de\n\n  document_embedder:\n    type: deepset_cloud_custom_nodes.embedders.nvidia.document_embedder.DeepsetNvidiaDocumentEmbedder\n    init_parameters:\n      normalize_embeddings: true\n      model: intfloat/multilingual-e5-base\n\n  writer:\n    type: haystack.components.writers.document_writer.DocumentWriter\n    init_parameters:\n      document_store:\n        type: haystack_integrations.document_stores.opensearch.document_store.OpenSearchDocumentStore\n        init_parameters:\n          embedding_dim: 768\n      policy: OVERWRITE\n\nconnections:  # Defines how the components are connected\n- sender: file_classifier.text/plain\n  receiver: text_converter.sources\n- sender: file_classifier.application/pdf\n  receiver: pdf_converter.sources\n- sender: file_classifier.text/markdown\n  receiver: markdown_converter.sources\n- sender: file_classifier.text/html\n  receiver: html_converter.sources\n- sender: file_classifier.application/vnd.openxmlformats-officedocument.wordprocessingml.document\n  receiver: docx_converter.sources\n- sender: file_classifier.application/vnd.openxmlformats-officedocument.presentationml.presentation\n  receiver: pptx_converter.sources\n- sender: file_classifier.application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\n  receiver: xlsx_converter.sources\n- sender: file_classifier.text/csv\n  receiver: csv_converter.sources\n- sender: text_converter.documents\n  receiver: joiner.documents\n- sender: pdf_converter.documents\n  receiver: joiner.documents\n- sender: markdown_converter.documents\n  receiver: joiner.documents\n- sender: html_converter.documents\n  receiver: joiner.documents\n- sender: docx_converter.documents\n  receiver: joiner.documents\n- sender: pptx_converter.documents\n  receiver: joiner.documents\n- sender: joiner.documents\n  receiver: splitter.documents\n- sender: splitter.documents\n  receiver: joiner_xlsx.documents\n- sender: xlsx_converter.documents\n  receiver: joiner_xlsx.documents\n- sender: csv_converter.documents\n  receiver: joiner_xlsx.documents\n- sender: joiner_xlsx.documents\n  receiver: document_embedder.documents\n- sender: document_embedder.documents\n  receiver: writer.documents\n\ninputs:  # Define the inputs for your pipeline\n  files: \"file_classifier.sources\"  # This component will receive the files to index as input\n"
    })


@pytest.fixture
async def index_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> IndexResource:
    """Create an IndexResource instance for testing."""
    return IndexResource(client=client, workspace=test_workspace)


@pytest.fixture
default_index_name = "test-index"


@pytest.mark.asyncio
async def test_create_index(
    index_resource: IndexResource,
    valid_index_config: str,
    default_index_name: str,
) -> None:
    """Test creating a new index."""
    # Create a new index
    config = json.loads(valid_index_config)
    await index_resource.create(
        name=default_index_name,
        yaml_config=config["config_yaml"],
        description="Test index description"
    )

    # Verify the index was created by retrieving it
    index: Index = await index_resource.get(index_name=default_index_name)

    assert index.name == default_index_name
    assert index.config_yaml == config["config_yaml"]


@pytest.mark.asyncio
async def test_list_indexes(
    index_resource: IndexResource,
    valid_index_config: str,
) -> None:
    """Test listing indexes with pagination."""
    # Create multiple test indexes
    config = json.loads(valid_index_config)
    index_names = []
    for i in range(3):
        index_name = f"test-list-index-{i}"
        index_names.append(index_name)
        await index_resource.create(
            name=index_name,
            yaml_config=config["config_yaml"]
        )

    # Test listing without pagination
    indexes = await index_resource.list(limit=10)
    assert len(indexes.data) == 3

    # Verify our created indexes are in the list
    retrieved_names = [p.name for p in indexes.data]
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
        assert first_page.data[0].id != second_page.data[0].id


@pytest.mark.asyncio
async def test_get_index(
    index_resource: IndexResource,
    valid_index_config: str,
    default_index_name: str,
) -> None:
    """Test getting a single index by name."""
    # Create an index to retrieve
    config = json.loads(valid_index_config)
    await index_resource.create(
        name=default_index_name,
        yaml_config=config["config_yaml"]
    )

    # Test getting the index
    index: Index = await index_resource.get(index_name=default_index_name)
    assert index.name == default_index_name
    assert index.config_yaml == config["config_yaml"]


@pytest.mark.asyncio
async def test_update_index(
    index_resource: IndexResource,
    valid_index_config: str,
) -> None:
    """Test updating an existing index's name and config."""
    original_name = "test-update-index-original"
    updated_name = "test-update-index-updated"

    # Create an index to update
    config = json.loads(valid_index_config)
    await index_resource.create(
        name=original_name,
        yaml_config=config["config_yaml"]
    )

    # Update the index name
    await index_resource.update(
        index_name=original_name,
        updated_index_name=updated_name,
    )

    # Verify the name was updated
    updated_index: Index = await index_resource.get(index_name=updated_name)
    assert updated_index.name == updated_name

    # Update the index config
    modified_yaml = config["config_yaml"].replace("split_length: 250", "split_length: 300")
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
