# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource for the LLM cost stats API."""

import asyncio
from typing import TYPE_CHECKING, Any, Literal

from deepset_mcp.api import ids
from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals
from deepset_mcp.api.cost.protocols import CostResourceProtocol
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol

# Aggregating a wide date range over a large organization can take longer than the default 5s.
COST_REQUEST_TIMEOUT = 30.0


class CostResource(CostResourceProtocol):
    """Reads one workspace's LLM cost through the v2 cost stats routes.

    The routes are keyed by organization UUID and filter by workspace and pipeline UUIDs; this resource
    takes names and resolves them on each call. Costs are in USD.
    """

    def __init__(self, client: "AsyncClientProtocol", workspace: str) -> None:
        """Initialize the cost resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def _get(self, stat: str, pipeline_name: str | None, params: dict[str, Any]) -> Any:
        lookups = [ids.organization_id(self._client), ids.workspace_id(self._client, self._workspace)]
        if pipeline_name is not None:
            lookups.append(ids.pipeline_id(self._client, self._workspace, pipeline_name))
        organization_id, workspace_id, *pipeline_id = await asyncio.gather(*lookups)

        params = {"workspace_id": workspace_id, **params}
        if pipeline_id:
            params["pipeline_id"] = pipeline_id[0]
        resp = await self._client.request(
            endpoint=f"v2/cost/organizations/{organization_id}/stats/{stat}",
            method="GET",
            params={key: value for key, value in params.items() if value is not None},
            timeout=COST_REQUEST_TIMEOUT,
        )
        raise_for_status(resp)
        return resp.json

    async def totals(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostTotals:
        """Read the workspace's LLM cost totals.

        :param pipeline_name: Restrict to this pipeline.
        :param start_date: Inclusive ISO timestamp. Defaults to 30 days before ``end_date``.
        :param end_date: Exclusive ISO timestamp. Defaults to no upper bound.
        :returns: The totals.
        """
        data = await self._get("totals", pipeline_name, {"start_date": start_date, "end_date": end_date})
        return CostTotals.model_validate(data)

    async def over_time(
        self, pipeline_name: str | None = None, start_date: str | None = None, end_date: str | None = None
    ) -> CostOverTime:
        """Read the workspace's LLM cost per UTC day.

        :param pipeline_name: Restrict to this pipeline.
        :param start_date: Inclusive ISO timestamp. Defaults to 30 days before ``end_date``.
        :param end_date: Exclusive ISO timestamp. Defaults to no upper bound.
        :returns: One point per day with usage.
        """
        data = await self._get("cost-over-time", pipeline_name, {"start_date": start_date, "end_date": end_date})
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
        return CostBreakdown.model_validate(await self._get("breakdown", pipeline_name, params))
