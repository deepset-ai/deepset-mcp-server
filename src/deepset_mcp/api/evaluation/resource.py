# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource for the evaluation API: Evaluators, Metric Groups, their scoring runs, Experiments, and Sessions."""

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from deepset_mcp.api import ids
from deepset_mcp.api.evaluation.models import (
    Dataset,
    DatasetSummary,
    EvaluationGoal,
    EvaluationRun,
    EvaluationTryResult,
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
    SessionList,
    SessionReplayRun,
    SessionWindow,
    TestCase,
    TryState,
)
from deepset_mcp.api.evaluation.protocols import EvaluationResourceProtocol
from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


def _dump(test_cases: list[NewTestCase]) -> list[dict[str, Any]]:
    """Only the fields the caller set: hub-api rejects a test case that sends both a Session and inputs."""
    return [test_case.model_dump(exclude_none=True) for test_case in test_cases]


def _metric_group_body(name: str, evaluator_ids: list[str], weights: list[MetricWeight] | None) -> dict[str, Any]:
    """``weights`` is left out when None, which on update keeps the stored ones; [] clears them."""
    body: dict[str, Any] = {"name": name, "evaluator_ids": evaluator_ids}
    if weights is not None:
        body["weights"] = [weight.model_dump() for weight in weights]
    return body


class EvaluationResource(EvaluationResourceProtocol):
    """Reads Evaluators, Experiments, their runs, and Sessions through the v2 evaluation routes.

    The routes are keyed by workspace and pipeline UUIDs; this resource takes names, like every
    other resource, and resolves them on each call.
    """

    def __init__(self, client: "AsyncClientProtocol", workspace: str) -> None:
        """Initialize the evaluation resource.

        :param client: The async REST client.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def _post(self, path: str, data: dict[str, Any]) -> Any:
        resp = await self._client.request(endpoint=path, method="POST", data=data)
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)
        return resp.json

    async def _put(self, path: str, data: dict[str, Any]) -> Any:
        resp = await self._client.request(endpoint=path, method="PUT", data=data)
        raise_for_status(resp)
        return resp.json

    async def _patch(self, path: str, data: dict[str, Any]) -> Any:
        resp = await self._client.request(endpoint=path, method="PATCH", data=data)
        raise_for_status(resp)
        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)
        return resp.json

    async def _delete(self, path: str) -> None:
        raise_for_status(await self._client.request(endpoint=path, method="DELETE"))

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self._client.request(endpoint=path, method="GET", params=params)
        raise_for_status(resp)
        return resp.json

    @staticmethod
    def _path(*segments: str) -> str:
        return "v2/workspaces/" + "/".join(quote(segment, safe="") for segment in segments)

    async def _workspace_path(self, *parts: str) -> str:
        return self._path(await ids.workspace_id(self._client, self._workspace), "evaluation", *parts)

    async def _evaluators_path(self, *parts: str) -> str:
        return await self._workspace_path("evaluators", *parts)

    async def _pipeline_path(self, pipeline_name: str, *parts: str) -> str:
        workspace_id, pipeline_id = await ids.workspace_and_pipeline_ids(self._client, self._workspace, pipeline_name)
        return self._path(workspace_id, "evaluation", "pipelines", pipeline_id, *parts)

    async def list_evaluators(self, limit: int = 200, archived: bool | None = None) -> list[Evaluator]:
        """List the workspace's Evaluators, each with its newest version but no source.

        :param limit: Maximum number of Evaluators to return (the API caps it at 200 and has no further paging).
        :param archived: ``True`` for only archived Evaluators, ``False`` for only the others; both when omitted.
        :returns: The Evaluators.
        """
        params: dict[str, Any] = {"limit": limit}
        if archived is not None:
            params["archived"] = archived
        data = await self._get(await self._evaluators_path(), params)
        return [Evaluator.model_validate(item) for item in data or []]

    async def get_evaluator(self, evaluator_id: str) -> Evaluator:
        """Fetch one Evaluator with every version, newest first, none with source.

        :param evaluator_id: The Evaluator's id.
        :returns: The Evaluator.
        """
        return Evaluator.model_validate(await self._get(await self._evaluators_path(evaluator_id)))

    async def get_evaluator_version(self, evaluator_id: str, version_id: str) -> EvaluatorVersion:
        """Fetch one Evaluator version with its Python source.

        :param evaluator_id: The Evaluator's id.
        :param version_id: The version's id.
        :returns: The version.
        """
        path = await self._evaluators_path(evaluator_id, "versions", version_id)
        return EvaluatorVersion.model_validate(await self._get(path))

    async def list_metric_groups(self, limit: int = 200) -> list[MetricGroup]:
        """List the workspace's Metric Groups, newest first.

        :param limit: Maximum number of Metric Groups to return (the API caps it at 200).
        :returns: The Metric Groups.
        """
        data = await self._get(await self._workspace_path("metric-groups"), {"limit": limit})
        return [MetricGroup.model_validate(item) for item in data or []]

    async def list_evaluation_goals(self, pipeline_name: str) -> list[EvaluationGoal]:
        """List the Evaluation Goals set on one pipeline, oldest first.

        :param pipeline_name: Name of the pipeline.
        :returns: The Evaluation Goals.
        """
        raise NotImplementedError

    async def list_experiment_runs(
        self, pipeline_name: str, metric_group_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List a Metric Group's scoring runs on one pipeline, newest first, without their grids.

        :param pipeline_name: Name of the pipeline.
        :param metric_group_id: The Metric Group's id.
        :param limit: Maximum number of runs to return.
        :returns: The runs.
        """
        path = await self._pipeline_path(pipeline_name, "metric-groups", metric_group_id, "scoring-runs")
        return [ExperimentRun.model_validate(item) for item in await self._get(path, {"limit": limit}) or []]

    async def list_session_experiment_runs(
        self, pipeline_name: str, session_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List the scoring runs, of any Metric Group, that judged one Session, newest first.

        :param pipeline_name: Name of the pipeline.
        :param session_id: The Session the runs judged.
        :param limit: Maximum number of runs to return (the API caps it at 200).
        :returns: The runs, each naming its Metric Group.
        """
        path = await self._pipeline_path(pipeline_name, "scoring-runs")
        data = await self._get(path, {"session_id": session_id, "limit": limit})
        return [ExperimentRun.model_validate(item) for item in data or []]

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
        """Start a scoring run: a Metric Group judging named Sessions, or every Session in a window.

        :param pipeline_name: Name of the pipeline.
        :param metric_group_id: The Metric Group to judge with.
        :param session_ids: The Sessions to judge. Send this or ``window``.
        :param window: Judge every Session whose last activity falls in this window. Send this or ``session_ids``.
        :param reuse: RERUN_ALL or REUSE_SUCCEEDED; omitted, the server's default (RERUN_ALL).
        :param selection: SAMPLED or HAND_PICKED; omitted, the server's default (SAMPLED).
        :param focus: Per Session, the turns to judge by query id; a Session left out is judged on every turn.
        :returns: The queued run and how many cells it will have.
        """
        body: dict[str, Any] = {}
        if session_ids is not None:
            body["session_ids"] = session_ids
        if window is not None:
            body["window"] = window.model_dump(by_alias=True, exclude_none=True)
        if reuse is not None:
            body["reuse"] = reuse
        if selection is not None:
            body["selection"] = selection
        if focus is not None:
            body["focus"] = focus
        path = await self._pipeline_path(pipeline_name, "metric-groups", metric_group_id, "scoring-runs")
        return ExperimentRunAccepted.model_validate(await self._post(path, body))

    async def preview_experiment_run(
        self, pipeline_name: str, metric_group_id: str, window: SessionWindow
    ) -> ExperimentRunPreview:
        """Count what a window run would judge, without starting it.

        :param pipeline_name: Name of the pipeline.
        :param metric_group_id: The Metric Group the run would judge with.
        :param window: The window of Sessions.
        :returns: Sessions, Evaluators and cells, against the ceiling a window run may not pass.
        """
        path = await self._pipeline_path(pipeline_name, "metric-groups", metric_group_id, "scoring-runs", "preview")
        data = await self._post(path, window.model_dump(by_alias=True, exclude_none=True))
        return ExperimentRunPreview.model_validate(data)

    async def run_evaluator(self, pipeline_name: str, evaluator_version_id: str, session_id: str) -> str:
        """Start one Evaluator version on one Session.

        :param pipeline_name: Name of the pipeline.
        :param evaluator_version_id: The exact Evaluator version to run.
        :param session_id: The Session to judge.
        :returns: The Evaluation Run id to poll.
        """
        path = await self._pipeline_path(pipeline_name, "evaluation-runs")
        data = await self._post(path, {"evaluator_version_id": evaluator_version_id, "session_id": session_id})
        return str(data["evaluation_run_id"])

    async def list_evaluation_runs(self, pipeline_name: str, limit: int = 50) -> list[EvaluationRun]:
        """List a pipeline's Evaluation Runs, newest first.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of runs to return (the API caps it at 200).
        :returns: The runs.
        """
        data = await self._get(await self._pipeline_path(pipeline_name, "evaluation-runs"), {"limit": limit})
        return [EvaluationRun.model_validate(item) for item in data or []]

    async def get_evaluation_run(self, pipeline_name: str, evaluation_run_id: str) -> EvaluationRun:
        """Read one Evaluation Run: its progress, or its Metrics once judged.

        :param pipeline_name: Name of the pipeline.
        :param evaluation_run_id: The run's id.
        :returns: The run.
        """
        path = await self._pipeline_path(pipeline_name, "evaluation-runs", evaluation_run_id)
        return EvaluationRun.model_validate(await self._get(path))

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
        """Fetch one scoring run as a grid of Sessions by Evaluators.

        :param pipeline_name: Name of the pipeline.
        :param metric_group_id: The Metric Group's id.
        :param run_id: The run's id.
        :param origin: Only cells whose Session came from SERVICE, PIPELINE_RUN or PLAYGROUND.
        :param deployment_id: Only cells whose Session this Service served.
        :param pipeline_version_id: Only cells whose Session this pipeline version served.
        :param session_id: Only this Session's row.
        :returns: The grid.
        """
        params = {
            "origin": origin,
            "deployment_id": deployment_id,
            "pipeline_version_id": pipeline_version_id,
            "session_id": session_id,
        }
        path = await self._pipeline_path(pipeline_name, "metric-groups", metric_group_id, "scoring-runs", run_id)
        query = {k: v for k, v in params.items() if v is not None}
        return ExperimentRunGrid.model_validate(await self._get(path, query))

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
        """Create an Experiment: a candidate pipeline version against a baseline on one Dataset.

        :param name: Human-readable name.
        :param dataset_id: The Dataset's id (the UI's Dataset dropdown).
        :param metric_group_id: The Metric Group to score with.
        :param candidate_pipeline_name: Name of the candidate pipeline.
        :param candidate_pipeline_version_id: Candidate version id.
        :param baseline_pipeline_name: Baseline pipeline name; None means a Recorded baseline.
        :param baseline_pipeline_version_id: Baseline version id; required when baseline_pipeline_name is given.
        :param sessions_per_test_case: Repetitions per test case (1..50).
        :param replay_mode: FIRST_USER_MESSAGE or ALL_USER_MESSAGES.
        :param reuse_sessions: False replays every Session each side scores instead of reusing existing ones.
        :returns: The created Experiment.
        """
        body = {
            "name": name,
            **await self._experiment_targets(
                dataset_id,
                metric_group_id,
                candidate_pipeline_name,
                candidate_pipeline_version_id,
                baseline_pipeline_name,
                baseline_pipeline_version_id,
                sessions_per_test_case,
                replay_mode,
                reuse_sessions,
            ),
        }
        data = await self._post(await self._workspace_path("experiments"), body)
        return Experiment.model_validate(data)

    async def _experiment_targets(
        self,
        dataset_id: str,
        metric_group_id: str,
        candidate_pipeline_name: str,
        candidate_pipeline_version_id: str,
        baseline_pipeline_name: str | None,
        baseline_pipeline_version_id: str | None,
        sessions_per_test_case: int,
        replay_mode: str,
        reuse_sessions: bool,
    ) -> dict[str, Any]:
        """What an Experiment compares: the body of a preview, and of a create once it has a name."""
        body: dict[str, Any] = {
            "session_replay_dataset_id": dataset_id,
            "metric_group_id": metric_group_id,
            "candidate": await self._side(candidate_pipeline_name, candidate_pipeline_version_id),
            "sessions_per_test_case": sessions_per_test_case,
            "replay_mode": replay_mode,
        }
        if baseline_pipeline_name is not None:
            body["baseline"] = await self._side(baseline_pipeline_name, baseline_pipeline_version_id)
        if not reuse_sessions:
            body["reuse_sessions"] = False
        return body

    async def _side(self, pipeline_name: str, pipeline_version_id: str | None) -> dict[str, Any]:
        pipeline_id = await ids.pipeline_id(self._client, self._workspace, pipeline_name)
        return {"pipeline_id": pipeline_id, "pipeline_version_id": pipeline_version_id}

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
        """Plan an Experiment without starting it: Sessions reused and replays needed per side.

        :param dataset_id: The Dataset's id.
        :param metric_group_id: The Metric Group to score with.
        :param candidate_pipeline_name: Name of the candidate pipeline.
        :param candidate_pipeline_version_id: Candidate version id.
        :param baseline_pipeline_name: Baseline pipeline name; None means a Recorded baseline.
        :param baseline_pipeline_version_id: Baseline version id; required when baseline_pipeline_name is given.
        :param sessions_per_test_case: Repetitions per test case (1..50).
        :param replay_mode: FIRST_USER_MESSAGE or ALL_USER_MESSAGES.
        :param reuse_sessions: False replays every Session each side scores instead of reusing existing ones.
        :returns: The plan.
        """
        body = await self._experiment_targets(
            dataset_id,
            metric_group_id,
            candidate_pipeline_name,
            candidate_pipeline_version_id,
            baseline_pipeline_name,
            baseline_pipeline_version_id,
            sessions_per_test_case,
            replay_mode,
            reuse_sessions,
        )
        data = await self._post(await self._workspace_path("experiments", "preview"), body)
        return ExperimentPlan.model_validate(data)

    async def get_experiment(self, experiment_id: str) -> ExperimentDetail:
        """Fetch one Experiment with its test cases and each side's progress.

        :param experiment_id: The Experiment's id.
        :returns: The Experiment.
        """
        data = await self._get(await self._workspace_path("experiments", experiment_id))
        return ExperimentDetail.model_validate(data)

    async def _experiment_changes(
        self,
        name: str | None,
        candidate_pipeline_name: str | None,
        candidate_pipeline_version_id: str | None,
        baseline_pipeline_name: str | None,
        baseline_pipeline_version_id: str | None,
        recorded_baseline: bool,
    ) -> dict[str, Any]:
        """Only what changes: hub-api reads a side left out as unchanged."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if candidate_pipeline_name is not None:
            body["candidate"] = await self._side(candidate_pipeline_name, candidate_pipeline_version_id)
        if baseline_pipeline_name is not None:
            body["baseline"] = await self._side(baseline_pipeline_name, baseline_pipeline_version_id)
        if recorded_baseline:
            body["recorded_baseline"] = True
        return body

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
        """Rename an Experiment or change a side; a changed side is replayed and scored again.

        :param experiment_id: The Experiment's id.
        :param name: A new name.
        :param candidate_pipeline_name: Pipeline of the new candidate.
        :param candidate_pipeline_version_id: The new candidate version.
        :param baseline_pipeline_name: Pipeline of the new baseline.
        :param baseline_pipeline_version_id: The new baseline version.
        :param recorded_baseline: True makes the baseline the Dataset's recorded Sessions.
        :returns: The Experiment.
        """
        body = await self._experiment_changes(
            name,
            candidate_pipeline_name,
            candidate_pipeline_version_id,
            baseline_pipeline_name,
            baseline_pipeline_version_id,
            recorded_baseline,
        )
        data = await self._patch(await self._workspace_path("experiments", experiment_id), body)
        return Experiment.model_validate(data)

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
        """Plan an update without changing anything; a side the changes leave alone is null.

        :param experiment_id: The Experiment's id.
        :param name: A new name.
        :param candidate_pipeline_name: Pipeline of the new candidate.
        :param candidate_pipeline_version_id: The new candidate version.
        :param baseline_pipeline_name: Pipeline of the new baseline.
        :param baseline_pipeline_version_id: The new baseline version.
        :param recorded_baseline: True makes the baseline the Dataset's recorded Sessions.
        :returns: The plan.
        """
        body = await self._experiment_changes(
            name,
            candidate_pipeline_name,
            candidate_pipeline_version_id,
            baseline_pipeline_name,
            baseline_pipeline_version_id,
            recorded_baseline,
        )
        data = await self._post(await self._workspace_path("experiments", experiment_id, "preview-update"), body)
        return ExperimentUpdatePlan.model_validate(data)

    async def rerun_failed_experiment(self, experiment_id: str, replays: bool = False) -> Experiment:
        """Judge again the failed evaluations, or with ``replays`` replay again the failed replays.

        :param experiment_id: The Experiment's id.
        :param replays: True retries the failed replays; False the failed evaluations.
        :returns: The Experiment.
        """
        route = "rerun-failed-replays" if replays else "rerun-failed"
        data = await self._post(await self._workspace_path("experiments", experiment_id, route), {})
        return Experiment.model_validate(data)

    async def rescore_experiment(self, experiment_id: str) -> Experiment:
        """Score both sides again with the Metric Group as it is now.

        :param experiment_id: The Experiment's id.
        :returns: The Experiment.
        """
        data = await self._post(await self._workspace_path("experiments", experiment_id, "rescore"), {})
        return Experiment.model_validate(data)

    async def delete_experiment(self, experiment_id: str) -> None:
        """Delete an Experiment; its Sessions, replays and scoring runs are kept.

        :param experiment_id: The Experiment's id.
        """
        await self._delete(await self._workspace_path("experiments", experiment_id))

    async def list_experiments(self, pipeline_name: str | None = None, limit: int = 50) -> list[Experiment]:
        """List the workspace's Experiments, newest first.

        :param pipeline_name: Only Experiments with either side on this pipeline, when given.
        :param limit: Maximum number of Experiments to return (the API caps it at 200).
        :returns: The Experiments.
        """
        params: dict[str, Any] = {"limit": limit}
        if pipeline_name is None:
            path = await self._workspace_path("experiments")
        else:
            workspace_id, params["pipeline_id"] = await ids.workspace_and_pipeline_ids(
                self._client, self._workspace, pipeline_name
            )
            path = self._path(workspace_id, "evaluation", "experiments")
        data = await self._get(path, params)
        return [Experiment.model_validate(item) for item in data or []]

    async def get_experiment_results(self, experiment_id: str) -> ExperimentResults:
        """Fetch an Experiment's results so far: each Metric, candidate against baseline, then per test case.

        :param experiment_id: The Experiment's id.
        :returns: The results.
        """
        path = await self._workspace_path("experiments", experiment_id, "results")
        return ExperimentResults.model_validate(await self._get(path))

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
        """List a pipeline's Sessions that a run can judge, newest last activity first.

        :param pipeline_name: Name of the pipeline.
        :param origin: Only Sessions whose every turn came from SERVICE, PIPELINE_RUN or PLAYGROUND.
        :param deployment_id: Only Sessions whose every turn this Service served.
        :param pipeline_version_id: Only Sessions whose every turn this pipeline version served.
        :param revision_id: Only Sessions whose every turn this Service revision served (exact where a version is
            not: one version can be pushed to a Service more than once).
        :param since: ISO-8601 time; last activity at or after it.
        :param until: ISO-8601 time; last activity at or before it.
        :param limit: Maximum number of Sessions per page (the API caps it at 200).
        :param cursor: The ``next`` value of the previous page.
        :returns: One page of Sessions.
        """
        params = {
            "origin": origin,
            "deployment_id": deployment_id,
            "pipeline_version_id": pipeline_version_id,
            "revision_id": revision_id,
            "from": since,
            "to": until,
            "limit": limit,
            "cursor": cursor,
        }
        path = await self._pipeline_path(pipeline_name, "sessions")
        data = await self._get(path, {k: v for k, v in params.items() if v is not None})
        return SessionList.model_validate(data or {"data": []})

    async def start_try(
        self, pipeline_name: str, python_code: str, session_id: str, test_case_id: str | None = None
    ) -> str:
        """Start an ad-hoc try of Evaluator source on one Session. Persists nothing.

        :param pipeline_name: Name of the pipeline.
        :param python_code: The Evaluation Function's source.
        :param session_id: The Session to judge.
        :param test_case_id: A Dataset test case whose `expected` data the Evaluation Function receives; omitted,
            the test case the Session replayed, if any.
        :returns: The try id to poll.
        """
        path = await self._pipeline_path(pipeline_name, "tries")
        body = {"python_code": python_code, "session_id": session_id}
        if test_case_id is not None:
            body["session_replay_test_case_id"] = test_case_id
        data = await self._post(path, body)
        return str(data["try_id"])

    async def get_try(self, pipeline_name: str, try_id: str) -> TryState:
        """Read an ad-hoc try: running (202), finished (200) or aged out (410).

        :param pipeline_name: Name of the pipeline.
        :param try_id: The id `start_try` returned.
        :returns: The try's state, with its result once finished.
        """
        path = await self._pipeline_path(pipeline_name, "tries", try_id)
        resp = await self._client.request(endpoint=path, method="GET")
        if resp.status_code == 202:
            return TryState(status="RUNNING")
        if resp.status_code == 410:
            return TryState(status="EXPIRED")
        raise_for_status(resp)
        return TryState(status="READY", result=EvaluationTryResult.model_validate(resp.json))

    async def start_session_replay(
        self,
        pipeline_name: str,
        session_id: str,
        pipeline_version_id: str,
        replay_mode: str | None = None,
        setup_source: str | None = None,
        cleanup_source: str | None = None,
    ) -> str:
        """Start replaying a Session against a pipeline version, a draft included.

        :param pipeline_name: Name of the pipeline.
        :param session_id: The Session to replay.
        :param pipeline_version_id: The pipeline version to replay it against.
        :param replay_mode: FIRST_USER_MESSAGE or ALL_USER_MESSAGES; omitted, the server's default.
        :param setup_source: Python source run before the pipeline; omitted, no setup step.
        :param cleanup_source: Python source run after the pipeline; omitted, no cleanup step.
        :returns: The replay run id to poll.
        """
        body = {"session_id": session_id, "pipeline_version_id": pipeline_version_id}
        optional = {"replay_mode": replay_mode, "setup_source": setup_source, "cleanup_source": cleanup_source}
        body.update({k: v for k, v in optional.items() if v is not None})
        data = await self._post(await self._pipeline_path(pipeline_name, "replay-runs"), body)
        return str(data["session_replay_run_id"])

    async def get_session_replay(self, pipeline_name: str, replay_run_id: str) -> SessionReplayRun:
        """Read a session replay run.

        :param pipeline_name: Name of the pipeline.
        :param replay_run_id: The id `start_session_replay` returned.
        :returns: The run.
        """
        path = await self._pipeline_path(pipeline_name, "replay-runs", replay_run_id)
        return SessionReplayRun.model_validate(await self._get(path))

    async def list_datasets(self, pipeline_name: str | None = None, limit: int = 50) -> list[DatasetSummary]:
        """List the workspace's Datasets without their test cases, newest first.

        :param pipeline_name: Only Datasets with a test case on this pipeline, when given.
        :param limit: Maximum number of Datasets to return (the API caps it at 200).
        :returns: The Datasets.
        """
        params: dict[str, Any] = {"limit": limit}
        if pipeline_name is None:
            path = await self._workspace_path("datasets")
        else:
            workspace_id, params["pipeline_id"] = await ids.workspace_and_pipeline_ids(
                self._client, self._workspace, pipeline_name
            )
            path = self._path(workspace_id, "evaluation", "datasets")
        return [DatasetSummary.model_validate(item) for item in await self._get(path, params) or []]

    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Fetch one Dataset with its test cases.

        :param dataset_id: The Dataset's id.
        :returns: The Dataset.
        """
        return Dataset.model_validate(await self._get(await self._workspace_path("datasets", dataset_id)))

    async def create_dataset(
        self, name: str, pipeline_name: str | None = None, test_cases: list[NewTestCase] | None = None
    ) -> Dataset:
        """Create a Dataset, optionally with its first test cases. Replays nothing.

        :param name: What the Dataset is called.
        :param pipeline_name: The pipeline the test cases' Sessions were recorded on; needed for Sessions.
        :param test_cases: The test cases to start with.
        :returns: The created Dataset.
        """
        body: dict[str, Any] = {"name": name}
        if pipeline_name is not None:
            body["pipeline_id"] = await ids.pipeline_id(self._client, self._workspace, pipeline_name)
        if test_cases:
            body["test_cases"] = _dump(test_cases)
        return Dataset.model_validate(await self._post(await self._workspace_path("datasets"), body))

    async def update_dataset(self, dataset_id: str, name: str) -> Dataset:
        """Rename a Dataset.

        :param dataset_id: The Dataset's id.
        :param name: The new name.
        :returns: The Dataset.
        """
        data = await self._put(await self._workspace_path("datasets", dataset_id), {"name": name})
        return Dataset.model_validate(data)

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a Dataset and its test cases.

        :param dataset_id: The Dataset's id.
        """
        await self._delete(await self._workspace_path("datasets", dataset_id))

    async def add_test_cases(
        self, dataset_id: str, test_cases: list[NewTestCase], pipeline_name: str | None = None
    ) -> Dataset:
        """Append test cases to a Dataset.

        :param dataset_id: The Dataset's id.
        :param test_cases: The test cases to add, in order.
        :param pipeline_name: The pipeline the test cases' Sessions were recorded on; needed for Sessions.
        :returns: The Dataset with all its test cases.
        """
        body: dict[str, Any] = {"test_cases": _dump(test_cases)}
        if pipeline_name is not None:
            body["pipeline_id"] = await ids.pipeline_id(self._client, self._workspace, pipeline_name)
        path = await self._workspace_path("datasets", dataset_id, "test-cases")
        return Dataset.model_validate(await self._post(path, body))

    async def copy_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        """Copy existing test cases, from any Dataset of the workspace, into a Dataset.

        :param dataset_id: The Dataset to copy into.
        :param test_case_ids: The test cases to copy, in order.
        :returns: The Dataset with all its test cases.
        """
        path = await self._workspace_path("datasets", dataset_id, "test-cases", "copy")
        return Dataset.model_validate(await self._post(path, {"session_replay_test_case_ids": test_case_ids}))

    async def remove_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        """Remove test cases from a Dataset. Ids it does not hold are ignored.

        :param dataset_id: The Dataset's id.
        :param test_case_ids: The test cases to remove.
        :returns: The Dataset with the test cases left.
        """
        path = await self._workspace_path("datasets", dataset_id, "test-cases", "remove")
        return Dataset.model_validate(await self._post(path, {"session_replay_test_case_ids": test_case_ids}))

    async def update_test_case(self, dataset_id: str, test_case_id: str, changes: dict[str, Any]) -> TestCase:
        """Change one test case. A field left out of ``changes`` is kept; one sent as None is removed.

        :param dataset_id: The Dataset's id.
        :param test_case_id: The test case's id.
        :param changes: The fields to change: name, inputs, expected, setup_source, cleanup_source.
        :returns: The test case.
        """
        path = await self._workspace_path("datasets", dataset_id, "test-cases", test_case_id)
        return TestCase.model_validate(await self._put(path, changes))

    async def create_evaluator(
        self,
        name: str,
        python_code: str,
        metric_group_ids: list[str] | None = None,
        new_metric_group_name: str | None = None,
    ) -> Evaluator:
        """Create an Evaluator and its first version, optionally adding it to Metric Groups.

        :param name: The Evaluator's name; unused in the workspace.
        :param python_code: The Evaluation Function's source.
        :param metric_group_ids: Existing Metric Groups to add it to, each at the end of its set.
        :param new_metric_group_name: Creates a Metric Group of this name with the Evaluator as its only member.
        :returns: The created Evaluator.
        """
        body: dict[str, Any] = {"name": name, "python_code": python_code}
        if metric_group_ids:
            body["metric_group_ids"] = metric_group_ids
        if new_metric_group_name is not None:
            body["new_metric_group_name"] = new_metric_group_name
        return Evaluator.model_validate(await self._post(await self._evaluators_path(), body))

    async def update_evaluator(
        self, evaluator_id: str, name: str | None = None, python_code: str | None = None
    ) -> Evaluator:
        """Rename an Evaluator, add a version of its source, or both. Only the fields given are sent.

        :param evaluator_id: The Evaluator's id.
        :param name: The new name.
        :param python_code: The new source; adds a version unless the lineage already holds it.
        :returns: The Evaluator.
        """
        changes = {k: v for k, v in (("name", name), ("python_code", python_code)) if v is not None}
        return Evaluator.model_validate(await self._put(await self._evaluators_path(evaluator_id), changes))

    async def set_evaluator_archived(self, evaluator_id: str, archived: bool) -> Evaluator:
        """Archive or unarchive an Evaluator.

        :param evaluator_id: The Evaluator's id.
        :param archived: True to archive it, False to unarchive it.
        :returns: The Evaluator.
        """
        path = await self._evaluators_path(evaluator_id, "archive" if archived else "unarchive")
        return Evaluator.model_validate(await self._post(path, {}))

    async def list_evaluator_templates(self) -> list[EvaluatorTemplate]:
        """List the built-in Evaluator templates, each with its code.

        :returns: The templates.
        """
        data = await self._get(await self._workspace_path("evaluator-templates"))
        return [EvaluatorTemplate.model_validate(item) for item in data or []]

    async def create_metric_group(
        self, name: str, evaluator_ids: list[str], weights: list[MetricWeight] | None = None
    ) -> MetricGroup:
        """Create a Metric Group of Evaluators, optionally with Metric weights.

        :param name: The Metric Group's name.
        :param evaluator_ids: The Evaluators it runs, in order.
        :param weights: How much each Metric counts toward the Composite; none by default.
        :returns: The created Metric Group.
        """
        body = _metric_group_body(name, evaluator_ids, weights)
        return MetricGroup.model_validate(await self._post(await self._workspace_path("metric-groups"), body))

    async def update_metric_group(
        self, metric_group_id: str, name: str, evaluator_ids: list[str], weights: list[MetricWeight] | None = None
    ) -> MetricGroup:
        """Replace a Metric Group's name and Evaluator set; weights only when given.

        :param metric_group_id: The Metric Group's id.
        :param name: The name to keep or change to.
        :param evaluator_ids: Every Evaluator the group keeps, in order.
        :param weights: Replaces the weights (an empty list clears them); None keeps those of the Evaluators that stay.
        :returns: The Metric Group.
        """
        body = _metric_group_body(name, evaluator_ids, weights)
        path = await self._workspace_path("metric-groups", metric_group_id)
        return MetricGroup.model_validate(await self._put(path, body))

    async def delete_metric_group(self, metric_group_id: str) -> None:
        """Delete a Metric Group and its Experiment runs. The Evaluators stay.

        :param metric_group_id: The Metric Group's id.
        """
        await self._delete(await self._workspace_path("metric-groups", metric_group_id))
