from typing import Any

import pytest
import pytest_asyncio

from deepset_mcp.client import AsyncDeepsetClient
from deepset_mcp.transport import AsyncTransport, TransportProtocol


class DummyProtocol(TransportProtocol):
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.closed: bool = False

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        # Record the request and return a dummy response
        record: dict[str, Any] = {"method": method, "url": url, **kwargs}
        self.requests.append(record)
        return {"dummy": "response"}

    async def close(self) -> None:
        self.closed = True


@pytest_asyncio.fixture(autouse=True)  # type: ignore
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure DEEPSET_API_KEY is unset by default unless explicitly set
    monkeypatch.delenv("DEEPSET_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_init_with_api_key_and_transport() -> None:
    dummy: DummyProtocol = DummyProtocol()
    client: AsyncDeepsetClient = AsyncDeepsetClient(api_key="testkey", transport=dummy)
    assert client.api_key == "testkey"
    assert client._transport is dummy


@pytest.mark.asyncio
async def test_init_without_api_key_raises() -> None:
    # No API key in args or env
    with pytest.raises(ValueError):
        AsyncDeepsetClient()


@pytest.mark.asyncio
async def test_init_with_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSET_API_KEY", "envkey")
    client: AsyncDeepsetClient = AsyncDeepsetClient()
    assert client.api_key == "envkey"
    # Default transport is AsyncTransport
    assert isinstance(client._transport, AsyncTransport)


@pytest.mark.asyncio
async def test_request_default_headers_and_url() -> None:
    dummy: DummyProtocol = DummyProtocol()
    client: AsyncDeepsetClient = AsyncDeepsetClient(api_key="key", base_url="https://api.test", transport=dummy)

    resp: Any = await client.request("endpoint")
    # Should normalize endpoint to '/endpoint'
    assert resp == {"dummy": "response"}
    assert len(dummy.requests) == 1

    call: dict[str, Any] = dummy.requests[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://api.test/endpoint"
    headers: dict[str, str] = call["headers"]
    assert headers["Authorization"] == "Bearer key"
    assert headers["Accept"] == "application/json,text/plain,*/*"
    assert "Content-Type" not in headers
    assert call.get("json") is None


@pytest.mark.asyncio
async def test_request_with_data_and_custom_headers() -> None:
    dummy: DummyProtocol = DummyProtocol()
    client: AsyncDeepsetClient = AsyncDeepsetClient(api_key="key", base_url="https://api.test", transport=dummy)

    data: dict[str, Any] = {"foo": "bar"}
    custom: dict[str, str] = {"X-Custom": "value"}
    resp: Any = await client.request("/path", method="POST", data=data, headers=custom)
    assert resp == {"dummy": "response"}
    assert len(dummy.requests) == 1

    call = dummy.requests[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.test/path"
    headers = call["headers"]
    # Custom header merged
    assert headers["X-Custom"] == "value"
    assert headers["Content-Type"] == "application/json"
    # Authorization preserved
    assert headers["Authorization"] == "Bearer key"
    assert call.get("json") == data


@pytest.mark.asyncio
async def test_close_and_context_manager() -> None:
    dummy: DummyProtocol = DummyProtocol()
    client: AsyncDeepsetClient = AsyncDeepsetClient(api_key="key", transport=dummy)

    # Test close
    await client.close()
    assert dummy.closed is True

    # Test async context manager
    dummy2: DummyProtocol = DummyProtocol()
    async with AsyncDeepsetClient(api_key="key", transport=dummy2) as ctx:
        assert isinstance(ctx, AsyncDeepsetClient)
    # After exit, close should be called
    assert dummy2.closed is True
