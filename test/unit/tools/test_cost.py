# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Literal

import pytest

from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals
from deepset_mcp.api.cost.protocols import CostResourceProtocol
from deepset_mcp.api.exceptions import RequestTimeoutError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.tools.cost import get_cost_breakdown, get_cost_over_time, get_cost_totals
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
PIPELINE = "my-pipeline"

TOTALS = CostTotals.model_validate(
    {
        "total_cost": 12.5,
        "total_tokens": 1000,
        "total_requests": 10,
        "avg_cost_per_request": 1.25,
        "is_cost_complete": True,
        "unpriced_models": [],
    }
)
OVER_TIME = CostOverTime.model_validate({"data": [{"date": "2026-10-01T00:00:00Z", "cost_total": 1.5}]})
BREAKDOWN = CostBreakdown.model_validate(
    {
        "group_by": "model",
        "data": [{"key": "gpt-5", "label": "gpt-5", "cost_total": 12.5, "total_tokens": 1000, "total_requests": 10}],
        "total": 1,
        "has_more": False,
    }
)


class FakeCostResource(CostResourceProtocol):
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, method: str, **kwargs: Any) -> None:
        self.calls.append((method, kwargs))
        if self._error is not None:
            raise self._error

    async def totals(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostTotals:
        self._record("totals", pipeline_name=pipeline_name, start_date=start_date, end_date=end_date)
        return TOTALS

    async def over_time(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostOverTime:
        self._record("over_time", pipeline_name=pipeline_name, start_date=start_date, end_date=end_date)
        return OVER_TIME

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
        self._record(
            "breakdown",
            group_by=group_by,
            pipeline_name=pipeline_name,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            page_number=page_number,
        )
        return BREAKDOWN


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeCostResource) -> None:
        super().__init__()
        self.resource = resource
        self.workspaces_used: list[str] = []

    def cost(self, workspace: str) -> FakeCostResource:
        self.workspaces_used.append(workspace)
        return self.resource


@pytest.mark.asyncio
async def test_get_cost_totals_passes_filters() -> None:
    client = FakeClient(FakeCostResource())

    result = await get_cost_totals(
        client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, start_date="2026-09-01T00:00:00Z"
    )

    assert result == TOTALS
    assert client.workspaces_used == [WORKSPACE]
    assert client.resource.calls == [
        ("totals", {"pipeline_name": PIPELINE, "start_date": "2026-09-01T00:00:00Z", "end_date": None})
    ]


@pytest.mark.asyncio
async def test_get_cost_over_time() -> None:
    client = FakeClient(FakeCostResource())

    result = await get_cost_over_time(client=client, workspace=WORKSPACE, end_date="2026-10-01T00:00:00Z")

    assert result == OVER_TIME
    assert client.resource.calls == [
        ("over_time", {"pipeline_name": None, "start_date": None, "end_date": "2026-10-01T00:00:00Z"})
    ]


@pytest.mark.asyncio
async def test_get_cost_breakdown_passes_grouping_sorting_and_paging() -> None:
    client = FakeClient(FakeCostResource())

    result = await get_cost_breakdown(
        client=client, workspace=WORKSPACE, group_by="model", sort_by="label", sort_order="ASC", limit=100
    )

    assert result == BREAKDOWN
    method, kwargs = client.resource.calls[0]
    assert method == "breakdown"
    assert kwargs["group_by"] == "model"
    assert kwargs["sort_by"] == "label"
    assert kwargs["sort_order"] == "ASC"
    assert kwargs["limit"] == 100
    assert kwargs["page_number"] == 1


@pytest.mark.asyncio
async def test_unknown_workspace() -> None:
    client = FakeClient(FakeCostResource(ResourceNotFoundError()))

    result = await get_cost_totals(client=client, workspace=WORKSPACE)

    assert result == f"Workspace '{WORKSPACE}' not found."


@pytest.mark.asyncio
async def test_unknown_pipeline_points_to_the_breakdown() -> None:
    client = FakeClient(FakeCostResource(ResourceNotFoundError()))

    result = await get_cost_over_time(client=client, workspace=WORKSPACE, pipeline_name="gone")

    assert isinstance(result, str)
    assert "pipeline 'gone' not found" in result
    assert "group_by='pipeline'" in result


@pytest.mark.asyncio
async def test_forbidden_explains_the_missing_permission() -> None:
    client = FakeClient(FakeCostResource(UnexpectedAPIError(status_code=403, message="Forbidden")))

    result = await get_cost_breakdown(client=client, workspace=WORKSPACE, group_by="pipeline")

    assert result == (
        f"Failed to get cost breakdown: the API key has no permission to read cost in workspace '{WORKSPACE}'."
    )


@pytest.mark.asyncio
async def test_timeout_suggests_a_shorter_range() -> None:
    client = FakeClient(FakeCostResource(RequestTimeoutError(method="GET", url="/x", timeout=30.0)))

    result = await get_cost_totals(client=client, workspace=WORKSPACE)

    assert result == "Failed to get cost totals: the request timed out. Try a shorter date range."


@pytest.mark.asyncio
async def test_other_api_errors_carry_the_message() -> None:
    client = FakeClient(FakeCostResource(UnexpectedAPIError(status_code=500, message="Server error")))

    result = await get_cost_totals(client=client, workspace=WORKSPACE)

    assert result == "Failed to get cost totals: Server error (Status Code: 500)"
