# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import Any

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.config import DEFAULT_CLIENT_HEADER, DOCS_SEARCH_TOOL_NAME
from deepset_mcp.initialize_embedding_model import get_initialized_model
from deepset_mcp.tool_models import DeepsetDocsConfig, MemoryType, ToolConfig
from deepset_mcp.tools.custom_components import (
    get_latest_custom_component_installation_logs as get_latest_custom_component_installation_logs_tool,
    list_custom_component_installations as list_custom_component_installations_tool,
)
from deepset_mcp.tools.doc_search import search_docs as search_docs_tool
from deepset_mcp.tools.haystack_service import (
    get_component_definition as get_component_definition_tool,
    get_custom_components as get_custom_components_tool,
    list_component_families as list_component_families_tool,
    search_component_definition as search_component_definition_tool,
)
from deepset_mcp.tools.indexes import (
    create_index as create_index_tool,
    deploy_index as deploy_index_tool,
    get_index as get_index_tool,
    list_indexes as list_indexes_tool,
    update_index as update_index_tool,
)
from deepset_mcp.tools.object_store import create_get_from_object_store, create_get_slice_from_object_store
from deepset_mcp.tools.pipeline import (
    create_pipeline as create_pipeline_tool,
    deploy_pipeline as deploy_pipeline_tool,
    get_pipeline as get_pipeline_tool,
    get_pipeline_logs as get_pipeline_logs_tool,
    list_pipelines as list_pipelines_tool,
    search_pipeline as search_pipeline_tool,
    update_pipeline as update_pipeline_tool,
    validate_pipeline as validate_pipeline_tool,
)
from deepset_mcp.tools.pipeline_template import (
    get_template as get_pipeline_template_tool,
    list_templates as list_pipeline_templates_tool,
    search_templates as search_pipeline_templates_tool,
)
from deepset_mcp.tools.secrets import get_secret as get_secret_tool, list_secrets as list_secrets_tool
from deepset_mcp.tools.workspace import (
    create_workspace as create_workspace_tool,
    get_workspace as get_workspace_tool,
    list_workspaces as list_workspaces_tool,
)


def get_docs_search_tool(config: DeepsetDocsConfig) -> Callable[..., Any]:
    """Get a docs search tool configured with the provided config."""

    async def search_docs(query: str) -> str:
        """Search the deepset platform documentation.

        This tool allows you to search through deepset's official documentation to find
        information about features, API usage, best practices, and troubleshooting guides.
        Use this when you need to look up specific deepset functionality or help users
        understand how to use deepset features.

        :param query: The search query to execute against the documentation.
        :returns: The formatted search results from the documentation.
        """
        async with AsyncDeepsetClient(api_key=config.api_key, transport_config=DEFAULT_CLIENT_HEADER) as client:
            response = await search_docs_tool(
                client=client,
                workspace=config.workspace_name,
                pipeline_name=config.pipeline_name,
                query=query,
            )
        return response

    return search_docs


TOOL_REGISTRY: dict[str, tuple[Callable[..., Any], ToolConfig]] = {
    # Workspace tools
    "list_pipelines": (
        list_pipelines_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "create_pipeline": (
        create_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.BOTH,
            custom_args={"skip_validation_errors": True},
        ),
    ),
    "update_pipeline": (
        update_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.BOTH,
            custom_args={"skip_validation_errors": True},
        ),
    ),
    "get_pipeline": (
        get_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "deploy_pipeline": (
        deploy_pipeline_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"wait_for_deployment": True, "timeout_seconds": 600, "poll_interval": 5},
        ),
    ),
    "validate_pipeline": (
        validate_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "get_pipeline_logs": (
        get_pipeline_logs_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_pipeline": (
        search_pipeline_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_indexes": (
        list_indexes_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_index": (
        get_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "create_index": (
        create_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "update_index": (
        update_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.BOTH),
    ),
    "deploy_index": (
        deploy_index_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_templates": (
        list_pipeline_templates_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"field": "created_at", "order": "DESC", "limit": 100},
        ),
    ),
    "get_template": (
        get_pipeline_template_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_templates": (
        search_pipeline_templates_tool,
        ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.EXPLORABLE,
            custom_args={"model": get_initialized_model()},
        ),
    ),
    "list_custom_component_installations": (
        list_custom_component_installations_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_latest_custom_component_installation_logs": (
        get_latest_custom_component_installation_logs_tool,
        ToolConfig(needs_client=True, needs_workspace=True, memory_type=MemoryType.EXPLORABLE),
    ),
    # Non-workspace tools
    "list_component_families": (
        list_component_families_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "get_component_definition": (
        get_component_definition_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "search_component_definitions": (
        search_component_definition_tool,
        ToolConfig(
            needs_client=True, memory_type=MemoryType.EXPLORABLE, custom_args={"model": get_initialized_model()}
        ),
    ),
    "get_custom_components": (
        get_custom_components_tool,
        ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE),
    ),
    "list_secrets": (list_secrets_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_secret": (get_secret_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "list_workspaces": (list_workspaces_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_workspace": (get_workspace_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "create_workspace": (create_workspace_tool, ToolConfig(needs_client=True, memory_type=MemoryType.EXPLORABLE)),
    "get_from_object_store": (create_get_from_object_store, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
    "get_slice_from_object_store": (create_get_slice_from_object_store, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
    DOCS_SEARCH_TOOL_NAME: (get_docs_search_tool, ToolConfig(memory_type=MemoryType.NO_MEMORY)),
}

ALL_DEEPSET_TOOLS = set(TOOL_REGISTRY.keys())
