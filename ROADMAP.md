# Implementation Roadmap (ROADMAP.md)

## Master Phase Breakdown

- [x] **Phase 0 — Environment and Project Baseline**
  - Tool verification (Python 3.12+, Git, Docker, Docker Compose, WSL2).
  - Safety baseline, `.gitignore`, and foundational documentation (`ARCHITECTURE.md`, `DECISIONS.md`, `SECURITY.md`, `ROADMAP.md`, `CHANGELOG.md`, `ENVIRONMENT_REPORT.md`, `PROJECT_STATUS.md`).

- [x] **Phase 1 — Foundation and Core Contracts**
  - `pyproject.toml` with pinned dependencies (Typer, Rich, Pydantic, Pydantic Settings, pytest, Ruff, mypy).
  - Package structure: `adversary.core`, `adversary.config`, `adversary.models`.
  - Error taxonomy, structured logging with secret redaction, typed domain models.
  - Typer CLI entry point skeleton (`adversary --help`).
  - Unit tests for models, config, and CLI.

- [x] **Phase 2 — Repository Intelligence**
  - File scanner with path traversal/symlink guards.
  - Python AST analysis: extract modules, classes, functions, imports, docstrings, calls, tests.
  - SHA-256 source fingerprinting for evidence staleness checks.
  - Manifest generation and test fixtures.

- [x] **Phase 3 — Deterministic Analysis and Finding Engine**
  - Ruff analyzer integration.
  - Deterministic AST vulnerability and anti-pattern detectors (e.g. division by zero, unhandled None, resource leak, mutable default argument, command injection).
  - Finding normalization, deduplication, and `DefectHypothesis` model generation.
  - Known positive/negative test fixtures.

- [x] **Phase 4 — Adversarial Test Generation**
  - Red Team / Breaker agent implementation.
  - Boundary value, empty input, exception path, and property-based test generation.
  - Generated test syntax validator and safety scanner.
  - Hypothesis-to-test traceability preservation.

- [x] **Phase 5 — Docker Sandbox and Evidence Collection**
  - Docker sandbox runner (`adversary.sandbox`) with resource limits (RAM, CPU, PID, timeout) and `--network none`.
  - Robust execution manager with graceful fallback when Docker is unavailable or for local mocking.
  - Result parsing: exit code, stdout/stderr, exception traceback extraction, execution metrics.

- [x] **Phase 6 — Independent Verification Engine**
  - Verification agent (`adversary.verification`).
  - Evidence attribution: verify exception originates in target code under test.
  - Classify outcome: `CONFIRMED`, `DISPROVED`, `INCONCLUSIVE`, `UNVERIFIED`, `EXECUTION_ERROR`.
  - Prevent unverified findings from claiming confirmation.

- [x] **Phase 7 — Multi-Agent Orchestration**
  - State machine coordinator (`adversary.orchestration`).
  - State transitions: `INIT` -> `INDEXED` -> `ANALYZED` -> `HYPOTHESIZED` -> `TESTED` -> `VERIFIED` -> `COMPLETED`.
  - Concurrency management, timeout budgets, partial failure recovery.

- [x] **Phase 8 — Persistence and Reporting**
  - SQLite storage schema (`adversary.persistence`).
  - Store review runs, candidate findings, hypotheses, generated tests, raw evidence, and verification decisions.
  - JSON and GitHub-flavored Markdown report generators.

- [x] **Phase 9 — Repair and Regression Verification**
  - Blue Team / Patcher agent (`adversary.patching`).
  - Minimal diff generation in isolated temporary workspace.
  - Re-run adversarial proof tests (must turn to PASS) and existing test suite (must PASS).
  - Human approval barrier for working tree modification.

- [x] **Phase 10 — Security, Reliability, and Production Hardening**
  - Comprehensive security audit: prompt injection resistance, path traversal attacks, denial of service / infinite loop tests, secret masking.
  - Failure injection and chaos testing.

- [x] **Phase 11 — Complete System Integration and Release**
  - End-to-end integration tests on sample repositories with seeded defects.
  - Full CLI command verification (`init`, `review`, `findings`, `explain`, `verify`, `fix`, `report`).
  - Release documentation, packaging verification, and final sign-off.

