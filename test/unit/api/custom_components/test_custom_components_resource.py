# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.custom_components.models import (
    CustomComponentInstallationList,
)
from deepset_mcp.api.custom_components.resource import CustomComponentsResource
from test.unit.conftest import BaseFakeClient


@pytest.mark.asyncio
async def test_list_installations() -> None:
    """Test listing custom component installations."""
    mock_data = {
        "data": [
            {
                "custom_component_id": "comp_123",
                "status": "installed",
                "organization_id": "org-123",
                "version": "1.0.0",
                "created_by_user_id": "user_123",
                "logs": [{"level": "INFO", "msg": "Installation complete"}],
            }
        ],
        "total": 1,
        "has_more": False,
    }

    fake_client = BaseFakeClient(
        responses={"v2/custom_components?limit=20&page_number=1&field=created_at&order=DESC": mock_data}
    )

    def custom_components(workspace: str) -> CustomComponentsResource:
        return CustomComponentsResource(client=fake_client)

    fake_client.custom_components = custom_components  # type: ignore[method-assign]

    resource = fake_client.custom_components("test-workspace")
    result = await resource.list_installations()

    assert isinstance(result, CustomComponentInstallationList)
    assert len(result.data) == 1
    assert result.total == 1
    assert not result.has_more
    assert result.data[0].custom_component_id == "comp_123"
    assert result.data[0].status == "installed"
    assert result.data[0].version == "1.0.0"
    assert result.data[0].created_by_user_id == "user_123"
    assert len(result.data[0].logs) == 1
    assert result.data[0].logs[0]["level"] == "INFO"
    assert result.data[0].logs[0]["msg"] == "Installation complete"


@pytest.mark.asyncio
async def test_list_installations_empty() -> None:
    """Test listing custom component installations when none exist."""
    mock_data = {
        "data": [],
        "total": 0,
        "has_more": False,
    }

    fake_client = BaseFakeClient(
        responses={"v2/custom_components?limit=20&page_number=1&field=created_at&order=DESC": mock_data}
    )

    def custom_components(workspace: str) -> CustomComponentsResource:
        return CustomComponentsResource(client=fake_client)

    fake_client.custom_components = custom_components  # type: ignore[method-assign]

    resource = fake_client.custom_components("test-workspace")
    result = await resource.list_installations()

    assert isinstance(result, CustomComponentInstallationList)
    assert len(result.data) == 0
    assert result.total == 0
    assert not result.has_more


@pytest.mark.asyncio
async def test_list_installations_with_params() -> None:
    """Test listing custom component installations with custom parameters."""
    mock_data = {
        "data": [],
        "total": 0,
        "has_more": False,
    }

    fake_client = BaseFakeClient(
        responses={"v2/custom_components?limit=50&page_number=2&field=status&order=ASC": mock_data}
    )

    def custom_components(workspace: str) -> CustomComponentsResource:
        return CustomComponentsResource(client=fake_client)

    fake_client.custom_components = custom_components  # type: ignore[method-assign]

    resource = fake_client.custom_components("test-workspace")
    await resource.list_installations(limit=50, page_number=2, field="status", order="ASC")

    # Check that the request was made with the correct parameters
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert "limit=50" in request["endpoint"]
    assert "page_number=2" in request["endpoint"]
    assert "field=status" in request["endpoint"]
    assert "order=ASC" in request["endpoint"]


@pytest.mark.asyncio
async def test_get_latest_installation_logs() -> None:
    """Test getting latest installation logs."""
    mock_logs = "Installation started\nInstalling dependencies\nInstallation complete"

    fake_client = BaseFakeClient(responses={"v2/custom_components/logs": mock_logs})

    def custom_components(workspace: str) -> CustomComponentsResource:
        return CustomComponentsResource(client=fake_client)

    fake_client.custom_components = custom_components  # type: ignore[method-assign]

    resource = fake_client.custom_components("test-workspace")
    result = await resource.get_latest_installation_logs()

    assert result == mock_logs
