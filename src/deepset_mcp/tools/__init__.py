# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from .custom_components import get_latest_custom_component_installation_logs, list_custom_component_installations
from .doc_search import search_docs
from .haystack_service import (
    get_component_definition,
    get_custom_components,
    list_component_families,
    run_component,
    search_component_definition,
)
from .indexes import create_index, deploy_index, get_index, list_indexes, update_index, validate_index
from .object_store import create_get_from_object_store, create_get_slice_from_object_store
from .pipeline import (
    create_pipeline,
    create_pipeline_version,
    deploy_pipeline,
    get_pipeline,
    get_pipeline_logs,
    get_pipeline_version,
    list_pipeline_versions,
    list_pipelines,
    patch_pipeline_version,
    restore_pipeline_version,
    search_pipeline,
    search_pipeline_with_filters,
    search_pipeline_with_params,
    validate_pipeline,
)
from .pipeline_template import get_template, list_templates, search_templates
from .search_history import list_pipeline_search_history, list_search_history
from .secrets import get_secret, list_secrets
from .workspace import get_workspace, list_workspaces

__all__ = [
    "list_custom_component_installations",
    "get_latest_custom_component_installation_logs",
    "search_docs",
    "run_component",
    "get_custom_components",
    "get_component_definition",
    "search_component_definition",
    "list_component_families",
    "list_indexes",
    "deploy_index",
    "update_index",
    "create_index",
    "get_index",
    "validate_index",
    "create_get_from_object_store",
    "create_get_slice_from_object_store",
    "list_pipelines",
    "get_pipeline",
    "get_pipeline_logs",
    "deploy_pipeline",
    "search_pipeline",
    "search_pipeline_with_filters",
    "search_pipeline_with_params",
    "create_pipeline",
    "validate_pipeline",
    "list_pipeline_versions",
    "create_pipeline_version",
    "get_pipeline_version",
    "patch_pipeline_version",
    "restore_pipeline_version",
    "list_templates",
    "get_template",
    "search_templates",
    "list_search_history",
    "list_pipeline_search_history",
    "get_secret",
    "list_secrets",
    "list_workspaces",
    "get_workspace",
]
