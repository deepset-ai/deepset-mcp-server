# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    Experiment,
    ExperimentRun,
    ExperimentRunGrid,
    ExperimentRunReport,
    SessionList,
)
from deepset_mcp.api.evaluation.protocols import EvaluationResourceProtocol
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.tools.evaluation import (
    get_evaluator,
    get_experiment_run,
    list_evaluators,
    list_experiments,
    list_sessions,
)
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
PIPELINE = "my-pipeline"
E1 = "11111111-1111-1111-1111-111111111111"
E2 = "22222222-2222-2222-2222-222222222222"
V1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXPERIMENT_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"
SESSION_A = "55555555-5555-5555-5555-555555555555"
SESSION_B = "66666666-6666-6666-6666-666666666666"


def run(run_id: str = RUN_ID) -> ExperimentRun:
    return ExperimentRun.model_validate(
        {
            "pipeline_experiment_run_id": run_id,
            "pipeline_experiment_id": EXPERIMENT_ID,
            "status": "ENDED",
            "selection": "HAND_PICKED",
            "created_at": "2026-10-01T00:00:00Z",
        }
    )


def cell(evaluator_id: str, outcome: str | None, metrics: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "evaluator_id": evaluator_id,
        "evaluation_run": {
            "evaluation_run_id": "77777777-7777-7777-7777-777777777777",
            "pipeline_id": "88888888-8888-8888-8888-888888888888",
            "status": extra.pop("status", "ENDED"),
            "outcome": outcome,
            "metrics": metrics,
            "evaluator_version_id": V1,
            "trace_ids": ["99999999-9999-9999-9999-999999999999"],
            "created_at": "2026-10-01T00:00:00Z",
            **extra,
        },
    }


def grid() -> ExperimentRunGrid:
    """Two Sessions; E1 declares a Score and a Label, E2 breaks on one Session and fails on the other."""
    return ExperimentRunGrid.model_validate(
        {
            "run": run().model_dump(),
            "evaluator_ids": [E1, E2],
            "rows": [
                {
                    "session_id": SESSION_A,
                    "cells": [
                        cell(
                            E1,
                            "SUCCEEDED",
                            [
                                {"metric_key": "accuracy", "address": "session", "kind": "score", "score": 0.8},
                                {"metric_key": "answered", "address": "turn/0", "kind": "label", "label": "yes"},
                                {
                                    "metric_key": "answered",
                                    "address": "turn/1",
                                    "kind": "label",
                                    "label": "no",
                                    "rationale": "The reply asks the question back.",
                                },
                            ],
                        ),
                        cell(
                            E2,
                            "ERRORED",
                            [],
                            error_detail={"type": "KeyError", "message": "'replies'", "stacktrace": []},
                        ),
                    ],
                },
                {
                    "session_id": SESSION_B,
                    "cells": [
                        cell(
                            E1,
                            "SUCCEEDED",
                            [
                                {"metric_key": "accuracy", "address": "session", "kind": "score", "score": 0.4},
                                {
                                    "metric_key": "answered",
                                    "address": "turn/0",
                                    "kind": "not_applicable",
                                    "reason": "No reply.",
                                },
                            ],
                        ),
                        cell(E2, None, [], status="FAILED"),
                    ],
                },
            ],
            "counts": {"cells": 4, "succeeded": 2, "errored": 1, "failed": 1, "unresolved_sessions": 0, "running": 0},
        }
    )


class FakeEvaluationResource(EvaluationResourceProtocol):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))
        if self.error is not None:
            raise self.error

    async def list_evaluators(self, limit: int = 200) -> list[Evaluator]:
        self._record("list_evaluators", limit=limit)
        return [
            Evaluator.model_validate(
                {"evaluator_id": E1, "name": "Answered", "created_at": "2026-10-01T00:00:00Z", "latest_version": None}
            )
        ]

    async def get_evaluator(self, evaluator_id: str) -> Evaluator:
        self._record("get_evaluator", evaluator_id=evaluator_id)
        return Evaluator.model_validate(
            {"evaluator_id": evaluator_id, "name": "Answered", "created_at": "2026-10-01T00:00:00Z"}
        )

    async def get_evaluator_version(self, evaluator_id: str, version_id: str) -> EvaluatorVersion:
        self._record("get_evaluator_version", evaluator_id=evaluator_id, version_id=version_id)
        return EvaluatorVersion.model_validate(
            {
                "evaluator_version_id": version_id,
                "evaluator_id": evaluator_id,
                "content_hash": "abc",
                "metrics": {},
                "metrics_legacy": True,
                "created_at": "2026-10-01T00:00:00Z",
                "python_code": "def evaluate(session, focus): ...",
            }
        )

    async def list_experiments(self, pipeline_name: str, limit: int = 200) -> list[Experiment]:
        self._record("list_experiments", pipeline_name=pipeline_name)
        return [
            Experiment.model_validate(
                {
                    "pipeline_experiment_id": experiment_id,
                    "name": name,
                    "evaluator_ids": [E1],
                    "created_at": "2026-10-01T00:00:00Z",
                }
            )
            for experiment_id, name in [(EXPERIMENT_ID, "Weekly"), ("00000000-0000-0000-0000-00000000000e", "Fresh")]
        ]

    async def list_experiment_runs(self, pipeline_name: str, experiment_id: str, limit: int = 50) -> list[ExperimentRun]:
        self._record("list_experiment_runs", experiment_id=experiment_id, limit=limit)
        return [run()] if experiment_id == EXPERIMENT_ID else []

    async def get_experiment_run(self, pipeline_name: str, experiment_id: str, run_id: str) -> ExperimentRunGrid:
        self._record("get_experiment_run", experiment_id=experiment_id, run_id=run_id)
        return grid()

    async def list_sessions(
        self,
        pipeline_name: str,
        origin: str | None = None,
        deployment_id: str | None = None,
        pipeline_version_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionList:
        self._record("list_sessions", origin=origin, since=since, limit=limit, cursor=cursor)
        return SessionList.model_validate({"data": [], "next": None})


class FakeClient(BaseFakeClient):
    def __init__(self, evaluation_resource: FakeEvaluationResource) -> None:
        super().__init__()
        self.evaluation_resource = evaluation_resource

    def evaluation(self, workspace: str) -> FakeEvaluationResource:
        return self.evaluation_resource


@pytest.mark.asyncio
async def test_get_experiment_run_summarises_each_metric_over_every_row() -> None:
    report = await get_experiment_run(
        client=FakeClient(FakeEvaluationResource()),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        experiment_id=EXPERIMENT_ID,
        run_id=RUN_ID,
        max_rows=1,
    )

    assert isinstance(report, ExperimentRunReport)
    assert report.run.selection == "HAND_PICKED"
    assert report.counts.errored == 1
    by_key = {(m.evaluator_id, m.metric_key): m for m in report.metrics}
    accuracy = by_key[(E1, "accuracy")]
    assert (accuracy.kind, accuracy.count, accuracy.min, accuracy.max) == ("score", 2, 0.4, 0.8)
    assert accuracy.mean == pytest.approx(0.6)
    answered = by_key[(E1, "answered")]
    assert (answered.kind, answered.labels, answered.not_applicable) == ("label", {"yes": 1, "no": 1}, 1)
    assert set(by_key) == {(E1, "accuracy"), (E1, "answered")}


@pytest.mark.asyncio
async def test_get_experiment_run_flattens_cells_and_caps_rows() -> None:
    report = await get_experiment_run(
        client=FakeClient(FakeEvaluationResource()),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        experiment_id=EXPERIMENT_ID,
        run_id=RUN_ID,
        max_rows=1,
    )

    assert isinstance(report, ExperimentRunReport)
    assert (report.total_rows, report.rows_truncated, len(report.rows)) == (2, True, 1)
    judged, broken = report.rows[0].cells
    assert (judged.evaluator_id, judged.outcome, judged.evaluator_version_id) == (E1, "SUCCEEDED", V1)
    assert judged.metrics[2].rationale == "The reply asks the question back."
    assert (broken.outcome, broken.error_detail) == ("ERRORED", {"type": "KeyError", "message": "'replies'", "stacktrace": []})


@pytest.mark.asyncio
async def test_list_experiments_attaches_each_last_run() -> None:
    resource = FakeEvaluationResource()

    experiments = await list_experiments(client=FakeClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE)

    assert isinstance(experiments, list)
    assert [(e.name, e.last_run is not None) for e in experiments] == [("Weekly", True), ("Fresh", False)]
    assert {c[1]["limit"] for c in resource.calls if c[0] == "list_experiment_runs"} == {1}


@pytest.mark.asyncio
async def test_get_evaluator_reads_the_version_source_only_when_asked() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    evaluator = await get_evaluator(client=client, workspace=WORKSPACE, evaluator_id=E1)
    version = await get_evaluator(client=client, workspace=WORKSPACE, evaluator_id=E1, version_id=V1)

    assert isinstance(evaluator, Evaluator)
    assert isinstance(version, EvaluatorVersion)
    assert version.python_code.startswith("def evaluate")
    assert [c[0] for c in resource.calls] == ["get_evaluator", "get_evaluator_version"]


@pytest.mark.asyncio
async def test_list_evaluators_and_sessions_pass_through() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    evaluators = await list_evaluators(client=client, workspace=WORKSPACE)
    sessions = await list_sessions(
        client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, origin="SERVICE", since="2026-09-28T00:00:00Z"
    )

    assert isinstance(evaluators, list) and evaluators[0].name == "Answered"
    assert isinstance(sessions, SessionList)
    assert resource.calls[-1] == (
        "list_sessions",
        {"origin": "SERVICE", "since": "2026-09-28T00:00:00Z", "limit": 50, "cursor": None},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ResourceNotFoundError(), "not found"),
        (BadRequestError(message="bad"), "Failed"),
        (UnexpectedAPIError(status_code=500, message="boom"), "Failed"),
    ],
)
async def test_errors_come_back_as_readable_strings(error: Exception, expected: str) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))

    results = [
        await list_evaluators(client=client, workspace=WORKSPACE),
        await get_evaluator(client=client, workspace=WORKSPACE, evaluator_id=E1),
        await list_experiments(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE),
        await get_experiment_run(
            client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, experiment_id=EXPERIMENT_ID, run_id=RUN_ID
        ),
        await list_sessions(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE),
    ]

    for result in results:
        assert isinstance(result, str)
        assert expected in result
