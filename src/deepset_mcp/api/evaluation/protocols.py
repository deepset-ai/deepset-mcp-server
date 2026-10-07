# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    Experiment,
    ExperimentRun,
    ExperimentRunGrid,
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

    async def list_experiments(self, pipeline_name: str, limit: int = 200) -> list[Experiment]:
        """List a pipeline's Experiments."""
        ...

    async def list_experiment_runs(
        self, pipeline_name: str, experiment_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List an Experiment's runs, newest first."""
        ...

    async def get_experiment_run(self, pipeline_name: str, experiment_id: str, run_id: str) -> ExperimentRunGrid:
        """Fetch one Experiment run as a grid."""
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
