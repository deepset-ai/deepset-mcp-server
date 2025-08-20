# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any
from unittest.mock import AsyncMock

import pytest

from deepset_mcp.api.shared_models import PaginatedResponse


class MockItem:
    """Mock item for testing PaginatedResponse."""

    def __init__(self, item_id: str, name: str):
        self.item_id = item_id
        self.name = name

    def dict(self) -> dict[str, str]:
        return {"item_id": self.item_id, "name": self.name}


class TestPaginatedResponse:
    """Test suite for PaginatedResponse model."""

    def test_create_with_cursor_field_success(self) -> None:
        """Test successful creation of PaginatedResponse with cursor field."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
                {"item_id": "item2", "name": "Second Item"},
            ],
            "has_more": True,
            "total": 10,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        assert response.data == data["data"]
        assert response.has_more is True
        assert response.total == 10
        assert response.next_cursor == "item2"

    def test_create_with_cursor_field_no_more_pages(self) -> None:
        """Test creation when has_more is False - should not set cursor."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
            ],
            "has_more": False,
            "total": 1,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        assert response.data == data["data"]
        assert response.has_more is False
        assert response.total == 1
        assert response.next_cursor is None

    def test_create_with_cursor_field_empty_data(self) -> None:
        """Test creation with empty data list."""
        data = {
            "data": [],
            "has_more": False,
            "total": 0,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        assert response.data == []
        assert response.has_more is False
        assert response.total == 0
        assert response.next_cursor is None

    def test_create_with_cursor_field_missing_cursor_field(self) -> None:
        """Test creation when cursor field is missing from last item."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
                {"name": "Second Item"},  # Missing item_id
            ],
            "has_more": True,
            "total": 10,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        assert response.data == data["data"]
        assert response.has_more is True
        assert response.next_cursor is None  # Should be None when cursor field missing

    def test_create_without_cursor_field_raises_error(self) -> None:
        """Test that creating PaginatedResponse without cursor field raises ValueError."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
                {"item_id": "item2", "name": "Second Item"},
            ],
            "has_more": True,
            "total": 10,
        }

        with pytest.raises(ValueError, match="Cursor field must be specified when creating PaginatedResponse"):
            PaginatedResponse.model_validate(data)

    def test_create_without_cursor_field_no_more_pages_succeeds(self) -> None:
        """Test that creating without cursor field succeeds when has_more is False."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
            ],
            "has_more": False,
            "total": 1,
        }

        # Should not raise error since has_more is False
        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.model_validate(data)
        assert response.has_more is False
        assert response.next_cursor is None

    def test_create_with_different_cursor_fields(self) -> None:
        """Test creation with different cursor field names."""
        # Test with pipeline_id
        pipeline_data = {
            "data": [
                {"pipeline_id": "pipeline1", "name": "First Pipeline"},
                {"pipeline_id": "pipeline2", "name": "Second Pipeline"},
            ],
            "has_more": True,
        }

        pipeline_response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(
            pipeline_data, "pipeline_id"
        )
        assert pipeline_response.next_cursor == "pipeline2"

        # Test with user_id
        user_data = {
            "data": [
                {"user_id": "user1", "email": "user1@example.com"},
                {"user_id": "user2", "email": "user2@example.com"},
            ],
            "has_more": True,
        }

        user_response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(
            user_data, "user_id"
        )
        assert user_response.next_cursor == "user2"

    def test_inject_paginator(self) -> None:
        """Test injecting paginator functionality."""
        data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": False,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        # Mock fetch function and base args
        fetch_func = AsyncMock()
        base_args = {"limit": 10}

        response._inject_paginator(fetch_func, base_args)

        assert response._fetch_func == fetch_func
        assert response._base_args == base_args

    @pytest.mark.asyncio
    async def test_get_next_page_no_more(self) -> None:
        """Test getting next page when has_more is False."""
        data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": False,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        # Inject paginator
        fetch_func = AsyncMock()
        response._inject_paginator(fetch_func, {"limit": 10})

        next_page = await response._get_next_page()
        assert next_page is None
        fetch_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_next_page_no_cursor(self) -> None:
        """Test getting next page when next_cursor is None."""
        data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": True,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")
        # Override the next_cursor to None to test the case where it's missing
        response.next_cursor = None

        # Inject paginator
        fetch_func = AsyncMock()
        response._inject_paginator(fetch_func, {"limit": 10})

        next_page = await response._get_next_page()
        assert next_page is None
        fetch_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_next_page_success(self) -> None:
        """Test successful retrieval of next page."""
        data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": True,
            "next_cursor": "item1",  # This should be the cursor value from the data
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        # Mock next page data
        next_page_data = {
            "data": [{"item_id": "item2", "name": "Second Item"}],
            "has_more": False,
        }
        next_page_mock: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(
            next_page_data, "item_id"
        )

        # Mock fetch function
        fetch_func = AsyncMock(return_value=next_page_mock)
        base_args = {"limit": 10}

        response._inject_paginator(fetch_func, base_args)

        next_page = await response._get_next_page()

        # Verify fetch was called with correct args
        fetch_func.assert_called_once_with(limit=10, before="item1")

        # Verify returned page
        assert next_page == next_page_mock
        assert next_page._fetch_func == fetch_func
        assert next_page._base_args == base_args

    @pytest.mark.asyncio
    async def test_get_next_page_not_initialized(self) -> None:
        """Test getting next page when paginator is not initialized."""
        data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": True,
            "next_cursor": "cursor1",
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")

        with pytest.raises(TypeError, match="Paginator has not been initialized"):
            await response._get_next_page()

    @pytest.mark.asyncio
    async def test_items_iteration_single_page(self) -> None:
        """Test iterating over items in a single page."""
        data = {
            "data": [
                {"item_id": "item1", "name": "First Item"},
                {"item_id": "item2", "name": "Second Item"},
            ],
            "has_more": False,
        }

        response: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(data, "item_id")
        response._inject_paginator(AsyncMock(), {"limit": 10})

        items = []
        async for item in response.items():
            items.append(item)

        assert len(items) == 2
        assert items[0]["item_id"] == "item1"
        assert items[1]["item_id"] == "item2"

    @pytest.mark.asyncio
    async def test_items_iteration_multiple_pages(self) -> None:
        """Test iterating over items across multiple pages."""
        # First page
        first_page_data = {
            "data": [{"item_id": "item1", "name": "First Item"}],
            "has_more": True,
            "next_cursor": "cursor1",
        }

        # Second page
        second_page_data = {
            "data": [{"item_id": "item2", "name": "Second Item"}],
            "has_more": False,
        }

        first_page: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(
            first_page_data, "item_id"
        )
        second_page: PaginatedResponse[dict[str, Any]] = PaginatedResponse.create_with_cursor_field(
            second_page_data, "item_id"
        )

        # Mock fetch function to return second page
        fetch_func = AsyncMock(return_value=second_page)
        first_page._inject_paginator(fetch_func, {"limit": 10})

        items = []
        async for item in first_page.items():
            items.append(item)

        assert len(items) == 2
        assert items[0]["item_id"] == "item1"
        assert items[1]["item_id"] == "item2"
        fetch_func.assert_called_once()
