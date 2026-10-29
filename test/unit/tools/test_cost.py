# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Literal

import pytest

from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals
from deepset_mcp.api.cost.protocols import CostResourceProtocol
from deepset_mcp.api.cost.resource import (
    AmbiguousServiceError,
    OrganizationCostForbiddenError,
    PipelineLookupForbiddenError,
    ServiceLookupForbiddenError,
    ServiceNotFoundError,
    WorkspaceRequiredError,
)
from deepset_mcp.api.exceptions import BadRequestError, RequestTimeoutError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.tools.cost import get_cost_breakdown, get_cost_over_time, get_cost_totals
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
PIPELINE = "my-pipeline"
SERVICE = "Global Assistant"
API_KEY_ID = "5f0c6d55-9d57-4f0e-9a6e-0d2f6a1f7c11"

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
        self,
        pipeline_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        services: list[str] | None = None,
        providers: list[str] | None = None,
        api_keys: list[str] | None = None,
    ) -> CostTotals:
        self._record(
            "totals",
            pipeline_name=pipeline_name,
            start_date=start_date,
            end_date=end_date,
            services=services,
            providers=providers,
            api_keys=api_keys,
        )
        return TOTALS

    async def over_time(
        self,
        pipeline_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        services: list[str] | None = None,
        providers: list[str] | None = None,
        api_keys: list[str] | None = None,
    ) -> CostOverTime:
        self._record(
            "over_time",
            pipeline_name=pipeline_name,
            start_date=start_date,
            end_date=end_date,
            services=services,
            providers=providers,
            api_keys=api_keys,
        )
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
        services: list[str] | None = None,
        providers: list[str] | None = None,
        api_keys: list[str] | None = None,
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
            services=services,
            providers=providers,
            api_keys=api_keys,
        )
        return BREAKDOWN


class FakeClient(BaseFakeClient):
    def __init__(self, resource: FakeCostResource) -> None:
        super().__init__()
        self.resource = resource
        self.workspaces_used: list[str | None] = []

    def cost(self, workspace: str | None = None) -> FakeCostResource:
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
        (
            "totals",
            {
                "pipeline_name": PIPELINE,
                "start_date": "2026-09-01T00:00:00Z",
                "end_date": None,
                "services": None,
                "providers": None,
                "api_keys": None,
            },
        )
    ]


@pytest.mark.asyncio
async def test_get_cost_over_time() -> None:
    client = FakeClient(FakeCostResource())

    result = await get_cost_over_time(client=client, workspace=WORKSPACE, end_date="2026-10-01T00:00:00Z")

    assert result == OVER_TIME
    assert client.resource.calls == [
        (
            "over_time",
            {
                "pipeline_name": None,
                "start_date": None,
                "end_date": "2026-10-01T00:00:00Z",
                "services": None,
                "providers": None,
                "api_keys": None,
            },
        )
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
async def test_forbidden_pipeline_lookup_asks_for_pipelines_read() -> None:
    client = FakeClient(FakeCostResource(PipelineLookupForbiddenError(PIPELINE)))

    result = await get_cost_totals(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE)

    assert result == (
        f"Failed to get cost totals: filtering by pipeline name needs Pipelines read in workspace '{WORKSPACE}', "
        "which this API key doesn't have. To see cost per pipeline, use get_cost_breakdown with "
        "group_by='pipeline', which needs only Costs read."
    )


@pytest.mark.asyncio
async def test_invalid_key() -> None:
    html = "<html><head><title>401 Authorization Required</title></head></html>"
    client = FakeClient(FakeCostResource(UnexpectedAPIError(status_code=401, message=html)))

    result = await get_cost_over_time(client=client, workspace=WORKSPACE)

    assert result == "Failed to get cost over time: the API key is invalid or has expired."


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


@pytest.mark.asyncio
async def test_totals_passes_service_provider_and_api_key_filters() -> None:
    client = FakeClient(FakeCostResource())

    await get_cost_totals(
        client=client, workspace=WORKSPACE, services=[SERVICE], providers=["openai"], api_keys=[API_KEY_ID]
    )

    assert client.resource.calls[0][1] == {
        "pipeline_name": None,
        "start_date": None,
        "end_date": None,
        "services": [SERVICE],
        "providers": ["openai"],
        "api_keys": [API_KEY_ID],
    }


@pytest.mark.asyncio
async def test_over_time_and_breakdown_pass_the_same_filters() -> None:
    client = FakeClient(FakeCostResource())

    await get_cost_over_time(client=client, workspace=WORKSPACE, services=[SERVICE], api_keys=[API_KEY_ID])
    await get_cost_breakdown(client=client, workspace=WORKSPACE, group_by="model", services=[SERVICE], providers=["x"])

    (over_time_method, over_time), (breakdown_method, breakdown) = client.resource.calls
    assert over_time_method == "over_time"
    assert (over_time["services"], over_time["providers"], over_time["api_keys"]) == ([SERVICE], None, [API_KEY_ID])
    assert breakdown_method == "breakdown"
    assert (breakdown["services"], breakdown["providers"], breakdown["api_keys"]) == ([SERVICE], ["x"], None)


@pytest.mark.asyncio
async def test_unknown_service_name_says_how_to_find_it() -> None:
    client = FakeClient(FakeCostResource(ServiceNotFoundError("Gone")))

    result = await get_cost_totals(client=client, workspace=WORKSPACE, services=["Gone"])

    assert isinstance(result, str)
    assert "No Service named 'Gone'" in result
    assert "group_by='deployment'" in result
    assert "Workspace" not in result


@pytest.mark.asyncio
async def test_ambiguous_service_name_asks_for_the_id() -> None:
    client = FakeClient(FakeCostResource(AmbiguousServiceError("Twin")))

    result = await get_cost_breakdown(client=client, workspace=WORKSPACE, group_by="model", services=["Twin"])

    assert isinstance(result, str)
    assert "Several Services are named 'Twin'" in result
    assert "Pass the Service id" in result


@pytest.mark.asyncio
async def test_forbidden_service_lookup_points_to_the_service_id() -> None:
    client = FakeClient(FakeCostResource(ServiceLookupForbiddenError()))

    result = await get_cost_over_time(client=client, workspace=WORKSPACE, services=[SERVICE])

    assert isinstance(result, str)
    assert "looking up a Service by name needs Services read" in result
    assert "needs only Costs read" in result
    assert "has no permission to read cost" not in result


@pytest.mark.asyncio
async def test_error_messages_do_not_echo_api_key_ids() -> None:
    error = BadRequestError(message=f"Invalid api_token_id {API_KEY_ID}")
    client = FakeClient(FakeCostResource(error))

    result = await get_cost_totals(client=client, workspace=WORKSPACE, api_keys=[API_KEY_ID])

    assert isinstance(result, str)
    assert API_KEY_ID not in result
    assert result == "Failed to get cost totals: Invalid api_token_id <api key id> (Status Code: 400)"


@pytest.mark.asyncio
async def test_without_a_workspace_the_tools_read_the_organization() -> None:
    client = FakeClient(FakeCostResource())

    assert await get_cost_totals(client=client) == TOTALS
    assert await get_cost_over_time(client=client) == OVER_TIME
    assert await get_cost_breakdown(client=client, group_by="workspace") == BREAKDOWN

    assert client.workspaces_used == [None, None, None]


@pytest.mark.asyncio
async def test_a_given_workspace_is_still_used() -> None:
    client = FakeClient(FakeCostResource())

    await get_cost_totals(client=client, workspace=WORKSPACE)

    assert client.workspaces_used == [WORKSPACE]


@pytest.mark.asyncio
async def test_organization_read_without_the_admin_role_asks_for_a_workspace() -> None:
    client = FakeClient(FakeCostResource(OrganizationCostForbiddenError()))

    result = await get_cost_totals(client=client)

    assert isinstance(result, str)
    assert "needs the organization admin role" in result
    assert "Pass workspace" in result
    assert "has no permission to read cost" not in result


@pytest.mark.asyncio
async def test_pipeline_name_without_a_workspace_explains_what_to_do() -> None:
    client = FakeClient(FakeCostResource(WorkspaceRequiredError("pipeline_name")))

    result = await get_cost_breakdown(client=client, group_by="model", pipeline_name=PIPELINE)

    assert isinstance(result, str)
    assert "pipeline_name needs a workspace" in result
    assert "group_by='pipeline'" in result
