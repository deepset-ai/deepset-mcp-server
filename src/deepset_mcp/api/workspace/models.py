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
    workspace_id: UUID
    languages: dict[str, Any]
    default_idle_timeout_in_seconds: int


class WorkspaceList(BaseModel):
    """Model representing a list of workspaces."""

    data: list[Workspace]
    has_more: bool = False
    total: int
