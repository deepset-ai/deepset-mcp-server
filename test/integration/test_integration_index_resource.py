# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.indexes.models import Index
from deepset_mcp.api.indexes.resource import IndexResource
from deepset_mcp.api.pipeline.models import PipelineValidationResult

pytestmark = pytest.mark.integration


@pytest.fixture
def valid_index_config() -> str:
    """Return a valid index YAML configuration for testing."""
    return json.dumps(
        {
            "config_yaml": """
components:
  file_classifier:
    type: haystack.components.routers.file_type_router.FileTypeRouter
    init_parameters:
      mime_types:
      - text/plain
      - application/pdf
      - text/markdown
      - text/html
      - application/vnd.openxmlformats-officedocument.wordprocessingml.document
      - application/vnd.openxmlformats-officedocument.presentationml.presentation
      - application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
      - text/csv

  text_converter:
    type: haystack.components.converters.txt.TextFileToDocument
    init_parameters:
      encoding: utf-8

  pdf_converter:
    type: haystack.components.converters.pdfminer.PDFMinerToDocument
    init_parameters:
      line_overlap: 0.5
      char_margin: 2
      line_margin: 0.5
      word_margin: 0.1
      boxes_flow: 0.5
      detect_vertical: true
      all_texts: false
      store_full_path: false

  markdown_converter:
    type: haystack.components.converters.txt.TextFileToDocument
    init_parameters:
      encoding: utf-8

  html_converter:
    type: haystack.components.converters.html.HTMLToDocument
    init_parameters:
      # A dictionary of keyword arguments to customize how you want to extract content from your HTML files.
      # For the full list of available arguments, see
      # the [Trafilatura documentation](https://trafilatura.readthedocs.io/en/latest/corefunctions.html#extract).
      extraction_kwargs:
        output_format: markdown # Extract text from HTML. You can also also choose "txt"
        include_tables: true  # If true, includes tables in the output
        include_links: true  # If true, keeps links along with their targets

  docx_converter:
    type: haystack.components.converters.docx.DOCXToDocument
    init_parameters:
      link_format: markdown

  pptx_converter:
    type: haystack.components.converters.pptx.PPTXToDocument
    init_parameters: {}

  xlsx_converter:
    type: haystack.components.converters.xlsx.XLSXToDocument
    init_parameters: {}

  csv_converter:
    type: haystack.components.converters.csv.CSVToDocument
    init_parameters:
      encoding: utf-8

  joiner:
    type: haystack.components.joiners.document_joiner.DocumentJoiner
    init_parameters:
      join_mode: concatenate
      sort_by_score: false

  joiner_xlsx:  # merge split documents with non-split xlsx documents
    type: haystack.components.joiners.document_joiner.DocumentJoiner
    init_parameters:
      join_mode: concatenate
      sort_by_score: false

  splitter:
    type: haystack.components.preprocessors.document_splitter.DocumentSplitter
    init_parameters:
      split_by: word
      split_length: 250
      split_overlap: 30
      respect_sentence_boundary: true
      language: en

  document_embedder:
    type: haystack.components.embedders.sentence_transformers_document_embedder.SentenceTransformersDocumentEmbedder
    init_parameters:
      normalize_embeddings: true
      model: intfloat/e5-base-v2

  writer:
    type: haystack.components.writers.document_writer.DocumentWriter
    init_parameters:
      document_store:
        type: haystack_integrations.document_stores.opensearch.document_store.OpenSearchDocumentStore
        init_parameters:
          hosts:
          index: ''
          max_chunk_bytes: 104857600
          embedding_dim: 768
          return_embedding: false
          method:
          mappings:
          settings:
          create_index: true
          http_auth:
          use_ssl:
          verify_certs:
          timeout:
      policy: OVERWRITE

connections:  # Defines how the components are connected
- sender: file_classifier.text/plain
  receiver: text_converter.sources
- sender: file_classifier.application/pdf
  receiver: pdf_converter.sources
- sender: file_classifier.text/markdown
  receiver: markdown_converter.sources
- sender: file_classifier.text/html
  receiver: html_converter.sources
- sender: file_classifier.application/vnd.openxmlformats-officedocument.wordprocessingml.document
  receiver: docx_converter.sources
- sender: file_classifier.application/vnd.openxmlformats-officedocument.presentationml.presentation
  receiver: pptx_converter.sources
- sender: file_classifier.application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  receiver: xlsx_converter.sources
- sender: file_classifier.text/csv
  receiver: csv_converter.sources
- sender: text_converter.documents
  receiver: joiner.documents
- sender: pdf_converter.documents
  receiver: joiner.documents
- sender: markdown_converter.documents
  receiver: joiner.documents
- sender: html_converter.documents
  receiver: joiner.documents
- sender: docx_converter.documents
  receiver: joiner.documents
- sender: pptx_converter.documents
  receiver: joiner.documents
- sender: joiner.documents
  receiver: splitter.documents
- sender: splitter.documents
  receiver: joiner_xlsx.documents
- sender: xlsx_converter.documents
  receiver: joiner_xlsx.documents
- sender: csv_converter.documents
  receiver: joiner_xlsx.documents
- sender: joiner_xlsx.documents
  receiver: document_embedder.documents
- sender: document_embedder.documents
  receiver: writer.documents

inputs:  # Define the inputs for your pipeline
  files:                            # This component will receive the files to index as input
  - file_classifier.sources

max_runs_per_component: 100

metadata: {}
        """
        }
    )


@pytest.fixture
async def index_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> IndexResource:
    """Create an IndexResource instance for testing."""
    return IndexResource(client=client, workspace=test_workspace)


@pytest.fixture
def default_index_name() -> str:
    return "test-index"


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
        name=default_index_name, yaml_config=config["config_yaml"], description="Test index description"
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
        await index_resource.create(name=index_name, yaml_config=config["config_yaml"])

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
        assert first_page.data[0].pipeline_index_id != second_page.data[0].pipeline_index_id


@pytest.mark.asyncio
async def test_get_index(
    index_resource: IndexResource,
    valid_index_config: str,
    default_index_name: str,
) -> None:
    """Test getting a single index by name."""
    # Create an index to retrieve
    config = json.loads(valid_index_config)
    await index_resource.create(name=default_index_name, yaml_config=config["config_yaml"])

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
    await index_resource.create(name=original_name, yaml_config=config["config_yaml"])

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


@pytest.mark.asyncio
async def test_delete_index(
    index_resource: IndexResource,
    valid_index_config: str,
) -> None:
    """Test deleting an index."""
    index_name = "test-delete-index"

    # Create an index to delete
    config = json.loads(valid_index_config)
    await index_resource.create(name=index_name, yaml_config=config["config_yaml"])

    # Verify the index exists
    index: Index = await index_resource.get(index_name=index_name)
    assert index.name == index_name

    # Delete the index
    await index_resource.delete(index_name=index_name)

    # Verify the index no longer exists
    with pytest.raises(ResourceNotFoundError):
        await index_resource.get(index_name=index_name)


@pytest.mark.asyncio
async def test_deploy_index_success(
    index_resource: IndexResource,
    valid_index_config: str,
) -> None:
    """Test successful index deployment."""
    index_name = "test-deploy-index"

    # Create an index to deploy
    config = json.loads(valid_index_config)
    await index_resource.create(name=index_name, yaml_config=config["config_yaml"])

    # Deploy the index
    result = await index_resource.deploy(index_name=index_name)

    # Verify deployment was successful
    assert isinstance(result, PipelineValidationResult)
    assert result.valid is True


@pytest.mark.asyncio
async def test_deploy_nonexistent_index(
    index_resource: IndexResource,
) -> None:
    """Test deploying a non-existent index."""
    non_existent_name = "non-existent-deploy-index"

    # Deploy a non-existent index
    result = await index_resource.deploy(index_name=non_existent_name)

    # Verify deployment failed with appropriate error
    assert isinstance(result, PipelineValidationResult)
    assert result.valid is False
    assert len(result.errors) > 0
