# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class NoContentResponse(BaseModel):
    """Response model for an empty response."""

    success: bool = True
    message: str = "No content"


class DeepsetUser(BaseModel):
    """Model representing a user on the deepset platform."""

    id: str = Field(alias="user_id")
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
