"""Evidence parsing, traceback extraction, and outcome classification."""

import re
from typing import Any

from adversary.core.logging import get_logger
from adversary.models.enums import ExecutionOutcome
from adversary.models.schemas import ExecutionResult

logger = get_logger("adversary.evidence.collector")

EXCEPTION_REGEX = re.compile(
    r"^(?:E\s+)?([A-Z][a-zA-Z0-9_]*Error|[A-Z][a-zA-Z0-9_]*Exception|AssertionError|Failed):\s*(.*)$",
    re.MULTILINE,
)
TRACEBACK_HEADER_REGEX = re.compile(r"Traceback \(most recent call last\):", re.MULTILINE)


class EvidenceCollector:
    """Parses raw execution output, tracebacks, and classifies execution outcomes."""

    def parse_execution(
        self,
        test_id: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: float,
        timed_out: bool = False,
        env_info: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Construct structured ExecutionResult from raw process execution artifacts."""
        exec_id = f"EXEC-{test_id.replace('TEST-', '')}"
        metadata = env_info or {}

        if timed_out:
            return ExecutionResult(
                id=exec_id,
                test_id=test_id,
                outcome=ExecutionOutcome.TIMED_OUT,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr or "Execution timed out.",
                exception_name="TimeoutError",
                traceback_summary="Execution exceeded time limit and was terminated.",
                duration_ms=duration_ms,
                environment_info=metadata,
            )

        combined_output = f"{stdout}\n{stderr}".strip()

        # Parse exception name and message
        exc_match = EXCEPTION_REGEX.search(combined_output)
        exception_name: str | None = exc_match.group(1) if exc_match else None

        # Extract traceback snippet if present
        traceback_summary: str | None = None
        tb_pos = combined_output.find("Traceback (most recent call last):")
        if tb_pos != -1:
            traceback_summary = combined_output[tb_pos : tb_pos + 1500].strip()
        elif "FAILURES" in combined_output:
            fail_pos = combined_output.find("FAILURES")
            traceback_summary = combined_output[fail_pos : fail_pos + 1500].strip()

        # Classify outcome based on exit code and output
        if exit_code == 0:
            outcome = ExecutionOutcome.PASSED
        elif exit_code == 1:
            outcome = ExecutionOutcome.FAILED
        elif exit_code == 2:
            outcome = ExecutionOutcome.INVALID_TEST
        else:
            outcome = ExecutionOutcome.ERROR

        return ExecutionResult(
            id=exec_id,
            test_id=test_id,
            outcome=outcome,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            exception_name=exception_name,
            traceback_summary=traceback_summary,
            duration_ms=duration_ms,
            environment_info=metadata,
        )
