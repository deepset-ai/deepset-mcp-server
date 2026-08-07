# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.pipeline.models import PipelineDebugBreakpoint, PipelineDebugResult
from deepset_mcp.api.pipeline.protocols import PipelineResourceProtocol
from deepset_mcp.api.pipeline.resource import PipelineResource
from deepset_mcp.api.transport import TransportResponse
from test.unit.conftest import BaseFakeClient


class DummyClient(BaseFakeClient):
    """Dummy client for testing that implements AsyncClientProtocol."""

    def pipelines(self, workspace: str) -> PipelineResourceProtocol:
        return PipelineResource(client=self, workspace=workspace)


def _trace(status: str = "success") -> dict[str, Any]:
    return {
        "schema_version": "haystack-trace/v1",
        "run_id": "run-1",
        "started_at": "2026-01-01T00:00:00Z",
        "status": status,
    }


class TestPipelineResourceDebug:
    """Tests for the debug() method of the PipelineResource class."""

    @pytest.mark.asyncio
    async def test_debug_plain_run(self) -> None:
        response = {
            "status": "completed",
            "result": {"answer_builder": {"answers": ["hi"]}},
            "snapshot": None,
            "stopped_at": None,
            "trace": _trace(),
        }
        client = DummyClient(responses={"test-workspace/haystack/pipelines/debug": response})

        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.debug(pipeline_config={"components": {}}, inputs={"query": "hi"})

        assert isinstance(result, PipelineDebugResult)
        assert result.status == "completed"
        assert result.result == {"answer_builder": {"answers": ["hi"]}}
        assert result.snapshot is None
        assert result.stopped_at is None

        assert len(client.requests) == 1
        assert client.requests[0]["endpoint"] == "v1/workspaces/test-workspace/haystack/pipelines/debug"
        assert client.requests[0]["method"] == "POST"
        assert client.requests[0]["data"] == {
            "pipeline_config": {"components": {}},
            "inputs": {"query": "hi"},
            "dry_run": False,
        }

    @pytest.mark.asyncio
    async def test_debug_with_break_at(self) -> None:
        response = {
            "status": "stopped_at_breakpoint",
            "result": None,
            "snapshot": {"some": "snapshot"},
            "stopped_at": {"component_name": "retriever", "visit_count": 0},
            "trace": _trace(),
        }
        client = DummyClient(responses={"test-workspace/haystack/pipelines/debug": response})

        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.debug(
            pipeline_config={"components": {}},
            inputs={"query": "hi"},
            break_at=PipelineDebugBreakpoint(component_name="retriever", visit_count=0),
        )

        assert result.status == "stopped_at_breakpoint"
        assert result.snapshot == {"some": "snapshot"}
        assert result.stopped_at == PipelineDebugBreakpoint(component_name="retriever", visit_count=0)

        assert client.requests[0]["data"] == {
            "pipeline_config": {"components": {}},
            "inputs": {"query": "hi"},
            "dry_run": False,
            "break_at": {"component_name": "retriever", "visit_count": 0},
        }

    @pytest.mark.asyncio
    async def test_debug_with_resume_from(self) -> None:
        response = {
            "status": "completed",
            "result": {"answer_builder": {"answers": ["done"]}},
            "snapshot": None,
            "stopped_at": None,
            "trace": _trace(),
        }
        client = DummyClient(responses={"test-workspace/haystack/pipelines/debug": response})

        resource = PipelineResource(client=client, workspace="test-workspace")
        snapshot = {"pipeline_state": "..."}
        result = await resource.debug(
            pipeline_config={"components": {}},
            resume_from=snapshot,
        )

        assert result.status == "completed"
        assert client.requests[0]["data"] == {
            "pipeline_config": {"components": {}},
            "inputs": {},
            "dry_run": False,
            "resume_from": snapshot,
        }

    @pytest.mark.asyncio
    async def test_debug_with_dry_run_files_and_pipeline_ids(self) -> None:
        response = {
            "status": "completed",
            "result": {},
            "snapshot": None,
            "stopped_at": None,
            "trace": _trace(),
        }
        client = DummyClient(responses={"test-workspace/haystack/pipelines/debug": response})

        resource = PipelineResource(client=client, workspace="test-workspace")
        await resource.debug(
            pipeline_config={"components": {}},
            files=["11111111-1111-1111-1111-111111111111"],
            pipeline_id="22222222-2222-2222-2222-222222222222",
            pipeline_version_id="33333333-3333-3333-3333-333333333333",
            dry_run=True,
        )

        assert client.requests[0]["data"] == {
            "pipeline_config": {"components": {}},
            "inputs": {},
            "dry_run": True,
            "files": ["11111111-1111-1111-1111-111111111111"],
            "pipeline_id": "22222222-2222-2222-2222-222222222222",
            "pipeline_version_id": "33333333-3333-3333-3333-333333333333",
        }

    @pytest.mark.asyncio
    async def test_debug_failed_run_returns_trace(self) -> None:
        failure = {"type": "ValueError", "message": "boom", "stacktrace": []}
        response = {
            "status": "failed",
            "result": None,
            "snapshot": None,
            "stopped_at": None,
            "trace": {**_trace(status="failed"), "failure": failure},
        }
        client = DummyClient(responses={"test-workspace/haystack/pipelines/debug": response})

        resource = PipelineResource(client=client, workspace="test-workspace")
        result = await resource.debug(pipeline_config={"components": {}})

        assert result.status == "failed"
        assert result.trace.failure is not None
        assert result.trace.failure.message == "boom"

    @pytest.mark.asyncio
    async def test_debug_api_error(self) -> None:
        client = DummyClient()
        client.responses = {
            "test-workspace/haystack/pipelines/debug": TransportResponse(
                text="Internal error", status_code=500, json=None
            )
        }

        resource = PipelineResource(client=client, workspace="test-workspace")

        with pytest.raises(UnexpectedAPIError):
            await resource.debug(pipeline_config={"components": {}})

    @pytest.mark.asyncio
    async def test_debug_empty_response_raises(self) -> None:
        client = DummyClient()
        client.responses = {
            "test-workspace/haystack/pipelines/debug": TransportResponse(text="", status_code=200, json=None)
        }

        resource = PipelineResource(client=client, workspace="test-workspace")

        with pytest.raises(UnexpectedAPIError):
            await resource.debug(pipeline_config={"components": {}})
