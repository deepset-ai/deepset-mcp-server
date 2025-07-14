# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.indexes.models import Index, IndexList
from deepset_mcp.api.pipeline.models import PipelineValidationResult


class IndexResourceProtocol(Protocol):
    """Protocol defining the implementation for IndexResource."""

    async def list(self, limit: int = 10, page_number: int = 1) -> IndexList:
        """List indexes in the configured workspace."""
        ...

    async def get(self, index_name: str) -> Index:
        """Fetch a single index by its name."""
        ...

    async def create(self, name: str, yaml_config: str, description: str | None = None) -> Index:
        """Create a new index with the given name and configuration.

        :param name: Name of the index
        :param yaml_config: YAML configuration for the index
        :param description: Optional description for the index
        :returns: Created index details
        """
        ...

    async def update(
        self, index_name: str, updated_index_name: str | None = None, yaml_config: str | None = None
    ) -> Index:
        """Update name and/or configuration of an existing index.

        :param index_name: Name of the index to update
        :param updated_index_name: Optional new name for the index
        :param yaml_config: Optional new YAML configuration
        :returns: Updated index details
        """
        ...

    async def deploy(self, index_name: str) -> PipelineValidationResult:
        """Deploy an index to production.

        :param index_name: Name of the index to deploy.
        :returns: PipelineValidationResult containing deployment status and any errors.
        """
        ...

    async def delete(self, index_name: str) -> None:
        """Delete an index.

        :param index_name: Name of the index to delete.
        """
        ...
