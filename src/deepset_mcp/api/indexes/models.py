# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from rich.repr import Result

from deepset_mcp.api.shared_models import DeepsetUser


class IndexStatus(BaseModel):
    """Status information about documents in an index."""

    pending_file_count: int
    failed_file_count: int
    indexed_no_documents_file_count: int
    indexed_file_count: int
    total_file_count: int


class Index(BaseModel):
    """A deepset index."""

    pipeline_index_id: str
    name: str
    description: str | None = None
    config_yaml: str
    workspace_id: str
    settings: dict[str, Any]
    desired_status: str
    deployed_at: datetime | None = None
    last_edited_at: datetime | None = None
    max_index_replica_count: int
    created_at: datetime
    updated_at: datetime | None = None
    created_by: DeepsetUser
    last_edited_by: DeepsetUser | None = None
    status: IndexStatus

    def __rich_repr__(self) -> Result:
        """Used to display the model in an LLM friendly way."""
        yield "name", self.name
        yield "description", self.description, None
        yield "desired_status", self.desired_status
        yield "status", self.status
        yield "status", self.status
        yield "created_by", f"{self.created_by.given_name} {self.created_by.family_name} ({self.created_by.id})"
        yield "created_at", self.created_at.strftime("%m/%d/%Y %I:%M:%S %p")
        yield (
            "last_edited_by",
            f"{self.last_edited_by.given_name} {self.last_edited_by.family_name} ({self.last_edited_by.id})"
            if self.last_edited_by
            else None,
        )
        yield "last_edited_at", self.last_edited_at.strftime("%m/%d/%Y %I:%M:%S %p") if self.last_edited_at else None
        yield "config_yaml", self.config_yaml if self.config_yaml is not None else "Get full index to see config."


class IndexList(BaseModel):
    """Response model for listing indexes."""

    data: list[Index]
    has_more: bool
    total: int
