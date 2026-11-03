"""Typed domain models and schemas with Pydantic v2."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from adversary.models.enums import (
    Confidence,
    DifferentialOutcome,
    ExecutionOutcome,
    FindingCategory,
    RepairStatus,
    Severity,
    TestValidationStatus,
    VerificationStatus,
)


class SourceLocation(BaseModel):
    """Source code file and line coordinates."""

    model_config = ConfigDict(frozen=True)

    file_path: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    col_start: int | None = None
    col_end: int | None = None


class ASTFunctionInfo(BaseModel):
    """Metadata extracted from a Python function definition."""

    name: str
    docstring: str | None = None
    args: list[str] = Field(default_factory=list)
    returns: str | None = None
    is_async: bool = False
    line_start: int
    line_end: int
    called_functions: list[str] = Field(default_factory=list)


class ASTClassInfo(BaseModel):
    """Metadata extracted from a Python class definition."""

    name: str
    docstring: str | None = None
    methods: list[ASTFunctionInfo] = Field(default_factory=list)
    line_start: int
    line_end: int


class ASTModuleInfo(BaseModel):
    """Metadata and symbols extracted from a Python module."""

    file_path: str
    relative_path: str
    imports: list[str] = Field(default_factory=list)
    functions: list[ASTFunctionInfo] = Field(default_factory=list)
    classes: list[ASTClassInfo] = Field(default_factory=list)
    sha256_hash: str
    line_count: int


class RepositoryManifest(BaseModel):
    """Complete inventory of target repository structure and symbols."""

    root_path: str
    git_commit: str | None = None
    source_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    total_lines: int = 0
    modules: dict[str, ASTModuleInfo] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandidateFinding(BaseModel):
    """A suspicious code pattern or static diagnostic pending verification."""

    id: str
    title: str
    description: str
    category: FindingCategory
    severity: Severity
    confidence: Confidence
    location: SourceLocation
    originating_tool: str
    rule_id: str | None = None
    suggested_remediation: str | None = None
    verification_status: VerificationStatus = VerificationStatus.CANDIDATE
    source_hash: str | None = None
    base_commit: str | None = None
    target_commit: str | None = None
    hypothesis_id: str | None = None
    test_artifact_id: str | None = None
    evidence_id: str | None = None
    decision_id: str | None = None


class TestValidationResult(BaseModel):
    """Structured quality and security validation assessment of a test artifact."""

    __test__ = False

    is_valid: bool
    status: TestValidationStatus
    reasons: list[str] = Field(default_factory=list)
    checks_passed: list[str] = Field(default_factory=list)
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DefectHypothesis(BaseModel):
    """Formal hypothesis stating conditions to trigger and observe a defect."""

    id: str
    finding_id: str
    target_file: str
    target_function: str | None = None
    preconditions: str
    trigger_input: str
    expected_behavior: str
    defect_behavior: str
    rationale: str


class TestArtifact(BaseModel):
    """Adversarial test generated to reproduce or disprove a defect hypothesis."""

    __test__ = False

    id: str
    hypothesis_id: str
    file_name: str
    code: str
    strategy: str  # e.g., boundary, empty_input, property_based, exception_path
    timeout_seconds: int = 30
    dependencies: list[str] = Field(default_factory=list)
    validation_result: TestValidationResult | None = None


class ExecutionResult(BaseModel):
    """Result and evidence captured from Docker container execution."""

    id: str
    test_id: str
    outcome: ExecutionOutcome
    exit_code: int
    stdout: str
    stderr: str
    exception_name: str | None = None
    traceback_summary: str | None = None
    duration_ms: float = 0.0
    environment_info: dict[str, Any] = Field(default_factory=dict)


class VerificationDecision(BaseModel):
    """Independent verification outcome determining if evidence supports finding."""

    id: str
    finding_id: str
    hypothesis_id: str
    status: VerificationStatus
    is_attributed_to_target: bool
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    differential_outcome: DifferentialOutcome = DifferentialOutcome.NOT_APPLICABLE
    base_evidence_id: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PatchArtifact(BaseModel):
    """Minimal proposed code fix with validation proofs."""

    id: str
    finding_id: str
    diff: str
    affected_files: list[str]
    explanation: str
    repair_status: RepairStatus = RepairStatus.PROPOSED
    adversarial_test_passed: bool = False
    regression_tests_passed: bool = False
    applied_to_repo: bool = False
    patched_content: str | None = None


class ReviewReport(BaseModel):
    """Comprehensive review report with complete traceability."""

    run_id: str
    repo_path: str
    git_commit: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    findings: list[CandidateFinding] = Field(default_factory=list)
    hypotheses: list[DefectHypothesis] = Field(default_factory=list)
    tests: list[TestArtifact] = Field(default_factory=list)
    executions: list[ExecutionResult] = Field(default_factory=list)
    decisions: list[VerificationDecision] = Field(default_factory=list)
    patches: list[PatchArtifact] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
