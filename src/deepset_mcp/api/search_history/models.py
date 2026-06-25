# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for search history API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SearchHistoryEntry(BaseModel):
    """A single search history entry from the deepset platform (v1 API format).

    The v1 search history API returns entries with the following top-level fields.
    Key nested data:
    - The search query text is at ``request.query``.
    - The timestamp is at ``time`` (also aliased to ``created_at`` for convenience).
    - The pipeline name is at ``pipeline.name``.
    - Search results are in ``response`` (list of result entries).
    """

    model_config = {"extra": "allow"}

    # -- Record identifiers --
    search_history_id: str | None = Field(default=None, description="Unique identifier for this search history record")
    session_id: str | None = Field(default=None, description="Session identifier grouping related searches")

    # -- The search request --
    request: dict[str, Any] | None = Field(
        default=None,
        description="The original search request (contains 'query', 'filters', 'params', etc.)",
    )
    # Convenience field — extracted from request.query via model_validator
    query: str | None = Field(default=None, description="The search query text (extracted from request.query)")

    # -- The search response --
    response: list[dict[str, Any]] | None = Field(
        default=None, description="List of search result entries returned by the pipeline"
    )

    # -- Timing & status --
    time: str | None = Field(default=None, description="ISO-8601 timestamp when the search was performed")
    # Convenience alias — populated from `time` via model_validator
    created_at: str | None = Field(default=None, description="Alias for `time` — when the search was performed")
    duration: float | None = Field(default=None, description="End-to-end query duration in seconds")
    status: str | None = Field(default=None, description="Run status: 'success' or 'failed'")

    # -- Pipeline & version --
    pipeline: dict[str, Any] | None = Field(
        default=None, description="Pipeline metadata (contains 'name' and other pipeline info)"
    )
    pipeline_version_id: str | None = Field(default=None, description="UUID of the pipeline version used")
    client_source_path: str | None = Field(default=None, description="Client path that initiated the query")

    # -- User & auth --
    user: dict[str, Any] | None = Field(
        default=None, description="User who ran the search (contains 'id', 'given_name', 'family_name')"
    )
    api_key: dict[str, Any] | None = Field(default=None, description="API key used (contains 'id', 'name')")

    # -- Feedback, labels, notes --
    feedback: list[dict[str, Any]] | None = Field(default=None, description="User feedback on this search")
    labels: list[str] = Field(default_factory=list, description="Labels assigned to this search history record")
    note: str | None = Field(default=None, description="Free-text note attached to this search history record")

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        """Extract convenience fields from nested API response structure."""
        if not isinstance(data, dict):
            return data
        # Populate `query` from request.query if not already set at top level
        if not data.get("query") and isinstance(data.get("request"), dict):
            data["query"] = data["request"].get("query")
        # Populate `created_at` from `time` if not already set
        if not data.get("created_at") and data.get("time"):
            data["created_at"] = data["time"]
        return data

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
    """Full Haystack pipeline run trace (schema version haystack-trace/v1).

    Returned by the single-trace endpoint (``get_pipeline_trace``), which reads the
    full trace export. Includes every span with its complete tags (component input and
    output among them) as well as the run's log entries.
    """

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


class HaystackTraceV1Summary(BaseModel):
    """Trace summary returned by the traces *list* endpoint — no spans and no logs.

    The list endpoint deliberately omits span details and logs to keep the payload
    small. Use ``get_pipeline_trace`` to fetch the full trace (including spans with
    input/output and logs) for a single ``query_id``.
    """

    model_config = {"extra": "allow"}

    schema_version: str = Field(description="Trace schema version identifier")
    run_id: str = Field(description="Unique run identifier")
    started_at: str = Field(description="ISO-8601 timestamp when the run started")
    finished_at: str | None = Field(default=None, description="ISO-8601 timestamp when the run finished")
    duration_ms: float | None = Field(default=None, description="Total run duration in milliseconds")
    status: str | None = Field(default=None, description="Run status: 'success' or 'failed'")
    failure: HaystackTraceFailure | None = Field(default=None, description="Failure details if the run failed")


class _PipelineTraceBase(BaseModel):
    """Shared scalar fields of a pipeline trace record (v2 API format).

    Subclasses differ only in the shape of ``haystack_trace``: the list endpoint
    returns a summary, the single-trace endpoint returns the full trace.
    """

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


class PipelineTraceSummary(_PipelineTraceBase):
    """A pipeline trace as returned by the traces *list* endpoint.

    Carries run-level metadata (status, timing, failure) but no spans or logs. Use the
    ``query_id`` to fetch the full trace via ``get_pipeline_trace``.
    """

    haystack_trace: HaystackTraceV1Summary | None = Field(
        default=None, description="Run-level trace summary (no spans, no logs)"
    )


class PipelineTraceEntry(_PipelineTraceBase):
    """A single pipeline trace response from the deepset platform (v2 API format).

    Returned by ``get_pipeline_trace``. ``haystack_trace`` holds the full run trace:
    every span with complete tags (including component input/output) plus the logs.
    """

    haystack_trace: HaystackTraceV1 | None = Field(default=None, description="Full Haystack pipeline run trace")
