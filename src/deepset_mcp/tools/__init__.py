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
    deploy_pipeline,
    get_pipeline,
    get_pipeline_logs,
    list_pipelines,
    search_pipeline,
    update_pipeline,
    validate_pipeline,
)
from .pipeline_template import get_template, list_templates, search_templates
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
    "create_pipeline",
    "update_pipeline",
    "validate_pipeline",
    "list_templates",
    "get_template",
    "search_templates",
    "get_secret",
    "list_secrets",
    "list_workspaces",
    "get_workspace",
]
