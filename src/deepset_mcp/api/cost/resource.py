# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource for the LLM cost stats API."""

import asyncio
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from deepset_mcp.api import ids
from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals
from deepset_mcp.api.cost.protocols import CostResourceProtocol
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol

# Aggregating a wide date range over a large organization can take longer than the default 5s.
COST_REQUEST_TIMEOUT = 30.0


class PipelineLookupForbiddenError(UnexpectedAPIError):
    """The API key may not read the pipeline, so its name can't be resolved to the ID the cost routes filter by.

    Reading a pipeline needs Pipelines read, which a key with only Costs read doesn't have.
    """

    def __init__(self, pipeline_name: str, detail: Any | None = None) -> None:
        """Initialize the exception.

        :param pipeline_name: The pipeline that couldn't be read.
        :param detail: The error detail from the pipeline lookup.
        """
        super().__init__(status_code=403, message=f"Not allowed to read pipeline '{pipeline_name}'", detail=detail)
        self.pipeline_name = pipeline_name


class WorkspaceRequiredError(UnexpectedAPIError):
    """A pipeline or Service name was given without a workspace, so it can't be resolved to an ID."""

    def __init__(self, what: str) -> None:
        """Initialize the exception.

        :param what: What needs the workspace, such as ``pipeline_name`` or ``services`` by name.
        """
        super().__init__(status_code=400, message=f"{what} needs a workspace")
        self.what = what


class OrganizationCostForbiddenError(UnexpectedAPIError):
    """The API key may not read the cost of the whole organization, which needs the organization admin role."""

    def __init__(self, detail: Any | None = None) -> None:
        """Initialize the exception.

        :param detail: The error detail from the cost route.
        """
        super().__init__(status_code=403, message="Not allowed to read the organization's cost", detail=detail)


class ServiceLookupForbiddenError(UnexpectedAPIError):
    """The API key may not list the workspace's Services, so a Service name can't be resolved to its ID.

    Listing Services needs Services read, which a key with only Costs read doesn't have. A Service ID needs no
    lookup.
    """

    def __init__(self, detail: Any | None = None) -> None:
        """Initialize the exception.

        :param detail: The error detail from the Service listing.
        """
        super().__init__(status_code=403, message="Not allowed to list the workspace's Services", detail=detail)


class ServiceNotFoundError(ResourceNotFoundError):
    """No Service in the workspace has the given name."""

    def __init__(self, service: str) -> None:
        """Initialize the exception.

        :param service: The Service name that matched nothing.
        """
        super().__init__(message=f"No Service named '{service}'")
        self.service = service


class AmbiguousServiceError(UnexpectedAPIError):
    """More than one Service in the workspace has the given name, so it can't be resolved to one ID."""

    def __init__(self, service: str) -> None:
        """Initialize the exception.

        :param service: The Service name that matched several Services.
        """
        super().__init__(status_code=400, message=f"Several Services are named '{service}'")
        self.service = service


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


class CostResource(CostResourceProtocol):
    """Reads one workspace's LLM cost through the v2 cost stats routes.

    The routes are keyed by organization UUID and filter by workspace, pipeline and Service UUIDs; this resource
    takes names and resolves them on each call. Provider and API key filters are passed through as given.
    Without a workspace it reads the whole organization, which needs the organization admin role.
    Costs are in USD.
    """

    def __init__(self, client: "AsyncClientProtocol", workspace: str | None = None) -> None:
        """Initialize the cost resource.

        :param client: The async REST client.
        :param workspace: The workspace to use. ``None`` reads the whole organization.
        """
        self._client = client
        self._workspace = workspace

    async def _pipeline_id(self, pipeline_name: str) -> str:
        if self._workspace is None:
            raise WorkspaceRequiredError("pipeline_name")
        try:
            return await ids.pipeline_id(self._client, self._workspace, pipeline_name)
        except UnexpectedAPIError as e:
            if e.status_code == 403:
                raise PipelineLookupForbiddenError(pipeline_name, detail=e.detail) from e
            raise

    async def _service_ids(self, services: list[str]) -> list[str]:
        """Resolve Service names to IDs. Values that already are IDs pass through without a lookup."""
        by_name: dict[str, list[str]] = {}
        if not all(_is_uuid(service) for service in services):
            if self._workspace is None:
                raise WorkspaceRequiredError("A Service name")
            try:
                async for deployment in await self._client.deployments(self._workspace).list():
                    by_name.setdefault(deployment.name, []).append(str(deployment.deployment_id))
            except UnexpectedAPIError as e:
                if e.status_code == 403:
                    raise ServiceLookupForbiddenError(detail=e.detail) from e
                raise

        service_ids = []
        for service in services:
            if _is_uuid(service):
                service_ids.append(service)
                continue
            matches = by_name.get(service, [])
            if not matches:
                raise ServiceNotFoundError(service)
            if len(matches) > 1:
                raise AmbiguousServiceError(service)
            service_ids.append(matches[0])
        return service_ids

    async def _get(
        self,
        stat: str,
        pipeline_name: str | None,
        params: dict[str, Any],
        services: list[str] | None,
        providers: list[str] | None,
        api_keys: list[str] | None,
    ) -> Any:
        lookups: list[Coroutine[Any, Any, Any]] = [ids.organization_id(self._client)]
        if self._workspace is not None:
            lookups.append(ids.workspace_id(self._client, self._workspace))
        if pipeline_name is not None:
            lookups.append(self._pipeline_id(pipeline_name))
        if services:
            lookups.append(self._service_ids(services))
        organization_id, *resolved = await asyncio.gather(*lookups)

        if self._workspace is not None:
            params = {"workspace_id": resolved.pop(0), **params}
        if pipeline_name is not None:
            params["pipeline_id"] = resolved.pop(0)
        if services:
            params["deployment_id"] = resolved.pop(0)
        params["provider"] = providers or None
        params["api_token_id"] = api_keys or None
        resp = await self._client.request(
            endpoint=f"v2/cost/organizations/{organization_id}/stats/{stat}",
            method="GET",
            params={key: value for key, value in params.items() if value is not None},
            timeout=COST_REQUEST_TIMEOUT,
        )
        try:
            raise_for_status(resp)
        except UnexpectedAPIError as e:
            if e.status_code == 403 and self._workspace is None:
                raise OrganizationCostForbiddenError(detail=e.detail) from e
            raise
        return resp.json

    async def totals(
        self,
        pipeline_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        services: list[str] | None = None,
        providers: list[str] | None = None,
        api_keys: list[str] | None = None,
    ) -> CostTotals:
        """Read the workspace's LLM cost totals.

        :param pipeline_name: Restrict to this pipeline.
        :param start_date: Inclusive ISO timestamp. Defaults to 30 days before ``end_date``.
        :param end_date: Exclusive ISO timestamp. Defaults to no upper bound.
        :param services: Restrict to these Services, by name or ID.
        :param providers: Restrict to these providers, by the provider IDs the breakdown returns.
        :param api_keys: Restrict to these API keys, by key ID (never the secret token).
        :returns: The totals.
        """
        data = await self._get(
            "totals", pipeline_name, {"start_date": start_date, "end_date": end_date}, services, providers, api_keys
        )
        return CostTotals.model_validate(data)

    async def over_time(
        self,
        pipeline_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        services: list[str] | None = None,
        providers: list[str] | None = None,
        api_keys: list[str] | None = None,
    ) -> CostOverTime:
        """Read the workspace's LLM cost per UTC day.

        :param pipeline_name: Restrict to this pipeline.
        :param start_date: Inclusive ISO timestamp. Defaults to 30 days before ``end_date``.
        :param end_date: Exclusive ISO timestamp. Defaults to no upper bound.
        :param services: Restrict to these Services, by name or ID.
        :param providers: Restrict to these providers, by the provider IDs the breakdown returns.
        :param api_keys: Restrict to these API keys, by key ID (never the secret token).
        :returns: One point per day with usage.
        """
        data = await self._get(
            "cost-over-time",
            pipeline_name,
            {"start_date": start_date, "end_date": end_date},
            services,
            providers,
            api_keys,
        )
        return CostOverTime.model_validate(data)

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
        """Read the workspace's LLM cost grouped by a dimension.

        :param group_by: The dimension to group by.
        :param pipeline_name: Restrict to this pipeline.
        :param start_date: Inclusive ISO timestamp. Defaults to 30 days before ``end_date``.
        :param end_date: Exclusive ISO timestamp. Defaults to no upper bound.
        :param sort_by: The field to sort by. The API defaults to ``cost_total``.
        :param sort_order: ``ASC`` or ``DESC``. The API defaults to ``DESC``.
        :param limit: Groups per page, from 1 to 100.
        :param page_number: The page to read, starting at 1.
        :param services: Restrict to these Services, by name or ID.
        :param providers: Restrict to these providers, by the provider IDs the breakdown returns.
        :param api_keys: Restrict to these API keys, by key ID (never the secret token).
        :returns: One page of groups.
        """
        params = {
            "group_by": group_by,
            "start_date": start_date,
            "end_date": end_date,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "page_number": page_number,
        }
        return CostBreakdown.model_validate(
            await self._get("breakdown", pipeline_name, params, services, providers, api_keys)
        )
