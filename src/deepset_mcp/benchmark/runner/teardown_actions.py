import asyncio
import os
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
# 1) LOW-LEVEL: "teardown_pipeline" and "teardown_index" using AsyncDeepsetClient as a context manager
# ─────────────────────────────────────────────────────────────────────────────


async def teardown_pipeline_async(
    *,
    pipeline_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """
    Delete a pipeline in the given workspace.

    Uses DP_API_KEY or explicit api_key.
    """
    key_to_use = _get_api_key(api_key)
    async with AsyncDeepsetClient(api_key=key_to_use) as client:
        await client.pipelines(workspace=workspace_name).delete(pipeline_name)
    return None


async def teardown_index_async(
    *,
    index_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """
    Delete an index in the given workspace.

    Uses DP_API_KEY or explicit api_key.
    """
    key_to_use = _get_api_key(api_key)
    async with AsyncDeepsetClient(api_key=key_to_use) as client:
        await client.indexes(workspace=workspace_name).delete(index_name)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2) MID-LEVEL: teardown a full test-case (pipeline + index if present)
# ─────────────────────────────────────────────────────────────────────────────


async def teardown_test_case_async(
    *,
    test_cfg: TestCaseConfig,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """
    Given a TestCaseConfig, delete the index and the pipeline in the specified workspace.

    Uses DP_API_KEY or explicit api_key.
    """
    # 1) If there's a "query pipeline" to delete:
    if test_cfg.query_yaml:
        assert test_cfg.query_name is not None  # already validated by Pydantic model; added to satisfy mypy
        await teardown_pipeline_async(
            pipeline_name=test_cfg.query_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )

    # 2) If there's an index to delete:
    if test_cfg.index_yaml:
        assert test_cfg.index_name is not None  # already validated by Pydantic model; added to satisfy mypy
        await teardown_index_async(
            index_name=test_cfg.index_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 3) HIGH-LEVEL: parallel "teardown all" with configurable concurrency
# ─────────────────────────────────────────────────────────────────────────────


async def teardown_all_async(
    *,
    test_cfgs: list[TestCaseConfig],
    workspace_name: str,
    api_key: str | None = None,
    concurrency: int = 5,
) -> None:
    """
    Given a list of TestCaseConfig, delete all indexes and pipelines in parallel.

    Uses DP_API_KEY or explicit api_key.
    """
    semaphore = asyncio.Semaphore(concurrency)
    tasks: list[asyncio.Task[Any]] = []

    async def sem_task(cfg: TestCaseConfig) -> str:
        async with semaphore:
            await teardown_test_case_async(test_cfg=cfg, workspace_name=workspace_name, api_key=api_key)
            return cfg.name

    for cfg in test_cfgs:
        tasks.append(asyncio.create_task(sem_task(cfg)))

    done, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    errors: list[Exception] = []
    for t in done:
        if t.exception():
            errors.append(t.exception())  # type: ignore

    if errors:
        raise RuntimeError(f"Errors during teardown: {errors}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4) SYNC WRAPPERS for all of the above (now accept api_key)
# ─────────────────────────────────────────────────────────────────────────────


def teardown_pipeline(
    *,
    pipeline_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """Synchronous wrapper for teardown_pipeline_async. Blocks until the pipeline is deleted."""
    return asyncio.run(
        teardown_pipeline_async(
            pipeline_name=pipeline_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
    )


def teardown_index(
    *,
    index_name: str,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """Synchronous wrapper for teardown_index_async. Blocks until the index is deleted."""
    return asyncio.run(
        teardown_index_async(
            index_name=index_name,
            workspace_name=workspace_name,
            api_key=api_key,
        )
    )


def teardown_test_case(
    *,
    test_cfg: TestCaseConfig,
    workspace_name: str,
    api_key: str | None = None,
) -> None:
    """Synchronous wrapper: blocks until both pipeline and index (if any) are deleted."""
    return asyncio.run(teardown_test_case_async(test_cfg=test_cfg, workspace_name=workspace_name, api_key=api_key))


def teardown_all(
    *,
    test_cfgs: list[TestCaseConfig],
    workspace_name: str,
    api_key: str | None = None,
    concurrency: int = 5,
) -> None:
    """Synchronous wrapper for teardown_all_async. Blocks until all test-cases are deleted."""
    return asyncio.run(
        teardown_all_async(test_cfgs=test_cfgs, workspace_name=workspace_name, api_key=api_key, concurrency=concurrency)
    )
