"""Typer CLI entry point with Rich formatting."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adversary import __version__
from adversary.config.settings import AdversaryConfig

app = typer.Typer(
    name="adversary",
    help="Evidence-Gated Adversarial Multi-Agent Code Reviewer with Automated Test Proofs",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version() -> None:
    """Show the version and environment status."""
    console.print(
        Panel.fit(
            f"[bold blue]Adversary[/bold blue] v{__version__}\n"
            f"[dim]Python {sys.version.split()[0]} - Deterministic-First Evidence-Gated Reviewer[/dim]",
            title="Adversary Version",
            border_style="blue",
        )
    )


@app.command()
def init(
    target_dir: Path = typer.Argument(Path.cwd(), help="Target repository directory to initialize"),
) -> None:
    """Initialize Adversary configuration and workspace directories."""
    config = AdversaryConfig(workspace_dir=target_dir)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.reports_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        f"[bold green]✔[/bold green] Initialized Adversary workspace in [cyan]{config.data_dir}[/cyan]"
    )


@app.command()
def review(
    target_path: Path = typer.Argument(Path.cwd(), help="Path to local repository to review"),
    changed_only: bool = typer.Option(
        False, "--changed-only", help="Only review modified files in git"
    ),
    base_branch: str = typer.Option("main", "--base", help="Base branch for git diff comparison"),
) -> None:
    """Execute the full evidence-gated review pipeline on a repository."""
    console.print(f"[bold cyan]🔍 Reviewing target repository:[/bold cyan] {target_path}")
    # Integration hooks will connect to Orchestrator in Phase 7
    console.print(f"[dim]Options: changed_only={changed_only}, base_branch={base_branch}[/dim]")


@app.command()
def findings(
    run_id: str | None = typer.Option(None, "--run-id", help="Review run ID (defaults to latest)"),
) -> None:
    """List findings and their evidence verification status."""
    table = Table(title=f"Findings {f'for Run {run_id}' if run_id else '(Latest)'}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Category", style="magenta")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="green")
    table.add_column("Location", style="yellow")

    console.print(table)
    console.print("[dim]No findings recorded yet. Run `adversary review <path>` to begin.[/dim]")


@app.command()
def explain(
    finding_id: str = typer.Argument(..., help="ID of finding to explain (e.g. FIND-001)"),
) -> None:
    """Explain a finding, its defect hypothesis, adversarial test, and evidence."""
    console.print(f"[bold cyan]Finding Details:[/bold cyan] {finding_id}")
    console.print("[dim]Querying persistence store for finding evidence...[/dim]")


@app.command()
def verify(
    finding_id: str = typer.Argument(..., help="ID of finding to verify"),
) -> None:
    """Re-run adversarial test execution and independent verification."""
    console.print(f"[bold yellow]Verifying finding:[/bold yellow] {finding_id}")


@app.command()
def fix(
    finding_id: str = typer.Argument(..., help="ID of confirmed finding to repair"),
    apply: bool = typer.Option(
        False, "--apply", help="Apply patch to working tree after human review"
    ),
) -> None:
    """Generate minimal patch and run regression validation in an isolated workspace."""
    console.print(
        f"[bold magenta]Proposing repair for:[/bold magenta] {finding_id} (apply={apply})"
    )


@app.command()
def report(
    format_type: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown or json"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="File path to save report"
    ),
) -> None:
    """Generate review report in Markdown or JSON format."""
    console.print(f"[bold green]Generating report[/bold green] (format: {format_type})")


if __name__ == "__main__":
    app()
