# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource for the evaluation API: Evaluators, Experiments, their runs, and Sessions."""

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from deepset_mcp.api import ids
from deepset_mcp.api.evaluation.models import (
    Evaluator,
    EvaluatorVersion,
    Experiment,
    ExperimentRun,
    ExperimentRunGrid,
    SessionList,
)
from deepset_mcp.api.evaluation.protocols import EvaluationResourceProtocol
from deepset_mcp.api.transport import raise_for_status

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


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

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self._client.request(endpoint=path, method="GET", params=params)
        raise_for_status(resp)
        return resp.json

    @staticmethod
    def _path(*segments: str) -> str:
        return "v2/workspaces/" + "/".join(quote(segment, safe="") for segment in segments)

    async def _evaluators_path(self, *parts: str) -> str:
        return self._path(await ids.workspace_id(self._client, self._workspace), "evaluators", *parts)

    async def _pipeline_path(self, pipeline_name: str, *parts: str) -> str:
        workspace_id, pipeline_id = await ids.workspace_and_pipeline_ids(self._client, self._workspace, pipeline_name)
        return self._path(workspace_id, "pipelines", pipeline_id, *parts)

    async def list_evaluators(self, limit: int = 200) -> list[Evaluator]:
        """List the workspace's Evaluators, each with its newest version but no source.

        :param limit: Maximum number of Evaluators to return (the API caps it at 200).
        :returns: The Evaluators.
        """
        data = await self._get(await self._evaluators_path(), {"limit": limit})
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

    async def list_experiments(self, pipeline_name: str, limit: int = 200) -> list[Experiment]:
        """List a pipeline's Experiments.

        :param pipeline_name: Name of the pipeline.
        :param limit: Maximum number of Experiments to return (the API caps it at 200).
        :returns: The Experiments.
        """
        data = await self._get(await self._pipeline_path(pipeline_name, "experiments"), {"limit": limit})
        return [Experiment.model_validate(item) for item in data or []]

    async def list_experiment_runs(
        self, pipeline_name: str, experiment_id: str, limit: int = 50
    ) -> list[ExperimentRun]:
        """List an Experiment's runs, newest first, without their grids.

        :param pipeline_name: Name of the pipeline.
        :param experiment_id: The Experiment's id.
        :param limit: Maximum number of runs to return.
        :returns: The runs.
        """
        path = await self._pipeline_path(pipeline_name, "experiments", experiment_id, "runs")
        return [ExperimentRun.model_validate(item) for item in await self._get(path, {"limit": limit}) or []]

    async def get_experiment_run(self, pipeline_name: str, experiment_id: str, run_id: str) -> ExperimentRunGrid:
        """Fetch one Experiment run as a grid of Sessions by Evaluators.

        :param pipeline_name: Name of the pipeline.
        :param experiment_id: The Experiment's id.
        :param run_id: The run's id.
        :returns: The grid.
        """
        path = await self._pipeline_path(pipeline_name, "experiments", experiment_id, "runs", run_id)
        return ExperimentRunGrid.model_validate(await self._get(path))

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
        """List a pipeline's Sessions that a run can judge, newest last activity first.

        :param pipeline_name: Name of the pipeline.
        :param origin: Only Sessions whose every turn came from SERVICE, PIPELINE_RUN or PLAYGROUND.
        :param deployment_id: Only Sessions whose every turn this Service served.
        :param pipeline_version_id: Only Sessions whose every turn this pipeline version served.
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
            "from": since,
            "to": until,
            "limit": limit,
            "cursor": cursor,
        }
        path = await self._pipeline_path(pipeline_name, "sessions")
        data = await self._get(path, {k: v for k, v in params.items() if v is not None})
        return SessionList.model_validate(data or {"data": []})
