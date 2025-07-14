# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.exceptions import ResourceNotFoundError
from deepset_mcp.api.shared_models import DeepsetUser
from deepset_mcp.api.user.resource import UserResource
from test.unit.conftest import BaseFakeClient


@pytest.mark.asyncio
async def test_get_user() -> None:
    """Test getting user information."""
    mock_user_data = {
        "user_id": "user_123",
        "given_name": "John",
        "family_name": "Doe",
        "email": "john.doe@example.com",
    }

    fake_client = BaseFakeClient(responses={"v1/users/user_123": mock_user_data})

    def users() -> UserResource:
        return UserResource(client=fake_client)

    fake_client.users = users  # type: ignore[method-assign]

    resource = fake_client.users()
    result = await resource.get("user_123")

    assert isinstance(result, DeepsetUser)
    assert result.id == "user_123"
    assert result.given_name == "John"
    assert result.family_name == "Doe"
    assert result.email == "john.doe@example.com"


@pytest.mark.asyncio
async def test_get_user_partial_data() -> None:
    """Test getting user information with partial data."""
    mock_user_data = {
        "user_id": "user_456",
        "given_name": "Jane",
        "family_name": None,
        "email": None,
    }

    fake_client = BaseFakeClient(responses={"v1/users/user_456": mock_user_data})

    def users() -> UserResource:
        return UserResource(client=fake_client)

    fake_client.users = users  # type: ignore[method-assign]

    resource = fake_client.users()
    result = await resource.get("user_456")

    assert isinstance(result, DeepsetUser)
    assert result.id == "user_456"
    assert result.given_name == "Jane"
    assert result.family_name is None
    assert result.email is None


@pytest.mark.asyncio
async def test_get_user_not_found() -> None:
    """Test getting user information when user doesn't exist."""
    fake_client = BaseFakeClient(responses={"v1/users/nonexistent": None})

    def users() -> UserResource:
        return UserResource(client=fake_client)

    fake_client.users = users  # type: ignore[method-assign]

    resource = fake_client.users()

    with pytest.raises(ResourceNotFoundError, match="User 'nonexistent' not found."):
        await resource.get("nonexistent")
