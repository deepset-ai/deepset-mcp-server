# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

.PHONY: help install test test-unit test-integration test-integration-slow test-all lint lint-fix format format-check types clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install              Install dependencies with uv"
	@echo "  test-unit            Run unit tests only (excludes integration tests)"
	@echo "  test-integration     Run integration tests without extra slow tests"
	@echo "  test-integration-slow Run integration tests including extra slow tests"
	@echo "  test-all             Run all tests"
	@echo "  lint                 Run ruff check"
	@echo "  lint-fix             Run ruff check with --fix"
	@echo "  format               Run ruff format"
	@echo "  format-check         Run ruff format with --check"
	@echo "  types                Run mypy type checking"
	@echo "  clean                Clean up cache files"

# Install dependencies
install:
	uv sync --locked --all-extras --all-groups

# Test commands
test-unit:
	uv run --dev pytest -m "not integration"

test-integration:
	uv run --dev pytest -m "integration and not extra_slow"

test-integration-slow:
	uv run --dev pytest -m "integration"

test-all:
	uv run --dev pytest

# Shorthand for test-unit (most common use case)
test: test-unit

# Linting commands
lint:
	uv run ruff check

lint-fix:
	uv run ruff check --fix

# Formatting commands
format:
	uv run ruff format

format-check:
	uv run ruff format --check

# Type checking
types:
	uv run mypy src/ test/

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
