# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Models for search history API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchHistoryEntry(BaseModel):
    """A single search history entry from the deepset platform.

    Contains query, answers, prompts, feedback, and other metadata.
    """

    model_config = {"extra": "allow"}

    query: str | None = Field(default=None, description="The search query that was executed")
    answer: str | None = Field(default=None, description="The answer returned by the pipeline")
    created_at: str | None = Field(default=None, description="When the search was performed")
    pipeline_name: str | None = Field(default=None, description="Name of the pipeline used")
    feedback: list[dict[str, Any]] | None = Field(default=None, description="User feedback on the search")

    @field_validator("feedback", mode="before")
    @classmethod
    def _feedback_to_list(cls, v: Any) -> list[dict[str, Any]] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return [v]
        return None
