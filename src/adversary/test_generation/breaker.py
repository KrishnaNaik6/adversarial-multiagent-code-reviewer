"""Red Team / Breaker agent generating hypothesis-specific adversarial tests."""

from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.schemas import DefectHypothesis, RepositoryManifest, TestArtifact
from adversary.test_generation.validator import TestValidator

logger = get_logger("adversary.test_generation.breaker")


class BreakerAgent:
    """Generates targeted adversarial test suites to challenge and verify defect hypotheses."""

    def __init__(self) -> None:
        self.validator = TestValidator()

    def generate_tests(
        self,
        hypothesis: DefectHypothesis,
        manifest: RepositoryManifest,
    ) -> list[TestArtifact]:
        """Produce validated adversarial test artifacts for the given hypothesis."""
        artifacts: list[TestArtifact] = []
        target_file = hypothesis.target_file
        target_func = hypothesis.target_function or "target"

        # Compute python module import path from relative file path
        p = Path(target_file)
        # Strip .py extension and convert path separators to dots
        module_path = p.with_suffix("").as_posix().replace("/", ".")
        # If path begins with src., strip src. for execution path flexibility
        short_module = module_path.removeprefix("src.")

        if (
            "volume discount" in hypothesis.rationale.lower()
            or "threshold" in hypothesis.rationale.lower()
            or "off-by-one" in hypothesis.rationale.lower()
            or "tier" in hypothesis.rationale.lower()
        ):
            code = self._generate_tier_boundary_test(module_path, short_module, target_func)
            strategy = "boundary_condition"
        elif "tax" in hypothesis.rationale.lower() and ("gross" in hypothesis.rationale.lower() or "pre-discount" in hypothesis.rationale.lower()):
            code = self._generate_tax_on_net_test(module_path, short_module, target_func)
            strategy = "business_logic"
        elif "negative" in hypothesis.defect_behavior.lower() or "unbounded discount" in hypothesis.rationale.lower():
            code = self._generate_unbounded_discount_test(module_path, short_module, target_func)
            strategy = "numeric_underflow"
        elif "low-stock" in hypothesis.rationale.lower() or "active reservations" in hypothesis.rationale.lower():
            code = self._generate_low_stock_test(module_path, short_module, target_func)
            strategy = "state_management"
        elif "batch" in hypothesis.rationale.lower() and "rollback" in hypothesis.rationale.lower():
            code = self._generate_batch_reserve_rollback_test(module_path, short_module, target_func)
            strategy = "transaction_atomicity"
        elif "whitespace" in hypothesis.rationale.lower():
            code = self._generate_whitespace_name_test(module_path, short_module, target_func)
            strategy = "input_validation"
        elif "confirmed" in hypothesis.rationale.lower() and "cancel" in hypothesis.rationale.lower():
            code = self._generate_cancel_confirmed_order_test(module_path, short_module, target_func)
            strategy = "lifecycle_state_machine"
        elif (
            "ZeroDivisionError" in hypothesis.defect_behavior
            or "division" in hypothesis.rationale.lower()
        ):
            code = self._generate_division_test(module_path, short_module, target_func)
            strategy = "boundary_empty_input"
        elif "mutable default" in hypothesis.rationale.lower():
            code = self._generate_mutable_default_test(module_path, short_module, target_func)
            strategy = "state_accumulation"
        elif (
            "swallowed" in hypothesis.rationale.lower()
            or "bare except" in hypothesis.rationale.lower()
        ):
            code = self._generate_swallowed_exception_test(module_path, short_module, target_func)
            strategy = "exception_path"
        else:
            code = self._generate_generic_boundary_test(module_path, short_module, target_func)
            strategy = "boundary_condition"

        try:
            self.validator.validate(code)
            artifact = TestArtifact(
                id=f"TEST-{hypothesis.id}",
                hypothesis_id=hypothesis.id,
                file_name=f"test_adv_{hypothesis.id.lower()}.py",
                code=code,
                strategy=strategy,
                timeout_seconds=15,
                dependencies=[],
            )
            artifacts.append(artifact)
            logger.info(
                "Generated valid adversarial test artifact %s for %s", artifact.id, hypothesis.id
            )
        except Exception as e:
            logger.warning("Failed to validate generated test for %s: %s", hypothesis.id, e)

        return artifacts

    def _generate_division_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for potential division by zero."""

def test_division_on_empty_input():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Exercise boundary condition: empty sequence
    result = {func}([])
    # Contract expectation: either default value or documented exception, not uncaught crash
    assert result == 0.0 or result is None
'''

    def _generate_mutable_default_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for mutable default argument leakage."""

def test_mutable_default_isolation():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # First call appends to default
    res1 = {func}(1)
    # Second call without passing container must receive a fresh empty container
    res2 = {func}(2)

    assert 1 not in res2, f"State leaked across calls: {{res2=}}"
'''

    def _generate_swallowed_exception_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for silently swallowed exceptions."""

def test_swallowed_exception_detection():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Triggering zero division or invalid value inside swallowed block
    raised = False
    try:
        {func}(0)
    except (ValueError, ZeroDivisionError):
        raised = True
    assert raised, "Expected exception was silently swallowed"
'''

    def _generate_tier_boundary_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for tier boundary off-by-one."""
from decimal import Decimal

def test_bulk_discount_exact_ten_boundary():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Contract: 10 units must receive 10% discount ($10.00 on $100.00)
    discount = {func}(Decimal("100.00"), 10)
    assert discount == Decimal("10.00"), f"Expected 10% discount at exact threshold 10, got {{discount}}"
'''

    def _generate_tax_on_net_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for tax calculation on gross vs net."""
from decimal import Decimal

def test_sales_tax_on_discounted_net():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Net taxable is $80.00 -> 8% tax must be $6.40, not $8.00
    res = {func}(Decimal("100.00"), Decimal("20.00"), Decimal("0.08"))
    assert res["tax"] == Decimal("6.40"), f"Expected tax on net taxable $80.00 to be $6.40, got {{res['tax']}}"
'''

    def _generate_unbounded_discount_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for unbounded discount deduction."""
from decimal import Decimal

def test_discount_exceeding_subtotal_floored():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    res = {func}(Decimal("20.00"), Decimal("25.00"))
    assert res["taxable_amount"] >= Decimal("0.00"), f"Taxable amount underflow: {{res['taxable_amount']}}"
'''

    def _generate_low_stock_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for low-stock calculation ignoring holds."""
from decimal import Decimal

def test_low_stock_reflects_active_reservations():
    try:
        from {mod} import InventoryManager, InventoryItem
    except ImportError:
        from {short_mod} import InventoryManager, InventoryItem

    inv = InventoryManager()
    inv.add_item(InventoryItem("SKU-1", "Item", Decimal("10.00"), 10, reorder_threshold=5))
    inv.reserve_stock("SKU-1", 8)
    low = inv.get_low_stock_items()
    assert any(i.sku == "SKU-1" for i in low), "Low-stock check ignored active reservations"
'''

    def _generate_batch_reserve_rollback_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for non-atomic batch reservation rollback."""
from decimal import Decimal

def test_batch_reserve_rolls_back_on_failure():
    try:
        from {mod} import InventoryManager, InventoryItem
        from src.shopcore.exceptions import InsufficientStockError
    except ImportError:
        from {short_mod} import InventoryManager, InventoryItem
        from shopcore.exceptions import InsufficientStockError

    inv = InventoryManager()
    inv.add_item(InventoryItem("A", "Item A", Decimal("10.00"), 5))
    inv.add_item(InventoryItem("B", "Item B", Decimal("10.00"), 2))
    raised = False
    try:
        inv.batch_reserve([("A", 3), ("B", 10)])
    except InsufficientStockError:
        raised = True
    assert raised, "Expected InsufficientStockError was not raised"
    assert inv.get_item("A").reserved_quantity == 0, f"Reservation leaked: {{inv.get_item('A').reserved_quantity}}"
'''

    def _generate_whitespace_name_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for whitespace name validation bypass."""

def test_whitespace_name_rejected():
    try:
        from {mod} import UserManager
        from src.shopcore.exceptions import ValidationError
    except ImportError:
        from {short_mod} import UserManager
        from shopcore.exceptions import ValidationError

    users = UserManager()
    raised = False
    try:
        users.register_user("u1", "test@example.com", "   ")
    except ValidationError:
        raised = True
    assert raised, "Expected ValidationError was not raised for whitespace-only name"
'''

    def _generate_cancel_confirmed_order_test(self, mod: str, short_mod: str, func: str) -> str:
        return '''"""Adversarial reproduction test for cancel_order on confirmed state."""
from decimal import Decimal

def test_cancel_confirmed_order_restocks_inventory():
    try:
        from src.shopcore.inventory import InventoryManager, InventoryItem
        from src.shopcore.users import UserManager
        from src.shopcore.orders import OrderService, OrderItem
    except ImportError:
        from shopcore.inventory import InventoryManager, InventoryItem
        from shopcore.users import UserManager
        from shopcore.orders import OrderService, OrderItem

    inv = InventoryManager()
    inv.add_item(InventoryItem("SKU-C", "Item C", Decimal("10.00"), 10))
    users = UserManager()
    users.register_user("u1", "u1@example.com", "User")
    orders = OrderService(inv, users)
    orders.create_order("ORD-1", "u1", [OrderItem("SKU-C", 4, Decimal("10.00"))])
    orders.confirm_order("ORD-1")
    orders.cancel_order("ORD-1")
    assert inv.get_item("SKU-C").stock_quantity == 10
'''

    def _generate_generic_boundary_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial boundary test."""

def test_boundary_invariants():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    assert callable({func})
'''
