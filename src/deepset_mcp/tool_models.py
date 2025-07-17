# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    """Configuration for how memory is provided to tools."""

    EXPLORABLE = "explorable"
    REFERENCEABLE = "referenceable"
    BOTH = "both"
    NO_MEMORY = "no_memory"


@dataclass
class ToolConfig:
    """Configuration for tool registration."""

    needs_client: bool = False
    needs_workspace: bool = False
    memory_type: MemoryType = MemoryType.NO_MEMORY
    custom_args: dict[str, Any] = field(default_factory=dict)


class WorkspaceMode(StrEnum):
    """Configuration for how workspace is provided to tools."""

    STATIC = "static"  # workspace from env, no parameter in tool signature
    DYNAMIC = "dynamic"  # workspace as required parameter in tool signature


@dataclass
class DeepsetDocsConfig:
    """Configuration for deepset documentation search tool."""

    pipeline_name: str
    api_key: str
    workspace_name: str
