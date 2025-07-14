# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Resource implementation for integrations API."""

import logging
from typing import TYPE_CHECKING

from deepset_mcp.api.integrations.models import Integration, IntegrationList, IntegrationProvider
from deepset_mcp.api.integrations.protocols import IntegrationResourceProtocol
from deepset_mcp.api.transport import raise_for_status

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deepset_mcp.api.protocols import AsyncClientProtocol


class IntegrationResource(IntegrationResourceProtocol):
    """Manages interactions with the deepset integrations API."""

    def __init__(self, client: "AsyncClientProtocol") -> None:
        """Initialize an IntegrationResource instance.

        :param client: The async client protocol instance.
        """
        self._client = client

    async def list(self) -> IntegrationList:
        """Retrieve all integrations.

        :returns: IntegrationList containing all available integrations.
        """
        resp = await self._client.request(
            endpoint="v1/model_registry_tokens",
            method="GET",
        )

        raise_for_status(resp)

        if resp.json is not None:
            integrations = [Integration.model_validate(item) for item in resp.json]
            return IntegrationList(integrations=integrations)
        else:
            return IntegrationList(integrations=[])

    async def get(self, provider: IntegrationProvider) -> Integration:
        """Retrieve a specific integration by provider.

        :param provider: The integration provider to retrieve.
        :returns: Integration instance for the specified provider.
        """
        resp = await self._client.request(
            endpoint=f"v1/model_registry_tokens/{provider.value}",
            method="GET",
        )

        raise_for_status(resp)

        return Integration.model_validate(resp.json)
