import os
import logging
from typing import Any, AsyncIterator, Protocol, TypeVar
from typing_extensions import Self  # For python 3.11 compatibility
from unittest import mock

import httpx

# Types for dependency injection/protocol
T = TypeVar("T")


class HttpClient(Protocol):
    """Protocol for HTTP clients to enable dependency injection and testing."""

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make a GET request."""
        ...

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a POST request."""
        ...

    async def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a PUT request."""
        ...


class HttpxClient:
    """Implementation of HttpClient using httpx."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize with an httpx client."""
        self._client = client

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make a GET request using httpx."""
        return await self._client.get(url, headers=headers, params=params)

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a POST request using httpx."""
        return await self._client.post(url, headers=headers, json=json, data=data)

    async def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a PUT request using httpx."""
        return await self._client.put(url, headers=headers, json=json, data=data)


class DeepsetClient:
    """Client for interacting with the deepset API."""

    def __init__(
        self,
        api_key: str | None = None,
        workspace: str | None = None,
        base_url: str = "https://api.cloud.deepset.ai/api/v1",
        http_client: HttpClient | None = None,
    ) -> None:
        """Initialize the DeepsetClient.

        Parameters
        ----------
        api_key : str, optional
            The API key to use for authentication. If not provided, it will be read from the DEEPSET_API_KEY
            environment variable.
        workspace : str, optional
            The workspace to use. If not provided, it will be read from the DEEPSET_WORKSPACE environment variable.
        base_url : str, optional
            The base URL for the deepset API. Defaults to "https://api.cloud.deepset.ai/api/v1".
        http_client : HttpClient, optional
            The HTTP client to use for making requests. If not provided, an HttpxClient will be created.
        """
        self.api_key = api_key or os.environ.get("DEEPSET_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and DEEPSET_API_KEY environment variable not set")

        self.workspace = workspace or os.environ.get("DEEPSET_WORKSPACE")
        if not self.workspace:
            raise ValueError("Workspace not provided and DEEPSET_WORKSPACE environment variable not set")

        self.base_url = base_url
        self._http_client = http_client
        self._owns_client = http_client is None
        self._logger = logging.getLogger(__name__)

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        if self._http_client is None:
            httpx_client = httpx.AsyncClient()
            self._http_client = HttpxClient(httpx_client)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager."""
        if self._owns_client and isinstance(self._http_client, HttpxClient):
            await self._http_client._client.aclose()

    def _get_headers(self, content_type: str | None = None) -> dict[str, str]:
        """Get headers with authentication."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json,text/plain,*/*"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _build_url(self, endpoint: str) -> str:
        """Build a URL from an endpoint."""
        # Ensure endpoint starts with a slash if not empty
        if endpoint and not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{self.base_url}{endpoint}"

    async def _process_response(self, response: httpx.Response) -> dict[str, Any]:
        """Process a response from the API."""
        if response.status_code >= 400:
            error_message = f"API Error: {response.status_code}"
            try:
                error_details = response.json()
            except Exception:
                error_details = response.text if response.text else "No error details provided by API"
            return {"error": error_message, "details": error_details}

        if not response.text or not response.text.strip():
            return {"status": "success", "message": "API returned empty response body"}

        try:
            return response.json()
        except Exception:
            return {"result": response.text, "warning": "API response was not valid JSON"}

    async def request(
        self, endpoint: str, method: str = "GET", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a request to the deepset API.

        Parameters
        ----------
        endpoint : str
            The endpoint to request, relative to the base URL.
        method : str, optional
            The HTTP method to use. Defaults to "GET".
        data : dict[str, Any], optional
            The data to send with the request. Defaults to None.

        Returns
        -------
        dict[str, Any]
            The response from the API, processed into a dictionary.
        """
        if not self._http_client:
            raise RuntimeError("DeepsetClient must be used as an async context manager")

        url = self._build_url(endpoint)
        self._logger.debug(f"Making {method} request to {url}")

        try:
            if method == "GET":
                response = await self._http_client.get(url, headers=self._get_headers())
            elif method == "POST":
                response = await self._http_client.post(
                    url, headers=self._get_headers("application/json"), json=data
                )
            elif method == "PUT":
                response = await self._http_client.put(
                    url, headers=self._get_headers("application/json"), json=data
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return await self._process_response(response)
        except httpx.RequestError as e:
            self._logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            self._logger.error(f"Unexpected error during request: {str(e)}")
            return {"error": f"Unexpected error during request: {str(e)}"}

    async def request_with_custom_headers(
        self, endpoint: str, headers: dict[str, str], method: str = "GET", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a request to the deepset API with custom headers.

        This is useful for endpoints that need special headers (like text/plain for logs).

        Parameters
        ----------
        endpoint : str
            The endpoint to request, relative to the base URL.
        headers : dict[str, str]
            The headers to use for the request. Authorization will be added if not present.
        method : str, optional
            The HTTP method to use. Defaults to "GET".
        data : dict[str, Any], optional
            The data to send with the request. Defaults to None.

        Returns
        -------
        dict[str, Any]
            The response from the API, processed into a dictionary.
        """
        if not self._http_client:
            raise RuntimeError("DeepsetClient must be used as an async context manager")

        url = self._build_url(endpoint)
        self._logger.debug(f"Making {method} request to {url} with custom headers")

        # Add authorization if not present
        if "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if method == "GET":
                response = await self._http_client.get(url, headers=headers)
            elif method == "POST":
                response = await self._http_client.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = await self._http_client.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return await self._process_response(response)
        except httpx.RequestError as e:
            self._logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            self._logger.error(f"Unexpected error during request: {str(e)}")
            return {"error": f"Unexpected error during request: {str(e)}"}

    async def request_v2_api(
        self, endpoint: str, method: str = "GET", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a request to the deepset API v2 endpoint.

        Parameters
        ----------
        endpoint : str
            The endpoint to request, relative to the base URL (without /api/v2).
        method : str, optional
            The HTTP method to use. Defaults to "GET".
        data : dict[str, Any], optional
            The data to send with the request. Defaults to None.

        Returns
        -------
        dict[str, Any]
            The response from the API, processed into a dictionary.
        """
        url = self._build_url(endpoint).replace("/api/v1", "/api/v2")
        self._logger.debug(f"Making {method} request to v2 API: {url}")

        if not self._http_client:
            raise RuntimeError("DeepsetClient must be used as an async context manager")

        try:
            if method == "GET":
                response = await self._http_client.get(url, headers=self._get_headers())
            elif method == "POST":
                response = await self._http_client.post(
                    url, headers=self._get_headers("application/json"), json=data
                )
            elif method == "PUT":
                response = await self._http_client.put(
                    url, headers=self._get_headers("application/json"), json=data
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return await self._process_response(response)
        except httpx.RequestError as e:
            self._logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            self._logger.error(f"Unexpected error during request: {str(e)}")
            return {"error": f"Unexpected error during request: {str(e)}"}

