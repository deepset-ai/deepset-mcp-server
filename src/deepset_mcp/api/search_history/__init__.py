# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Search history API module."""

from .models import SearchHistoryEntry
from .resource import SearchHistoryResource

__all__ = ["SearchHistoryEntry", "SearchHistoryResource"]
