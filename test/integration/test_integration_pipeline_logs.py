# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineLogList
from deepset_mcp.api.pipeline.resource import PipelineResource

pytestmark = pytest.mark.integration


@pytest.fixture
async def pipeline_resource(
    client: AsyncDeepsetClient,
    test_workspace: str,
) -> PipelineResource:
    """Create a PipelineResource instance for testing."""
    return PipelineResource(client=client, workspace=test_workspace)


@pytest.fixture
def simple_yaml_config() -> str:
    """Return a simple YAML configuration that should deploy quickly."""
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


async def wait_for_pipeline_deployment(
    pipeline_resource: PipelineResource,
    pipeline_name: str,
    timeout_seconds: int = 300,
    poll_interval: int = 10,
) -> DeepsetPipeline:
    """
    Wait for a pipeline to reach DEPLOYED status by polling its status.

    Args:
        pipeline_resource: The pipeline resource to use for API calls
        pipeline_name: Name of the pipeline to monitor
        timeout_seconds: Maximum time to wait for deployment (default: 5 minutes)
        poll_interval: Time between status checks in seconds (default: 10 seconds)

    Returns:
        The deployed pipeline object

    Raises:
        TimeoutError: If the pipeline doesn't deploy within the timeout period
        Exception: If the pipeline deployment fails
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout_seconds:
            raise TimeoutError(
                f"Pipeline '{pipeline_name}' did not reach DEPLOYED status within {timeout_seconds} seconds"
            )

        # Get the current pipeline status
        pipeline = await pipeline_resource.get(pipeline_name=pipeline_name, include_yaml=False)

        if pipeline.status == "DEPLOYED":
            return pipeline
        elif pipeline.status == "FAILED":
            raise Exception(f"Pipeline '{pipeline_name}' deployment failed")

        # Wait before next poll
        await asyncio.sleep(poll_interval)


@pytest.mark.extra_slow
@pytest.mark.asyncio
async def test_get_logs_for_deployed_pipeline(
    pipeline_resource: PipelineResource,
    simple_yaml_config: str,
) -> None:
    """
    Test getting logs for a deployed pipeline.

    This test:
    1. Creates a valid pipeline
    2. Deploys the pipeline
    3. Waits for the pipeline to reach DEPLOYED status
    4. Fetches logs for the deployed pipeline
    """
    pipeline_name = "test-logs-pipeline"

    # Step 1: Create a pipeline
    await pipeline_resource.create(name=pipeline_name, yaml_config=simple_yaml_config)

    # Step 2: Deploy the pipeline
    deploy_result = await pipeline_resource.deploy(pipeline_name=pipeline_name)
    assert deploy_result.valid is True, f"Pipeline deployment failed: {deploy_result.errors}"

    # Step 3: Wait for the pipeline to be deployed
    deployed_pipeline = await wait_for_pipeline_deployment(
        pipeline_resource=pipeline_resource,
        pipeline_name=pipeline_name,
        timeout_seconds=300,  # 5 minutes timeout
        poll_interval=15,  # Check every 15 seconds
    )

    assert deployed_pipeline.status == "DEPLOYED"

    # Step 4: Get logs for the deployed pipeline
    logs = await pipeline_resource.get_logs(pipeline_name=pipeline_name)

    # Verify the response structure
    assert isinstance(logs, PipelineLogList)
    assert isinstance(logs.data, list)
    assert isinstance(logs.has_more, bool)
    assert isinstance(logs.total, int)

    # The pipeline should have at least some logs after deployment
    # Note: We can't guarantee specific log content, but we can verify the structure
    for log_entry in logs.data:
        assert hasattr(log_entry, "log_id")
        assert hasattr(log_entry, "message")
        assert hasattr(log_entry, "logged_at")
        assert hasattr(log_entry, "level")
        assert hasattr(log_entry, "origin")


@pytest.mark.asyncio
async def test_get_logs_for_non_deployed_pipeline(
    pipeline_resource: PipelineResource,
    simple_yaml_config: str,
) -> None:
    """
    Test getting logs for a pipeline that is created but not deployed.
    This should still work but may return empty or minimal logs.
    """
    pipeline_name = "test-logs-non-deployed-pipeline"

    # Create pipeline but do not deploy it
    await pipeline_resource.create(name=pipeline_name, yaml_config=simple_yaml_config)

    # Try to get logs for the non-deployed pipeline
    logs = await pipeline_resource.get_logs(pipeline_name=pipeline_name)

    # Should return a valid response structure even if empty
    assert isinstance(logs, PipelineLogList)
    assert isinstance(logs.data, list)
    assert isinstance(logs.has_more, bool)
    assert isinstance(logs.total, int)


@pytest.mark.extra_slow
@pytest.mark.asyncio
async def test_deployment_timeout_handling(
    pipeline_resource: PipelineResource,
    simple_yaml_config: str,
) -> None:
    """
    Test that our deployment polling handles timeouts correctly.
    This test uses a very short timeout to verify the timeout mechanism works.
    """
    pipeline_name = "test-timeout-pipeline"

    # Create and deploy pipeline
    await pipeline_resource.create(name=pipeline_name, yaml_config=simple_yaml_config)
    deploy_result = await pipeline_resource.deploy(pipeline_name=pipeline_name)
    assert deploy_result.valid is True

    # Test timeout with very short timeout (this should timeout unless deployment is very fast)
    with pytest.raises(TimeoutError, match="did not reach DEPLOYED status within 1 seconds"):
        await wait_for_pipeline_deployment(
            pipeline_resource=pipeline_resource,
            pipeline_name=pipeline_name,
            timeout_seconds=1,  # Very short timeout
            poll_interval=1,
        )
