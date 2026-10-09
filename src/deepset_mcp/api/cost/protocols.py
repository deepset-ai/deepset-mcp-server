# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Literal, Protocol

from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals


class CostResourceProtocol(Protocol):
    """Protocol defining the implementation for CostResource."""

    async def totals(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostTotals:
        """Read the workspace's LLM cost totals."""
        ...

    async def over_time(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostOverTime:
        """Read the workspace's LLM cost per UTC day."""
        ...

    async def breakdown(
        self,
        group_by: CostGroupBy,
        pipeline_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort_by: CostSortBy | None = None,
        sort_order: Literal["ASC", "DESC"] | None = None,
        limit: int = 10,
        page_number: int = 1,
    ) -> CostBreakdown:
        """Read the workspace's LLM cost grouped by a dimension."""
        ...
