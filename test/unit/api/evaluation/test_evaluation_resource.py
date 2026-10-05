# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for EvaluationResource."""

from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    Experiment,
    ExperimentRun,
    ExperimentRunGrid,
    SessionList,
)
from deepset_mcp.api.evaluation.resource import EvaluationResource
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline.models import DeepsetPipeline
from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.api.workspace.models import Workspace
from test.unit.conftest import BaseFakeClient

WORKSPACE_NAME = "my-workspace"
WORKSPACE_UUID = "76d361b5-a551-40e3-a5c9-fdbc20028021"
PIPELINE_NAME = "my-pipeline"
PIPELINE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EVALUATOR_ID = "11111111-1111-1111-1111-111111111111"
VERSION_ID = "22222222-2222-2222-2222-222222222222"
EXPERIMENT_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"
SESSION_ID = "55555555-5555-5555-5555-555555555555"
EVALUATION_RUN_ID = "66666666-6666-6666-6666-666666666666"

EVALUATORS = f"v2/workspaces/{WORKSPACE_UUID}/evaluators"
EXPERIMENTS = f"v2/workspaces/{WORKSPACE_UUID}/pipelines/{PIPELINE_UUID}/experiments"
RUNS = f"{EXPERIMENTS}/{EXPERIMENT_ID}/runs"
SESSIONS = f"v2/workspaces/{WORKSPACE_UUID}/pipelines/{PIPELINE_UUID}/sessions"


def version_summary() -> dict[str, Any]:
    return {
        "evaluator_version_id": VERSION_ID,
        "evaluator_id": EVALUATOR_ID,
        "content_hash": "abc",
        "metrics": {"answered": {"shape": "label", "grain": "turn", "vocabulary": ["yes", "no"]}},
        "metrics_legacy": False,
        "created_at": "2026-10-01T00:00:00Z",
    }


def evaluator_dict() -> dict[str, Any]:
    return {
        "evaluator_id": EVALUATOR_ID,
        "workspace_id": WORKSPACE_UUID,
        "name": "Answered",
        "latest_version": version_summary(),
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": None,
    }


def experiment_dict() -> dict[str, Any]:
    return {
        "pipeline_experiment_id": EXPERIMENT_ID,
        "workspace_id": WORKSPACE_UUID,
        "pipeline_id": PIPELINE_UUID,
        "name": "Weekly",
        "evaluator_ids": [EVALUATOR_ID],
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": None,
    }


def run_dict() -> dict[str, Any]:
    return {
        "pipeline_experiment_run_id": RUN_ID,
        "pipeline_experiment_id": EXPERIMENT_ID,
        "status": "ENDED",
        "started_at": "2026-10-01T00:00:00Z",
        "ended_at": "2026-10-01T00:05:00Z",
        "ran_by_user_id": None,
        "selection": "SAMPLED",
        "created_at": "2026-10-01T00:00:00Z",
    }


def grid_dict() -> dict[str, Any]:
    return {
        "run": run_dict(),
        "evaluator_ids": [EVALUATOR_ID],
        "rows": [
            {
                "session_id": SESSION_ID,
                "cells": [
                    {
                        "evaluator_id": EVALUATOR_ID,
                        "evaluation_run": {
                            "evaluation_run_id": EVALUATION_RUN_ID,
                            "pipeline_id": PIPELINE_UUID,
                            "status": "ENDED",
                            "outcome": "SUCCEEDED",
                            "metrics": [
                                {"metric_key": "answered", "address": "turn/0", "kind": "label", "label": "yes"}
                            ],
                            "evaluator_version_id": VERSION_ID,
                            "session_id": SESSION_ID,
                            "trace_ids": [],
                            "provenance": None,
                            "error_detail": None,
                            "created_at": "2026-10-01T00:00:00Z",
                        },
                    }
                ],
            }
        ],
        "counts": {"cells": 1, "succeeded": 1, "errored": 0, "failed": 0, "unresolved_sessions": 0, "running": 0},
    }


def sessions_dict() -> dict[str, Any]:
    return {
        "data": [
            {
                "session_id": SESSION_ID,
                "turn_count": 2,
                "first_activity_at": "2026-10-01T00:00:00Z",
                "last_activity_at": "2026-10-01T00:01:00Z",
                "first_query": "Where is my order?",
                "provenance": {"origin": "SERVICE", "deployment_id": None, "pipeline_version_ids": []},
            }
        ],
        "next": "cursor-2",
    }


class FakeWorkspaceResource:
    def __init__(self, result: Workspace | Exception) -> None:
        self._result = result
        self.calls: list[str] = []

    async def get(self, workspace_name: str) -> Workspace:
        self.calls.append(workspace_name)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakePipelineResource:
    def __init__(self, result: DeepsetPipeline | Exception) -> None:
        self._result = result
        self.calls: list[str] = []

    async def get(self, pipeline_name: str) -> DeepsetPipeline:
        self.calls.append(pipeline_name)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeEvaluationClient(BaseFakeClient):
    """Resolves the workspace and pipeline through fakes and answers HTTP calls from a dict."""

    def __init__(self, http_responses: dict[str, Any], pipeline: DeepsetPipeline | Exception | None = None) -> None:
        super().__init__(responses=http_responses)
        self.workspace_resource = FakeWorkspaceResource(
            Workspace(
                name=WORKSPACE_NAME,
                workspace_id=UUID(WORKSPACE_UUID),
                languages={},
                default_idle_timeout_in_seconds=43200,
            )
        )
        self.pipeline_resource = FakePipelineResource(
            pipeline
            if pipeline is not None
            else DeepsetPipeline.model_validate(
                {
                    "pipeline_id": PIPELINE_UUID,
                    "name": PIPELINE_NAME,
                    "status": "DEPLOYED",
                    "service_level": "PRODUCTION",
                    "created_at": "2024-01-01T00:00:00Z",
                    "created_by": {"user_id": "u-001", "given_name": "Test", "family_name": "User"},
                }
            )
        )

    def workspaces(self) -> FakeWorkspaceResource:  # type: ignore[override]
        return self.workspace_resource

    def pipelines(self, workspace: str) -> FakePipelineResource:  # type: ignore[override]
        return self.pipeline_resource


def resource(client: FakeEvaluationClient) -> EvaluationResource:
    return EvaluationResource(client=client, workspace=WORKSPACE_NAME)


@pytest.mark.asyncio
async def test_list_evaluators_calls_the_workspace_route_by_uuid() -> None:
    client = FakeEvaluationClient({EVALUATORS: [evaluator_dict()]})

    evaluators = await resource(client).list_evaluators()

    assert [e.name for e in evaluators] == ["Answered"]
    assert isinstance(evaluators[0], Evaluator)
    assert evaluators[0].latest_version is not None
    assert evaluators[0].latest_version.metrics["answered"].vocabulary == ["yes", "no"]
    assert client.requests[0]["endpoint"] == EVALUATORS
    assert client.requests[0]["params"] == {"limit": 200}
    assert client.workspace_resource.calls == [WORKSPACE_NAME]
    assert client.pipeline_resource.calls == []


@pytest.mark.asyncio
async def test_get_evaluator_and_version() -> None:
    client = FakeEvaluationClient(
        {
            f"{EVALUATORS}/{EVALUATOR_ID}": {**evaluator_dict(), "versions": [version_summary()]},
            f"{EVALUATORS}/{EVALUATOR_ID}/versions/{VERSION_ID}": {**version_summary(), "python_code": "def f(): ..."},
        }
    )

    evaluator = await resource(client).get_evaluator(EVALUATOR_ID)
    version = await resource(client).get_evaluator_version(EVALUATOR_ID, VERSION_ID)

    assert [v.evaluator_version_id for v in evaluator.versions] == [VERSION_ID]
    assert isinstance(version, EvaluatorVersion)
    assert version.python_code == "def f(): ..."


@pytest.mark.asyncio
async def test_list_experiments_and_runs_resolve_the_pipeline_uuid() -> None:
    client = FakeEvaluationClient({EXPERIMENTS: [experiment_dict()], RUNS: [run_dict()]})

    experiments = await resource(client).list_experiments(PIPELINE_NAME)
    runs = await resource(client).list_experiment_runs(PIPELINE_NAME, EXPERIMENT_ID, limit=1)

    assert isinstance(experiments[0], Experiment)
    assert experiments[0].evaluator_ids == [EVALUATOR_ID]
    assert isinstance(runs[0], ExperimentRun)
    assert runs[0].selection == "SAMPLED"
    assert client.requests[1]["endpoint"] == RUNS
    assert client.requests[1]["params"] == {"limit": 1}
    assert client.pipeline_resource.calls == [PIPELINE_NAME, PIPELINE_NAME]


@pytest.mark.asyncio
async def test_get_experiment_run_returns_the_grid() -> None:
    client = FakeEvaluationClient({f"{RUNS}/{RUN_ID}": grid_dict()})

    grid = await resource(client).get_experiment_run(PIPELINE_NAME, EXPERIMENT_ID, RUN_ID)

    assert isinstance(grid, ExperimentRunGrid)
    cell = grid.rows[0].cells[0]
    assert cell.evaluation_run.outcome == "SUCCEEDED"
    assert cell.evaluation_run.metrics[0].label == "yes"
    assert grid.counts.succeeded == 1


@pytest.mark.asyncio
async def test_list_sessions_passes_filters_under_the_route_names() -> None:
    client = FakeEvaluationClient({SESSIONS: sessions_dict()})

    sessions = await resource(client).list_sessions(
        PIPELINE_NAME, origin="SERVICE", since="2026-09-24T00:00:00Z", limit=20, cursor="cursor-1"
    )

    assert isinstance(sessions, SessionList)
    assert sessions.next == "cursor-2"
    assert sessions.data[0].provenance.origin == "SERVICE"
    assert client.requests[0]["params"] == {
        "origin": "SERVICE",
        "from": "2026-09-24T00:00:00Z",
        "limit": 20,
        "cursor": "cursor-1",
    }


@pytest.mark.asyncio
async def test_unknown_pipeline_raises_not_found() -> None:
    client = FakeEvaluationClient({}, pipeline=ResourceNotFoundError())

    with pytest.raises(ResourceNotFoundError):
        await resource(client).list_experiments("missing")


@pytest.mark.asyncio
async def test_404_from_the_route_raises_not_found() -> None:
    client = FakeEvaluationClient(
        {f"{EVALUATORS}/{EVALUATOR_ID}": TransportResponse(text="{}", status_code=404, json={"message": "gone"})}
    )

    with pytest.raises(ResourceNotFoundError):
        await resource(client).get_evaluator(EVALUATOR_ID)
