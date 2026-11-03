"""Evaluation and benchmarking framework for evidence-gated code review."""

from adversary.evaluation.harness import EvaluationHarness
from adversary.evaluation.schemas import (
    BenchmarkRunReport,
    EvaluationBenchmarkMetrics,
    EvaluationCondition,
    GroundTruthDefect,
)

__all__ = [
    "BenchmarkRunReport",
    "EvaluationBenchmarkMetrics",
    "EvaluationCondition",
    "EvaluationHarness",
    "GroundTruthDefect",
]
