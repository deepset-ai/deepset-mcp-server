# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the LLM cost stats API."""

from typing import Literal

from pydantic import BaseModel, Field

CostGroupBy = Literal["model", "workspace", "pipeline", "deployment", "api_key", "provider"]
CostSortBy = Literal["label", "cost_total", "total_tokens", "total_requests"]


class UnpricedModel(BaseModel):
    """A model with LLM calls that have no price, so their cost is missing from the totals."""

    model: str | None = Field(description="The model name on the LLM calls. Null for calls without a model name.")
    generation_count: int = Field(description="Number of unpriced LLM calls for this model")
    total_tokens: int
    last_seen_at: str


class CostTotals(BaseModel):
    """LLM cost, tokens and requests summed over the filtered scope."""

    total_cost: float | None = Field(description="Sum of priced LLM calls' cost. Null when nothing was priced.")
    total_tokens: int
    total_requests: int = Field(description="Number of distinct queries, not the number of LLM calls")
    avg_cost_per_request: float | None
    is_cost_complete: bool = Field(
        description="False when any LLM call is unpriced or pending: total_cost is then a lower bound"
    )
    priced_generation_count: int = 0
    unpriced_generation_count: int = 0
    pending_generation_count: int = Field(
        default=0, description="LLM calls whose cost is still being calculated. Usually clears within a minute."
    )
    unpriced_tokens: int = 0
    pending_tokens: int = 0
    unpriced_models: list[UnpricedModel] = Field(default_factory=list)
    currency: str = "USD"


class CostOverTimePoint(BaseModel):
    """The cost of one UTC day."""

    date: str = Field(description="Start of the UTC day")
    cost_total: float | None = Field(description="Null when nothing that day was priced")


class CostOverTime(BaseModel):
    """Daily cost, ordered by date. Days without usage are left out."""

    data: list[CostOverTimePoint]


class CostBreakdownEntry(BaseModel):
    """The cost of one group in a breakdown."""

    key: str = Field(
        description="Model or provider name, or the UUID of the workspace, pipeline, deployment or API key"
    )
    label: str = Field(description="Readable name; equals key when the object was deleted")
    cost_total: float | None = Field(description="Null when nothing in this group was priced")
    total_tokens: int
    total_requests: int = Field(description="Number of distinct queries, not the number of LLM calls")
    workspace_id: str | None = None
    workspace_name: str | None = None


class CostBreakdown(BaseModel):
    """One page of cost grouped by a dimension."""

    group_by: str
    data: list[CostBreakdownEntry]
    total: int = Field(description="Number of groups across all pages")
    has_more: bool
