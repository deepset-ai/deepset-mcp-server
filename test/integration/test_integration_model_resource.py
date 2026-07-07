# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for ModelResource."""

import os

import pytest

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.model.models import ModelList

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestModelResourceIntegration:
    """Integration tests for ModelResource.

    These tests run against the actual deepset API and require:
    - DEEPSET_API_KEY environment variable to be set
    - Valid API access
    """

    @pytest.fixture(autouse=True)
    def check_api_key(self) -> None:
        """Ensure API key is available for integration tests."""
        if not os.environ.get("DEEPSET_API_KEY"):
            pytest.skip("DEEPSET_API_KEY not set, skipping integration tests")

    async def test_list_models_real_api(self, test_workspace: str) -> None:
        """Test listing models for a real workspace against the real API."""
        async with AsyncDeepsetClient() as client:
            result = await client.models(workspace=test_workspace).list()

            assert isinstance(result, ModelList)
            assert isinstance(result.data, list)
            assert isinstance(result.has_more, bool)
            assert isinstance(result.total, int)

            for model in result.data:
                assert isinstance(model.name, str)
                assert isinstance(model.provider, str)
