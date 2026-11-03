"""Schemas and data models for evidence-based evaluation framework."""

from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluationCondition(StrEnum):
    """Controlled experimental review conditions."""

    CONDITION_A_DETERMINISTIC_BASELINE = "condition_a_deterministic_baseline"
    CONDITION_B_AI_ASSISTED_NO_EXECUTION = "condition_b_ai_assisted_no_execution"
    CONDITION_C_ADVERSARIAL_TESTING_NO_VERIFIER = "condition_c_adversarial_testing_no_verifier"
    CONDITION_D_FULL_EVIDENCE_GATED = "condition_d_full_evidence_gated"


class GroundTruthDefect(BaseModel):
    """Ground truth defect specification for benchmark repos."""

    id: str
    target_file: str
    target_function: str
    line: int
    category: str
    description: str
    expected_exception_or_failure: str


class EvaluationBenchmarkMetrics(BaseModel):
    """Statistical evaluation metrics for code review systems."""

    condition: EvaluationCondition
    condition_name: str
    total_candidates_flagged: int = 0
    confirmed_defects_reported: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0
    attribution_accuracy: float = 0.0
    reproducibility_rate: float = 0.0
    execution_time_seconds: float = 0.0


class BenchmarkRunReport(BaseModel):
    """Comprehensive benchmark comparison report across all 4 experimental conditions."""

    repository_path: str
    ground_truth_count: int
    ground_truth_defects: list[GroundTruthDefect]
    condition_results: dict[str, EvaluationBenchmarkMetrics] = Field(default_factory=dict)
