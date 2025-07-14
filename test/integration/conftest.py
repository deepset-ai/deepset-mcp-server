# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
from dotenv import load_dotenv

from deepset_mcp.api.client import AsyncDeepsetClient

load_dotenv()


@pytest.fixture
def test_workspace_name() -> str:
    """Create a unique workspace name for testing."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"test-workspace-{timestamp}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncDeepsetClient, None]:
    """Create and configure the deepset client."""
    api_key = os.environ.get("DEEPSET_API_KEY")
    if not api_key:
        pytest.skip("DEEPSET_API_KEY environment variable not set")

    async with AsyncDeepsetClient(api_key=api_key) as client:
        yield client


@pytest.fixture
async def test_workspace(
    client: AsyncDeepsetClient,
    test_workspace_name: str,
) -> AsyncGenerator[str, None]:
    """Create a test workspace and clean it up after tests."""
    # Create a test workspace
    await client.request(
        endpoint="v1/workspaces",
        method="POST",
        data={"name": test_workspace_name},
    )

    yield test_workspace_name

    # Clean up the workspace after tests
    try:
        await client.request(
            endpoint=f"v1/workspaces/{test_workspace_name}",
            method="DELETE",
        )
    except Exception as e:
        print(f"Failed to delete test workspace: {e}")
