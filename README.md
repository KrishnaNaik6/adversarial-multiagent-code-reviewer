# Adversarial Multi-Agent Code Reviewer with Automated Test Proofs

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: Docker-isolated](https://img.shields.io/badge/security-docker--isolated-green.svg)](SECURITY.md)
[![Release: v0.1.0](https://img.shields.io/badge/release-v0.1.0-brightgreen.svg)](CHANGELOG.md)

An evidence-gated, reliability-first code review system that moves beyond plausible AI commentary. It analyzes software repositories, detects suspicious code patterns, formulates explicit defect hypotheses, generates targeted adversarial tests, executes them in isolated Docker sandboxes, and verifies whether reproducible execution evidence proves the defect before claiming a bug exists.

---

## Core System Architecture

```text
Repository Input
      │
      ▼
Repository Intelligence (AST & Symbol Extraction, Safe Scanner)
      │
      ▼
Deterministic Static Analysis (AST Rule Engine & Ruff Adapter)
      │
      ▼
Candidate Findings Normalization & Deduplication
      │
      ▼
Defect Hypothesis Engine (Preconditions, Trigger, Expected vs Defect)
      │
      ▼
Red Team / Breaker Agent (Targeted Adversarial Test Generation & AST Safety Validation)
      │
      ▼
Docker Sandbox Execution (Non-Root, --network none, Resource Limits, Ephemeral Mounts)
      │
      ▼
Evidence Collection & Traceback Parsing (Exit Codes, Duration, Error Trace)
      │
      ▼
Independent Verification Engine (Attribution Analysis & Outcome Classification)
      │
      ├───────────────────────┬────────────────────────┐
      ▼                       ▼                        ▼
[CONFIRMED]             [DISPROVED]              [INCONCLUSIVE]
      │
      ▼ (Optional / User-Authorized)
Blue Team / Patcher (Isolated Working Copy, Adversarial Proof & Regression Validation)
      │
      ▼
Human Approval Gate (Diff Preview & Explicit Approval Barrier)
      │
      ▼
Persistence & Reporting (Versioned SQLite Storage & Markdown / JSON Reports)
```

---

## Logical Agents & Core Modules

1. **Repository Intelligence (`adversary.repository` & `adversary.analysis.ast`)**:
   - Safe filesystem discovery with symlink and directory traversal guards.
   - Comprehensive Python AST symbol extractor (classes, methods, functions, docstrings, parameters, return types, call graphs).
   - Git commit SHA and content SHA-256 fingerprinting for evidence staleness detection.

2. **Static Analysis & Findings Engine (`adversary.analysis`)**:
   - `DeterministicASTAnalyzer`: AST pattern detection for division by zero (`AST-DIV-001`, `AST-DIV-002`), mutable default arguments (`AST-MUT-001`), insecure shell execution (`AST-SEC-001`), and swallowed exceptions (`AST-EXC-001`). Includes guard tracking to eliminate false positives on guarded code.
   - `RuffAnalyzer`: Adapter executing Ruff with JSON output parsing.
   - `FindingEngine`: Aggregates and deduplicates diagnostics sharing location coordinates.

3. **Hypothesis Formulation (`adversary.hypotheses`)**:
   - Translates suspicious patterns into testable `DefectHypothesis` objects specifying preconditions, trigger input, expected behavior, and defect behavior.

4. **Red Team / Breaker Agent (`adversary.test_generation`)**:
   - Produces targeted test suites aimed at proving the hypothesis (boundary conditions, empty sequence inputs, state accumulation, exception paths).
   - `TestValidator`: AST validator blocking syntax errors and dangerous imports (`socket`, `subprocess`, `urllib`, `shutil`).

5. **Docker Sandbox Execution (`adversary.sandbox`)**:
   - Manages restricted test execution with `--network none` (no network access), memory quotas (`1g`), PIDs limits (100), and execution timeouts.
   - Host target repository mounted strictly read-only (`:ro`).
   - Ephemeral standalone test harness (`harness.py`) enabling 100% offline test execution without third-party dependencies inside any Python 3.12 container.

6. **Evidence Collection (`adversary.evidence`)**:
   - Parses exit codes, duration, stdout, stderr, exception names, and stack traces into structured `ExecutionResult` records.

7. **Independent Verification Agent (`adversary.verification`)**:
   - Attribution analysis verifying that failures originated in the target code and not due to harness issues or missing packages (`ModuleNotFoundError`).
   - Classifies outcomes strictly: `CONFIRMED`, `DISPROVED`, `INCONCLUSIVE`, or `EXECUTION_ERROR`.

8. **Blue Team / Patcher Agent (`adversary.patching`)**:
   - Generates minimal localized fixes in isolated temporary scratch directories.
   - Automated proof validation: requires the adversarial reproduction test to turn from `FAILED` to `PASSED` and all regression tests to `PASS`.
   - `PatchApplier`: Strict human approval barrier preventing any modification to the original repository without explicit approval (`--apply`).

9. **Persistence & Reporting (`adversary.persistence` & `adversary.reporting`)**:
   - Relational SQLite database with versioned schema (`review_runs`, `findings`, `hypotheses`, `test_artifacts`, `execution_results`, `verification_decisions`).
   - Rich Markdown and JSON report generators with complete traceback provenance.

---

## Installation

### Prerequisites
- Python 3.12+
- Git 2.40+
- Docker Engine (with Linux containers)

### Quickstart
```bash
# Clone the repository
git clone https://github.com/example/adversarial-multiagent-code-reviewer.git
cd adversarial-multiagent-code-reviewer

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate  # Windows (or source .venv/bin/activate on Linux/macOS)

# Install adversary with development dependencies
pip install -e ".[dev]"
```

---

## CLI Usage Guide

```bash
# 1. Initialize workspace directories and configuration
adversary init

# 2. Review a target repository
adversary review ./my-python-project

# 3. View findings table from the review
adversary findings

# 4. Deep-dive into finding evidence and container execution traceback
adversary explain FIND-001

# 5. Propose a minimal patch verified in an isolated workspace
adversary fix FIND-001

# 6. Apply verified patch to repository (explicit human gate)
adversary fix FIND-001 --apply

# 7. Generate audit reports
adversary report --format markdown --output review_report.md
adversary report --format json --output review_report.json
```

---

## Testing & Quality Assurance

Run the complete test suite:
```bash
# Run 60 unit, security, integration, and e2e tests
pytest

# Code style and linting
ruff check .

# Static type checking
mypy src tests
```

---

## Security Policy

See [`SECURITY.md`](SECURITY.md) for detailed threat modeling, container isolation policies, and verification audit results.

## License
Apache-2.0
