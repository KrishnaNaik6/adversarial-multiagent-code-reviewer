"""Unit tests for the CLI interface."""

from typer.testing import CliRunner

from adversary.cli.main import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Evidence-Gated Adversarial Multi-Agent Code Reviewer" in result.stdout
    assert "review" in result.stdout
    assert "findings" in result.stdout
    assert "explain" in result.stdout


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Adversary" in result.stdout


def test_cli_findings_empty() -> None:
    result = runner.invoke(app, ["findings", "--run-id", "non-existent-run-id"])
    assert result.exit_code == 0
    assert "No findings recorded yet" in result.stdout


def test_cli_explain_missing() -> None:
    result = runner.invoke(app, ["explain", "NON-EXISTENT-ID"])
    assert result.exit_code == 0
    assert "not found" in result.stdout


def test_cli_report() -> None:
    result = runner.invoke(app, ["report", "--format", "json"])
    assert result.exit_code == 0


def test_cli_init(tmp_path: str) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Initialized Adversary workspace" in result.stdout
