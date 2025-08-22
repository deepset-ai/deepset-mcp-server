# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for workspace API responses."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class Workspace(BaseModel):
    """Model representing a workspace on the deepset platform."""

    name: str
    "Human-readable name of the workspace"
    workspace_id: UUID
    "Unique identifier for the workspace"
    languages: dict[str, Any]
    "Supported languages and their configuration settings"
    default_idle_timeout_in_seconds: int
    "Default timeout in seconds before workspace becomes idle"
