"""Formal defect hypothesis generator."""

from adversary.core.logging import get_logger
from adversary.models.enums import FindingCategory
from adversary.models.schemas import CandidateFinding, DefectHypothesis, RepositoryManifest

logger = get_logger("adversary.hypotheses.generator")


class HypothesisGenerator:
    """Translates candidate findings and AST context into formal, testable defect hypotheses."""

    def generate_hypotheses(
        self,
        findings: list[CandidateFinding],
        manifest: RepositoryManifest,
    ) -> list[DefectHypothesis]:
        hypotheses: list[DefectHypothesis] = []

        for i, finding in enumerate(findings, 1):
            target_file = finding.location.file_path
            module_info = manifest.modules.get(target_file)

            # Locate the function containing the finding line range
            target_func: str | None = None
            if module_info:
                for func in module_info.functions:
                    if func.line_start <= finding.location.line_start <= func.line_end:
                        target_func = func.name
                        break
                if not target_func:
                    for cls in module_info.classes:
                        for method in cls.methods:
                            if method.line_start <= finding.location.line_start <= method.line_end:
                                target_func = f"{cls.name}.{method.name}"
                                break

            hyp = self._build_hypothesis(f"HYP-{i:03d}", finding, target_file, target_func)
            hypotheses.append(hyp)

        return hypotheses

    def _build_hypothesis(
        self,
        hyp_id: str,
        finding: CandidateFinding,
        target_file: str,
        target_func: str | None,
    ) -> DefectHypothesis:
        func_display = target_func or "module level"

        if (
            finding.category == FindingCategory.BOUNDARY_CONDITION
            or "division by zero" in finding.title.lower()
        ):
            preconditions = (
                "Caller passes an empty sequence or zero denominator to division operation."
            )
            trigger_input = "[] (empty list) or len(collection) == 0"
            expected_behavior = (
                "Function returns default (e.g. 0.0) or raises documented ValueError."
            )
            defect_behavior = "Uncaught ZeroDivisionError crashes execution."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "division is executed without checking if denominator evaluates to 0."
            )
        elif finding.category == FindingCategory.SECURITY:
            preconditions = "Attacker controls string input passed to execution sink."
            trigger_input = "'; cat /etc/passwd' or malicious command injection payload"
            expected_behavior = (
                "Input is treated strictly as data or safely escaped without shell evaluation."
            )
            defect_behavior = "Subshell interprets malicious shell commands."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "command execution sink evaluates raw input in subshell."
            )
        elif "mutable default" in finding.title.lower():
            preconditions = (
                "Function is called multiple times without providing the optional argument."
            )
            trigger_input = "Consecutive invocations relying on default argument"
            expected_behavior = (
                "Each call receives an independent, freshly allocated empty collection."
            )
            defect_behavior = "Mutations accumulate into the shared default across invocations."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "Python evaluates default argument expressions once at function definition time."
            )
        elif finding.category == FindingCategory.EXCEPTION_HANDLING:
            preconditions = "An unexpected exception or error occurs inside protected try block."
            trigger_input = "Any exception raised during execution of try block"
            expected_behavior = "Exception is logged, handled, or re-raised to alert callers."
            defect_behavior = "Exception is silently suppressed by pass statement."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "bare except handler masks errors."
            )
        else:
            preconditions = "Specific input triggers suspicious code path."
            trigger_input = "Adversarial boundary value or edge case"
            expected_behavior = "Graceful handling according to component contract."
            defect_behavior = f"Observed violation: {finding.title}"
            rationale = (
                f"Static analysis identified rule violation: {finding.rule_id} in {target_file}."
            )

        return DefectHypothesis(
            id=hyp_id,
            finding_id=finding.id,
            target_file=target_file,
            target_function=target_func,
            preconditions=preconditions,
            trigger_input=trigger_input,
            expected_behavior=expected_behavior,
            defect_behavior=defect_behavior,
            rationale=rationale,
        )
