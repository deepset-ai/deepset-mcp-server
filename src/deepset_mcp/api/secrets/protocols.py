# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.shared_models import NoContentResponse


class SecretResourceProtocol(Protocol):
    """Protocol defining the implementation for SecretResource."""

    async def list(
        self,
        limit: int = 10,
        field: str = "created_at",
        order: str = "DESC",
    ) -> SecretList:
        """List secrets with pagination."""
        ...

    async def create(self, name: str, secret: str) -> NoContentResponse:
        """Create a new secret."""
        ...

    async def get(self, secret_id: str) -> Secret:
        """Get a specific secret by ID."""
        ...

    async def delete(self, secret_id: str) -> NoContentResponse:
        """Delete a secret by ID."""
        ...
