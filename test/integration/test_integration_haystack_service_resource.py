# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.haystack_service.resource import HaystackServiceResource

pytestmark = pytest.mark.integration


@pytest.fixture
async def haystack_service_resource(
    client: AsyncDeepsetClient,
) -> HaystackServiceResource:
    """Create a PipelineResource instance for testing."""
    return HaystackServiceResource(client=client)


@pytest.mark.asyncio
async def test_get_component_schemas(
    haystack_service_resource: HaystackServiceResource,
) -> None:
    """Test for getting component schemas."""
    response = await haystack_service_resource.get_component_schemas()

    assert isinstance(response, dict)
    assert "component_schema" in response


@pytest.mark.asyncio
async def test_get_component_input_output(
    haystack_service_resource: HaystackServiceResource,
) -> None:
    """Test for getting component input/output schema."""
    response = await haystack_service_resource.get_component_input_output("Agent")

    assert isinstance(response, dict)
    assert "name" in response
    assert response["name"] == "Agent"
    assert "input" in response
    assert "output" in response


@pytest.mark.asyncio
async def test_run_component(
    haystack_service_resource: HaystackServiceResource,
) -> None:
    """Test for running a Haystack component."""
    response = await haystack_service_resource.run_component(
        component_type="haystack.components.builders.prompt_builder.PromptBuilder",
        init_params={"template": "Hello, {{name}}!"},
        input_data={"name": "deepset"},
        input_types={"name": "str"},
    )

    assert isinstance(response, dict)
    assert "prompt" in response
    assert response["prompt"] == "Hello, deepset!"


@pytest.mark.asyncio
async def test_run_component_with_workspace(
    haystack_service_resource: HaystackServiceResource,
) -> None:
    """Test for running a Haystack component in a specific workspace."""
    response = await haystack_service_resource.run_component(
        component_type="haystack.components.builders.prompt_builder.PromptBuilder",
        init_params={"template": "Hello, {{name}}!"},
        input_data={"name": "deepset"},
        input_types={"name": "str"},
        workspace="default",
    )

    assert isinstance(response, dict)
    assert "prompt" in response
    assert response["prompt"] == "Hello, deepset!"
