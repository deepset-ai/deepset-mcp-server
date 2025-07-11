import glob
import json
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from deepset_mcp.benchmark.core.config import TestCaseConfig
from deepset_mcp.benchmark.core.exceptions import TestCaseNotFoundError
from deepset_mcp.benchmark.logging.logging_config import get_benchmark_logger


class BenchmarkRepositoryProtocol(Protocol):
    """Interface for interacting with benchmark configurations and to persist results."""

    def save_test_result(
        self,
        test_case_name: str,
        run_id: str,
        result_data: dict[str, Any],
        output_dir: Path,
    ) -> Path:
        """Save individual test result to storage."""
        ...

    def save_run_summary(
        self,
        run_id: str,
        summary_data: dict[str, Any],
        output_dir: Path,
    ) -> Path:
        """Save benchmark run summary to storage."""
        ...

    def load_test_result(self, result_path: Path) -> dict[str, Any]:
        """Load test result from storage."""
        ...

    def load_test_case(self, name: str, base_dir: Path | None = None) -> TestCaseConfig:
        """Load a test case configuration by name."""
        ...

    def find_all_test_cases(self, base_dir: Path) -> list[TestCaseConfig]:
        """Find all available test cases in a directory."""
        ...


class FileSystemBenchmarkRepository(BenchmarkRepositoryProtocol):
    """Benchmark repository using filesystem storage for test cases and results."""

    def __init__(self, debug: bool = False):
        """Initialize the repository."""
        self.logger = get_benchmark_logger(__name__, debug)

    def default_task_dir(self) -> Path:
        """Return the path to the `benchmark/tasks` directory, resolved relative to this file."""
        return Path(__file__).parent.parent / "tasks"

    def find_all_test_case_paths(self, task_dir: str | Path | None = None) -> list[Path]:
        """
        Return a list of all `.yml` or `.yaml` files under `task_dir`.

        If `task_dir` is None, we resolve to `benchmark/tasks` (relative to this file).
        """
        if task_dir is None:
            base = self.default_task_dir()
        else:
            base = Path(task_dir)

        pattern1 = base / "*.yml"
        pattern2 = base / "*.yaml"
        return [Path(p) for p in glob.glob(str(pattern1))] + [Path(p) for p in glob.glob(str(pattern2))]

    def load_test_case_from_path(self, path: Path) -> TestCaseConfig:
        """
        Read a single test-case YAML at `path` using TestCaseConfig.from_file().

        Raises RuntimeError if validation or loading fails.
        """
        try:
            return TestCaseConfig.from_file(path)
        except (ValidationError, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to load {path}: {e}") from e

    def load_test_case_by_name(self, name: str, task_dir: str | Path | None = None) -> TestCaseConfig:
        """
        Given a test‐case "name" (without extension), locate the corresponding `.yml` or `.yaml`under `task_dir`.

        If `task_dir` is None, defaults to `benchmark/tasks` relative to this file.
        Returns a loaded TestCaseConfig or raises FileNotFoundError if not found.
        """
        if task_dir is None:
            base = self.default_task_dir()
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
        return self.load_test_case_from_path(candidates[0])

    def load_test_case(self, name: str, base_dir: Path | None = None) -> TestCaseConfig:
        """Load a test case configuration by name."""
        try:
            test_case = self.load_test_case_by_name(name=name, task_dir=str(base_dir) if base_dir else None)

            self.logger.debug(
                "Loaded test case",
                {
                    "name": name,
                    "base_dir": str(base_dir) if base_dir else None,
                },
            )

            return test_case

        except Exception as e:
            raise TestCaseNotFoundError(name, str(base_dir)) from e

    def find_all_test_cases(self, base_dir: Path) -> list[TestCaseConfig]:
        """Find all available test cases in a directory."""
        try:
            test_paths = self.find_all_test_case_paths(base_dir)
            test_cases = []

            for test_path in test_paths:
                try:
                    test_case = TestCaseConfig.from_file(test_path)
                    test_cases.append(test_case)
                except Exception as e:
                    self.logger.warning(
                        "Failed to load test case",
                        {
                            "path": str(test_path),
                            "error": str(e),
                        },
                    )

            self.logger.info(f"Found {len(test_cases)} test cases in {base_dir}")
            return test_cases

        except Exception as e:
            self.logger.error(
                "Failed to find test cases",
                {
                    "base_dir": str(base_dir),
                    "error": str(e),
                },
            )
            return []

    def save_test_result(
        self,
        test_case_name: str,
        run_id: str,
        result_data: dict[str, Any],
        output_dir: Path,
    ) -> Path:
        """Save individual test result to storage."""
        # Create directory structure
        run_dir = output_dir / "agent_runs" / run_id
        test_case_dir = run_dir / test_case_name
        test_case_dir.mkdir(parents=True, exist_ok=True)

        # Save messages.json
        messages_file = test_case_dir / "messages.json"
        with open(messages_file, "w", encoding="utf-8") as f:
            json.dump(result_data.get("agent_execution", {}).get("messages", []), f, indent=2)

        # Save test_results.csv
        csv_file = test_case_dir / "test_results.csv"
        self._save_test_csv(csv_file, test_case_name, result_data)

        # Save post_run_pipeline.yml if available
        if result_data.get("post_pipeline_yaml"):
            pipeline_file = test_case_dir / "post_run_pipeline.yml"
            with open(pipeline_file, "w", encoding="utf-8") as f:
                f.write(result_data["post_pipeline_yaml"])

        self.logger.info(
            "Test result saved",
            {
                "test_case": test_case_name,
                "run_id": run_id,
                "output_dir": str(test_case_dir),
            },
        )

        return test_case_dir

    def save_run_summary(
        self,
        run_id: str,
        summary_data: dict[str, Any],
        output_dir: Path,
    ) -> Path:
        """Save benchmark run summary to storage."""
        run_dir = output_dir / "agent_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        summary_file = run_dir / "run_summary.csv"

        # Create CSV content
        headers = [
            "run_id",
            "total_tests",
            "completed_tests",
            "failed_tests",
            "validation_passes",
            "validation_total",
            "validation_rate_percent",
            "total_tokens",
            "total_tool_calls",
            "avg_tool_calls",
        ]

        values = [str(summary_data.get(header, "")) for header in headers]

        csv_content = ",".join(headers) + "\n" + ",".join(values)

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(csv_content)

        self.logger.info(
            "Run summary saved",
            {
                "run_id": run_id,
                "summary_file": str(summary_file),
            },
        )

        return summary_file

    def load_test_result(self, result_path: Path) -> dict[str, Any]:
        """Load test result from storage."""
        try:
            messages_file = result_path / "messages.json"
            if messages_file.exists():
                with open(messages_file, encoding="utf-8") as f:
                    messages = json.load(f)
                return {"messages": messages}
            return {}
        except Exception as e:
            self.logger.error(
                "Failed to load test result",
                {
                    "result_path": str(result_path),
                    "error": str(e),
                },
            )
            return {}

    def _save_test_csv(self, csv_file: Path, test_case_name: str, result_data: dict[str, Any]) -> None:
        """Save test result as CSV."""
        metadata = result_data.get("metadata", {})
        agent_execution = result_data.get("agent_execution", {})
        validation = result_data.get("validation", {})

        # Extract data with defaults
        commit_hash = metadata.get("agent", {}).get("commit_hash", "unknown")
        agent_name = metadata.get("agent", {}).get("name", "unknown")
        usage = agent_execution.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        tool_calls = len(agent_execution.get("tool_calls", []))
        model = agent_execution.get("model", "unknown")

        pre_val = validation.get("pre_validation", {})
        post_val = validation.get("post_validation", {})
        pre_validation = "PASS" if pre_val.get("valid") else "FAIL" if pre_val else "N/A"
        post_validation = "PASS" if post_val.get("valid") else "FAIL" if post_val else "N/A"

        headers = [
            "commit",
            "test_case",
            "agent",
            "prompt_tokens",
            "completion_tokens",
            "tool_calls",
            "model",
            "pre_validation",
            "post_validation",
        ]

        values = [
            commit_hash,
            test_case_name,
            agent_name,
            str(prompt_tokens),
            str(completion_tokens),
            str(tool_calls),
            model,
            pre_validation,
            post_validation,
        ]

        csv_content = ",".join(headers) + "\n" + ",".join(values)

        with open(csv_file, "w", encoding="utf-8") as f:
            f.write(csv_content)
