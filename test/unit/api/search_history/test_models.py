# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for search history models."""

from deepset_mcp.api.search_history.models import (
    HaystackTraceFailure,
    HaystackTraceLog,
    HaystackTraceSpan,
    HaystackTraceV1,
    PipelineTraceEntry,
    SearchHistoryEntry,
)

# ---------------------------------------------------------------------------
# SearchHistoryEntry
# ---------------------------------------------------------------------------


class TestSearchHistoryEntryNormalization:
    def test_query_extracted_from_nested_request(self) -> None:
        entry = SearchHistoryEntry(request={"query": "what is haystack?", "filters": None})
        assert entry.query == "what is haystack?"

    def test_top_level_query_wins_over_request_query(self) -> None:
        """If the API ever returns both, the explicit top-level value takes precedence."""
        entry = SearchHistoryEntry(query="explicit", request={"query": "nested"})
        assert entry.query == "explicit"

    def test_query_is_none_when_request_missing(self) -> None:
        entry = SearchHistoryEntry()
        assert entry.query is None

    def test_query_is_none_when_request_has_no_query_key(self) -> None:
        entry = SearchHistoryEntry(request={"filters": None})
        assert entry.query is None

    def test_created_at_populated_from_time(self) -> None:
        entry = SearchHistoryEntry(time="2024-01-15T10:30:00Z")
        assert entry.created_at == "2024-01-15T10:30:00Z"
        assert entry.time == "2024-01-15T10:30:00Z"

    def test_explicit_created_at_not_overridden_by_time(self) -> None:
        entry = SearchHistoryEntry(time="2024-01-15T10:30:00Z", created_at="2024-01-01T00:00:00Z")
        assert entry.created_at == "2024-01-01T00:00:00Z"

    def test_created_at_none_when_time_missing(self) -> None:
        entry = SearchHistoryEntry()
        assert entry.created_at is None


class TestSearchHistoryEntryFeedbackValidator:
    def test_feedback_dict_becomes_single_item_list(self) -> None:
        entry = SearchHistoryEntry(feedback={"score": 1, "comment": "good"})  # type: ignore[arg-type]
        assert entry.feedback == [{"score": 1, "comment": "good"}]

    def test_feedback_list_unchanged(self) -> None:
        fb = [{"score": 1}, {"score": -1}]
        entry = SearchHistoryEntry(feedback=fb)
        assert entry.feedback == fb

    def test_feedback_none_stays_none(self) -> None:
        entry = SearchHistoryEntry(feedback=None)
        assert entry.feedback is None

    def test_feedback_non_list_non_dict_becomes_none(self) -> None:
        entry = SearchHistoryEntry(feedback="invalid")  # type: ignore[arg-type]
        assert entry.feedback is None


class TestSearchHistoryEntryFields:
    def test_all_explicit_fields_populated(self) -> None:
        entry = SearchHistoryEntry(
            search_history_id="sh-001",
            request={"query": "test", "filters": None, "params": {}},
            time="2024-03-01T12:00:00Z",
            duration=0.75,
            status="success",
            session_id="sess-001",
            pipeline={"name": "my-pipeline"},
            pipeline_version_id="pv-001",
            client_source_path="/app/search",
            user={"id": "u-001", "given_name": "Alice", "family_name": "Smith"},
            api_key={"id": "ak-001", "name": "prod-key"},
            labels=["reviewed", "good"],
            note="Follow up needed",
        )
        assert entry.search_history_id == "sh-001"
        assert entry.query == "test"
        assert entry.time == "2024-03-01T12:00:00Z"
        assert entry.created_at == "2024-03-01T12:00:00Z"
        assert entry.duration == 0.75
        assert entry.status == "success"
        assert entry.session_id == "sess-001"
        assert entry.pipeline == {"name": "my-pipeline"}
        assert entry.pipeline_version_id == "pv-001"
        assert entry.client_source_path == "/app/search"
        assert entry.user == {"id": "u-001", "given_name": "Alice", "family_name": "Smith"}
        assert entry.api_key == {"id": "ak-001", "name": "prod-key"}
        assert entry.labels == ["reviewed", "good"]
        assert entry.note == "Follow up needed"

    def test_extra_fields_preserved(self) -> None:
        entry = SearchHistoryEntry(custom_field="surprise", another=42)  # type: ignore[call-arg]
        assert entry.model_extra is not None
        assert entry.model_extra.get("custom_field") == "surprise"
        assert entry.model_extra.get("another") == 42

    def test_labels_default_to_empty_list(self) -> None:
        entry = SearchHistoryEntry()
        assert entry.labels == []

    def test_defaults_are_none(self) -> None:
        entry = SearchHistoryEntry()
        for field in (
            "search_history_id",
            "request",
            "time",
            "duration",
            "status",
            "session_id",
            "pipeline",
            "pipeline_version_id",
            "client_source_path",
            "user",
            "api_key",
            "feedback",
            "note",
        ):
            assert getattr(entry, field) is None, f"Expected {field} to default to None"


class TestSearchHistoryEntryFromApiDict:
    """Simulate the actual shape returned by the v1 API."""

    def test_full_api_response_parses_correctly(self) -> None:
        api_dict = {
            "search_history_id": "aaaa-bbbb",
            "request": {"query": "Who made Haystack?", "filters": None, "params": {}},
            "response": [{"type": 1, "rank": 1, "documents": [], "score": 0.9}],
            "time": "2024-06-01T08:00:00Z",
            "duration": 1.1,
            "status": "success",
            "session_id": "sess-xyz",
            "pipeline_version_id": "pv-xyz",
            "client_source_path": "/chat",
            "user": {"id": "u-xyz", "given_name": "Bob", "family_name": "Jones"},
            "pipeline": {"name": "rag-pipeline"},
            "api_key": {"id": "ak-xyz", "name": "dev-key"},
            "feedback": {"score": 1, "comment": "Helpful"},
            "labels": ["important"],
            "note": "Check later",
        }
        entry = SearchHistoryEntry.model_validate(api_dict)

        assert entry.query == "Who made Haystack?"
        assert entry.created_at == "2024-06-01T08:00:00Z"
        assert entry.time == "2024-06-01T08:00:00Z"
        assert entry.duration == 1.1
        assert entry.status == "success"
        assert entry.pipeline == {"name": "rag-pipeline"}
        assert entry.labels == ["important"]
        assert entry.feedback == [{"score": 1, "comment": "Helpful"}]
        assert entry.note == "Check later"


# ---------------------------------------------------------------------------
# HaystackTraceSpan
# ---------------------------------------------------------------------------


class TestHaystackTraceSpan:
    def test_minimal_required_fields(self) -> None:
        span = HaystackTraceSpan(
            span_id="span-001",
            operation_name="BM25Retriever.run",
            start_time="2024-03-01T12:00:00Z",
        )
        assert span.span_id == "span-001"
        assert span.operation_name == "BM25Retriever.run"
        assert span.start_time == "2024-03-01T12:00:00Z"
        assert span.parent_span_id is None
        assert span.component is None
        assert span.end_time is None
        assert span.duration_ms is None
        assert span.tags == {}

    def test_all_fields(self) -> None:
        span = HaystackTraceSpan(
            span_id="span-002",
            parent_span_id="span-001",
            operation_name="EmbeddingRetriever.run",
            component="EmbeddingRetriever",
            start_time="2024-03-01T12:00:00.000Z",
            end_time="2024-03-01T12:00:00.150Z",
            duration_ms=150.0,
            tags={"retriever.top_k": 5, "retriever.query_embedding_model": "ada-002"},
        )
        assert span.parent_span_id == "span-001"
        assert span.component == "EmbeddingRetriever"
        assert span.duration_ms == 150.0
        assert span.tags["retriever.top_k"] == 5

    def test_extra_fields_allowed(self) -> None:
        span = HaystackTraceSpan(
            span_id="s1",
            operation_name="op",
            start_time="2024-01-01T00:00:00Z",
            future_field="value",  # type: ignore[call-arg]
        )
        assert span.model_extra is not None
        assert span.model_extra.get("future_field") == "value"


# ---------------------------------------------------------------------------
# HaystackTraceLog
# ---------------------------------------------------------------------------


class TestHaystackTraceLog:
    def test_basic_log_entry(self) -> None:
        log = HaystackTraceLog(
            logger="haystack.pipeline",
            level="INFO",
            message="Running pipeline with query: test",
            timestamp="2024-03-01T12:00:00Z",
        )
        assert log.logger == "haystack.pipeline"
        assert log.level == "INFO"
        assert log.message == "Running pipeline with query: test"
        assert log.timestamp == "2024-03-01T12:00:00Z"
        assert log.extra_fields == {}

    def test_log_with_extra_fields(self) -> None:
        log = HaystackTraceLog(
            logger="haystack.components.retrievers",
            level="WARNING",
            message="Slow retrieval detected",
            timestamp="2024-03-01T12:00:01Z",
            extra_fields={"component": "BM25Retriever", "duration_ms": 2500},
        )
        assert log.extra_fields["component"] == "BM25Retriever"
        assert log.extra_fields["duration_ms"] == 2500


# ---------------------------------------------------------------------------
# HaystackTraceFailure
# ---------------------------------------------------------------------------


class TestHaystackTraceFailure:
    def test_failure_fields(self) -> None:
        failure = HaystackTraceFailure(
            type="ValueError",
            message="Invalid query format",
            stacktrace=[
                "Traceback (most recent call last):",
                '  File "pipeline.py", line 42, in run',
                "ValueError: Invalid query format",
            ],
        )
        assert failure.type == "ValueError"
        assert failure.message == "Invalid query format"
        assert len(failure.stacktrace) == 3
        assert "ValueError: Invalid query format" in failure.stacktrace


# ---------------------------------------------------------------------------
# HaystackTraceV1
# ---------------------------------------------------------------------------


class TestHaystackTraceV1:
    def test_minimal_trace(self) -> None:
        trace = HaystackTraceV1(
            schema_version="haystack-trace/v1",
            run_id="run-001",
            started_at="2024-03-01T12:00:00Z",
            status="success",
            traces=[],
            logs=[],
        )
        assert trace.schema_version == "haystack-trace/v1"
        assert trace.run_id == "run-001"
        assert trace.status == "success"
        assert trace.traces == []
        assert trace.logs == []
        assert trace.failure is None
        assert trace.finished_at is None
        assert trace.duration_ms is None

    def test_full_trace_with_spans_logs_and_failure(self) -> None:
        trace = HaystackTraceV1(
            schema_version="haystack-trace/v1",
            run_id="run-002",
            started_at="2024-03-01T12:00:00Z",
            finished_at="2024-03-01T12:00:01.5Z",
            duration_ms=1500.0,
            status="failed",
            traces=[
                HaystackTraceSpan(
                    span_id="s1",
                    operation_name="Pipeline.run",
                    start_time="2024-03-01T12:00:00Z",
                )
            ],
            logs=[
                HaystackTraceLog(
                    logger="haystack",
                    level="ERROR",
                    message="Pipeline failed",
                    timestamp="2024-03-01T12:00:01Z",
                )
            ],
            failure=HaystackTraceFailure(
                type="RuntimeError",
                message="Component timed out",
                stacktrace=["RuntimeError: Component timed out"],
            ),
        )
        assert len(trace.traces) == 1
        assert len(trace.logs) == 1
        assert trace.failure is not None
        assert trace.failure.type == "RuntimeError"
        assert trace.duration_ms == 1500.0

    def test_extra_fields_preserved(self) -> None:
        trace = HaystackTraceV1(
            schema_version="haystack-trace/v1",
            run_id="run-003",
            started_at="2024-03-01T12:00:00Z",
            status="success",
            traces=[],
            logs=[],
            new_field_from_future_api="value",  # type: ignore[call-arg]
        )
        assert trace.model_extra is not None
        assert trace.model_extra.get("new_field_from_future_api") == "value"

    def test_validates_from_api_dict(self) -> None:
        raw = {
            "schema_version": "haystack-trace/v1",
            "run_id": "run-abc",
            "started_at": "2024-03-01T12:00:00Z",
            "finished_at": "2024-03-01T12:00:01Z",
            "duration_ms": 1000.0,
            "status": "success",
            "traces": [
                {
                    "span_id": "sp-1",
                    "operation_name": "BM25Retriever.run",
                    "start_time": "2024-03-01T12:00:00Z",
                    "tags": {"top_k": 10},
                }
            ],
            "logs": [
                {
                    "logger": "haystack",
                    "level": "INFO",
                    "message": "Done",
                    "timestamp": "2024-03-01T12:00:01Z",
                }
            ],
        }
        trace = HaystackTraceV1.model_validate(raw)
        assert len(trace.traces) == 1
        assert trace.traces[0].span_id == "sp-1"
        assert trace.traces[0].tags["top_k"] == 10
        assert len(trace.logs) == 1


# ---------------------------------------------------------------------------
# PipelineTraceEntry
# ---------------------------------------------------------------------------


class TestPipelineTraceEntry:
    def test_minimal_entry(self) -> None:
        entry = PipelineTraceEntry(
            query_id="qid-001",
            query="What is Haystack?",
            duration_s=1.0,
            created_at="2024-03-01T12:00:00Z",
        )
        assert entry.query_id == "qid-001"
        assert entry.query == "What is Haystack?"
        assert entry.duration_s == 1.0
        assert entry.created_at == "2024-03-01T12:00:00Z"
        assert entry.status is None
        assert entry.haystack_trace is None

    def test_full_entry_with_nested_trace(self) -> None:
        entry = PipelineTraceEntry(
            query_id="qid-002",
            query="Summarise the document",
            status="success",
            duration_s=2.5,
            created_at="2024-03-01T13:00:00Z",
            client_source_path="/api/v1/search",
            pipeline_version_id="pv-abc",
            pipeline_version_name="v3",
            pipeline_version_number=3,
            api_key={"id": "ak-001", "name": "prod"},
            feedback={"score": 1},
            user_id="u-001",
            haystack_trace=HaystackTraceV1(
                schema_version="haystack-trace/v1",
                run_id="run-x",
                started_at="2024-03-01T13:00:00Z",
                status="success",
                traces=[],
                logs=[],
            ),
        )
        assert entry.status == "success"
        assert entry.pipeline_version_name == "v3"
        assert entry.pipeline_version_number == 3
        assert entry.haystack_trace is not None
        assert entry.haystack_trace.run_id == "run-x"

    def test_failed_entry_with_failure_info_in_trace(self) -> None:
        entry = PipelineTraceEntry(
            query_id="qid-003",
            query="Bad input",
            status="failed",
            duration_s=0.1,
            created_at="2024-03-01T14:00:00Z",
            haystack_trace=HaystackTraceV1(
                schema_version="haystack-trace/v1",
                run_id="run-fail",
                started_at="2024-03-01T14:00:00Z",
                status="failed",
                traces=[],
                logs=[],
                failure=HaystackTraceFailure(
                    type="ValueError",
                    message="bad input",
                    stacktrace=["ValueError: bad input"],
                ),
            ),
        )
        assert entry.status == "failed"
        assert entry.haystack_trace is not None
        assert entry.haystack_trace.failure is not None
        assert entry.haystack_trace.failure.type == "ValueError"

    def test_extra_fields_preserved(self) -> None:
        entry = PipelineTraceEntry(
            query_id="qid-004",
            query="q",
            duration_s=0.5,
            created_at="2024-03-01T12:00:00Z",
            future_field="extra",  # type: ignore[call-arg]
        )
        assert entry.model_extra is not None
        assert entry.model_extra.get("future_field") == "extra"

    def test_validates_from_full_api_dict(self) -> None:
        raw = {
            "query_id": "qid-api",
            "query": "Search for something",
            "status": "success",
            "duration_s": 0.8,
            "created_at": "2024-04-01T09:00:00Z",
            "client_source_path": "/v1/search",
            "pipeline_version_id": "pv-001",
            "pipeline_version_name": "production",
            "pipeline_version_number": 7,
            "api_key": {"id": "ak-001", "name": "main-key"},
            "user_id": "u-999",
            "haystack_trace": {
                "schema_version": "haystack-trace/v1",
                "run_id": "run-api",
                "started_at": "2024-04-01T09:00:00Z",
                "finished_at": "2024-04-01T09:00:00.800Z",
                "duration_ms": 800.0,
                "status": "success",
                "traces": [
                    {
                        "span_id": "s-001",
                        "operation_name": "PromptBuilder.run",
                        "start_time": "2024-04-01T09:00:00Z",
                        "component": "PromptBuilder",
                        "tags": {},
                    }
                ],
                "logs": [],
            },
        }
        entry = PipelineTraceEntry.model_validate(raw)

        assert entry.query_id == "qid-api"
        assert entry.status == "success"
        assert entry.pipeline_version_number == 7
        assert entry.haystack_trace is not None
        assert len(entry.haystack_trace.traces) == 1
        assert entry.haystack_trace.traces[0].component == "PromptBuilder"
