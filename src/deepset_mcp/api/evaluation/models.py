# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the evaluation API: Evaluators, Experiments, their runs, and Sessions."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class MetricDeclaration(BaseModel):
    """One Metric an Evaluator version declares in its ``@metrics`` decorator."""

    shape: Literal["score", "label"] | None = Field(
        default=None, description="What the Metric reports. Null only for a legacy version."
    )
    grain: str = Field(
        description="Where the Metric repeats, e.g. 'session', 'turn' or 'turn/retriever/outputs.documents[*]'"
    )
    vocabulary: list[str] | None = Field(default=None, description="The labels a closed Label may take")


class EvaluatorVersionSummary(BaseModel):
    """One revision of an Evaluator, without its source."""

    evaluator_version_id: str
    evaluator_id: str
    content_hash: str = Field(description="SHA-256 of the version's source")
    metrics: dict[str, MetricDeclaration] = Field(
        default_factory=dict, description="The Metrics this version declares, keyed by name"
    )
    metrics_legacy: bool = Field(
        default=False, description="True when the source declares no Metrics and reports one session Metric 'value'"
    )
    created_at: str


class EvaluatorVersion(EvaluatorVersionSummary):
    """One revision of an Evaluator, with its Python source."""

    python_code: str


class Evaluator(BaseModel):
    """An Evaluator lineage, its newest version, and, when read alone, every version."""

    evaluator_id: str
    name: str
    latest_version: EvaluatorVersionSummary | None = Field(default=None, description="The version a run uses today")
    versions: list[EvaluatorVersionSummary] = Field(
        default_factory=list, description="Every version, newest first. Only filled when one Evaluator is read."
    )
    created_at: str
    updated_at: str | None = None


class ExperimentRun(BaseModel):
    """One Experiment run's lifecycle, without its grid."""

    pipeline_experiment_run_id: str
    pipeline_experiment_id: str
    status: str = Field(description="Whether the fan-out finished. Not a verdict on the cells.")
    selection: Literal["SAMPLED", "HAND_PICKED"] = Field(
        description="How the Sessions were chosen. Only SAMPLED runs feed trends."
    )
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str


class Experiment(BaseModel):
    """A named set of Evaluators run against Sessions of one pipeline."""

    pipeline_experiment_id: str
    name: str
    evaluator_ids: list[str]
    created_at: str
    updated_at: str | None = None


class ExperimentSummary(Experiment):
    """An Experiment and its most recent run, if it has one."""

    last_run: ExperimentRun | None = None


class MetricRow(BaseModel):
    """One declared Metric's value at one Address, or why it does not apply there."""

    metric_key: str
    address: str = Field(
        description="'session', or a path such as 'turn/2' or 'turn/2/retriever#0/outputs.documents[3]'"
    )
    kind: Literal["score", "label", "not_applicable"]
    score: float | None = None
    label: str | None = None
    reason: str | None = Field(default=None, description="Why the Metric does not apply, when kind is not_applicable")
    rationale: str | None = Field(default=None, description="What the Evaluator wrote about this value")


class EvaluationRun(BaseModel):
    """The Evaluation Run behind one grid cell."""

    evaluation_run_id: str
    status: str = Field(description="Whether the run executed. Only FAILED is retryable.")
    outcome: Literal["SUCCEEDED", "ERRORED"] | None = Field(
        default=None, description="ERRORED means the Evaluator's code broke; null until judged or when it failed"
    )
    metrics: list[MetricRow] = Field(default_factory=list)
    evaluator_version_id: str
    session_id: str | None = None
    error_detail: dict[str, Any] | None = None


class ExperimentRunCell(BaseModel):
    """One grid cell: an Evaluator column and the Evaluation Run that filled it."""

    evaluator_id: str
    evaluation_run: EvaluationRun


class ExperimentRunRow(BaseModel):
    """One grid row: a Session and one cell per Evaluator that judged it."""

    session_id: str
    cells: list[ExperimentRunCell] = Field(default_factory=list)


class ExperimentRunCounts(BaseModel):
    """How the run's cells ended."""

    cells: int
    succeeded: int = Field(description="Cells whose Evaluator produced Metrics")
    errored: int = Field(description="Cells whose Evaluator code broke: user code, not a Metric of zero")
    failed: int = Field(description="Cells whose run never completed. Retryable, unlike errored.")
    unresolved_sessions: int = Field(description="Sessions that could not be read at all, counted once each")
    running: int


class ExperimentRunGrid(BaseModel):
    """One Experiment run as Sessions by Evaluators, as the API returns it."""

    run: ExperimentRun
    evaluator_ids: list[str]
    rows: list[ExperimentRunRow] = Field(default_factory=list)
    counts: ExperimentRunCounts


class MetricSummary(BaseModel):
    """One Metric of one Evaluator, aggregated over every row of a run."""

    evaluator_id: str
    metric_key: str
    kind: Literal["score", "label", "not_applicable"] = Field(
        description="score or label by the values seen; not_applicable when it applied nowhere"
    )
    count: int = Field(description="Values reported, not counting not_applicable rows")
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    labels: dict[str, int] = Field(default_factory=dict, description="How often each label was given")
    not_applicable: int = 0


class ReportCell(BaseModel):
    """One grid cell, flattened."""

    evaluator_id: str
    status: str
    outcome: Literal["SUCCEEDED", "ERRORED"] | None = None
    evaluator_version_id: str
    metrics: list[MetricRow] = Field(default_factory=list)
    error_detail: dict[str, Any] | None = None


class ReportRow(BaseModel):
    """One Session of a run report, with its flattened cells."""

    session_id: str
    cells: list[ReportCell]


class ExperimentRunReport(BaseModel):
    """An Experiment run read for explaining it: counts, per-metric summaries, then the rows."""

    run: ExperimentRun
    evaluator_ids: list[str]
    counts: ExperimentRunCounts
    metrics: list[MetricSummary] = Field(description="Computed over every row, including rows cut by max_rows")
    rows: list[ReportRow]
    total_rows: int
    rows_truncated: bool


class SessionProvenance(BaseModel):
    """Where a Session came from."""

    origin: str = Field(description="SERVICE, PIPELINE_RUN or PLAYGROUND")
    deployment_id: str | None = Field(default=None, description="The Service that served every turn, if one did")
    pipeline_version_ids: list[str] = Field(default_factory=list)


class SessionListItem(BaseModel):
    """One Session a run can judge."""

    session_id: str = Field(description="The id to pass to a run")
    turn_count: int
    first_activity_at: str
    last_activity_at: str
    first_query: str
    provenance: SessionProvenance


class SessionList(BaseModel):
    """One page of Sessions, newest last activity first."""

    data: list[SessionListItem]
    next: str | None = Field(default=None, description="Pass as cursor for the next page. Null on the last page.")
