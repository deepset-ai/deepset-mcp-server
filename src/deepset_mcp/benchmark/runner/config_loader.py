import glob
from pathlib import Path

from pydantic import ValidationError

from deepset_mcp.benchmark.runner.models import TestCaseConfig


def _default_task_dir() -> Path:
    """Return the path to the `benchmark/tasks` directory, resolved relative to this file."""
    return Path(__file__).parent.parent / "tasks"


def find_all_test_case_paths(task_dir: str | Path | None = None) -> list[Path]:
    """
    Return a list of all `.yml` or `.yaml` files under `task_dir`.

    If `task_dir` is None, we resolve to `benchmark/tasks` (relative to this file).
    """
    if task_dir is None:
        base = _default_task_dir()
    else:
        base = Path(task_dir)

    pattern1 = base / "*.yml"
    pattern2 = base / "*.yaml"
    return [Path(p) for p in glob.glob(str(pattern1))] + [Path(p) for p in glob.glob(str(pattern2))]


def load_test_case_from_path(path: Path) -> TestCaseConfig:
    """
    Read a single test-case YAML at `path` using TestCaseConfig.from_file().

    Raises RuntimeError if validation or loading fails.
    """
    try:
        return TestCaseConfig.from_file(path)
    except (ValidationError, FileNotFoundError) as e:
        raise RuntimeError(f"Failed to load {path}: {e}") from e


def load_test_case_by_name(name: str, task_dir: str | Path | None = None) -> TestCaseConfig:
    """
    Given a test‐case “name” (without extension), locate the corresponding `.yml` or `.yaml`under `task_dir`.

    If `task_dir` is None, defaults to `benchmark/tasks` relative to this file.
    Returns a loaded TestCaseConfig or raises FileNotFoundError if not found.
    """
    if task_dir is None:
        base = _default_task_dir()
    else:
        base = Path(task_dir)

    candidates: list[Path] = []
    for ext in (".yml", ".yaml"):
        p = base / f"{name}{ext}"
        if p.exists():
            candidates.append(p)

    if not candidates:
        raise FileNotFoundError(f"No test-case named '{name}' under {base}")

    # If multiple matches exist, pick the first
    return load_test_case_from_path(candidates[0])
