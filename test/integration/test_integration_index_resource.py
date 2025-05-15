import os

import pytest
from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.api.indexes.models import Index, IndexList


@pytest.mark.skipif(
    os.environ.get("INTEGRATION_TEST") == "0", reason="Integration test not enabled"
)
class TestIndexResourceIntegration:
    """Integration tests for the IndexResource."""

    async def test_list_indexes(self) -> None:
        """Test that listing indexes works with the real API."""
        async with AsyncDeepsetClient() as client:
            result = await client.indexes("default").list()
            assert isinstance(result, IndexList)
            assert isinstance(result.data, list)
            if result.data:
                assert isinstance(result.data[0], Index)

    async def test_get_index(self) -> None:
        """Test that getting an index works with the real API."""
        async with AsyncDeepsetClient() as client:
            # First get a list of indexes
            index_list = await client.indexes("default").list()
            if not index_list.data:
                pytest.skip("No indexes available for testing")

            # Get the first index by name
            first_index = index_list.data[0]
            result = await client.indexes("default").get(first_index.name)
            assert isinstance(result, Index)
            assert result.name == first_index.name