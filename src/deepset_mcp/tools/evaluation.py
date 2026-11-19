# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for evaluation: Evaluators, Evaluation goals and their scoring runs, Datasets, Experiments, and Sessions."""

import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from statistics import fmean
from typing import Any, Literal, TypeVar

from deepset_mcp.api.evaluation.models import (
    Dataset,
    DatasetSummary,
    EvaluateGoalsAccepted,
    EvaluationGoal,
    EvaluationRun,
    Evaluator,
    EvaluatorTemplate,
    EvaluatorVersion,
    Experiment,
    ExperimentDetail,
    ExperimentResultsReport,
    ExperimentRun,
    ExperimentRunGrid,
    ExperimentRunReport,
    ExperimentUpdatePlan,
    GoalAggregation,
    GoalCategory,
    GoalExperimentStarted,
    GoalRunDataset,
    GoalRunPreview,
    GoalRunSource,
    GoalRunSummary,
    MetricSummary,
    NewTestCase,
    ReportCell,
    ReportRow,
    SessionList,
    SessionReplayRun,
    TestCase,
    TraceSummary,
    TryReport,
    TryState,
)
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_evaluators(
    *, client: AsyncClientProtocol, workspace: str, limit: int = 200, archived: bool | None = None
) -> list[Evaluator] | str:
    """Lists the Evaluators in the workspace.

    An Evaluator is a versioned Python function that judges a Session and reports named Metrics.
    Each entry carries its newest version's id and the Metrics that version declares (name, shape,
    grain and, for a closed Label, its vocabulary and, if it declares one, its ``scale``; for a
    Score, its ``range`` and ``better``), but not the source. Evaluators belong to the workspace,
    not to a pipeline; a pipeline's Evaluation goals pick the Metrics its scoring runs judge. The API has no
    paging: a result of exactly ``limit`` Evaluators may be cut off, and Evaluators past the 200 cap
    are reachable only by splitting the list with ``archived``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param limit: Most Evaluators to return (at most 200).
    :param archived: ``true`` for only archived Evaluators, ``false`` for only the others; omit for both.
    :returns: The Evaluators, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_evaluators(limit, archived)
    except ResourceNotFoundError:
        return f"Workspace '{workspace}' not found."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list evaluators in workspace '{workspace}': {e}"


async def get_evaluator(
    *, client: AsyncClientProtocol, workspace: str, evaluator_id: str, version_id: str | None = None
) -> Evaluator | EvaluatorVersion | str:
    """Fetches one Evaluator, or one of its versions with the Python source.

    Without ``version_id`` it returns the Evaluator with every version, newest first, each with
    the Metrics it declares but no source. With ``version_id`` it returns that version including
    its ``python_code``; pass ``latest_version.evaluator_version_id`` to read the current source.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param evaluator_id: The Evaluator's id.
    :param version_id: A version's id, to read that version's source.
    :returns: The Evaluator or the version, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        if version_id is not None:
            return await resource.get_evaluator_version(evaluator_id, version_id)
        return await resource.get_evaluator(evaluator_id)
    except ResourceNotFoundError:
        target = f"Version '{version_id}' of evaluator" if version_id else "Evaluator"
        return f"{target} '{evaluator_id}' not found in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to get evaluator '{evaluator_id}': {e}"


async def list_evaluation_goals(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str
) -> list[EvaluationGoal] | str:
    """Lists the Evaluation Goals set on one pipeline, oldest first.

    An Evaluation Goal is a pass/fail target on one pipeline, built on one Evaluator's Metric:
    ``threshold`` is the value a Session must reach for a Score Metric, ``passing_values`` the labels
    that count as passing for a Label Metric (exactly one of them is set), and ``min_pass_rate`` the
    share of judged Sessions that must pass for the goal to be met. Call this before suggesting new
    goals, so goals that already exist are not proposed again. The API has no paging.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline whose goals to list.
    :returns: The Evaluation Goals, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        return await resource.list_evaluation_goals(pipeline_name)
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}' (not found)."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list evaluation goals for pipeline '{pipeline_name}' in workspace '{workspace}': {e}"


async def create_evaluation_goal(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    name: str,
    evaluator_id: str,
    description: str = "",
    threshold: float | None = None,
    passing_values: list[str] | None = None,
    min_pass_rate: float = 1.0,
    category: GoalCategory | None = None,
    aggregation: GoalAggregation | None = None,
    percentile: float | None = None,
) -> EvaluationGoal | str:
    """Creates an Evaluation goal: a pass/fail target on one pipeline.

    Call ``list_evaluation_goals`` first so a goal is not created twice, and ``get_evaluator`` to see
    the Metrics the Evaluator declares.

    A goal reads one Metric of one Evaluator. For a Score Metric set ``threshold``: a Session passes
    when the mean of its rows reaches it (at least if the Score is better when higher, at most if
    lower). For a Label Metric set ``passing_values`` instead: a Session passes when every one of its
    rows is one of those labels. Set exactly one of the two. ``min_pass_rate`` (0 to 1, default 1) is
    the share of valued Sessions that must pass for the goal to be met. ``aggregation`` changes how
    the verdict is made: ``pass_rate`` (default) uses ``min_pass_rate``; ``mean`` needs the mean of
    the Session values to reach ``threshold``; ``percentile`` needs the ``percentile`` (between 0 and
    100, for example 95) of the Session values to reach it. ``mean`` and ``percentile`` take a Score
    Metric only. The ``percentile`` number is required with aggregation ``percentile`` and refused otherwise.
    ``category`` (SAFETY, QUALITY, EFFICIENCY, COST or MISC) groups goals in the UI.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline the goal is set on.
    :param name: What the goal is called.
    :param evaluator_id: The Evaluator whose Metric the goal reads.
    :param description: Why the goal matters.
    :param threshold: For a Score Metric: the value a Session must reach.
    :param passing_values: For a Label Metric: the labels that pass.
    :param min_pass_rate: Share (0 to 1) of valued Sessions that must pass.
    :param category: What the goal is about; the API picks one when omitted.
    :param aggregation: How Session values fold into a verdict; ``pass_rate`` when omitted.
    :param percentile: Which percentile, with aggregation ``percentile``.
    :returns: The new goal, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).create_evaluation_goal(
            pipeline_name,
            name,
            evaluator_id,
            description=description,
            threshold=threshold,
            passing_values=passing_values,
            min_pass_rate=min_pass_rate,
            category=category,
            aggregation=aggregation,
            percentile=percentile,
        )
    except _API_ERRORS as e:
        return f"Failed to create evaluation goal '{name}' on pipeline '{pipeline_name}': {e}"


async def get_evaluation_goal(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, evaluation_goal_id: str
) -> EvaluationGoal | str:
    """Reads one Evaluation goal of a pipeline, with its rule, category and aggregation.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param evaluation_goal_id: The goal's id, from ``list_evaluation_goals``.
    :returns: The goal, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).get_evaluation_goal(pipeline_name, evaluation_goal_id)
    except _API_ERRORS as e:
        return f"Failed to get evaluation goal '{evaluation_goal_id}' on pipeline '{pipeline_name}': {e}"


async def update_evaluation_goal(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    evaluation_goal_id: str,
    name: str,
    evaluator_id: str,
    description: str = "",
    threshold: float | None = None,
    passing_values: list[str] | None = None,
    min_pass_rate: float = 1.0,
    category: GoalCategory | None = None,
    aggregation: GoalAggregation | None = None,
    percentile: float | None = None,
) -> EvaluationGoal | str:
    """Replaces an Evaluation goal: it does not merge, so send every field, not only the changed ones.

    Read the goal with ``get_evaluation_goal`` first and send back the fields you keep. A field left
    out is reset to its default (``description`` empty, ``min_pass_rate`` 1, no ``threshold``), except
    ``category`` and ``aggregation``, which stay as they were.

    A goal reads one Metric of one Evaluator. For a Score Metric set ``threshold``: a Session passes
    when the mean of its rows reaches it (at least if the Score is better when higher, at most if
    lower). For a Label Metric set ``passing_values`` instead: a Session passes when every one of its
    rows is one of those labels. Set exactly one of the two. ``min_pass_rate`` (0 to 1, default 1) is
    the share of valued Sessions that must pass for the goal to be met. ``aggregation`` changes how
    the verdict is made: ``pass_rate`` (default) uses ``min_pass_rate``; ``mean`` needs the mean of
    the Session values to reach ``threshold``; ``percentile`` needs the ``percentile`` (between 0 and
    100, for example 95) of the Session values to reach it. ``mean`` and ``percentile`` take a Score
    Metric only. The ``percentile`` number is required with aggregation ``percentile`` and refused otherwise.
    ``category`` (SAFETY, QUALITY, EFFICIENCY, COST or MISC) groups goals in the UI.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param evaluation_goal_id: The goal's id.
    :param name: What the goal is called.
    :param evaluator_id: The Evaluator whose Metric the goal reads.
    :param description: Why the goal matters.
    :param threshold: For a Score Metric: the value a Session must reach.
    :param passing_values: For a Label Metric: the labels that pass.
    :param min_pass_rate: Share (0 to 1) of valued Sessions that must pass.
    :param category: What the goal is about; kept as it was when omitted.
    :param aggregation: How Session values fold into a verdict; kept as it was when omitted.
    :param percentile: Which percentile, with aggregation ``percentile``.
    :returns: The goal as saved, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).update_evaluation_goal(
            pipeline_name,
            evaluation_goal_id,
            name,
            evaluator_id,
            description=description,
            threshold=threshold,
            passing_values=passing_values,
            min_pass_rate=min_pass_rate,
            category=category,
            aggregation=aggregation,
            percentile=percentile,
        )
    except _API_ERRORS as e:
        return f"Failed to update evaluation goal '{evaluation_goal_id}' on pipeline '{pipeline_name}': {e}"


async def delete_evaluation_goal(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, evaluation_goal_id: str
) -> str:
    """Deletes an Evaluation goal (destructive).

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param evaluation_goal_id: The goal's id.
    :returns: A confirmation, or an error message.
    """
    try:
        await client.evaluation(workspace=workspace).delete_evaluation_goal(pipeline_name, evaluation_goal_id)
    except _API_ERRORS as e:
        return f"Failed to delete evaluation goal '{evaluation_goal_id}' on pipeline '{pipeline_name}': {e}"
    return f"Evaluation goal '{evaluation_goal_id}' deleted."


async def create_experiment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    name: str,
    dataset_id: str,
    candidate_pipeline_version_id: str,
    baseline_pipeline_version_id: str | None = None,
    sessions_per_test_case: int = 1,
    replay_mode: Literal["FIRST_USER_MESSAGE", "ALL_USER_MESSAGES"] = "FIRST_USER_MESSAGE",
    preview: bool = False,
) -> GoalExperimentStarted | GoalRunPreview | str:
    """Creates an Experiment that compares two versions of a pipeline against its Evaluation goals.

    Both sides are scored by the Evaluators of the pipeline's Evaluation goals over the test cases of
    one Dataset; the pipeline needs at least one goal (see ``list_evaluation_goals``). The candidate
    is a version of the pipeline that is replayed on each test case. The baseline is another version
    of the same pipeline (``baseline_pipeline_version_id``) or Recorded (leave it unset): a Recorded
    baseline reuses the Sessions each test case recorded, with nothing replayed.

    Creating costs money: it replays the pipeline on the customer's models, and then every Session
    is judged by the goals' Evaluators, which are billed when they use an LLM. Call it first with
    ``preview=True``: that starts nothing and returns ``judgments`` (test cases times Evaluators times
    ``sessions_per_test_case``, per side) against ``limit``, and ``replays`` each replayed side would
    start. Show that to the user and get a yes before creating for real. ``sessions_per_test_case``
    sets how many Sessions each side scores per test case (1..50). Find ``dataset_id`` with
    ``list_datasets``. Follow the Experiment with ``get_experiment`` and read it with
    ``get_experiment_results``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline whose versions are compared and whose goals score them.
    :param name: Human-readable name for the Experiment.
    :param dataset_id: The Dataset's id (the UI's Dataset dropdown).
    :param candidate_pipeline_version_id: The candidate pipeline version to replay.
    :param baseline_pipeline_version_id: Baseline version of the same pipeline; omit for a Recorded baseline.
    :param sessions_per_test_case: Repetitions per test case (1..50, default 1).
    :param replay_mode: FIRST_USER_MESSAGE replays the first turn only; ALL_USER_MESSAGES replays every turn.
    :param preview: True returns the counts and creates nothing.
    :returns: The new Experiment's and Dataset's ids, or with ``preview`` the counts, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        if preview:
            return await resource.preview_goal_run(
                pipeline_name,
                GoalRunDataset(kind="dataset", dataset_id=dataset_id),
                sessions_per_test_case=sessions_per_test_case,
            )
        return await resource.create_experiment(
            pipeline_name=pipeline_name,
            name=name,
            dataset_id=dataset_id,
            candidate_pipeline_version_id=candidate_pipeline_version_id,
            baseline_pipeline_version_id=baseline_pipeline_version_id,
            sessions_per_test_case=sessions_per_test_case,
            replay_mode=replay_mode,
        )
    except ResourceNotFoundError as e:
        return f"Could not create experiment: something it refers to was not found: {e}"
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to create experiment '{name}': {e}"


async def list_experiments(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str | None = None, limit: int = 50
) -> list[Experiment] | str:
    """Lists the workspace's Experiments, newest first.

    An Experiment compares a candidate pipeline version against a baseline on the test cases of one
    Dataset: each side gets its Sessions (reused, or replayed against its version) and is scored by
    the same Evaluators. The baseline is another version, or, when ``recorded``, the Sessions the
    Dataset recorded. ``status`` and each side's ``status`` go REPLAYING, SCORING, then ENDED or
    FAILED; a side's ``error`` says why it failed and ``scoring_counts`` how its evaluations ended.
    Read how the candidate did against the baseline with ``get_experiment_results``. To read one
    side's scoring run cell by cell, pass its ``scoring_runs[].experiment_run_id`` and that entry's
    ``pipeline_id`` resolved to a name with ``list_pipelines`` to ``get_experiment_run``. The API has no
    paging: a result of exactly
    ``limit`` Experiments may be cut off; raise ``limit`` (at most 200) or narrow with ``pipeline_name``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Only Experiments with either side on this pipeline, when given.
    :param limit: Most Experiments to return (at most 200).
    :returns: The Experiments, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_experiments(pipeline_name, limit)
    except ResourceNotFoundError:
        if pipeline_name is None:
            return f"Workspace '{workspace}' not found."
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}' (not found)."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list experiments in workspace '{workspace}': {e}"


async def get_experiment_results(
    *, client: AsyncClientProtocol, workspace: str, experiment_id: str, max_test_cases: int = 100
) -> ExperimentResultsReport | str:
    """Reads an Experiment's results: each Metric, candidate against baseline, then each test case.

    Find an Experiment with ``list_experiments``. ``metrics`` has one entry per Metric the
    Experiment scores, in its Evaluators' order: each side's ``value`` (or ``labels`` for a Label), ``delta`` and
    ``delta_pct`` of the candidate over the baseline, ``better`` (which way a change is an
    improvement, null when undeclared), ``change`` (improved, regressed, unchanged or unknown),
    and how many Sessions ``errored``, meaning the Evaluator's own code broke. A test case's value
    is the mean over its Sessions, and a Metric is averaged only over the ``paired_test_cases``
    both sides have a value for, so check that count before trusting a delta. Say a Metric
    improved or regressed only from ``change``; ``unknown`` means no judgement, so never infer a
    direction from the Metric's name. ``pipeline_metrics`` compares DURATION, TOKENS and COST the
    same way. Each test case lists the Sessions each side scored and, per Score Metric keyed
    ``{evaluator_id}:{metric_key}``, each side's mean; that is where to look for the test cases
    behind a regression. Resolve evaluator ids to names with ``list_evaluators``. Results are
    partial while ``status`` is REPLAYING or SCORING. ``headline`` gives each side's Composite
    (0 to 1, 1 best) and ``normalized_means``. When ``comparable`` is false the two sides used
    different formulas: report no change between them and give ``incomparable_reason``; each side's
    ``composite_weights`` shows the formula it used. ``aggregates`` gives each Metric over every Session
    a side scored, not just the paired test cases: each side's whole-run entry (a Score's ``mean``, a
    Label's ``shares``), ``delta``, ``share_deltas`` for a Label and ``change``. Empty until a side's
    scoring runs end.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id.
    :param max_test_cases: Most test cases to return; ``metrics`` still cover every test case.
    :returns: The results, or an error message.
    """
    try:
        results = await client.evaluation(workspace=workspace).get_experiment_results(experiment_id)
    except ResourceNotFoundError:
        return f"Experiment '{experiment_id}' not found in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to get results of experiment '{experiment_id}': {e}"
    return ExperimentResultsReport(
        **results.model_dump(exclude={"test_cases"}),
        test_cases=results.test_cases[:max_test_cases],
        total_test_cases=len(results.test_cases),
        test_cases_truncated=len(results.test_cases) > max_test_cases,
    )


async def get_experiment_run(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    run_id: str,
    max_rows: int = 100,
    origin: Literal["SERVICE", "PIPELINE_RUN", "PLAYGROUND"] | None = None,
    deployment_id: str | None = None,
    pipeline_version_id: str | None = None,
    session_id: str | None = None,
) -> ExperimentRunReport | str:
    """Reads one scoring run: how its cells ended, a summary per Metric, then the grid rows.

    A scoring run judges chosen Sessions of one pipeline with a set of Evaluators: an
    ``evaluate_goals`` run, or one side of an Experiment. Find one with ``list_experiment_runs``,
    ``evaluate_goals`` (``scoring_run_id``) or ``get_experiment`` (a side's ``experiment_run_id``).
    It judges each chosen Session with each Evaluator; one cell per pair. ``counts`` says how
    the cells ended: ``errored`` is the Evaluator's own code breaking (see the cell's
    ``error_detail``), not a low Metric; ``failed`` is a cell that never ran and can be retried.
    ``metrics`` summarises each Evaluator's Metric over every row, rows past ``max_rows``
    included: mean, min and max for a Score, a count per label for a Label, and how often it did
    not apply. Each row is a Session with its cells; a cell's ``metrics`` carry the value per
    address (``session``, ``turn/2``, ...) and the rationale the Evaluator wrote, which is what to
    group failures by. ``run.selection`` says whether the Sessions were SAMPLED or HAND_PICKED;
    only sampled runs say anything about traffic as a whole. ``composite`` is the run's single
    number, 0 to 1 with 1 best, from ``normalized_means`` (each Metric on that
    scale) weighted by ``run.composite_weights``, the formula the run started with. When it has
    no value it says ``reason`` and lists the Metrics that block it in ``missing``.
    ``aggregate`` is the API's whole-run result per Metric: how its Sessions fell out (``valued``,
    ``errored``, ``failed``, ``pending``, ...), ``coverage`` and the Metric's mean or label
    ``shares``, in the units it declares; it is null until the run ends. ``usage`` is what the
    pipeline spent on the run's Sessions (tokens, duration, ``cost`` in USD, null unless
    ``cost_status`` is ``priced``). ``evaluator_versions`` says which version of each Evaluator
    judged and what its Metrics declare. The filters keep only the cells whose Session's origin,
    Service or pipeline version match (a cell still running has no origin and matches none):
    they narrow ``counts``, ``rows`` and ``metrics``, but not ``aggregate``, ``usage``,
    ``normalized_means`` or ``composite``, which stay whole-run.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param run_id: The run's id.
    :param max_rows: Most rows to return; the summaries still cover every row.
    :param origin: Only cells whose Session came from a Service, the pipeline's own API, or the Playground.
    :param deployment_id: Only cells whose Session this Service served.
    :param pipeline_version_id: Only cells whose Session this pipeline version served.
    :param session_id: Only this Session's row.
    :returns: The run report, or an error message.
    """
    try:
        grid = await client.evaluation(workspace=workspace).get_experiment_run(
            pipeline_name,
            run_id,
            origin=origin,
            deployment_id=deployment_id,
            pipeline_version_id=pipeline_version_id,
            session_id=session_id,
        )
    except ResourceNotFoundError:
        return f"Run '{run_id}' on pipeline '{pipeline_name}' not found."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to get run '{run_id}': {e}"
    rows = [
        ReportRow(
            session_id=row.session_id,
            session_replay_run_id=row.session_replay_run_id,
            cells=[
                ReportCell(
                    evaluator_id=cell.evaluator_id,
                    status=cell.evaluation_run.status,
                    outcome=cell.evaluation_run.outcome,
                    evaluator_version_id=cell.evaluation_run.evaluator_version_id,
                    metrics=cell.evaluation_run.metrics,
                    error_detail=cell.evaluation_run.error_detail,
                )
                for cell in row.cells
            ],
        )
        for row in grid.rows
    ]
    return ExperimentRunReport(
        run=grid.run,
        evaluator_ids=grid.evaluator_ids,
        counts=grid.counts,
        metrics=_summarise(grid),
        aggregate=grid.aggregate,
        usage=grid.usage,
        evaluator_versions=grid.evaluator_versions,
        normalized_means=grid.normalized_means,
        composite=grid.composite,
        rows=rows[:max_rows],
        total_rows=len(rows),
        rows_truncated=len(rows) > max_rows,
    )


def _summarise(grid: ExperimentRunGrid) -> list[MetricSummary]:
    """Aggregate every value of each (Evaluator, Metric key) across the grid, in first-seen order."""
    scores: dict[tuple[str, str], list[float]] = {}
    labels: dict[tuple[str, str], Counter[str]] = {}
    not_applicable: Counter[tuple[str, str]] = Counter()
    for row in grid.rows:
        for cell in row.cells:
            for metric in cell.evaluation_run.metrics:
                key = (cell.evaluator_id, metric.metric_key)
                scores.setdefault(key, [])
                labels.setdefault(key, Counter())
                if metric.score is not None:
                    scores[key].append(metric.score)
                elif metric.label is not None:
                    labels[key][metric.label] += 1
                else:
                    not_applicable[key] += 1

    summaries = []
    for key, values in scores.items():
        kind: Literal["score", "label", "not_applicable"] = (
            "score" if values else "label" if labels[key] else "not_applicable"
        )
        summaries.append(
            MetricSummary(
                evaluator_id=key[0],
                metric_key=key[1],
                kind=kind,
                count=len(values) + labels[key].total(),
                mean=fmean(values) if values else None,
                min=min(values) if values else None,
                max=max(values) if values else None,
                labels=dict(labels[key]),
                not_applicable=not_applicable[key],
            )
        )
    return summaries


async def list_sessions(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    origin: Literal["SERVICE", "PIPELINE_RUN", "PLAYGROUND"] | None = None,
    deployment_id: str | None = None,
    pipeline_version_id: str | None = None,
    revision_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> SessionList | str:
    """Lists a pipeline's Sessions that a scoring run can judge, newest last activity first.

    A Session is the turns that share a ``search_session_id``; a run without one is a single-turn
    Session named by its ``query_id``. Only Sessions whose every turn still has its trace are
    listed. ``session_id`` is the id a scoring run takes. To find Sessions that went wrong
    (a failed turn, negative feedback), use ``list_pipeline_traces`` with an OData filter instead
    and take each row's ``search_session_id``, or its ``query_id`` when that is empty.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param origin: Only Sessions whose every turn came from a Service, the pipeline's own API, or the Playground.
    :param deployment_id: Only Sessions whose every turn this Service served.
    :param pipeline_version_id: Only Sessions whose every turn this pipeline version served.
    :param revision_id: Only Sessions whose every turn this Service revision served. Exact where a
        version is not: one version can be pushed to a Service more than once.
    :param since: ISO-8601 time; only Sessions last active at or after it.
    :param until: ISO-8601 time; only Sessions last active at or before it.
    :param limit: Most Sessions per page (at most 200). A page can hold fewer and still have a ``next``.
    :param cursor: The ``next`` value of the previous page.
    :returns: One page of Sessions, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_sessions(
            pipeline_name,
            origin=origin,
            deployment_id=deployment_id,
            pipeline_version_id=pipeline_version_id,
            revision_id=revision_id,
            since=since,
            until=until,
            limit=limit,
            cursor=cursor,
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}' (not found)."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list sessions for pipeline '{pipeline_name}': {e}"


# ---------------------------------------------------------------------------------------------
# Checks: the ad-hoc try
# ---------------------------------------------------------------------------------------------

POLL_INTERVAL_SECONDS = 2.0
RUN_DONE_STATUSES = frozenset({"ENDED", "FAILED"})
TOOL_NAME_TAG = "haystack.tool.name"

_State = TypeVar("_State")


async def _poll(
    read: Callable[[], Awaitable[_State]], is_done: Callable[[_State], bool], wait_seconds: float
) -> _State:
    """Read until done or until the wait runs out, and return the last state read."""
    deadline = time.monotonic() + wait_seconds
    state = await read()
    while not is_done(state) and time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        state = await read()
    return state


def _trace_summary(trace: dict[str, Any] | None) -> TraceSummary | None:
    """The Session Tools an evaluator called and whether it failed, without the content it read."""
    if trace is None:
        return None
    spans = trace.get("traces")
    names = (
        [
            span["tags"][TOOL_NAME_TAG]
            for span in spans
            if isinstance(span, dict) and isinstance((span.get("tags") or {}).get(TOOL_NAME_TAG), str)
        ]
        if isinstance(spans, list)
        else []
    )
    status = trace.get("status")
    return TraceSummary(tool_calls=names, failed=status is not None and status != "success")


def _try_report(try_id: str, state: TryState) -> TryReport:
    result = state.result
    if result is None:
        return TryReport(status=state.status, try_id=try_id)
    return TryReport(
        status=state.status,
        try_id=try_id,
        session_id=result.session_id,
        outcome=result.outcome,
        metrics=result.metrics,
        trace_ids=result.trace_ids,
        trace_summary=_trace_summary(result.trace),
        error_detail=result.error_detail,
    )


async def try_evaluator(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    python_code: str,
    session_id: str,
    test_case_id: str | None = None,
    wait_seconds: int = 120,
) -> TryReport | str:
    """Tries Evaluator source on one Session and returns what it found. Persists nothing.

    Use it to check a draft before showing it as ready, and to judge a replayed Session against
    its source. The source is an Evaluation Function: a Python function that reads one Session and
    reports named Metrics declared with ``@metrics``. To try a saved Evaluator, read a version's
    ``python_code`` with ``get_evaluator`` and pass it. A try that
    judges with a model costs a model call per judged turn on the customer's provider.

    ``test_case_id`` hands the Evaluation Function that Dataset test case's ``expected`` data, so a
    correctness Evaluator can be tried on any Session; leave it out to use the test case the Session
    replayed, if any.

    ``outcome`` ERRORED means the code broke: read ``error_detail`` and fix it. ``metrics`` are the
    values per address with their rationales. ``trace_summary`` says which Session Tools the
    evaluator called. If ``status`` is RUNNING the wait ran out: poll ``get_evaluation_try``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline the Session belongs to.
    :param python_code: The Evaluation Function's source.
    :param session_id: The Session to judge: a ``search_session_id``, or a single-turn run's ``query_id``.
    :param test_case_id: A Dataset test case whose ``expected`` data the Evaluation Function receives.
    :param wait_seconds: How long to wait for the result before handing back the id to poll.
    :returns: The try report, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        try_id = await resource.start_try(pipeline_name, python_code, session_id, test_case_id)
        state = await _poll(
            lambda: resource.get_try(pipeline_name, try_id), lambda s: s.status != "RUNNING", wait_seconds
        )
    except ResourceNotFoundError:
        return f"Pipeline '{pipeline_name}' or Session '{session_id}' not found in workspace '{workspace}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to try the evaluator on Session '{session_id}': {e}"
    return _try_report(try_id, state)


async def get_evaluation_try(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, try_id: str
) -> TryReport | str:
    """Reads an ad-hoc try that ``try_evaluator`` handed back while it was still running.

    EXPIRED means the result aged out (tries are kept for an hour): run ``try_evaluator`` again.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param try_id: The ``try_id`` from ``try_evaluator``.
    :returns: The try report, or an error message.
    """
    try:
        state = await client.evaluation(workspace=workspace).get_try(pipeline_name, try_id)
    except ResourceNotFoundError:
        return f"Try '{try_id}' not found for pipeline '{pipeline_name}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to read try '{try_id}': {e}"
    return _try_report(try_id, state)


async def replay_session(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    session_id: str,
    pipeline_version_id: str,
    replay_mode: Literal["FIRST_USER_MESSAGE", "ALL_USER_MESSAGES"] | None = None,
    setup_source: str | None = None,
    cleanup_source: str | None = None,
    wait_seconds: int = 300,
) -> SessionReplayRun | str:
    """Replays one Session against a pipeline version into a new Session. Costs money.

    Experiment support, for when you need it: to reproduce or retry the replay of one test case
    that failed or looks wrong, replay that test case's Session on the version the Experiment's side
    uses. It is a paid pipeline run on the customer's models: say what it costs and get a yes first.
    The replay is not linked to the Experiment, so the new Session is not added to it and changes none
    of its results. To retry an Experiment's failed replays inside the Experiment, use
    ``rerun_failed_experiment`` with ``rerun="replays"``. The source Session and the deployed pipeline
    are untouched.

    FIRST_USER_MESSAGE replays the first turn only; ALL_USER_MESSAGES replays every turn of a chat in
    order. Leave it unset to use the server's default (the first turn), and say so when reporting.
    The run's ``session_id`` is the new Session; judge it with ``try_evaluator``. If ``status`` is
    still CREATED or STARTED the wait ran out: poll ``get_session_replay`` with its
    ``session_replay_run_id``. When it is FAILED, read ``error_detail`` and the logs.

    ``setup_source`` and ``cleanup_source`` are optional Python run around the pipeline in an isolated
    worker. Setup must define exactly one public top-level function taking no arguments and returning a
    mapping with optional ``env`` (dict[str, str]), ``inputs`` (dict[str, Any], keyed by the pipeline's
    declared input names) and ``logs`` (list[str]); its ``env`` and ``inputs`` take precedence over the
    Session's own. Cleanup runs even when the replay failed; it must define one public top-level function
    taking the setup's return value (None without a setup) and returning a mapping with optional ``logs``.
    Helpers must be underscore-prefixed or imported. Omit either to skip that step.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param session_id: The Session to replay: a ``search_session_id``, or a single-turn run's ``query_id``.
    :param pipeline_version_id: The pipeline version to replay against, e.g. the Experiment side's version.
    :param replay_mode: FIRST_USER_MESSAGE or ALL_USER_MESSAGES; unset uses the server's default.
    :param setup_source: Python source run before the pipeline; unset skips the step.
    :param cleanup_source: Python source run after the pipeline; unset skips the step.
    :param wait_seconds: How long to wait for the replay before handing back the run to poll.
    :returns: The replay run, with the new Session's ``session_id``, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        run_id = await resource.start_session_replay(
            pipeline_name, session_id, pipeline_version_id, replay_mode, setup_source, cleanup_source
        )
        return await _poll(
            lambda: resource.get_session_replay(pipeline_name, run_id),
            lambda r: r.status in RUN_DONE_STATUSES,
            wait_seconds,
        )
    except ResourceNotFoundError:
        return (
            f"Pipeline '{pipeline_name}', Session '{session_id}' or version '{pipeline_version_id}' "
            f"not found in workspace '{workspace}'."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to replay Session '{session_id}': {e}"


async def get_session_replay(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, replay_run_id: str
) -> SessionReplayRun | str:
    """Reads one replay run. Free to call.

    Experiment support, for when you need it: to see why an Experiment's replay failed or looks wrong,
    read its run. Get the id from a row's ``session_replay_run_id`` in ``get_experiment_run`` (the row
    is the Session the replay produced), or from ``replay_session``. The run has ``status`` (CREATED,
    STARTED, ENDED or FAILED), ``error_detail`` when it failed, ``setup_logs`` and ``cleanup_logs`` from
    the setup and cleanup steps, ``session_id`` (the new Session the replay produced), ``source_session_id``
    (the Session it replayed), ``test_case_id`` (the Dataset test case it was for, if any), and the
    ``trace_ids`` it produced. Only a FAILED run is retryable, with ``rerun_failed_experiment``
    (``rerun="replays"``).

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param replay_run_id: The replay run's ``session_replay_run_id``.
    :returns: The replay run, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).get_session_replay(pipeline_name, replay_run_id)
    except ResourceNotFoundError:
        return f"Replay '{replay_run_id}' not found for pipeline '{pipeline_name}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to read replay '{replay_run_id}': {e}"


_API_ERRORS = (ResourceNotFoundError, BadRequestError, UnexpectedAPIError)


async def list_datasets(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str | None = None, limit: int = 50
) -> list[DatasetSummary] | str:
    """Lists the workspace's Datasets, newest first, without their test cases.

    A Dataset is a named list of test cases (a recorded Session or a set of inputs, with optional
    expected data) that an Experiment replays against a pipeline version. Each entry has its
    ``dataset_id``, ``test_case_count`` and the ``pipeline_ids`` its test cases belong to. Read the
    test cases with ``get_dataset``; pass ``dataset_id`` to ``create_experiment``. The API has no
    paging: a result of exactly ``limit`` Datasets may be cut off; raise ``limit`` (at most 200) or
    narrow with ``pipeline_name``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Only Datasets with a test case on this pipeline, when given.
    :param limit: Most Datasets to return (at most 200).
    :returns: The Datasets, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_datasets(pipeline_name, limit)
    except _API_ERRORS as e:
        return f"Failed to list datasets: {e}"


async def get_dataset(*, client: AsyncClientProtocol, workspace: str, dataset_id: str) -> Dataset | str:
    """Fetches one Dataset with all its test cases, in the order an Experiment replays them.

    Each test case has its ``test_case_id`` (for ``update_test_case``, ``copy_test_cases`` and
    ``remove_test_cases``), the ``session_id`` it replays or the ``inputs`` it sends, its ``expected``
    data and its setup and cleanup source.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :returns: The Dataset, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).get_dataset(dataset_id)
    except _API_ERRORS as e:
        return f"Failed to get dataset '{dataset_id}': {e}"


async def create_dataset(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    name: str,
    pipeline_name: str | None = None,
    test_cases: list[NewTestCase] | None = None,
) -> Dataset | str:
    """Creates a Dataset, optionally with its first test cases. Replays nothing and costs nothing.

    Each test case is either a recorded Session (``session_id``, find them with ``list_sessions``)
    or ``inputs`` to send to the pipeline, never both. A Session needs ``pipeline_name``, the
    pipeline it was recorded on. A Session sent twice becomes one test case. Add more later with
    ``add_test_cases``. Then run it with ``create_experiment`` using the returned ``dataset_id``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: What the Dataset is called.
    :param pipeline_name: The pipeline the Sessions were recorded on; required when a test case has a ``session_id``.
    :param test_cases: The test cases to start with; none by default.
    :returns: The created Dataset, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).create_dataset(name, pipeline_name, test_cases)
    except _API_ERRORS as e:
        return f"Failed to create dataset '{name}': {e}"


async def update_dataset(*, client: AsyncClientProtocol, workspace: str, dataset_id: str, name: str) -> Dataset | str:
    """Renames a Dataset. Change its test cases with the test case tools.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :param name: The new name.
    :returns: The Dataset, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).update_dataset(dataset_id, name)
    except _API_ERRORS as e:
        return f"Failed to rename dataset '{dataset_id}': {e}"


async def delete_dataset(*, client: AsyncClientProtocol, workspace: str, dataset_id: str) -> str:
    """Deletes a Dataset and all its test cases. This cannot be undone: get a yes first.

    Experiments that used the Dataset keep their results but lose the link to it. hub-api refuses with a
    message while something else still uses the Dataset; relay that message.
    Afterwards every Experiment that used the Dataset can no longer change sides or rerun failed replays
    (hub-api answers 409).

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :returns: A confirmation, or an error message.
    """
    try:
        await client.evaluation(workspace=workspace).delete_dataset(dataset_id)
    except _API_ERRORS as e:
        return f"Failed to delete dataset '{dataset_id}': {e}"
    return f"Dataset '{dataset_id}' deleted."


async def add_test_cases(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    dataset_id: str,
    test_cases: list[NewTestCase],
    pipeline_name: str | None = None,
) -> Dataset | str:
    """Adds test cases to the end of a Dataset. Replays nothing and costs nothing.

    Each test case is either a recorded Session (``session_id``) or ``inputs``, never both. A
    Session needs ``pipeline_name``. A Session the Dataset already holds is skipped. To reuse test
    cases from another Dataset use ``copy_test_cases``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :param test_cases: The test cases to add, in order.
    :param pipeline_name: The pipeline the Sessions were recorded on; required when a test case has a ``session_id``.
    :returns: The Dataset with all its test cases, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).add_test_cases(dataset_id, test_cases, pipeline_name)
    except _API_ERRORS as e:
        return f"Failed to add test cases to dataset '{dataset_id}': {e}"


async def update_test_case(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    dataset_id: str,
    test_case_id: str,
    name: str | None = None,
    inputs: dict[str, Any] | None = None,
    expected: dict[str, Any] | None = None,
    setup_source: str | None = None,
    cleanup_source: str | None = None,
    clear: list[Literal["expected", "setup_source", "cleanup_source"]] | None = None,
) -> TestCase | str:
    """Changes one test case of a Dataset. Fields you leave out are kept.

    ``inputs`` replaces the inputs and works only on a test case created with ``inputs``, not on a
    Session-based one. ``expected`` replaces the expected data.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :param test_case_id: The test case's id.
    :param name: The new name.
    :param inputs: The new pipeline inputs, as ``{name: value}``.
    :param expected: The new expected data.
    :param setup_source: New Python source that runs before every replay.
    :param cleanup_source: New Python source that runs after every replay.
    :param clear: Fields to remove from the test case.
    :returns: The test case, or an error message.
    """
    changes: dict[str, Any] = {
        field: value
        for field, value in (
            ("name", name),
            ("inputs", inputs),
            ("expected", expected),
            ("setup_source", setup_source),
            ("cleanup_source", cleanup_source),
        )
        if value is not None
    }
    conflict = sorted(set(clear or []) & changes.keys())
    if conflict:
        return f"Cannot both set and clear {', '.join(conflict)}: give a new value or list it in clear, not both."
    changes.update(dict.fromkeys(clear or []))
    if not changes:
        return (
            "Nothing to change: give a new value for name, inputs, expected, setup_source or cleanup_source, or clear."
        )
    try:
        return await client.evaluation(workspace=workspace).update_test_case(dataset_id, test_case_id, changes)
    except _API_ERRORS as e:
        return f"Failed to update test case '{test_case_id}': {e}"


async def copy_test_cases(
    *, client: AsyncClientProtocol, workspace: str, dataset_id: str, test_case_ids: list[str]
) -> Dataset | str:
    """Copies test cases from any Dataset of the workspace to the end of this one.

    Each copy keeps the Session or inputs, name, expected data and scripts, and gets its own id, so
    editing a copy leaves the original untouched. Find ids with ``get_dataset``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset to copy into.
    :param test_case_ids: The test cases to copy, in order.
    :returns: The Dataset with all its test cases, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).copy_test_cases(dataset_id, test_case_ids)
    except _API_ERRORS as e:
        return f"Failed to copy test cases into dataset '{dataset_id}': {e}"


async def remove_test_cases(
    *, client: AsyncClientProtocol, workspace: str, dataset_id: str, test_case_ids: list[str]
) -> Dataset | str:
    """Removes test cases from a Dataset. Destructive: the removed test cases are gone, so get a yes first.

    Ids that are not in the Dataset are ignored.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param dataset_id: The Dataset's id.
    :param test_case_ids: The test cases to remove.
    :returns: The Dataset with the test cases left, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).remove_test_cases(dataset_id, test_case_ids)
    except _API_ERRORS as e:
        return f"Failed to remove test cases from dataset '{dataset_id}': {e}"


async def create_evaluator(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    name: str,
    python_code: str,
) -> Evaluator | str:
    """Creates an Evaluator from Python source and adds it to the workspace. Judged Metrics cost money when run.

    Always validate new code first: run it on a real Session with ``try_evaluator`` and fix what it
    reports before saving. ``python_code`` is the Evaluation Function; its ``@metrics`` declaration
    names the Metrics it reports, and hub-api rejects code whose declaration it cannot read. Start
    from ``list_evaluator_templates`` rather than from scratch. The name must be unused in the
    workspace. The Evaluator judges a pipeline's scoring runs once one of its Metrics backs an
    Evaluation goal of that pipeline (see ``list_evaluation_goals``); until then run it on a Session
    with ``run_evaluator``. Change it later with ``update_evaluator``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: The Evaluator's name; must not exist in the workspace yet.
    :param python_code: The Evaluation Function's Python source.
    :returns: The created Evaluator, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).create_evaluator(name, python_code)
    except _API_ERRORS as e:
        return f"Failed to create evaluator '{name}': {e}"


async def update_evaluator(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    evaluator_id: str,
    name: str | None = None,
    python_code: str | None = None,
) -> Evaluator | str:
    """Renames an Evaluator, saves new source as a new version, or both. Send only what changes.

    New source adds a version; Evaluation goals built on the Evaluator judge with the newest version
    from the next run on, and past runs keep the version they used. Validate the new code with
    ``try_evaluator`` first. Source the Evaluator already had in its history adds no version, so
    reverting is safe. hub-api rejects code that changes what an existing Metric measures (its shape,
    grain or range, a narrowed vocabulary); a declaration that drops a Metric leaves a goal built on it
    without a value: check ``list_evaluation_goals`` afterwards. Read the current source with ``get_evaluator``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param evaluator_id: The Evaluator's id.
    :param name: The new name; must not be taken.
    :param python_code: The new Python source.
    :returns: The Evaluator, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).update_evaluator(evaluator_id, name, python_code)
    except _API_ERRORS as e:
        return f"Failed to update evaluator '{evaluator_id}': {e}"


async def set_evaluator_archived(
    *, client: AsyncClientProtocol, workspace: str, evaluator_id: str, archived: bool
) -> Evaluator | str:
    """Archives or unarchives an Evaluator. Nothing is deleted.

    An archived Evaluator keeps its versions and name, and Evaluation goals built on it still score
    with it; it only shows an ``archived_at`` time. Use it to retire an Evaluator without breaking history.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param evaluator_id: The Evaluator's id.
    :param archived: True to archive it, False to unarchive it.
    :returns: The Evaluator, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).set_evaluator_archived(evaluator_id, archived)
    except _API_ERRORS as e:
        return f"Failed to {'archive' if archived else 'unarchive'} evaluator '{evaluator_id}': {e}"


async def list_evaluator_templates(*, client: AsyncClientProtocol, workspace: str) -> list[EvaluatorTemplate] | str:
    """Lists the built-in Evaluator templates: ready-made Evaluation Functions to start from.

    They cover agent efficiency, agent quality, RAG quality and retrieval quality. Each has a ``key``,
    ``name``, ``category``, its ``python_code`` and the Metrics it declares. A template with a
    ``judge_model`` asks a model per Session, so running it costs money. ``expected_columns`` are the
    columns of a Dataset test case's expected data it reads. To use one, pass its ``name`` and
    ``python_code`` to ``create_evaluator``; the copy is yours and does not follow the template.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :returns: The templates, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_evaluator_templates()
    except _API_ERRORS as e:
        return f"Failed to list evaluator templates: {e}"


async def get_experiment(*, client: AsyncClientProtocol, workspace: str, experiment_id: str) -> ExperimentDetail | str:
    """Reads one Experiment: its test cases and how far each side has got. Free to call.

    Use it to follow an Experiment after ``create_experiment``, ``update_experiment`` or a rerun,
    and to see why a side failed. ``status`` and each side's ``status`` go REPLAYING, SCORING, then
    ENDED or FAILED. Per side: ``run_counts`` (replays by status, ``failed`` ones can be replayed
    again), ``scoring_counts`` (evaluations; ``failed`` and ``errored`` ones can be judged again),
    ``error`` (why it could not be scored) and ``experiment_run_id`` (the scoring run, for
    ``get_experiment_run``). The Sessions each side scored are not included; they are per test case
    in ``get_experiment_results``. To retry what failed use ``rerun_failed_experiment``; to see why one
    replay failed, read it with ``get_session_replay`` (its id is on the Session's row in ``get_experiment_run``).

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id, from ``list_experiments``.
    :returns: The Experiment, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).get_experiment(experiment_id)
    except _API_ERRORS as e:
        return f"Failed to get experiment '{experiment_id}': {e}"


async def update_experiment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    experiment_id: str,
    name: str | None = None,
    candidate_pipeline_name: str | None = None,
    candidate_pipeline_version_id: str | None = None,
    baseline_pipeline_name: str | None = None,
    baseline_pipeline_version_id: str | None = None,
    recorded_baseline: bool = False,
    preview: bool = False,
) -> Experiment | ExperimentUpdatePlan | str:
    """Renames an Experiment or changes its candidate or baseline. Changing a side costs money.

    Send only what changes. A changed side is planned again as on a new Experiment: Sessions that
    already exist on it are reused, the rest are replayed, and it is judged again once they have
    finished; its previous scoring run is stopped and the other side is left alone. Only renaming
    costs nothing. Call it first with ``preview=True``: that changes nothing and returns, for each
    changed side, ``reused_sessions`` and ``replays_needed`` (a side left alone is null). Show that
    to the user and get a yes before changing for real. Follow progress with ``get_experiment``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id.
    :param name: A new name.
    :param candidate_pipeline_name: Pipeline of the new candidate; give it with its version id.
    :param candidate_pipeline_version_id: The new candidate version.
    :param baseline_pipeline_name: Pipeline of the new baseline; give it with its version id.
    :param baseline_pipeline_version_id: The new baseline version.
    :param recorded_baseline: True makes the baseline the Dataset's recorded Sessions, with nothing replayed.
    :param preview: True returns the plan and changes nothing.
    :returns: The updated Experiment, or with ``preview`` the plan, or an error message.
    """
    if (candidate_pipeline_name is None) != (candidate_pipeline_version_id is None):
        return "Give both candidate_pipeline_name and candidate_pipeline_version_id, or neither."
    if (baseline_pipeline_name is None) != (baseline_pipeline_version_id is None):
        return "Give both baseline_pipeline_name and baseline_pipeline_version_id, or neither."
    resource = client.evaluation(workspace=workspace)
    changes: dict[str, Any] = {
        "name": name,
        "candidate_pipeline_name": candidate_pipeline_name,
        "candidate_pipeline_version_id": candidate_pipeline_version_id,
        "baseline_pipeline_name": baseline_pipeline_name,
        "baseline_pipeline_version_id": baseline_pipeline_version_id,
        "recorded_baseline": recorded_baseline,
    }
    try:
        if preview:
            return await resource.preview_update_experiment(experiment_id, **changes)
        return await resource.update_experiment(experiment_id, **changes)
    except _API_ERRORS as e:
        return f"Failed to update experiment '{experiment_id}': {e}"


async def rerun_failed_experiment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    experiment_id: str,
    rerun: Literal["evaluations", "replays"] = "evaluations",
) -> Experiment | str:
    """Retries what failed in an Experiment. Costs money: judges or replays again.

    ``rerun="evaluations"`` judges again the evaluations a side's scoring run left failed or
    errored (see ``scoring_counts`` in ``get_experiment``), reusing every one that succeeded; it
    bills only those Evaluators again. ``rerun="replays"`` replays again the replays that failed
    (``run_counts.failed``), reusing every Session that exists, then scores that side again, which
    bills the new Sessions' replays and evaluations. hub-api refuses with a message when nothing
    failed or while a side is still running. Follow progress with ``get_experiment``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id.
    :param rerun: Which failures to retry: "evaluations" (default) or "replays".
    :returns: The Experiment, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).rerun_failed_experiment(
            experiment_id, replays=rerun == "replays"
        )
    except _API_ERRORS as e:
        return f"Failed to rerun failed {rerun} of experiment '{experiment_id}': {e}"


async def rescore_experiment(*, client: AsyncClientProtocol, workspace: str, experiment_id: str) -> Experiment | str:
    """Scores both sides of an Experiment again with its Evaluators as they are now. Costs money.

    Use it after changing an Evaluator (``update_evaluator``). Every Session is judged again, so every
    evaluation is billed again; the
    Sessions are not replayed. hub-api refuses with a message while a side is still running or if
    no side has been scored. Follow progress with ``get_experiment``, then read
    ``get_experiment_results``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id.
    :returns: The Experiment, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).rescore_experiment(experiment_id)
    except _API_ERRORS as e:
        return f"Failed to rescore experiment '{experiment_id}': {e}"


async def delete_experiment(*, client: AsyncClientProtocol, workspace: str, experiment_id: str) -> str:
    """Deletes an Experiment and its results. This cannot be undone: get a yes first.

    The Sessions it reused, its replays and its scoring runs are kept, so later Experiments can
    reuse them.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param experiment_id: The Experiment's id.
    :returns: A confirmation, or an error message.
    """
    try:
        await client.evaluation(workspace=workspace).delete_experiment(experiment_id)
    except _API_ERRORS as e:
        return f"Failed to delete experiment '{experiment_id}': {e}"
    return f"Experiment '{experiment_id}' deleted."


async def list_experiment_runs(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    session_id: str | None = None,
    limit: int = 50,
) -> list[GoalRunSummary] | list[ExperimentRun] | str:
    """Lists goal runs: the pipeline's recent ones, or every one that judged a given Session.

    A goal run judges chosen Sessions of one pipeline against its Evaluation goals: an
    ``evaluate_goals`` run, or one side of an Experiment. Without ``session_id`` it lists the
    pipeline's goal runs, newest first. The list leaves out the runs the AI Operator and the
    Deployment Gate start. Each has its ``status``, how many ``sessions`` it judges, and its
    ``source`` (a window, a Dataset, or a side of an Experiment). With ``session_id`` it lists the
    runs that judged that Session, newest first, without their grids. Read one run's grid with
    ``get_experiment_run``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param session_id: List the runs that judged this Session instead.
    :param limit: Most runs to return (at most 100 for a pipeline, 200 for a Session). The tool reads one
        page: a result of exactly this many may be cut off.
    :returns: The runs, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        if session_id is not None:
            return await resource.list_session_experiment_runs(pipeline_name, session_id, limit)
        return await resource.list_experiment_runs(pipeline_name, limit)
    except _API_ERRORS as e:
        return f"Failed to list goal runs on pipeline '{pipeline_name}': {e}"


async def evaluate_goals(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    source: GoalRunSource | None = None,
    preview: bool = False,
) -> EvaluateGoalsAccepted | GoalRunPreview | str:
    """Evaluates a pipeline's Evaluation goals now: one scoring run of their Evaluators. Costs money.

    Every Evaluator behind the pipeline's goals (see ``list_evaluation_goals``) judges every chosen
    Session, and an Evaluator that judges with a model is billed per judged turn on the customer's
    provider. Without ``source`` it judges the newest live Sessions of the last 7 days, up to the run
    limit. A ``source`` picks the Sessions instead, by ``kind``: ``window`` judges the live Sessions
    whose last activity falls in ``start``..``end`` (ISO 8601 with a timezone, not in the future), at
    most ``max_sessions``; ``dataset`` judges the Sessions a Dataset (``dataset_id``, see
    ``list_datasets``) recorded on this pipeline, as recorded, with nothing replayed; ``new_dataset``
    keeps a window's newest live Sessions as a new Dataset called ``name`` and judges them.
    To judge specific Sessions, put them in a Dataset (``create_dataset`` or ``copy_test_cases``) and
    pass a ``dataset`` source; to judge one Session with one Evaluator, use ``run_evaluator``.

    Preview first: ``preview=True`` with a ``source`` starts nothing and returns ``sessions``,
    ``judged`` and ``judgments`` (the judge calls it would make) against ``limit``. Show that to the
    user and get a yes before starting for real. To preview the default run, pass a ``window`` over the
    last 7 days.

    The run is queued, not finished: poll it with ``get_experiment_run`` and its ``scoring_run_id``.
    If a goal run of the pipeline is already going, nothing starts and ``already_running`` is true;
    the returned id is that run.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline whose goals are evaluated.
    :param source: The Sessions to judge: a ``window``, a ``dataset`` or a ``new_dataset``; omit for the
        last 7 days.
    :param preview: True sizes the run over ``source`` and starts nothing.
    :returns: The queued run (``scoring_run_id``, ``sessions``), or with ``preview`` the counts, or an error.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        if preview:
            if source is None:
                return "Give a source to preview: a window over the last 7 days previews the default run."
            return await resource.preview_goal_run(pipeline_name, source)
        return await resource.evaluate_goals(pipeline_name, source)
    except _API_ERRORS as e:
        return f"Failed to evaluate the Evaluation goals of pipeline '{pipeline_name}': {e}"


async def run_evaluator(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    evaluator_version_id: str,
    session_id: str,
    wait_seconds: int = 120,
) -> EvaluationRun | str:
    """Runs one Evaluator version on one Session and keeps the result. A judged Evaluator costs money.

    Unlike ``try_evaluator``, which runs source you send and stores nothing, this runs a saved
    Evaluator version and stores an Evaluation Run that shows in ``list_evaluation_runs`` and in the Metric's history
    over time. Use it to judge one Session with
    an Evaluator that already exists; to judge many Sessions against the pipeline's Evaluation goals use
    ``evaluate_goals``. An Evaluator that judges with a model costs a model call per judged
    turn on the customer's provider, so say so and get a yes first. Find the version id with
    ``get_evaluator`` (``latest_version`` or ``versions``) and the Session with ``list_sessions``.

    ``outcome`` ERRORED means the Evaluator's code broke: read ``error_detail``. ``metrics`` are
    the values per address with their rationales. If ``status`` is still CREATED or STARTED the
    wait ran out: poll ``get_evaluation_run`` with the ``evaluation_run_id``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline the Session belongs to.
    :param evaluator_version_id: The exact Evaluator version to run.
    :param session_id: The Session to judge: a ``search_session_id``, or a single-turn run's ``query_id``.
    :param wait_seconds: How long to wait for the result before handing back the id to poll.
    :returns: The Evaluation Run, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        run_id = await resource.run_evaluator(pipeline_name, evaluator_version_id, session_id)
        return await _poll(
            lambda: resource.get_evaluation_run(pipeline_name, run_id),
            lambda r: r.status in RUN_DONE_STATUSES,
            wait_seconds,
        )
    except _API_ERRORS as e:
        return f"Failed to run Evaluator version '{evaluator_version_id}' on Session '{session_id}': {e}"


async def list_evaluation_runs(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, limit: int = 50
) -> list[EvaluationRun] | str:
    """Lists a pipeline's Evaluation Runs, newest first: one Evaluator version judging one Session each.

    Includes the runs behind a scoring run's cells and the ones ``run_evaluator`` made. Each has its
    ``session_id``, ``evaluator_version_id``, ``outcome`` and ``metrics``. Read one with
    ``get_evaluation_run``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param limit: Most runs to return (at most 200). The API has no further paging: a result of exactly
        this many may be cut off.
    :returns: The runs, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_evaluation_runs(pipeline_name, limit)
    except _API_ERRORS as e:
        return f"Failed to list Evaluation Runs of pipeline '{pipeline_name}': {e}"


async def get_evaluation_run(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, evaluation_run_id: str
) -> EvaluationRun | str:
    """Reads one Evaluation Run: its progress, or what the Evaluator found once it ended.

    Use it to follow a run ``run_evaluator`` handed back while still going. ``status`` ENDED with
    ``outcome`` SUCCEEDED has ``metrics``; ERRORED means the Evaluator's code broke (see
    ``error_detail``); FAILED never completed and can be run again.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param evaluation_run_id: The ``evaluation_run_id`` from ``run_evaluator`` or ``list_evaluation_runs``.
    :returns: The Evaluation Run, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).get_evaluation_run(pipeline_name, evaluation_run_id)
    except _API_ERRORS as e:
        return f"Failed to read Evaluation Run '{evaluation_run_id}': {e}"
