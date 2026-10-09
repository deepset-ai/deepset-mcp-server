# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for CostResource."""

from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.cost.models import CostBreakdown, CostOverTime, CostTotals
from deepset_mcp.api.cost.resource import CostResource
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import DeepsetPipeline
from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.api.workspace.models import Workspace
from test.unit.conftest import BaseFakeClient

WORKSPACE_NAME = "my-workspace"
WORKSPACE_UUID = "76d361b5-a551-40e3-a5c9-fdbc20028021"
PIPELINE_NAME = "my-pipeline"
PIPELINE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ORGANIZATION_UUID = "0b5e1b5a-1111-2222-3333-444444444444"

STATS = f"v2/cost/organizations/{ORGANIZATION_UUID}/stats"
ME = {"user_id": "u-1", "organization": {"organization_id": ORGANIZATION_UUID, "name": "acme"}}


def totals_dict() -> dict[str, Any]:
    return {
        "total_cost": 12.5,
        "total_tokens": 1000,
        "total_requests": 10,
        "avg_cost_per_request": 1.25,
        "priced_generation_count": 18,
        "unpriced_generation_count": 2,
        "pending_generation_count": 0,
        "unpriced_tokens": 100,
        "pending_tokens": 0,
        "is_cost_complete": False,
        "unpriced_models": [
            {"model": "my-model", "generation_count": 2, "total_tokens": 100, "last_seen_at": "2026-10-01T00:00:00Z"}
        ],
        "currency": "USD",
    }


def breakdown_dict() -> dict[str, Any]:
    return {
        "group_by": "pipeline",
        "data": [
            {
                "key": PIPELINE_UUID,
                "label": PIPELINE_NAME,
                "cost_total": 10.0,
                "total_tokens": 800,
                "total_requests": 8,
                "workspace_id": WORKSPACE_UUID,
                "workspace_name": WORKSPACE_NAME,
            }
        ],
        "total": 3,
        "has_more": True,
    }


class FakeWorkspaceResource:
    async def get(self, workspace_name: str) -> Workspace:
        return Workspace(
            name=workspace_name,
            workspace_id=UUID(WORKSPACE_UUID),
            languages={},
            default_idle_timeout_in_seconds=43200,
        )


class FakePipelineResource:
    def __init__(self, result: DeepsetPipeline | Exception) -> None:
        self._result = result
        self.calls: list[str] = []

    async def get(self, pipeline_name: str) -> DeepsetPipeline:
        self.calls.append(pipeline_name)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeCostClient(BaseFakeClient):
    """Resolves the workspace and pipeline through fakes and answers HTTP calls from a dict."""

    def __init__(self, http_responses: dict[str, Any], pipeline: DeepsetPipeline | Exception | None = None) -> None:
        super().__init__(responses={"v1/me": ME, **http_responses})
        self.pipeline_resource = FakePipelineResource(
            pipeline
            if pipeline is not None
            else DeepsetPipeline.model_validate(
                {
                    "pipeline_id": PIPELINE_UUID,
                    "name": PIPELINE_NAME,
                    "status": "DEPLOYED",
                    "service_level": "PRODUCTION",
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": {"user_id": "u-001", "given_name": "Test", "family_name": "User"},
                }
            )
        )

    def workspaces(self) -> FakeWorkspaceResource:  # type: ignore[override]
        return FakeWorkspaceResource()

    def pipelines(self, workspace: str) -> FakePipelineResource:  # type: ignore[override]
        return self.pipeline_resource

    def stats_request(self) -> dict[str, Any]:
        return next(r for r in self.requests if r["endpoint"].startswith(STATS))


def resource(client: FakeCostClient) -> CostResource:
    return CostResource(client=client, workspace=WORKSPACE_NAME)


@pytest.mark.asyncio
async def test_totals_resolves_organization_and_workspace_ids() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    totals = await resource(client).totals()

    assert isinstance(totals, CostTotals)
    assert totals.is_cost_complete is False
    assert totals.unpriced_models[0].model == "my-model"
    request = client.stats_request()
    assert request["endpoint"] == f"{STATS}/totals"
    assert request["params"] == {"workspace_id": WORKSPACE_UUID}
    assert client.pipeline_resource.calls == []


@pytest.mark.asyncio
async def test_totals_filters_by_pipeline_and_dates() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    await resource(client).totals(
        pipeline_name=PIPELINE_NAME, start_date="2026-09-01T00:00:00Z", end_date="2026-10-01T00:00:00Z"
    )

    assert client.stats_request()["params"] == {
        "workspace_id": WORKSPACE_UUID,
        "pipeline_id": PIPELINE_UUID,
        "start_date": "2026-09-01T00:00:00Z",
        "end_date": "2026-10-01T00:00:00Z",
    }
    assert client.pipeline_resource.calls == [PIPELINE_NAME]


@pytest.mark.asyncio
async def test_over_time() -> None:
    client = FakeCostClient(
        {f"{STATS}/cost-over-time": {"data": [{"date": "2026-10-01T00:00:00Z", "cost_total": None}]}}
    )

    over_time = await resource(client).over_time()

    assert isinstance(over_time, CostOverTime)
    assert over_time.data[0].cost_total is None
    assert client.stats_request()["endpoint"] == f"{STATS}/cost-over-time"


@pytest.mark.asyncio
async def test_breakdown_sends_grouping_sorting_and_paging() -> None:
    client = FakeCostClient({f"{STATS}/breakdown": breakdown_dict()})

    breakdown = await resource(client).breakdown(
        group_by="pipeline", sort_by="total_tokens", sort_order="ASC", limit=50, page_number=2
    )

    assert isinstance(breakdown, CostBreakdown)
    assert breakdown.data[0].label == PIPELINE_NAME
    assert breakdown.has_more is True
    assert client.stats_request()["params"] == {
        "workspace_id": WORKSPACE_UUID,
        "group_by": "pipeline",
        "sort_by": "total_tokens",
        "sort_order": "ASC",
        "limit": 50,
        "page_number": 2,
    }


@pytest.mark.asyncio
async def test_unknown_pipeline_raises_not_found() -> None:
    client = FakeCostClient({}, pipeline=ResourceNotFoundError())

    with pytest.raises(ResourceNotFoundError):
        await resource(client).totals(pipeline_name="gone")


@pytest.mark.asyncio
async def test_forbidden_carries_the_api_error_message() -> None:
    forbidden = TransportResponse(text="", status_code=403, json={"errors": ["Forbidden"]})
    client = FakeCostClient({f"{STATS}/totals": forbidden})

    with pytest.raises(UnexpectedAPIError) as exc_info:
        await resource(client).totals()

    assert exc_info.value.status_code == 403
    assert str(exc_info.value) == "Forbidden (Status Code: 403)"


@pytest.mark.asyncio
async def test_me_without_organization_raises() -> None:
    client = FakeCostClient({"v1/me": {"user_id": "u-1"}})

    with pytest.raises(UnexpectedAPIError):
        await resource(client).totals()
