# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for EvaluationResource."""

from typing import Any
from uuid import UUID

import pytest

from deepset_mcp.api.evaluation.models import (
    CombinedEvaluatorTemplates,
    Dataset,
    DatasetSummary,
    EvaluationRun,
    Evaluator,
    EvaluatorTemplate,
    EvaluatorVersion,
    Experiment,
    ExperimentDetail,
    ExperimentPlan,
    ExperimentResults,
    ExperimentRun,
    ExperimentRunAccepted,
    ExperimentRunGrid,
    ExperimentRunPreview,
    ExperimentUpdatePlan,
    MetricGroup,
    MetricWeight,
    NewTestCase,
    ReplaySuite,
    ReplaySuiteAccepted,
    ReplaySuiteSummary,
    SessionList,
    SessionWindow,
    TestCase,
)
from deepset_mcp.api.evaluation.resource import EvaluationResource
from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.pipeline.models import DeepsetPipeline
from deepset_mcp.api.search_history.models import PipelineTraceEntry
from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.api.workspace.models import Workspace
from test.unit.conftest import BaseFakeClient

WORKSPACE_NAME = "my-workspace"
WORKSPACE_UUID = "76d361b5-a551-40e3-a5c9-fdbc20028021"
PIPELINE_NAME = "my-pipeline"
PIPELINE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EVALUATOR_ID = "11111111-1111-1111-1111-111111111111"
VERSION_ID = "22222222-2222-2222-2222-222222222222"
METRIC_GROUP_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"
SESSION_ID = "55555555-5555-5555-5555-555555555555"
EVALUATION_RUN_ID = "66666666-6666-6666-6666-666666666666"
COMPARISON_ID = "77777777-7777-7777-7777-777777777777"

EVALUATION = f"v2/workspaces/{WORKSPACE_UUID}/evaluation"
PIPELINE = f"{EVALUATION}/pipelines/{PIPELINE_UUID}"
EVALUATORS = f"{EVALUATION}/evaluators"
METRIC_GROUPS = f"{EVALUATION}/metric-groups"
EXPERIMENTS = f"{EVALUATION}/experiments"
RUNS = f"{PIPELINE}/metric-groups/{METRIC_GROUP_ID}/scoring-runs"
SESSIONS = f"{PIPELINE}/sessions"
DATASETS = f"{EVALUATION}/datasets"
DATASET_ID = "bbbbbbbb-1111-2222-3333-444444444444"
TEST_CASE_ID = "cccccccc-1111-2222-3333-444444444444"
DATASET = f"{DATASETS}/{DATASET_ID}"


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


def metric_group_dict() -> dict[str, Any]:
    return {
        "metric_group_id": METRIC_GROUP_ID,
        "workspace_id": WORKSPACE_UUID,
        "name": "Weekly",
        "evaluator_ids": [EVALUATOR_ID],
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": None,
    }


def comparison_dict() -> dict[str, Any]:
    side = {
        "pipeline_id": PIPELINE_UUID,
        "pipeline_version_id": VERSION_ID,
        "status": "SCORING",
        "experiment_run_id": RUN_ID,
        "scoring_runs": [{"pipeline_id": PIPELINE_UUID, "experiment_run_id": RUN_ID}],
        "reused_sessions": 1,
        "replays_needed": 1,
        "sessions": [],
        "scoring_counts": None,
    }
    return {
        "comparison_id": COMPARISON_ID,
        "workspace_id": WORKSPACE_UUID,
        "name": "New prompt",
        "session_replay_dataset_id": None,
        "dataset_name": "Regression set",
        "metric_group_id": METRIC_GROUP_ID,
        "metric_group_name": "Weekly",
        "sessions_per_test_case": 1,
        "replay_mode": "LIVE",
        "status": "SCORING",
        "candidate": side,
        "baseline": {**side, "status": "ENDED"},
        "created_at": "2026-10-01T00:00:00Z",
    }


def results_dict() -> dict[str, Any]:
    """An Experiment's results as `GET .../evaluation/experiments/{id}/results` returns them."""
    candidate = {"value": 0.8, "labels": None, "sessions": 2, "errored": 0}
    baseline = {"value": 0.6, "labels": None, "sessions": 2, "errored": 1}
    return {
        "comparison_id": COMPARISON_ID,
        "status": "ENDED",
        "metrics": [
            {
                "evaluator_id": EVALUATOR_ID,
                "evaluator_version_ids": [VERSION_ID],
                "metric_key": "accuracy",
                "shape": "score",
                "candidate": candidate,
                "baseline": baseline,
                "delta": 0.2,
                "delta_pct": 33.3,
                "paired_test_cases": 2,
            }
        ],
        "pipeline_metrics": [
            {
                "key": "COST",
                "candidate": candidate,
                "baseline": baseline,
                "delta": 0.2,
                "delta_pct": 33.3,
                "paired_test_cases": 2,
            }
        ],
        "test_cases": [
            {
                "session_replay_test_case_id": EVALUATION_RUN_ID,
                "name": "Order status",
                "candidate_session_ids": [SESSION_ID],
                "baseline_session_ids": [SESSION_ID],
                "values": {f"{EVALUATOR_ID}:accuracy": {"candidate": 1.0, "baseline": 0.5}},
                "pipeline_values": {"COST": {"candidate": 0.01, "baseline": None}},
            }
        ],
    }


def run_dict() -> dict[str, Any]:
    return {
        "pipeline_experiment_run_id": RUN_ID,
        "pipeline_experiment_id": METRIC_GROUP_ID,
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
                                {"metric_key": "answered", "address": "turn/1", "kind": "label", "label": "yes"}
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
async def test_list_metric_groups_calls_the_workspace_route() -> None:
    client = FakeEvaluationClient({METRIC_GROUPS: [metric_group_dict()]})

    groups = await resource(client).list_metric_groups()

    assert isinstance(groups[0], MetricGroup)
    assert groups[0].evaluator_ids == [EVALUATOR_ID]
    assert client.requests[0]["endpoint"] == METRIC_GROUPS
    assert client.pipeline_resource.calls == []


@pytest.mark.asyncio
async def test_list_experiment_runs_resolves_the_pipeline_uuid() -> None:
    client = FakeEvaluationClient({RUNS: [run_dict()]})

    runs = await resource(client).list_experiment_runs(PIPELINE_NAME, METRIC_GROUP_ID, limit=1)

    assert isinstance(runs[0], ExperimentRun)
    assert runs[0].selection == "SAMPLED"
    assert client.requests[0]["endpoint"] == RUNS
    assert client.requests[0]["params"] == {"limit": 1}
    assert client.pipeline_resource.calls == [PIPELINE_NAME]


@pytest.mark.asyncio
async def test_list_experiments_lists_the_workspace_without_a_pipeline() -> None:
    client = FakeEvaluationClient({EXPERIMENTS: [comparison_dict()]})

    experiments = await resource(client).list_experiments()

    assert isinstance(experiments[0], Experiment)
    assert experiments[0].experiment_id == COMPARISON_ID
    assert experiments[0].candidate.scoring_runs[0].experiment_run_id == RUN_ID
    assert client.requests[0]["endpoint"] == EXPERIMENTS
    assert client.requests[0]["params"] == {"limit": 50}
    assert client.pipeline_resource.calls == []


@pytest.mark.asyncio
async def test_list_experiments_filters_by_the_pipeline_uuid() -> None:
    client = FakeEvaluationClient({EXPERIMENTS: [comparison_dict()]})

    await resource(client).list_experiments(PIPELINE_NAME, limit=10)

    assert client.requests[0]["endpoint"] == EXPERIMENTS
    assert client.requests[0]["params"] == {"limit": 10, "pipeline_id": PIPELINE_UUID}


@pytest.mark.asyncio
async def test_create_experiment_posts_the_body_with_resolved_pipeline_ids() -> None:
    client = FakeEvaluationClient({EXPERIMENTS: comparison_dict()})
    dataset_id = "88888888-8888-8888-8888-888888888888"
    candidate_version = "99999999-9999-9999-9999-999999999999"
    baseline_version = "aaaaaaaa-1111-2222-3333-444444444444"

    recorded = await resource(client).create_experiment(
        name="New prompt",
        dataset_id=dataset_id,
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE_NAME,
        candidate_pipeline_version_id=candidate_version,
    )
    await resource(client).create_experiment(
        name="Against v1",
        dataset_id=dataset_id,
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE_NAME,
        candidate_pipeline_version_id=candidate_version,
        baseline_pipeline_name=PIPELINE_NAME,
        baseline_pipeline_version_id=baseline_version,
        sessions_per_test_case=3,
        replay_mode="ALL_USER_MESSAGES",
    )

    assert isinstance(recorded, Experiment)
    assert recorded.experiment_id == COMPARISON_ID

    posts = [r for r in client.requests if r["method"] == "POST" and r["endpoint"] == EXPERIMENTS]
    assert posts[0]["data"] == {
        "name": "New prompt",
        "session_replay_dataset_id": dataset_id,
        "metric_group_id": METRIC_GROUP_ID,
        "candidate": {"pipeline_id": PIPELINE_UUID, "pipeline_version_id": candidate_version},
        "sessions_per_test_case": 1,
        "replay_mode": "FIRST_USER_MESSAGE",
    }
    assert posts[1]["data"]["baseline"] == {
        "pipeline_id": PIPELINE_UUID,
        "pipeline_version_id": baseline_version,
    }
    assert posts[1]["data"]["sessions_per_test_case"] == 3
    assert posts[1]["data"]["replay_mode"] == "ALL_USER_MESSAGES"


@pytest.mark.asyncio
async def test_get_experiment_results_calls_the_workspace_route() -> None:
    client = FakeEvaluationClient({f"{EXPERIMENTS}/{COMPARISON_ID}/results": results_dict()})

    results = await resource(client).get_experiment_results(COMPARISON_ID)

    assert isinstance(results, ExperimentResults)
    assert results.experiment_id == COMPARISON_ID
    assert results.metrics[0].delta == 0.2
    assert results.pipeline_metrics[0].key == "COST"
    assert results.test_cases[0].test_case_id == EVALUATION_RUN_ID
    assert results.test_cases[0].values[f"{EVALUATOR_ID}:accuracy"].baseline == 0.5
    assert client.pipeline_resource.calls == []


@pytest.mark.asyncio
async def test_get_experiment_run_returns_the_grid() -> None:
    client = FakeEvaluationClient({f"{RUNS}/{RUN_ID}": grid_dict()})

    grid = await resource(client).get_experiment_run(PIPELINE_NAME, METRIC_GROUP_ID, RUN_ID)

    assert isinstance(grid, ExperimentRunGrid)
    cell = grid.rows[0].cells[0]
    assert cell.evaluation_run.outcome == "SUCCEEDED"
    assert cell.evaluation_run.metrics[0].label == "yes"
    assert grid.counts.succeeded == 1


@pytest.mark.asyncio
async def test_list_evaluators_sends_the_archived_filter_only_when_given() -> None:
    client = FakeEvaluationClient({EVALUATORS: []})

    await resource(client).list_evaluators(limit=5, archived=False)
    await resource(client).list_evaluators()

    assert client.requests[0]["params"] == {"limit": 5, "archived": False}
    assert client.requests[1]["params"] == {"limit": 200}


@pytest.mark.asyncio
async def test_get_experiment_run_sends_the_grid_filters_and_parses_aggregate_and_usage() -> None:
    payload = {
        **grid_dict(),
        "usage": {
            "duration_s": 3.0,
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
            "cost": None,
            "cost_status": "pending",
            "sessions": 1,
        },
        "aggregate": {
            "metrics": [
                {
                    "shape": "label",
                    "evaluator_id": EVALUATOR_ID,
                    "metric_key": "answered",
                    "evaluator_version_ids": [VERSION_ID],
                    "sessions": {"valued": 1},
                    "coverage": 1.0,
                    "shares": {"yes": 1.0},
                    "vocabulary": ["yes", "no"],
                }
            ]
        },
        "evaluator_versions": [
            {
                "evaluator_version_id": VERSION_ID,
                "evaluator_id": EVALUATOR_ID,
                "content_hash": "abc",
                "metrics": {},
                "metrics_legacy": False,
                "created_at": "2026-10-01T00:00:00Z",
            }
        ],
    }
    client = FakeEvaluationClient({f"{RUNS}/{RUN_ID}": payload})

    grid = await resource(client).get_experiment_run(
        PIPELINE_NAME,
        METRIC_GROUP_ID,
        RUN_ID,
        origin="SERVICE",
        deployment_id="dep-1",
        pipeline_version_id="ver-1",
        session_id="ses-1",
    )

    assert client.requests[0]["params"] == {
        "origin": "SERVICE",
        "deployment_id": "dep-1",
        "pipeline_version_id": "ver-1",
        "session_id": "ses-1",
    }
    assert grid.usage is not None and grid.usage.cost_status == "pending" and grid.usage.cost is None
    assert grid.aggregate is not None and grid.aggregate.metrics[0].metric_key == "answered"
    assert [v.evaluator_version_id for v in grid.evaluator_versions] == [VERSION_ID]


@pytest.mark.asyncio
async def test_get_experiment_run_sends_no_params_without_filters() -> None:
    client = FakeEvaluationClient({f"{RUNS}/{RUN_ID}": grid_dict()})

    await resource(client).get_experiment_run(PIPELINE_NAME, METRIC_GROUP_ID, RUN_ID)

    assert not client.requests[0]["params"]


@pytest.mark.asyncio
async def test_list_sessions_sends_the_revision_id() -> None:
    client = FakeEvaluationClient({SESSIONS: sessions_dict()})

    await resource(client).list_sessions(PIPELINE_NAME, revision_id="rev-1", cursor="c")

    assert client.requests[0]["params"] == {"revision_id": "rev-1", "limit": 50, "cursor": "c"}


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


TRIES = f"{PIPELINE}/tries"
REPLAYS = f"{PIPELINE}/replay-runs"
TRY_ID = "signed-try-id"
REPLAY_RUN_ID = "77777777-7777-7777-7777-777777777777"
DRAFT_VERSION_ID = "88888888-8888-8888-8888-888888888888"


def try_result_dict() -> dict[str, Any]:
    return {
        "content_hash": "abc",
        "session_id": SESSION_ID,
        "outcome": "SUCCEEDED",
        "metrics": [{"metric_key": "answered", "address": "turn/1", "kind": "label", "label": "yes"}],
        "trace_ids": [SESSION_ID],
        "trace": {"traces": [], "status": "success"},
        "error_detail": None,
    }


def replay_run_dict(status: str = "ENDED", trace_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "session_replay_run_id": REPLAY_RUN_ID,
        "pipeline_id": PIPELINE_UUID,
        "pipeline_version_id": DRAFT_VERSION_ID,
        "status": status,
        "source_session_id": SESSION_ID,
        "result": None,
        "trace_ids": trace_ids if trace_ids is not None else [EVALUATION_RUN_ID],
        "error_detail": None,
        "created_at": "2026-10-07T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_start_try_posts_the_source_and_the_session() -> None:
    client = FakeEvaluationClient({TRIES: {"try_id": TRY_ID}})

    try_id = await resource(client).start_try(PIPELINE_NAME, "def evaluate(session, focus): ...", SESSION_ID)

    assert try_id == TRY_ID
    assert client.requests[0]["method"] == "POST"
    assert client.requests[0]["data"] == {"python_code": "def evaluate(session, focus): ...", "session_id": SESSION_ID}


@pytest.mark.asyncio
async def test_start_try_sends_the_test_case_only_when_set() -> None:
    client = FakeEvaluationClient({TRIES: {"try_id": TRY_ID}})

    await resource(client).start_try(PIPELINE_NAME, "code", SESSION_ID, test_case_id=TEST_CASE_ID)

    assert client.requests[0]["data"]["session_replay_test_case_id"] == TEST_CASE_ID


@pytest.mark.asyncio
async def test_get_try_reads_running_ready_and_expired() -> None:
    running = FakeEvaluationClient({f"{TRIES}/{TRY_ID}": TransportResponse(text="", status_code=202, json=None)})
    ready = FakeEvaluationClient({f"{TRIES}/{TRY_ID}": try_result_dict()})
    gone = FakeEvaluationClient(
        {f"{TRIES}/{TRY_ID}": TransportResponse(text="{}", status_code=410, json={"code": "try_expired"})}
    )

    assert (await resource(running).get_try(PIPELINE_NAME, TRY_ID)).status == "RUNNING"
    state = await resource(ready).get_try(PIPELINE_NAME, TRY_ID)
    assert state.status == "READY"
    assert state.result is not None and state.result.metrics[0].label == "yes"
    assert (await resource(gone).get_try(PIPELINE_NAME, TRY_ID)).status == "EXPIRED"


@pytest.mark.asyncio
async def test_start_session_replay_sends_replay_mode_only_when_set() -> None:
    client = FakeEvaluationClient({REPLAYS: {"session_replay_run_id": REPLAY_RUN_ID}})

    await resource(client).start_session_replay(PIPELINE_NAME, SESSION_ID, DRAFT_VERSION_ID)
    await resource(client).start_session_replay(
        PIPELINE_NAME, SESSION_ID, DRAFT_VERSION_ID, replay_mode="ALL_USER_MESSAGES"
    )

    first, second = (r for r in client.requests if r["endpoint"] == REPLAYS)
    assert first["method"] == "POST"
    assert first["data"] == {"session_id": SESSION_ID, "pipeline_version_id": DRAFT_VERSION_ID}
    assert second["data"]["replay_mode"] == "ALL_USER_MESSAGES"


@pytest.mark.asyncio
async def test_start_session_replay_sends_setup_and_cleanup_only_when_set() -> None:
    client = FakeEvaluationClient({REPLAYS: {"session_replay_run_id": REPLAY_RUN_ID}})

    await resource(client).start_session_replay(
        PIPELINE_NAME, SESSION_ID, DRAFT_VERSION_ID, setup_source="s", cleanup_source="c"
    )

    assert client.requests[0]["data"] == {
        "session_id": SESSION_ID,
        "pipeline_version_id": DRAFT_VERSION_ID,
        "setup_source": "s",
        "cleanup_source": "c",
    }


@pytest.mark.asyncio
async def test_get_session_replay_reads_the_run() -> None:
    client = FakeEvaluationClient({f"{REPLAYS}/{REPLAY_RUN_ID}": replay_run_dict()})

    run = await resource(client).get_session_replay(PIPELINE_NAME, REPLAY_RUN_ID)

    assert (run.status, run.source_session_id, run.trace_ids) == ("ENDED", SESSION_ID, [EVALUATION_RUN_ID])


def test_case_dict(**overrides: Any) -> dict[str, Any]:
    return {
        "session_replay_test_case_id": TEST_CASE_ID,
        "pipeline_id": PIPELINE_UUID,
        "session_id": SESSION_ID,
        "inputs": None,
        "expected": {"answer": "Paris"},
        "name": "Capital of France",
        "setup_source": None,
        "cleanup_source": None,
        "is_imported": False,
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": None,
        **overrides,
    }


def dataset_dict() -> dict[str, Any]:
    return {
        "session_replay_dataset_id": DATASET_ID,
        "workspace_id": WORKSPACE_UUID,
        "pipeline_ids": [PIPELINE_UUID],
        "name": "Regression set",
        "test_case_count": 1,
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": None,
        "test_cases": [test_case_dict()],
    }


@pytest.mark.asyncio
async def test_list_datasets_calls_the_workspace_route_and_renames_the_id() -> None:
    summary = {k: v for k, v in dataset_dict().items() if k != "test_cases"}
    client = FakeEvaluationClient({DATASETS: [summary]})

    datasets = await resource(client).list_datasets(limit=10)

    assert isinstance(datasets[0], DatasetSummary)
    assert datasets[0].dataset_id == DATASET_ID
    assert datasets[0].test_case_count == 1
    assert client.requests[0]["method"] == "GET"
    assert client.requests[0]["endpoint"] == DATASETS
    assert client.requests[0]["params"] == {"limit": 10}


@pytest.mark.asyncio
async def test_list_datasets_filters_by_the_pipeline_uuid() -> None:
    client = FakeEvaluationClient({DATASETS: []})

    await resource(client).list_datasets(pipeline_name=PIPELINE_NAME)

    assert client.requests[0]["params"] == {"limit": 50, "pipeline_id": PIPELINE_UUID}


@pytest.mark.asyncio
async def test_get_dataset_returns_its_test_cases() -> None:
    client = FakeEvaluationClient({DATASET: dataset_dict()})

    dataset = await resource(client).get_dataset(DATASET_ID)

    assert isinstance(dataset, Dataset)
    assert dataset.dataset_id == DATASET_ID
    assert dataset.test_cases[0].test_case_id == TEST_CASE_ID
    assert dataset.test_cases[0].expected == {"answer": "Paris"}
    assert client.requests[0]["endpoint"] == DATASET


@pytest.mark.asyncio
async def test_create_dataset_posts_the_pipeline_uuid_and_only_the_fields_set() -> None:
    client = FakeEvaluationClient({DATASETS: dataset_dict()})

    dataset = await resource(client).create_dataset(
        "Regression set",
        pipeline_name=PIPELINE_NAME,
        test_cases=[NewTestCase(session_id=SESSION_ID), NewTestCase(inputs={"query": "hi"}, expected={"a": 1})],
    )

    assert dataset.name == "Regression set"
    [request] = client.requests
    assert request["method"] == "POST"
    assert request["endpoint"] == DATASETS
    assert request["data"] == {
        "name": "Regression set",
        "pipeline_id": PIPELINE_UUID,
        "test_cases": [{"session_id": SESSION_ID}, {"inputs": {"query": "hi"}, "expected": {"a": 1}}],
    }


@pytest.mark.asyncio
async def test_create_dataset_without_pipeline_or_test_cases_sends_just_the_name() -> None:
    client = FakeEvaluationClient({DATASETS: dataset_dict()})

    await resource(client).create_dataset("Empty")

    assert client.requests[0]["data"] == {"name": "Empty"}


@pytest.mark.asyncio
async def test_update_dataset_puts_the_new_name() -> None:
    client = FakeEvaluationClient({DATASET: dataset_dict()})

    await resource(client).update_dataset(DATASET_ID, "Renamed")

    [request] = client.requests
    assert request["method"] == "PUT"
    assert request["endpoint"] == DATASET
    assert request["data"] == {"name": "Renamed"}


@pytest.mark.asyncio
async def test_delete_dataset_calls_delete_on_the_dataset() -> None:
    client = FakeEvaluationClient({DATASET: None})

    await resource(client).delete_dataset(DATASET_ID)

    [request] = client.requests
    assert request["method"] == "DELETE"
    assert request["endpoint"] == DATASET


@pytest.mark.asyncio
async def test_add_test_cases_posts_them_with_the_pipeline_uuid() -> None:
    client = FakeEvaluationClient({f"{DATASET}/test-cases": dataset_dict()})

    await resource(client).add_test_cases(
        DATASET_ID, [NewTestCase(session_id=SESSION_ID, name="n", setup_source="x")], pipeline_name=PIPELINE_NAME
    )

    [request] = client.requests
    assert request["method"] == "POST"
    assert request["endpoint"] == f"{DATASET}/test-cases"
    assert request["data"] == {
        "pipeline_id": PIPELINE_UUID,
        "test_cases": [{"session_id": SESSION_ID, "name": "n", "setup_source": "x"}],
    }


@pytest.mark.asyncio
async def test_add_test_cases_with_inputs_needs_no_pipeline() -> None:
    client = FakeEvaluationClient({f"{DATASET}/test-cases": dataset_dict()})

    await resource(client).add_test_cases(DATASET_ID, [NewTestCase(inputs={"query": "hi"})])

    assert client.requests[0]["data"] == {"test_cases": [{"inputs": {"query": "hi"}}]}


@pytest.mark.asyncio
async def test_copy_test_cases_posts_the_ids() -> None:
    client = FakeEvaluationClient({f"{DATASET}/test-cases/copy": dataset_dict()})

    await resource(client).copy_test_cases(DATASET_ID, [TEST_CASE_ID])

    [request] = client.requests
    assert request["method"] == "POST"
    assert request["endpoint"] == f"{DATASET}/test-cases/copy"
    assert request["data"] == {"session_replay_test_case_ids": [TEST_CASE_ID]}


@pytest.mark.asyncio
async def test_remove_test_cases_posts_the_ids() -> None:
    client = FakeEvaluationClient({f"{DATASET}/test-cases/remove": dataset_dict()})

    await resource(client).remove_test_cases(DATASET_ID, [TEST_CASE_ID])

    [request] = client.requests
    assert request["method"] == "POST"
    assert request["endpoint"] == f"{DATASET}/test-cases/remove"
    assert request["data"] == {"session_replay_test_case_ids": [TEST_CASE_ID]}


@pytest.mark.asyncio
async def test_update_test_case_puts_the_changes_and_keeps_an_explicit_null() -> None:
    client = FakeEvaluationClient({f"{DATASET}/test-cases/{TEST_CASE_ID}": test_case_dict(name="New")})

    test_case = await resource(client).update_test_case(DATASET_ID, TEST_CASE_ID, {"name": "New", "setup_source": None})

    assert isinstance(test_case, TestCase)
    assert test_case.name == "New"
    [request] = client.requests
    assert request["method"] == "PUT"
    assert request["endpoint"] == f"{DATASET}/test-cases/{TEST_CASE_ID}"
    assert request["data"] == {"name": "New", "setup_source": None}


@pytest.mark.asyncio
async def test_dataset_methods_surface_a_not_found_from_the_api() -> None:
    client = FakeEvaluationClient({DATASET: ResourceNotFoundError("Dataset not found")})

    with pytest.raises(ResourceNotFoundError):
        await resource(client).get_dataset(DATASET_ID)


def template_dict() -> dict[str, Any]:
    return {
        "key": "tool_calls",
        "name": "Tool calls",
        "category": "Agent efficiency",
        "description": "Counts tool calls.",
        "python_code": "def evaluate(): ...",
        "metrics": {"calls": {"shape": "score", "grain": "session"}},
        "judge_model": None,
        "expected_columns": [],
        "combinable_as_code": True,
    }


@pytest.mark.asyncio
async def test_create_evaluator_posts_name_and_code_only_by_default() -> None:
    client = FakeEvaluationClient({EVALUATORS: evaluator_dict()})

    evaluator = await resource(client).create_evaluator("Answered", "def evaluate(): ...")

    assert isinstance(evaluator, Evaluator)
    assert evaluator.evaluator_id == EVALUATOR_ID
    [request] = client.requests
    assert request["method"] == "POST"
    assert request["endpoint"] == EVALUATORS
    assert request["data"] == {"name": "Answered", "python_code": "def evaluate(): ..."}


@pytest.mark.asyncio
async def test_create_evaluator_posts_the_metric_groups_it_joins() -> None:
    client = FakeEvaluationClient({EVALUATORS: evaluator_dict()})

    await resource(client).create_evaluator(
        "Answered", "code", metric_group_ids=[METRIC_GROUP_ID], new_metric_group_name="Fresh"
    )

    assert client.requests[0]["data"] == {
        "name": "Answered",
        "python_code": "code",
        "metric_group_ids": [METRIC_GROUP_ID],
        "new_metric_group_name": "Fresh",
    }


@pytest.mark.asyncio
async def test_update_evaluator_puts_only_the_fields_given() -> None:
    client = FakeEvaluationClient({f"{EVALUATORS}/{EVALUATOR_ID}": evaluator_dict()})

    await resource(client).update_evaluator(EVALUATOR_ID, python_code="new")
    await resource(client).update_evaluator(EVALUATOR_ID, name="Renamed")

    assert [(r["method"], r["endpoint"], r["data"]) for r in client.requests] == [
        ("PUT", f"{EVALUATORS}/{EVALUATOR_ID}", {"python_code": "new"}),
        ("PUT", f"{EVALUATORS}/{EVALUATOR_ID}", {"name": "Renamed"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(("archived", "action"), [(True, "archive"), (False, "unarchive")])
async def test_set_evaluator_archived_posts_to_archive_or_unarchive(archived: bool, action: str) -> None:
    endpoint = f"{EVALUATORS}/{EVALUATOR_ID}/{action}"
    client = FakeEvaluationClient({endpoint: {**evaluator_dict(), "archived_at": "2026-10-02T00:00:00Z"}})

    evaluator = await resource(client).set_evaluator_archived(EVALUATOR_ID, archived)

    assert evaluator.archived_at == "2026-10-02T00:00:00Z"
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", endpoint)


@pytest.mark.asyncio
async def test_list_evaluator_templates_gets_the_templates() -> None:
    client = FakeEvaluationClient({f"{EVALUATION}/evaluator-templates": [template_dict()]})

    templates = await resource(client).list_evaluator_templates()

    assert isinstance(templates[0], EvaluatorTemplate)
    assert templates[0].combinable_as_code is True
    assert templates[0].metrics["calls"].grain == "session"
    assert client.requests[0]["method"] == "GET"


@pytest.mark.asyncio
async def test_combine_evaluator_templates_posts_keys_and_title() -> None:
    endpoint = f"{EVALUATION}/evaluator-templates/combine"
    client = FakeEvaluationClient({endpoint: {"python_code": "merged", "metrics": {"a": {"grain": "session"}}}})

    combined = await resource(client).combine_evaluator_templates(["tool_calls", "steps"], "Efficiency")

    assert isinstance(combined, CombinedEvaluatorTemplates)
    assert combined.python_code == "merged"
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", endpoint)
    assert request["data"] == {"template_keys": ["tool_calls", "steps"], "title": "Efficiency"}


@pytest.mark.asyncio
async def test_create_metric_group_posts_evaluators_and_weights() -> None:
    client = FakeEvaluationClient({METRIC_GROUPS: metric_group_dict()})

    group = await resource(client).create_metric_group(
        "Weekly", [EVALUATOR_ID], [MetricWeight(evaluator_id=EVALUATOR_ID, metric_key="answered", weight=2)]
    )

    assert isinstance(group, MetricGroup)
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", METRIC_GROUPS)
    assert request["data"] == {
        "name": "Weekly",
        "evaluator_ids": [EVALUATOR_ID],
        "weights": [{"evaluator_id": EVALUATOR_ID, "metric_key": "answered", "weight": 2}],
    }


@pytest.mark.asyncio
async def test_create_metric_group_without_weights_omits_the_field() -> None:
    client = FakeEvaluationClient({METRIC_GROUPS: metric_group_dict()})

    await resource(client).create_metric_group("Weekly", [EVALUATOR_ID])

    assert client.requests[0]["data"] == {"name": "Weekly", "evaluator_ids": [EVALUATOR_ID]}


@pytest.mark.asyncio
async def test_update_metric_group_puts_weights_only_when_given() -> None:
    endpoint = f"{METRIC_GROUPS}/{METRIC_GROUP_ID}"
    client = FakeEvaluationClient({endpoint: metric_group_dict()})

    await resource(client).update_metric_group(METRIC_GROUP_ID, "Weekly", [EVALUATOR_ID])
    await resource(client).update_metric_group(METRIC_GROUP_ID, "Weekly", [EVALUATOR_ID], weights=[])

    assert [(r["method"], r["endpoint"], r["data"]) for r in client.requests] == [
        ("PUT", endpoint, {"name": "Weekly", "evaluator_ids": [EVALUATOR_ID]}),
        ("PUT", endpoint, {"name": "Weekly", "evaluator_ids": [EVALUATOR_ID], "weights": []}),
    ]


@pytest.mark.asyncio
async def test_delete_metric_group_calls_delete_on_the_group() -> None:
    endpoint = f"{METRIC_GROUPS}/{METRIC_GROUP_ID}"
    client = FakeEvaluationClient({endpoint: None})

    await resource(client).delete_metric_group(METRIC_GROUP_ID)

    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("DELETE", endpoint)


EXPERIMENT = f"{EXPERIMENTS}/{COMPARISON_ID}"
NEW_VERSION = "99999999-9999-9999-9999-999999999999"
SIDE_PLAN = {"reused_sessions": 2, "replays_needed": 1, "test_cases_short": 1}


@pytest.mark.asyncio
async def test_preview_experiment_posts_the_targets_without_a_name() -> None:
    plan = {"candidate": SIDE_PLAN, "baseline": SIDE_PLAN, "cells": 6, "max_cells": 100, "max_runs": 50}
    client = FakeEvaluationClient({f"{EXPERIMENTS}/preview": plan})

    result = await resource(client).preview_experiment(
        dataset_id=DATASET_ID,
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE_NAME,
        candidate_pipeline_version_id=NEW_VERSION,
        sessions_per_test_case=2,
    )

    assert isinstance(result, ExperimentPlan)
    assert result.candidate.replays_needed == 1
    assert result.max_cells == 100
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", f"{EXPERIMENTS}/preview")
    assert request["data"] == {
        "session_replay_dataset_id": DATASET_ID,
        "metric_group_id": METRIC_GROUP_ID,
        "candidate": {"pipeline_id": PIPELINE_UUID, "pipeline_version_id": NEW_VERSION},
        "sessions_per_test_case": 2,
        "replay_mode": "FIRST_USER_MESSAGE",
    }


@pytest.mark.asyncio
async def test_get_experiment_reads_the_detail_with_test_cases_and_run_counts() -> None:
    detail = comparison_dict()
    detail["test_cases"] = [{"session_replay_test_case_id": TEST_CASE_ID, "name": "Order status"}]
    detail["candidate"] = {
        **detail["candidate"],
        "pipeline_name": PIPELINE_NAME,
        "run_counts": {"created": 0, "started": 1, "ended": 2, "failed": 1},
        "sessions": [{"session_replay_test_case_id": TEST_CASE_ID, "session_id": SESSION_ID, "source": "ORIGINAL"}],
    }
    client = FakeEvaluationClient({EXPERIMENT: detail})

    experiment = await resource(client).get_experiment(COMPARISON_ID)

    assert isinstance(experiment, ExperimentDetail)
    assert experiment.experiment_id == COMPARISON_ID
    assert [(t.test_case_id, t.name) for t in experiment.test_cases] == [(TEST_CASE_ID, "Order status")]
    assert experiment.candidate.run_counts is not None
    assert experiment.candidate.run_counts.failed == 1
    assert experiment.candidate.experiment_run_id == RUN_ID
    assert experiment.candidate.pipeline_name == PIPELINE_NAME
    assert client.requests[0]["method"] == "GET"


@pytest.mark.asyncio
async def test_get_experiment_from_an_older_api_without_detail_fields_still_parses() -> None:
    client = FakeEvaluationClient({EXPERIMENT: comparison_dict()})

    experiment = await resource(client).get_experiment(COMPARISON_ID)

    assert experiment.test_cases == []
    assert experiment.candidate.run_counts is None


@pytest.mark.asyncio
async def test_update_experiment_patches_only_what_changes_with_resolved_pipeline_ids() -> None:
    client = FakeEvaluationClient({EXPERIMENT: comparison_dict()})

    result = await resource(client).update_experiment(
        COMPARISON_ID, name="Renamed", candidate_pipeline_name=PIPELINE_NAME, candidate_pipeline_version_id=NEW_VERSION
    )
    await resource(client).update_experiment(COMPARISON_ID, name="Only a name")
    await resource(client).update_experiment(COMPARISON_ID, recorded_baseline=True)

    assert isinstance(result, Experiment)
    assert [(r["method"], r["endpoint"]) for r in client.requests] == [("PATCH", EXPERIMENT)] * 3
    assert client.requests[0]["data"] == {
        "name": "Renamed",
        "candidate": {"pipeline_id": PIPELINE_UUID, "pipeline_version_id": NEW_VERSION},
    }
    assert client.requests[1]["data"] == {"name": "Only a name"}
    assert client.requests[2]["data"] == {"recorded_baseline": True}


@pytest.mark.asyncio
async def test_preview_update_experiment_posts_the_same_body_to_preview_update() -> None:
    client = FakeEvaluationClient({f"{EXPERIMENT}/preview-update": {"candidate": None, "baseline": SIDE_PLAN}})

    plan = await resource(client).preview_update_experiment(
        COMPARISON_ID, baseline_pipeline_name=PIPELINE_NAME, baseline_pipeline_version_id=NEW_VERSION
    )

    assert isinstance(plan, ExperimentUpdatePlan)
    assert plan.candidate is None
    assert plan.baseline is not None
    assert plan.baseline.replays_needed == 1
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", f"{EXPERIMENT}/preview-update")
    assert request["data"] == {"baseline": {"pipeline_id": PIPELINE_UUID, "pipeline_version_id": NEW_VERSION}}


@pytest.mark.asyncio
@pytest.mark.parametrize(("replays", "suffix"), [(False, "rerun-failed"), (True, "rerun-failed-replays")])
async def test_rerun_failed_experiment_posts_to_the_evaluations_or_replays_route(replays: bool, suffix: str) -> None:
    client = FakeEvaluationClient({f"{EXPERIMENT}/{suffix}": comparison_dict()})

    result = await resource(client).rerun_failed_experiment(COMPARISON_ID, replays=replays)

    assert isinstance(result, Experiment)
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", f"{EXPERIMENT}/{suffix}")


@pytest.mark.asyncio
async def test_rescore_experiment_posts_to_rescore() -> None:
    client = FakeEvaluationClient({f"{EXPERIMENT}/rescore": comparison_dict()})

    result = await resource(client).rescore_experiment(COMPARISON_ID)

    assert isinstance(result, Experiment)
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", f"{EXPERIMENT}/rescore")


@pytest.mark.asyncio
async def test_delete_experiment_calls_delete_on_the_experiment() -> None:
    client = FakeEvaluationClient({EXPERIMENT: None})

    await resource(client).delete_experiment(COMPARISON_ID)

    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("DELETE", EXPERIMENT)


SESSION_SCORING_RUNS = f"{PIPELINE}/scoring-runs"
EVALUATION_RUNS = f"{PIPELINE}/evaluation-runs"
DEPLOYMENT_ID = "dddddddd-1111-2222-3333-444444444444"
WINDOW = SessionWindow(
    start="2026-10-01T00:00:00Z", end="2026-10-08T00:00:00Z", origin="SERVICE", deployment_id=DEPLOYMENT_ID
)
WINDOW_BODY = {
    "from": "2026-10-01T00:00:00Z",
    "to": "2026-10-08T00:00:00Z",
    "origin": "SERVICE",
    "deployment_id": DEPLOYMENT_ID,
}


@pytest.mark.asyncio
async def test_list_session_experiment_runs_reads_the_pipeline_wide_route_with_the_session() -> None:
    client = FakeEvaluationClient({SESSION_SCORING_RUNS: [run_dict()]})

    runs = await resource(client).list_session_experiment_runs(PIPELINE_NAME, SESSION_ID, limit=5)

    assert [r.pipeline_experiment_id for r in runs] == [METRIC_GROUP_ID]
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("GET", SESSION_SCORING_RUNS)
    assert request["params"] == {"session_id": SESSION_ID, "limit": 5}


@pytest.mark.asyncio
async def test_an_experiment_run_reads_the_window_it_judged_by_its_api_names() -> None:
    client = FakeEvaluationClient({RUNS: [{**run_dict(), "window": WINDOW_BODY, "resolved_sessions": 12}, run_dict()]})

    windowed, named = await resource(client).list_experiment_runs(PIPELINE_NAME, METRIC_GROUP_ID)

    assert windowed.window == WINDOW
    assert windowed.resolved_sessions == 12
    assert (named.window, named.resolved_sessions) == (None, None)


@pytest.mark.asyncio
async def test_start_experiment_run_posts_the_named_sessions_and_only_what_is_set() -> None:
    accepted = {"pipeline_experiment_run_id": RUN_ID, "cells": 2}
    client = FakeEvaluationClient({RUNS: accepted})

    result = await resource(client).start_experiment_run(PIPELINE_NAME, METRIC_GROUP_ID, session_ids=[SESSION_ID])

    assert result == ExperimentRunAccepted(pipeline_experiment_run_id=RUN_ID, cells=2)
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", RUNS)
    assert request["data"] == {"session_ids": [SESSION_ID]}


@pytest.mark.asyncio
async def test_start_experiment_run_posts_a_window_under_its_api_names_with_reuse_selection_and_focus() -> None:
    client = FakeEvaluationClient({RUNS: {"pipeline_experiment_run_id": RUN_ID, "cells": 40}})
    query_id = "99999999-1111-2222-3333-444444444444"

    await resource(client).start_experiment_run(PIPELINE_NAME, METRIC_GROUP_ID, window=WINDOW, reuse="REUSE_SUCCEEDED")
    await resource(client).start_experiment_run(
        PIPELINE_NAME,
        METRIC_GROUP_ID,
        session_ids=[SESSION_ID],
        selection="HAND_PICKED",
        focus={SESSION_ID: [query_id]},
    )

    windowed, focused = (r["data"] for r in client.requests)
    assert windowed == {"window": WINDOW_BODY, "reuse": "REUSE_SUCCEEDED"}
    assert focused == {"session_ids": [SESSION_ID], "selection": "HAND_PICKED", "focus": {SESSION_ID: [query_id]}}


@pytest.mark.asyncio
async def test_preview_experiment_run_posts_the_window_to_preview() -> None:
    preview = {
        "sessions": 12,
        "more_than": False,
        "evaluators": 3,
        "cells": 36,
        "ceiling": {"sessions": 50, "cells": 200},
    }
    client = FakeEvaluationClient({f"{RUNS}/preview": preview})

    result = await resource(client).preview_experiment_run(PIPELINE_NAME, METRIC_GROUP_ID, WINDOW)

    assert isinstance(result, ExperimentRunPreview)
    assert (result.cells, result.ceiling.cells) == (36, 200)
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", f"{RUNS}/preview")
    assert request["data"] == WINDOW_BODY


@pytest.mark.asyncio
async def test_run_evaluator_posts_the_version_and_the_session_and_returns_the_run_id() -> None:
    client = FakeEvaluationClient({EVALUATION_RUNS: {"evaluation_run_id": EVALUATION_RUN_ID}})

    run_id = await resource(client).run_evaluator(PIPELINE_NAME, VERSION_ID, SESSION_ID)

    assert run_id == EVALUATION_RUN_ID
    [request] = client.requests
    assert (request["method"], request["endpoint"]) == ("POST", EVALUATION_RUNS)
    assert request["data"] == {"evaluator_version_id": VERSION_ID, "session_id": SESSION_ID}


def evaluation_run_dict(**overrides: Any) -> dict[str, Any]:
    return {
        "evaluation_run_id": EVALUATION_RUN_ID,
        "pipeline_id": PIPELINE_UUID,
        "status": "ENDED",
        "outcome": "SUCCEEDED",
        "metrics": [{"metric_key": "answered", "address": "session", "kind": "label", "label": "yes"}],
        "evaluator_version_id": VERSION_ID,
        "session_id": SESSION_ID,
        "trace_ids": [SESSION_ID],
        "focus": None,
        "provenance": {"origin": "SERVICE", "deployment_id": DEPLOYMENT_ID, "pipeline_version_ids": []},
        "error_detail": None,
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-01T00:01:00Z",
        **overrides,
    }


@pytest.mark.asyncio
async def test_list_evaluation_runs_reads_the_pipeline_route_with_the_limit() -> None:
    client = FakeEvaluationClient({EVALUATION_RUNS: [evaluation_run_dict()]})

    runs = await resource(client).list_evaluation_runs(PIPELINE_NAME, limit=7)

    assert isinstance(runs[0], EvaluationRun)
    assert runs[0].provenance is not None
    assert runs[0].provenance.deployment_id == DEPLOYMENT_ID
    [request] = client.requests
    assert (request["method"], request["endpoint"], request["params"]) == ("GET", EVALUATION_RUNS, {"limit": 7})


@pytest.mark.asyncio
async def test_get_evaluation_run_reads_one_run_by_id() -> None:
    client = FakeEvaluationClient({f"{EVALUATION_RUNS}/{EVALUATION_RUN_ID}": evaluation_run_dict()})

    run = await resource(client).get_evaluation_run(PIPELINE_NAME, EVALUATION_RUN_ID)

    assert (run.status, run.outcome, run.metrics[0].label) == ("ENDED", "SUCCEEDED", "yes")
    assert run.trace_ids == [SESSION_ID]


@pytest.mark.asyncio
async def test_an_evaluation_run_from_an_older_api_without_the_extra_fields_still_parses() -> None:
    minimal = {"evaluation_run_id": EVALUATION_RUN_ID, "status": "STARTED", "evaluator_version_id": VERSION_ID}
    client = FakeEvaluationClient({f"{EVALUATION_RUNS}/{EVALUATION_RUN_ID}": minimal})

    run = await resource(client).get_evaluation_run(PIPELINE_NAME, EVALUATION_RUN_ID)

    assert (run.provenance, run.focus, run.trace_ids, run.created_at) == (None, None, [], None)


@pytest.mark.asyncio
async def test_create_and_preview_experiment_send_reuse_sessions_only_when_false() -> None:
    client = FakeEvaluationClient(
        {
            EXPERIMENTS: comparison_dict(),
            f"{EXPERIMENTS}/preview": {
                "candidate": SIDE_PLAN,
                "baseline": SIDE_PLAN,
                "cells": 6,
                "max_cells": 100,
                "max_runs": 50,
            },
        }
    )
    target: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "metric_group_id": METRIC_GROUP_ID,
        "candidate_pipeline_name": PIPELINE_NAME,
        "candidate_pipeline_version_id": NEW_VERSION,
    }

    await resource(client).create_experiment(name="Default", **target)
    await resource(client).create_experiment(name="Fresh", reuse_sessions=False, **target)
    await resource(client).preview_experiment(**target)
    await resource(client).preview_experiment(reuse_sessions=False, **target)

    default_create, fresh_create, default_preview, fresh_preview = (r["data"] for r in client.requests)
    assert "reuse_sessions" not in default_create
    assert "reuse_sessions" not in default_preview
    assert fresh_create["reuse_sessions"] is False
    assert fresh_preview["reuse_sessions"] is False


SUITES = f"{PIPELINE}/replay-suites"
SUITE_ID = "dddddddd-1111-2222-3333-555555555555"
IMPORTED = f"{EVALUATION}/imported-sessions/{SESSION_ID}"
QUERY_ID = "eeeeeeee-1111-2222-3333-555555555555"
SPAN_ID = "ffffffff-1111-2222-3333-555555555555"


def suite_dict() -> dict[str, Any]:
    run = {**replay_run_dict(), "session_id": SESSION_ID, "session_replay_suite_id": SUITE_ID, "repetition": 2}
    return {
        "session_replay_suite_id": SUITE_ID,
        "pipeline_id": PIPELINE_UUID,
        "pipeline_version_id": DRAFT_VERSION_ID,
        "session_replay_dataset_id": DATASET_ID,
        "test_case_count": 1,
        "repetitions": 2,
        "replay_mode": "FIRST_USER_MESSAGE",
        "status": "STARTED",
        "run_counts": {"created": 0, "started": 1, "ended": 1, "failed": 0},
        "experiment": {
            "pipeline_experiment_id": METRIC_GROUP_ID,
            "reuse": "RERUN_ALL",
            "source_experiment_run_id": RUN_ID,
            "source_error": None,
            "replayed_experiment_run_id": None,
            "replayed_error": "too many runs",
        },
        "created_at": "2026-10-07T00:00:00Z",
        "test_cases": [
            {
                "session_replay_test_case_id": TEST_CASE_ID,
                "name": "Order status",
                "session_id": SESSION_ID,
                "runs": [run],
            }
        ],
    }


def imported_turn_dict() -> dict[str, Any]:
    return {
        "query_id": QUERY_ID,
        "query": "who wrote Dune?",
        "status": "success",
        "duration_s": 1.5,
        "created_at": "2026-10-07T00:00:00Z",
        "haystack_trace": {
            "schema_version": "haystack-trace/v1",
            "run_id": RUN_ID,
            "started_at": "2026-10-07T00:00:00Z",
            "status": "success",
            "traces": [
                {
                    "span_id": SPAN_ID,
                    "operation_name": "haystack.component.run",
                    "start_time": "2026-10-07T00:00:00Z",
                    "tags": {"haystack.component.type": "Retriever"},
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_list_session_replays_calls_the_replay_runs_route() -> None:
    run = {**replay_run_dict(), "session_replay_suite_id": SUITE_ID, "repetition": 2, "session_id": SESSION_ID}
    client = FakeEvaluationClient({REPLAYS: [run]})

    runs = await resource(client).list_session_replays(PIPELINE_NAME, limit=5)

    assert (runs[0].suite_id, runs[0].repetition, runs[0].session_id) == (SUITE_ID, 2, SESSION_ID)
    assert client.requests[0]["method"] == "GET"
    assert client.requests[0]["endpoint"] == REPLAYS
    assert client.requests[0]["params"] == {"limit": 5}


@pytest.mark.asyncio
async def test_start_replay_suite_posts_the_dataset_and_version_and_only_the_metric_group_when_given() -> None:
    client = FakeEvaluationClient({SUITES: {"session_replay_suite_id": SUITE_ID, "run_count": 4}})

    plain = await resource(client).start_replay_suite(PIPELINE_NAME, DATASET_ID, DRAFT_VERSION_ID)
    scored = await resource(client).start_replay_suite(
        PIPELINE_NAME,
        DATASET_ID,
        DRAFT_VERSION_ID,
        repetitions=2,
        replay_mode="ALL_USER_MESSAGES",
        metric_group_id=METRIC_GROUP_ID,
        reuse="REUSE_SUCCEEDED",
    )
    with_default_reuse = await resource(client).start_replay_suite(
        PIPELINE_NAME, DATASET_ID, DRAFT_VERSION_ID, metric_group_id=METRIC_GROUP_ID
    )

    assert isinstance(plain, ReplaySuiteAccepted)
    assert (plain.suite_id, plain.run_count) == (SUITE_ID, 4)
    assert scored.suite_id == with_default_reuse.suite_id == SUITE_ID
    first, second, third = client.requests
    assert first["method"] == "POST"
    assert first["endpoint"] == SUITES
    assert first["data"] == {
        "session_replay_dataset_id": DATASET_ID,
        "pipeline_version_id": DRAFT_VERSION_ID,
        "repetitions": 1,
        "replay_mode": "FIRST_USER_MESSAGE",
    }
    assert second["data"] == {
        "session_replay_dataset_id": DATASET_ID,
        "pipeline_version_id": DRAFT_VERSION_ID,
        "repetitions": 2,
        "replay_mode": "ALL_USER_MESSAGES",
        "experiment": {"pipeline_experiment_id": METRIC_GROUP_ID, "reuse": "REUSE_SUCCEEDED"},
    }
    assert third["data"]["experiment"] == {"pipeline_experiment_id": METRIC_GROUP_ID}


@pytest.mark.asyncio
async def test_list_replay_suites_calls_the_suites_route() -> None:
    summary = {k: v for k, v in suite_dict().items() if k != "test_cases"}
    client = FakeEvaluationClient({SUITES: [summary]})

    suites = await resource(client).list_replay_suites(PIPELINE_NAME, limit=7)

    assert isinstance(suites[0], ReplaySuiteSummary)
    assert (suites[0].suite_id, suites[0].dataset_id, suites[0].run_counts.ended) == (SUITE_ID, DATASET_ID, 1)
    assert suites[0].metric_group is not None
    assert suites[0].metric_group.metric_group_id == METRIC_GROUP_ID
    assert client.requests[0]["method"] == "GET"
    assert client.requests[0]["endpoint"] == SUITES
    assert client.requests[0]["params"] == {"limit": 7}


@pytest.mark.asyncio
async def test_get_replay_suite_returns_its_runs_by_test_case() -> None:
    client = FakeEvaluationClient({f"{SUITES}/{SUITE_ID}": suite_dict()})

    suite = await resource(client).get_replay_suite(PIPELINE_NAME, SUITE_ID)

    assert isinstance(suite, ReplaySuite)
    assert suite.test_cases[0].test_case_id == TEST_CASE_ID
    assert suite.test_cases[0].runs[0].repetition == 2
    assert suite.metric_group is not None
    assert (suite.metric_group.source_run_id, suite.metric_group.replayed_error) == (RUN_ID, "too many runs")
    assert client.requests[0]["endpoint"] == f"{SUITES}/{SUITE_ID}"


@pytest.mark.asyncio
async def test_a_replay_suite_parses_without_the_fields_an_older_hub_api_lacks() -> None:
    client = FakeEvaluationClient({f"{SUITES}/{SUITE_ID}": {"session_replay_suite_id": SUITE_ID, "status": "CREATED"}})

    suite = await resource(client).get_replay_suite(PIPELINE_NAME, SUITE_ID)

    assert (suite.suite_id, suite.metric_group, suite.test_cases) == (SUITE_ID, None, [])


@pytest.mark.asyncio
async def test_list_imported_session_traces_calls_the_workspace_route() -> None:
    client = FakeEvaluationClient({f"{IMPORTED}/traces": [imported_turn_dict()]})

    turns = await resource(client).list_imported_session_traces(SESSION_ID)

    assert isinstance(turns[0], PipelineTraceEntry)
    assert turns[0].query_id == QUERY_ID
    assert turns[0].haystack_trace is not None
    assert turns[0].haystack_trace.traces[0].span_id == SPAN_ID
    assert client.requests[0]["method"] == "GET"
    assert client.requests[0]["endpoint"] == f"{IMPORTED}/traces"


@pytest.mark.asyncio
async def test_get_imported_session_trace_calls_the_turn_route() -> None:
    client = FakeEvaluationClient({f"{IMPORTED}/traces/{QUERY_ID}": imported_turn_dict()})

    turn = await resource(client).get_imported_session_trace(SESSION_ID, QUERY_ID)

    assert turn.query == "who wrote Dune?"
    assert client.requests[0]["endpoint"] == f"{IMPORTED}/traces/{QUERY_ID}"


@pytest.mark.asyncio
async def test_get_imported_session_trace_span_tags_calls_the_span_route() -> None:
    tags = {"haystack.component.input": {"query": "x"}}
    client = FakeEvaluationClient({f"{IMPORTED}/traces/{QUERY_ID}/tags/{SPAN_ID}": tags})

    result = await resource(client).get_imported_session_trace_span_tags(SESSION_ID, QUERY_ID, SPAN_ID)

    assert result == tags
    assert client.requests[0]["endpoint"] == f"{IMPORTED}/traces/{QUERY_ID}/tags/{SPAN_ID}"
