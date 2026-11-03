"""Central orchestrator driving the closed-loop multi-agent review workflow."""

import contextlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from adversary.analysis.findings.engine import FindingEngine
from adversary.config.settings import AdversaryConfig
from adversary.core.logging import get_logger
from adversary.hypotheses.generator import HypothesisGenerator
from adversary.models.enums import VerificationStatus
from adversary.models.schemas import (
    CandidateFinding,
    DefectHypothesis,
    ExecutionResult,
    ReviewReport,
    TestArtifact,
    VerificationDecision,
)
from adversary.orchestration.state import WorkflowContext, WorkflowState
from adversary.persistence.repository import RunStore
from adversary.repository.git import get_git_info
from adversary.repository.scanner import RepositoryScanner
from adversary.sandbox.differential import DifferentialRunner
from adversary.sandbox.runner import DockerSandboxRunner
from adversary.test_generation.breaker import BreakerAgent
from adversary.verification.verifier import IndependentVerifier

logger = get_logger("adversary.orchestration.coordinator")


class ReviewOrchestrator:
    """Coordinates logical agents through the verification workflow with state validation."""

    def __init__(self, config: AdversaryConfig | None = None) -> None:
        self.config = config or AdversaryConfig()
        self.scanner = RepositoryScanner()
        self.finding_engine = FindingEngine()
        self.hypothesis_gen = HypothesisGenerator()
        self.breaker = BreakerAgent()
        self.sandbox = DockerSandboxRunner(config=self.config.sandbox)
        self.diff_runner = DifferentialRunner(self.sandbox)
        self.verifier = IndependentVerifier()
        self.store = RunStore(self.config.db_path)

    def run(self, repo_path: Path, base_ref: str | None = None) -> ReviewReport:
        """Execute full review pipeline from repository ingestion to verified report."""
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_id = f"RUN-{timestamp_str}-{uuid.uuid4().hex[:6]}"
        ctx = WorkflowContext(run_id)

        try:
            # Stage 1: Ingestion & Repository Intelligence
            canonical_repo = repo_path.resolve()
            logger.info("Stage 1: Scanning repository at %s", canonical_repo)
            manifest = self.scanner.scan(canonical_repo)
            git_info = get_git_info(canonical_repo)
            ctx.transition_to(WorkflowState.INDEXED, f"Indexed {len(manifest.source_files)} source files")

            # Stage 2: Deterministic Static Analysis
            logger.info("Stage 2: Running deterministic static analyzers")
            raw_findings = self.finding_engine.analyze_repository(canonical_repo, manifest)
            ctx.transition_to(WorkflowState.ANALYZED, f"Identified {len(raw_findings)} candidate findings")

            # Stage 3: Defect Hypothesis Formulation
            logger.info("Stage 3: Generating defect hypotheses")
            hypotheses = self.hypothesis_gen.generate_hypotheses(raw_findings, manifest)
            ctx.transition_to(WorkflowState.HYPOTHESIZED, f"Formulated {len(hypotheses)} hypotheses")

            # Stage 4: Adversarial Test Generation (Red Team)
            logger.info("Stage 4: Generating targeted adversarial tests")
            tests: list[TestArtifact] = []
            hyp_by_id: dict[str, DefectHypothesis] = {h.id: h for h in hypotheses}
            for hyp in hypotheses:
                try:
                    generated = self.breaker.generate_tests(hyp, manifest)
                    tests.extend(generated)
                except Exception as e:
                    logger.warning("Test generation failed for hypothesis %s: %s", hyp.id, e)
            ctx.transition_to(WorkflowState.TESTS_GENERATED, f"Generated {len(tests)} test artifacts")

            # Stage 5: Sandbox Execution (Differential when base_ref provided)
            logger.info("Stage 5: Executing adversarial tests in sandbox")
            executions: list[ExecutionResult] = []
            base_executions: dict[str, ExecutionResult] = {}
            for test in tests:
                try:
                    res, base_res = self.diff_runner.run_differential_test(
                        target_repo=canonical_repo,
                        base_ref=base_ref,
                        test_artifact=test,
                        timeout_seconds=test.timeout_seconds,
                    )
                    executions.append(res)
                    if base_res:
                        base_executions[test.id] = base_res
                except Exception as e:
                    logger.warning("Sandbox execution failed for test %s: %s", test.id, e)
            ctx.transition_to(WorkflowState.SANDBOX_EXECUTED, f"Executed {len(executions)} tests in sandbox")

            # Stage 6: Independent Verification
            logger.info("Stage 6: Evaluating execution evidence")
            decisions: list[VerificationDecision] = []
            exec_by_test_id: dict[str, ExecutionResult] = {e.test_id: e for e in executions}
            test_by_hyp_id: dict[str, TestArtifact] = {t.hypothesis_id: t for t in tests}

            finding_status_map: dict[str, VerificationStatus] = {}
            finding_decision_map: dict[str, VerificationDecision] = {}

            for test in tests:
                target_hyp = hyp_by_id.get(test.hypothesis_id)
                exec_result = exec_by_test_id.get(test.id)
                if target_hyp is None or exec_result is None:
                    continue

                decision = self.verifier.verify(
                    hypothesis=target_hyp,
                    test_artifact=test,
                    execution_result=exec_result,
                    base_execution_result=base_executions.get(test.id),
                )
                decisions.append(decision)
                finding_status_map[decision.finding_id] = decision.status
                finding_decision_map[decision.finding_id] = decision

            ctx.transition_to(WorkflowState.VERIFIED, f"Verified {len(decisions)} findings")

            # Update candidate findings with full provenance and verified statuses
            hyp_by_finding_id: dict[str, DefectHypothesis] = {h.finding_id: h for h in hypotheses}
            updated_findings: list[CandidateFinding] = []
            for f in raw_findings:
                verified_status = finding_status_map.get(f.id, VerificationStatus.UNVERIFIED)
                matching_hyp = hyp_by_finding_id.get(f.id)
                matching_test = test_by_hyp_id.get(matching_hyp.id) if matching_hyp else None
                matching_exec = exec_by_test_id.get(matching_test.id) if matching_test else None
                matching_decision = finding_decision_map.get(f.id)

                updated_findings.append(
                    CandidateFinding(
                        id=f.id,
                        title=f.title,
                        description=f.description,
                        category=f.category,
                        severity=f.severity,
                        confidence=f.confidence,
                        location=f.location,
                        originating_tool=f.originating_tool,
                        rule_id=f.rule_id,
                        suggested_remediation=f.suggested_remediation,
                        verification_status=verified_status,
                        source_hash=f.source_hash,
                        base_commit=base_ref or (git_info.get("base_commit") if git_info else None),
                        target_commit=(git_info.get("commit_hash") if git_info else None) or manifest.git_commit,
                        hypothesis_id=matching_hyp.id if matching_hyp else None,
                        test_artifact_id=matching_test.id if matching_test else None,
                        evidence_id=matching_exec.id if matching_exec else None,
                        decision_id=matching_decision.id if matching_decision else None,
                    )
                )

            # Stage 7: Report Assembly
            summary_stats = {
                "total_findings": len(updated_findings),
                "confirmed": sum(1 for f in updated_findings if f.verification_status == VerificationStatus.CONFIRMED),
                "disproved": sum(1 for f in updated_findings if f.verification_status == VerificationStatus.DISPROVED),
                "inconclusive": sum(1 for f in updated_findings if f.verification_status == VerificationStatus.INCONCLUSIVE),
                "unverified": sum(1 for f in updated_findings if f.verification_status == VerificationStatus.UNVERIFIED),
            }

            report = ReviewReport(
                run_id=run_id,
                repo_path=str(canonical_repo),
                git_commit=manifest.git_commit,
                findings=updated_findings,
                hypotheses=hypotheses,
                tests=tests,
                executions=executions,
                decisions=decisions,
                summary=summary_stats,
            )

            ctx.transition_to(WorkflowState.COMPLETED, f"Review completed with {summary_stats['confirmed']} confirmed defects")

            # Persist run to SQLite store
            with contextlib.suppress(Exception):
                self.store.save_run(report)

            return report

        except Exception as e:
            logger.error("Review workflow failed: %s", e)
            with contextlib.suppress(Exception):
                ctx.transition_to(WorkflowState.FAILED, str(e))
            raise
