# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for SearchHistoryResource."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.models import DeepsetPipeline, PipelineServiceLevel
from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
from deepset_mcp.api.search_history.resource import SearchHistoryResource
from deepset_mcp.api.shared_models import DeepsetUser, PaginatedResponse
from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.api.workspace.models import Workspace
from test.unit.conftest import BaseFakeClient

# Fixed test constants
WORKSPACE_NAME = "my-workspace"
WORKSPACE_UUID = "76d361b5-a551-40e3-a5c9-fdbc20028021"
PIPELINE_NAME = "my-pipeline"
PIPELINE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
QUERY_UUID = "11111111-2222-3333-4444-555555555555"

TRACES_ENDPOINT = f"v2/workspaces/{WORKSPACE_UUID}/pipelines/{PIPELINE_UUID}/search_history/traces"
SINGLE_TRACE_ENDPOINT = f"v2/workspaces/{WORKSPACE_UUID}/pipelines/{PIPELINE_UUID}/search_history/{QUERY_UUID}/trace"


def make_workspace() -> Workspace:
    return Workspace(
        name=WORKSPACE_NAME,
        workspace_id=UUID(WORKSPACE_UUID),
        languages={},
        default_idle_timeout_in_seconds=43200,
    )


def make_pipeline(pipeline_id: str = PIPELINE_UUID, name: str = PIPELINE_NAME) -> DeepsetPipeline:
    return DeepsetPipeline.model_validate(
        {
            "pipeline_id": pipeline_id,
            "name": name,
            "status": "DEPLOYED",
            "service_level": "PRODUCTION",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": {"user_id": "u-001", "given_name": "Test", "family_name": "User"},
        }
    )


def make_trace_entry_dict(
    query_id: str = "qid-001",
    query: str = "What is Haystack?",
    status: str = "success",
    created_at: str = "2024-03-01T12:00:00Z",
    duration_s: float = 1.0,
) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "query": query,
        "status": status,
        "duration_s": duration_s,
        "created_at": created_at,
        "haystack_trace": {
            "schema_version": "haystack-trace/v1",
            "run_id": f"run-{query_id}",
            "started_at": created_at,
            "status": status,
            "traces": [
                {
                    "span_id": f"span-{query_id}",
                    "operation_name": "Pipeline.run",
                    "start_time": created_at,
                    "tags": {},
                }
            ],
            "logs": [],
        },
    }


class FakeWorkspaceResource:
    """Fake workspace resource that returns a predefined Workspace or raises."""

    def __init__(self, result: Workspace | Exception) -> None:
        self._result = result
        self.calls: list[str] = []

    async def get(self, workspace_name: str) -> Workspace:
        self.calls.append(workspace_name)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakePipelineResource:
    """Fake pipeline resource that returns a predefined DeepsetPipeline or raises."""

    def __init__(self, result: DeepsetPipeline | Exception) -> None:
        self._result = result
        self.calls: list[tuple[str, bool]] = []

    async def get(self, pipeline_name: str, include_yaml: bool = True) -> DeepsetPipeline:
        self.calls.append((pipeline_name, include_yaml))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeTracesClient(BaseFakeClient):
    """Client that delegates workspace/pipeline lookups to fake resources
    and HTTP calls to the BaseFakeClient response dict."""

    def __init__(
        self,
        http_responses: dict[str, Any],
        workspace_resource: FakeWorkspaceResource | None = None,
        pipeline_resource: FakePipelineResource | None = None,
    ) -> None:
        super().__init__(responses=http_responses)
        self._workspace_resource = workspace_resource or FakeWorkspaceResource(make_workspace())
        self._pipeline_resource = pipeline_resource or FakePipelineResource(make_pipeline())

    def workspaces(self) -> FakeWorkspaceResource:  # type: ignore[override]
        return self._workspace_resource

    def pipelines(self, workspace: str) -> FakePipelineResource:  # type: ignore[override]
        return self._pipeline_resource


# ---------------------------------------------------------------------------
# SearchHistoryResource.list
# ---------------------------------------------------------------------------


class TestSearchHistoryResourceList:
    @pytest.mark.asyncio
    async def test_list_success_returns_entries(self) -> None:
        items = [
            {"search_history_id": "sh-1", "request": {"query": "q1"}, "time": "2024-03-01T12:00:00Z"},
            {"search_history_id": "sh-2", "request": {"query": "q2"}, "time": "2024-03-01T11:00:00Z"},
        ]
        client = BaseFakeClient(
            responses={
                "v1/workspaces/my-workspace/search_history": {
                    "data": items,
                    "has_more": False,
                    "total": 2,
                }
            }
        )
        resource = SearchHistoryResource(client=client, workspace="my-workspace")

        result = await resource.list()

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.total == 2
        assert result.data[0].query == "q1"
        assert result.data[1].query == "q2"

    @pytest.mark.asyncio
    async def test_list_uses_correct_endpoint(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/test-ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="test-ws")

        await resource.list()

        assert client.requests[0]["endpoint"] == "v1/workspaces/test-ws/search_history"

    @pytest.mark.asyncio
    async def test_list_sort_params_forwarded_as_field_and_order(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list(sort_field="duration", sort_order="ASC")

        params = client.requests[0]["params"]
        assert params["field"] == "duration"
        assert params["order"] == "ASC"
        assert "sort_field" not in params
        assert "sort_order" not in params

    @pytest.mark.asyncio
    async def test_list_default_sort_params(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list()

        params = client.requests[0]["params"]
        assert params["field"] == "created_at"
        assert params["order"] == "DESC"

    @pytest.mark.asyncio
    async def test_list_after_cursor_forwarded(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list(after="2024-01-01T00:00:00Z")

        assert client.requests[0]["params"]["after"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_list_omits_after_when_none(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list()

        assert "after" not in client.requests[0]["params"]

    @pytest.mark.asyncio
    async def test_list_query_filter_forwarded(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": [], "has_more": False, "total": 0}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list(query_filter="status eq 'failed'")

        assert client.requests[0]["params"]["filter"] == "status eq 'failed'"

    @pytest.mark.asyncio
    async def test_list_cursor_extracted_from_time_field(self) -> None:
        """next_cursor is built from the `time` field (not `created_at`) of the last item."""
        items = [
            {"search_history_id": "sh-1", "time": "2024-03-01T12:00:00Z"},
            {"search_history_id": "sh-2", "time": "2024-03-01T10:00:00Z"},
        ]
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": items, "has_more": True, "total": 20}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        result = await resource.list()

        assert result.has_more is True
        assert result.next_cursor == "2024-03-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_list_no_cursor_when_has_more_false(self) -> None:
        items = [{"search_history_id": "sh-1", "time": "2024-03-01T12:00:00Z"}]
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": {"data": items, "has_more": False, "total": 1}}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        result = await resource.list()

        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_list_null_response_returns_empty(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": TransportResponse(text="", status_code=200, json=None)}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        result = await resource.list()

        assert result.data == []
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_404_raises_resource_not_found(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": TransportResponse(text="Not Found", status_code=404)}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        with pytest.raises(ResourceNotFoundError):
            await resource.list()

    @pytest.mark.asyncio
    async def test_list_500_raises_unexpected_api_error(self) -> None:
        client = BaseFakeClient(
            responses={"v1/workspaces/ws/search_history": TransportResponse(text="Internal Error", status_code=500)}
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        with pytest.raises(UnexpectedAPIError):
            await resource.list()


# ---------------------------------------------------------------------------
# SearchHistoryResource.list_pipeline
# ---------------------------------------------------------------------------


class TestSearchHistoryResourceListPipeline:
    @pytest.mark.asyncio
    async def test_list_pipeline_uses_archive_endpoint(self) -> None:
        client = BaseFakeClient(
            responses={
                "v1/workspaces/ws/pipelines/pipe/search_history_archive": {"data": [], "has_more": False, "total": 0}
            }
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list_pipeline("pipe")

        assert client.requests[0]["endpoint"] == "v1/workspaces/ws/pipelines/pipe/search_history_archive"

    @pytest.mark.asyncio
    async def test_list_pipeline_sort_params_forwarded_as_field_and_order(self) -> None:
        client = BaseFakeClient(
            responses={
                "v1/workspaces/ws/pipelines/pipe/search_history_archive": {"data": [], "has_more": False, "total": 0}
            }
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        await resource.list_pipeline("pipe", sort_field="query", sort_order="ASC")

        params = client.requests[0]["params"]
        assert params["field"] == "query"
        assert params["order"] == "ASC"

    @pytest.mark.asyncio
    async def test_list_pipeline_cursor_from_time_field(self) -> None:
        items = [
            {"search_history_id": "sh-1", "time": "2024-03-01T12:00:00Z"},
            {"search_history_id": "sh-2", "time": "2024-03-01T09:00:00Z"},
        ]
        client = BaseFakeClient(
            responses={
                "v1/workspaces/ws/pipelines/pipe/search_history_archive": {"data": items, "has_more": True, "total": 50}
            }
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        result = await resource.list_pipeline("pipe")

        assert result.next_cursor == "2024-03-01T09:00:00Z"

    @pytest.mark.asyncio
    async def test_list_pipeline_returns_entries(self) -> None:
        items = [
            {"search_history_id": "sh-1", "request": {"query": "pipeline test"}, "time": "2024-03-01T10:00:00Z"},
        ]
        client = BaseFakeClient(
            responses={
                "v1/workspaces/ws/pipelines/pipe/search_history_archive": {"data": items, "has_more": False, "total": 1}
            }
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        result = await resource.list_pipeline("pipe")

        assert len(result.data) == 1
        assert result.data[0].query == "pipeline test"

    @pytest.mark.asyncio
    async def test_list_pipeline_404_raises_resource_not_found(self) -> None:
        client = BaseFakeClient(
            responses={
                "v1/workspaces/ws/pipelines/gone/search_history_archive": TransportResponse(
                    text="Not Found", status_code=404
                )
            }
        )
        resource = SearchHistoryResource(client=client, workspace="ws")

        with pytest.raises(ResourceNotFoundError):
            await resource.list_pipeline("gone")


# ---------------------------------------------------------------------------
# SearchHistoryResource.list_pipeline_traces
# ---------------------------------------------------------------------------


class TestSearchHistoryResourceListPipelineTraces:
    @pytest.mark.asyncio
    async def test_list_pipeline_traces_success(self) -> None:
        entries = [
            make_trace_entry_dict("qid-001", "first query"),
            make_trace_entry_dict("qid-002", "second query"),
        ]
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": entries, "has_more": False, "total": 2}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.list_pipeline_traces(PIPELINE_NAME)

        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 2
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_entry_fields(self) -> None:
        entry = make_trace_entry_dict("qid-abc", "precise query", status="success", duration_s=0.75)
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [entry], "has_more": False, "total": 1}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.list_pipeline_traces(PIPELINE_NAME)

        trace = result.data[0]
        assert isinstance(trace, PipelineTraceEntry)
        assert trace.query_id == "qid-abc"
        assert trace.query == "precise query"
        assert trace.status == "success"
        assert trace.duration_s == 0.75
        assert trace.haystack_trace is not None

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_resolves_workspace_uuid(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        assert client._workspace_resource.calls == [WORKSPACE_NAME]

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_resolves_pipeline_uuid_with_include_yaml_false(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        assert client._pipeline_resource.calls == [(PIPELINE_NAME, False)]

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_calls_v2_endpoint(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        # Find the traces HTTP request (the 3rd request after two lookups)
        endpoints = [r["endpoint"] for r in client.requests]
        assert TRACES_ENDPOINT in endpoints

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_sort_params_forwarded_as_field_and_order(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME, sort_field="duration", sort_order="ASC")

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert traces_req["params"]["field"] == "duration"
        assert traces_req["params"]["order"] == "ASC"
        assert "sort_field" not in traces_req["params"]
        assert "sort_order" not in traces_req["params"]

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_default_sort_params(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert traces_req["params"]["field"] == "created_at"
        assert traces_req["params"]["order"] == "DESC"

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_after_cursor_forwarded(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME, after="2024-01-15T08:00:00Z")

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert traces_req["params"]["after"] == "2024-01-15T08:00:00Z"

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_omits_after_when_none(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert "after" not in traces_req["params"]

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_query_filter_forwarded(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME, query_filter="status eq 'failed'")

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert traces_req["params"]["filter"] == "status eq 'failed'"

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_cursor_from_created_at(self) -> None:
        """next_cursor for traces is extracted from `created_at` (the v2 field name)."""
        entries = [
            make_trace_entry_dict("qid-1", created_at="2024-03-01T12:00:00Z"),
            make_trace_entry_dict("qid-2", created_at="2024-03-01T10:00:00Z"),
        ]
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": entries, "has_more": True, "total": 20}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.list_pipeline_traces(PIPELINE_NAME)

        assert result.has_more is True
        assert result.next_cursor == "2024-03-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_no_cursor_when_not_has_more(self) -> None:
        entries = [make_trace_entry_dict("qid-1", created_at="2024-03-01T12:00:00Z")]
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": entries, "has_more": False, "total": 1}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.list_pipeline_traces(PIPELINE_NAME)

        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_null_http_response_returns_empty(self) -> None:
        client = FakeTracesClient(
            http_responses={TRACES_ENDPOINT: TransportResponse(text="", status_code=200, json=None)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.list_pipeline_traces(PIPELINE_NAME)

        assert result.data == []
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_workspace_not_found_propagates(self) -> None:
        client = FakeTracesClient(
            http_responses={},
            workspace_resource=FakeWorkspaceResource(ResourceNotFoundError()),
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.list_pipeline_traces(PIPELINE_NAME)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_pipeline_not_found_propagates(self) -> None:
        client = FakeTracesClient(
            http_responses={},
            pipeline_resource=FakePipelineResource(ResourceNotFoundError()),
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.list_pipeline_traces(PIPELINE_NAME)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_404_raises_resource_not_found(self) -> None:
        client = FakeTracesClient(
            http_responses={TRACES_ENDPOINT: TransportResponse(text="Not Found", status_code=404)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.list_pipeline_traces(PIPELINE_NAME)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_500_raises_unexpected_api_error(self) -> None:
        client = FakeTracesClient(
            http_responses={TRACES_ENDPOINT: TransportResponse(text="Internal Error", status_code=500)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(UnexpectedAPIError):
            await resource.list_pipeline_traces(PIPELINE_NAME)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_limit_forwarded(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME, limit=5)

        traces_req = next(r for r in client.requests if r["endpoint"] == TRACES_ENDPOINT)
        assert traces_req["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_uses_uuid_in_endpoint_not_name(self) -> None:
        """The endpoint must contain the workspace/pipeline UUIDs, not their names."""
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        endpoints_called = [r["endpoint"] for r in client.requests]
        traces_call = next(e for e in endpoints_called if "traces" in e)
        assert WORKSPACE_UUID in traces_call
        assert PIPELINE_UUID in traces_call
        assert WORKSPACE_NAME not in traces_call
        assert PIPELINE_NAME not in traces_call

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_uses_v2_prefix(self) -> None:
        client = FakeTracesClient(http_responses={TRACES_ENDPOINT: {"data": [], "has_more": False, "total": 0}})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.list_pipeline_traces(PIPELINE_NAME)

        traces_endpoint = next(r["endpoint"] for r in client.requests if "traces" in r["endpoint"])
        assert traces_endpoint.startswith("v2/")


# ---------------------------------------------------------------------------
# SearchHistoryResource.get_pipeline_trace
# ---------------------------------------------------------------------------


class TestSearchHistoryResourceGetPipelineTrace:
    @pytest.mark.asyncio
    async def test_get_pipeline_trace_success(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID, "Get single trace")
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        assert isinstance(result, PipelineTraceEntry)
        assert result.query_id == QUERY_UUID
        assert result.query == "Get single trace"
        assert result.haystack_trace is not None

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_calls_correct_v2_endpoint(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID)
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        endpoints = [r["endpoint"] for r in client.requests]
        assert SINGLE_TRACE_ENDPOINT in endpoints

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_endpoint_contains_uuids_not_names(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID)
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        trace_endpoint = next(
            r["endpoint"] for r in client.requests if "trace" in r["endpoint"] and QUERY_UUID in r["endpoint"]
        )
        assert WORKSPACE_UUID in trace_endpoint
        assert PIPELINE_UUID in trace_endpoint
        assert QUERY_UUID in trace_endpoint
        assert WORKSPACE_NAME not in trace_endpoint
        assert PIPELINE_NAME not in trace_endpoint

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_uses_v2_prefix(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID)
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        trace_endpoint = next(r["endpoint"] for r in client.requests if QUERY_UUID in r["endpoint"])
        assert trace_endpoint.startswith("v2/")

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_null_response_returns_none(self) -> None:
        client = FakeTracesClient(
            http_responses={SINGLE_TRACE_ENDPOINT: TransportResponse(text="", status_code=200, json=None)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        result = await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_resolves_workspace_uuid(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID)
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        assert client._workspace_resource.calls == [WORKSPACE_NAME]

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_resolves_pipeline_uuid_with_include_yaml_false(self) -> None:
        trace_dict = make_trace_entry_dict(QUERY_UUID)
        client = FakeTracesClient(http_responses={SINGLE_TRACE_ENDPOINT: trace_dict})
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

        assert client._pipeline_resource.calls == [(PIPELINE_NAME, False)]

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_pipeline_not_found_propagates(self) -> None:
        client = FakeTracesClient(
            http_responses={},
            pipeline_resource=FakePipelineResource(ResourceNotFoundError()),
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_workspace_not_found_propagates(self) -> None:
        client = FakeTracesClient(
            http_responses={},
            workspace_resource=FakeWorkspaceResource(ResourceNotFoundError()),
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_404_raises_resource_not_found(self) -> None:
        client = FakeTracesClient(
            http_responses={SINGLE_TRACE_ENDPOINT: TransportResponse(text="Not Found", status_code=404)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(ResourceNotFoundError):
            await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_500_raises_unexpected_api_error(self) -> None:
        client = FakeTracesClient(
            http_responses={SINGLE_TRACE_ENDPOINT: TransportResponse(text="Server Error", status_code=500)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(UnexpectedAPIError):
            await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_bad_request_raises_error(self) -> None:
        client = FakeTracesClient(
            http_responses={SINGLE_TRACE_ENDPOINT: TransportResponse(text="Bad Request", status_code=400)}
        )
        resource = SearchHistoryResource(client=client, workspace=WORKSPACE_NAME)

        with pytest.raises(BadRequestError):
            await resource.get_pipeline_trace(PIPELINE_NAME, QUERY_UUID)
