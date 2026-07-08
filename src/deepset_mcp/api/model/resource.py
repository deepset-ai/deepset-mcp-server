# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for the model API."""

import builtins
import logging
from typing import TYPE_CHECKING, Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.model.models import Model, ModelList, ModelProvider
from deepset_mcp.api.model.protocols import ModelResourceProtocol
from deepset_mcp.api.transport import raise_for_status

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol

# Safety bound on the number of pages fetched when filtering locally, to guard against a
# pathological API response (e.g. `has_more` never turning False).
_MAX_FILTER_PAGES = 50
_FILTER_FETCH_PAGE_SIZE = 100


def _matches_filters(entry: Model, provider: ModelProvider | str | None, model_name: str | None) -> bool:
    """Check whether a model matches the given provider/model-name filters."""
    if provider is not None and entry.provider.lower() != provider.lower():
        return False

    if model_name is not None:
        if entry.model is None or model_name.lower() not in entry.model.lower():
            return False

    return True


class ModelResource(ModelResourceProtocol):
    """Manages interactions with the deepset model API."""

    def __init__(self, client: "AsyncClientProtocol", workspace: str) -> None:
        """Initialize a ModelResource instance.

        :param client: The async client protocol instance.
        :param workspace: The workspace to use.
        """
        self._client = client
        self._workspace = workspace

    async def list(
        self,
        limit: int = 100,
        page_number: int = 1,
        connected: bool | None = None,
        provider: ModelProvider | str | None = None,
        model: str | None = None,
    ) -> ModelList:
        """List the models including their configuration options available for the configured workspace.

        :param limit: Maximum number of models to return per page.
        :param page_number: The page to fetch, starting at 1.
        :param connected: If set, only return models for which the workspace does (True) or
            does not (False) have a working integration.
        :param provider: If set, only return models from this provider (case-insensitive, exact match).
            Accepts a `ModelProvider` value or any other provider name as a plain string.
            Since the API does not support this filter, all models are fetched and filtered locally.
        :param model: If set, only return models whose `model` field contains this value
            (case-insensitive, substring match). Since the API does not support this filter,
            all models are fetched and filtered locally.
        :returns: A page of models including their configuration options.
        """
        workspace = await self._client.workspaces().get(self._workspace)

        if provider is None and model is None:
            return await self._fetch_page(
                workspace_id=str(workspace.workspace_id), limit=limit, page_number=page_number, connected=connected
            )

        all_models = await self._fetch_all(workspace_id=str(workspace.workspace_id), connected=connected)
        filtered = [m for m in all_models if _matches_filters(m, provider, model)]

        start = (page_number - 1) * limit
        end = start + limit

        return ModelList(data=filtered[start:end], has_more=end < len(filtered), total=len(filtered))

    async def _fetch_all(self, workspace_id: str, connected: bool | None) -> builtins.list[Model]:
        """Fetch every model available for the workspace by paging through the API."""
        all_models: builtins.list[Model] = []
        page_number = 1

        for _ in range(_MAX_FILTER_PAGES):
            page = await self._fetch_page(
                workspace_id=workspace_id, limit=_FILTER_FETCH_PAGE_SIZE, page_number=page_number, connected=connected
            )
            all_models.extend(page.data)
            if not page.has_more:
                break
            page_number += 1
        else:
            logger.warning(
                "Stopped fetching models for workspace '%s' after %d pages; results may be incomplete.",
                self._workspace,
                _MAX_FILTER_PAGES,
            )

        return all_models

    async def _fetch_page(self, workspace_id: str, limit: int, page_number: int, connected: bool | None) -> ModelList:
        """Fetch a single page of models directly from the API."""
        params: dict[str, Any] = {"limit": limit, "page_number": page_number}
        if connected is not None:
            params["connected"] = connected

        resp = await self._client.request(
            endpoint=f"v2/workspaces/{workspace_id}/models",
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return ModelList.model_validate(resp.json)
