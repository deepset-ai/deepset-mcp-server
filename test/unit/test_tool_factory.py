# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for tool factory functions."""

import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from deepset_mcp.api.protocols import AsyncClientProtocol
from deepset_mcp.tool_factory import (
    apply_client,
    apply_custom_args,
    apply_memory,
    apply_workspace,
    build_tool,
)
from deepset_mcp.tool_models import MemoryType, ToolConfig, WorkspaceMode
from deepset_mcp.tools.tokonomics.object_store import InMemoryBackend, ObjectStore
from test.unit.conftest import BaseFakeClient


class TestApplyCustomArgs:
    """Test the apply_custom_args function."""

    def test_no_custom_args_returns_original(self) -> None:
        """Test that function is returned unchanged when no custom args."""

        async def sample_func(a: int, b: str) -> str:
            return f"{a}:{b}"

        config = ToolConfig()
        result = apply_custom_args(sample_func, config)

        assert result is sample_func

    def test_custom_args_applied(self) -> None:
        """Test that custom args are applied to function."""

        async def sample_func(a: int, b: str, c: bool = True) -> str:
            """A test function.

            :param a: some parameter
            :param b: some parameter
            :param c: some parameter
            """
            return f"{a}:{b}:{c}"

        config = ToolConfig(custom_args={"c": False})
        result = apply_custom_args(sample_func, config)

        # Check signature was updated
        sig = inspect.signature(result)
        assert "c" not in sig.parameters
        assert len(sig.parameters) == 2

        # Check docstring was updated
        doc = result.__doc__
        assert doc is not None
        assert ":param c:" not in doc
        assert ":param a:" in doc
        assert ":param b:" in doc

    @pytest.mark.asyncio
    async def test_custom_args_applied_for_default(self) -> None:
        """Test that custom args function works correctly."""

        async def sample_func(a: int, b: str, c: bool = True) -> str:
            return f"{a}:{b}:{c}"

        config = ToolConfig(custom_args={"c": False})
        result = apply_custom_args(sample_func, config)

        # Call should work with custom arg applied
        output = await result(a=1, b="test")
        assert output == "1:test:False"


class TestApplyWorkspace:
    """Test the apply_workspace function."""

    def test_no_workspace_needed_returns_original(self) -> None:
        """Test that function is returned unchanged when no workspace needed."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig(needs_workspace=False)
        result = apply_workspace(sample_func, config, WorkspaceMode.STATIC)

        assert result is sample_func

    def test_dynamic_workspace_returns_original(self) -> None:
        """Test that function is returned unchanged in dynamic mode."""

        async def sample_func(workspace: str, a: int) -> str:
            return f"{workspace}:{a}"

        config = ToolConfig(needs_workspace=True)
        result = apply_workspace(sample_func, config, WorkspaceMode.DYNAMIC)

        assert result is sample_func

    def test_static_workspace_signature_updated(self) -> None:
        """Test that workspace parameter is removed in static mode."""

        async def sample_func(workspace: str, a: int) -> str:
            """Sample function.

            :param workspace: The workspace
            :param a: First param
            """
            return f"{workspace}:{a}"

        config = ToolConfig(needs_workspace=True)
        result = apply_workspace(sample_func, config, WorkspaceMode.STATIC, "test-workspace")

        # Check signature was updated
        sig = inspect.signature(result)
        assert "workspace" not in sig.parameters
        assert len(sig.parameters) == 1

        # Check docstring was updated
        doc = result.__doc__
        assert doc is not None
        assert ":param workspace:" not in doc
        assert ":param a:" in doc

    @pytest.mark.asyncio
    async def test_static_workspace_function_behavior(self) -> None:
        """Test that static workspace function works correctly."""

        async def sample_func(workspace: str, a: int) -> str:
            return f"{workspace}:{a}"

        config = ToolConfig(needs_workspace=True)
        result = apply_workspace(sample_func, config, WorkspaceMode.STATIC, "test-workspace")

        # Call should work with workspace injected
        output = await result(a=42)
        assert output == "test-workspace:42"


class TestApplyMemory:
    """Test the apply_memory function."""

    @pytest.fixture
    def store(self) -> ObjectStore:
        """Create an ObjectStore for testing."""
        return ObjectStore(backend=InMemoryBackend())

    def test_no_memory_returns_original(self) -> None:
        """Test that function is returned unchanged when no memory needed."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig(memory_type=MemoryType.NO_MEMORY)
        result = apply_memory(sample_func, config)

        assert result is sample_func

    def test_invalid_memory_type_raises_error(self, store: ObjectStore) -> None:
        """Test that invalid memory type raises ValueError."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig(memory_type="invalid")  # type: ignore

        with pytest.raises(ValueError, match="Invalid memory type"):
            apply_memory(sample_func, config, store)

    @patch("deepset_mcp.tool_factory.explorable")
    def test_explorable_memory_applied(self, mock_explorable: Any, store: ObjectStore) -> None:
        """Test that explorable decorator is applied."""

        async def sample_func(a: int) -> str:
            return str(a)

        mock_decorator = MagicMock()
        mock_explorable.return_value = mock_decorator
        mock_decorator.return_value = sample_func

        config = ToolConfig(memory_type=MemoryType.EXPLORABLE)
        apply_memory(sample_func, config, store)

        mock_explorable.assert_called_once()
        mock_decorator.assert_called_once_with(sample_func)

    @patch("deepset_mcp.tool_factory.referenceable")
    def test_referenceable_memory_applied(self, mock_referenceable: Any, store: ObjectStore) -> None:
        """Test that referenceable decorator is applied."""

        async def sample_func(a: int) -> str:
            return str(a)

        mock_decorator = MagicMock()
        mock_referenceable.return_value = mock_decorator
        mock_decorator.return_value = sample_func

        config = ToolConfig(memory_type=MemoryType.REFERENCEABLE)
        apply_memory(sample_func, config, store)

        mock_referenceable.assert_called_once()
        mock_decorator.assert_called_once_with(sample_func)

    @patch("deepset_mcp.tool_factory.explorable_and_referenceable")
    def test_both_memory_applied(self, mock_both: Any, store: ObjectStore) -> None:
        """Test that both memory decorator is applied."""

        async def sample_func(a: int) -> str:
            return str(a)

        mock_decorator = MagicMock()
        mock_both.return_value = mock_decorator
        mock_decorator.return_value = sample_func

        config = ToolConfig(memory_type=MemoryType.BOTH)
        apply_memory(sample_func, config, store)

        mock_both.assert_called_once()
        mock_decorator.assert_called_once_with(sample_func)


class TestApplyClient:
    """Test the apply_client function."""

    def test_no_client_needed_returns_original(self) -> None:
        """Test that function is returned unchanged when no client needed."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig(needs_client=False)
        result = apply_client(sample_func, config)

        assert result is sample_func

    def test_client_signature_updated_with_context(self) -> None:
        """Test that client parameter is removed and ctx is added."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            """Sample function.

            :param client: The client
            :param a: First param
            """
            return str(a)

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True)

        # Check signature was updated
        sig = inspect.signature(result)
        assert "client" not in sig.parameters
        assert "ctx" in sig.parameters
        assert len(sig.parameters) == 2

        # Check docstring was updated
        assert result.__doc__ is not None
        assert ":param client:" not in result.__doc__
        assert ":param a:" in result.__doc__

    def test_client_signature_updated_without_context(self) -> None:
        """Test that client parameter is removed without ctx."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            """Sample function.

            :param client: The client
            :param a: First param
            """
            return str(a)

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=False)

        # Check signature was updated
        sig = inspect.signature(result)
        assert "client" not in sig.parameters
        assert "ctx" not in sig.parameters
        assert len(sig.parameters) == 1

        # Check docstring was updated
        assert result.__doc__ is not None
        assert ":param client:" not in result.__doc__

    @pytest.mark.asyncio
    async def test_client_context_missing_raises_error(self) -> None:
        """Test that missing context raises ValueError."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return str(a)

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True)

        with pytest.raises(ValueError, match="Context is required"):
            await result(a=42)

    @pytest.mark.asyncio
    async def test_client_missing_auth_header_raises_error(self) -> None:
        """Test that missing auth header raises ValueError."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return str(a)

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True)

        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = None

        with pytest.raises(ValueError, match="No Authorization header"):
            await result(a=42, ctx=mock_ctx)

    @pytest.mark.asyncio
    async def test_client_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises ValueError."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return str(a)

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True)

        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer "

        with pytest.raises(ValueError, match="API key cannot be empty"):
            await result(a=42, ctx=mock_ctx)

    @pytest.mark.asyncio
    async def test_client_bearer_token_processed(self) -> None:
        """Test that Bearer token is processed correctly."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True)

        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer test-token"

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42, ctx=mock_ctx)

            # Check that client was created with correct API key
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["api_key"] == "test-token"

    @pytest.mark.asyncio
    async def test_client_with_api_key_and_context_uses_context(self) -> None:
        """Test that client uses API key from request context."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=True, api_key="unused-token")

        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer test-token"

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42, ctx=mock_ctx)

            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert "api_key" in call_args[1]
            assert call_args[1]["api_key"] == "test-token"

    @pytest.mark.asyncio
    async def test_client_without_context_uses_api_key(self) -> None:
        """Test that client without context uses environment variables."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=False, api_key="test-token")

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42)

            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert "api_key" in call_args[1]
            assert call_args[1]["api_key"] == "test-token"

    @pytest.mark.asyncio
    async def test_client_with_base_url_context(self) -> None:
        """Test that client is created with custom base_url when provided with context."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        custom_url = "https://custom.api.example.com"
        result = apply_client(sample_func, config, use_request_context=True, base_url=custom_url)

        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer test-token"

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42, ctx=mock_ctx)

            # Check that client was created with correct base_url
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["base_url"] == custom_url
            assert call_args[1]["api_key"] == "test-token"

    @pytest.mark.asyncio
    async def test_client_with_base_url_no_context(self) -> None:
        """Test that client is created with custom base_url when provided without context."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        custom_url = "https://custom.api.example.com"
        result = apply_client(sample_func, config, use_request_context=False, base_url=custom_url)

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42)

            # Check that client was created with correct base_url
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["base_url"] == custom_url

    @pytest.mark.asyncio
    async def test_client_without_base_url(self) -> None:
        """Test that client is created without base_url when not provided."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        result = apply_client(sample_func, config, use_request_context=False, base_url=None)

        # Mock the AsyncDeepsetClient to return our FakeClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42)

            # Check that client was created without base_url
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert "base_url" not in call_args[1]


class TestBuildTool:
    """Test the build_tool function."""

    @pytest.fixture
    def object_store(self) -> ObjectStore:
        """Create an ObjectStore for testing."""
        return ObjectStore(backend=InMemoryBackend())

    @pytest.mark.asyncio
    async def test_basic_function_enhancement(self) -> None:
        """Test that basic function is enhanced correctly."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig()
        result = build_tool(sample_func, config, WorkspaceMode.STATIC)

        # Should return async function
        assert inspect.iscoroutinefunction(result)

        # Should work when called
        output = await result(a=42)
        assert output == "42"

    @pytest.mark.asyncio
    async def test_sync_function_made_async(self) -> None:
        """Test that sync functions are made async."""

        def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig()
        result = build_tool(sample_func, config, WorkspaceMode.STATIC)

        # Should return async function
        assert inspect.iscoroutinefunction(result)

        # Should work when called
        output = await result(a=42)
        assert output == "42"

    @pytest.mark.asyncio
    async def test_full_enhancement_chain(self) -> None:
        """Test that all enhancements are applied in correct order."""

        async def sample_func(client: AsyncClientProtocol, workspace: str, a: int, custom_arg: str = "default") -> str:
            """Some test docs for a test function.

            :param client: The client to use for testing.
            :param workspace: The workspace to use.
            :param a: The a.
            :param custom_arg: The custom argument.
            :returns: The result.
            """
            return f"{workspace}:{a}:{custom_arg}"

        config = ToolConfig(
            needs_client=True,
            needs_workspace=True,
            memory_type=MemoryType.NO_MEMORY,
            custom_args={"custom_arg": "injected"},
        )

        result = build_tool(sample_func, config, WorkspaceMode.STATIC, workspace="test-workspace")

        # Check final signature
        sig = inspect.signature(result)
        assert "client" not in sig.parameters
        assert "workspace" not in sig.parameters
        assert "custom_arg" not in sig.parameters
        assert "ctx" in sig.parameters
        assert "a" in sig.parameters

        # Check docstring was updated
        assert result.__doc__ is not None
        assert ":param client:" not in result.__doc__
        assert ":param workspace:" not in result.__doc__
        assert ":param custom_arg:" not in result.__doc__
        assert ":param a:" in result.__doc__

    @pytest.mark.asyncio
    async def test_enhanced_tool_execution_with_client(self) -> None:
        """Test that enhanced tool executes correctly with client injection."""

        async def sample_func(client: AsyncClientProtocol, workspace: str, a: int) -> str:
            return f"{workspace}:{a}"

        config = ToolConfig(
            needs_client=True,
            needs_workspace=True,
        )

        result = build_tool(
            sample_func, config, WorkspaceMode.STATIC, workspace="test-workspace", use_request_context=True
        )

        # Mock the context and use FakeClient
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer test-token"

        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            output = await result(a=42, ctx=mock_ctx)
            assert output == "test-workspace:42"

            # Verify client was created with correct token
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["api_key"] == "test-token"

    @pytest.mark.asyncio
    async def test_enhanced_tool_without_client_or_workspace(self) -> None:
        """Test that enhanced tool works without client or workspace."""

        async def sample_func(a: int, b: str) -> str:
            return f"{a}:{b}"

        config = ToolConfig(
            needs_client=False,
            needs_workspace=False,
        )

        result = build_tool(sample_func, config, WorkspaceMode.STATIC)

        # Should work without ctx
        output = await result(a=42, b="test")
        assert output == "42:test"

    @pytest.mark.asyncio
    async def test_enhanced_tool_with_memory_decorators(self, object_store: ObjectStore) -> None:
        """Test that enhanced tool works with memory decorators."""

        async def sample_func(a: int) -> str:
            return str(a)

        config = ToolConfig(
            memory_type=MemoryType.EXPLORABLE,
        )

        with patch("deepset_mcp.tool_factory.explorable") as mock_explorable:
            mock_decorator = MagicMock()
            mock_explorable.return_value = mock_decorator
            mock_decorator.return_value = sample_func

            build_tool(sample_func, config, WorkspaceMode.STATIC, object_store=object_store)

            # Should have applied the decorator
            mock_explorable.assert_called_once()
            mock_decorator.assert_called_once_with(sample_func)

    @pytest.mark.asyncio
    async def test_api_key_error_handling(self) -> None:
        """Test proper error handling for API key issues."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return str(a)

        config = ToolConfig(needs_client=True)
        result = build_tool(sample_func, config, WorkspaceMode.STATIC)

        # Test missing context
        with pytest.raises(ValueError, match="Context is required"):
            await result(a=42)

        # Test missing auth header
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = None

        with pytest.raises(ValueError, match="No Authorization header"):
            await result(a=42, ctx=mock_ctx)

        # Test empty API key
        mock_ctx.request_context.request.headers.get.return_value = "Bearer "

        with pytest.raises(ValueError, match="API key cannot be empty"):
            await result(a=42, ctx=mock_ctx)

    @pytest.mark.asyncio
    async def test_build_tool_with_base_url(self) -> None:
        """Test that build_tool passes base_url correctly to client."""

        async def sample_func(client: AsyncClientProtocol, a: int) -> str:
            return f"client:{a}"

        config = ToolConfig(needs_client=True)
        custom_url = "https://custom.api.example.com"
        result = build_tool(sample_func, config, WorkspaceMode.STATIC, base_url=custom_url)

        # Mock the context
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers.get.return_value = "Bearer test-token"

        # Mock the AsyncDeepsetClient
        fake_client = BaseFakeClient()

        with patch("deepset_mcp.tool_factory.AsyncDeepsetClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = fake_client

            await result(a=42, ctx=mock_ctx)

            # Verify client was created with correct base_url
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["base_url"] == custom_url
            assert call_args[1]["api_key"] == "test-token"
