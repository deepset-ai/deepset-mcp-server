# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.initialize_embedding_model import get_initialized_model
from deepset_mcp.tools.haystack_service import (
    get_component_definition,
    get_custom_components,
    list_component_families,
    run_component,
    search_component_definition,
)
from deepset_mcp.tools.haystack_service_models import (
    ComponentDefinition,
    ComponentDefinitionList,
    ComponentFamilyList,
    ComponentSearchResults,
)
from deepset_mcp.tools.model_protocol import ModelProtocol

pytestmark = pytest.mark.integration


@pytest.fixture
def embedding_model() -> ModelProtocol:
    """Create an embedding model for testing search functionality."""
    return get_initialized_model()


@pytest.mark.asyncio
async def test_get_component_definition(client: AsyncDeepsetClient) -> None:
    """Test getting a specific component definition."""
    result = await get_component_definition(
        client=client, component_type="haystack.components.builders.prompt_builder.PromptBuilder"
    )

    assert isinstance(result, ComponentDefinition)
    assert result.component_type == "haystack.components.builders.prompt_builder.PromptBuilder"
    assert result.title is not None
    assert result.description is not None
    assert result.family is not None
    assert len(result.init_parameters) > 0

    # Check that input/output schemas are included
    assert result.input_schema is not None
    assert result.output_schema is not None


@pytest.mark.asyncio
async def test_get_component_definition_nonexistent(client: AsyncDeepsetClient) -> None:
    """Test getting a non-existent component definition."""
    result = await get_component_definition(client=client, component_type="nonexistent.component.Type")

    assert isinstance(result, str)
    assert "Component not found" in result


@pytest.mark.asyncio
async def test_search_component_definition(client: AsyncDeepsetClient, embedding_model: ModelProtocol) -> None:
    """Test searching for components by query."""
    result = await search_component_definition(client=client, query="prompt builder", model=embedding_model, top_k=3)

    assert isinstance(result, ComponentSearchResults)
    assert result.query == "prompt builder"
    assert result.total_found >= 0
    assert len(result.results) <= 3

    if result.results:
        for search_result in result.results:
            assert isinstance(search_result.component, ComponentDefinition)
            assert isinstance(search_result.similarity_score, float)
            assert 0.0 <= search_result.similarity_score <= 1.0


@pytest.mark.asyncio
async def test_search_component_definition_generator_query(
    client: AsyncDeepsetClient, embedding_model: ModelProtocol
) -> None:
    """Test searching for generator components."""
    result = await search_component_definition(
        client=client, query="generate text openai", model=embedding_model, top_k=5
    )

    assert isinstance(result, ComponentSearchResults)
    assert result.query == "generate text openai"
    assert result.total_found > 0

    # Should find OpenAI generator or similar components
    found_generator = False
    for search_result in result.results:
        if "generator" in search_result.component.component_type.lower():
            found_generator = True
            break

    assert found_generator, "Should find at least one generator component"


@pytest.mark.asyncio
async def test_list_component_families(client: AsyncDeepsetClient) -> None:
    """Test listing all component families."""
    result = await list_component_families(client=client)

    assert isinstance(result, ComponentFamilyList)
    assert result.total_count > 0
    assert len(result.families) > 0
    assert len(result.families) == result.total_count

    # Check for expected families
    family_names = [family.name for family in result.families]
    expected_families = ["builders", "generators", "retrievers"]

    for expected_family in expected_families:
        assert any(expected_family in family_name for family_name in family_names), (
            f"Expected to find family containing '{expected_family}'"
        )

    for family in result.families:
        assert family.name is not None
        assert family.description is not None


@pytest.mark.asyncio
async def test_get_custom_components(client: AsyncDeepsetClient) -> None:
    """Test getting custom components."""
    result = await get_custom_components(client=client)

    # This could be either a ComponentDefinitionList or a string message if no custom components exist
    if isinstance(result, ComponentDefinitionList):
        assert result.total_count >= 0
        assert len(result.components) == result.total_count

        for component in result.components:
            assert isinstance(component, ComponentDefinition)
            assert component.is_custom is True
            assert component.package_version is not None
    else:
        # Should be a string message about no custom components
        assert isinstance(result, str)
        assert "custom components" in result.lower()


@pytest.mark.asyncio
async def test_run_component_prompt_builder(client: AsyncDeepsetClient) -> None:
    """Test running a PromptBuilder component."""
    result = await run_component(
        client=client,
        component_type="haystack.components.builders.prompt_builder.PromptBuilder",
        init_params={"template": "Hello, {{name}}! How are you?"},
        input_data={"name": "World"},
        input_types={"name": "str"},
    )

    assert isinstance(result, dict)
    assert "prompt" in result
    assert result["prompt"] == "Hello, World! How are you?"


@pytest.mark.asyncio
async def test_run_component_prompt_builder_no_variables(client: AsyncDeepsetClient) -> None:
    """Test running a PromptBuilder component with no template variables."""
    result = await run_component(
        client=client,
        component_type="haystack.components.builders.prompt_builder.PromptBuilder",
        init_params={"template": "Static message"},
        input_data={},
        input_types={},
    )

    assert isinstance(result, dict)
    assert "prompt" in result
    assert result["prompt"] == "Static message"


@pytest.mark.asyncio
async def test_run_component_answer_builder(client: AsyncDeepsetClient) -> None:
    """Test running an AnswerBuilder component."""
    result = await run_component(
        client=client,
        component_type="haystack.components.builders.answer_builder.AnswerBuilder",
        init_params={},
        input_data={"query": "What is AI?", "replies": ["AI is artificial intelligence."]},
        input_types={"query": "str", "replies": "list[str]"},
    )

    assert isinstance(result, dict)
    assert "answers" in result
    assert isinstance(result["answers"], list)
    assert len(result["answers"]) > 0


@pytest.mark.asyncio
async def test_run_component_with_invalid_params(client: AsyncDeepsetClient) -> None:
    """Test running a component with invalid parameters."""
    result = await run_component(
        client=client,
        component_type="haystack.components.builders.prompt_builder.PromptBuilder",
        init_params={"invalid_param": "value"},
        input_data={"name": "World"},
        input_types={"name": "str"},
    )

    # Should return an error string
    assert isinstance(result, str)
    assert "Failed to run component" in result
