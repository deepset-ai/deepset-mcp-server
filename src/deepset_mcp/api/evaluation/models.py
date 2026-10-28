# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for the evaluation API: Evaluators, Metric Groups, their scoring runs, Experiments, and Sessions."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Better = Literal["higher", "lower"]
Change = Literal["improved", "regressed", "unchanged", "unknown"]

_BETTER = "Which way a change in this Metric is an improvement: 'higher', 'lower', or null when unknown."
_CHANGE = (
    "How the candidate moved this Metric, read against `better`: 'improved', 'regressed', 'unchanged', or "
    "'unknown' when no direction is declared or the change cannot be judged. Report improved or regressed "
    "only from this field, never from the Metric's name."
)

_EVALUATOR_ID = "The Evaluator the Metric belongs to."
_METRIC_KEY = "The Metric, by the key its Evaluator declares, for example `helpful`."


class CompositeWeight(BaseModel):
    """How much one Metric counted toward a scoring run's Composite, as the run recorded it when it started."""

    evaluator_id: str = Field(description=_EVALUATOR_ID)
    metric_key: str = Field(description=_METRIC_KEY)
    weight: float = Field(
        description=(
            "The Metric's weight when the run started, a number above 0. Weights are relative: the Composite "
            "divides each by their sum, so 2, 1 and 1 count as 0.5, 0.25 and 0.25."
        )
    )


class NormalizedMean(BaseModel):
    """A Metric's whole-run value on a scale from 0 to 1, where 1 is best."""

    kind: Literal["value"] = "value"
    evaluator_id: str = Field(description=_EVALUATOR_ID)
    metric_key: str = Field(description=_METRIC_KEY)
    value: float = Field(
        description=(
            "The Metric's mean on a scale from 0 to 1, where 1 is best. A Score's mean is placed in its "
            "`range` and turned around when `better` is 'lower'. A Label's is each label's share of the "
            "Sessions times its value on the Label's Scale, summed."
        )
    )


class NoNormalizedMean(BaseModel):
    """A Metric that cannot be put on the 0-to-1 scale in this run, and why."""

    kind: Literal["missing"] = "missing"
    evaluator_id: str = Field(description=_EVALUATOR_ID)
    metric_key: str = Field(description=_METRIC_KEY)
    reason: str = Field(
        description=(
            "Why the Metric has no Normalized mean, for example that the Score declares no `range` or "
            "`better`, that the Label declares no Scale, or that no Session has a value for it."
        )
    )


class Composite(BaseModel):
    """The Metric Group's single number for a run."""

    kind: Literal["value"] = "value"
    value: float = Field(
        description=(
            "The weighted mean of the weighted Metrics' Normalized means, from 0 to 1 where 1 is best. It is "
            "a number to compare runs by, not a verdict that the run is good."
        )
    )
    coverage: float = Field(
        description=(
            "The lowest share of judged Sessions that have a value, among the weighted Metrics. Low coverage "
            "means the Composite rests on few Sessions."
        )
    )


class NoComposite(BaseModel):
    """Why a run has no Composite."""

    kind: Literal["missing"] = "missing"
    reason: str = Field(
        description="Why there is no Composite, for example that the run's Metric Group had no weights when it started."
    )
    missing: list[NoNormalizedMean] = Field(
        default_factory=list,
        description=(
            "The weighted Metrics that have no Normalized mean in this run, each with why. The Composite needs "
            "every one of them, so fixing these is what brings it back."
        ),
    )


MetricNormalizedMean = Annotated[NormalizedMean | NoNormalizedMean, Field(discriminator="kind")]
CompositeResult = Annotated[Composite | NoComposite, Field(discriminator="kind")]

_NORMALIZED_MEANS = (
    "Each Metric on one scale from 0 to 1, where 1 is best. An entry with `kind` 'value' has the `value`; one "
    "with `kind` 'missing' has the `reason` it has none. Empty until the run has results."
)


class MetricDeclaration(BaseModel):
    """One Metric an Evaluator version declares in its ``@metrics`` decorator."""

    shape: Literal["score", "label"] | None = Field(
        default=None, description="What the Metric reports. Null only for a legacy version."
    )
    grain: str = Field(
        description="Where the Metric repeats, e.g. 'session', 'turn' or 'turn/retriever/outputs.documents[*]'"
    )
    vocabulary: list[str] | None = Field(default=None, description="The labels a closed Label may take")
    range: list[float] | None = Field(
        default=None, description="The scale a Score's values are on, as [low, high]. Null when none is declared."
    )
    better: Better | None = Field(
        default=None,
        description=(
            "Which way a change in the Score is an improvement: 'higher' or 'lower'. It says nothing about "
            "whether a value is good. Null when the Score declares none."
        ),
    )
    scale: dict[str, float] | None = Field(
        default=None,
        description=(
            "A closed Label's Scale: each word of the vocabulary mapped to a number from 0 to 1, higher is "
            "better. It orders the words; it does not say which pass. Null when the Label declares none, and "
            "for a Score."
        ),
    )


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
    """One scoring run's lifecycle, without its grid."""

    pipeline_experiment_run_id: str
    pipeline_experiment_id: str
    status: str = Field(description="Whether the fan-out finished. Not a verdict on the cells.")
    selection: Literal["SAMPLED", "HAND_PICKED"] = Field(
        description="How the Sessions were chosen. Only SAMPLED runs feed trends."
    )
    started_at: str | None = None
    ended_at: str | None = None
    composite_weights: list[CompositeWeight] | None = Field(
        default=None,
        description=(
            "The Composite formula the run started with: its Metric Group's weights that were usable then. The "
            "run's Composite always uses these, so editing the group's weights changes only later runs. Null "
            "when there was nothing to weigh, and the run then has no Composite."
        ),
    )
    created_at: str


class WeightedMetric(BaseModel):
    """How much one Metric counts toward its Metric Group's Composite."""

    evaluator_id: str = Field(description=_EVALUATOR_ID)
    metric_key: str = Field(description=_METRIC_KEY)
    weight: float = Field(
        description="The weight as saved, a number above 0. Weights are relative: they are divided by their sum."
    )
    usable: bool = Field(
        description=(
            "Whether the Evaluator's latest version still declares the Metric with a Normalized mean. A newer "
            "version can drop the key or remove its `range`, `better` or `scale`."
        )
    )
    unusable_reason: str | None = Field(
        default=None, description="Why the weight is not usable, for example that the key is no longer declared."
    )


class MetricGroup(BaseModel):
    """A named, ordered set of the workspace's Evaluators that a scoring run judges with."""

    metric_group_id: str
    name: str
    evaluator_ids: list[str]
    weights: list[WeightedMetric] = Field(
        default_factory=list,
        description=(
            "How much each Metric counts toward the group's Composite, in the group's Evaluator order. Empty "
            "when the group has no weights, and then its runs have no Composite. An unusable weight is kept "
            "and says why; it does not count in new runs."
        ),
    )
    created_at: str
    updated_at: str | None = None


class MetricGroupSummary(MetricGroup):
    """A Metric Group and, when a pipeline was asked about, its most recent scoring run there."""

    last_run: ExperimentRun | None = None


class ExperimentScoringCounts(BaseModel):
    """How a side's scoring evaluations ended."""

    cells: int = Field(description="Evaluations the scoring run made: Sessions times Metrics")
    succeeded: int
    errored: int = Field(description="Evaluations whose Evaluation Function broke. User code, not a score of 0.")
    failed: int = Field(description="Evaluations that never ran and can be retried")
    running: int


class ExperimentScoringRun(BaseModel):
    """One scoring run of a side, on one pipeline. Read it with ``get_experiment_run``."""

    pipeline_id: str
    experiment_run_id: str | None = Field(default=None, description="Null until it has started")


class ExperimentSide(BaseModel):
    """The candidate or the baseline of an Experiment, and how far it has got."""

    pipeline_id: str | None = Field(default=None, description="Null for a recorded baseline")
    pipeline_version_id: str | None = Field(default=None, description="Null for a recorded baseline")
    recorded: bool = Field(
        default=False,
        description="True for a baseline made of each test case's own recorded Session, with nothing replayed",
    )
    status: str = Field(description="REPLAYING, SCORING, ENDED or FAILED")
    reused_sessions: int
    replays_needed: int
    scoring_runs: list[ExperimentScoringRun] = Field(
        default_factory=list, description="One per pipeline this side scores on"
    )
    scoring_counts: ExperimentScoringCounts | None = Field(default=None, description="Null until scoring has started")
    error: str | None = Field(default=None, description="Why this side could not be scored")


class Experiment(BaseModel):
    """A comparison of a candidate pipeline version against a baseline on one Dataset, scored by one Metric Group."""

    experiment_id: str = Field(validation_alias="comparison_id")
    name: str
    dataset_id: str | None = Field(
        default=None, validation_alias="session_replay_dataset_id", description="Null once the Dataset is deleted"
    )
    dataset_name: str
    metric_group_id: str | None = Field(default=None, description="Null once the Metric Group is deleted")
    metric_group_name: str
    sessions_per_test_case: int
    replay_mode: str
    status: str = Field(
        description="REPLAYING while either side replays, then SCORING, then FAILED if either side failed, else ENDED"
    )
    candidate: ExperimentSide
    baseline: ExperimentSide
    created_at: str
    updated_at: str | None = None


class ExperimentValue(BaseModel):
    """One Metric on one side of an Experiment, over the test cases both sides have a value for."""

    value: float | None = Field(
        default=None,
        description="Mean over paired test cases of each test case's mean over its Sessions. Null for a Label.",
    )
    labels: dict[str, int] | None = Field(
        default=None, description="For a Label, how often each label occurred on the paired test cases"
    )
    sessions: int = Field(description="Sessions with a value, on the paired test cases")
    errored: int = Field(description="Sessions this side's Evaluator broke on, so produced no Metric")


class ExperimentMetric(BaseModel):
    """One Metric of the Metric Group, candidate against baseline."""

    evaluator_id: str
    evaluator_version_ids: list[str] = Field(description="Every Evaluator version that judged either side")
    metric_key: str
    shape: str | None = Field(default=None, description="score, label, or null when the rows disagree")
    candidate: ExperimentValue
    baseline: ExperimentValue
    delta: float | None = Field(default=None, description="candidate.value minus baseline.value")
    delta_pct: float | None = Field(
        default=None, description="delta as a percentage of the baseline's absolute value. Null if the baseline is 0."
    )
    paired_test_cases: int = Field(description="Test cases with a value on both sides, the only ones aggregated")
    better: Better | None = Field(default=None, description=_BETTER)
    change: Change = Field(default="unknown", description=_CHANGE)


class ExperimentPipelineMetric(BaseModel):
    """One default Metric every scoring run carries, candidate against baseline."""

    key: str = Field(
        description=(
            "DURATION is the pipeline's run time in seconds, summed over a Session's turns. TOKENS is every "
            "token the pipeline's LLM calls used. COST is what those calls cost in USD, counted only for "
            "Sessions whose every call is priced."
        )
    )
    candidate: ExperimentValue
    baseline: ExperimentValue
    delta: float | None = Field(default=None, description="candidate.value minus baseline.value")
    delta_pct: float | None = Field(
        default=None, description="delta as a percentage of the baseline's value. Null if the baseline is 0."
    )
    paired_test_cases: int = Field(description="Test cases with a value on both sides, the only ones aggregated")
    better: Better | None = Field(default=None, description=_BETTER)
    change: Change = Field(default="unknown", description=_CHANGE)


class ExperimentTestCaseValue(BaseModel):
    """One Metric's mean over a test case's Sessions, per side."""

    candidate: float | None = None
    baseline: float | None = None


class ExperimentTestCaseResult(BaseModel):
    """One test case: the Sessions each side scored, and each Score Metric's mean per side."""

    test_case_id: str = Field(validation_alias="session_replay_test_case_id")
    name: str
    candidate_session_ids: list[str]
    baseline_session_ids: list[str]
    values: dict[str, ExperimentTestCaseValue] = Field(
        default_factory=dict, description="Keyed by '{evaluator_id}:{metric_key}'"
    )
    pipeline_values: dict[str, ExperimentTestCaseValue] = Field(
        default_factory=dict, description="Keyed by DURATION, TOKENS and COST"
    )


class ExperimentSideHeadline(BaseModel):
    """One side's Metrics on the 0-to-1 scale, and the Metric Group's Composite over them."""

    normalized_means: list[MetricNormalizedMean] = Field(
        default_factory=list, description=_NORMALIZED_MEANS + " Also empty for a side that spans several runs."
    )
    composite: CompositeResult = Field(
        description=(
            "The side's Composite, from the weights its scoring run recorded when it started. With `kind` "
            "'missing' it says why there is none, for example the side is not scored yet."
        )
    )


class ExperimentHeadline(BaseModel):
    """Each side's single number: the Metric Group's Composite, with the Normalized means it weighs."""

    candidate: ExperimentSideHeadline
    baseline: ExperimentSideHeadline
    comparable: bool = Field(
        default=True,
        description=(
            "Whether the two Composites can be compared. False when the two runs weighed different Metrics or "
            "the same Metrics in different ratios: both values stand, but the difference would read a new "
            "formula as a change in quality, so report no change."
        ),
    )
    incomparable_reason: str | None = Field(
        default=None, description="Why the Composites cannot be compared. Null when `comparable` is true."
    )


class ExperimentResults(BaseModel):
    """An Experiment's results so far, as the API returns them. Partial while either side is still scoring."""

    model_config = ConfigDict(populate_by_name=True)

    experiment_id: str = Field(validation_alias="comparison_id")
    status: str = Field(description="REPLAYING, SCORING, ENDED or FAILED")
    metrics: list[ExperimentMetric] = Field(description="In the Metric Group's order, then by Metric key")
    pipeline_metrics: list[ExperimentPipelineMetric] = Field(default_factory=list)
    test_cases: list[ExperimentTestCaseResult] = Field(default_factory=list)
    headline: ExperimentHeadline | None = Field(
        default=None,
        description=(
            "Each side's Normalized means and Composite, so the two sides compare on one number when "
            "`comparable` is true. Null from an API that predates it."
        ),
    )


class ExperimentResultsReport(ExperimentResults):
    """An Experiment's results with the test cases capped."""

    total_test_cases: int
    test_cases_truncated: bool


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
    """One scoring run as Sessions by Evaluators, as the API returns it."""

    run: ExperimentRun
    evaluator_ids: list[str]
    rows: list[ExperimentRunRow] = Field(default_factory=list)
    counts: ExperimentRunCounts
    normalized_means: list[MetricNormalizedMean] = Field(default_factory=list, description=_NORMALIZED_MEANS)
    composite: CompositeResult | None = Field(
        default=None,
        description=(
            "The Metric Group's single number for the run, its recorded `run.composite_weights` applied to "
            "`normalized_means`. With `kind` 'value' it has the `value` and its `coverage`. With `kind` "
            "'missing' it has the `reason` there is none and lists in `missing` the weighted Metrics that "
            "have no Normalized mean. Null from an API that predates it."
        ),
    )


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
    """A scoring run read for explaining it: counts, per-metric summaries, then the rows."""

    run: ExperimentRun
    evaluator_ids: list[str]
    counts: ExperimentRunCounts
    metrics: list[MetricSummary] = Field(description="Computed over every row, including rows cut by max_rows")
    normalized_means: list[MetricNormalizedMean] = Field(default_factory=list, description=_NORMALIZED_MEANS)
    composite: CompositeResult | None = Field(
        default=None,
        description=(
            "The Metric Group's single number for the run, from 0 to 1 where 1 is best. See `run.composite_weights` "
            "for the formula. With `kind` 'missing' it has the `reason` there is none and the weighted Metrics "
            "that have no Normalized mean in `missing`. Null from an API that predates it."
        ),
    )
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


class EvaluationTryResult(BaseModel):
    """What an ad-hoc try found, as hub-api returns it. Never persisted; it ages out within the hour."""

    session_id: str
    outcome: Literal["SUCCEEDED", "ERRORED"] | None = None
    metrics: list[MetricRow] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)
    trace: dict[str, Any] | None = Field(default=None, description="The judge's own haystack-trace/v1 artifact")
    error_detail: dict[str, Any] | None = None


class TryState(BaseModel):
    """Where an ad-hoc try stands: still running, finished with a result, or aged out."""

    status: Literal["RUNNING", "READY", "EXPIRED"]
    result: EvaluationTryResult | None = None


class TraceSummary(BaseModel):
    """What an evaluator did while judging, without the Session content its trace quotes."""

    tool_calls: list[str] = Field(default_factory=list, description="Session Tools it called, in order")
    failed: bool = Field(description="Whether the evaluator's own run failed")


class TryReport(BaseModel):
    """An ad-hoc try, read for the assistant."""

    status: Literal["RUNNING", "READY", "EXPIRED"] = Field(
        description="RUNNING: poll get_evaluation_try with try_id. EXPIRED: the result aged out, try again."
    )
    try_id: str
    session_id: str | None = None
    outcome: Literal["SUCCEEDED", "ERRORED"] | None = Field(
        default=None, description="ERRORED means the evaluator's code broke; read error_detail"
    )
    metrics: list[MetricRow] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list, description="The turns judged, in order")
    trace_summary: TraceSummary | None = None
    error_detail: dict[str, Any] | None = None


class SessionReplayRun(BaseModel):
    """A session replay run, as hub-api returns it."""

    session_replay_run_id: str
    pipeline_version_id: str
    status: str = Field(description="CREATED, STARTED, ENDED or FAILED")
    source_session_id: str
    replay_mode: str | None = None
    trace_ids: list[str] = Field(default_factory=list, description="The traces the replay produced, in order")
    error_detail: dict[str, Any] | None = None


class SessionReplayReport(BaseModel):
    """A session replay, read for the assistant: what was replayed, and the Session it produced."""

    status: str = Field(
        description="ENDED or FAILED once done; CREATED or STARTED: poll get_session_replay with replay_run_id"
    )
    replay_run_id: str
    source_session_id: str
    replayed_session_id: str | None = Field(
        default=None, description="The new Session the replay produced; pass it to try_evaluator"
    )
    pipeline_version_id: str
    replay_mode: str | None = Field(
        default=None, description="FIRST_USER_MESSAGE replays the first turn only; ALL_USER_MESSAGES every turn"
    )
    trace_ids: list[str] = Field(default_factory=list)
    error_detail: dict[str, Any] | None = None
