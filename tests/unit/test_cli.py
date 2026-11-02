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
    result = runner.invoke(app, ["findings"])
    assert result.exit_code == 0
    assert "Findings" in result.stdout


def test_cli_init(tmp_path: str) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Initialized Adversary workspace" in result.stdout
