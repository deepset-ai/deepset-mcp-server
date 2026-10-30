# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for CostResource."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.cost.models import CostBreakdown, CostOverTime, CostTotals
from deepset_mcp.api.cost.resource import (
    AmbiguousServiceError,
    CostResource,
    OrganizationCostForbiddenError,
    PipelineLookupForbiddenError,
    ServiceLookupForbiddenError,
    ServiceNotFoundError,
    WorkspaceRequiredError,
)
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
SERVICE_NAME = "Global Assistant"
SERVICE_UUID = "11111111-2222-3333-4444-555555555555"
OTHER_SERVICE_UUID = "66666666-7777-8888-9999-000000000000"
API_KEY_ID = "5f0c6d55-9d57-4f0e-9a6e-0d2f6a1f7c11"

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


class FakeServicePage:
    def __init__(self, services: list[SimpleNamespace]) -> None:
        self._services = services

    async def __aiter__(self) -> AsyncIterator[SimpleNamespace]:
        for service in self._services:
            yield service


class FakeDeploymentResource:
    def __init__(self, services: list[tuple[str, str]] | Exception) -> None:
        self._services = services
        self.list_calls = 0

    async def list(self) -> FakeServicePage:
        self.list_calls += 1
        if isinstance(self._services, Exception):
            raise self._services
        return FakeServicePage([SimpleNamespace(name=name, deployment_id=UUID(uid)) for name, uid in self._services])


class FakeCostClient(BaseFakeClient):
    """Resolves the workspace and pipeline through fakes and answers HTTP calls from a dict."""

    def __init__(
        self,
        http_responses: dict[str, Any],
        pipeline: DeepsetPipeline | Exception | None = None,
        services: list[tuple[str, str]] | Exception | None = None,
    ) -> None:
        super().__init__(responses={"v1/me": ME, **http_responses})
        self.deployment_resource = FakeDeploymentResource(services if services is not None else [])
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

    def deployments(self, workspace: str) -> FakeDeploymentResource:  # type: ignore[override]
        return self.deployment_resource

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
async def test_forbidden_pipeline_lookup_raises_a_dedicated_error() -> None:
    client = FakeCostClient({}, pipeline=UnexpectedAPIError(status_code=403, message="Forbidden"))

    with pytest.raises(PipelineLookupForbiddenError) as exc_info:
        await resource(client).totals(pipeline_name=PIPELINE_NAME)

    assert exc_info.value.pipeline_name == PIPELINE_NAME
    assert exc_info.value.status_code == 403
    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_other_pipeline_lookup_errors_pass_through() -> None:
    client = FakeCostClient({}, pipeline=UnexpectedAPIError(status_code=500, message="Server error"))

    with pytest.raises(UnexpectedAPIError) as exc_info:
        await resource(client).totals(pipeline_name=PIPELINE_NAME)

    assert not isinstance(exc_info.value, PipelineLookupForbiddenError)


@pytest.mark.asyncio
async def test_forbidden_carries_the_api_error_message() -> None:
    forbidden = TransportResponse(text="", status_code=403, json={"errors": ["Forbidden"]})
    client = FakeCostClient({f"{STATS}/totals": forbidden})

    with pytest.raises(UnexpectedAPIError) as exc_info:
        await resource(client).totals()

    assert exc_info.value.status_code == 403
    assert not isinstance(exc_info.value, PipelineLookupForbiddenError)
    assert str(exc_info.value) == "Forbidden (Status Code: 403)"


@pytest.mark.asyncio
async def test_me_without_organization_raises() -> None:
    client = FakeCostClient({"v1/me": {"user_id": "u-1"}})

    with pytest.raises(UnexpectedAPIError):
        await resource(client).totals()


@pytest.mark.asyncio
async def test_provider_and_api_key_filters_are_sent_as_repeated_params() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    await resource(client).totals(providers=["openai", "bedrock_converse"], api_keys=[API_KEY_ID])

    assert client.stats_request()["params"] == {
        "workspace_id": WORKSPACE_UUID,
        "provider": ["openai", "bedrock_converse"],
        "api_token_id": [API_KEY_ID],
    }


@pytest.mark.asyncio
async def test_empty_filter_lists_send_nothing() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    await resource(client).totals(services=[], providers=[], api_keys=[])

    assert client.stats_request()["params"] == {"workspace_id": WORKSPACE_UUID}
    assert client.deployment_resource.list_calls == 0


@pytest.mark.asyncio
async def test_service_ids_pass_through_without_a_lookup() -> None:
    client = FakeCostClient({f"{STATS}/cost-over-time": {"data": []}})

    await resource(client).over_time(services=[SERVICE_UUID])

    assert client.stats_request()["params"] == {"workspace_id": WORKSPACE_UUID, "deployment_id": [SERVICE_UUID]}
    assert client.deployment_resource.list_calls == 0


@pytest.mark.asyncio
async def test_service_names_resolve_to_ids_and_mix_with_ids() -> None:
    client = FakeCostClient(
        {f"{STATS}/breakdown": breakdown_dict()},
        services=[(SERVICE_NAME, SERVICE_UUID), ("Other", "99999999-9999-9999-9999-999999999999")],
    )

    await resource(client).breakdown(group_by="model", services=[SERVICE_NAME, OTHER_SERVICE_UUID])

    assert client.stats_request()["params"]["deployment_id"] == [SERVICE_UUID, OTHER_SERVICE_UUID]
    assert client.deployment_resource.list_calls == 1


@pytest.mark.asyncio
async def test_service_filter_combines_with_pipeline_and_the_other_filters() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()}, services=[(SERVICE_NAME, SERVICE_UUID)])

    await resource(client).totals(
        pipeline_name=PIPELINE_NAME, services=[SERVICE_NAME], providers=["openai"], api_keys=[API_KEY_ID]
    )

    assert client.stats_request()["params"] == {
        "workspace_id": WORKSPACE_UUID,
        "pipeline_id": PIPELINE_UUID,
        "deployment_id": [SERVICE_UUID],
        "provider": ["openai"],
        "api_token_id": [API_KEY_ID],
    }


@pytest.mark.asyncio
async def test_unknown_service_name_raises_not_found() -> None:
    client = FakeCostClient({}, services=[(SERVICE_NAME, SERVICE_UUID)])

    with pytest.raises(ServiceNotFoundError) as exc_info:
        await resource(client).totals(services=["Gone"])

    assert exc_info.value.service == "Gone"
    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_ambiguous_service_name_raises() -> None:
    client = FakeCostClient({}, services=[(SERVICE_NAME, SERVICE_UUID), (SERVICE_NAME, OTHER_SERVICE_UUID)])

    with pytest.raises(AmbiguousServiceError) as exc_info:
        await resource(client).totals(services=[SERVICE_NAME])

    assert exc_info.value.service == SERVICE_NAME
    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_forbidden_service_listing_raises_a_dedicated_error() -> None:
    client = FakeCostClient({}, services=UnexpectedAPIError(status_code=403, message="Forbidden"))

    with pytest.raises(ServiceLookupForbiddenError) as exc_info:
        await resource(client).totals(services=[SERVICE_NAME])

    assert exc_info.value.status_code == 403
    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_other_service_listing_errors_pass_through() -> None:
    client = FakeCostClient({}, services=UnexpectedAPIError(status_code=500, message="Server error"))

    with pytest.raises(UnexpectedAPIError) as exc_info:
        await resource(client).totals(services=[SERVICE_NAME])

    assert not isinstance(exc_info.value, ServiceLookupForbiddenError)


@pytest.mark.asyncio
async def test_api_key_of_another_workspace_is_scoped_by_the_workspace_and_returns_nothing() -> None:
    """The backend ANDs ``api_token_id`` with ``workspace_id``, so a key id from another workspace (or one that
    doesn't exist) narrows to no usage: a zero result, not an error. The resource must therefore always send
    ``workspace_id`` and never widen the request.
    """
    empty = {**totals_dict(), "total_cost": None, "total_tokens": 0, "total_requests": 0, "unpriced_models": []}
    client = FakeCostClient({f"{STATS}/totals": empty})

    totals = await resource(client).totals(api_keys=[API_KEY_ID])

    assert totals.total_requests == 0
    assert totals.total_cost is None
    params = client.stats_request()["params"]
    assert params["workspace_id"] == WORKSPACE_UUID
    assert params["api_token_id"] == [API_KEY_ID]


def organization_resource(client: FakeCostClient) -> CostResource:
    return CostResource(client=client, workspace=None)


@pytest.mark.asyncio
async def test_without_a_workspace_the_whole_organization_is_read() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    totals = await organization_resource(client).totals(start_date="2026-09-01T00:00:00Z")

    assert isinstance(totals, CostTotals)
    request = client.stats_request()
    assert request["endpoint"] == f"{STATS}/totals"
    assert request["params"] == {"start_date": "2026-09-01T00:00:00Z"}
    assert [r["endpoint"] for r in client.requests] == ["v1/me", f"{STATS}/totals"]


@pytest.mark.asyncio
async def test_organization_over_time_and_breakdown_send_no_workspace() -> None:
    client = FakeCostClient(
        {
            f"{STATS}/cost-over-time": {"data": [{"date": "2026-10-01T00:00:00Z", "cost_total": 1.5}]},
            f"{STATS}/breakdown": breakdown_dict(),
        }
    )

    await organization_resource(client).over_time()
    await organization_resource(client).breakdown(group_by="workspace")

    for request in (r for r in client.requests if r["endpoint"].startswith(STATS)):
        assert "workspace_id" not in request["params"]


@pytest.mark.asyncio
async def test_organization_filters_combine_with_service_ids_providers_and_api_keys() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    await organization_resource(client).totals(services=[SERVICE_UUID], providers=["openai"], api_keys=[API_KEY_ID])

    assert client.stats_request()["params"] == {
        "deployment_id": [SERVICE_UUID],
        "provider": ["openai"],
        "api_token_id": [API_KEY_ID],
    }
    assert client.deployment_resource.list_calls == 0


@pytest.mark.asyncio
async def test_organization_view_cannot_resolve_a_pipeline_name() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    with pytest.raises(WorkspaceRequiredError) as exc_info:
        await organization_resource(client).totals(pipeline_name=PIPELINE_NAME)

    assert exc_info.value.what == "pipeline_name"
    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_organization_view_cannot_resolve_a_service_name() -> None:
    client = FakeCostClient({f"{STATS}/totals": totals_dict()})

    with pytest.raises(WorkspaceRequiredError):
        await organization_resource(client).totals(services=[SERVICE_NAME])

    assert not any(r["endpoint"].startswith(STATS) for r in client.requests)


@pytest.mark.asyncio
async def test_forbidden_organization_read_raises_a_dedicated_error() -> None:
    forbidden = TransportResponse(text="", status_code=403, json={"errors": ["Forbidden"]})
    client = FakeCostClient({f"{STATS}/totals": forbidden})

    with pytest.raises(OrganizationCostForbiddenError) as exc_info:
        await organization_resource(client).totals()

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_forbidden_workspace_read_is_not_an_organization_error() -> None:
    forbidden = TransportResponse(text="", status_code=403, json={"errors": ["Forbidden"]})
    client = FakeCostClient({f"{STATS}/totals": forbidden})

    with pytest.raises(UnexpectedAPIError) as exc_info:
        await resource(client).totals()

    assert not isinstance(exc_info.value, OrganizationCostForbiddenError)
