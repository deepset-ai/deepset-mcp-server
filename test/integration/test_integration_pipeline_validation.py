import os

import pytest
from dotenv import load_dotenv

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.pipeline.resource import PipelineResource

pytestmark = pytest.mark.integration
load_dotenv()


@pytest.mark.asyncio
async def test_validation_valid_yaml(
    pipeline_resource: PipelineResource,
) -> None:
    """Test validating a valid pipeline YAML configuration."""
    # Create a valid YAML config
    valid_yaml = """
components:
  openai_generator:
    type: haystack.components.generators.openai.OpenAIGenerator
    init_parameters:
      api_key: {"type": "env_var", "env_vars": ["OPENAI_API_KEY"], "strict": false}
      model: "gpt-4o-mini"
      generation_kwargs:
        temperature: 0.1
        max_tokens: 300

inputs:
  query:
    - "openai_generator.prompt"

outputs:
  answers: "openai_generator.replies"
"""

    # Validate the YAML
    result = await pipeline_resource.validate(yaml_config=valid_yaml)

    # Check that validation succeeded
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

    # Validate the YAML
    result = await pipeline_resource.validate(yaml_config=invalid_yaml)

    # Check that validation failed with errors
    assert result.valid is False
    assert len(result.errors) > 0
    
    # Print the errors for debugging
    print(f"Validation errors: {[f'{e.code}: {e.message}' for e in result.errors]}")


@pytest.mark.asyncio
async def test_validation_syntax_error(
    pipeline_resource: PipelineResource,
) -> None:
    """Test validating a YAML with syntax errors."""
    # Create a YAML with syntax errors
    invalid_yaml_syntax = """
components:
  openai_generator:
    type: haystack.components.generators.openai.OpenAIGenerator
    init_parameters
      api_key: # Missing colon
"""

    # Validate the YAML and expect an exception
    with pytest.raises(ValueError):
        await pipeline_resource.validate(yaml_config=invalid_yaml_syntax)
