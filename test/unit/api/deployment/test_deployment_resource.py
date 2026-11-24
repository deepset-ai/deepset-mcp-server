# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.deployment.models import (
    Deployment,
    DeploymentEvent,
    DeploymentMetrics,
    DeploymentRevision,
    DeploymentRevisionDetail,
    DeploymentStatistics,
)
from deepset_mcp.api.deployment.resource import DeploymentResource
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
BASE = f"v1/workspaces/{WORKSPACE}/deployments"

ORG_ID = "00000000-0000-0000-0000-000000000001"
WS_ID = "00000000-0000-0000-0000-000000000002"
USER_ID = "00000000-0000-0000-0000-000000000003"
DEP_1 = "11111111-1111-1111-1111-111111111111"
DEP_2 = "22222222-2222-2222-2222-222222222222"
REV_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
REV_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
EVT_1 = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def sample_deployment(deployment_id: str = DEP_1, name: str = "my-gateway") -> dict[str, Any]:
    return {
        "deployment_id": deployment_id,
        "name": name,
        "description": None,
        "group_label": None,
        "tags": ["prod"],
        "organization_id": ORG_ID,
        "workspace_id": WS_ID,
        "origin_pipeline_id": None,
        "pipeline_name": "my-pipeline",
        "output_type": "generative",
        "deployment_mode": "MANAGED",
        "desired_status": "DEPLOYED",
        "status": "DEPLOYED",
        "service_level": "DEVELOPMENT",
        "active_revision_id": None,
        "active_revision": None,
        "pending_revision_id": None,
        "idle_timeout_in_seconds": 300,
        "min_query_replica_count": 1,
        "max_query_replica_count": 1,
        "max_index_replica_count": 1,
        "cpu_request": None,
        "cpu_limit": None,
        "memory_request": None,
        "memory_limit": None,
        "gpu_limit_gigabyte": None,
        "settings": {},
        "log_storage_enabled": True,
        "search_history_enabled": True,
        "created_by": {"user_id": USER_ID, "given_name": "Test", "family_name": "User"},
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": None,
    }


def sample_revision(revision_id: str = REV_1, deployment_id: str = DEP_1, with_yaml: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "revision_id": revision_id,
        "deployment_id": deployment_id,
        "source_type": "PLATFORM_PIPELINE",
        "source_version_id": "00000000-0000-0000-0000-000000000009",
        "source_pipeline_id": None,
        "source_metadata": None,
        "status": "ACTIVE",
        "config_hash": "abc123",
        "haystack_version": "2.0.0",
        "comment": "initial",
        "created_by_user_id": USER_ID,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": None,
    }
    if with_yaml:
        data["config_yaml"] = "components: {}"
        data["output_type"] = "generative"
    return data


@pytest.fixture
def fake_client() -> BaseFakeClient:
    client = BaseFakeClient()

    def deployments(workspace: str) -> DeploymentResource:
        return DeploymentResource(client=client, workspace=workspace)

    client.deployments = deployments  # type: ignore[method-assign]
    return client


@pytest.mark.asyncio
async def test_list_deployments(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {
        BASE: {"data": [sample_deployment(DEP_1), sample_deployment(DEP_2)], "has_more": False, "total": 2}
    }

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.list()

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 2
    assert all(isinstance(d, Deployment) for d in result.data)
    assert str(result.data[0].deployment_id) == DEP_1


@pytest.mark.asyncio
async def test_list_deployments_cursor_population(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {
        BASE: {"data": [sample_deployment(DEP_1), sample_deployment(DEP_2)], "has_more": True, "total": 5}
    }

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.list(limit=2)

    assert result.has_more is True
    assert result.next_cursor == DEP_2


@pytest.mark.asyncio
async def test_list_deployments_filters_and_pagination_params(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {BASE: {"data": [], "has_more": False, "total": 0}}

    resource = fake_client.deployments(WORKSPACE)
    await resource.list(limit=5, after="cursor-1", group_label="team-a", tags=["prod", "eu"])

    request = fake_client.requests[0]
    assert request["params"] == {
        "limit": 5,
        "after": "cursor-1",
        "group_label": "team-a",
        "tags": ["prod", "eu"],
    }


@pytest.mark.asyncio
async def test_list_deployment_tags(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"v1/workspaces/{WORKSPACE}/deployment-tags": ["prod", "staging"]}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.list_tags()

    assert result == ["prod", "staging"]


@pytest.mark.asyncio
async def test_create_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {BASE: sample_deployment(DEP_1, "new-gateway")}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.create(name="new-gateway")

    assert isinstance(result, Deployment)
    assert result.name == "new-gateway"

    request = fake_client.requests[0]
    assert request["endpoint"] == BASE
    assert request["method"] == "POST"
    assert request["data"] == {
        "name": "new-gateway",
        "deployment_mode": "MANAGED",
        "service_level": "DEVELOPMENT",
    }


@pytest.mark.asyncio
async def test_get_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}": sample_deployment(DEP_1)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.get(DEP_1)

    assert isinstance(result, Deployment)
    assert str(result.deployment_id) == DEP_1


@pytest.mark.asyncio
async def test_get_deployment_not_found(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}": None}

    resource = fake_client.deployments(WORKSPACE)

    with pytest.raises(ResourceNotFoundError):
        await resource.get(DEP_1)


@pytest.mark.asyncio
async def test_update_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}": sample_deployment(DEP_1, "renamed")}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.update(DEP_1, name="renamed")

    assert isinstance(result, Deployment)
    request = fake_client.requests[0]
    assert request["method"] == "PATCH"
    assert request["data"] == {"name": "renamed"}


@pytest.mark.asyncio
async def test_update_deployment_no_fields_raises(fake_client: BaseFakeClient) -> None:
    resource = fake_client.deployments(WORKSPACE)

    with pytest.raises(ValueError, match="At least one field"):
        await resource.update(DEP_1)


@pytest.mark.asyncio
async def test_delete_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}": TransportResponse(text="", status_code=204, json=None)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.delete(DEP_1)

    assert isinstance(result, NoContentResponse)
    request = fake_client.requests[0]
    assert request["method"] == "DELETE"


@pytest.mark.asyncio
async def test_add_deployment_tag(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/tags": ["prod", "eu"]}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.add_tag(DEP_1, "eu")

    assert result == ["prod", "eu"]
    request = fake_client.requests[0]
    assert request["method"] == "POST"
    assert request["data"] == {"name": "eu"}


@pytest.mark.asyncio
async def test_delete_deployment_tag(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/tags/eu": ["prod"]}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.delete_tag(DEP_1, "eu")

    assert result == ["prod"]
    request = fake_client.requests[0]
    assert request["method"] == "DELETE"


@pytest.mark.asyncio
async def test_list_deployment_revisions(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {
        f"{BASE}/{DEP_1}/revisions": {"data": [sample_revision(REV_1)], "has_more": False, "total": 1}
    }

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.list_revisions(DEP_1)

    assert isinstance(result, PaginatedResponse)
    assert len(result.data) == 1
    assert isinstance(result.data[0], DeploymentRevision)


@pytest.mark.asyncio
async def test_get_deployment_revision(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/revisions/{REV_1}": sample_revision(REV_1, with_yaml=True)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.get_revision(DEP_1, REV_1)

    assert isinstance(result, DeploymentRevisionDetail)
    assert result.config_yaml == "components: {}"


@pytest.mark.asyncio
async def test_create_deployment_revision(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/revisions": sample_revision(REV_2)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.create_revision(DEP_1, comment="new revision", config_yaml="components: {}")

    assert isinstance(result, DeploymentRevision)
    request = fake_client.requests[0]
    assert request["method"] == "POST"
    assert request["data"] == {
        "comment": "new revision",
        "config_yaml": "components: {}",
        "source_type": "PLATFORM_PIPELINE",
    }


@pytest.mark.asyncio
async def test_activate_deployment_revision(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/revisions/{REV_1}/activate": sample_deployment(DEP_1)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.activate_revision(DEP_1, REV_1)

    assert isinstance(result, Deployment)
    assert fake_client.requests[0]["method"] == "POST"


@pytest.mark.asyncio
async def test_activate_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/activate": sample_deployment(DEP_1)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.activate(DEP_1)

    assert isinstance(result, Deployment)


@pytest.mark.asyncio
async def test_deactivate_deployment(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/deactivate": sample_deployment(DEP_1)}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.deactivate(DEP_1)

    assert isinstance(result, Deployment)


@pytest.mark.asyncio
async def test_list_deployment_activity(fake_client: BaseFakeClient) -> None:
    event = {
        "event_id": EVT_1,
        "deployment_id": DEP_1,
        "revision_id": REV_1,
        "event_type": "REVISION_ACTIVATED",
        "triggered_by": USER_ID,
        "created_at": "2025-01-01T00:00:00Z",
    }
    fake_client.responses = {f"{BASE}/{DEP_1}/activity": {"data": [event], "has_more": False, "total": 1}}

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.list_activity(DEP_1)

    assert isinstance(result, PaginatedResponse)
    assert isinstance(result.data[0], DeploymentEvent)


@pytest.mark.asyncio
async def test_get_deployment_metrics(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {
        f"{BASE}/{DEP_1}/metrics": {
            "cpu": [],
            "memory": [],
            "replicas": [],
            "cpu_limit_cores": 1.0,
            "memory_limit_bytes": 1024.0,
        }
    }

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.get_metrics(DEP_1, start_ms=0, end_ms=1000)

    assert isinstance(result, DeploymentMetrics)
    request = fake_client.requests[0]
    assert request["params"] == {"start": 0, "end": 1000}


@pytest.mark.asyncio
async def test_get_deployment_metrics_empty_response_raises(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {f"{BASE}/{DEP_1}/metrics": TransportResponse(text="", status_code=200, json=None)}

    resource = fake_client.deployments(WORKSPACE)

    with pytest.raises(UnexpectedAPIError):
        await resource.get_metrics(DEP_1, start_ms=0, end_ms=1000)


@pytest.mark.asyncio
async def test_get_deployment_stats(fake_client: BaseFakeClient) -> None:
    fake_client.responses = {
        f"{BASE}/{DEP_1}/stats": {
            "window_days": 30,
            "granularity": "DAY",
            "time_zone": "UTC",
            "total_queries": 10,
            "series": [],
        }
    }

    resource = fake_client.deployments(WORKSPACE)
    result = await resource.get_stats(DEP_1)

    assert isinstance(result, DeploymentStatistics)
    assert result.total_queries == 10
