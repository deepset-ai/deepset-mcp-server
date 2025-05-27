import os

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError

skipif_no_api_key = pytest.mark.skipif(
    os.getenv("DEEPSET_API_KEY") is None,
    reason="DEEPSET_API_KEY environment variable not set",
)


@skipif_no_api_key
@pytest.mark.asyncio
async def test_get_user_invalid_id() -> None:
    """Test getting user with invalid ID."""
    async with AsyncDeepsetClient() as client:
        users = client.users()

        with pytest.raises(ResourceNotFoundError):
            await users.get("nonexistent_user_id")


@skipif_no_api_key
@pytest.mark.asyncio
async def test_get_user_empty_id() -> None:
    """Test getting user with empty ID."""
    async with AsyncDeepsetClient() as client:
        users = client.users()

        with pytest.raises((ValueError, ResourceNotFoundError)):
            await users.get("")
