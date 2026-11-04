# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from deepset_mcp.api.evaluation.models import (
    CombinedEvaluatorTemplates,
    Composite,
    Dataset,
    DatasetSummary,
    EvaluationRun,
    EvaluationTryResult,
    Evaluator,
    EvaluatorTemplate,
    EvaluatorVersion,
    Experiment,
    ExperimentDetail,
    ExperimentPlan,
    ExperimentResults,
    ExperimentResultsReport,
    ExperimentRun,
    ExperimentRunAccepted,
    ExperimentRunGrid,
    ExperimentRunPreview,
    ExperimentRunReport,
    ExperimentUpdatePlan,
    LabelAggregate,
    MetricDeclaration,
    MetricGroup,
    MetricWeight,
    NewTestCase,
    NoComposite,
    NoNormalizedMean,
    NormalizedMean,
    ReplaySuite,
    ReplaySuiteAccepted,
    ReplaySuiteSummary,
    ScoreAggregate,
    SessionList,
    SessionReplayReport,
    SessionReplayRun,
    SessionWindow,
    TestCase,
    TryReport,
    TryState,
)
from deepset_mcp.api.evaluation.protocols import EvaluationResourceProtocol
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.search_history.models import PipelineTraceEntry, PipelineTraceSummary
from deepset_mcp.api.shared_models import PaginatedResponse
from deepset_mcp.tools import evaluation as evaluation_tools
from deepset_mcp.tools.evaluation import (
    add_test_cases,
    combine_evaluator_templates,
    copy_test_cases,
    create_dataset,
    create_evaluator,
    create_experiment,
    create_metric_group,
    delete_dataset,
    delete_experiment,
    delete_metric_group,
    get_dataset,
    get_evaluation_run,
    get_evaluation_try,
    get_evaluator,
    get_experiment,
    get_experiment_results,
    get_experiment_run,
    get_imported_session_trace,
    get_imported_session_trace_span_tags,
    get_replay_suite,
    get_session_replay,
    list_datasets,
    list_evaluation_runs,
    list_evaluator_templates,
    list_evaluators,
    list_experiment_runs,
    list_experiments,
    list_imported_session_traces,
    list_metric_groups,
    list_replay_suites,
    list_session_replays,
    list_sessions,
    remove_test_cases,
    replay_session,
    rerun_failed_experiment,
    rescore_experiment,
    run_evaluator,
    set_evaluator_archived,
    start_experiment_run,
    start_replay_suite,
    try_evaluator,
    update_dataset,
    update_evaluator,
    update_experiment,
    update_metric_group,
    update_test_case,
)
from test.unit.conftest import BaseFakeClient

WORKSPACE = "my-workspace"
PIPELINE = "my-pipeline"
E1 = "11111111-1111-1111-1111-111111111111"
E2 = "22222222-2222-2222-2222-222222222222"
V1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
METRIC_GROUP_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"
SESSION_A = "55555555-5555-5555-5555-555555555555"
SESSION_B = "66666666-6666-6666-6666-666666666666"
COMPARISON_ID = "99999999-9999-9999-9999-999999999999"
PIPELINE_ID = "88888888-8888-8888-8888-888888888888"

DATASET_ID = "bbbbbbbb-1111-2222-3333-444444444444"
TEST_CASE_ID = "cccccccc-1111-2222-3333-444444444444"
SIDE_PLAN = {"reused_sessions": 2, "replays_needed": 1, "test_cases_short": 1}


def dataset_dict() -> dict[str, Any]:
    return {
        "session_replay_dataset_id": DATASET_ID,
        "pipeline_ids": [PIPELINE_ID],
        "name": "Regression set",
        "test_case_count": 1,
        "created_at": "2026-10-01T00:00:00Z",
        "test_cases": [
            {
                "session_replay_test_case_id": TEST_CASE_ID,
                "session_id": SESSION_A,
                "name": "Order status",
                "created_at": "2026-10-01T00:00:00Z",
            }
        ],
    }


def run(run_id: str = RUN_ID) -> ExperimentRun:
    return ExperimentRun.model_validate(
        {
            "pipeline_experiment_run_id": run_id,
            "pipeline_experiment_id": METRIC_GROUP_ID,
            "status": "ENDED",
            "selection": "HAND_PICKED",
            "created_at": "2026-10-01T00:00:00Z",
        }
    )


EVALUATION_RUN_ID = "77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def evaluation_run(status: str = "ENDED") -> EvaluationRun:
    return EvaluationRun.model_validate(
        {
            "evaluation_run_id": EVALUATION_RUN_ID,
            "status": status,
            "outcome": "SUCCEEDED" if status == "ENDED" else None,
            "metrics": [{"metric_key": "answered", "address": "session", "kind": "label", "label": "yes"}]
            if status == "ENDED"
            else [],
            "evaluator_version_id": V1,
            "session_id": SESSION_A,
        }
    )


def comparison_side(**overrides: Any) -> dict[str, Any]:
    return {
        "pipeline_id": PIPELINE_ID,
        "pipeline_version_id": "00000000-0000-0000-0000-0000000000b1",
        "recorded": False,
        "status": "ENDED",
        "session_replay_suite_id": None,
        "experiment_run_id": RUN_ID,
        "scoring_runs": [{"pipeline_id": PIPELINE_ID, "experiment_run_id": RUN_ID}],
        "reused_sessions": 2,
        "replays_needed": 0,
        "run_counts": None,
        "sessions": [{"session_replay_test_case_id": E2, "session_id": SESSION_A, "source": "ORIGINAL"}],
        "scoring_counts": {"cells": 2, "succeeded": 1, "errored": 1, "failed": 0, "running": 0},
        "error": None,
        **overrides,
    }


def comparison() -> dict[str, Any]:
    """A comparison as `GET .../evaluation/experiments` lists it."""
    return {
        "comparison_id": COMPARISON_ID,
        "workspace_id": "00000000-0000-0000-0000-00000000000a",
        "name": "New prompt",
        "session_replay_dataset_id": "00000000-0000-0000-0000-0000000000d1",
        "dataset_name": "Regression set",
        "metric_group_id": METRIC_GROUP_ID,
        "metric_group_name": "Weekly",
        "sessions_per_test_case": 1,
        "replay_mode": "LIVE",
        "status": "ENDED",
        "candidate": comparison_side(),
        "baseline": comparison_side(recorded=True, pipeline_version_id=None, status="FAILED", error="No Sessions"),
        "created_by_user_id": None,
        "created_at": "2026-10-01T00:00:00Z",
    }


def experiment_results(test_cases: int) -> dict[str, Any]:
    """An Experiment's results as `GET .../evaluation/experiments/{id}/results` returns them."""
    side = {"value": 0.5, "labels": None, "sessions": test_cases, "errored": 0}
    return {
        "comparison_id": COMPARISON_ID,
        "status": "SCORING",
        "metrics": [
            {
                "evaluator_id": E1,
                "evaluator_version_ids": [V1],
                "metric_key": "accuracy",
                "shape": "score",
                "candidate": side,
                "baseline": side,
                "delta": 0.0,
                "delta_pct": 0.0,
                "paired_test_cases": test_cases,
            }
        ],
        "test_cases": [
            {
                "session_replay_test_case_id": f"00000000-0000-0000-0000-{i:012d}",
                "name": f"Case {i}",
                "candidate_session_ids": [SESSION_A],
                "baseline_session_ids": [SESSION_B],
                "values": {f"{E1}:accuracy": {"candidate": 0.5, "baseline": 0.5}},
            }
            for i in range(test_cases)
        ],
    }


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
                                {"metric_key": "answered", "address": "turn/1", "kind": "label", "label": "yes"},
                                {
                                    "metric_key": "answered",
                                    "address": "turn/2",
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
                                    "address": "turn/1",
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


SUITE_ID = "dddddddd-1111-2222-3333-555555555555"
IMPORTED_SESSION_ID = "eeeeeeee-1111-2222-3333-555555555555"
IMPORTED_QUERY_ID = "ffffffff-1111-2222-3333-555555555555"
IMPORTED_SPAN_ID = "abababab-1111-2222-3333-555555555555"


def suite_dict() -> dict[str, Any]:
    return {
        "session_replay_suite_id": SUITE_ID,
        "pipeline_version_id": "88888888-8888-8888-8888-888888888888",
        "test_case_count": 1,
        "repetitions": 2,
        "status": "ENDED",
        "run_counts": {"ended": 1, "failed": 1},
        "experiment": {"pipeline_experiment_id": METRIC_GROUP_ID, "source_experiment_run_id": RUN_ID},
        "created_at": "2026-10-07T00:00:00Z",
        "test_cases": [
            {
                "session_replay_test_case_id": "cccccccc-1111-2222-3333-444444444444",
                "name": "Order status",
                "runs": [
                    {
                        "session_replay_run_id": "77777777-7777-7777-7777-777777777777",
                        "status": "FAILED",
                        "repetition": 2,
                    }
                ],
            }
        ],
    }


def imported_turn_dict() -> dict[str, Any]:
    return {
        "query_id": IMPORTED_QUERY_ID,
        "query": "who wrote Dune?",
        "duration_s": 1.5,
        "created_at": "2026-10-07T00:00:00Z",
        "haystack_trace": {
            "schema_version": "haystack-trace/v1",
            "run_id": RUN_ID,
            "started_at": "2026-10-07T00:00:00Z",
            "traces": [
                {
                    "span_id": IMPORTED_SPAN_ID,
                    "operation_name": "haystack.component.run",
                    "start_time": "2026-10-07T00:00:00Z",
                    "tags": {"haystack.component.type": "Retriever"},
                }
            ],
        },
    }


class FakeEvaluationResource(EvaluationResourceProtocol):
    """Answers reads with fixtures, and each check poll with the next state in line, then the last."""

    def __init__(
        self,
        error: Exception | None = None,
        try_states: list[TryState] | None = None,
        replay_states: list[SessionReplayRun] | None = None,
        results: dict[str, Any] | None = None,
        weights: list[dict[str, Any]] | None = None,
        run_grid: ExperimentRunGrid | None = None,
        evaluation_run_states: list[EvaluationRun] | None = None,
    ) -> None:
        self.evaluation_run_states = evaluation_run_states or []
        self.error = error
        self.weights = weights or []
        self.run_grid = run_grid
        self.results = results
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.try_states = try_states or []
        self.replay_states = replay_states or []

    def _record(self, name: str, /, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))
        if self.error is not None:
            raise self.error

    async def list_evaluators(self, limit: int = 200, archived: bool | None = None) -> list[Evaluator]:
        self._record("list_evaluators", limit=limit, archived=archived)
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

    async def list_metric_groups(self, limit: int = 200) -> list[MetricGroup]:
        self._record("list_metric_groups", limit=limit)
        return [
            MetricGroup.model_validate(
                {
                    "metric_group_id": metric_group_id,
                    "workspace_id": "00000000-0000-0000-0000-00000000000a",
                    "name": name,
                    "evaluator_ids": [E1],
                    "weights": self.weights,
                    "created_at": "2026-10-01T00:00:00Z",
                }
            )
            for metric_group_id, name in [
                (METRIC_GROUP_ID, "Weekly"),
                ("00000000-0000-0000-0000-00000000000e", "Fresh"),
            ]
        ]

    async def list_experiment_runs(
        self, pipeline_name: str, metric_group_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        self._record("list_experiment_runs", metric_group_id=metric_group_id, limit=limit)
        return [run()] if metric_group_id == METRIC_GROUP_ID else []

    async def list_session_experiment_runs(
        self, pipeline_name: str, session_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        self._record("list_session_experiment_runs", session_id=session_id, limit=limit)
        return [run()]

    async def start_experiment_run(
        self,
        pipeline_name: str,
        metric_group_id: str,
        session_ids: list[str] | None = None,
        window: SessionWindow | None = None,
        reuse: str | None = None,
        selection: str | None = None,
        focus: dict[str, list[str]] | None = None,
    ) -> ExperimentRunAccepted:
        self._record(
            "start_experiment_run",
            metric_group_id=metric_group_id,
            session_ids=session_ids,
            window=window,
            reuse=reuse,
            selection=selection,
            focus=focus,
        )
        return ExperimentRunAccepted(pipeline_experiment_run_id=RUN_ID, cells=4)

    async def preview_experiment_run(
        self, pipeline_name: str, metric_group_id: str, window: SessionWindow
    ) -> ExperimentRunPreview:
        self._record("preview_experiment_run", metric_group_id=metric_group_id, window=window)
        return ExperimentRunPreview.model_validate(
            {
                "sessions": 12,
                "more_than": False,
                "evaluators": 3,
                "cells": 36,
                "ceiling": {"sessions": 50, "cells": 200},
            }
        )

    async def run_evaluator(self, pipeline_name: str, evaluator_version_id: str, session_id: str) -> str:
        self._record("run_evaluator", evaluator_version_id=evaluator_version_id, session_id=session_id)
        return EVALUATION_RUN_ID

    async def list_evaluation_runs(self, pipeline_name: str, limit: int = 50) -> list[EvaluationRun]:
        self._record("list_evaluation_runs", limit=limit)
        return [evaluation_run()]

    async def get_evaluation_run(self, pipeline_name: str, evaluation_run_id: str) -> EvaluationRun:
        self._record("get_evaluation_run", evaluation_run_id=evaluation_run_id)
        if len(self.evaluation_run_states) > 1:
            return self.evaluation_run_states.pop(0)
        return self.evaluation_run_states[0] if self.evaluation_run_states else evaluation_run()

    async def get_experiment_run(
        self,
        pipeline_name: str,
        metric_group_id: str,
        run_id: str,
        origin: str | None = None,
        deployment_id: str | None = None,
        pipeline_version_id: str | None = None,
        session_id: str | None = None,
    ) -> ExperimentRunGrid:
        self._record(
            "get_experiment_run",
            metric_group_id=metric_group_id,
            run_id=run_id,
            origin=origin,
            deployment_id=deployment_id,
            pipeline_version_id=pipeline_version_id,
            session_id=session_id,
        )
        return self.run_grid or grid()

    async def list_experiments(self, pipeline_name: str | None = None, limit: int = 50) -> list[Experiment]:
        self._record("list_experiments", pipeline_name=pipeline_name, limit=limit)
        return [Experiment.model_validate(comparison())]

    async def create_experiment(
        self,
        name: str,
        dataset_id: str,
        metric_group_id: str,
        candidate_pipeline_name: str,
        candidate_pipeline_version_id: str,
        baseline_pipeline_name: str | None = None,
        baseline_pipeline_version_id: str | None = None,
        sessions_per_test_case: int = 1,
        replay_mode: str = "FIRST_USER_MESSAGE",
        reuse_sessions: bool = True,
    ) -> Experiment:
        self._record(
            "create_experiment",
            body={
                "name": name,
                "dataset_id": dataset_id,
                "metric_group_id": metric_group_id,
                "candidate_pipeline_name": candidate_pipeline_name,
                "candidate_pipeline_version_id": candidate_pipeline_version_id,
                "baseline_pipeline_name": baseline_pipeline_name,
                "baseline_pipeline_version_id": baseline_pipeline_version_id,
                "sessions_per_test_case": sessions_per_test_case,
                "replay_mode": replay_mode,
                "reuse_sessions": reuse_sessions,
            },
        )
        return Experiment.model_validate(comparison())

    async def get_experiment_results(self, experiment_id: str) -> ExperimentResults:
        self._record("get_experiment_results", experiment_id=experiment_id)
        return ExperimentResults.model_validate(self.results or experiment_results(test_cases=3))

    async def list_sessions(
        self,
        pipeline_name: str,
        origin: str | None = None,
        deployment_id: str | None = None,
        pipeline_version_id: str | None = None,
        revision_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionList:
        self._record("list_sessions", origin=origin, revision_id=revision_id, since=since, limit=limit, cursor=cursor)
        return SessionList.model_validate({"data": [], "next": None})

    async def start_try(self, pipeline_name: str, python_code: str, session_id: str) -> str:
        self._record("start_try", python_code=python_code, session_id=session_id)
        return TRY_ID

    async def get_try(self, pipeline_name: str, try_id: str) -> TryState:
        self._record("get_try", try_id=try_id)
        return self.try_states.pop(0) if len(self.try_states) > 1 else self.try_states[0]

    async def start_session_replay(
        self, pipeline_name: str, session_id: str, pipeline_version_id: str, replay_mode: str | None = None
    ) -> str:
        self._record(
            "start_session_replay",
            session_id=session_id,
            pipeline_version_id=pipeline_version_id,
            replay_mode=replay_mode,
        )
        return REPLAY_RUN_ID

    async def get_session_replay(self, pipeline_name: str, replay_run_id: str) -> SessionReplayRun:
        self._record("get_session_replay", replay_run_id=replay_run_id)
        return self.replay_states.pop(0) if len(self.replay_states) > 1 else self.replay_states[0]

    async def list_session_replays(self, pipeline_name: str, limit: int = 50) -> list[SessionReplayRun]:
        self._record("list_session_replays", pipeline_name=pipeline_name, limit=limit)
        return [replay_run("ENDED")]

    async def start_replay_suite(
        self,
        pipeline_name: str,
        dataset_id: str,
        pipeline_version_id: str,
        repetitions: int = 1,
        replay_mode: str = "FIRST_USER_MESSAGE",
        metric_group_id: str | None = None,
        reuse: str | None = None,
    ) -> ReplaySuiteAccepted:
        self._record(
            "start_replay_suite",
            dataset_id=dataset_id,
            pipeline_version_id=pipeline_version_id,
            repetitions=repetitions,
            replay_mode=replay_mode,
            metric_group_id=metric_group_id,
            reuse=reuse,
        )
        return ReplaySuiteAccepted.model_validate({"session_replay_suite_id": SUITE_ID, "run_count": 6})

    async def list_replay_suites(self, pipeline_name: str, limit: int = 50) -> list[ReplaySuiteSummary]:
        self._record("list_replay_suites", pipeline_name=pipeline_name, limit=limit)
        return [ReplaySuiteSummary.model_validate(suite_dict())]

    async def get_replay_suite(self, pipeline_name: str, suite_id: str) -> ReplaySuite:
        self._record("get_replay_suite", suite_id=suite_id)
        return ReplaySuite.model_validate(suite_dict())

    async def list_imported_session_traces(self, session_id: str) -> list[PipelineTraceEntry]:
        self._record("list_imported_session_traces", session_id=session_id)
        return [PipelineTraceEntry.model_validate(imported_turn_dict())]

    async def get_imported_session_trace(self, session_id: str, query_id: str) -> PipelineTraceEntry:
        self._record("get_imported_session_trace", session_id=session_id, query_id=query_id)
        return PipelineTraceEntry.model_validate(imported_turn_dict())

    async def get_imported_session_trace_span_tags(
        self, session_id: str, query_id: str, span_id: str
    ) -> dict[str, Any]:
        self._record("get_imported_session_trace_span_tags", session_id=session_id, query_id=query_id, span_id=span_id)
        return {"haystack.component.input": {"query": "x"}}

    async def list_datasets(self, pipeline_name: str | None = None, limit: int = 50) -> list[DatasetSummary]:
        self._record("list_datasets", pipeline_name=pipeline_name, limit=limit)
        return [DatasetSummary.model_validate({k: v for k, v in dataset_dict().items() if k != "test_cases"})]

    async def get_dataset(self, dataset_id: str) -> Dataset:
        self._record("get_dataset", dataset_id=dataset_id)
        return Dataset.model_validate(dataset_dict())

    async def create_dataset(
        self, name: str, pipeline_name: str | None = None, test_cases: list[NewTestCase] | None = None
    ) -> Dataset:
        self._record("create_dataset", dataset_name=name, pipeline_name=pipeline_name, test_cases=test_cases)
        return Dataset.model_validate(dataset_dict())

    async def update_dataset(self, dataset_id: str, name: str) -> Dataset:
        self._record("update_dataset", dataset_id=dataset_id, dataset_name=name)
        return Dataset.model_validate(dataset_dict())

    async def delete_dataset(self, dataset_id: str) -> None:
        self._record("delete_dataset", dataset_id=dataset_id)

    async def add_test_cases(
        self, dataset_id: str, test_cases: list[NewTestCase], pipeline_name: str | None = None
    ) -> Dataset:
        self._record("add_test_cases", dataset_id=dataset_id, test_cases=test_cases, pipeline_name=pipeline_name)
        return Dataset.model_validate(dataset_dict())

    async def copy_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        self._record("copy_test_cases", dataset_id=dataset_id, test_case_ids=test_case_ids)
        return Dataset.model_validate(dataset_dict())

    async def remove_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        self._record("remove_test_cases", dataset_id=dataset_id, test_case_ids=test_case_ids)
        return Dataset.model_validate(dataset_dict())

    async def update_test_case(self, dataset_id: str, test_case_id: str, changes: dict[str, Any]) -> TestCase:
        self._record("update_test_case", dataset_id=dataset_id, test_case_id=test_case_id, changes=changes)
        return TestCase.model_validate(dataset_dict()["test_cases"][0])

    @staticmethod
    def _evaluator(evaluator_id: str) -> Evaluator:
        return Evaluator(evaluator_id=evaluator_id, name="Answered", created_at="2026-10-01T00:00:00Z")

    async def create_evaluator(
        self,
        name: str,
        python_code: str,
        metric_group_ids: list[str] | None = None,
        new_metric_group_name: str | None = None,
    ) -> Evaluator:
        self._record(
            "create_evaluator",
            evaluator_name=name,
            python_code=python_code,
            metric_group_ids=metric_group_ids,
            new_metric_group_name=new_metric_group_name,
        )
        return self._evaluator(E1)

    async def update_evaluator(
        self, evaluator_id: str, name: str | None = None, python_code: str | None = None
    ) -> Evaluator:
        self._record("update_evaluator", evaluator_id=evaluator_id, evaluator_name=name, python_code=python_code)
        return self._evaluator(evaluator_id)

    async def set_evaluator_archived(self, evaluator_id: str, archived: bool) -> Evaluator:
        self._record("set_evaluator_archived", evaluator_id=evaluator_id, archived=archived)
        return self._evaluator(evaluator_id)

    async def list_evaluator_templates(self) -> list[EvaluatorTemplate]:
        self._record("list_evaluator_templates")
        return [EvaluatorTemplate(key="tool_calls", name="Tool calls", python_code="def evaluate(): ...")]

    async def combine_evaluator_templates(self, template_keys: list[str], title: str) -> CombinedEvaluatorTemplates:
        self._record("combine_evaluator_templates", template_keys=template_keys, title=title)
        return CombinedEvaluatorTemplates(python_code="merged")

    def _metric_group(self) -> MetricGroup:
        return MetricGroup(
            metric_group_id=METRIC_GROUP_ID, name="Weekly", evaluator_ids=[E1], created_at="2026-10-01T00:00:00Z"
        )

    async def create_metric_group(
        self, name: str, evaluator_ids: list[str], weights: list[MetricWeight] | None = None
    ) -> MetricGroup:
        self._record("create_metric_group", group_name=name, evaluator_ids=evaluator_ids, weights=weights)
        return self._metric_group()

    async def update_metric_group(
        self, metric_group_id: str, name: str, evaluator_ids: list[str], weights: list[MetricWeight] | None = None
    ) -> MetricGroup:
        self._record(
            "update_metric_group",
            metric_group_id=metric_group_id,
            group_name=name,
            evaluator_ids=evaluator_ids,
            weights=weights,
        )
        return self._metric_group()

    async def delete_metric_group(self, metric_group_id: str) -> None:
        self._record("delete_metric_group", metric_group_id=metric_group_id)

    async def preview_experiment(
        self,
        dataset_id: str,
        metric_group_id: str,
        candidate_pipeline_name: str,
        candidate_pipeline_version_id: str,
        baseline_pipeline_name: str | None = None,
        baseline_pipeline_version_id: str | None = None,
        sessions_per_test_case: int = 1,
        replay_mode: str = "FIRST_USER_MESSAGE",
        reuse_sessions: bool = True,
    ) -> ExperimentPlan:
        self._record(
            "preview_experiment",
            dataset_id=dataset_id,
            sessions_per_test_case=sessions_per_test_case,
            reuse_sessions=reuse_sessions,
        )
        return ExperimentPlan.model_validate({"candidate": SIDE_PLAN, "baseline": SIDE_PLAN, "cells": 6})

    async def get_experiment(self, experiment_id: str) -> ExperimentDetail:
        self._record("get_experiment", experiment_id=experiment_id)
        return ExperimentDetail.model_validate(
            {
                **comparison(),
                "test_cases": [{"session_replay_test_case_id": E2, "name": "Order status"}],
                "candidate": comparison_side(run_counts={"created": 0, "started": 0, "ended": 1, "failed": 1}),
            }
        )

    async def update_experiment(
        self,
        experiment_id: str,
        name: str | None = None,
        candidate_pipeline_name: str | None = None,
        candidate_pipeline_version_id: str | None = None,
        baseline_pipeline_name: str | None = None,
        baseline_pipeline_version_id: str | None = None,
        recorded_baseline: bool = False,
    ) -> Experiment:
        self._record("update_experiment", experiment_id=experiment_id, name=name, recorded_baseline=recorded_baseline)
        return Experiment.model_validate(comparison())

    async def preview_update_experiment(
        self,
        experiment_id: str,
        name: str | None = None,
        candidate_pipeline_name: str | None = None,
        candidate_pipeline_version_id: str | None = None,
        baseline_pipeline_name: str | None = None,
        baseline_pipeline_version_id: str | None = None,
        recorded_baseline: bool = False,
    ) -> ExperimentUpdatePlan:
        self._record("preview_update_experiment", experiment_id=experiment_id, name=name)
        return ExperimentUpdatePlan.model_validate({"candidate": SIDE_PLAN, "baseline": None})

    async def rerun_failed_experiment(self, experiment_id: str, replays: bool = False) -> Experiment:
        self._record("rerun_failed_experiment", experiment_id=experiment_id, replays=replays)
        return Experiment.model_validate(comparison())

    async def rescore_experiment(self, experiment_id: str) -> Experiment:
        self._record("rescore_experiment", experiment_id=experiment_id)
        return Experiment.model_validate(comparison())

    async def delete_experiment(self, experiment_id: str) -> None:
        self._record("delete_experiment", experiment_id=experiment_id)


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
        metric_group_id=METRIC_GROUP_ID,
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
        metric_group_id=METRIC_GROUP_ID,
        run_id=RUN_ID,
        max_rows=1,
    )

    assert isinstance(report, ExperimentRunReport)
    assert (report.total_rows, report.rows_truncated, len(report.rows)) == (2, True, 1)
    judged, broken = report.rows[0].cells
    assert (judged.evaluator_id, judged.outcome, judged.evaluator_version_id) == (E1, "SUCCEEDED", V1)
    assert judged.metrics[2].rationale == "The reply asks the question back."
    assert broken.outcome == "ERRORED"
    assert broken.error_detail == {"type": "KeyError", "message": "'replies'", "stacktrace": []}


@pytest.mark.asyncio
async def test_list_metric_groups_attaches_each_last_run_on_the_given_pipeline() -> None:
    resource = FakeEvaluationResource()

    groups = await list_metric_groups(client=FakeClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE)

    assert isinstance(groups, list)
    assert [(g.name, g.last_run is not None) for g in groups] == [("Weekly", True), ("Fresh", False)]
    assert {c[1]["limit"] for c in resource.calls if c[0] == "list_experiment_runs"} == {1}


@pytest.mark.asyncio
async def test_list_metric_groups_reads_no_runs_without_a_pipeline() -> None:
    resource = FakeEvaluationResource()

    groups = await list_metric_groups(client=FakeClient(resource), workspace=WORKSPACE)

    assert isinstance(groups, list)
    assert [g.last_run for g in groups] == [None, None]
    assert [c[0] for c in resource.calls] == ["list_metric_groups"]


@pytest.mark.asyncio
async def test_list_experiments_passes_the_pipeline_and_drops_each_sides_sessions() -> None:
    resource = FakeEvaluationResource()

    experiments = await list_experiments(client=FakeClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE)

    assert isinstance(experiments, list)
    [experiment] = experiments
    assert resource.calls == [("list_experiments", {"pipeline_name": PIPELINE, "limit": 50})]
    dumped = experiment.model_dump()
    assert dumped["experiment_id"] == COMPARISON_ID
    assert dumped["dataset_name"] == "Regression set"
    assert dumped["candidate"]["scoring_runs"] == [{"pipeline_id": PIPELINE_ID, "experiment_run_id": RUN_ID}]
    assert dumped["baseline"]["error"] == "No Sessions"
    assert "sessions" not in dumped["candidate"]


@pytest.mark.asyncio
async def test_create_experiment_refuses_partial_baseline_without_calling_the_resource() -> None:
    resource = FakeEvaluationResource()

    result = await create_experiment(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        name="Partial",
        dataset_id="d-1",
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE,
        candidate_pipeline_version_id=V1,
        baseline_pipeline_name=PIPELINE,
    )

    assert isinstance(result, str)
    assert "baseline_pipeline_version_id" in result
    assert resource.calls == []


@pytest.mark.asyncio
async def test_create_experiment_forwards_the_recorded_baseline_as_no_baseline() -> None:
    resource = FakeEvaluationResource()

    experiment = await create_experiment(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        name="Recorded",
        dataset_id="d-1",
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE,
        candidate_pipeline_version_id=V1,
    )

    assert isinstance(experiment, Experiment)
    [(call, kwargs)] = resource.calls
    assert call == "create_experiment"
    body = kwargs["body"]
    assert body["baseline_pipeline_name"] is None
    assert body["baseline_pipeline_version_id"] is None
    assert body["replay_mode"] == "FIRST_USER_MESSAGE"
    assert body["sessions_per_test_case"] == 1


@pytest.mark.asyncio
async def test_get_experiment_results_caps_the_test_cases_but_not_the_metrics() -> None:
    resource = FakeEvaluationResource()

    results = await get_experiment_results(
        client=FakeClient(resource), workspace=WORKSPACE, experiment_id=COMPARISON_ID, max_test_cases=2
    )

    assert isinstance(results, ExperimentResultsReport)
    assert resource.calls == [("get_experiment_results", {"experiment_id": COMPARISON_ID})]
    assert results.experiment_id == COMPARISON_ID
    assert results.metrics[0].paired_test_cases == 3
    assert [case.name for case in results.test_cases] == ["Case 0", "Case 1"]
    assert results.total_test_cases == 3
    assert results.test_cases_truncated


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
        {"origin": "SERVICE", "revision_id": None, "since": "2026-09-28T00:00:00Z", "limit": 50, "cursor": None},
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
        await list_metric_groups(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE),
        await list_experiments(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE),
        await get_experiment_results(client=client, workspace=WORKSPACE, experiment_id=COMPARISON_ID),
        await get_experiment_run(
            client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, metric_group_id=METRIC_GROUP_ID, run_id=RUN_ID
        ),
        await list_sessions(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE),
    ]

    for result in results:
        assert isinstance(result, str)
        assert expected in result


# ---------------------------------------------------------------------------------------------
# Checks: the try and session replay
# ---------------------------------------------------------------------------------------------

TRY_ID = "signed-try-id"
REPLAY_RUN_ID = "77777777-7777-7777-7777-777777777777"
DRAFT_VERSION_ID = "88888888-8888-8888-8888-888888888888"
REPLAYED_QUERY_ID = "99999999-9999-9999-9999-999999999990"
REPLAYED_SESSION_ID = "99999999-9999-9999-9999-999999999991"


def try_result(**overrides: Any) -> EvaluationTryResult:
    return EvaluationTryResult.model_validate(
        {
            "session_id": SESSION_A,
            "outcome": "SUCCEEDED",
            "metrics": [{"metric_key": "answered", "address": "turn/1", "kind": "label", "label": "yes"}],
            "trace_ids": [SESSION_A],
            "trace": {
                "status": "success",
                "traces": [
                    {"operation_name": "haystack.tool.invoke", "tags": {"haystack.tool.name": "get_turn"}},
                    {"operation_name": "haystack.component.run", "tags": {}},
                    {"operation_name": "haystack.tool.invoke", "tags": {"haystack.tool.name": "report_metric"}},
                ],
            },
            **overrides,
        }
    )


def replay_run(status: str, trace_ids: list[str] | None = None) -> SessionReplayRun:
    return SessionReplayRun.model_validate(
        {
            "session_replay_run_id": REPLAY_RUN_ID,
            "pipeline_version_id": DRAFT_VERSION_ID,
            "status": status,
            "source_session_id": SESSION_A,
            "trace_ids": trace_ids if trace_ids is not None else [],
        }
    )


class FakeTraces:
    def __init__(self, search_session_id: str | None) -> None:
        self.search_session_id = search_session_id
        self.filters: list[str | None] = []

    async def list_pipeline_traces(
        self, pipeline_name: str, limit: int = 10, query_filter: str | None = None, **_: Any
    ) -> Any:
        self.filters.append(query_filter)
        row = {
            "query_id": REPLAYED_QUERY_ID,
            "query": "who wrote Dune?",
            "duration_s": 1.0,
            "created_at": "2026-10-07T00:00:00Z",
            "search_session_id": self.search_session_id,
        }
        return PaginatedResponse[PipelineTraceSummary](data=[PipelineTraceSummary.model_validate(row)], has_more=False)


class FakeCheckClient(FakeClient):
    def __init__(self, evaluation_resource: FakeEvaluationResource, traces: FakeTraces | None = None) -> None:
        super().__init__(evaluation_resource)
        self.traces = traces or FakeTraces(REPLAYED_SESSION_ID)

    def search_history(self, workspace: str) -> FakeTraces:  # type: ignore[override]
        return self.traces


@pytest.fixture(autouse=True)
def no_poll_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluation_tools, "POLL_INTERVAL_SECONDS", 0)


@pytest.mark.asyncio
async def test_try_evaluator_polls_until_ready_and_keeps_only_a_summary_of_the_judge_trace() -> None:
    resource = FakeEvaluationResource(
        try_states=[TryState(status="RUNNING"), TryState(status="READY", result=try_result())]
    )

    report = await try_evaluator(
        client=FakeCheckClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        python_code="def evaluate(session, focus): ...",
        session_id=SESSION_A,
    )

    assert isinstance(report, TryReport)
    assert (report.status, report.try_id, report.outcome) == ("READY", TRY_ID, "SUCCEEDED")
    assert report.metrics[0].label == "yes"
    assert report.trace_summary is not None
    assert report.trace_summary.tool_calls == ["get_turn", "report_metric"]
    assert report.trace_summary.failed is False
    assert "trace" not in report.model_dump()
    assert [c[0] for c in resource.calls] == ["start_try", "get_try", "get_try"]


@pytest.mark.asyncio
async def test_try_evaluator_hands_back_the_id_when_the_wait_runs_out() -> None:
    resource = FakeEvaluationResource(try_states=[TryState(status="RUNNING")])

    report = await try_evaluator(
        client=FakeCheckClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        python_code="def evaluate(session, focus): ...",
        session_id=SESSION_A,
        wait_seconds=0,
    )

    assert isinstance(report, TryReport)
    assert (report.status, report.try_id, report.metrics) == ("RUNNING", TRY_ID, [])


@pytest.mark.asyncio
async def test_get_evaluation_try_says_an_expired_try_must_run_again() -> None:
    resource = FakeEvaluationResource(try_states=[TryState(status="EXPIRED")])

    report = await get_evaluation_try(
        client=FakeCheckClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE, try_id=TRY_ID
    )

    assert isinstance(report, TryReport)
    assert report.status == "EXPIRED"


@pytest.mark.asyncio
async def test_replay_session_polls_until_ended_and_names_the_replayed_session() -> None:
    traces = FakeTraces(REPLAYED_SESSION_ID)
    resource = FakeEvaluationResource(
        replay_states=[replay_run("STARTED"), replay_run("ENDED", trace_ids=[REPLAYED_QUERY_ID])]
    )

    report = await replay_session(
        client=FakeCheckClient(resource, traces),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        session_id=SESSION_A,
        pipeline_version_id=DRAFT_VERSION_ID,
        replay_mode="ALL_USER_MESSAGES",
    )

    assert isinstance(report, SessionReplayReport)
    assert (report.status, report.replay_run_id) == ("ENDED", REPLAY_RUN_ID)
    assert (report.source_session_id, report.replayed_session_id) == (SESSION_A, REPLAYED_SESSION_ID)
    assert traces.filters == [f"query_id eq '{REPLAYED_QUERY_ID}'"]
    assert resource.calls[0] == (
        "start_session_replay",
        {"session_id": SESSION_A, "pipeline_version_id": DRAFT_VERSION_ID, "replay_mode": "ALL_USER_MESSAGES"},
    )


@pytest.mark.asyncio
async def test_a_replay_without_a_search_session_is_named_by_its_query_id() -> None:
    resource = FakeEvaluationResource(replay_states=[replay_run("ENDED", trace_ids=[REPLAYED_QUERY_ID])])

    report = await get_session_replay(
        client=FakeCheckClient(resource, FakeTraces(None)),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        replay_run_id=REPLAY_RUN_ID,
    )

    assert isinstance(report, SessionReplayReport)
    assert report.replayed_session_id == REPLAYED_QUERY_ID


@pytest.mark.asyncio
async def test_a_failed_replay_names_no_session() -> None:
    resource = FakeEvaluationResource(replay_states=[replay_run("FAILED")])

    report = await replay_session(
        client=FakeCheckClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        session_id=SESSION_A,
        pipeline_version_id=DRAFT_VERSION_ID,
    )

    assert isinstance(report, SessionReplayReport)
    assert (report.status, report.replayed_session_id) == ("FAILED", None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ResourceNotFoundError(), "not found"),
        (BadRequestError(message="bad"), "Failed"),
        (UnexpectedAPIError(status_code=503, message="queue down"), "Failed"),
    ],
)
async def test_check_errors_come_back_as_readable_strings(error: Exception, expected: str) -> None:
    client = FakeCheckClient(FakeEvaluationResource(error=error))

    results = [
        await try_evaluator(
            client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, python_code="x", session_id=SESSION_A
        ),
        await get_evaluation_try(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, try_id=TRY_ID),
        await replay_session(
            client=client,
            workspace=WORKSPACE,
            pipeline_name=PIPELINE,
            session_id=SESSION_A,
            pipeline_version_id=DRAFT_VERSION_ID,
        ),
        await get_session_replay(
            client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, replay_run_id=REPLAY_RUN_ID
        ),
    ]

    for result in results:
        assert isinstance(result, str)
        assert expected in result


def test_a_metric_declaration_carries_better_and_range_and_defaults_both_to_none() -> None:
    declared = MetricDeclaration.model_validate(
        {"shape": "score", "grain": "session", "better": "lower", "range": [1, 5]}
    )
    older = MetricDeclaration.model_validate({"shape": "score", "grain": "session"})

    assert (declared.better, declared.range) == ("lower", [1.0, 5.0])
    assert (older.better, older.range) == (None, None)


def test_a_label_declaration_carries_its_scale_as_floats_and_defaults_to_none() -> None:
    scaled = MetricDeclaration.model_validate(
        {
            "shape": "label",
            "grain": "session",
            "vocabulary": ["wrong", "partial", "correct"],
            "scale": {"wrong": 0, "partial": 0.5, "correct": 1},
        }
    )
    unscaled = MetricDeclaration.model_validate({"shape": "label", "grain": "session", "vocabulary": ["a", "b"]})

    assert scaled.scale == {"wrong": 0.0, "partial": 0.5, "correct": 1.0}
    assert unscaled.scale is None


def _results_with(metric_extras: list[dict[str, Any]], pipeline_extras: list[dict[str, Any]]) -> dict[str, Any]:
    payload = experiment_results(test_cases=1)
    base = payload["metrics"][0]
    payload["metrics"] = [{**base, "metric_key": f"m{i}", **extra} for i, extra in enumerate(metric_extras)]
    side = base["candidate"]
    payload["pipeline_metrics"] = [
        {
            "key": key,
            "candidate": side,
            "baseline": side,
            "delta": 0.0,
            "delta_pct": 0.0,
            "paired_test_cases": 1,
            **extra,
        }
        for key, extra in zip(["DURATION", "COST"], pipeline_extras, strict=True)
    ]
    return payload


@pytest.mark.asyncio
async def test_get_experiment_results_reports_better_and_change_per_metric() -> None:
    payload = _results_with(
        [
            {"better": "higher", "change": "improved"},
            {"better": "lower", "change": "regressed"},
            {"better": None, "change": "unknown"},
        ],
        [{"better": "lower", "change": "improved"}, {"better": "lower", "change": "regressed"}],
    )

    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource(results=payload)), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert [(m.better, m.change) for m in results.metrics] == [
        ("higher", "improved"),
        ("lower", "regressed"),
        (None, "unknown"),
    ]
    assert [(m.better, m.change) for m in results.pipeline_metrics] == [("lower", "improved"), ("lower", "regressed")]


@pytest.mark.asyncio
async def test_get_experiment_results_from_an_older_api_reads_every_change_as_unknown() -> None:
    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource()), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert [(m.better, m.change) for m in results.metrics] == [(None, "unknown")]


WEIGHT = {"evaluator_id": E1, "metric_key": "accuracy", "weight": 2.0}


def test_a_metric_group_carries_its_weights_and_defaults_to_none() -> None:
    base = {
        "metric_group_id": METRIC_GROUP_ID,
        "name": "W",
        "evaluator_ids": [E1],
        "created_at": "2026-10-01T00:00:00Z",
    }
    weighted = MetricGroup.model_validate(
        {
            **base,
            "weights": [
                {**WEIGHT, "usable": True},
                {**WEIGHT, "metric_key": "gone", "usable": False, "unusable_reason": "no longer declared"},
            ],
        }
    )
    older = MetricGroup.model_validate(base)

    assert [(w.metric_key, w.weight, w.usable, w.unusable_reason) for w in weighted.weights] == [
        ("accuracy", 2.0, True, None),
        ("gone", 2.0, False, "no longer declared"),
    ]
    assert older.weights == []


@pytest.mark.asyncio
async def test_list_metric_groups_keeps_each_groups_weights() -> None:
    groups = await list_metric_groups(
        client=FakeClient(FakeEvaluationResource(weights=[{**WEIGHT, "usable": True}])), workspace=WORKSPACE
    )

    assert isinstance(groups, list)
    assert [len(g.weights) for g in groups] == [1, 1]


def _grid_with(**extra: Any) -> ExperimentRunGrid:
    payload = grid().model_dump()
    payload["run"] = {**payload["run"], **extra.pop("run", {})}
    return ExperimentRunGrid.model_validate({**payload, **extra})


async def _report(resource_grid: ExperimentRunGrid) -> ExperimentRunReport:
    resource = FakeEvaluationResource(run_grid=resource_grid)
    report = await get_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        run_id=RUN_ID,
    )
    assert isinstance(report, ExperimentRunReport)
    return report


@pytest.mark.asyncio
async def test_get_experiment_run_reports_the_formula_normalized_means_and_composite() -> None:
    report = await _report(
        _grid_with(
            run={"composite_weights": [WEIGHT]},
            normalized_means=[
                {"kind": "value", "evaluator_id": E1, "metric_key": "accuracy", "value": 0.6},
                {"kind": "missing", "evaluator_id": E1, "metric_key": "answered", "reason": "no Scale"},
            ],
            composite={"kind": "value", "value": 0.6, "coverage": 1.0},
        )
    )

    assert [(w.metric_key, w.weight) for w in report.run.composite_weights or []] == [("accuracy", 2.0)]
    assert [type(m) for m in report.normalized_means] == [NormalizedMean, NoNormalizedMean]
    assert report.composite == Composite(value=0.6, coverage=1.0)


@pytest.mark.asyncio
async def test_get_experiment_run_says_why_there_is_no_composite() -> None:
    report = await _report(
        _grid_with(
            composite={
                "kind": "missing",
                "reason": "some weighted Metrics have no Normalized mean",
                "missing": [{"kind": "missing", "evaluator_id": E1, "metric_key": "answered", "reason": "no Scale"}],
            }
        )
    )

    assert isinstance(report.composite, NoComposite)
    assert [(m.metric_key, m.reason) for m in report.composite.missing] == [("answered", "no Scale")]
    assert report.run.composite_weights is None


@pytest.mark.asyncio
async def test_get_experiment_run_from_an_older_api_has_no_composite_fields() -> None:
    report = await _report(grid())

    assert (report.run.composite_weights, report.normalized_means, report.composite) == (None, [], None)


def _side(composite: dict[str, Any]) -> dict[str, Any]:
    return {"normalized_means": [], "composite": composite}


@pytest.mark.asyncio
async def test_get_experiment_results_reports_each_sides_composite_and_why_they_are_incomparable() -> None:
    payload = experiment_results(test_cases=1)
    payload["headline"] = {
        "candidate": _side({"kind": "value", "value": 0.8, "coverage": 1.0}),
        "baseline": _side({"kind": "value", "value": 0.7, "coverage": 0.5}),
        "comparable": False,
        "incomparable_reason": "the runs weighed different Metrics",
    }

    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource(results=payload)), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert results.headline is not None
    assert results.headline.candidate.composite == Composite(value=0.8, coverage=1.0)
    assert (results.headline.comparable, results.headline.incomparable_reason) == (
        False,
        "the runs weighed different Metrics",
    )


@pytest.mark.asyncio
async def test_get_experiment_results_headline_is_comparable_without_a_reason_and_may_lack_a_composite() -> None:
    payload = experiment_results(test_cases=1)
    payload["headline"] = {
        "candidate": _side({"kind": "value", "value": 0.8, "coverage": 1.0}),
        "baseline": _side({"kind": "missing", "reason": "not scored yet"}),
    }

    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource(results=payload)), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert results.headline is not None
    assert (results.headline.comparable, results.headline.incomparable_reason) == (True, None)
    assert results.headline.baseline.composite == NoComposite(reason="not scored yet")


@pytest.mark.asyncio
async def test_get_experiment_results_from_an_older_api_has_no_headline() -> None:
    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource()), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert results.headline is None


@pytest.mark.asyncio
async def test_dataset_reads_return_the_dataset_models() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    listed = await list_datasets(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE)
    dataset = await get_dataset(client=client, workspace=WORKSPACE, dataset_id=DATASET_ID)

    assert isinstance(listed, list)
    assert listed[0].dataset_id == DATASET_ID
    assert isinstance(dataset, Dataset)
    assert dataset.test_cases[0].test_case_id == TEST_CASE_ID
    assert resource.calls == [
        ("list_datasets", {"pipeline_name": PIPELINE, "limit": 50}),
        ("get_dataset", {"dataset_id": DATASET_ID}),
    ]


@pytest.mark.asyncio
async def test_dataset_writes_forward_their_arguments_and_return_the_dataset() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)
    cases = [NewTestCase(session_id=SESSION_A)]

    results = [
        await create_dataset(client=client, workspace=WORKSPACE, name="N", pipeline_name=PIPELINE, test_cases=cases),
        await update_dataset(client=client, workspace=WORKSPACE, dataset_id=DATASET_ID, name="R"),
        await add_test_cases(
            client=client, workspace=WORKSPACE, dataset_id=DATASET_ID, test_cases=cases, pipeline_name=PIPELINE
        ),
        await copy_test_cases(client=client, workspace=WORKSPACE, dataset_id=DATASET_ID, test_case_ids=[TEST_CASE_ID]),
        await remove_test_cases(
            client=client, workspace=WORKSPACE, dataset_id=DATASET_ID, test_case_ids=[TEST_CASE_ID]
        ),
    ]

    assert all(isinstance(result, Dataset) for result in results)
    assert resource.calls == [
        ("create_dataset", {"dataset_name": "N", "pipeline_name": PIPELINE, "test_cases": cases}),
        ("update_dataset", {"dataset_id": DATASET_ID, "dataset_name": "R"}),
        ("add_test_cases", {"dataset_id": DATASET_ID, "test_cases": cases, "pipeline_name": PIPELINE}),
        ("copy_test_cases", {"dataset_id": DATASET_ID, "test_case_ids": [TEST_CASE_ID]}),
        ("remove_test_cases", {"dataset_id": DATASET_ID, "test_case_ids": [TEST_CASE_ID]}),
    ]


@pytest.mark.asyncio
async def test_delete_dataset_confirms_in_a_string() -> None:
    resource = FakeEvaluationResource()

    result = await delete_dataset(client=FakeClient(resource), workspace=WORKSPACE, dataset_id=DATASET_ID)

    assert DATASET_ID in result
    assert resource.calls == [("delete_dataset", {"dataset_id": DATASET_ID})]


@pytest.mark.asyncio
async def test_update_test_case_sends_only_what_changes_and_nulls_what_is_cleared() -> None:
    resource = FakeEvaluationResource()

    result = await update_test_case(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        dataset_id=DATASET_ID,
        test_case_id=TEST_CASE_ID,
        name="New",
        expected={"answer": "Paris"},
        clear=["setup_source"],
    )

    assert isinstance(result, TestCase)
    [(_, kwargs)] = resource.calls
    assert kwargs["changes"] == {"name": "New", "expected": {"answer": "Paris"}, "setup_source": None}


@pytest.mark.asyncio
async def test_update_test_case_without_a_change_does_not_call_the_api() -> None:
    resource = FakeEvaluationResource()

    result = await update_test_case(
        client=FakeClient(resource), workspace=WORKSPACE, dataset_id=DATASET_ID, test_case_id=TEST_CASE_ID
    )

    assert isinstance(result, str)
    assert resource.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        ResourceNotFoundError(message="Dataset not found"),
        BadRequestError(message="bad"),
        UnexpectedAPIError(status_code=422, message="Dataset over its size limit"),
    ],
)
async def test_dataset_tools_return_the_api_message_instead_of_raising(error: Exception) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))
    common: dict[str, Any] = {"client": client, "workspace": WORKSPACE}
    cases = [NewTestCase(inputs={"query": "hi"})]

    results = [
        await list_datasets(**common),
        await get_dataset(**common, dataset_id=DATASET_ID),
        await create_dataset(**common, name="N"),
        await update_dataset(**common, dataset_id=DATASET_ID, name="R"),
        await delete_dataset(**common, dataset_id=DATASET_ID),
        await add_test_cases(**common, dataset_id=DATASET_ID, test_cases=cases),
        await copy_test_cases(**common, dataset_id=DATASET_ID, test_case_ids=[TEST_CASE_ID]),
        await remove_test_cases(**common, dataset_id=DATASET_ID, test_case_ids=[TEST_CASE_ID]),
        await update_test_case(**common, dataset_id=DATASET_ID, test_case_id=TEST_CASE_ID, name="x"),
    ]

    assert all(isinstance(result, str) and str(error.args[0]) in result for result in results)


@pytest.mark.asyncio
async def test_evaluator_writes_forward_their_arguments_and_return_the_evaluator() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    results = [
        await create_evaluator(
            client=client,
            workspace=WORKSPACE,
            name="N",
            python_code="code",
            metric_group_ids=[METRIC_GROUP_ID],
            new_metric_group_name="G",
        ),
        await update_evaluator(client=client, workspace=WORKSPACE, evaluator_id=E1, python_code="new"),
        await set_evaluator_archived(client=client, workspace=WORKSPACE, evaluator_id=E1, archived=True),
    ]

    assert all(isinstance(result, Evaluator) for result in results)
    assert resource.calls == [
        (
            "create_evaluator",
            {
                "evaluator_name": "N",
                "python_code": "code",
                "metric_group_ids": [METRIC_GROUP_ID],
                "new_metric_group_name": "G",
            },
        ),
        ("update_evaluator", {"evaluator_id": E1, "evaluator_name": None, "python_code": "new"}),
        ("set_evaluator_archived", {"evaluator_id": E1, "archived": True}),
    ]


@pytest.mark.asyncio
async def test_template_tools_return_the_template_models() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    templates = await list_evaluator_templates(client=client, workspace=WORKSPACE)
    combined = await combine_evaluator_templates(
        client=client, workspace=WORKSPACE, template_keys=["a", "b"], title="T"
    )

    assert isinstance(templates, list)
    assert templates[0].key == "tool_calls"
    assert isinstance(combined, CombinedEvaluatorTemplates)
    assert resource.calls == [
        ("list_evaluator_templates", {}),
        ("combine_evaluator_templates", {"template_keys": ["a", "b"], "title": "T"}),
    ]


@pytest.mark.asyncio
async def test_metric_group_writes_forward_weights_and_return_the_group() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)
    weights = [MetricWeight(evaluator_id=E1, metric_key="answered", weight=2)]

    created = await create_metric_group(
        client=client, workspace=WORKSPACE, name="W", evaluator_ids=[E1], weights=weights
    )
    updated = await update_metric_group(
        client=client, workspace=WORKSPACE, metric_group_id=METRIC_GROUP_ID, name="W", evaluator_ids=[E1]
    )

    assert isinstance(created, MetricGroup)
    assert isinstance(updated, MetricGroup)
    assert resource.calls == [
        ("create_metric_group", {"group_name": "W", "evaluator_ids": [E1], "weights": weights}),
        (
            "update_metric_group",
            {"metric_group_id": METRIC_GROUP_ID, "group_name": "W", "evaluator_ids": [E1], "weights": None},
        ),
    ]


@pytest.mark.asyncio
async def test_delete_metric_group_confirms_in_a_string() -> None:
    resource = FakeEvaluationResource()

    result = await delete_metric_group(
        client=FakeClient(resource), workspace=WORKSPACE, metric_group_id=METRIC_GROUP_ID
    )

    assert METRIC_GROUP_ID in result
    assert resource.calls == [("delete_metric_group", {"metric_group_id": METRIC_GROUP_ID})]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        ResourceNotFoundError(message="Evaluator not found"),
        BadRequestError(message="bad"),
        UnexpectedAPIError(status_code=409, message="An evaluator named 'N' already exists"),
    ],
)
async def test_evaluator_and_metric_group_write_tools_return_the_api_message_instead_of_raising(
    error: Exception,
) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))
    common: dict[str, Any] = {"client": client, "workspace": WORKSPACE}

    results = [
        await create_evaluator(**common, name="N", python_code="code"),
        await update_evaluator(**common, evaluator_id=E1, name="N"),
        await set_evaluator_archived(**common, evaluator_id=E1, archived=False),
        await list_evaluator_templates(**common),
        await combine_evaluator_templates(**common, template_keys=["a", "b"], title="T"),
        await create_metric_group(**common, name="W", evaluator_ids=[E1]),
        await update_metric_group(**common, metric_group_id=METRIC_GROUP_ID, name="W", evaluator_ids=[E1]),
        await delete_metric_group(**common, metric_group_id=METRIC_GROUP_ID),
    ]

    assert all(isinstance(result, str) and str(error.args[0]) in result for result in results)


@pytest.mark.asyncio
async def test_create_experiment_with_preview_returns_the_plan_and_creates_nothing() -> None:
    resource = FakeEvaluationResource()

    plan = await create_experiment(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        name="Preview",
        dataset_id="d-1",
        metric_group_id=METRIC_GROUP_ID,
        candidate_pipeline_name=PIPELINE,
        candidate_pipeline_version_id=V1,
        sessions_per_test_case=3,
        preview=True,
    )

    assert isinstance(plan, ExperimentPlan)
    assert plan.candidate.replays_needed == 1
    assert resource.calls == [
        ("preview_experiment", {"dataset_id": "d-1", "sessions_per_test_case": 3, "reuse_sessions": True})
    ]


@pytest.mark.asyncio
async def test_get_experiment_returns_test_cases_and_run_counts_but_not_the_sessions() -> None:
    resource = FakeEvaluationResource()

    experiment = await get_experiment(client=FakeClient(resource), workspace=WORKSPACE, experiment_id=COMPARISON_ID)

    assert isinstance(experiment, ExperimentDetail)
    assert resource.calls == [("get_experiment", {"experiment_id": COMPARISON_ID})]
    dumped = experiment.model_dump()
    assert dumped["test_cases"] == [{"test_case_id": E2, "name": "Order status"}]
    assert dumped["candidate"]["run_counts"]["failed"] == 1
    assert dumped["candidate"]["scoring_counts"]["errored"] == 1
    assert dumped["candidate"]["experiment_run_id"] == RUN_ID
    assert dumped["baseline"]["error"] == "No Sessions"
    assert "sessions" not in dumped["candidate"]


@pytest.mark.asyncio
async def test_update_experiment_forwards_the_changes_and_previews_without_changing() -> None:
    resource = FakeEvaluationResource()
    common: dict[str, Any] = {"client": FakeClient(resource), "workspace": WORKSPACE, "experiment_id": COMPARISON_ID}

    updated = await update_experiment(**common, name="Renamed", recorded_baseline=True)
    plan = await update_experiment(**common, name="Renamed", preview=True)

    assert isinstance(updated, Experiment)
    assert isinstance(plan, ExperimentUpdatePlan)
    assert plan.baseline is None
    assert resource.calls == [
        ("update_experiment", {"experiment_id": COMPARISON_ID, "name": "Renamed", "recorded_baseline": True}),
        ("preview_update_experiment", {"experiment_id": COMPARISON_ID, "name": "Renamed"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side", [{"candidate_pipeline_name": PIPELINE}, {"baseline_pipeline_version_id": V1}], ids=["candidate", "baseline"]
)
async def test_update_experiment_refuses_a_half_given_side_without_calling_the_resource(side: dict[str, Any]) -> None:
    resource = FakeEvaluationResource()

    result = await update_experiment(
        client=FakeClient(resource), workspace=WORKSPACE, experiment_id=COMPARISON_ID, **side
    )

    assert isinstance(result, str)
    assert "pipeline_name" in result
    assert resource.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("rerun", "replays"), [("evaluations", False), ("replays", True)])
async def test_rerun_failed_experiment_picks_evaluations_or_replays(rerun: Any, replays: bool) -> None:
    resource = FakeEvaluationResource()

    result = await rerun_failed_experiment(
        client=FakeClient(resource), workspace=WORKSPACE, experiment_id=COMPARISON_ID, rerun=rerun
    )

    assert isinstance(result, Experiment)
    assert resource.calls == [("rerun_failed_experiment", {"experiment_id": COMPARISON_ID, "replays": replays})]


@pytest.mark.asyncio
async def test_rescore_and_delete_experiment_call_the_resource_and_delete_confirms_in_a_string() -> None:
    resource = FakeEvaluationResource()
    common: dict[str, Any] = {"client": FakeClient(resource), "workspace": WORKSPACE, "experiment_id": COMPARISON_ID}

    rescored = await rescore_experiment(**common)
    deleted = await delete_experiment(**common)

    assert isinstance(rescored, Experiment)
    assert COMPARISON_ID in deleted
    assert [name for name, _ in resource.calls] == ["rescore_experiment", "delete_experiment"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        ResourceNotFoundError(message="Experiment not found"),
        BadRequestError(message="bad"),
        UnexpectedAPIError(status_code=409, message="No failed evaluations to rerun in this Experiment"),
        UnexpectedAPIError(status_code=429, message="Too many scoring runs"),
    ],
)
async def test_experiment_tools_return_the_api_message_instead_of_raising(error: Exception) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))
    common: dict[str, Any] = {"client": client, "workspace": WORKSPACE}
    target: dict[str, Any] = {**common, "experiment_id": COMPARISON_ID}

    results = [
        await create_experiment(
            **common,
            name="N",
            dataset_id="d-1",
            metric_group_id=METRIC_GROUP_ID,
            candidate_pipeline_name=PIPELINE,
            candidate_pipeline_version_id=V1,
            preview=True,
        ),
        await get_experiment(**target),
        await update_experiment(**target, name="N"),
        await update_experiment(**target, name="N", preview=True),
        await rerun_failed_experiment(**target),
        await rescore_experiment(**target),
        await delete_experiment(**target),
    ]

    assert all(isinstance(result, str) and str(error.args[0]) in result for result in results)


# ---------------------------------------------------------------------------------------------
# Standalone scoring runs, single Evaluation Runs, and fresh Sessions for an Experiment
# ---------------------------------------------------------------------------------------------

WINDOW_FROM = "2026-10-01T00:00:00Z"
WINDOW_TO = "2026-10-08T00:00:00Z"


@pytest.mark.asyncio
async def test_list_experiment_runs_reads_a_metric_groups_runs_or_the_runs_that_judged_a_session() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    by_group = await list_experiment_runs(
        client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, metric_group_id=METRIC_GROUP_ID, limit=5
    )
    by_session = await list_experiment_runs(
        client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, session_id=SESSION_A
    )

    assert by_group == by_session == [run()]
    assert resource.calls == [
        ("list_experiment_runs", {"metric_group_id": METRIC_GROUP_ID, "limit": 5}),
        ("list_session_experiment_runs", {"session_id": SESSION_A, "limit": 50}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("target", [{}, {"metric_group_id": METRIC_GROUP_ID, "session_id": SESSION_A}])
async def test_list_experiment_runs_wants_exactly_one_of_metric_group_and_session(target: dict[str, Any]) -> None:
    resource = FakeEvaluationResource()

    result = await list_experiment_runs(
        client=FakeClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE, **target
    )

    assert isinstance(result, str)
    assert "metric_group_id" in result
    assert "session_id" in result
    assert resource.calls == []


@pytest.mark.asyncio
async def test_start_experiment_run_over_named_sessions_forwards_them_and_returns_the_run_to_poll() -> None:
    resource = FakeEvaluationResource()

    accepted = await start_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        session_ids=[SESSION_A, SESSION_B],
        reuse="REUSE_SUCCEEDED",
        selection="HAND_PICKED",
        focus={SESSION_A: [E1]},
    )

    assert accepted == ExperimentRunAccepted(pipeline_experiment_run_id=RUN_ID, cells=4)
    assert resource.calls == [
        (
            "start_experiment_run",
            {
                "metric_group_id": METRIC_GROUP_ID,
                "session_ids": [SESSION_A, SESSION_B],
                "window": None,
                "reuse": "REUSE_SUCCEEDED",
                "selection": "HAND_PICKED",
                "focus": {SESSION_A: [E1]},
            },
        )
    ]


@pytest.mark.asyncio
async def test_start_experiment_run_over_a_window_builds_the_window_from_its_parts() -> None:
    resource = FakeEvaluationResource()

    accepted = await start_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        window_from=WINDOW_FROM,
        window_to=WINDOW_TO,
        origin="SERVICE",
        deployment_id=E2,
    )

    assert isinstance(accepted, ExperimentRunAccepted)
    [(_, kwargs)] = resource.calls
    assert kwargs["session_ids"] is None
    assert kwargs["window"] == SessionWindow(start=WINDOW_FROM, end=WINDOW_TO, origin="SERVICE", deployment_id=E2)


@pytest.mark.asyncio
async def test_start_experiment_run_with_preview_counts_the_window_and_starts_nothing() -> None:
    resource = FakeEvaluationResource()

    plan = await start_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        window_from=WINDOW_FROM,
        window_to=WINDOW_TO,
        preview=True,
    )

    assert isinstance(plan, ExperimentRunPreview)
    assert (plan.sessions, plan.cells, plan.ceiling.cells) == (12, 36, 200)
    assert resource.calls == [
        (
            "preview_experiment_run",
            {"metric_group_id": METRIC_GROUP_ID, "window": SessionWindow(start=WINDOW_FROM, end=WINDOW_TO)},
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "mentions"),
    [
        ({"window_from": WINDOW_FROM}, "window_to"),
        ({"window_to": WINDOW_TO}, "window_from"),
        ({"origin": "SERVICE"}, "window_from"),
        ({"session_ids": [SESSION_A], "preview": True}, "window"),
    ],
)
async def test_start_experiment_run_refuses_a_half_given_window_or_a_preview_of_named_sessions(
    arguments: dict[str, Any], mentions: str
) -> None:
    resource = FakeEvaluationResource()

    result = await start_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        **arguments,
    )

    assert isinstance(result, str)
    assert mentions in result
    assert resource.calls == []


@pytest.mark.asyncio
async def test_run_evaluator_polls_until_the_run_ended_and_returns_it() -> None:
    resource = FakeEvaluationResource(evaluation_run_states=[evaluation_run("STARTED"), evaluation_run("ENDED")])

    result = await run_evaluator(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        evaluator_version_id=V1,
        session_id=SESSION_A,
    )

    assert isinstance(result, EvaluationRun)
    assert (result.status, result.outcome, result.metrics[0].label) == ("ENDED", "SUCCEEDED", "yes")
    assert [c[0] for c in resource.calls] == ["run_evaluator", "get_evaluation_run", "get_evaluation_run"]
    assert resource.calls[0][1] == {"evaluator_version_id": V1, "session_id": SESSION_A}


@pytest.mark.asyncio
async def test_run_evaluator_hands_back_the_id_when_the_wait_runs_out() -> None:
    resource = FakeEvaluationResource(evaluation_run_states=[evaluation_run("STARTED")])

    result = await run_evaluator(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        evaluator_version_id=V1,
        session_id=SESSION_A,
        wait_seconds=0,
    )

    assert isinstance(result, EvaluationRun)
    assert (result.evaluation_run_id, result.status, result.metrics) == (EVALUATION_RUN_ID, "STARTED", [])


@pytest.mark.asyncio
async def test_list_and_get_evaluation_run_pass_through() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    listed = await list_evaluation_runs(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, limit=3)
    one = await get_evaluation_run(
        client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, evaluation_run_id=EVALUATION_RUN_ID
    )

    assert listed == [one] == [evaluation_run()]
    assert resource.calls == [
        ("list_evaluation_runs", {"limit": 3}),
        ("get_evaluation_run", {"evaluation_run_id": EVALUATION_RUN_ID}),
    ]


@pytest.mark.asyncio
async def test_create_experiment_forwards_reuse_sessions_to_the_create_and_the_preview() -> None:
    resource = FakeEvaluationResource()
    common: dict[str, Any] = {
        "client": FakeClient(resource),
        "workspace": WORKSPACE,
        "name": "Fresh",
        "dataset_id": "d-1",
        "metric_group_id": METRIC_GROUP_ID,
        "candidate_pipeline_name": PIPELINE,
        "candidate_pipeline_version_id": V1,
        "reuse_sessions": False,
    }

    await create_experiment(**common)
    await create_experiment(**common, preview=True)

    created, previewed = resource.calls
    assert created[1]["body"]["reuse_sessions"] is False
    assert previewed[1]["reuse_sessions"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        ResourceNotFoundError(message="Session not found"),
        BadRequestError(message="There are no Sessions in this window"),
        UnexpectedAPIError(status_code=422, message="This window has more than 50 Sessions"),
        UnexpectedAPIError(status_code=429, message="Too many experiment runs in flight"),
    ],
)
async def test_run_tools_return_the_api_message_instead_of_raising(error: Exception) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))
    common: dict[str, Any] = {"client": client, "workspace": WORKSPACE, "pipeline_name": PIPELINE}
    window: dict[str, Any] = {"window_from": WINDOW_FROM, "window_to": WINDOW_TO}

    results = [
        await list_experiment_runs(**common, metric_group_id=METRIC_GROUP_ID),
        await list_experiment_runs(**common, session_id=SESSION_A),
        await start_experiment_run(**common, metric_group_id=METRIC_GROUP_ID, session_ids=[SESSION_A]),
        await start_experiment_run(**common, metric_group_id=METRIC_GROUP_ID, **window, preview=True),
        await run_evaluator(**common, evaluator_version_id=V1, session_id=SESSION_A),
        await list_evaluation_runs(**common),
        await get_evaluation_run(**common, evaluation_run_id=EVALUATION_RUN_ID),
    ]

    assert all(isinstance(result, str) and str(error.args[0]) in result for result in results)


def _aggregate(**fields: Any) -> dict[str, Any]:
    """One side's whole-run entry for a Metric, as hub-api's Aggregate reports it."""
    return {
        "evaluator_id": E1,
        "evaluator_version_ids": ["22222222-2222-2222-2222-222222222222"],
        "sessions": {"valued": 2, "not_applicable": 0, "unusable": 0, "errored": 0, "failed": 0, "pending": 0},
        "coverage": 1.0,
        **fields,
    }


@pytest.mark.asyncio
async def test_get_experiment_results_reports_each_sides_whole_run_aggregate_and_formula() -> None:
    weights = [{"evaluator_id": E1, "metric_key": "helpful", "weight": 2.0}]
    payload = experiment_results(test_cases=1)
    payload["headline"] = {
        "candidate": {**_side({"kind": "value", "value": 0.8, "coverage": 1.0}), "composite_weights": weights},
        "baseline": _side({"kind": "missing", "reason": "not scored yet"}),
    }
    payload["aggregates"] = [
        {
            "evaluator_id": E1,
            "metric_key": "helpful",
            "shape": "score",
            "candidate": _aggregate(metric_key="helpful", shape="score", mean=0.9, better="higher", range=[0, 1]),
            "baseline": _aggregate(metric_key="helpful", shape="score", mean=0.6, better="higher", range=[0, 1]),
            "delta": 0.3,
            "share_deltas": None,
            "change": "improved",
        },
        {
            "evaluator_id": E1,
            "metric_key": "tone",
            "shape": "label",
            "candidate": _aggregate(metric_key="tone", shape="label", shares={"kind": 1.0}, vocabulary=None),
            "baseline": None,
            "delta": None,
            "share_deltas": None,
            "change": "unknown",
        },
    ]

    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource(results=payload)), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert results.headline is not None
    assert [(w.metric_key, w.weight) for w in results.headline.candidate.composite_weights] == [("helpful", 2.0)]
    assert results.headline.baseline.composite_weights == []
    helpful, tone = results.aggregates
    assert (helpful.delta, helpful.change) == (0.3, "improved")
    assert isinstance(helpful.candidate, ScoreAggregate) and helpful.candidate.mean == 0.9
    assert isinstance(tone.candidate, LabelAggregate) and tone.candidate.shares == {"kind": 1.0}
    assert (tone.baseline, tone.change) == (None, "unknown")


@pytest.mark.asyncio
async def test_get_experiment_results_from_an_older_api_has_no_aggregates() -> None:
    results = await get_experiment_results(
        client=FakeClient(FakeEvaluationResource()), workspace=WORKSPACE, experiment_id=COMPARISON_ID
    )

    assert isinstance(results, ExperimentResultsReport)
    assert results.aggregates == []


@pytest.mark.asyncio
async def test_get_session_replay_reports_a_run_of_inputs_without_a_source_session_or_version() -> None:
    run = SessionReplayRun.model_validate(
        {
            "session_replay_run_id": REPLAY_RUN_ID,
            "pipeline_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "pipeline_version_id": None,
            "pipeline_optimization_candidate_id": "dddddddd-1111-2222-3333-444444444444",
            "status": "FAILED",
            "source_session_id": None,
            "inputs": {"query": "who wrote Dune?"},
            "session_id": "eeeeeeee-1111-2222-3333-444444444444",
            "trace_ids": [],
            "created_at": "2026-10-07T00:00:00Z",
        }
    )

    report = await get_session_replay(
        client=FakeCheckClient(FakeEvaluationResource(replay_states=[run])),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        replay_run_id=REPLAY_RUN_ID,
    )

    assert isinstance(report, SessionReplayReport)
    assert (report.status, report.source_session_id, report.pipeline_version_id) == ("FAILED", None, None)


@pytest.mark.asyncio
async def test_list_session_replays_returns_the_runs() -> None:
    resource = FakeEvaluationResource()

    runs = await list_session_replays(client=FakeClient(resource), workspace=WORKSPACE, pipeline_name=PIPELINE, limit=5)

    assert isinstance(runs, list)
    assert runs[0].session_replay_run_id == REPLAY_RUN_ID
    assert resource.calls == [("list_session_replays", {"pipeline_name": PIPELINE, "limit": 5})]


@pytest.mark.asyncio
async def test_start_replay_suite_hands_back_the_suite_without_waiting() -> None:
    resource = FakeEvaluationResource()

    accepted = await start_replay_suite(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        dataset_id="bbbbbbbb-1111-2222-3333-444444444444",
        pipeline_version_id=DRAFT_VERSION_ID,
        repetitions=3,
        metric_group_id=METRIC_GROUP_ID,
        reuse="REUSE_SUCCEEDED",
    )

    assert isinstance(accepted, ReplaySuiteAccepted)
    assert (accepted.suite_id, accepted.run_count) == (SUITE_ID, 6)
    assert resource.calls == [
        (
            "start_replay_suite",
            {
                "dataset_id": "bbbbbbbb-1111-2222-3333-444444444444",
                "pipeline_version_id": DRAFT_VERSION_ID,
                "repetitions": 3,
                "replay_mode": "FIRST_USER_MESSAGE",
                "metric_group_id": METRIC_GROUP_ID,
                "reuse": "REUSE_SUCCEEDED",
            },
        )
    ]


@pytest.mark.asyncio
async def test_reuse_without_a_metric_group_is_refused_before_any_replay_starts() -> None:
    resource = FakeEvaluationResource()

    result = await start_replay_suite(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        dataset_id="bbbbbbbb-1111-2222-3333-444444444444",
        pipeline_version_id=DRAFT_VERSION_ID,
        reuse="RERUN_ALL",
    )

    assert isinstance(result, str)
    assert "metric_group_id" in result
    assert resource.calls == []


@pytest.mark.asyncio
async def test_list_and_get_replay_suite_return_the_suite_with_its_counts_and_runs() -> None:
    client = FakeClient(FakeEvaluationResource())

    suites = await list_replay_suites(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE)
    suite = await get_replay_suite(client=client, workspace=WORKSPACE, pipeline_name=PIPELINE, suite_id=SUITE_ID)

    assert isinstance(suites, list)
    assert suites[0].run_counts.failed == 1
    assert isinstance(suite, ReplaySuite)
    assert suite.test_cases[0].runs[0].repetition == 2


@pytest.mark.asyncio
async def test_imported_session_traces_read_like_pipeline_traces() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    turns = await list_imported_session_traces(client=client, workspace=WORKSPACE, session_id=IMPORTED_SESSION_ID)
    turn = await get_imported_session_trace(
        client=client, workspace=WORKSPACE, session_id=IMPORTED_SESSION_ID, query_id=IMPORTED_QUERY_ID
    )
    tags = await get_imported_session_trace_span_tags(
        client=client,
        workspace=WORKSPACE,
        session_id=IMPORTED_SESSION_ID,
        query_id=IMPORTED_QUERY_ID,
        span_id=IMPORTED_SPAN_ID,
    )

    assert isinstance(turns, list)
    assert isinstance(turn, PipelineTraceEntry)
    assert turns[0].query_id == turn.query_id == IMPORTED_QUERY_ID
    assert tags == {"haystack.component.input": {"query": "x"}}
    assert [name for name, _ in resource.calls] == [
        "list_imported_session_traces",
        "get_imported_session_trace",
        "get_imported_session_trace_span_tags",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ResourceNotFoundError(), "not found"),
        (BadRequestError(message="bad"), "Failed"),
        (UnexpectedAPIError(status_code=503, message="queue down"), "Failed"),
    ],
)
async def test_replay_suite_and_imported_trace_errors_come_back_as_readable_strings(
    error: Exception, expected: str
) -> None:
    client = FakeClient(FakeEvaluationResource(error=error))
    base: dict[str, Any] = {"client": client, "workspace": WORKSPACE}
    imported = {**base, "session_id": IMPORTED_SESSION_ID}

    results = [
        await list_session_replays(**base, pipeline_name=PIPELINE),
        await start_replay_suite(**base, pipeline_name=PIPELINE, dataset_id="d", pipeline_version_id=DRAFT_VERSION_ID),
        await list_replay_suites(**base, pipeline_name=PIPELINE),
        await get_replay_suite(**base, pipeline_name=PIPELINE, suite_id=SUITE_ID),
        await list_imported_session_traces(**imported),
        await get_imported_session_trace(**imported, query_id=IMPORTED_QUERY_ID),
        await get_imported_session_trace_span_tags(**imported, query_id=IMPORTED_QUERY_ID, span_id=IMPORTED_SPAN_ID),
    ]

    for result in results:
        assert isinstance(result, str)
        assert expected in result


@pytest.mark.asyncio
async def test_lists_without_paging_pass_the_limit_so_the_agent_can_raise_it_to_the_api_cap() -> None:
    resource = FakeEvaluationResource()
    client = FakeClient(resource)

    await list_evaluators(client=client, workspace=WORKSPACE, limit=7, archived=True)
    await list_metric_groups(client=client, workspace=WORKSPACE, limit=8)
    await list_experiments(client=client, workspace=WORKSPACE, limit=200)
    await list_datasets(client=client, workspace=WORKSPACE, limit=9)

    assert resource.calls == [
        ("list_evaluators", {"limit": 7, "archived": True}),
        ("list_metric_groups", {"limit": 8}),
        ("list_experiments", {"pipeline_name": None, "limit": 200}),
        ("list_datasets", {"pipeline_name": None, "limit": 9}),
    ]


@pytest.mark.asyncio
async def test_list_sessions_passes_the_revision_and_the_cursor_for_the_next_page() -> None:
    resource = FakeEvaluationResource()

    await list_sessions(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        revision_id="rev-1",
        cursor="cursor-2",
    )

    assert resource.calls[-1][1]["revision_id"] == "rev-1"
    assert resource.calls[-1][1]["cursor"] == "cursor-2"


@pytest.mark.asyncio
async def test_get_experiment_run_passes_the_grid_filters() -> None:
    resource = FakeEvaluationResource()

    await get_experiment_run(
        client=FakeClient(resource),
        workspace=WORKSPACE,
        pipeline_name=PIPELINE,
        metric_group_id=METRIC_GROUP_ID,
        run_id=RUN_ID,
        origin="SERVICE",
        deployment_id="dep-1",
        pipeline_version_id="ver-1",
        session_id="ses-1",
    )

    assert resource.calls == [
        (
            "get_experiment_run",
            {
                "metric_group_id": METRIC_GROUP_ID,
                "run_id": RUN_ID,
                "origin": "SERVICE",
                "deployment_id": "dep-1",
                "pipeline_version_id": "ver-1",
                "session_id": "ses-1",
            },
        )
    ]


@pytest.mark.asyncio
async def test_get_experiment_run_returns_the_apis_aggregate_usage_and_evaluator_versions() -> None:
    version = {
        "evaluator_version_id": V1,
        "evaluator_id": E1,
        "content_hash": "abc",
        "metrics": {},
        "created_at": "2026-10-01T00:00:00Z",
    }
    report = await _report(
        _grid_with(
            aggregate={
                "metrics": [
                    {
                        "shape": "score",
                        "evaluator_id": E1,
                        "metric_key": "accuracy",
                        "evaluator_version_ids": [V1],
                        "sessions": {"valued": 2, "errored": 1},
                        "coverage": 0.67,
                        "mean": 0.6,
                        "better": "higher",
                        "range": [0, 1],
                    }
                ]
            },
            usage={
                "duration_s": 12.5,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.02,
                "cost_status": "priced",
                "sessions": 2,
            },
            evaluator_versions=[version],
        )
    )

    assert report.aggregate is not None
    [accuracy] = report.aggregate.metrics
    assert isinstance(accuracy, ScoreAggregate)
    assert (accuracy.mean, accuracy.sessions.valued, accuracy.sessions.errored) == (0.6, 2, 1)
    assert report.usage is not None
    assert (report.usage.total_tokens, report.usage.cost, report.usage.cost_status, report.usage.sessions) == (
        150,
        0.02,
        "priced",
        2,
    )
    assert [v.evaluator_version_id for v in report.evaluator_versions] == [V1]


@pytest.mark.asyncio
async def test_get_experiment_run_from_an_older_api_has_no_aggregate_or_usage() -> None:
    report = await _report(grid())

    assert (report.aggregate, report.usage, report.evaluator_versions) == (None, None, [])
