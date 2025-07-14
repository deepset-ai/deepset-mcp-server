# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol

from deepset_mcp.api.shared_models import DeepsetUser


class UserResourceProtocol(Protocol):
    """Protocol defining the implementation for UserResource."""

    async def get(self, user_id: str) -> DeepsetUser:
        """Get user information by user ID."""
        ...
