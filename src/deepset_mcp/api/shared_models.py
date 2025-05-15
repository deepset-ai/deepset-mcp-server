from pydantic import BaseModel, Field


class DeepsetUser(BaseModel):
    """Model representing a user on the deepset platform."""

    id: str = Field(alias="user_id")
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
