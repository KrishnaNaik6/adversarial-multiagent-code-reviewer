# Adversarial Multi-Agent Code Reviewer with Automated Test Proofs

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Security: Docker-isolated](https://img.shields.io/badge/security-docker--isolated-green.svg)](SECURITY.md)

An evidence-gated, reliability-first code review system that moves beyond plausible AI commentary. It analyzes repositories, detects suspicious patterns, formulates explicit bug hypotheses, generates adversarial tests, executes them in isolated Docker sandboxes, and verifies whether reproducible execution evidence proves the defect before claiming a bug exists.

---

## Key Features

- **Evidence-Gated Defect Verification:** A finding is never confirmed without attributable, reproducible test execution evidence.
- **Deterministic-First Core:** Runs completely offline without cloud API keys using deterministic AST analysis and static analyzers.
- **Docker Isolation:** Executes untrusted tests in non-root, restricted containers with `--network none` and strict resource boundaries.
- **Multi-Agent Specialist Roles:**
  - *Repository Intelligence:* AST inspection, call graphs, symbol tables, and revision fingerprinting.
  - *Static Analysis:* Deterministic rule enforcement and diagnostic normalization.
  - *Red Team / Breaker:* Targeted adversarial test generator (boundary, property-based, exception path).
  - *Independent Verifier:* Objective evidence attribution and outcome classifier (`CONFIRMED`, `DISPROVED`, `INCONCLUSIVE`).
  - *Blue Team / Patcher:* Minimal repairs tested in isolated working copies with regression gates and human authorization.
- **Auditable Persistence & Reporting:** Versioned SQLite storage and rich Markdown/JSON reports with complete hypothesis-to-traceback provenance.

---

## Documentation

- [`PROJECT_KNOWLEDGE.md`](PROJECT_KNOWLEDGE.md) — Comprehensive product and engineering specifications.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Detailed architecture, agent contracts, and workflows.
- [`SECURITY.md`](SECURITY.md) — Threat model, isolation policies, and prompt injection defenses.
- [`DECISIONS.md`](DECISIONS.md) — Formal Architecture Decision Records (ADRs).
- [`ROADMAP.md`](ROADMAP.md) — Complete 12-phase implementation lifecycle.
- [`docs/implementation/PROJECT_STATUS.md`](docs/implementation/PROJECT_STATUS.md) — Authoritative implementation log.

---

## Quickstart

### Prerequisites
- Python 3.12+
- Git 2.40+
- Docker Engine (with Linux container support)

### Installation
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows (or source .venv/bin/activate on Linux/macOS)
pip install -e ".[dev]"
```

### CLI Usage
```bash
# Review a repository
adversary review ./my-project

# View verified findings
adversary findings

# Inspect finding evidence and stack trace proof
adversary explain FIND-001
```

---

## License
Apache-2.0
