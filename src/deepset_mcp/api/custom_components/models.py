# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from pydantic import BaseModel

from deepset_mcp.api.shared_models import DeepsetUser


class CustomComponentInstallation(BaseModel):
    """Model representing a custom component installation."""

    custom_component_id: str
    status: str
    version: str
    created_by_user_id: str
    logs: list[dict[str, Any]]
    organization_id: str
    user_info: DeepsetUser | None = None


class CustomComponentInstallationList(BaseModel):
    """Model representing a list of custom component installations."""

    data: list[CustomComponentInstallation]
    total: int
    has_more: bool
