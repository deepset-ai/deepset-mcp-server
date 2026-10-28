# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for reading a workspace's LLM cost: totals, cost per day, and a breakdown by model, pipeline and more."""

from typing import Literal

from deepset_mcp.api.cost.models import CostBreakdown, CostGroupBy, CostOverTime, CostSortBy, CostTotals
from deepset_mcp.api.cost.resource import (
    AmbiguousServiceError,
    PipelineLookupForbiddenError,
    ServiceLookupForbiddenError,
    ServiceNotFoundError,
)
from deepset_mcp.api.exceptions import (
    BadRequestError,
    RequestTimeoutError,
    ResourceNotFoundError,
    UnexpectedAPIError,
)
from deepset_mcp.api.protocols import AsyncClientProtocol

_REDACTED_KEY_ID = "<api key id>"


def _error_message(
    error: Exception, action: str, workspace: str, pipeline_name: str | None, api_keys: list[str] | None = None
) -> str:
    if isinstance(error, ServiceNotFoundError):
        return (
            f"Failed to {action}: {error.message}. Pass a Service name as shown on the Cost Management page, or its "
            "id from get_cost_breakdown with group_by='deployment'."
        )
    if isinstance(error, AmbiguousServiceError):
        return (
            f"Failed to {action}: {error.message}. Pass the Service id instead; get_cost_breakdown with "
            "group_by='deployment' lists each Service's id as its key."
        )
    if isinstance(error, ServiceLookupForbiddenError):
        return (
            f"Failed to {action}: looking up a Service by name needs Services read in workspace '{workspace}', which "
            "this API key doesn't have. Pass the Service id instead; get_cost_breakdown with "
            "group_by='deployment' lists each Service's id as its key and needs only Costs read."
        )
    if isinstance(error, ResourceNotFoundError):
        if pipeline_name is None:
            return f"Workspace '{workspace}' not found."
        return (
            f"Workspace '{workspace}' or pipeline '{pipeline_name}' not found. A deleted pipeline can't be used as a "
            "filter; its cost still shows up in get_cost_breakdown with group_by='pipeline'."
        )
    if isinstance(error, PipelineLookupForbiddenError):
        return (
            f"Failed to {action}: filtering by pipeline name needs Pipelines read in workspace '{workspace}', which "
            "this API key doesn't have. To see cost per pipeline, use get_cost_breakdown with group_by='pipeline', "
            "which needs only Costs read."
        )
    if isinstance(error, UnexpectedAPIError) and error.status_code == 403:
        return f"Failed to {action}: the API key has no permission to read cost in workspace '{workspace}'."
    if isinstance(error, UnexpectedAPIError) and error.status_code == 401:
        return f"Failed to {action}: the API key is invalid or has expired."
    if isinstance(error, RequestTimeoutError):
        return f"Failed to {action}: the request timed out. Try a shorter date range."
    message = f"Failed to {action}: {error}"
    for key_id in api_keys or []:
        message = message.replace(key_id, _REDACTED_KEY_ID)
    return message


async def get_cost_totals(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    services: list[str] | None = None,
    providers: list[str] | None = None,
    api_keys: list[str] | None = None,
) -> CostTotals | str:
    """Reads the total LLM cost, tokens and requests of the workspace, or of one pipeline, over a date range.

    Use this to answer how much a workspace or pipeline spent on LLM calls. Costs are in USD.
    Without dates the range is the last 30 days. ``start_date`` is inclusive and ``end_date`` exclusive, so
    for September 2026 pass ``2026-09-01T00:00:00Z`` and ``2026-10-01T00:00:00Z``.

    Narrow the figures with ``services``, ``providers`` and ``api_keys``. They combine: usage must match every
    kind you set, and any one value within a list.

    Check ``is_cost_complete`` before reporting ``total_cost``. When it is false, ``total_cost`` is a lower
    bound, not the final figure: say so, and name the models in ``unpriced_models`` (LLM calls with no price
    on file) and mention ``pending_generation_count`` (calls whose cost is still being calculated, which
    usually clears within a minute). ``total_requests`` counts queries, not individual LLM calls; one query
    can make several LLM calls.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Restrict to this pipeline. Omit for the whole workspace. Needs Pipelines read as well as
        Costs read.
    :param start_date: Inclusive start as an ISO timestamp. Defaults to 30 days before ``end_date``.
    :param end_date: Exclusive end as an ISO timestamp. Defaults to no upper bound.
    :param services: Restrict to these Services (``deployment`` in the API; a published Service endpoint, not a
        deployed pipeline, which is a pipeline). Each value is a Service name or its id, the ``key`` from
        ``get_cost_breakdown`` with ``group_by='deployment'``. Looking a Service up by name needs Services read as
        well as Costs read; an id needs only Costs read.
    :param providers: Restrict to these providers. Use the provider ids from ``get_cost_breakdown`` with
        ``group_by='provider'``, such as ``bedrock_converse`` or ``openai``, not their display names.
    :param api_keys: Restrict to these API keys. Use the key ids from ``get_cost_breakdown`` with
        ``group_by='api_key'``, never a key's secret token.
    :returns: The cost totals, or an error message.
    """
    try:
        return await client.cost(workspace=workspace).totals(
            pipeline_name=pipeline_name,
            start_date=start_date,
            end_date=end_date,
            services=services,
            providers=providers,
            api_keys=api_keys,
        )
    except (ResourceNotFoundError, BadRequestError, UnexpectedAPIError, RequestTimeoutError) as e:
        return _error_message(e, "get cost totals", workspace, pipeline_name, api_keys)


async def get_cost_over_time(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    services: list[str] | None = None,
    providers: list[str] | None = None,
    api_keys: list[str] | None = None,
) -> CostOverTime | str:
    """Reads the LLM cost of the workspace, or of one pipeline, per UTC day.

    Use this to see how spending developed, find the day a cost spike started, or compare periods.
    Costs are in USD. There is one point per day with usage; days without usage are left out, so a missing
    day means zero cost. A ``cost_total`` of null means that day had usage but none of it was priced.
    Without dates the range is the last 30 days. ``start_date`` is inclusive and ``end_date`` exclusive.
    The daily figures leave out unpriced LLM calls; use ``get_cost_totals`` to check whether the cost is
    complete.

    Narrow the figures with ``services``, ``providers`` and ``api_keys``. They combine: usage must match every
    kind you set, and any one value within a list.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Restrict to this pipeline. Omit for the whole workspace. Needs Pipelines read as well as
        Costs read.
    :param start_date: Inclusive start as an ISO timestamp. Defaults to 30 days before ``end_date``.
    :param end_date: Exclusive end as an ISO timestamp. Defaults to no upper bound.
    :param services: Restrict to these Services (``deployment`` in the API; a published Service endpoint, not a
        deployed pipeline, which is a pipeline). Each value is a Service name or its id, the ``key`` from
        ``get_cost_breakdown`` with ``group_by='deployment'``. Looking a Service up by name needs Services read as
        well as Costs read; an id needs only Costs read.
    :param providers: Restrict to these providers. Use the provider ids from ``get_cost_breakdown`` with
        ``group_by='provider'``, such as ``bedrock_converse`` or ``openai``, not their display names.
    :param api_keys: Restrict to these API keys. Use the key ids from ``get_cost_breakdown`` with
        ``group_by='api_key'``, never a key's secret token.
    :returns: The daily cost, or an error message.
    """
    try:
        return await client.cost(workspace=workspace).over_time(
            pipeline_name=pipeline_name,
            start_date=start_date,
            end_date=end_date,
            services=services,
            providers=providers,
            api_keys=api_keys,
        )
    except (ResourceNotFoundError, BadRequestError, UnexpectedAPIError, RequestTimeoutError) as e:
        return _error_message(e, "get cost over time", workspace, pipeline_name, api_keys)


async def get_cost_breakdown(
    *,
    client: AsyncClientProtocol,
    workspace: str,
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
) -> CostBreakdown | str:
    """Reads the LLM cost of the workspace, or of one pipeline, grouped by model, pipeline, Service or API key.

    Use this to find what drove the cost: which models, pipelines, Services or API keys spent the most.
    Costs are in USD. Results are sorted by cost, highest first, unless you set ``sort_by`` and ``sort_order``.
    Each entry has a ``key`` (a model or provider name, or a UUID for the other dimensions) and a readable
    ``label``. A deleted pipeline still shows up with ``group_by='pipeline'``, labelled with its UUID.
    ``total`` is the number of groups across all pages; when ``has_more`` is true, read the next
    ``page_number``. ``total_requests`` counts queries, not individual LLM calls. A ``cost_total`` of null
    means the group had usage but none of it was priced. Without dates the range is the last 30 days.

    A Service (``group_by='deployment'``) is a published Service endpoint; a deployed pipeline is a pipeline
    (``group_by='pipeline'``). The two overlap: a query through a Service that runs a pipeline counts in both,
    so never add Service groups and pipeline groups together. Usage that did not go through a Service shows up
    as ``__unattributed__`` under ``group_by='deployment'``.

    Narrow the breakdown with ``services``, ``providers`` and ``api_keys``, for example the models of one
    Service. They combine: usage must match every kind you set, and any one value within a list.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param group_by: The dimension to group by: model, workspace, pipeline, deployment (a Service), api_key or
        provider.
    :param pipeline_name: Restrict to this pipeline. Omit for the whole workspace. Needs Pipelines read as well as
        Costs read.
    :param start_date: Inclusive start as an ISO timestamp. Defaults to 30 days before ``end_date``.
    :param end_date: Exclusive end as an ISO timestamp. Defaults to no upper bound.
    :param sort_by: Sort by label, cost_total, total_tokens or total_requests. Defaults to cost_total.
    :param sort_order: ASC or DESC. Defaults to DESC.
    :param limit: Groups per page, from 1 to 100.
    :param page_number: The page to read, starting at 1.
    :param services: Restrict to these Services (``deployment`` in the API; a published Service endpoint, not a
        deployed pipeline, which is a pipeline). Each value is a Service name or its id, the ``key`` from
        ``get_cost_breakdown`` with ``group_by='deployment'``. Looking a Service up by name needs Services read as
        well as Costs read; an id needs only Costs read.
    :param providers: Restrict to these providers. Use the provider ids from ``get_cost_breakdown`` with
        ``group_by='provider'``, such as ``bedrock_converse`` or ``openai``, not their display names.
    :param api_keys: Restrict to these API keys. Use the key ids from ``get_cost_breakdown`` with
        ``group_by='api_key'``, never a key's secret token.
    :returns: One page of the breakdown, or an error message.
    """
    try:
        return await client.cost(workspace=workspace).breakdown(
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
    except (ResourceNotFoundError, BadRequestError, UnexpectedAPIError, RequestTimeoutError) as e:
        return _error_message(e, "get cost breakdown", workspace, pipeline_name, api_keys)
