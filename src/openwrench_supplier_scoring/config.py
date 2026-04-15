from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricSpec:
    name: str
    raw_column: str
    support_column: str
    kind: str
    weight: float
    direction: int
    prior_strength: float
    count_column: str | None
    positive_phrase: str
    negative_phrase: str


@dataclass
class ScoringConfig:
    min_peer_suppliers: int = 4
    min_peer_jobs: int = 25
    peer_blend_supplier_target: int = 4
    peer_blend_job_target: int = 25
    continuous_prior_strength: float = 8.0
    binary_prior_strength: float = 10.0
    rating_prior_strength: float = 5.0
    bootstrap_iterations: int = 300
    random_seed: int = 42
    score_center: float = 50.0
    score_scale: float = 10.0
    final_score_prior_strength: float = 6.0
    confidence_jobs_target: int = 12
    confidence_rating_target: int = 5
    confidence_group_supplier_target: int = 6
    confidence_low_job_cap: int = 2
    confidence_medium_job_cap: int = 4
    metrics: tuple[MetricSpec, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metrics",
            (
                MetricSpec(
                    name="response_time_hours",
                    raw_column="response_time_hours_raw",
                    support_column="jobs_observed",
                    kind="continuous",
                    weight=0.20,
                    direction=-1,
                    prior_strength=self.continuous_prior_strength,
                    count_column=None,
                    positive_phrase="fast response times",
                    negative_phrase="slower response times",
                ),
                MetricSpec(
                    name="completion_time_hours",
                    raw_column="completion_time_hours_raw",
                    support_column="jobs_observed",
                    kind="continuous",
                    weight=0.20,
                    direction=-1,
                    prior_strength=self.continuous_prior_strength,
                    count_column=None,
                    positive_phrase="fast completion times",
                    negative_phrase="slower completion times",
                ),
                MetricSpec(
                    name="cost_usd",
                    raw_column="cost_usd_raw",
                    support_column="jobs_observed",
                    kind="continuous",
                    weight=0.15,
                    direction=-1,
                    prior_strength=self.continuous_prior_strength,
                    count_column=None,
                    positive_phrase="cost efficiency",
                    negative_phrase="above-peer costs",
                ),
                MetricSpec(
                    name="nte_compliance",
                    raw_column="nte_compliance_raw",
                    support_column="jobs_observed",
                    kind="binary",
                    weight=0.15,
                    direction=1,
                    prior_strength=self.binary_prior_strength,
                    count_column="nte_successes",
                    positive_phrase="strong NTE compliance",
                    negative_phrase="weaker NTE compliance",
                ),
                MetricSpec(
                    name="customer_rating",
                    raw_column="customer_rating_raw",
                    support_column="ratings_observed",
                    kind="continuous",
                    weight=0.10,
                    direction=1,
                    prior_strength=self.rating_prior_strength,
                    count_column=None,
                    positive_phrase="strong customer ratings",
                    negative_phrase="weaker customer ratings",
                ),
                MetricSpec(
                    name="reopened",
                    raw_column="reopened_raw",
                    support_column="jobs_observed",
                    kind="binary",
                    weight=0.20,
                    direction=-1,
                    prior_strength=self.binary_prior_strength,
                    count_column="reopened_events",
                    positive_phrase="a low reopen rate",
                    negative_phrase="a higher reopen rate",
                ),
            ),
        )
