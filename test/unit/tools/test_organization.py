# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from deepset_mcp.tools.organization import list_organizations
from test.unit.conftest import BaseFakeClient


@pytest.mark.asyncio
async def test_list_organizations_returns_organizations() -> None:
    orgs = [{"organization_id": "org-1", "name": "Acme"}]
    client = BaseFakeClient(responses={"/v2/organizations": {"organizations": orgs}})

    assert await list_organizations(client=client) == orgs
