# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for the model API."""

import logging
from typing import TYPE_CHECKING, Any

from deepset_mcp.api.exceptions import UnexpectedAPIError
from deepset_mcp.api.model.models import ModelList
from deepset_mcp.api.model.protocols import ModelResourceProtocol
from deepset_mcp.api.transport import raise_for_status

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


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
    ) -> ModelList:
        """List the models including their configuration options available for the configured workspace.

        :param limit: Maximum number of models to return per page.
        :param page_number: The page to fetch, starting at 1.
        :param connected: If set, only return models for which the workspace does (True) or
            does not (False) have a working integration.
        :returns: A page of models including their configuration options.
        """
        workspace = await self._client.workspaces().get(self._workspace)

        params: dict[str, Any] = {"limit": limit, "page_number": page_number}
        if connected is not None:
            params["connected"] = connected

        resp = await self._client.request(
            endpoint=f"v2/workspaces/{workspace.workspace_id}/models",
            method="GET",
            params=params,
        )

        raise_for_status(resp)

        if resp.json is None:
            raise UnexpectedAPIError(status_code=resp.status_code, message="Empty response", detail=None)

        return ModelList.model_validate(resp.json)
