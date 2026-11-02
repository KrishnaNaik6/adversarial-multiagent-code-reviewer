"""Markdown report generator with full evidence traceability."""

from adversary.models.enums import VerificationStatus
from adversary.models.schemas import ReviewReport


class MarkdownReporter:
    """Generates structured GitHub-flavored Markdown review reports."""

    def generate_report(self, report: ReviewReport) -> str:
        lines: list[str] = [
            "# Adversary Code Review Report",
            "",
            f"**Run ID:** `{report.run_id}`  ",
            f"**Target Repository:** `{report.repo_path}`  ",
            f"**Git Commit:** `{report.git_commit or 'Not a git repo / clean tree'}`  ",
            f"**Generated:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Count |",
            "|---|---|",
            f"| Total Candidate Findings | {report.summary.get('total_findings', 0)} |",
            f"| **Confirmed Defects (Proven by Test)** | **{report.summary.get('confirmed', 0)}** |",
            f"| Disproved Hypotheses | {report.summary.get('disproved', 0)} |",
            f"| Inconclusive Findings | {report.summary.get('inconclusive', 0)} |",
            f"| Unverified Findings | {report.summary.get('unverified', 0)} |",
            "",
            "---",
            "",
            "## 2. Confirmed Defects",
            "",
        ]

        confirmed_findings = [
            f for f in report.findings if f.verification_status == VerificationStatus.CONFIRMED
        ]

        if not confirmed_findings:
            lines.extend(
                [
                    "_No confirmed defects were reproduced during this review run._",
                    "",
                ]
            )
        else:
            hyp_map = {h.finding_id: h for h in report.hypotheses}
            dec_map = {d.finding_id: d for d in report.decisions}
            test_map = {t.hypothesis_id: t for t in report.tests}
            exec_map = {e.test_id: e for e in report.executions}

            for f in confirmed_findings:
                hyp = hyp_map.get(f.id)
                dec = dec_map.get(f.id)
                test = test_map.get(hyp.id) if hyp else None
                execution = exec_map.get(test.id) if test else None

                lines.extend(
                    [
                        f"### [{f.id}] {f.title}",
                        "",
                        f"- **File:** `{f.location.file_path}:{f.location.line_start}`",
                        f"- **Category:** `{f.category.value}`",
                        f"- **Severity:** `{f.severity.value.upper()}`",
                        f"- **Confidence:** `{f.confidence.value.upper()}`",
                        f"- **Detected by:** `{f.originating_tool}` (Rule: `{f.rule_id}`)",
                        "",
                        "#### Defect Hypothesis",
                        f"- **Preconditions:** {hyp.preconditions if hyp else 'N/A'}",
                        f"- **Trigger Input:** `{hyp.trigger_input if hyp else 'N/A'}`",
                        f"- **Expected Behavior:** {hyp.expected_behavior if hyp else 'N/A'}",
                        f"- **Observed Defect:** {hyp.defect_behavior if hyp else 'N/A'}",
                        "",
                        "#### Adversarial Reproduction Proof",
                    ]
                )

                if test:
                    lines.extend(
                        [
                            f"- **Test Artifact:** `{test.file_name}` (Strategy: `{test.strategy}`)",
                            "```python",
                            test.code.strip(),
                            "```",
                        ]
                    )

                if execution and execution.traceback_summary:
                    lines.extend(
                        [
                            "",
                            "#### Execution Evidence",
                            f"- **Exit Code:** `{execution.exit_code}`",
                            f"- **Exception:** `{execution.exception_name or 'Failure'}`",
                            f"- **Execution Time:** `{execution.duration_ms:.2f} ms`",
                            "```text",
                            execution.traceback_summary.strip(),
                            "```",
                        ]
                    )

                if dec:
                    lines.extend(
                        [
                            "",
                            f"**Verification Decision:** {dec.explanation}",
                            "",
                        ]
                    )

                if f.suggested_remediation:
                    lines.extend(
                        [
                            f"**Remediation Suggestion:** {f.suggested_remediation}",
                            "",
                        ]
                    )
                lines.append("---")
                lines.append("")

        # Section 3: Disproved / Inconclusive Findings
        lines.extend(
            [
                "## 3. Disproved and Inconclusive Findings",
                "",
                "| Finding ID | Title | File | Status | Rationale |",
                "|---|---|---|---|---|",
            ]
        )

        other_findings = [
            f for f in report.findings if f.verification_status != VerificationStatus.CONFIRMED
        ]
        dec_map = {d.finding_id: d for d in report.decisions}

        for f in other_findings:
            d = dec_map.get(f.id)
            expl = d.explanation if d else "Not evaluated"
            # Truncate explanation for table
            short_expl = (expl[:80] + "...") if len(expl) > 80 else expl
            lines.append(
                f"| `{f.id}` | {f.title} | `{f.location.file_path}:{f.location.line_start}` | `{f.verification_status.value.upper()}` | {short_expl} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. Methodology and Trust Notice",
                "",
                "> **Principle:** Every finding in this report has earned its status through reproducible execution evidence.",
                "> No candidate warning is confirmed without an attributable failing test executed inside an isolated Docker sandbox.",
                "",
            ]
        )

        return "\n".join(lines)
