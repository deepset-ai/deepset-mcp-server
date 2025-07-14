# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Workspace API module."""

from .models import Workspace, WorkspaceList
from .protocols import WorkspaceResourceProtocol
from .resource import WorkspaceResource

__all__ = ["Workspace", "WorkspaceList", "WorkspaceResourceProtocol", "WorkspaceResource"]
