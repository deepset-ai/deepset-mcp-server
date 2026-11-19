# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Protocol

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
    ExperimentResults,
    ExperimentRun,
    ExperimentRunGrid,
    ExperimentUpdatePlan,
    GoalAggregation,
    GoalCategory,
    GoalExperimentStarted,
    GoalRunPreview,
    GoalRunSource,
    GoalRunSummary,
    NewTestCase,
    SessionList,
    SessionReplayRun,
    TestCase,
    TryState,
)


class EvaluationResourceProtocol(Protocol):
    """Protocol defining the implementation for EvaluationResource."""

    async def list_evaluators(self, limit: int = 200, archived: bool | None = None) -> list[Evaluator]:
        """List the workspace's Evaluators."""
        ...

    async def get_evaluator(self, evaluator_id: str) -> Evaluator:
        """Fetch one Evaluator with every version."""
        ...

    async def get_evaluator_version(self, evaluator_id: str, version_id: str) -> EvaluatorVersion:
        """Fetch one Evaluator version with its source."""
        ...

    async def list_evaluation_goals(self, pipeline_name: str) -> list[EvaluationGoal]:
        """List the Evaluation Goals set on one pipeline, oldest first."""
        ...

    async def create_evaluation_goal(
        self,
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
    ) -> EvaluationGoal:
        """Create an Evaluation goal on one pipeline."""
        ...

    async def get_evaluation_goal(self, pipeline_name: str, evaluation_goal_id: str) -> EvaluationGoal:
        """Fetch one Evaluation goal of a pipeline."""
        ...

    async def update_evaluation_goal(
        self,
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
    ) -> EvaluationGoal:
        """Replace an Evaluation goal: every field is sent."""
        ...

    async def delete_evaluation_goal(self, pipeline_name: str, evaluation_goal_id: str) -> None:
        """Delete an Evaluation goal."""
        ...

    async def list_experiment_runs(self, pipeline_name: str, limit: int = 20) -> list[GoalRunSummary]:
        """List the goal runs users started on one pipeline, newest first."""
        ...

    async def list_session_experiment_runs(
        self, pipeline_name: str, session_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List the scoring runs that judged one Session, newest first."""
        ...

    async def evaluate_goals(self, pipeline_name: str, source: GoalRunSource | None = None) -> EvaluateGoalsAccepted:
        """Start a scoring run of the pipeline's Evaluation goals, or return the one already going."""
        ...

    async def preview_goal_run(
        self, pipeline_name: str, source: GoalRunSource, sessions_per_test_case: int | None = None
    ) -> GoalRunPreview:
        """Size what a goal run, or with ``sessions_per_test_case`` an Experiment, would judge."""
        ...

    async def run_evaluator(self, pipeline_name: str, evaluator_version_id: str, session_id: str) -> str:
        """Start one Evaluator version on one Session and return the Evaluation Run id to poll."""
        ...

    async def list_evaluation_runs(self, pipeline_name: str, limit: int = 50) -> list[EvaluationRun]:
        """List a pipeline's Evaluation Runs, newest first."""
        ...

    async def get_evaluation_run(self, pipeline_name: str, evaluation_run_id: str) -> EvaluationRun:
        """Read one Evaluation Run: its progress, or its Metrics."""
        ...

    async def get_experiment_run(
        self,
        pipeline_name: str,
        run_id: str,
        origin: str | None = None,
        deployment_id: str | None = None,
        pipeline_version_id: str | None = None,
        session_id: str | None = None,
    ) -> ExperimentRunGrid:
        """Fetch one scoring run as a grid."""
        ...

    async def create_experiment(
        self,
        pipeline_name: str,
        name: str,
        dataset_id: str,
        candidate_pipeline_version_id: str,
        baseline_pipeline_version_id: str | None = None,
        sessions_per_test_case: int = 1,
        replay_mode: str = "FIRST_USER_MESSAGE",
    ) -> GoalExperimentStarted:
        """Start an Experiment scored against the pipeline's Evaluation goals."""
        ...

    async def list_experiments(self, pipeline_name: str | None = None, limit: int = 50) -> list[Experiment]:
        """List the workspace's Experiments, optionally only those touching one pipeline."""
        ...

    async def get_experiment_results(self, experiment_id: str) -> ExperimentResults:
        """Fetch an Experiment's results, candidate against baseline."""
        ...

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
        """List a pipeline's Sessions that a run can judge."""
        ...

    async def start_try(
        self, pipeline_name: str, python_code: str, session_id: str, test_case_id: str | None = None
    ) -> str:
        """Start an ad-hoc try of Evaluator source on one Session."""
        ...

    async def get_try(self, pipeline_name: str, try_id: str) -> TryState:
        """Read an ad-hoc try."""
        ...

    async def start_session_replay(
        self,
        pipeline_name: str,
        session_id: str,
        pipeline_version_id: str,
        replay_mode: str | None = None,
        setup_source: str | None = None,
        cleanup_source: str | None = None,
    ) -> str:
        """Start replaying a Session against a pipeline version."""
        ...

    async def get_session_replay(self, pipeline_name: str, replay_run_id: str) -> SessionReplayRun:
        """Read a session replay run."""
        ...

    async def list_datasets(self, pipeline_name: str | None = None, limit: int = 50) -> list[DatasetSummary]:
        """List the workspace's Datasets, optionally only those with a test case on one pipeline."""
        ...

    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Fetch one Dataset with its test cases."""
        ...

    async def create_dataset(
        self, name: str, pipeline_name: str | None = None, test_cases: list[NewTestCase] | None = None
    ) -> Dataset:
        """Create a Dataset, optionally with its first test cases."""
        ...

    async def update_dataset(self, dataset_id: str, name: str) -> Dataset:
        """Rename a Dataset."""
        ...

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a Dataset and its test cases."""
        ...

    async def add_test_cases(
        self, dataset_id: str, test_cases: list[NewTestCase], pipeline_name: str | None = None
    ) -> Dataset:
        """Append test cases to a Dataset."""
        ...

    async def copy_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        """Copy existing test cases into a Dataset."""
        ...

    async def remove_test_cases(self, dataset_id: str, test_case_ids: list[str]) -> Dataset:
        """Remove test cases from a Dataset."""
        ...

    async def update_test_case(self, dataset_id: str, test_case_id: str, changes: dict[str, Any]) -> TestCase:
        """Change one test case; a field left out of ``changes`` is kept, one sent as None is removed."""
        ...

    async def create_evaluator(self, name: str, python_code: str) -> Evaluator:
        """Create an Evaluator and its first version."""
        ...

    async def update_evaluator(
        self, evaluator_id: str, name: str | None = None, python_code: str | None = None
    ) -> Evaluator:
        """Rename an Evaluator, add a version of its source, or both."""
        ...

    async def set_evaluator_archived(self, evaluator_id: str, archived: bool) -> Evaluator:
        """Archive or unarchive an Evaluator."""
        ...

    async def list_evaluator_templates(self) -> list[EvaluatorTemplate]:
        """List the built-in Evaluator templates."""
        ...

    async def get_experiment(self, experiment_id: str) -> ExperimentDetail:
        """Fetch one Experiment with its test cases and each side's progress."""
        ...

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
        """Rename an Experiment or change a side; a changed side is replayed and scored again."""
        ...

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
        """Plan an update without changing anything."""
        ...

    async def rerun_failed_experiment(self, experiment_id: str, replays: bool = False) -> Experiment:
        """Judge again the failed evaluations, or with ``replays`` replay again the failed replays."""
        ...

    async def rescore_experiment(self, experiment_id: str) -> Experiment:
        """Score both sides again with the Evaluators as they are now."""
        ...

    async def delete_experiment(self, experiment_id: str) -> None:
        """Delete an Experiment; its Sessions, replays and scoring runs are kept."""
        ...
