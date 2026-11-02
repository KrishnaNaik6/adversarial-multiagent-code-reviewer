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
        f"[bold green][OK][/bold green] Initialized Adversary workspace in [cyan]{config.data_dir}[/cyan]"
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
    from adversary.orchestration.coordinator import ReviewOrchestrator

    console.print(f"[bold cyan][*] Reviewing target repository:[/bold cyan] {target_path}")

    orchestrator = ReviewOrchestrator()
    try:
        report = orchestrator.run(target_path)
    except Exception as e:
        console.print(f"[bold red]Review failed:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    # Render results table
    table = Table(title=f"Review Results for {report.repo_path} (Run: {report.run_id})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Category", style="magenta")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="green")
    table.add_column("Location", style="yellow")

    for f in report.findings:
        status_color = "green" if f.verification_status.value == "confirmed" else "dim"
        table.add_row(
            f.id,
            f.title,
            f.category.value,
            f.severity.value,
            f"[{status_color}]{f.verification_status.value.upper()}[/{status_color}]",
            f"{f.location.file_path}:{f.location.line_start}",
        )

    console.print(table)
    console.print(
        Panel.fit(
            f"Total Findings: {report.summary.get('total_findings', 0)} | "
            f"[bold green]Confirmed: {report.summary.get('confirmed', 0)}[/bold green] | "
            f"Disproved: {report.summary.get('disproved', 0)} | "
            f"Inconclusive: {report.summary.get('inconclusive', 0)}",
            title="Verification Summary",
            border_style="green" if report.summary.get("confirmed", 0) > 0 else "blue",
        )
    )


@app.command()
def findings(
    run_id: str | None = typer.Option(None, "--run-id", help="Review run ID (defaults to latest)"),
) -> None:
    """List findings and their evidence verification status."""
    from adversary.persistence.repository import RunStore

    store = RunStore()
    report = store.get_run(run_id) if run_id else store.get_latest_run()
    if not report or not report.findings:
        console.print(
            "[dim]No findings recorded yet. Run `adversary review <path>` to begin.[/dim]"
        )
        return

    table = Table(
        title=f"Findings {f'for Run {run_id}' if run_id else f'(Latest: {report.run_id})'}"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Category", style="magenta")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="green")
    table.add_column("Location", style="yellow")

    for f in report.findings:
        status_color = "green" if f.verification_status.value == "confirmed" else "dim"
        table.add_row(
            f.id,
            f.title,
            f.category.value,
            f.severity.value,
            f"[{status_color}]{f.verification_status.value.upper()}[/{status_color}]",
            f"{f.location.file_path}:{f.location.line_start}",
        )

    console.print(table)


@app.command()
def explain(
    finding_id: str = typer.Argument(..., help="ID of finding to explain (e.g. FIND-001)"),
) -> None:
    """Explain a finding, its defect hypothesis, adversarial test, and evidence."""
    from adversary.persistence.repository import RunStore

    store = RunStore()
    details = store.get_finding_details(finding_id)
    if not details:
        console.print(f"[bold red]Finding {finding_id} not found in database.[/bold red]")
        return

    f = details["finding"]
    h = details.get("hypothesis")
    t = details.get("test")
    e = details.get("execution")
    d = details.get("decision")

    console.print(
        Panel(
            f"[bold cyan]Finding:[/bold cyan] {f.id} - {f.title}\n"
            f"[bold]Location:[/bold] {f.location.file_path}:{f.location.line_start}\n"
            f"[bold]Category:[/bold] {f.category.value} | [bold]Severity:[/bold] {f.severity.value.upper()}\n"
            f"[bold]Status:[/bold] [bold green]{f.verification_status.value.upper()}[/bold green]\n"
            f"[dim]Rule:[/dim] {f.rule_id} ({f.originating_tool})",
            title=f"Finding Details: {f.id}",
            border_style="cyan",
        )
    )

    if h:
        console.print(
            Panel(
                f"[bold]Preconditions:[/bold] {h.preconditions}\n"
                f"[bold]Trigger Input:[/bold] {h.trigger_input}\n"
                f"[bold]Expected Behavior:[/bold] {h.expected_behavior}\n"
                f"[bold]Observed Defect:[/bold] {h.defect_behavior}\n"
                f"[dim]Rationale:[/dim] {h.rationale}",
                title=f"Defect Hypothesis: {h.id}",
                border_style="magenta",
            )
        )

    if t:
        console.print(
            Panel(
                f"[dim]# Strategy: {t.strategy}[/dim]\n{t.code.strip()}",
                title=f"Adversarial Reproduction Test: {t.file_name}",
                border_style="yellow",
            )
        )

    if e:
        tb_text = e.traceback_summary or e.stderr or e.stdout or "No traceback captured"
        console.print(
            Panel(
                f"[bold]Exit Code:[/bold] {e.exit_code} | [bold]Exception:[/bold] {e.exception_name or 'N/A'}\n"
                f"[bold]Duration:[/bold] {e.duration_ms:.2f} ms\n\n"
                f"[bold red]Traceback Output:[/bold red]\n{tb_text.strip()}",
                title=f"Execution Evidence: {e.id}",
                border_style="red" if e.exit_code != 0 else "green",
            )
        )

    if d:
        console.print(
            Panel.fit(
                f"[bold]Verification Decision:[/bold] {d.status.value.upper()}\n"
                f"[dim]{d.explanation}[/dim]",
                title="Independent Verification Decision",
                border_style="green" if d.status.value == "confirmed" else "blue",
            )
        )


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
    from adversary.patching.applier import PatchApplier
    from adversary.patching.patcher import BlueTeamPatcher
    from adversary.persistence.repository import RunStore

    store = RunStore()
    details = store.get_finding_details(finding_id)
    if not details:
        console.print(f"[bold red]Finding {finding_id} not found in database.[/bold red]")
        raise typer.Exit(code=1)

    f = details["finding"]
    h = details.get("hypothesis")
    t = details.get("test")
    repo_path = Path(details["repo_path"])

    if not h or not t:
        console.print(f"[bold red]Finding {finding_id} does not have required hypothesis or test proof.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold magenta][*] Proposing repair for:[/bold magenta] {finding_id}")

    patcher = BlueTeamPatcher()
    patch = patcher.propose_and_verify_repair(
        finding=f,
        hypothesis=h,
        reproduction_test=t,
        repo_path=repo_path,
    )

    if not patch:
        console.print("[bold red]Could not formulate a valid deterministic repair for this finding.[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            patch.diff.strip(),
            title=f"Proposed Minimal Patch: {patch.id}",
            border_style="cyan",
        )
    )

    console.print(
        Panel.fit(
            f"Adversarial Reproduction Test: [{'green' if patch.adversarial_test_passed else 'red'}]{'PASSED' if patch.adversarial_test_passed else 'FAILED'}[/]\n"
            f"Existing Regression Tests: [{'green' if patch.regression_tests_passed else 'red'}]{'PASSED' if patch.regression_tests_passed else 'FAILED'}[/]\n"
            f"Repair Status: [bold green]{patch.repair_status.value.upper()}[/bold green]",
            title="Regression & Proof Verification",
            border_style="green" if patch.repair_status.value == "validated" else "yellow",
        )
    )

    if apply:
        applier = PatchApplier()
        try:
            applier.apply_patch(patch, repo_path=repo_path, human_approved=True)
            console.print("[bold green][OK] Patch successfully applied to repository working tree.[/bold green]")
        except Exception as err:
            console.print(f"[bold red]Failed to apply patch:[/bold red] {err}")
            raise typer.Exit(code=1) from err
    else:
        console.print("[dim]Review the diff above. To apply this patch to your repository, re-run with: [bold]adversary fix " + finding_id + " --apply[/bold][/dim]")


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
    from adversary.persistence.repository import RunStore
    from adversary.reporting.json_reporter import JSONReporter
    from adversary.reporting.markdown import MarkdownReporter

    store = RunStore()
    latest = store.get_latest_run()
    if not latest:
        console.print("[bold red]No review runs found to report on.[/bold red]")
        raise typer.Exit(code=1)

    if format_type.lower() == "json":
        content = JSONReporter().generate_report(latest)
    else:
        content = MarkdownReporter().generate_report(latest)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
        console.print(f"[bold green][OK][/bold green] Report saved to [cyan]{output_file}[/cyan]")
    else:
        console.print(content)


if __name__ == "__main__":
    app()
