# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Any, cast
from uuid import UUID

import pytest

from deepset_mcp.api.deployment.models import (
    Deployment,
    DeploymentDesiredStatus,
    DeploymentEvent,
    DeploymentMetrics,
    DeploymentMode,
    DeploymentRevision,
    DeploymentRevisionDetail,
    DeploymentServiceLevel,
    DeploymentSourceType,
    DeploymentStatistics,
    DeploymentStatsGranularity,
    DeploymentStatus,
)
from deepset_mcp.api.deployment.protocols import DeploymentResourceProtocol
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.shared_models import NoContentResponse, PaginatedResponse
from deepset_mcp.tools.deployment import (
    activate_deployment,
    activate_deployment_revision,
    add_deployment_tag,
    create_deployment,
    create_deployment_revision,
    deactivate_deployment,
    delete_deployment,
    delete_deployment_tag,
    get_deployment,
    get_deployment_metrics,
    get_deployment_revision,
    get_deployment_stats,
    list_deployment_activity,
    list_deployment_revisions,
    list_deployment_tags,
    list_deployments,
    update_deployment,
)
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
DEPLOYMENT_ID = "11111111-1111-1111-1111-111111111111"
REVISION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def make_deployment() -> Deployment:
    return Deployment(
        deployment_id=UUID(DEPLOYMENT_ID),
        name="my-gateway",
        tags=[],
        organization_id=UUID("00000000-0000-0000-0000-000000000001"),
        deployment_mode=DeploymentMode.MANAGED,
        desired_status=DeploymentDesiredStatus.DEPLOYED,
        status=DeploymentStatus.DEPLOYED,
        service_level=DeploymentServiceLevel.DEVELOPMENT,
        idle_timeout_in_seconds=300,
        min_query_replica_count=1,
        max_query_replica_count=1,
        max_index_replica_count=1,
        log_storage_enabled=True,
        search_history_enabled=True,
        created_at=datetime(2025, 1, 1),
    )


def make_revision(detail: bool = False) -> DeploymentRevision | DeploymentRevisionDetail:
    kwargs: dict[str, Any] = {
        "revision_id": REVISION_ID,
        "deployment_id": DEPLOYMENT_ID,
        "status": "ACTIVE",
        "config_hash": "abc123",
        "haystack_version": "2.0.0",
        "created_at": "2025-01-01T00:00:00Z",
    }
    if detail:
        return DeploymentRevisionDetail(**kwargs, config_yaml="components: {}")
    return DeploymentRevision(**kwargs)


class FakeDeploymentResource(DeploymentResourceProtocol):
    """Configurable fake implementing DeploymentResourceProtocol.

    Each method looks up a canned result or exception by its own name in the maps passed to
    the constructor, so a single fake class can drive every tool test in this module.
    """

    def __init__(self, results: dict[str, Any] | None = None, exceptions: dict[str, Exception] | None = None) -> None:
        self.results = results or {}
        self.exceptions = exceptions or {}
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _resolve(self, _method_name: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((_method_name, args, kwargs))
        if _method_name in self.exceptions:
            raise self.exceptions[_method_name]
        return self.results.get(_method_name)

    async def list_tags(self, name: str | None = None, order: str = "ASC") -> list[str]:
        return cast(list[str], self._resolve("list_tags", name=name, order=order) or [])

    async def create(
        self,
        name: str,
        description: str | None = None,
        group_label: str | None = None,
        origin_pipeline_id: str | None = None,
        deployment_mode: DeploymentMode = DeploymentMode.MANAGED,
        service_level: DeploymentServiceLevel = DeploymentServiceLevel.DEVELOPMENT,
        idle_timeout_in_seconds: int | None = None,
        min_query_replica_count: int | None = None,
        max_query_replica_count: int | None = None,
        max_index_replica_count: int | None = None,
        cpu_request: str | None = None,
        cpu_limit: str | None = None,
        memory_request: str | None = None,
        memory_limit: str | None = None,
        gpu_limit_gigabyte: int | None = None,
    ) -> Deployment:
        return cast(Deployment, self._resolve("create", name=name))

    async def get(self, deployment_id: str) -> Deployment:
        return cast(Deployment, self._resolve("get", deployment_id))

    async def update(
        self,
        deployment_id: str,
        name: str | None = None,
        description: str | None = None,
        group_label: str | None = None,
        deployment_mode: DeploymentMode | None = None,
        service_level: DeploymentServiceLevel | None = None,
        idle_timeout_in_seconds: int | None = None,
        min_query_replica_count: int | None = None,
        max_query_replica_count: int | None = None,
        max_index_replica_count: int | None = None,
        cpu_request: str | None = None,
        cpu_limit: str | None = None,
        memory_request: str | None = None,
        memory_limit: str | None = None,
        gpu_limit_gigabyte: int | None = None,
    ) -> Deployment:
        return cast(Deployment, self._resolve("update", deployment_id, name=name))

    async def delete(self, deployment_id: str) -> NoContentResponse:
        result = self._resolve("delete", deployment_id)
        return cast(NoContentResponse, result) if result is not None else NoContentResponse(message="Deleted")

    async def add_tag(self, deployment_id: str, name: str) -> list[str]:
        return cast(list[str], self._resolve("add_tag", deployment_id, name) or [])

    async def delete_tag(self, deployment_id: str, tag_name: str) -> list[str]:
        return cast(list[str], self._resolve("delete_tag", deployment_id, tag_name) or [])

    async def list_revisions(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentRevision]:
        result = self._resolve("list_revisions", deployment_id, limit=limit, after=after)
        return result if result is not None else PaginatedResponse[DeploymentRevision](data=[], has_more=False, total=0)

    async def get_revision(self, deployment_id: str, revision_id: str) -> DeploymentRevisionDetail:
        return cast(DeploymentRevisionDetail, self._resolve("get_revision", deployment_id, revision_id))

    async def create_revision(
        self,
        deployment_id: str,
        comment: str,
        config_yaml: str | None = None,
        source_version_id: str | None = None,
        source_type: DeploymentSourceType = DeploymentSourceType.PLATFORM_PIPELINE,
    ) -> DeploymentRevision:
        return cast(
            DeploymentRevision,
            self._resolve(
                "create_revision",
                deployment_id,
                comment=comment,
                config_yaml=config_yaml,
                source_version_id=source_version_id,
                source_type=source_type,
            ),
        )

    async def activate_revision(self, deployment_id: str, revision_id: str) -> Deployment:
        return cast(Deployment, self._resolve("activate_revision", deployment_id, revision_id))

    async def activate(self, deployment_id: str) -> Deployment:
        return cast(Deployment, self._resolve("activate", deployment_id))

    async def deactivate(self, deployment_id: str) -> Deployment:
        return cast(Deployment, self._resolve("deactivate", deployment_id))

    async def list_activity(
        self, deployment_id: str, limit: int = 100, after: str | None = None
    ) -> PaginatedResponse[DeploymentEvent]:
        result = self._resolve("list_activity", deployment_id, limit=limit, after=after)
        return result if result is not None else PaginatedResponse[DeploymentEvent](data=[], has_more=False, total=0)

    async def get_metrics(self, deployment_id: str, start_ms: int, end_ms: int) -> DeploymentMetrics:
        return cast(DeploymentMetrics, self._resolve("get_metrics", deployment_id, start_ms=start_ms, end_ms=end_ms))

    async def get_stats(
        self,
        deployment_id: str,
        days: int = 30,
        granularity: DeploymentStatsGranularity = DeploymentStatsGranularity.DAY,
        time_zone: str = "UTC",
    ) -> DeploymentStatistics:
        return cast(
            DeploymentStatistics,
            self._resolve("get_stats", deployment_id, days=days, granularity=granularity, time_zone=time_zone),
        )

    async def list(
        self,
        limit: int = 100,
        after: str | None = None,
        group_label: str | None = None,
        tags: list[str] | None = None,
    ) -> PaginatedResponse[Deployment]:
        result = self._resolve("list", limit=limit, after=after, group_label=group_label, tags=tags)
        return result if result is not None else PaginatedResponse[Deployment](data=[], has_more=False, total=0)


def make_client(fake: FakeDeploymentResource) -> BaseFakeClient:
    client = BaseFakeClient()
    client.deployments = lambda workspace: fake  # type: ignore[method-assign]
    return client


@pytest.mark.asyncio
async def test_list_deployments_success() -> None:
    page = PaginatedResponse[Deployment](data=[make_deployment()], has_more=False, total=1)
    client = make_client(FakeDeploymentResource(results={"list": page}))

    result = await list_deployments(client=client, workspace=WORKSPACE)

    assert result is page


@pytest.mark.asyncio
async def test_list_deployments_workspace_not_found() -> None:
    client = make_client(FakeDeploymentResource(exceptions={"list": ResourceNotFoundError("not found")}))

    result = await list_deployments(client=client, workspace=WORKSPACE)

    assert isinstance(result, str)
    assert "no workspace" in result


@pytest.mark.asyncio
async def test_list_deployment_tags_success() -> None:
    client = make_client(FakeDeploymentResource(results={"list_tags": ["prod", "eu"]}))

    result = await list_deployment_tags(client=client, workspace=WORKSPACE)

    assert result == ["prod", "eu"]


@pytest.mark.asyncio
async def test_create_deployment_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"create": deployment}))

    result = await create_deployment(client=client, workspace=WORKSPACE, name="my-gateway")

    assert result is deployment


@pytest.mark.asyncio
async def test_create_deployment_api_error() -> None:
    client = make_client(FakeDeploymentResource(exceptions={"create": UnexpectedAPIError(message="boom")}))

    result = await create_deployment(client=client, workspace=WORKSPACE, name="my-gateway")

    assert isinstance(result, str)
    assert "Failed to create deployment" in result


@pytest.mark.asyncio
async def test_get_deployment_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"get": deployment}))

    result = await get_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is deployment


@pytest.mark.asyncio
async def test_get_deployment_not_found() -> None:
    client = make_client(FakeDeploymentResource(exceptions={"get": ResourceNotFoundError("missing")}))

    result = await get_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert isinstance(result, str)
    assert DEPLOYMENT_ID in result


@pytest.mark.asyncio
async def test_update_deployment_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"update": deployment}))

    result = await update_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, name="renamed")

    assert result is deployment


@pytest.mark.asyncio
async def test_update_deployment_value_error_surfaced() -> None:
    client = make_client(FakeDeploymentResource(exceptions={"update": ValueError("At least one field")}))

    result = await update_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result == "At least one field"


@pytest.mark.asyncio
async def test_delete_deployment_success() -> None:
    response = NoContentResponse(message="Deployment deleted successfully.")
    client = make_client(FakeDeploymentResource(results={"delete": response}))

    result = await delete_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is response


@pytest.mark.asyncio
async def test_add_deployment_tag_success() -> None:
    client = make_client(FakeDeploymentResource(results={"add_tag": ["prod", "eu"]}))

    result = await add_deployment_tag(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, tag_name="eu")

    assert result == ["prod", "eu"]


@pytest.mark.asyncio
async def test_delete_deployment_tag_success() -> None:
    client = make_client(FakeDeploymentResource(results={"delete_tag": ["prod"]}))

    result = await delete_deployment_tag(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, tag_name="eu")

    assert result == ["prod"]


@pytest.mark.asyncio
async def test_list_deployment_revisions_success() -> None:
    page = PaginatedResponse[DeploymentRevision](data=[make_revision()], has_more=False, total=1)
    client = make_client(FakeDeploymentResource(results={"list_revisions": page}))

    result = await list_deployment_revisions(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is page


@pytest.mark.asyncio
async def test_get_deployment_revision_success() -> None:
    revision = make_revision(detail=True)
    client = make_client(FakeDeploymentResource(results={"get_revision": revision}))

    result = await get_deployment_revision(
        client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, revision_id=REVISION_ID
    )

    assert result is revision


@pytest.mark.asyncio
async def test_create_deployment_revision_success() -> None:
    revision = make_revision()
    client = make_client(FakeDeploymentResource(results={"create_revision": revision}))

    result = await create_deployment_revision(
        client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, comment="new revision"
    )

    assert result is revision


@pytest.mark.asyncio
async def test_activate_deployment_revision_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"activate_revision": deployment}))

    result = await activate_deployment_revision(
        client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, revision_id=REVISION_ID
    )

    assert result is deployment


@pytest.mark.asyncio
async def test_activate_deployment_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"activate": deployment}))

    result = await activate_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is deployment


@pytest.mark.asyncio
async def test_deactivate_deployment_success() -> None:
    deployment = make_deployment()
    client = make_client(FakeDeploymentResource(results={"deactivate": deployment}))

    result = await deactivate_deployment(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is deployment


@pytest.mark.asyncio
async def test_list_deployment_activity_success() -> None:
    page: PaginatedResponse[DeploymentEvent] = PaginatedResponse(data=[], has_more=False, total=0)
    client = make_client(FakeDeploymentResource(results={"list_activity": page}))

    result = await list_deployment_activity(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is page


@pytest.mark.asyncio
async def test_get_deployment_metrics_success() -> None:
    metrics = DeploymentMetrics(cpu=[], memory=[], replicas=[])
    client = make_client(FakeDeploymentResource(results={"get_metrics": metrics}))

    result = await get_deployment_metrics(
        client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID, start_ms=0, end_ms=1000
    )

    assert result is metrics


@pytest.mark.asyncio
async def test_get_deployment_stats_success() -> None:
    stats = DeploymentStatistics(window_days=30, granularity=DeploymentStatsGranularity.DAY, time_zone="UTC")
    client = make_client(FakeDeploymentResource(results={"get_stats": stats}))

    result = await get_deployment_stats(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert result is stats


@pytest.mark.asyncio
async def test_get_deployment_stats_not_found() -> None:
    client = make_client(FakeDeploymentResource(exceptions={"get_stats": ResourceNotFoundError("missing")}))

    result = await get_deployment_stats(client=client, workspace=WORKSPACE, deployment_id=DEPLOYMENT_ID)

    assert isinstance(result, str)
    assert DEPLOYMENT_ID in result
