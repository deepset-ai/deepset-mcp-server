# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.custom_components.models import CustomComponentInstallationList


class CustomComponentsProtocol(Protocol):
    """Protocol defining the implementation for CustomComponentsResource."""

    async def list_installations(
        self, limit: int = 20, page_number: int = 1, field: str = "created_at", order: str = "DESC"
    ) -> CustomComponentInstallationList:
        """List custom component installations."""
        ...

    async def get_latest_installation_logs(self) -> str | None:
        """Get the logs from the latest custom component installation."""
        ...
