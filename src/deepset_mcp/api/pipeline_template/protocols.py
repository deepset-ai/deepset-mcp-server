# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.pipeline_template.models import PipelineTemplate
from deepset_mcp.api.shared_models import PaginatedResponse


class PipelineTemplateResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineTemplateResource."""

    async def get_template(self, template_name: str) -> PipelineTemplate:
        """Fetch a single pipeline template by its name."""
        ...

    async def list(
        self,
        limit: int = 10,
        after: str | None = None,
        field: str = "created_at",
        order: str = "DESC",
        filter: str | None = None,
    ) -> PaginatedResponse[PipelineTemplate]:
        """Lists pipeline templates and returns the first page of results with pagination support."""
        ...
