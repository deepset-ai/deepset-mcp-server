# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from deepset_mcp.api.exceptions import RequestTimeoutError
from deepset_mcp.api.transport import AsyncTransport, TransportResponse


@pytest.mark.asyncio
class TestAsyncTransport:
    """Unit tests for AsyncTransport."""

    @pytest_asyncio.fixture
    async def transport(self) -> AsyncTransport:
        """Create an AsyncTransport instance for testing."""
        return AsyncTransport(base_url="https://api.example.com", api_key="test-api-key", config={"timeout": 30.0})

    @pytest_asyncio.fixture
    def mock_httpx_client(self) -> AsyncMock:
        """Create a mock httpx.AsyncClient."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        return mock_client

    async def test_init_with_config(self) -> None:
        """Test AsyncTransport initialization with config."""
        config = {"timeout": 60.0, "follow_redirects": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            AsyncTransport(base_url="https://api.example.com", api_key="test-key", config=config)

            # Verify httpx.AsyncClient was called with correct parameters
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args[1]

            assert call_args["base_url"] == "https://api.example.com"
            assert call_args["headers"]["Authorization"] == "Bearer test-key"
            assert call_args["timeout"] == 60.0
            assert call_args["follow_redirects"] is True

    async def test_init_without_config(self) -> None:
        """Test AsyncTransport initialization without config."""
        with patch("httpx.AsyncClient") as mock_client_class:
            AsyncTransport(base_url="https://api.example.com", api_key="test-key")

            # Verify httpx.AsyncClient was called with minimal parameters
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args[1]

            assert call_args["base_url"] == "https://api.example.com"
            assert call_args["headers"]["Authorization"] == "Bearer test-key"
            assert "timeout" not in call_args

    async def test_request_success(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test successful request."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = '{"result": "success"}'
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_httpx_client.request.return_value = mock_response

        # Patch the transport's client
        transport._client = mock_httpx_client

        # Make request
        response = await transport.request(method="POST", url="/test", response_type=dict[str, Any])

        # Verify request was made correctly
        mock_httpx_client.request.assert_called_once_with("POST", "/test")

        # Verify response
        assert isinstance(response, TransportResponse)
        assert response.status_code == 200
        assert response.text == '{"result": "success"}'
        assert response.json == {"result": "success"}

    async def test_request_with_timeout_config(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test request uses config timeout when timeout='config'."""
        mock_response = MagicMock()
        mock_response.text = "success"
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)
        mock_httpx_client.request.return_value = mock_response

        transport._client = mock_httpx_client

        # Make request with timeout="config" (default)
        await transport.request(method="GET", url="/test", timeout="config")

        # Verify timeout was not passed to httpx (uses client's configured timeout)
        mock_httpx_client.request.assert_called_once_with("GET", "/test")

    async def test_request_with_explicit_timeout(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test request with explicit timeout value."""
        mock_response = MagicMock()
        mock_response.text = "success"
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)
        mock_httpx_client.request.return_value = mock_response

        transport._client = mock_httpx_client

        # Make request with explicit timeout
        await transport.request(method="GET", url="/test", timeout=60.0)

        # Verify timeout was passed to httpx
        mock_httpx_client.request.assert_called_once_with("GET", "/test", timeout=60.0)

    async def test_request_with_none_timeout(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test request with None timeout (disabled)."""
        mock_response = MagicMock()
        mock_response.text = "success"
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)
        mock_httpx_client.request.return_value = mock_response

        transport._client = mock_httpx_client

        # Make request with timeout=None
        await transport.request(method="GET", url="/test", timeout=None)

        # Verify timeout=None was passed to httpx
        mock_httpx_client.request.assert_called_once_with("GET", "/test", timeout=None)

    async def test_request_timeout_exception(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test timeout exception is caught and re-raised as RequestTimeoutError."""
        # Setup mock to raise timeout exception
        mock_httpx_client.request.side_effect = httpx.ReadTimeout("Request timed out")
        transport._client = mock_httpx_client

        # Make request that will timeout
        with pytest.raises(RequestTimeoutError) as exc_info:
            await transport.request(method="POST", url="/search", timeout=30.0)

        # Verify RequestTimeoutError details
        error = exc_info.value
        assert error.method == "POST"
        assert error.url == "/search"
        assert error.timeout == 30.0
        assert error.duration is not None
        assert error.duration > 0  # Should be small since it's mocked
        assert "Request timed out after" in str(error)
        assert "limit: 30.0s" in str(error)

    async def test_request_timeout_with_search_detail(
        self, transport: AsyncTransport, mock_httpx_client: AsyncMock
    ) -> None:
        """Test timeout on search URL includes helpful detail message."""
        # Setup mock to raise timeout exception after a delay
        mock_httpx_client.request.side_effect = httpx.ReadTimeout("Request timed out")
        transport._client = mock_httpx_client

        with patch("time.time", side_effect=[0, 65]):  # Mock 65 second duration
            with pytest.raises(RequestTimeoutError) as exc_info:
                await transport.request(method="POST", url="/v1/pipelines/search", timeout=180.0)

        # Verify search-specific detail is included
        error = exc_info.value
        assert error.detail is not None
        assert "Search operations can take longer" in error.detail
        assert "Consider increasing the timeout" in error.detail

    async def test_request_timeout_different_exceptions(
        self, transport: AsyncTransport, mock_httpx_client: AsyncMock
    ) -> None:
        """Test different httpx timeout exceptions are handled."""
        transport._client = mock_httpx_client

        # Test different timeout exception types
        timeout_exceptions = [
            httpx.ReadTimeout("Read timeout"),
            httpx.WriteTimeout("Write timeout"),
            httpx.ConnectTimeout("Connect timeout"),
            httpx.PoolTimeout("Pool timeout"),
        ]

        for exception in timeout_exceptions:
            mock_httpx_client.request.side_effect = exception

            with pytest.raises(RequestTimeoutError):
                await transport.request(method="GET", url="/test", timeout=10.0)

    async def test_request_non_timeout_exception_not_caught(
        self, transport: AsyncTransport, mock_httpx_client: AsyncMock
    ) -> None:
        """Test non-timeout exceptions are not caught."""
        # Setup mock to raise non-timeout exception
        mock_httpx_client.request.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
        transport._client = mock_httpx_client

        # Non-timeout exceptions should not be caught
        with pytest.raises(httpx.HTTPStatusError):
            await transport.request(method="GET", url="/test")

    async def test_request_json_decode_error_handling(
        self, transport: AsyncTransport, mock_httpx_client: AsyncMock
    ) -> None:
        """Test handling of invalid JSON responses."""
        mock_response = MagicMock()
        mock_response.text = "not valid json"
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)
        mock_httpx_client.request.return_value = mock_response

        transport._client = mock_httpx_client

        # Make request
        response = await transport.request(method="GET", url="/test")

        # Verify response handles JSON decode error gracefully
        assert response.status_code == 200
        assert response.text == "not valid json"
        assert response.json is None

    async def test_close(self, transport: AsyncTransport, mock_httpx_client: AsyncMock) -> None:
        """Test transport close method."""
        transport._client = mock_httpx_client

        await transport.close()

        mock_httpx_client.aclose.assert_called_once()
