# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, PrivateAttr, model_validator


class NoContentResponse(BaseModel):
    """Response model for an empty response."""

    success: bool = True
    "Indicates whether the operation was successful"
    message: str = "No content"
    "Human-readable message describing the response"


class DeepsetUser(BaseModel):
    """Model representing a user on the deepset platform."""

    id: str = Field(alias="user_id")
    "Unique identifier for the user"
    given_name: str | None = None
    "User's given (first) name"
    family_name: str | None = None
    "User's family (last) name"
    email: str | None = None
    "User's email address"


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    A response model for a single page of cursor-paginated results.

    This model also acts as an async iterator to fetch subsequent pages.
    """

    # --- Public Data Fields ---
    data: list[T]
    "List of items for the current page"
    has_more: bool
    "Whether there are more items available beyond this page"
    total: int | None = None
    "Total number of items across all pages, if known"
    next_cursor: str | None = None
    "Cursor for fetching the next page of results"

    # --- Internal Paginator State (Defaults to None) ---
    _fetch_func: Callable[..., Coroutine[Any, Any, "PaginatedResponse[T]"]] | None = PrivateAttr(default=None)
    _base_args: dict[str, Any] | None = PrivateAttr(default=None)
    _cursor_param: str = PrivateAttr(default="before")

    @model_validator(mode="before")
    @classmethod
    def populate_cursors_from_data(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Populate next_cursor from the last element of data."""
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            data_list = data["data"]

            if data_list and data.get("has_more"):
                last_item = data_list[-1]
                if isinstance(last_item, dict):
                    # Use the cursor field if specified, raise if not provided
                    cursor_field = data.get("_cursor_field")
                    if not cursor_field:
                        raise ValueError("Cursor field must be specified when creating PaginatedResponse")
                    cursor = last_item.get(cursor_field)
                    data["next_cursor"] = cursor

        return data

    @classmethod
    def create_with_cursor_field(cls, data: dict[str, Any], cursor_field: str) -> "PaginatedResponse[T]":
        """Factory method that allows specifying the cursor field."""
        # Inject the cursor field into the data before validation
        data_copy = data.copy()
        data_copy["_cursor_field"] = cursor_field
        return cls.model_validate(data_copy)

    def _inject_paginator(
        self,
        fetch_func: Callable[..., Awaitable["PaginatedResponse[T]"]],
        base_args: dict[str, Any],
        cursor_param: str = "before",
    ) -> None:
        """Injects the necessary components to make this object iterable."""
        # Convert Awaitable to Coroutine for typing compatibility
        if callable(fetch_func):
            # This is a runtime check - mypy doesn't understand the callable compatibility
            self._fetch_func = fetch_func  # type: ignore
        self._base_args = {k: v for k, v in base_args.items() if v is not None}
        self._cursor_param = cursor_param

    async def _get_next_page(self) -> "PaginatedResponse[T] | None":
        """Fetches the next page of results using the stored fetch function."""
        if self._fetch_func is None or self._base_args is None:
            raise TypeError(
                "Paginator has not been initialized. Please use the resource's list() method to create this object."
            )

        if not self.has_more or not self.next_cursor:
            return None

        args = self._base_args.copy()
        # TODO: Pagination in the deepset API is currently implemented in an unintuitive way.
        # TODO: The cursor is always time based (created_at) and after signifies pipelines older than the current cursor
        # TODO: while 'before' signals pipelines younger than the current cursor.
        # TODO: This is applied irrespective of any sort (e.g. name) that would conflict with this approach.
        # TODO: Change this to 'after' once the behaviour is fixed on the deepset API
        args[self._cursor_param] = self.next_cursor

        next_page = await self._fetch_func(**args)
        next_page._inject_paginator(self._fetch_func, self._base_args, self._cursor_param)
        return next_page

    async def items(self) -> AsyncIterator[T]:
        """Asynchronously iterates over each item across all pages, starting from this page."""
        current_page: PaginatedResponse[T] | None = self
        while current_page:
            for item in current_page.data:
                yield item
            current_page = await current_page._get_next_page()

    def __aiter__(self) -> AsyncIterator[T]:
        """Make the object itself iterable for the most pythonic experience."""
        return self.items()
