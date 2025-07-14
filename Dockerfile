# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

# ─── BUILD STAGE ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# 1. Install curl & build tools for uv & any C extensions
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl build-essential git \
 && rm -rf /var/lib/apt/lists/*

# 2. Install uv standalone and symlink it
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && ln -sf /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /src

# We need git for uv-dynamic-versioning
COPY .git/ .git/

# 3. Copy in only what uv needs to build the locked venv
COPY pyproject.toml uv.lock README.md entrypoint.sh ./
COPY src/deepset_mcp/ src/deepset_mcp/

# 4. Create & populate .venv from uv.lock
RUN uv sync --locked



# ─── RUNTIME STAGE ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# 2. Create an unprivileged user with a home directory
RUN groupadd --system appgroup \
 && useradd --system --create-home --home-dir /home/appuser --gid appgroup appuser

ENV HOME=/home/appuser

WORKDIR /app

# 5. Copy in the pre-built venv and your project sources
COPY --from=builder /src/.venv               /app/.venv
COPY --from=builder /src/pyproject.toml      /app/pyproject.toml
COPY --from=builder /src/uv.lock              /app/uv.lock
COPY --from=builder /src/README.md            /app/README.md
COPY --from=builder /src/src/deepset_mcp      /app/src/deepset_mcp
COPY --from=builder /src/entrypoint.sh        /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# 6. Ensure appuser owns all of /app
RUN chown -R appuser:appgroup /app

# 7. Put the venv’s bin first in PATH
ENV PATH="/app/.venv/bin:${PATH}"

# 9. Switch to non-root user
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
