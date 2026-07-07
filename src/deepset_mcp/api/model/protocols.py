# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocol definitions for the model resource."""

from typing import Protocol

from deepset_mcp.api.model.models import ModelList


class ModelResourceProtocol(Protocol):
    """Protocol for model resource operations."""

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
        ...
