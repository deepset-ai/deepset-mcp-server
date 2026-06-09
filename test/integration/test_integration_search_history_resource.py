# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for SearchHistoryResource.

Most tests run against a freshly created workspace (empty search history).
Tests that require real search history data are gated behind the
``DEEPSET_TEST_PIPELINE`` environment variable — set it to the name of a
pipeline in your workspace that has existing query history.
"""

import os

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.search_history.models import PipelineTraceEntry, SearchHistoryEntry
from deepset_mcp.api.search_history.resource import SearchHistoryResource
from deepset_mcp.api.shared_models import PaginatedResponse

pytestmark = pytest.mark.integration

# Minimal pipeline YAML — valid YAML that can be created without deployment
_MINIMAL_YAML = """
components:
  answer_builder:
    type: haystack.components.builders.answer_builder.AnswerBuilder
    init_parameters: {}

connections: []

inputs:
  query:
    - "answer_builder.query"

outputs:
  answers: "answer_builder.answers"
"""

_TEST_PIPELINE_NAME = "test-sh-integration-pipeline"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def search_history_resource(client: AsyncDeepsetClient, test_workspace: str) -> SearchHistoryResource:
    """Search history resource bound to the ephemeral test workspace."""
    return SearchHistoryResource(client=client, workspace=test_workspace)


@pytest.fixture
async def pipeline_resource(client: AsyncDeepsetClient, test_workspace: str) -> PipelineResource:
    """Pipeline resource bound to the ephemeral test workspace."""
    return PipelineResource(client=client, workspace=test_workspace)


@pytest.fixture
async def test_pipeline(pipeline_resource: PipelineResource) -> str:
    """Create a minimal pipeline in the test workspace and return its name.

    The pipeline is not deployed, so it will never have search history.
    This fixture is used purely so pipeline-specific endpoints have a valid
    target to call.
    """
    await pipeline_resource.create(pipeline_name=_TEST_PIPELINE_NAME, yaml_config=_MINIMAL_YAML)
    return _TEST_PIPELINE_NAME


# ---------------------------------------------------------------------------
# Tests: SearchHistoryResource.list()
# ---------------------------------------------------------------------------


class TestIntegrationSearchHistoryList:
    """Workspace-level search history listing against a fresh workspace."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(self, search_history_resource: SearchHistoryResource) -> None:
        """Calling list() always returns a PaginatedResponse regardless of data."""
        result = await search_history_resource.list()
        assert isinstance(result, PaginatedResponse)
        assert isinstance(result.data, list)
        assert isinstance(result.has_more, bool)

    @pytest.mark.asyncio
    async def test_list_fresh_workspace_is_empty(self, search_history_resource: SearchHistoryResource) -> None:
        """A brand new workspace has no search history."""
        result = await search_history_resource.list()
        assert result.data == []
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, search_history_resource: SearchHistoryResource) -> None:
        """The limit param is forwarded correctly — response never exceeds it."""
        result = await search_history_resource.list(limit=1)
        assert len(result.data) <= 1

    @pytest.mark.asyncio
    async def test_list_entries_are_search_history_entries(
        self, search_history_resource: SearchHistoryResource
    ) -> None:
        """Each item deserialises into SearchHistoryEntry."""
        result = await search_history_resource.list(limit=5)
        for entry in result.data:
            assert isinstance(entry, SearchHistoryEntry)

    @pytest.mark.asyncio
    async def test_list_sort_asc(self, search_history_resource: SearchHistoryResource) -> None:
        """sort_order=ASC is accepted without error."""
        result = await search_history_resource.list(sort_order="ASC", limit=5)
        assert isinstance(result, PaginatedResponse)

    @pytest.mark.asyncio
    async def test_list_sort_by_duration(self, search_history_resource: SearchHistoryResource) -> None:
        """sort_field=duration is accepted without error."""
        result = await search_history_resource.list(sort_field="duration", sort_order="DESC", limit=5)
        assert isinstance(result, PaginatedResponse)

    @pytest.mark.asyncio
    async def test_list_filter_no_match_returns_empty(self, search_history_resource: SearchHistoryResource) -> None:
        """A valid OData filter that matches nothing returns an empty list."""
        result = await search_history_resource.list(
            query_filter="status eq 'nonexistent_status_xyz'",
            limit=5,
        )
        assert isinstance(result, PaginatedResponse)
        assert result.data == []

    @pytest.mark.asyncio
    async def test_list_pagination_cursor_produces_disjoint_pages(
        self, search_history_resource: SearchHistoryResource
    ) -> None:
        """Cursor-based pagination returns non-overlapping pages when enough data exists."""
        first = await search_history_resource.list(limit=2)
        if not (first.has_more and first.next_cursor):
            pytest.skip("Not enough search history data to test pagination")

        second = await search_history_resource.list(limit=2, after=first.next_cursor)
        assert isinstance(second, PaginatedResponse)

        first_ids = {e.search_history_id for e in first.data if e.search_history_id}
        second_ids = {e.search_history_id for e in second.data if e.search_history_id}
        assert first_ids.isdisjoint(second_ids), "Cursor pagination returned duplicate entries across pages"


# ---------------------------------------------------------------------------
# Tests: SearchHistoryResource.list_pipeline()
# ---------------------------------------------------------------------------


class TestIntegrationSearchHistoryListPipeline:
    """Pipeline-scoped search history listing."""

    @pytest.mark.asyncio
    async def test_list_pipeline_returns_paginated_response(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """list_pipeline() returns a well-formed PaginatedResponse."""
        result = await search_history_resource.list_pipeline(pipeline_name=test_pipeline)
        assert isinstance(result, PaginatedResponse)
        assert isinstance(result.data, list)
        assert isinstance(result.has_more, bool)

    @pytest.mark.asyncio
    async def test_list_pipeline_empty_for_new_pipeline(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """A pipeline that has never been queried returns empty search history."""
        result = await search_history_resource.list_pipeline(pipeline_name=test_pipeline)
        assert result.data == []
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_pipeline_respects_limit(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """The limit param is forwarded — response never exceeds it."""
        result = await search_history_resource.list_pipeline(pipeline_name=test_pipeline, limit=1)
        assert len(result.data) <= 1

    @pytest.mark.asyncio
    async def test_list_pipeline_sort_params_accepted(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """Sort parameters are forwarded without error."""
        result = await search_history_resource.list_pipeline(
            pipeline_name=test_pipeline,
            sort_field="duration",
            sort_order="ASC",
            limit=5,
        )
        assert isinstance(result, PaginatedResponse)

    @pytest.mark.asyncio
    async def test_list_pipeline_nonexistent_pipeline_raises(
        self, search_history_resource: SearchHistoryResource
    ) -> None:
        """A pipeline name that doesn't exist raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            await search_history_resource.list_pipeline(pipeline_name="definitely-does-not-exist-xyzabc")

    @pytest.mark.asyncio
    async def test_list_pipeline_entries_are_search_history_entries(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """Each returned item deserialises into SearchHistoryEntry."""
        result = await search_history_resource.list_pipeline(pipeline_name=test_pipeline, limit=5)
        for entry in result.data:
            assert isinstance(entry, SearchHistoryEntry)


# ---------------------------------------------------------------------------
# Tests: SearchHistoryResource.list_pipeline_traces()
# ---------------------------------------------------------------------------


class TestIntegrationSearchHistoryListPipelineTraces:
    """Pipeline traces listing via the v2 API (requires UUID resolution)."""

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_returns_paginated_response(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """list_pipeline_traces() returns a well-formed PaginatedResponse."""
        result = await search_history_resource.list_pipeline_traces(pipeline_name=test_pipeline)
        assert isinstance(result, PaginatedResponse)
        assert isinstance(result.data, list)
        assert isinstance(result.has_more, bool)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_empty_for_new_pipeline(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """A pipeline that has never been queried has no traces."""
        result = await search_history_resource.list_pipeline_traces(pipeline_name=test_pipeline)
        assert result.data == []
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_respects_limit(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """The limit param is forwarded — response never exceeds it."""
        result = await search_history_resource.list_pipeline_traces(pipeline_name=test_pipeline, limit=1)
        assert len(result.data) <= 1

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_sort_params_accepted(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """Sort parameters are forwarded without error."""
        result = await search_history_resource.list_pipeline_traces(
            pipeline_name=test_pipeline,
            sort_field="duration",
            sort_order="ASC",
            limit=5,
        )
        assert isinstance(result, PaginatedResponse)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_filter_no_match_returns_empty(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """A valid OData filter that matches nothing returns an empty list."""
        result = await search_history_resource.list_pipeline_traces(
            pipeline_name=test_pipeline,
            query_filter="status eq 'nonexistent_status_xyz'",
            limit=5,
        )
        assert isinstance(result, PaginatedResponse)
        assert result.data == []

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_entries_are_pipeline_trace_entries(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """Each returned item deserialises into PipelineTraceEntry."""
        result = await search_history_resource.list_pipeline_traces(pipeline_name=test_pipeline, limit=5)
        for entry in result.data:
            assert isinstance(entry, PipelineTraceEntry)

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_nonexistent_pipeline_raises(
        self, search_history_resource: SearchHistoryResource
    ) -> None:
        """A pipeline name that doesn't exist raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError):
            await search_history_resource.list_pipeline_traces(pipeline_name="definitely-does-not-exist-xyzabc")

    @pytest.mark.asyncio
    async def test_list_pipeline_traces_pagination_cursor(
        self,
        search_history_resource: SearchHistoryResource,
    ) -> None:
        """Cursor-based pagination returns non-overlapping pages when enough trace data exists.

        Requires DEEPSET_TEST_PIPELINE to point to a pipeline with >2 traces.
        """
        pipeline_name = os.environ.get("DEEPSET_TEST_PIPELINE")
        if not pipeline_name:
            pytest.skip("DEEPSET_TEST_PIPELINE not set")

        workspace = os.environ.get("DEEPSET_TEST_WORKSPACE")
        if workspace:
            resource = SearchHistoryResource(client=search_history_resource._client, workspace=workspace)
        else:
            resource = search_history_resource

        first = await resource.list_pipeline_traces(pipeline_name=pipeline_name, limit=2)
        if not (first.has_more and first.next_cursor):
            pytest.skip("Not enough trace data to test pagination")

        second = await resource.list_pipeline_traces(pipeline_name=pipeline_name, limit=2, after=first.next_cursor)
        assert isinstance(second, PaginatedResponse)

        first_ids = {e.query_id for e in first.data}
        second_ids = {e.query_id for e in second.data}
        assert first_ids.isdisjoint(second_ids), "Cursor pagination returned duplicate trace entries"


# ---------------------------------------------------------------------------
# Tests: SearchHistoryResource.get_pipeline_trace()
# ---------------------------------------------------------------------------


class TestIntegrationSearchHistoryGetPipelineTrace:
    """Single-trace retrieval via the v2 API."""

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_nonexistent_query_raises(
        self,
        search_history_resource: SearchHistoryResource,
        test_pipeline: str,
    ) -> None:
        """A query_id that doesn't exist raises an API error (typically 404)."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        with pytest.raises((ResourceNotFoundError, UnexpectedAPIError)):
            await search_history_resource.get_pipeline_trace(
                pipeline_name=test_pipeline,
                query_id=non_existent_id,
            )

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_nonexistent_pipeline_raises(
        self, search_history_resource: SearchHistoryResource
    ) -> None:
        """A pipeline that doesn't exist raises ResourceNotFoundError during UUID resolution."""
        with pytest.raises(ResourceNotFoundError):
            await search_history_resource.get_pipeline_trace(
                pipeline_name="definitely-does-not-exist-xyzabc",
                query_id="00000000-0000-0000-0000-000000000000",
            )

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_returns_pipeline_trace_entry(self) -> None:
        """Fetch a real trace when DEEPSET_TEST_PIPELINE is set and has data.

        Set DEEPSET_TEST_PIPELINE to a pipeline name and DEEPSET_TEST_WORKSPACE
        to the workspace name.  If no traces exist the test is skipped.
        """
        pipeline_name = os.environ.get("DEEPSET_TEST_PIPELINE")
        workspace = os.environ.get("DEEPSET_TEST_WORKSPACE")
        api_key = os.environ.get("DEEPSET_API_KEY")

        if not pipeline_name or not workspace or not api_key:
            pytest.skip("DEEPSET_TEST_PIPELINE, DEEPSET_TEST_WORKSPACE, and DEEPSET_API_KEY must all be set")

        async with AsyncDeepsetClient(api_key=api_key) as client:
            resource = SearchHistoryResource(client=client, workspace=workspace)

            traces = await resource.list_pipeline_traces(pipeline_name=pipeline_name, limit=1)
            if not traces.data:
                pytest.skip(f"No traces found for pipeline '{pipeline_name}' in workspace '{workspace}'")

            entry = traces.data[0]
            trace = await resource.get_pipeline_trace(pipeline_name=pipeline_name, query_id=entry.query_id)

        assert trace is not None
        assert isinstance(trace, PipelineTraceEntry)
        assert trace.query_id == entry.query_id
        assert isinstance(trace.query, str)
        assert isinstance(trace.duration_s, float)
        assert isinstance(trace.created_at, str)

    @pytest.mark.asyncio
    async def test_get_pipeline_trace_haystack_trace_structure(self) -> None:
        """When a trace has haystack_trace data, verify its nested structure.

        Requires DEEPSET_TEST_PIPELINE pointing to a pipeline with traces.
        """
        pipeline_name = os.environ.get("DEEPSET_TEST_PIPELINE")
        workspace = os.environ.get("DEEPSET_TEST_WORKSPACE")
        api_key = os.environ.get("DEEPSET_API_KEY")

        if not pipeline_name or not workspace or not api_key:
            pytest.skip("DEEPSET_TEST_PIPELINE, DEEPSET_TEST_WORKSPACE, and DEEPSET_API_KEY must all be set")

        async with AsyncDeepsetClient(api_key=api_key) as client:
            resource = SearchHistoryResource(client=client, workspace=workspace)

            traces = await resource.list_pipeline_traces(pipeline_name=pipeline_name, limit=5)
            if not traces.data:
                pytest.skip(f"No traces found for pipeline '{pipeline_name}'")

            entry = traces.data[0]
            trace = await resource.get_pipeline_trace(pipeline_name=pipeline_name, query_id=entry.query_id)

        assert trace is not None
        if trace.haystack_trace is None:
            pytest.skip("Trace has no haystack_trace data")

        ht = trace.haystack_trace
        assert isinstance(ht.schema_version, str)
        assert isinstance(ht.run_id, str)
        assert isinstance(ht.started_at, str)
        assert isinstance(ht.traces, list)
        assert isinstance(ht.logs, list)
