# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    """Configuration for how memory is provided to tools."""

    EXPLORABLE = "explorable"
    """The tool's output is stored in the object store and nested properties can be explored through using the object
    store tools.
    """

    REFERENCEABLE = "referenceable"
    """The tool can be called by referencing an object or object-property that was stored in the object store."""

    EXPLORABLE_AND_REFERENCEABLE = "explorable_and_referenceable"
    """The tool's output is stored in the object store and it can be called by reference."""

    NO_MEMORY = "no_memory"
    """The tool returns all outputs as is. It does not interact with the object store."""


@dataclass
class ExplorerConfig:
    """Overrides for 'RichExplorer' defaults. Fields left as 'None' fall back to the 'RichExplorer' default."""

    max_items: int | None = None
    """Overrides 'RichExplorer.max_items' for this tool."""

    max_string_length: int | None = None
    """Overrides 'RichExplorer.max_string_length' for this tool."""

    max_depth: int | None = None
    """Overrides 'RichExplorer.max_depth' for this tool."""

    max_search_matches: int | None = None
    """Overrides 'RichExplorer.max_search_matches' for this tool."""

    search_context_length: int | None = None
    """Overrides 'RichExplorer.search_context_length' for this tool."""

    def to_kwargs(self) -> dict[str, int]:
        """Builds the keyword arguments to override 'RichExplorer' defaults with.

        :returns: A dict of the non-'None' explorer override fields on this config.
        """
        overrides = {
            "max_items": self.max_items,
            "max_string_length": self.max_string_length,
            "max_depth": self.max_depth,
            "max_search_matches": self.max_search_matches,
            "search_context_length": self.search_context_length,
        }
        return {name: value for name, value in overrides.items() if value is not None}


@dataclass
class ToolConfig:
    """Configuration for tool registration.

    It allows users to define what arguments should be passed to the tool at registration time. These arguments will not
    be provided by the LLM as the tool will receive them programmatically through partial application.

    The configuration also determines if a tool should store outputs in the object store.
    """

    needs_client: bool = False
    """If the tool should receive a configured instance of the 'AsyncDeepsetClient' at tool-registration time."""

    needs_workspace: bool = False
    """If the tool should receive a static deepset workspace at tool-registration time."""

    memory_type: MemoryType = MemoryType.NO_MEMORY
    """The type of memory this tool should use."""

    custom_args: dict[str, Any] = field(default_factory=dict)
    """Any other arguments that should be passed to the tool at registration time instead of being passed by the LLM."""

    explorer_config: ExplorerConfig = field(default_factory=ExplorerConfig)
    """Overrides for the 'RichExplorer' defaults used by this tool's memory decorator."""


@dataclass
class DeepsetDocsConfig:
    """Configuration for deepset documentation search tool."""

    pipeline_name: str
    api_key: str
    workspace_name: str
