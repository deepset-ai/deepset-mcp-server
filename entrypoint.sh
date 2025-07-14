#!/bin/sh
# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

# entrypoint.sh

# 1) Change into the app dir
cd /app

# 2) Make sure we use the venv’s Python
PYTHON_BIN=/app/.venv/bin/python

# 3) Point Python at the src/ directory so it can import deepset_mcp
export PYTHONPATH=/app/src

# 4) Exec your MCP server
exec "$PYTHON_BIN" -m deepset_mcp.main \
  --workspace "${DEEPSET_WORKSPACE}" \
  --api-key   "${DEEPSET_API_KEY}"