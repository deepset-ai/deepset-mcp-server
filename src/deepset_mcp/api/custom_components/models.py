from typing import Any

from pydantic import BaseModel


class CustomComponentInstallation(BaseModel):
    """Model representing a custom component installation."""
    
    custom_component_id: str
    status: str
    version: str
    created_by_user_id: str
    created_at: str
    logs: list[dict[str, Any]]


class CustomComponentInstallationList(BaseModel):
    """Model representing a list of custom component installations."""
    
    data: list[CustomComponentInstallation]
    total: int
    has_more: bool


class User(BaseModel):
    """Model representing a user."""
    
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
