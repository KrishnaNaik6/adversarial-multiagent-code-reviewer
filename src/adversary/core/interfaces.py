"""Core interfaces and contracts for the modular architecture."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from adversary.models.schemas import (
    CandidateFinding,
    DefectHypothesis,
    ExecutionResult,
    PatchArtifact,
    RepositoryManifest,
    ReviewReport,
    TestArtifact,
    VerificationDecision,
)


@runtime_checkable
class RepositoryScannerProtocol(Protocol):
    """Protocol for repository scanning and AST intelligence."""

    def scan(self, repo_path: Path) -> RepositoryManifest:
        """Scan repository and produce structured manifest."""
        ...


@runtime_checkable
class StaticAnalyzerProtocol(Protocol):
    """Protocol for deterministic static analysis tools."""

    name: str

    def analyze(self, repo_path: Path, manifest: RepositoryManifest) -> list[CandidateFinding]:
        """Execute analyzer and return candidate findings."""
        ...


@runtime_checkable
class BreakerProtocol(Protocol):
    """Protocol for the Red Team / Breaker adversarial test generator."""

    def generate_tests(
        self,
        hypothesis: DefectHypothesis,
        manifest: RepositoryManifest,
    ) -> list[TestArtifact]:
        """Generate adversarial test artifacts targeting the hypothesis."""
        ...


@runtime_checkable
class SandboxRunnerProtocol(Protocol):
    """Protocol for isolated Docker sandbox execution."""

    def execute_test(
        self,
        repo_path: Path,
        test_artifact: TestArtifact,
        timeout_seconds: int = 30,
    ) -> ExecutionResult:
        """Execute a test artifact inside the isolated container environment."""
        ...


@runtime_checkable
class VerifierProtocol(Protocol):
    """Protocol for the Independent Verification Agent."""

    def verify(
        self,
        hypothesis: DefectHypothesis,
        test_artifact: TestArtifact,
        execution_result: ExecutionResult,
    ) -> VerificationDecision:
        """Independently evaluate execution evidence against the defect hypothesis."""
        ...


@runtime_checkable
class PatcherProtocol(Protocol):
    """Protocol for the Blue Team / Patcher repair engine."""

    def propose_patch(
        self,
        finding: CandidateFinding,
        hypothesis: DefectHypothesis,
        repo_path: Path,
    ) -> PatchArtifact | None:
        """Generate a minimal patch for a verified defect in an isolated workspace."""
        ...


@runtime_checkable
class PersistenceProtocol(Protocol):
    """Protocol for persistence and report storage."""

    def save_run(self, report: ReviewReport) -> str:
        """Persist a complete review report and return run ID."""
        ...

    def get_run(self, run_id: str) -> ReviewReport | None:
        """Retrieve a review report by run ID."""
        ...
