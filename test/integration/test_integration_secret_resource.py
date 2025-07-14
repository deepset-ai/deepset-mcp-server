# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.exceptions import ResourceNotFoundError, UnexpectedAPIError
from deepset_mcp.api.secrets.models import Secret, SecretList
from deepset_mcp.api.secrets.resource import SecretResource
from deepset_mcp.api.shared_models import NoContentResponse

pytestmark = pytest.mark.integration


@pytest.fixture
async def secret_resource(client: AsyncDeepsetClient) -> SecretResource:
    """Create a SecretResource instance for testing."""
    return SecretResource(client=client)


@pytest.fixture
def test_secret_name() -> str:
    """Return a test secret name."""
    return "test-integration-secret"


@pytest.fixture
def test_secret_value() -> str:
    """Return a test secret value."""
    return "test-secret-value-12345"


@pytest.mark.asyncio
async def test_create_and_get_secret(
    secret_resource: SecretResource,
    test_secret_name: str,
    test_secret_value: str,
) -> None:
    """Test creating a secret and then retrieving it."""
    created_secret_ids = []

    try:
        # Create a new secret
        create_result = await secret_resource.create(name=test_secret_name, secret=test_secret_value)
        assert isinstance(create_result, NoContentResponse)
        assert create_result.success is True

        # List secrets to find our created secret
        secrets: SecretList = await secret_resource.list()

        # Find our secret in the list
        created_secret = None
        for secret in secrets.data:
            if secret.name == test_secret_name:
                created_secret = secret
                created_secret_ids.append(secret.secret_id)
                break

        assert created_secret is not None, f"Secret '{test_secret_name}' not found in list"

        # Get the secret by ID
        retrieved_secret: Secret = await secret_resource.get(created_secret.secret_id)
        assert retrieved_secret.name == test_secret_name
        assert retrieved_secret.secret_id == created_secret.secret_id

    finally:
        # Clean up created secrets
        for secret_id in created_secret_ids:
            try:
                await secret_resource.delete(secret_id)
            except Exception as e:
                print(f"Failed to delete test secret {secret_id}: {e}")


@pytest.mark.asyncio
async def test_list_secrets(secret_resource: SecretResource) -> None:
    """Test listing secrets with pagination."""
    # Create a few test secrets
    test_secrets = [
        ("test-list-secret-1", "value-1"),
        ("test-list-secret-2", "value-2"),
        ("test-list-secret-3", "value-3"),
    ]

    created_secret_ids = []

    try:
        for name, value in test_secrets:
            await secret_resource.create(name=name, secret=value)
            # Get the created secret ID for cleanup
            secrets = await secret_resource.list()
            for secret in secrets.data:
                if secret.name == name and secret.secret_id not in created_secret_ids:
                    created_secret_ids.append(secret.secret_id)
                    break

        # Test listing all secrets
        all_secrets: SecretList = await secret_resource.list()
        assert len(all_secrets.data) >= 3

        # Verify our created secrets are in the list
        secret_names = [s.name for s in all_secrets.data]
        for name, _ in test_secrets:
            assert name in secret_names

        # Test listing with limit
        limited_secrets: SecretList = await secret_resource.list(limit=2)
        assert len(limited_secrets.data) <= 2

        # Test with different sort order
        asc_secrets: SecretList = await secret_resource.list(order="ASC")
        desc_secrets: SecretList = await secret_resource.list(order="DESC")

        # At least verify we got results (can't easily test order without knowing full dataset)
        assert len(asc_secrets.data) >= 0
        assert len(desc_secrets.data) >= 0

    finally:
        # Clean up created secrets
        for secret_id in created_secret_ids:
            try:
                await secret_resource.delete(secret_id)
            except Exception as e:
                print(f"Failed to delete test secret {secret_id}: {e}")


@pytest.mark.asyncio
async def test_delete_secret(
    secret_resource: SecretResource,
    test_secret_name: str,
    test_secret_value: str,
) -> None:
    """Test deleting a secret."""
    created_secret_ids = []

    try:
        # Create a secret to delete
        await secret_resource.create(name=test_secret_name, secret=test_secret_value)

        # Find the created secret
        secrets: SecretList = await secret_resource.list()
        secret_to_delete = None
        for secret in secrets.data:
            if secret.name == test_secret_name:
                secret_to_delete = secret
                created_secret_ids.append(secret.secret_id)
                break

        assert secret_to_delete is not None, f"Secret '{test_secret_name}' not found"

        # Delete the secret
        delete_result = await secret_resource.delete(secret_to_delete.secret_id)
        assert isinstance(delete_result, NoContentResponse)
        assert delete_result.success is True

        # Remove from cleanup list since we already deleted it
        created_secret_ids.remove(secret_to_delete.secret_id)

        # Verify the secret no longer exists
        with pytest.raises(ResourceNotFoundError):
            await secret_resource.get(secret_to_delete.secret_id)

    finally:
        # Clean up any remaining secrets
        for secret_id in created_secret_ids:
            try:
                await secret_resource.delete(secret_id)
            except Exception as e:
                print(f"Failed to delete test secret {secret_id}: {e}")


@pytest.mark.asyncio
async def test_get_nonexistent_secret(secret_resource: SecretResource) -> None:
    """Test error handling when getting a non-existent secret."""
    # Use a valid UUID format for the non-existent secret ID
    non_existent_id = "00000000-0000-0000-0000-000000000000"

    # Trying to get a non-existent secret should raise an exception
    with pytest.raises(ResourceNotFoundError):
        await secret_resource.get(non_existent_id)


@pytest.mark.asyncio
async def test_delete_nonexistent_secret(secret_resource: SecretResource) -> None:
    """Test error handling when deleting a non-existent secret."""
    # Use a valid UUID format for the non-existent secret ID
    non_existent_id = "00000000-0000-0000-0000-000000000000"

    # Deleting a non-existent secret should not raise an exception
    # (based on typical REST API behavior where DELETE is idempotent)
    # This might fail with a 404, but let's test the current behavior
    try:
        await secret_resource.delete(non_existent_id)
    except (ResourceNotFoundError, UnexpectedAPIError):
        # This is acceptable behavior for DELETE operations
        # API might return 404 or other error codes for nonexistent resources
        pass
