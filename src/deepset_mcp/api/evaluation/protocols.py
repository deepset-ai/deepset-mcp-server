# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    Experiment,
    ExperimentResults,
    ExperimentRun,
    ExperimentRunGrid,
    MetricGroup,
    SessionList,
    SessionReplayRun,
    TryState,
)


class EvaluationResourceProtocol(Protocol):
    """Protocol defining the implementation for EvaluationResource."""

    async def list_evaluators(self, limit: int = 200) -> list[Evaluator]:
        """List the workspace's Evaluators."""
        ...

    async def get_evaluator(self, evaluator_id: str) -> Evaluator:
        """Fetch one Evaluator with every version."""
        ...

    async def get_evaluator_version(self, evaluator_id: str, version_id: str) -> EvaluatorVersion:
        """Fetch one Evaluator version with its source."""
        ...

    async def list_metric_groups(self, limit: int = 200) -> list[MetricGroup]:
        """List the workspace's Metric Groups."""
        ...

    async def list_experiment_runs(
        self, pipeline_name: str, metric_group_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List a Metric Group's scoring runs on one pipeline, newest first."""
        ...

    async def get_experiment_run(self, pipeline_name: str, metric_group_id: str, run_id: str) -> ExperimentRunGrid:
        """Fetch one scoring run as a grid."""
        ...

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
    ) -> Experiment:
        """Create an Experiment comparing a candidate pipeline version against a baseline."""
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
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionList:
        """List a pipeline's Sessions that a run can judge."""
        ...

    async def start_try(self, pipeline_name: str, python_code: str, session_id: str) -> str:
        """Start an ad-hoc try of Evaluator source on one Session."""
        ...

    async def get_try(self, pipeline_name: str, try_id: str) -> TryState:
        """Read an ad-hoc try."""
        ...

    async def start_session_replay(
        self, pipeline_name: str, session_id: str, pipeline_version_id: str, replay_mode: str | None = None
    ) -> str:
        """Start replaying a Session against a pipeline version."""
        ...

    async def get_session_replay(self, pipeline_name: str, replay_run_id: str) -> SessionReplayRun:
        """Read a session replay run."""
        ...
