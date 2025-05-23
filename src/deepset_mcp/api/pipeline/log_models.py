from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineLog(BaseModel):
    """Model representing a single log entry from a pipeline."""

    log_id: str
    message: str
    logged_at: datetime
    level: str
    origin: str
    exceptions: str | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)


class PipelineLogList(BaseModel):
    """Model representing a paginated list of pipeline logs."""

    data: list[PipelineLog]
    has_more: bool
    total: int