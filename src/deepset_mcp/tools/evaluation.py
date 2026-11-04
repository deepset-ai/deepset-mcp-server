# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for reading evaluation state and running the assistant's two checks.

The reads cover Evaluators, Metric Groups and their scoring runs, Experiments, and Sessions. The
checks are an ad-hoc try of Evaluator source and a session replay against a pipeline version.
"""

import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from statistics import fmean
from typing import Any, Literal, TypeVar

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
    ExperimentResultsReport,
    ExperimentRun,
    ExperimentRunAccepted,
    ExperimentRunGrid,
    ExperimentRunPreview,
    ExperimentRunReport,
    ExperimentUpdatePlan,
    MetricGroup,
    MetricGroupSummary,
    MetricSummary,
    MetricWeight,
    NewTestCase,
    ReportCell,
    ReportRow,
    SessionList,
    SessionReplayReport,
    SessionReplayRun,
    TestCase,
    TraceSummary,
    TryReport,
    TryState,
)
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_evaluators(*, client: AsyncClientProtocol, workspace: str) -> list[Evaluator] | str:
    """Lists the Evaluators in the workspace.

    An Evaluator is a versioned Python function that judges a Session and reports named Metrics.
    Each entry carries its newest version's id and the Metrics that version declares (name, shape,
    grain and, for a closed Label, its vocabulary and, if it declares one, its ``scale``; for a
    Score, its ``range`` and ``better``), but not the source. Evaluators belong to the workspace,
    not to a pipeline; a Metric Group picks which ones a scoring run judges with.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :returns: The Evaluators, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_evaluators()
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


async def list_metric_groups(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str | None = None
) -> list[MetricGroupSummary] | str:
    """Lists the workspace's Metric Groups, newest first.

    A Metric Group is a named, ordered set of Evaluators. It belongs to the workspace, not to a
    pipeline: a scoring run judges chosen Sessions of one pipeline with it, and an Experiment scores
    both its sides with one. With ``pipeline_name``, each entry's ``last_run`` is its newest scoring
    run on that pipeline without the grid (status, ``selection``, timing), or null when it never ran
    there; read a run's results with ``get_experiment_run``. ``weights`` says how much each Metric
    counts toward the group's Composite (empty: no Composite); a weight with ``usable`` false
    says in ``unusable_reason`` why it will not count in a new run.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: A pipeline to attach each Metric Group's most recent scoring run on.
    :returns: The Metric Groups, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        groups = await resource.list_metric_groups()
        if pipeline_name is None:
            return [MetricGroupSummary(**group.model_dump()) for group in groups]
        last_runs = await asyncio.gather(
            *(resource.list_experiment_runs(pipeline_name, group.metric_group_id, limit=1) for group in groups)
        )
    except ResourceNotFoundError:
        if pipeline_name is None:
            return f"Workspace '{workspace}' not found."
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}' (not found)."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list metric groups in workspace '{workspace}': {e}"
    return [
        MetricGroupSummary(**group.model_dump(), last_run=runs[0] if runs else None)
        for group, runs in zip(groups, last_runs, strict=True)
    ]


async def create_experiment(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    name: str,
    dataset_id: str,
    metric_group_id: str,
    candidate_pipeline_name: str,
    candidate_pipeline_version_id: str,
    baseline_pipeline_name: str | None = None,
    baseline_pipeline_version_id: str | None = None,
    sessions_per_test_case: int = 1,
    replay_mode: Literal["FIRST_USER_MESSAGE", "ALL_USER_MESSAGES"] = "FIRST_USER_MESSAGE",
    reuse_sessions: bool = True,
    preview: bool = False,
) -> Experiment | ExperimentPlan | str:
    """Creates an Experiment that compares a candidate pipeline version against a baseline.

    Both sides are scored by the same Metric Group over the test cases of one Dataset. The baseline
    is either another pipeline version (give ``baseline_pipeline_name`` and
    ``baseline_pipeline_version_id`` together) or Recorded (leave both unset): a Recorded baseline
    reuses the Sessions each test case recorded, with nothing replayed. The candidate is always a
    pipeline version that will be replayed on each test case.

    Creating costs money: it replays the pipeline on the customer's models, and then every Session
    is judged by the Metric Group's Evaluators, which are billed when they use an LLM. Call it first
    with ``preview=True``: that starts nothing and returns, per side, how many Sessions are
    ``reused_sessions`` and how many ``replays_needed``, plus ``cells`` (Sessions times Evaluators)
    against ``max_cells``. Show that to the user and get a yes before creating for real.
    ``sessions_per_test_case`` sets how many Sessions each side scores per test case
    (1..50); existing Sessions on that version are reused and only the shortfall is replayed. Find
    ids with ``list_metric_groups`` (metric groups) and ``list_experiments`` (an existing
    Experiment's ``dataset_id``). Read the running or finished Experiment with
    ``get_experiment_results``; follow its progress with ``get_experiment``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: Human-readable name for the Experiment.
    :param dataset_id: The Dataset's id (the UI's Dataset dropdown).
    :param metric_group_id: The Metric Group id to score both sides with.
    :param candidate_pipeline_name: Name of the candidate pipeline.
    :param candidate_pipeline_version_id: The candidate pipeline version to replay.
    :param baseline_pipeline_name: Baseline pipeline name; omit for a Recorded baseline.
    :param baseline_pipeline_version_id: Baseline version id; required when baseline_pipeline_name is given.
    :param sessions_per_test_case: Repetitions per test case (1..50, default 1).
    :param replay_mode: FIRST_USER_MESSAGE replays the first turn only; ALL_USER_MESSAGES replays every turn.
    :param preview: True returns the plan (what would be reused and replayed) and creates nothing.
    :returns: The created Experiment, or with ``preview`` the plan, or an error message.
    """
    if (baseline_pipeline_name is None) != (baseline_pipeline_version_id is None):
        return (
            "Give both baseline_pipeline_name and baseline_pipeline_version_id for a Pipeline-version "
            "baseline, or neither for a Recorded baseline."
        )
    resource = client.evaluation(workspace=workspace)
    try:
        if preview:
            return await resource.preview_experiment(
                dataset_id=dataset_id,
                metric_group_id=metric_group_id,
                candidate_pipeline_name=candidate_pipeline_name,
                candidate_pipeline_version_id=candidate_pipeline_version_id,
                baseline_pipeline_name=baseline_pipeline_name,
                baseline_pipeline_version_id=baseline_pipeline_version_id,
                sessions_per_test_case=sessions_per_test_case,
                replay_mode=replay_mode,
            )
        return await resource.create_experiment(
            name=name,
            dataset_id=dataset_id,
            metric_group_id=metric_group_id,
            candidate_pipeline_name=candidate_pipeline_name,
            candidate_pipeline_version_id=candidate_pipeline_version_id,
            baseline_pipeline_name=baseline_pipeline_name,
            baseline_pipeline_version_id=baseline_pipeline_version_id,
            sessions_per_test_case=sessions_per_test_case,
            replay_mode=replay_mode,
        )
    except ResourceNotFoundError as e:
        missing = [
            f"workspace '{workspace}'",
            f"pipeline '{candidate_pipeline_name}'",
        ]
        if baseline_pipeline_name is not None:
            missing.append(f"baseline pipeline '{baseline_pipeline_name}'")
        return f"Could not create experiment: one of {', '.join(missing)} not found ({e})."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to create experiment '{name}': {e}"


async def list_experiments(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str | None = None
) -> list[Experiment] | str:
    """Lists the workspace's Experiments, newest first.

    An Experiment compares a candidate pipeline version against a baseline on the test cases of one
    Dataset: each side gets its Sessions (reused, or replayed against its version) and is scored by
    the same Metric Group. The baseline is another version, or, when ``recorded``, the Sessions the
    Dataset recorded. ``status`` and each side's ``status`` go REPLAYING, SCORING, then ENDED or
    FAILED; a side's ``error`` says why it failed and ``scoring_counts`` how its evaluations ended.
    Read how the candidate did against the baseline with ``get_experiment_results``. To read one
    side's scoring run cell by cell, pass its ``scoring_runs[].experiment_run_id``, that entry's
    ``pipeline_id`` resolved to a name with ``list_pipelines``, and the Experiment's
    ``metric_group_id`` to ``get_experiment_run``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Only Experiments with either side on this pipeline, when given.
    :returns: The Experiments, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_experiments(pipeline_name)
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

    Find an Experiment with ``list_experiments``. ``metrics`` has one entry per Metric of the
    Metric Group, in its order: each side's ``value`` (or ``labels`` for a Label), ``delta`` and
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
    different formulas: report no change between them and give ``incomparable_reason``.

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
    metric_group_id: str,
    run_id: str,
    max_rows: int = 100,
) -> ExperimentRunReport | str:
    """Reads one scoring run: how its cells ended, a summary per Metric, then the grid rows.

    A scoring run is a Metric Group judging chosen Sessions of one pipeline. Find one with
    ``list_metric_groups`` (``last_run``) or ``list_experiments`` (a side's ``scoring_runs``).
    It judges each chosen Session with each Evaluator; one cell per pair. ``counts`` says how
    the cells ended: ``errored`` is the Evaluator's own code breaking (see the cell's
    ``error_detail``), not a low Metric; ``failed`` is a cell that never ran and can be retried.
    ``metrics`` summarises each Evaluator's Metric over every row, rows past ``max_rows``
    included: mean, min and max for a Score, a count per label for a Label, and how often it did
    not apply. Each row is a Session with its cells; a cell's ``metrics`` carry the value per
    address (``session``, ``turn/2``, ...) and the rationale the Evaluator wrote, which is what to
    group failures by. ``run.selection`` says whether the Sessions were SAMPLED or HAND_PICKED;
    only sampled runs say anything about traffic as a whole. ``composite`` is the Metric Group's
    single number for the run, 0 to 1 with 1 best, from ``normalized_means`` (each Metric on that
    scale) weighted by ``run.composite_weights``, the formula the run started with. When it has
    no value it says ``reason`` and lists the Metrics that block it in ``missing``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param metric_group_id: The id of the Metric Group the run scored with.
    :param run_id: The run's id.
    :param max_rows: Most rows to return; the summaries still cover every row.
    :returns: The run report, or an error message.
    """
    try:
        grid = await client.evaluation(workspace=workspace).get_experiment_run(pipeline_name, metric_group_id, run_id)
    except ResourceNotFoundError:
        return f"Run '{run_id}' of metric group '{metric_group_id}' on pipeline '{pipeline_name}' not found."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to get run '{run_id}': {e}"
    rows = [
        ReportRow(
            session_id=row.session_id,
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
# Checks: the ad-hoc try and session replay
# ---------------------------------------------------------------------------------------------

POLL_INTERVAL_SECONDS = 2.0
REPLAY_DONE_STATUSES = frozenset({"ENDED", "FAILED"})
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
    wait_seconds: int = 120,
) -> TryReport | str:
    """Tries Evaluator source on one Session and returns what it found. Persists nothing.

    Use it to check a draft before showing it as ready, and to judge a replayed Session against
    its source. The source is an Evaluation Function: a Python function that reads one Session and
    reports named Metrics declared with ``@metrics``. To try a saved Evaluator, read a version's
    ``python_code`` with ``get_evaluator`` and pass it. A try that
    judges with a model costs a model call per judged turn on the customer's provider.

    ``outcome`` ERRORED means the code broke: read ``error_detail`` and fix it. ``metrics`` are the
    values per address with their rationales. ``trace_summary`` says which Session Tools the
    evaluator called. If ``status`` is RUNNING the wait ran out: poll ``get_evaluation_try``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline the Session belongs to.
    :param python_code: The Evaluation Function's source.
    :param session_id: The Session to judge: a ``search_session_id``, or a single-turn run's ``query_id``.
    :param wait_seconds: How long to wait for the result before handing back the id to poll.
    :returns: The try report, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        try_id = await resource.start_try(pipeline_name, python_code, session_id)
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


async def _replay_report(
    client: AsyncClientProtocol, workspace: str, pipeline_name: str, run: SessionReplayRun
) -> SessionReplayReport:
    """The run, with the Session it produced: read off its first trace, else that trace itself."""
    replayed_session_id = None
    if run.status == "ENDED" and run.trace_ids:
        first = run.trace_ids[0]
        traces = await client.search_history(workspace=workspace).list_pipeline_traces(
            pipeline_name=pipeline_name, limit=1, query_filter=f"query_id eq '{first}'"
        )
        row = traces.data[0] if traces.data else None
        replayed_session_id = (getattr(row, "search_session_id", None) if row else None) or first
    return SessionReplayReport(
        status=run.status,
        replay_run_id=run.session_replay_run_id,
        source_session_id=run.source_session_id,
        replayed_session_id=replayed_session_id,
        pipeline_version_id=run.pipeline_version_id,
        replay_mode=run.replay_mode,
        trace_ids=run.trace_ids,
        error_detail=run.error_detail,
    )


async def replay_session(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    session_id: str,
    pipeline_version_id: str,
    replay_mode: Literal["FIRST_USER_MESSAGE", "ALL_USER_MESSAGES"] | None = None,
    wait_seconds: int = 300,
) -> SessionReplayReport | str:
    """Replays a recorded Session against a pipeline version, a draft included, into a new Session.

    Use it to check a pipeline change on real Sessions: replay the Sessions behind the change
    against the draft version, then ``try_evaluator`` the relevant Evaluators on each source
    Session and on its ``replayed_session_id``, and compare. Each replay runs the pipeline on the
    customer's models, so say what it costs and get a yes before replaying. The source Session and
    the deployed pipeline are untouched.

    FIRST_USER_MESSAGE replays the first turn only; ALL_USER_MESSAGES replays every turn of a chat in
    order. Leave it unset to use the server's default (the first turn), and say so when reporting.
    If ``status`` is still CREATED or STARTED the wait ran out: poll ``get_session_replay``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param session_id: The Session to replay: a ``search_session_id``, or a single-turn run's ``query_id``.
    :param pipeline_version_id: The pipeline version to replay against, e.g. the current draft's.
    :param replay_mode: FIRST_USER_MESSAGE or ALL_USER_MESSAGES; unset uses the server's default.
    :param wait_seconds: How long to wait for the replay before handing back the id to poll.
    :returns: The replay report with the new Session's id, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        run_id = await resource.start_session_replay(pipeline_name, session_id, pipeline_version_id, replay_mode)
        run = await _poll(
            lambda: resource.get_session_replay(pipeline_name, run_id),
            lambda r: r.status in REPLAY_DONE_STATUSES,
            wait_seconds,
        )
        return await _replay_report(client, workspace, pipeline_name, run)
    except ResourceNotFoundError:
        return (
            f"Pipeline '{pipeline_name}', Session '{session_id}' or version '{pipeline_version_id}' "
            f"not found in workspace '{workspace}'."
        )
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to replay Session '{session_id}': {e}"


async def get_session_replay(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, replay_run_id: str
) -> SessionReplayReport | str:
    """Reads a session replay that ``replay_session`` handed back while it was still running.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param replay_run_id: The ``replay_run_id`` from ``replay_session``.
    :returns: The replay report with the new Session's id once it ended, or an error message.
    """
    try:
        run = await client.evaluation(workspace=workspace).get_session_replay(pipeline_name, replay_run_id)
        return await _replay_report(client, workspace, pipeline_name, run)
    except ResourceNotFoundError:
        return f"Replay '{replay_run_id}' not found for pipeline '{pipeline_name}'."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to read replay '{replay_run_id}': {e}"


_API_ERRORS = (ResourceNotFoundError, BadRequestError, UnexpectedAPIError)


async def list_datasets(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str | None = None
) -> list[DatasetSummary] | str:
    """Lists the workspace's Datasets, newest first, without their test cases.

    A Dataset is a named list of test cases (a recorded Session or a set of inputs, with optional
    expected data) that an Experiment replays against a pipeline version. Each entry has its
    ``dataset_id``, ``test_case_count`` and the ``pipeline_ids`` its test cases belong to. Read the
    test cases with ``get_dataset``; pass ``dataset_id`` to ``create_experiment``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Only Datasets with a test case on this pipeline, when given.
    :returns: The Datasets, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_datasets(pipeline_name)
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

    Experiments that used the Dataset keep their results but lose the link to it.

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
    metric_group_ids: list[str] | None = None,
    new_metric_group_name: str | None = None,
) -> Evaluator | str:
    """Creates an Evaluator from Python source and adds it to the workspace. Judged Metrics cost money when run.

    Always validate new code first: run it on a real Session with ``try_evaluator`` and fix what it
    reports before saving. ``python_code`` is the Evaluation Function; its ``@metrics`` declaration
    names the Metrics it reports, and hub-api rejects code whose declaration it cannot read. Start
    from ``list_evaluator_templates`` rather than from scratch. The name must be unused in the
    workspace. The Evaluator scores nothing until a Metric Group runs it: add it to existing groups
    with ``metric_group_ids`` (each at the end of its set), to a new group with
    ``new_metric_group_name``, or later with ``update_metric_group``. Change it later with
    ``update_evaluator``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: The Evaluator's name; must not exist in the workspace yet.
    :param python_code: The Evaluation Function's Python source.
    :param metric_group_ids: Existing Metric Groups to add it to.
    :param new_metric_group_name: Also creates a Metric Group of this name holding only this Evaluator.
    :returns: The created Evaluator, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).create_evaluator(
            name, python_code, metric_group_ids, new_metric_group_name
        )
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

    New source adds a version; the Evaluator's Metric Groups judge with the newest version from the next
    run on, and past runs keep the version they used. Validate the new code with ``try_evaluator``
    first. Source the Evaluator already had in its history adds no version, so reverting is safe.
    hub-api rejects code that changes what an existing Metric measures (its shape, grain or range,
    a narrowed vocabulary), and a changed declaration can make a Metric Group weight unusable: check
    ``weights`` with ``list_metric_groups`` afterwards. Read the current source with ``get_evaluator``.

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

    An archived Evaluator keeps its versions and name, and its Metric Groups still score with it; it
    only shows an ``archived_at`` time. Use it to retire an Evaluator without breaking history.

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
    ``combinable_as_code`` templates can be merged with ``combine_evaluator_templates``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :returns: The templates, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).list_evaluator_templates()
    except _API_ERRORS as e:
        return f"Failed to list evaluator templates: {e}"


async def combine_evaluator_templates(
    *, client: AsyncClientProtocol, workspace: str, template_keys: list[str], title: str
) -> CombinedEvaluatorTemplates | str:
    """Merges code templates into one Evaluation Function that reports all their Metrics. Saves nothing.

    Only templates whose ``combinable_as_code`` is true can be merged; an unknown key, a judge template
    or a repeated key is rejected. The returned ``python_code`` is not yet an Evaluator: pass it to
    ``try_evaluator`` and then ``create_evaluator``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param template_keys: Keys of two or more templates, in the order their Metrics should be reported.
    :param title: What the combined code's opening comment calls it, e.g. "Agent efficiency metrics".
    :returns: The merged code and its Metrics, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).combine_evaluator_templates(template_keys, title)
    except _API_ERRORS as e:
        return f"Failed to combine evaluator templates: {e}"


async def create_metric_group(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    name: str,
    evaluator_ids: list[str],
    weights: list[MetricWeight] | None = None,
) -> MetricGroup | str:
    """Creates a Metric Group: a named, ordered set of Evaluators to score Sessions of any pipeline with.

    The group names Evaluators, not versions, so each run judges with their newest versions. Running
    it costs money if an Evaluator is judged. Find Evaluator ids with ``list_evaluators``.

    ``weights`` say how much each Metric counts toward the group's Composite, as
    ``{evaluator_id, metric_key, weight}`` entries. ``weight`` is a number above 0 and relative: weights
    are divided by their sum, so 2, 1, 1 count as 50%, 25%, 25%. Each Evaluator must be in the group,
    each ``metric_key`` must be one its newest version declares with a Normalized mean (a Score
    with both ``range`` and ``better``, or a Label with a ``scale``), and no pair may repeat; otherwise
    hub-api rejects the request. Without weights a group has no Composite. A stored weight with
    ``usable`` false and an ``unusable_reason`` means a newer Evaluator version dropped the Metric or
    its normalization: it is kept but no longer counts in new runs.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param name: The Metric Group's name.
    :param evaluator_ids: The Evaluators to run, in the order results show them (at least one).
    :param weights: Optional Metric weights, as described above.
    :returns: The created Metric Group, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).create_metric_group(name, evaluator_ids, weights)
    except _API_ERRORS as e:
        return f"Failed to create metric group '{name}': {e}"


async def update_metric_group(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    metric_group_id: str,
    name: str,
    evaluator_ids: list[str],
    weights: list[MetricWeight] | None = None,
) -> MetricGroup | str:
    """Replaces a Metric Group's name and Evaluator set, and optionally its Metric weights.

    This is a full replace of name and Evaluators: send every Evaluator the group keeps, in order
    (read them with ``list_metric_groups``). Past runs are unaffected; each recorded the versions it
    used, and a run's Composite keeps the weights it started with, so edits change only later runs.
    Leave ``weights`` out to keep the stored weights of the Evaluators that stay (those of removed
    Evaluators are dropped); send an empty list to clear them all, which removes the Composite.

    ``weights`` say how much each Metric counts toward the group's Composite, as
    ``{evaluator_id, metric_key, weight}`` entries. ``weight`` is a number above 0 and relative: weights
    are divided by their sum, so 2, 1, 1 count as 50%, 25%, 25%. Each Evaluator must be in the group,
    each ``metric_key`` must be one its newest version declares with a Normalized mean (a Score
    with both ``range`` and ``better``, or a Label with a ``scale``), and no pair may repeat; otherwise
    hub-api rejects the request. Without weights a group has no Composite. A stored weight with
    ``usable`` false and an ``unusable_reason`` means a newer Evaluator version dropped the Metric or
    its normalization: it is kept but no longer counts in new runs.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param metric_group_id: The Metric Group's id.
    :param name: The name to keep or change to.
    :param evaluator_ids: Every Evaluator the group keeps, in order (at least one).
    :param weights: Replaces the stored weights; None keeps them, [] clears them.
    :returns: The Metric Group, or an error message.
    """
    try:
        return await client.evaluation(workspace=workspace).update_metric_group(
            metric_group_id, name, evaluator_ids, weights
        )
    except _API_ERRORS as e:
        return f"Failed to update metric group '{metric_group_id}': {e}"


async def delete_metric_group(*, client: AsyncClientProtocol, workspace: str, metric_group_id: str) -> str:
    """Deletes a Metric Group together with all its scoring runs. This cannot be undone: get a yes first.

    The Evaluators themselves stay. hub-api refuses with a message while an optimization goal judges
    with the group; change the goal first.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param metric_group_id: The Metric Group's id.
    :returns: A confirmation, or an error message.
    """
    try:
        await client.evaluation(workspace=workspace).delete_metric_group(metric_group_id)
    except _API_ERRORS as e:
        return f"Failed to delete metric group '{metric_group_id}': {e}"
    return f"Metric group '{metric_group_id}' deleted."


async def get_experiment(*, client: AsyncClientProtocol, workspace: str, experiment_id: str) -> ExperimentDetail | str:
    """Reads one Experiment: its test cases and how far each side has got. Free to call.

    Use it to follow an Experiment after ``create_experiment``, ``update_experiment`` or a rerun,
    and to see why a side failed. ``status`` and each side's ``status`` go REPLAYING, SCORING, then
    ENDED or FAILED. Per side: ``run_counts`` (replays by status, ``failed`` ones can be replayed
    again), ``scoring_counts`` (evaluations; ``failed`` and ``errored`` ones can be judged again),
    ``error`` (why it could not be scored) and ``experiment_run_id`` (the scoring run, for
    ``get_experiment_run``). The Sessions each side scored are not included; they are per test case
    in ``get_experiment_results``. To retry what failed use ``rerun_failed_experiment``.

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
    """Scores both sides of an Experiment again with the Metric Group as it is now. Costs money.

    Use it after changing the Metric Group's Evaluators or weights (``update_metric_group``,
    ``update_evaluator``). Every Session is judged again, so every evaluation is billed again; the
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
    metric_group_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[ExperimentRun] | str:
    """Not implemented yet."""
    raise NotImplementedError


async def start_experiment_run(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    metric_group_id: str,
    session_ids: list[str] | None = None,
    window_from: str | None = None,
    window_to: str | None = None,
    origin: Literal["SERVICE", "PIPELINE_RUN", "PLAYGROUND"] | None = None,
    deployment_id: str | None = None,
    pipeline_version_id: str | None = None,
    revision_id: str | None = None,
    reuse: Literal["RERUN_ALL", "REUSE_SUCCEEDED"] = "RERUN_ALL",
    selection: Literal["SAMPLED", "HAND_PICKED"] = "SAMPLED",
    focus: dict[str, list[str]] | None = None,
    preview: bool = False,
) -> ExperimentRunAccepted | ExperimentRunPreview | str:
    """Not implemented yet."""
    raise NotImplementedError


async def run_evaluator(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    evaluator_version_id: str,
    session_id: str,
    wait_seconds: int = 120,
) -> EvaluationRun | str:
    """Not implemented yet."""
    raise NotImplementedError


async def list_evaluation_runs(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, limit: int = 50
) -> list[EvaluationRun] | str:
    """Not implemented yet."""
    raise NotImplementedError


async def get_evaluation_run(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str, evaluation_run_id: str
) -> EvaluationRun | str:
    """Not implemented yet."""
    raise NotImplementedError
