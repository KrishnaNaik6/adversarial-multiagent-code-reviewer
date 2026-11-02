# Changelog

All notable changes to the **Adversarial Multi-Agent Code Reviewer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 10: Security, Reliability, and Production Hardening (path traversal guards, container timeout tests, secret redactor audit, malicious test validation suite, and chaos failure injection).
- Phase 9: Repair and Regression Verification (Blue Team patcher in isolated workspace, automated proof and regression validation, human approval gate, and CLI `fix` command).
- Phase 8: Persistence and Reporting (SQLite relational store, versioned schema, Markdown/JSON report generators, CLI findings/explain/report integration).
- Phase 7: Multi-Agent Orchestration (workflow state coordinator, central review pipeline, Typer CLI live review, standalone container test harness).
- Phase 6: Independent Verification Engine (evidence attribution engine, target path checks, strict outcome classification, and false-failure rejection).
- Phase 5: Docker Sandbox and Evidence Collection (isolated container runner, `--network none` restriction, resource bounds, pytest evidence parser, traceback extractor, and read-only host protection).
- Phase 4: Adversarial Test Generation (Red Team Breaker agent, AST-based test syntax and safety validator, hypothesis-linked adversarial test templates).
- Phase 3: Deterministic Analysis and Finding Engine (AST defect rules with false-positive guard tracking, Ruff analyzer adapter, finding deduplication engine, formal defect hypothesis generator, and test fixtures).
- Phase 2: Repository Intelligence (safe filesystem discovery, path traversal/symlink guards, Python AST symbol analysis, git revision capture, line counting, and content hashing).
- Phase 1: Foundation and Core Contracts (domain models, configuration, error taxonomy, secret redactor, protocols, Typer CLI, and unit test suite).
- Phase 0: Initialized project baseline, environment verification, security policy, architectural specifications, and implementation roadmap.

