# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for CostResource.

They run against a freshly created workspace, which has no usage, so they check the request shape and
response parsing rather than the figures.
"""

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.cost.models import CostBreakdown, CostOverTime, CostTotals
from deepset_mcp.api.exceptions import ResourceNotFoundError

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_totals_of_an_empty_workspace(client: AsyncDeepsetClient, test_workspace: str) -> None:
    totals = await client.cost(test_workspace).totals()

    assert isinstance(totals, CostTotals)
    assert totals.total_requests == 0
    assert totals.currency == "USD"


@pytest.mark.asyncio
async def test_over_time_and_breakdown_of_an_empty_workspace(client: AsyncDeepsetClient, test_workspace: str) -> None:
    over_time = await client.cost(test_workspace).over_time(start_date="2026-01-01T00:00:00Z")
    breakdown = await client.cost(test_workspace).breakdown(group_by="model", limit=5)

    assert isinstance(over_time, CostOverTime)
    assert over_time.data == []
    assert isinstance(breakdown, CostBreakdown)
    assert breakdown.data == []
    assert breakdown.has_more is False


@pytest.mark.asyncio
async def test_unknown_pipeline_raises_not_found(client: AsyncDeepsetClient, test_workspace: str) -> None:
    with pytest.raises(ResourceNotFoundError):
        await client.cost(test_workspace).totals(pipeline_name="does-not-exist")
