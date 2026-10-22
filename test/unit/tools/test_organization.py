# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.api.transport import TransportResponse
from deepset_mcp.tools.organization import list_organizations
from test.unit.conftest import BaseFakeClient


@pytest.mark.asyncio
async def test_list_organizations_returns_organizations() -> None:
    orgs = [{"organization_id": "org-1", "name": "Acme"}]
    client = BaseFakeClient(responses={"/v2/organizations": {"organizations": orgs}})

    assert await list_organizations(client=client) == orgs


@pytest.mark.asyncio
async def test_list_organizations_explains_api_keys_on_401() -> None:
    client = BaseFakeClient(responses={"/v2/organizations": TransportResponse(text="", status_code=401, json=None)})

    result = await list_organizations(client=client)

    assert isinstance(result, str)
    assert "only works with OAuth" in result
    assert "bound to a single organization" in result
