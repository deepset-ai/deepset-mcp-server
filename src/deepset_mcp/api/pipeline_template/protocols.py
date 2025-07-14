# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.pipeline_template.models import PipelineTemplate, PipelineTemplateList


class PipelineTemplateResourceProtocol(Protocol):
    """Protocol defining the implementation for PipelineTemplateResource."""

    async def get_template(self, template_name: str) -> PipelineTemplate:
        """Fetch a single pipeline template by its name."""
        ...

    async def list_templates(
        self, limit: int = 100, field: str = "created_at", order: str = "DESC", filter: str | None = None
    ) -> PipelineTemplateList:
        """List pipeline templates in the configured workspace."""
        ...
