"""Domain enumerations for findings, verification, and execution."""

from enum import StrEnum


class Severity(StrEnum):
    """Measures potential impact of a defect."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Confidence(StrEnum):
    """Measures the strength of supporting evidence or static detection."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(StrEnum):
    """Evidence-based outcome classification for findings."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    DISPROVED = "disproved"
    INCONCLUSIVE = "inconclusive"
    UNVERIFIED = "unverified"
    EXECUTION_ERROR = "execution_error"


class FindingCategory(StrEnum):
    """Taxonomy category for code review findings."""

    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BOUNDARY_CONDITION = "boundary_condition"
    EXCEPTION_HANDLING = "exception_handling"
    RESOURCE_LEAK = "resource_leak"
    CONCURRENCY = "concurrency"
    BUSINESS_LOGIC = "business_logic"
    NUMERIC_UNDERFLOW = "numeric_underflow"
    STATE_MANAGEMENT = "state_management"
    TRANSACTION_ATOMICITY = "transaction_atomicity"
    INPUT_VALIDATION = "input_validation"
    LIFECYCLE_STATE_MACHINE = "lifecycle_state_machine"


class ExecutionOutcome(StrEnum):
    """Result of running a test in the Docker sandbox."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ERROR = "error"
    INVALID_TEST = "invalid_test"


class RepairStatus(StrEnum):
    """Status of patch generation and regression validation."""

    NOT_ATTEMPTED = "not_attempted"
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REVERTED = "reverted"
    APPLIED = "applied"
