# Architecture and Technology Decisions (DECISIONS.md)

This document records the architectural and technology decisions established for the **Adversarial Multi-Agent Code Reviewer with Automated Test Proofs**.

---

## ADR-001: Deterministic-First Hybrid AI Architecture
- **Context:** Large language models can hallucinate plausible defects, invent non-existent APIs, or claim tests pass when they fail.
- **Decision:** The system operates on a deterministic-first baseline. Static analysis, AST parsing, test execution, and evidence evaluation are deterministic. AI assistance is optional and used for heuristic reasoning, edge-case hypothesis generation, and patch suggestions.
- **Consequence:** Full offline operation without API keys is guaranteed. Findings cannot be marked confirmed unless backed by verifiable execution evidence.

## ADR-002: Modular Monolith
- **Context:** Premature microservices or distributed task runners introduce operational complexity, network latency, and deployment overhead.
- **Decision:** Use a single Python codebase structured into explicit modular packages with typed domain boundaries (`adversary.*`).
- **Consequence:** Easy installation, direct debugging, single CLI binary/entry point, with clear boundaries preserving future service extraction if necessary.

## ADR-003: Isolated Docker Sandbox for Untrusted Code Execution
- **Context:** Reviewed repositories and generated adversarial tests are untrusted and potentially malicious.
- **Decision:** All execution of repository code and generated tests occurs inside restricted Docker containers with:
  - Network disabled (`--network none`) by default.
  - Read-only source code mount.
  - Non-root container execution.
  - Strict memory, CPU, PID limits, and wall-clock execution timeouts.
  - No Docker socket or host user credential mounts.
- **Consequence:** Prevents host contamination, unauthorized outbound network requests, and accidental host modifications.

## ADR-004: Evidence-Gated Finding Classification
- **Context:** Traditional reviewers confuse static warnings with real bugs.
- **Decision:** Findings must progress through a closed-loop hypothesis-test-evidence cycle:
  - `Candidate` -> `Hypothesis` -> `Adversarial Test` -> `Sandbox Execution` -> `Independent Verification` -> `Outcome`.
  - Allowed terminal/verified outcomes: `Confirmed`, `Disproved`, `Inconclusive`, `Unverified`, `Execution Error`.
  - Severity (impact) is strictly separated from Confidence (evidence strength).
- **Consequence:** False positives are minimized, and every confirmed finding is accompanied by a reproducible test proof.

## ADR-005: Technology Stack Selections
- **Python:** 3.12+ (leveraging modern typing, exception groups, performance improvements).
- **CLI:** Typer & Rich for ergonomic terminal interface and human-friendly outputs.
- **Domain Modeling & Settings:** Pydantic v2 & Pydantic Settings for schema validation and immutability.
- **Static Analysis & Ingestion:** Python standard `ast` module, Ruff CLI/API.
- **Adversarial Testing:** pytest, Hypothesis.
- **Persistence:** SQLite with versioned schema for run history, findings, and evidence traceability.
- **Reporting:** Structured JSON (machine-readable) and GitHub-flavored Markdown (developer-readable).

