"""Workflow state machine and transition tracker."""

from enum import StrEnum
from typing import Any

from adversary.core.errors import AdversaryError
from adversary.core.logging import get_logger

logger = get_logger("adversary.orchestration.state")


class WorkflowState(StrEnum):
    """Explicit workflow states for the multi-agent review lifecycle."""

    CREATED = "created"
    INDEXED = "indexed"
    ANALYZED = "analyzed"
    HYPOTHESIZED = "hypothesized"
    TESTS_GENERATED = "tests_generated"
    SANDBOX_EXECUTED = "sandbox_executed"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.CREATED: {WorkflowState.INDEXED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.INDEXED: {WorkflowState.ANALYZED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.ANALYZED: {WorkflowState.HYPOTHESIZED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.HYPOTHESIZED: {WorkflowState.TESTS_GENERATED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.TESTS_GENERATED: {WorkflowState.SANDBOX_EXECUTED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.SANDBOX_EXECUTED: {WorkflowState.VERIFIED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.VERIFIED: {WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.COMPLETED: set(),
    WorkflowState.FAILED: set(),
    WorkflowState.CANCELLED: set(),
}


class WorkflowContext:
    """Maintains active review workflow state, timestamps, and transition history."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.current_state: WorkflowState = WorkflowState.CREATED
        self.history: list[dict[str, Any]] = [{"state": self.current_state, "message": "Workflow created"}]

    def transition_to(self, new_state: WorkflowState, message: str = "") -> None:
        """Enforce valid state transition graph."""
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            raise AdversaryError(
                f"Invalid workflow state transition: cannot transition from {self.current_state} to {new_state}"
            )

        self.current_state = new_state
        self.history.append({"state": new_state, "message": message})
        logger.info("Workflow [%s] transitioned to %s: %s", self.run_id, new_state, message)
