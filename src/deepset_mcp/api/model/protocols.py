# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocol definitions for the model resource."""

from typing import Protocol

from deepset_mcp.api.model.models import ModelList, ModelProvider


class ModelResourceProtocol(Protocol):
    """Protocol for model resource operations."""

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
        ...
