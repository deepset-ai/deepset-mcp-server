# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from rich.repr import Result

from deepset_mcp.api.shared_models import DeepsetUser


class IndexStatus(BaseModel):
    """Status information about documents in an index."""

    pending_file_count: int
    "Number of files waiting to be processed"
    failed_file_count: int
    "Number of files that failed during indexing"
    indexed_no_documents_file_count: int
    "Number of files indexed but containing no documents"
    indexed_file_count: int
    "Number of successfully indexed files"
    total_file_count: int
    "Total number of files in the index"


class Index(BaseModel):
    """A deepset index."""

    pipeline_index_id: str
    "Unique identifier for the pipeline index"
    name: str
    "Human-readable name of the index"
    description: str | None = None
    "Optional description of the index purpose and contents"
    yaml_config: str = Field(alias="config_yaml")
    "YAML configuration defining the index structure and settings"
    workspace_id: str
    "ID of the workspace containing this index"
    settings: dict[str, Any]
    "Index configuration settings and parameters"
    desired_status: str
    "Target operational status for the index"
    deployed_at: datetime | None = None
    "Timestamp when the index was deployed"
    last_edited_at: datetime | None = None
    "Timestamp when the index was last modified"
    max_index_replica_count: int
    "Maximum number of replicas allowed for this index"
    created_at: datetime
    "Timestamp when the index was created"
    updated_at: datetime | None = None
    "Timestamp when the index was last updated"
    created_by: DeepsetUser
    "User who created the index"
    last_edited_by: DeepsetUser | None = None
    "User who last modified the index"
    status: IndexStatus
    "Current status information about documents in the index"

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
        yield "yaml_config", self.yaml_config if self.yaml_config is not None else "Get full index to see config."
