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

        if "ZeroDivisionError" in hypothesis.defect_behavior or "division" in hypothesis.rationale.lower():
            code = self._generate_division_test(module_path, short_module, target_func)
            strategy = "boundary_empty_input"
        elif "mutable default" in hypothesis.rationale.lower():
            code = self._generate_mutable_default_test(module_path, short_module, target_func)
            strategy = "state_accumulation"
        elif "swallowed" in hypothesis.rationale.lower() or "bare except" in hypothesis.rationale.lower():
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
                dependencies=["pytest"],
            )
            artifacts.append(artifact)
            logger.info("Generated valid adversarial test artifact %s for %s", artifact.id, hypothesis.id)
        except Exception as e:
            logger.warning("Failed to validate generated test for %s: %s", hypothesis.id, e)

        return artifacts

    def _generate_division_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for potential division by zero."""
import pytest

def test_division_on_empty_input():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Exercise boundary condition: empty sequence
    result = {func}([])
    # Contract expect: either default value or documented exception, not uncaught crash
    assert result == 0.0 or result is None
'''

    def _generate_mutable_default_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial reproduction test for mutable default argument leakage."""
import pytest

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
import pytest

def test_swallowed_exception_detection():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    # Triggering zero division or invalid value inside swallowed block
    # Should either succeed or raise an informative exception, not return silently
    with pytest.raises((ValueError, ZeroDivisionError)):
        {func}(0)
'''

    def _generate_generic_boundary_test(self, mod: str, short_mod: str, func: str) -> str:
        return f'''"""Adversarial boundary test."""
import pytest

def test_boundary_invariants():
    try:
        from {mod} import {func}
    except ImportError:
        from {short_mod} import {func}

    assert callable({func})
'''
