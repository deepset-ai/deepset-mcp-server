import asyncio
import os
from pathlib import Path
from typing import Any

from deepset_mcp.api.client import AsyncDeepsetClient
from deepset_mcp.benchmark.runner.models import TestCaseConfig


def _get_api_key(explicit_key: str | None) -> str:
    """
    Return whichever API key to use: explicit_key takes precedence, otherwise read DP_API_KEY from the environment.

    If still missing, raise ValueError.
    """
    if explicit_key:
        return explicit_key
    env_key = os.getenv("DP_API_KEY")
    if not env_key:
        raise ValueError("No API key provided: pass --api-key or set DP_API_KEY in env.")
    return env_key


# ─────────────────────────────────────────────────────────────────────────────
# 1) LOW-LEVEL: “setup_pipeline” and “setup_index” using AsyncDeepsetClient as a context manager
# ─────────────────────────────────────────────────────────────────────────────


async def setup_pipeline_async(
    *,
    yaml_path: str | None = None,
    yaml_content: str | None = None,
    pipeline_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """
    Create a new pipeline in the given workspace. Exactly one of (yaml_path, yaml_content) must be provided.

    Uses DP_API_KEY or explicit api_key.
    """
    if (yaml_path and yaml_content) or (not yaml_path and not yaml_content):
        raise ValueError("Exactly one of `yaml_path` or `yaml_content` must be specified.")

    if yaml_path is not None:
        yaml_str = Path(yaml_path).read_text(encoding="utf-8")
    else:
        yaml_str = yaml_content  # type: ignore

    key_to_use = _get_api_key(api_key)
    async with AsyncDeepsetClient(api_key=key_to_use) as client:
        await client.pipelines(workspace=workspace_name).create(
            name=pipeline_name,
            yaml_config=yaml_str,
        )
    return None


async def setup_index_async(
    *,
    yaml_path: str | None = None,
    yaml_content: str | None = None,
    index_name: str,
    workspace_name: str,
    api_key: str | None = None,
    description: str | None = None,
) -> None:
    """
    Create a new index in the given workspace. Exactly one of (yaml_path, yaml_content) must be provided.

    Uses DP_API_KEY or explicit api_key.
    """
    if (yaml_path and yaml_content) or (not yaml_path and not yaml_content):
        raise ValueError("Exactly one of `yaml_path` or `yaml_content` must be specified.")

    if yaml_path is not None:
        yaml_str = Path(yaml_path).read_text(encoding="utf-8")
    else:
        yaml_str = yaml_content  # type: ignore

    key_to_use = _get_api_key(api_key)
    async with AsyncDeepsetClient(api_key=key_to_use) as client:
        await client.indexes(workspace=workspace_name).create(
            name=index_name,
            yaml_config=yaml_str,
            description=description or "",
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2) MID-LEVEL: setup a full test-case (pipeline + index if present)
# ─────────────────────────────────────────────────────────────────────────────


async def setup_test_case_async(
    *,
    test_cfg: TestCaseConfig,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """
    Given a TestCaseConfig, create the index and the pipeline in the specified workspace.

    Uses DP_API_KEY or explicit api_key.
    """
    # 1) If there’s an index to create:
    if test_cfg.index_yaml:
        assert test_cfg.index_name is not None  # already validated by Pydantic model; added to satisfy mypy
        await setup_index_async(
            yaml_content=test_cfg.get_index_yaml_text(),
            index_name=test_cfg.index_name,
            workspace_name=workspace_name,
            api_key=api_key,
            description=f"Index for test {test_cfg.name}",
        )

    # 2) If there’s a “query pipeline” to create:
    if test_cfg.query_yaml:
        assert test_cfg.query_name is not None  # already validated by Pydantic model; added to satisfy mypy
        await setup_pipeline_async(
            yaml_content=test_cfg.get_query_yaml_text(),
            pipeline_name=test_cfg.query_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 3) HIGH-LEVEL: parallel “setup all” with configurable concurrency
# ─────────────────────────────────────────────────────────────────────────────


async def setup_all_async(
    *,
    test_cfgs: list[TestCaseConfig],
    workspace_name: str,
    api_key: str | None = None,
    concurrency: int = 5,
) -> None:
    """
    Given a list of TestCaseConfig, create all indexes and pipelines in parallel.

    Uses DP_API_KEY or explicit api_key.
    """
    semaphore = asyncio.Semaphore(concurrency)
    tasks: list[asyncio.Task[Any]] = []

    async def sem_task(cfg: TestCaseConfig) -> str:
        async with semaphore:
            await setup_test_case_async(test_cfg=cfg, workspace_name=workspace_name, api_key=api_key)
            return cfg.name

    for cfg in test_cfgs:
        tasks.append(asyncio.create_task(sem_task(cfg)))

    done, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    errors: list[Exception] = []
    for t in done:
        if t.exception():
            errors.append(t.exception())  # type: ignore

    if errors:
        raise RuntimeError(f"Errors during setup: {errors}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4) SYNC WRAPPERS for all of the above (now accept api_key)
# ─────────────────────────────────────────────────────────────────────────────


def setup_pipeline(
    *,
    yaml_path: str | None = None,
    yaml_content: str | None = None,
    pipeline_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """Synchronous wrapper for setup_pipeline_async. Blocks until the pipeline is created."""
    return asyncio.run(
        setup_pipeline_async(
            yaml_path=yaml_path,
            yaml_content=yaml_content,
            pipeline_name=pipeline_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
    )


def setup_index(
    *,
    yaml_path: str | None = None,
    yaml_content: str | None = None,
    index_name: str,
    workspace_name: str,
    api_key: str | None = None,
    description: str | None = None,
) -> None:
    """Synchronous wrapper for setup_index_async. Blocks until the index is created."""
    return asyncio.run(
        setup_index_async(
            yaml_path=yaml_path,
            yaml_content=yaml_content,
            index_name=index_name,
            workspace_name=workspace_name,
            api_key=api_key,
            description=description,
        )
    )


def setup_test_case(
    *,
    test_cfg: TestCaseConfig,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """Synchronous wrapper: blocks until both pipeline and index (if any) are created."""
    return asyncio.run(setup_test_case_async(test_cfg=test_cfg, workspace_name=workspace_name, api_key=api_key))


def setup_all(
    *,
    test_cfgs: list[TestCaseConfig],
    workspace_name: str,
    api_key: str | None = None,
    concurrency: int = 5,
) -> None:
    """Synchronous wrapper for setup_all_async. Blocks until all test-cases are created."""
    return asyncio.run(
        setup_all_async(test_cfgs=test_cfgs, workspace_name=workspace_name, api_key=api_key, concurrency=concurrency)
    )
