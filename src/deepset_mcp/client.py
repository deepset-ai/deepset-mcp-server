import os
import logging
from typing import Any, AsyncIterator, Protocol, TypeVar
from typing_extensions import Self  # For python 3.11 compatibility

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

    # API-specific methods
    async def list_pipelines(self) -> dict[str, Any]:
        """List all pipelines in the workspace."""
        return await self.request(f"/workspaces/{self.workspace}/pipelines")

    async def get_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        """Get a pipeline by ID."""
        return await self.request(f"/workspaces/{self.workspace}/pipelines/{pipeline_id}")

    async def get_component_schemas(self) -> dict[str, Any]:
        """Get the schemas for all available Haystack components."""
        return await self.request("/haystack/components")

    async def validate_pipeline_yaml(self, yaml_content: str) -> dict[str, Any]:
        """Validate a pipeline YAML configuration."""
        payload = {"query_yaml": yaml_content}
        return await self.request(
            f"/workspaces/{self.workspace}/pipeline_validations", method="POST", data=payload
        )

    async def get_pipeline_yaml(self, pipeline_name: str) -> dict[str, Any]:
        """Get the YAML configuration for a pipeline."""
        return await self.request(f"/workspaces/{self.workspace}/pipelines/{pipeline_name}/yaml")

    async def update_pipeline_yaml(self, pipeline_name: str, yaml_content: str) -> dict[str, Any]:
        """Update a pipeline YAML configuration."""
        payload = {"query_yaml": yaml_content}
        return await self.request(
            f"/workspaces/{self.workspace}/pipelines/{pipeline_name}/yaml", method="PUT", data=payload
        )

    async def list_pipeline_templates(self, limit: int = 100, page: int = 1) -> dict[str, Any]:
        """List pipeline templates."""
        endpoint = f"/workspaces/{self.workspace}/pipeline_templates?limit={limit}&page_number={page}&field=created_at&order=DESC"
        return await self.request(endpoint)

    async def get_pipeline_template(self, template_name: str) -> dict[str, Any]:
        """Get a pipeline template by name."""
        return await self.request(f"/workspaces/{self.workspace}/pipeline_templates/{template_name}")

    async def get_custom_components(self) -> dict[str, Any]:
        """Get all custom components."""
        return await self.get_component_schemas()

    async def get_latest_custom_component_installation_logs(self) -> dict[str, Any]:
        """Get the logs from the latest custom component installation."""
        # This endpoint uses v2 of the API
        endpoint = "/custom_components/logs"
        url = self._build_url(endpoint).replace("/api/v1", "/api/v2")

        if not self._http_client:
            raise RuntimeError("DeepsetClient must be used as an async context manager")

        try:
            # Use text/plain accept header specifically for logs
            headers = self._get_headers()
            headers["Accept"] = "text/plain"
            response = await self._http_client.get(url, headers=headers)

            if response.status_code >= 400:
                error_message = f"API Error: {response.status_code}"
                try:
                    error_details = response.json()
                except Exception:
                    error_details = response.text if response.text else "No error details provided by API"
                return {"error": error_message, "details": error_details}

            # Return raw text response
            return {"logs": response.text}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def list_custom_component_installations(self, limit: int = 20, page: int = 1) -> dict[str, Any]:
        """List custom component installations."""
        # This endpoint uses v2 of the API
        endpoint = f"/custom_components?limit={limit}&page_number={page}&field=created_at&order=DESC"
        url = self._build_url(endpoint).replace("/api/v1", "/api/v2")

        if not self._http_client:
            raise RuntimeError("DeepsetClient must be used as an async context manager")

        try:
            response = await self._http_client.get(url, headers=self._get_headers())
            return await self._process_response(response)
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get information about a user."""
        return await self.request(f"/users/{user_id}")
