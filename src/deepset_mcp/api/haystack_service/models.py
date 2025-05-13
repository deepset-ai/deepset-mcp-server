from typing import Any

from pydantic import BaseModel


class HaystackComponentSchema(BaseModel):
    """Model for the Haystack component schema response."""

    model_config = {"extra": "allow"}

    __root__: dict[str, Any]
