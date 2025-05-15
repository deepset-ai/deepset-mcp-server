from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    """A deepset user."""

    given_name: str
    family_name: str
    user_id: str


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
    description: Optional[str] = None
    config_yaml: str
    workspace_id: str
    settings: dict
    desired_status: str
    deployed_at: Optional[datetime] = None
    last_edited_at: Optional[datetime] = None
    max_index_replica_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: User
    last_edited_by: Optional[User] = None
    status: IndexStatus


class IndexList(BaseModel):
    """Response model for listing indexes."""

    data: list[Index]
    has_more: bool
    total: int