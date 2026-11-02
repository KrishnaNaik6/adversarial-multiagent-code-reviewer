"""SQLite database connection and versioned schema management."""

import sqlite3
from pathlib import Path

from adversary.core.logging import get_logger

logger = get_logger("adversary.persistence.database")

SCHEMA_VERSION = 1

INIT_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_runs (
    run_id TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    git_commit TEXT,
    created_at TIMESTAMP NOT NULL,
    summary_json TEXT NOT NULL,
    report_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    source_hash TEXT,
    PRIMARY KEY (id, run_id),
    FOREIGN KEY (run_id) REFERENCES review_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    target_file TEXT NOT NULL,
    target_function TEXT,
    preconditions TEXT,
    trigger_input TEXT,
    expected_behavior TEXT,
    defect_behavior TEXT,
    rationale TEXT,
    PRIMARY KEY (id, run_id),
    FOREIGN KEY (run_id) REFERENCES review_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_artifacts (
    id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    hypothesis_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    code TEXT NOT NULL,
    strategy TEXT NOT NULL,
    PRIMARY KEY (id, run_id),
    FOREIGN KEY (run_id) REFERENCES review_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS execution_results (
    id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    stdout TEXT,
    stderr TEXT,
    exception_name TEXT,
    traceback_summary TEXT,
    duration_ms REAL,
    PRIMARY KEY (id, run_id),
    FOREIGN KEY (run_id) REFERENCES review_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verification_decisions (
    id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    hypothesis_id TEXT NOT NULL,
    status TEXT NOT NULL,
    is_attributed_to_target BOOLEAN NOT NULL,
    explanation TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    decided_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id, run_id),
    FOREIGN KEY (run_id) REFERENCES review_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_run_id ON hypotheses(run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_run_id ON verification_decisions(run_id);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with versioned tables and indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    with conn:
        conn.executescript(INIT_SQL)
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,))
        if not cur.fetchone():
            cur.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

    return conn
