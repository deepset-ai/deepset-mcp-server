# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for IntegrationResource."""

import os

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.integrations.models import IntegrationProvider


@pytest.mark.asyncio
@pytest.mark.integration
class TestIntegrationResourceIntegration:
    """Integration tests for IntegrationResource.

    These tests run against the actual deepset API and require:
    - DEEPSET_API_KEY environment variable to be set
    - Valid API access
    """

    @pytest.fixture(autouse=True)
    def check_api_key(self) -> None:
        """Ensure API key is available for integration tests."""
        if not os.environ.get("DEEPSET_API_KEY"):
            pytest.skip("DEEPSET_API_KEY not set, skipping integration tests")

    async def test_list_integrations_real_api(self) -> None:
        """Test listing integrations against real API."""
        async with AsyncDeepsetClient() as client:
            # Act
            result = await client.integrations().list()

            # Assert
            # We can't assert specific content since it depends on the account configuration
            # but we can verify the structure is correct
            assert hasattr(result, "integrations")
            assert isinstance(result.integrations, list)

            # If there are integrations, verify their structure
            for integration in result.integrations:
                assert hasattr(integration, "invalid")
                assert hasattr(integration, "model_registry_token_id")
                assert hasattr(integration, "provider")
                assert hasattr(integration, "provider_domain")
                assert isinstance(integration.invalid, bool)
                assert isinstance(integration.provider, IntegrationProvider)
                assert isinstance(integration.provider_domain, str)

    async def test_get_integration_real_api(self) -> None:
        """Test getting a specific integration against real API.

        This test attempts to get an AWS Bedrock integration.
        If it doesn't exist, the test will expect a 404 error.
        """
        async with AsyncDeepsetClient() as client:
            try:
                # Act
                result = await client.integrations().get(IntegrationProvider.AWS_BEDROCK)

                # Assert - if we get a result, verify its structure
                assert hasattr(result, "invalid")
                assert hasattr(result, "model_registry_token_id")
                assert hasattr(result, "provider")
                assert hasattr(result, "provider_domain")
                assert isinstance(result.invalid, bool)
                assert result.provider == IntegrationProvider.AWS_BEDROCK
                assert isinstance(result.provider_domain, str)

            except Exception as e:
                # If the integration doesn't exist, we expect a 404-like error
                # The exact error type depends on the API implementation
                # This is acceptable for integration tests
                assert "404" in str(e) or "not found" in str(e).lower() or "Not Found" in str(e)
