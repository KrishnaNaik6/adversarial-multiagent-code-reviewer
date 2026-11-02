# Changelog

All notable changes to the **Adversarial Multi-Agent Code Reviewer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-03

### Added
- **Phase 11 (Complete System Integration and Release)**:
  - End-to-end integration lifecycle test suite (`tests/e2e/test_full_workflow.py`) validating the full review -> hypothesize -> test -> sandbox verify -> patch -> regression test -> approval gate -> apply -> re-review loop.
  - Complete CLI commands verified: `init`, `review`, `findings`, `explain`, `verify`, `fix`, `report`, and `version`.
  - Comprehensive documentation: `ARCHITECTURE.md`, `DECISIONS.md`, `SECURITY.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, and complete `README.md` with architectural diagrams and quickstart guide.
- **Phase 10 (Security, Reliability, and Production Hardening)**:
  - Security audit and automated attack suites: path traversal attacks, Docker sandbox timeouts, memory limits, network denial, secret and token redaction, and malicious test module blocking.
  - Failure injection and chaos testing across analyzer exceptions, runner crashes, and timeout recoveries.
- **Phase 9 (Repair and Regression Verification)**:
  - Blue Team patcher in isolated temporary workspaces.
  - Unified diff generation and automated dual verification (adversarial test turns to PASS + regression test suite remains PASS).
  - Human approval barrier for applying verified patches to the working repository tree (`adversary fix <id> --apply`).
- **Phase 8 (Persistence and Reporting)**:
  - SQLite database persistence engine with versioned schema storing runs, findings, hypotheses, generated tests, and verification decisions.
  - Export capabilities in GitHub-flavored Markdown (`report --format markdown`) and machine-readable JSON (`report --format json`).
  - Interactive CLI inspection commands: `findings`, `explain <id>`, and `report`.
- **Phase 7 (Multi-Agent Orchestration)**:
  - Central `ReviewOrchestrator` managing the full 6-stage closed-loop pipeline with bounded state transitions.
  - Standalone container test harness (`harness.py`) for zero-dependency container test execution.
  - Rich CLI formatting with live progress, defect tables, and verification summary cards.
- **Phase 6 (Independent Verification Engine)**:
  - Independent verification agent attributing runtime evidence directly to suspect target code locations.
  - Strict outcome classification (`CONFIRMED`, `DISPROVED`, `INCONCLUSIVE`, `EXECUTION_ERROR`) eliminating hallucinated bug reports.
- **Phase 5 (Docker Sandbox and Evidence Collection)**:
  - Docker container runner executing tests with `--network none`, non-root execution, 512MB RAM cap, and 15s timeout.
  - Standardized evidence collector parsing exit codes, execution times, tracebacks, and exceptions.
- **Phase 4 (Adversarial Test Generation)**:
  - Red Team Breaker agent generating targeted adversarial reproduction tests.
  - AST security validator ensuring tests contain no dangerous calls (`os.system`, `subprocess`, file writes, network requests).
- **Phase 3 (Deterministic Analysis and Finding Engine)**:
  - Deterministic AST vulnerability rules with guard detection (division-by-zero, mutable defaults, insecure system calls, swallowed exceptions).
  - Ruff analyzer adapter and finding deduplication engine.
  - Formal defect hypothesis generator (`DefectHypothesis`).
- **Phase 2 (Repository Intelligence)**:
  - Safe repository file scanner with path traversal and symlink guards.
  - AST symbol extractor indexing modules, functions, classes, imports, and docstrings.
  - SHA-256 fingerprinting for change detection and evidence freshness.
- **Phase 1 (Foundation and Core Contracts)**:
  - Pydantic v2 schemas and enums, typed domain models, and error taxonomy.
  - Structured logging with automatic secret and API key redaction.
  - Typer CLI framework with Rich formatting.
- **Phase 0 (Environment Baseline)**:
  - Development environment verification (Python 3.12+, Docker, Git).
  - System architecture specification and baseline engineering documentation.

