# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from pydantic import BaseModel

from deepset_mcp.api.shared_models import DeepsetUser


class CustomComponentInstallation(BaseModel):
    """Model representing a custom component installation."""

    custom_component_id: str
    "Unique identifier for the custom component"
    status: str
    "Current installation status of the component"
    version: str
    "Version number of the installed component"
    created_by_user_id: str
    "ID of the user who initiated the installation"
    logs: list[dict[str, Any]]
    "Installation log entries with timestamps and messages"
    organization_id: str
    "ID of the organization where the component is installed"
    user_info: DeepsetUser | None = None
    "Detailed information about the user who created the installation"
