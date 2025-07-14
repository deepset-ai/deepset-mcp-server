# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Protocol definitions for integrations resource."""

from typing import TYPE_CHECKING, Protocol

from deepset_mcp.api.integrations.models import Integration, IntegrationList, IntegrationProvider

if TYPE_CHECKING:
    pass


class IntegrationResourceProtocol(Protocol):
    """Protocol for integration resource operations."""

    async def list(self) -> IntegrationList:
        """Retrieve all integrations.

        :returns: IntegrationList containing all available integrations.
        """
        ...

    async def get(self, provider: IntegrationProvider) -> Integration:
        """Retrieve a specific integration by provider.

        :param provider: The integration provider to retrieve.
        :returns: Integration instance for the specified provider.
        """
        ...
