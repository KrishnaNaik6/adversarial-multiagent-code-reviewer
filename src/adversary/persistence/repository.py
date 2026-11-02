"""Repository implementation for persisting and querying review data in SQLite."""

import json
from pathlib import Path
from typing import Any

from adversary.core.logging import get_logger
from adversary.models.schemas import ReviewReport
from adversary.persistence.database import init_db

logger = get_logger("adversary.persistence.repository")


class RunStore:
    """Store and query review runs, findings, hypotheses, and evidence in SQLite."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path(".adversary/adversary.db")

    def save_run(self, report: ReviewReport) -> None:
        """Persist entire review run graph with relational integrity."""
        conn = init_db(self.db_path)
        with conn:
            # 1. Insert review_runs
            conn.execute(
                """
                INSERT OR REPLACE INTO review_runs
                (run_id, repo_path, git_commit, created_at, summary_json, report_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.repo_path,
                    report.git_commit,
                    report.created_at.isoformat(),
                    json.dumps(report.summary),
                    report.model_dump_json(),
                ),
            )

            # 2. Insert findings
            for f in report.findings:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO findings
                    (id, run_id, title, description, category, severity, confidence,
                     verification_status, file_path, line_start, line_end, source_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f.id,
                        report.run_id,
                        f.title,
                        f.description,
                        f.category.value,
                        f.severity.value,
                        f.confidence.value,
                        f.verification_status.value,
                        f.location.file_path,
                        f.location.line_start,
                        f.location.line_end,
                        f.source_hash,
                    ),
                )

            # 3. Insert hypotheses
            for h in report.hypotheses:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO hypotheses
                    (id, run_id, finding_id, target_file, target_function, preconditions,
                     trigger_input, expected_behavior, defect_behavior, rationale)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        h.id,
                        report.run_id,
                        h.finding_id,
                        h.target_file,
                        h.target_function,
                        h.preconditions,
                        h.trigger_input,
                        h.expected_behavior,
                        h.defect_behavior,
                        h.rationale,
                    ),
                )

            # 4. Insert test artifacts
            for t in report.tests:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO test_artifacts
                    (id, run_id, hypothesis_id, file_name, code, strategy)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (t.id, report.run_id, t.hypothesis_id, t.file_name, t.code, t.strategy),
                )

            # 5. Insert execution results
            for e in report.executions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO execution_results
                    (id, run_id, test_id, outcome, exit_code, stdout, stderr, exception_name, traceback_summary, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e.id,
                        report.run_id,
                        e.test_id,
                        e.outcome.value,
                        e.exit_code,
                        e.stdout,
                        e.stderr,
                        e.exception_name,
                        e.traceback_summary,
                        e.duration_ms,
                    ),
                )

            # 6. Insert verification decisions
            for d in report.decisions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO verification_decisions
                    (id, run_id, finding_id, hypothesis_id, status, is_attributed_to_target,
                     explanation, evidence_ids_json, decided_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.id,
                        report.run_id,
                        d.finding_id,
                        d.hypothesis_id,
                        d.status.value,
                        d.is_attributed_to_target,
                        d.explanation,
                        json.dumps(d.evidence_ids),
                        d.decided_at.isoformat(),
                    ),
                )

        conn.close()
        logger.info("Saved review run %s to SQLite database at %s", report.run_id, self.db_path)

    def get_run(self, run_id: str) -> ReviewReport | None:
        """Retrieve full review report by run ID."""
        if not self.db_path.exists():
            return None

        conn = init_db(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT report_json FROM review_runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return ReviewReport.model_validate_json(row[0])

    def get_latest_run(self) -> ReviewReport | None:
        """Retrieve the most recently saved review report."""
        if not self.db_path.exists():
            return None

        conn = init_db(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT report_json FROM review_runs ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return ReviewReport.model_validate_json(row[0])

    def list_runs(self) -> list[dict[str, Any]]:
        """List summary of all recorded review runs."""
        if not self.db_path.exists():
            return []

        conn = init_db(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT run_id, repo_path, git_commit, created_at, summary_json FROM review_runs ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        conn.close()

        runs: list[dict[str, Any]] = []
        for r in rows:
            runs.append(
                {
                    "run_id": r[0],
                    "repo_path": r[1],
                    "git_commit": r[2],
                    "created_at": r[3],
                    "summary": json.loads(r[4]) if r[4] else {},
                }
            )
        return runs

    def get_finding_details(
        self, finding_id: str, run_id: str | None = None
    ) -> dict[str, Any] | None:
        """Query correlated finding, hypothesis, test, execution result, and decision."""
        report = self.get_run(run_id) if run_id else self.get_latest_run()
        if not report:
            return None

        finding = next((f for f in report.findings if f.id == finding_id), None)
        if not finding:
            return None

        hypothesis = next((h for h in report.hypotheses if h.finding_id == finding_id), None)
        test = (
            next((t for t in report.tests if t.hypothesis_id == hypothesis.id), None)
            if hypothesis
            else None
        )
        execution = (
            next((e for e in report.executions if e.test_id == test.id), None) if test else None
        )
        decision = next((d for d in report.decisions if d.finding_id == finding_id), None)

        return {
            "finding": finding,
            "hypothesis": hypothesis,
            "test": test,
            "execution": execution,
            "decision": decision,
            "run_id": report.run_id,
            "repo_path": report.repo_path,
        }
