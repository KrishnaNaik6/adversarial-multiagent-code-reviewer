"""JSON report generator following versioned schema."""

from adversary.models.schemas import ReviewReport


class JSONReporter:
    """Exports machine-readable JSON review reports."""

    def generate_report(self, report: ReviewReport, indent: int = 2) -> str:
        """Format ReviewReport domain model as indented JSON string."""
        return report.model_dump_json(indent=indent)

