from datetime import datetime
from typing import Any

from pydantic import BaseModel

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


class IndexList(BaseModel):
    """Response model for listing indexes."""

    data: list[Index]
    has_more: bool
    total: int
