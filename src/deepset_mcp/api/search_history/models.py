# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for search history API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchHistoryEntry(BaseModel):
    """A single search history entry from the deepset platform.

    Contains query, answers, prompts, feedback, and other metadata.
    """

    model_config = {"extra": "allow"}

    query: str | None = Field(default=None, description="The search query that was executed")
    answer: str | None = Field(default=None, description="The answer returned by the pipeline")
    created_at: str | None = Field(default=None, description="When the search was performed")
    pipeline_name: str | None = Field(default=None, description="Name of the pipeline used")
    feedback: list[dict[str, Any]] | None = Field(default=None, description="User feedback on the search")

    @field_validator("feedback", mode="before")
    @classmethod
    def _feedback_to_list(cls, v: Any) -> list[dict[str, Any]] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None


class HaystackTraceSpan(BaseModel):
    """A single span in a Haystack pipeline trace."""

    model_config = {"extra": "allow"}

    span_id: str = Field(description="Unique identifier for this span")
    parent_span_id: str | None = Field(default=None, description="Parent span ID, if this is a child span")
    operation_name: str = Field(description="Name of the operation performed in this span")
    component: str | None = Field(default=None, description="Haystack component that produced this span")
    start_time: str = Field(description="ISO-8601 timestamp when the span started")
    end_time: str | None = Field(default=None, description="ISO-8601 timestamp when the span ended")
    duration_ms: float | None = Field(default=None, description="Duration of the span in milliseconds")
    tags: dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value tags attached to the span")


class HaystackTraceLog(BaseModel):
    """A log entry emitted during a Haystack pipeline run."""

    model_config = {"extra": "allow"}

    logger: str = Field(description="Logger name that emitted this entry")
    level: str = Field(description="Log level (e.g. INFO, WARNING, ERROR)")
    message: str = Field(description="Log message text")
    timestamp: str = Field(description="ISO-8601 timestamp of the log entry")
    extra_fields: dict[str, Any] = Field(default_factory=dict, description="Additional structured fields")


class HaystackTraceFailure(BaseModel):
    """Failure information for a Haystack pipeline run."""

    type: str = Field(description="Exception type name")
    message: str = Field(description="Exception message")
    stacktrace: list[str] = Field(description="Stack trace lines")


class HaystackTraceV1(BaseModel):
    """Full Haystack pipeline run trace (schema version haystack-trace/v1)."""

    model_config = {"extra": "allow"}

    schema_version: str = Field(description="Trace schema version identifier")
    run_id: str = Field(description="Unique run identifier")
    started_at: str = Field(description="ISO-8601 timestamp when the run started")
    finished_at: str | None = Field(default=None, description="ISO-8601 timestamp when the run finished")
    duration_ms: float | None = Field(default=None, description="Total run duration in milliseconds")
    status: str | None = Field(default=None, description="Run status: 'success' or 'failed'")
    traces: list[HaystackTraceSpan] = Field(default_factory=list, description="Ordered list of trace spans")
    logs: list[HaystackTraceLog] = Field(default_factory=list, description="Log entries emitted during the run")
    failure: HaystackTraceFailure | None = Field(default=None, description="Failure details if the run failed")


class PipelineTraceEntry(BaseModel):
    """A single pipeline trace response from the deepset platform."""

    model_config = {"extra": "allow"}

    query_id: str = Field(description="Unique identifier for the search query")
    query: str = Field(description="The search query text that was executed")
    status: str | None = Field(default=None, description="Run status: 'success' or 'failed'")
    duration_s: float = Field(description="End-to-end query duration in seconds")
    created_at: str = Field(description="ISO-8601 timestamp when the query was executed")
    client_source_path: str | None = Field(default=None, description="Client path that initiated the query")
    pipeline_version_id: str | None = Field(default=None, description="UUID of the pipeline version used")
    pipeline_version_name: str | None = Field(default=None, description="Name of the pipeline version used")
    pipeline_version_number: int | None = Field(default=None, description="Number of the pipeline version used")
    api_key: dict[str, Any] | None = Field(default=None, description="API key metadata (id, name)")
    feedback: dict[str, Any] | None = Field(default=None, description="Aggregated user feedback for this query")
    user_id: str | None = Field(default=None, description="UUID of the user who ran the query")
    haystack_trace: HaystackTraceV1 | None = Field(default=None, description="Full Haystack pipeline run trace")
