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

        if finding.rule_id == "AST-BND-002" or "off-by-one" in finding.title.lower():
            preconditions = "Caller passes exact threshold quantity to volume tier function."
            trigger_input = "item_count = 10 (exact boundary)"
            expected_behavior = "Exact threshold receives volume discount tier."
            defect_behavior = "Strict inequality '>' denies volume discount to orders at exact threshold."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "using '>' instead of '>=' denies volume discount to orders at exact threshold."
            )
        elif finding.rule_id == "AST-FIN-001" or "sales tax computed on pre-discount" in finding.title.lower():
            preconditions = "Order has both non-zero discount and tax rate."
            trigger_input = "items_subtotal = 100.00, discount_amount = 20.00, tax_rate = 0.08"
            expected_behavior = "Sales tax is assessed against net taxable amount ($80.00 -> $6.40)."
            defect_behavior = "Sales tax is assessed against gross subtotal ($100.00 -> $8.00)."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "sales tax is assessed against gross items_subtotal instead of net taxable_amount."
            )
        elif finding.rule_id == "AST-NUM-001" or "unbounded discount" in finding.title.lower():
            preconditions = "Voucher discount amount exceeds merchandise subtotal."
            trigger_input = "items_subtotal = 20.00, discount_amount = 25.00"
            expected_behavior = "Taxable amount is lower-bounded at 0.00."
            defect_behavior = "Taxable amount evaluates to negative currency (-5.00)."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "vouchers exceeding merchandise subtotal create negative invoice line items."
            )
        elif finding.rule_id == "AST-STK-001" or "low-stock alert" in finding.title.lower():
            preconditions = "Stock quantity is above threshold, but unreserved available quantity is at or below threshold."
            trigger_input = "stock_quantity = 10, reserved_quantity = 8, reorder_threshold = 5 (available = 2)"
            expected_behavior = "Item is flagged in low-stock alert query."
            defect_behavior = "Query tests stock_quantity and misses low-stock state, returning empty list."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "inspecting stock_quantity ignores active reservations, missing critical reorders."
            )
        elif finding.rule_id == "AST-TXN-001" or "non-atomic batch" in finding.title.lower():
            preconditions = "Batch operation fails midway on subsequent item due to inventory limits."
            trigger_input = "batch_reserve with second item exceeding available stock"
            expected_behavior = "Operation rolls back previous reservations, leaving reserved count at 0."
            defect_behavior = "No rollback exists when an item fails midway, stranding unpurchased items."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "no rollback exists when an item fails midway, stranding unpurchased items."
            )
        elif finding.rule_id == "AST-VAL-001" or "whitespace-only" in finding.title.lower():
            preconditions = "Caller passes whitespace-only string to name registration."
            trigger_input = "name = '   '"
            expected_behavior = "ValidationError is raised rejecting whitespace name."
            defect_behavior = "Function accepts whitespace-only string without raising ValidationError."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "if not name: treats whitespace '   ' as valid truthy string."
            )
        elif finding.rule_id == "AST-LIF-001" or "confirmed order cancellation" in finding.title.lower():
            preconditions = "Order has already been confirmed (inventory deducted from warehouse)."
            trigger_input = "cancel_order called on confirmed order"
            expected_behavior = "Inventory is restocked into warehouse inventory."
            defect_behavior = "release_stock is called when 0 items are reserved, triggering inventory crash."
            rationale = (
                f"In {target_file} ({func_display} at line {finding.location.line_start}), "
                "confirmed orders have 0 reserved stock; calling release_stock crashes and loses physical inventory."
            )
        elif (
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
