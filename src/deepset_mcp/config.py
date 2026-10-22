# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""This module contains static configuration for the deepset MCP server."""

import importlib.metadata
import os

try:
    __version__ = importlib.metadata.version("deepset-mcp")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development mode

PACKAGE_VERSION = __version__

DEEPSET_DOCS_DEFAULT_SHARE_URL = "https://cloud.deepset.ai/shared_prototypes?share_token=prototype_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MTk3NTY4MDAuMCwiYXVkIjoiZXh0ZXJuYWwgdXNlciIsImlzcyI6ImRDIiwid29ya3NwYWNlX2lkIjoiOGMyNGYxMTItYjI5Yy00OTFjLTk5MzktYWU5MTA0YTU0MjFjIiwid29ya3NwYWNlX25hbWUiOiJkYy1kb2NzLWNvbnRlbnQiLCJvcmdhbml6YXRpb25faWQiOiJjYTlmMTRkNC1jMmM5LTQ2MGQtOGQyNi1mOGNiMGFjYTAyNGYiLCJzaGFyZV9pZCI6ImUwOWI3ZGQzLThhNGQtNGZhMi05NzRhLTczYzM4ZTZiMmU2YiIsImxvZ2luX3JlcXVpcmVkIjpmYWxzZX0.U1HQLhTQkf32t-SO-331Dbu546SrVSrfJrG32pB_0qA"
DOCS_BASE_URL = "https://docs.cloud.deepset.ai"
DOCS_SEARCH_API_URL = f"{DOCS_BASE_URL}/api/search"
DOCS_SEARCH_TOOL_NAME = "search_docs"
LIST_DOC_SECTIONS_TOOL_NAME = "list_doc_sections"

DEFAULT_CLIENT_HEADER = {"headers": {"User-Agent": f"deepset-mcp/{__version__}"}}
DEEPSET_CLIENT_TIMEOUT = float(os.environ.get("DEEPSET_CLIENT_TIMEOUT", 5))  # seconds
