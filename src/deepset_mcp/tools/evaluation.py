# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tools for reading Evaluators, Experiments, their runs, and the Sessions a run can judge."""

import asyncio
from collections import Counter
from statistics import fmean
from typing import Literal

from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    ExperimentRunGrid,
    ExperimentRunReport,
    ExperimentSummary,
    MetricSummary,
    ReportCell,
    ReportRow,
    SessionList,
)
from deepset_mcp.api.exceptions import BadRequestError, ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.protocols import AsyncClientProtocol


async def list_evaluators(*, client: AsyncClientProtocol, workspace: str) -> list[Evaluator] | str:
    """Lists the Evaluators in the workspace.

    An Evaluator is a versioned Python function that judges a Session and reports named Metrics.
    Each entry carries its newest version's id and the Metrics that version declares (name, shape,
    grain and, for a closed Label, its vocabulary), but not the source. Evaluators belong to the
    workspace, not to a pipeline; an Experiment picks which ones run on its pipeline.

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


async def list_experiments(
    *, client: AsyncClientProtocol, workspace: str, pipeline_name: str
) -> list[ExperimentSummary] | str:
    """Lists a pipeline's Experiments, each with its most recent run.

    An Experiment is a named set of Evaluators that runs against chosen Sessions of one pipeline.
    ``last_run`` is the newest run without its grid (status, ``selection``, timing), or null when
    the Experiment never ran; read a run's results with ``get_experiment_run``.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :returns: The Experiments, or an error message.
    """
    resource = client.evaluation(workspace=workspace)
    try:
        experiments = await resource.list_experiments(pipeline_name)
        last_runs = await asyncio.gather(
            *(resource.list_experiment_runs(pipeline_name, e.pipeline_experiment_id, limit=1) for e in experiments)
        )
    except ResourceNotFoundError:
        return f"There is no pipeline named '{pipeline_name}' in workspace '{workspace}' (not found)."
    except (BadRequestError, UnexpectedAPIError) as e:
        return f"Failed to list experiments for pipeline '{pipeline_name}': {e}"
    return [
        ExperimentSummary(**experiment.model_dump(), last_run=runs[0] if runs else None)
        for experiment, runs in zip(experiments, last_runs, strict=True)
    ]


async def get_experiment_run(
    *,
    client: AsyncClientProtocol,
    workspace: str,
    pipeline_name: str,
    experiment_id: str,
    run_id: str,
    max_rows: int = 100,
) -> ExperimentRunReport | str:
    """Reads one Experiment run: how its cells ended, a summary per Metric, then the grid rows.

    A run judges each chosen Session with each Evaluator; one cell per pair. ``counts`` says how
    the cells ended: ``errored`` is the Evaluator's own code breaking (see the cell's
    ``error_detail``), not a low Metric; ``failed`` is a cell that never ran and can be retried.
    ``metrics`` summarises each Evaluator's Metric over every row, rows past ``max_rows``
    included: mean, min and max for a Score, a count per label for a Label, and how often it did
    not apply. Each row is a Session with its cells; a cell's ``metrics`` carry the value per
    address (``session``, ``turn/2``, ...) and the rationale the Evaluator wrote, which is what to
    group failures by. ``run.selection`` says whether the Sessions were SAMPLED or HAND_PICKED;
    only sampled runs say anything about traffic as a whole.

    :param client: The async client for API communication.
    :param workspace: The workspace name.
    :param pipeline_name: Name of the pipeline.
    :param experiment_id: The Experiment's id.
    :param run_id: The run's id.
    :param max_rows: Most rows to return; the summaries still cover every row.
    :returns: The run report, or an error message.
    """
    try:
        grid = await client.evaluation(workspace=workspace).get_experiment_run(pipeline_name, experiment_id, run_id)
    except ResourceNotFoundError:
        return f"Run '{run_id}' of experiment '{experiment_id}' on pipeline '{pipeline_name}' not found."
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
    """Lists a pipeline's Sessions that an Experiment run can judge, newest last activity first.

    A Session is the turns that share a ``search_session_id``; a run without one is a single-turn
    Session named by its ``query_id``. Only Sessions whose every turn still has its trace are
    listed. ``session_id`` is the id an Experiment run takes. To find Sessions that went wrong
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
