# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline.models import DeepsetPipeline, DeepsetSearchResponse, DeepsetStreamEvent, PipelineList
from deepset_mcp.api.pipeline.resource import PipelineResource
from test.integration.test_integration_pipeline_logs import wait_for_pipeline_deployment

pytestmark = pytest.mark.integration


@pytest.fixture
async def pipeline_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> PipelineResource:
    """Create a PipelineResource instance for testing."""
    return PipelineResource(client=client, workspace=test_workspace)


@pytest.fixture
def sample_yaml_config() -> str:
    """Return a sample YAML configuration for testing."""
    return """
components:
  openai_generator:
    type: haystack.components.generators.openai.OpenAIGenerator
    init_parameters:
      api_key: {"type": "env_var", "env_vars": ["OPENAI_API_KEY"], "strict": false}
      model: "gpt-4o-mini"
      generation_kwargs:
        temperature: 0.1
        max_tokens: 300

  prompt_builder:
    type: haystack.components.builders.prompt_builder.PromptBuilder
    init_parameters:
      template: |
        Answer the following question: {{question}}

        Answer:

  answer_builder:
    type: haystack.components.builders.answer_builder.AnswerBuilder
    init_parameters: {}

connections:
  - sender: prompt_builder.prompt
    receiver: openai_generator.prompt
  - sender: openai_generator.replies
    receiver: answer_builder.replies

inputs:
  query:
    - "prompt_builder.question"
    - "answer_builder.query"

outputs:
  answers: "answer_builder.answers"
"""


@pytest.mark.asyncio
async def test_create_pipeline(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test creating a new pipeline."""
    pipeline_name = "test-pipeline"

    # Create a new pipeline
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Verify the pipeline was created by retrieving it
    pipeline: DeepsetPipeline = await pipeline_resource.get(pipeline_name=pipeline_name)

    assert pipeline.name == pipeline_name
    assert pipeline.yaml_config == sample_yaml_config


@pytest.mark.asyncio
async def test_list_pipelines(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test listing pipelines with pagination."""
    # Create multiple test pipelines
    pipeline_names = []
    for i in range(3):
        pipeline_name = f"test-list-pipeline-{i}"
        pipeline_names.append(pipeline_name)
        await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Test listing without pagination
    pipelines_list = await pipeline_resource.list(limit=10)
    assert isinstance(pipelines_list, PipelineList)
    assert len(pipelines_list.data) == 3

    # Verify our created pipelines are in the list
    retrieved_names = [p.name for p in pipelines_list.data]
    for name in pipeline_names:
        assert name in retrieved_names

    # Test pagination
    if len(pipelines_list.data) > 1:
        # Get the first page with 1 item
        first_page = await pipeline_resource.list(limit=1)
        assert isinstance(first_page, PipelineList)
        assert len(first_page.data) == 1
        assert isinstance(first_page.data[0], DeepsetPipeline)

        # Get the second page
        second_page = await pipeline_resource.list(page_number=2, limit=1)
        assert isinstance(second_page, PipelineList)
        assert len(second_page.data) == 1
        assert isinstance(second_page.data[0], DeepsetPipeline)

        # Verify they're different pipelines
        assert first_page.data[0].id != second_page.data[0].id


@pytest.mark.asyncio
async def test_get_pipeline(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test getting a single pipeline by name."""
    pipeline_name = "test-get-pipeline"

    # Create a pipeline to retrieve
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Test getting with YAML config
    pipeline_with_yaml: DeepsetPipeline = await pipeline_resource.get(pipeline_name=pipeline_name, include_yaml=True)
    assert pipeline_with_yaml.name == pipeline_name
    assert pipeline_with_yaml.yaml_config == sample_yaml_config

    # Test getting without YAML config
    pipeline_without_yaml: DeepsetPipeline = await pipeline_resource.get(
        pipeline_name=pipeline_name, include_yaml=False
    )
    assert pipeline_without_yaml.name == pipeline_name
    assert pipeline_without_yaml.yaml_config is None


@pytest.mark.asyncio
async def test_update_pipeline(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test updating an existing pipeline's name and config."""
    original_name = "test-update-pipeline-original"
    updated_name = "test-update-pipeline-updated"

    # Create a pipeline to update
    await pipeline_resource.create(name=original_name, yaml_config=sample_yaml_config)

    # Update the pipeline name
    await pipeline_resource.update(
        pipeline_name=original_name,
        updated_pipeline_name=updated_name,
    )

    # Verify the name was updated
    updated_pipeline: DeepsetPipeline = await pipeline_resource.get(pipeline_name=updated_name)
    assert updated_pipeline.name == updated_name

    # Update the pipeline config
    modified_yaml = sample_yaml_config.replace("temperature: 0.1", "temperature: 0.2")
    await pipeline_resource.update(
        pipeline_name=updated_name,
        yaml_config=modified_yaml,
    )

    # Verify the config was updated
    updated_pipeline = await pipeline_resource.get(pipeline_name=updated_name)
    assert updated_pipeline.yaml_config == modified_yaml


@pytest.mark.asyncio
async def test_get_nonexistent_pipeline(
    pipeline_resource: PipelineResource,
) -> None:
    """Test error handling when getting a non-existent pipeline."""
    non_existent_name = "non-existent-pipeline"

    # Trying to get a non-existent pipeline should raise an exception
    with pytest.raises(ResourceNotFoundError):
        await pipeline_resource.get(pipeline_name=non_existent_name)


@pytest.mark.asyncio
async def test_validation_valid_yaml(pipeline_resource: PipelineResource, sample_yaml_config: str) -> None:
    result = await pipeline_resource.validate(yaml_config=sample_yaml_config)

    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_validation_invalid_yaml(
    pipeline_resource: PipelineResource,
) -> None:
    """Test validating an invalid pipeline YAML configuration."""
    # Create an invalid YAML with missing required fields
    invalid_yaml = """
components:
  openai_generator:
    # Missing 'type' field
    init_parameters:
      api_key: {"type": "env_var", "env_vars": ["OPENAI_API_KEY"], "strict": false}
      model: "gpt-4o-mini"

inputs:
  query:
    - "openai_generator.prompt"

outputs:
  answers: "openai_generator.replies"
"""

    result = await pipeline_resource.validate(yaml_config=invalid_yaml)

    # Check that validation failed with errors
    assert result.valid is False
    assert len(result.errors) > 0

    assert result.errors[0].code == "PIPELINE_SCHEMA_ERROR"


@pytest.mark.asyncio
async def test_validation_syntax_error(
    pipeline_resource: PipelineResource,
) -> None:
    """Test validating a YAML with syntax errors."""
    invalid_yaml_syntax = """
components:
  openai_generator:
    type: haystack.components.generators.openai.OpenAIGenerator
    init_parameters
      api_key:
"""

    resp = await pipeline_resource.validate(yaml_config=invalid_yaml_syntax)

    assert resp.valid is False
    assert resp.errors[0].code == "YAML_ERROR"


@pytest.mark.asyncio
async def test_deploy_pipeline_success(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test successful pipeline deployment."""
    pipeline_name = "test-deploy-pipeline"

    # Create a pipeline to deploy
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Deploy the pipeline
    result = await pipeline_resource.deploy(pipeline_name=pipeline_name)

    # Verify deployment was successful
    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_deploy_nonexistent_pipeline(
    pipeline_resource: PipelineResource,
) -> None:
    """Test deploying a non-existent pipeline."""
    non_existent_name = "non-existent-deploy-pipeline"

    # Deploy a non-existent pipeline
    result = await pipeline_resource.deploy(pipeline_name=non_existent_name)

    # Should return validation errors indicating the pipeline doesn't exist
    assert result.valid is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_delete_pipeline(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test deleting a pipeline."""
    pipeline_name = "test-delete-pipeline"

    # Create a pipeline to delete
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Verify the pipeline exists
    pipeline = await pipeline_resource.get(pipeline_name=pipeline_name)
    assert pipeline.name == pipeline_name

    # Delete the pipeline
    result = await pipeline_resource.delete(pipeline_name=pipeline_name)
    assert result.success is True
    assert result.message == "Pipeline deleted successfully."

    # Verify the pipeline no longer exists
    with pytest.raises(ResourceNotFoundError):
        await pipeline_resource.get(pipeline_name=pipeline_name)


@pytest.mark.asyncio
async def test_delete_nonexistent_pipeline(
    pipeline_resource: PipelineResource,
) -> None:
    """Test deleting a non-existent pipeline."""
    non_existent_name = "non-existent-delete-pipeline"

    # Trying to delete a non-existent pipeline should raise an exception
    with pytest.raises(ResourceNotFoundError):
        await pipeline_resource.delete(pipeline_name=non_existent_name)


@pytest.mark.asyncio
@pytest.mark.extra_slow
async def test_search_pipeline(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test basic search functionality with a pipeline."""
    pipeline_name = "test-search-pipeline"

    # Create a pipeline for search
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Deploy the pipeline so it can be used for search
    await pipeline_resource.deploy(pipeline_name=pipeline_name)

    # We need to wait for the deployment to finish before we can proceed
    await wait_for_pipeline_deployment(pipeline_name=pipeline_name, pipeline_resource=pipeline_resource)

    # Perform a basic search
    result = await pipeline_resource.search(
        pipeline_name=pipeline_name,
        query="What is artificial intelligence?",
    )

    # Verify the structure of results
    assert isinstance(result, DeepsetSearchResponse)
    assert isinstance(result.answers, list)


@pytest.mark.asyncio
@pytest.mark.extra_slow
async def test_search_pipeline_with_stream(
    pipeline_resource: PipelineResource,
    sample_yaml_config: str,
) -> None:
    """Test basic search functionality with a pipeline."""
    pipeline_name = "test-search-pipeline"

    # Create a pipeline for search
    await pipeline_resource.create(name=pipeline_name, yaml_config=sample_yaml_config)

    # Deploy the pipeline so it can be used for search
    await pipeline_resource.deploy(pipeline_name=pipeline_name)

    await wait_for_pipeline_deployment(pipeline_name=pipeline_name, pipeline_resource=pipeline_resource)

    # Perform a basic search
    result = pipeline_resource.search_stream(pipeline_name=pipeline_name, query="What is artificial intelligence?")
    events = []
    async for event in result:
        events.append(event)
        assert isinstance(event, DeepsetStreamEvent)

    # Check if the last event contains the full response
    assert len(events) > 1
    last_event = events[-1]
    assert last_event.result is not None
    full_result = last_event.result
    assert isinstance(full_result, DeepsetSearchResponse)
    assert len(full_result.answers) == 1
    assert full_result.answers[0].answer != ""
