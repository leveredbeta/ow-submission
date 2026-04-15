from __future__ import annotations

from typing import Any

import pandas as pd

from .config import ScoringConfig
from .scoring import build_scored_supplier_frame


SENSITIVITY_SCENARIOS: dict[str, dict[str, Any]] = {
    "baseline": {},
    "lighter_shrinkage": {
        "continuous_prior_strength": 6.0,
        "binary_prior_strength": 8.0,
        "rating_prior_strength": 4.0,
        "final_score_prior_strength": 4.0,
    },
    "heavier_shrinkage": {
        "continuous_prior_strength": 12.0,
        "binary_prior_strength": 14.0,
        "rating_prior_strength": 6.0,
        "final_score_prior_strength": 10.0,
    },
    "more_local_comparison": {
        "min_peer_suppliers": 3,
        "min_peer_jobs": 18,
        "peer_blend_supplier_target": 3,
        "peer_blend_job_target": 18,
    },
    "more_conservative_local_comparison": {
        "min_peer_suppliers": 5,
        "min_peer_jobs": 35,
        "peer_blend_supplier_target": 5,
        "peer_blend_job_target": 35,
    },
    "quality_emphasis": {
        "metric_weight_overrides": {
            "response_time_hours": 0.15,
            "completion_time_hours": 0.15,
            "cost_usd": 0.10,
            "nte_compliance": 0.15,
            "customer_rating": 0.15,
            "reopened": 0.30,
        }
    },
    "speed_emphasis": {
        "metric_weight_overrides": {
            "response_time_hours": 0.25,
            "completion_time_hours": 0.25,
            "cost_usd": 0.15,
            "nte_compliance": 0.10,
            "customer_rating": 0.05,
            "reopened": 0.20,
        }
    },
}


def build_sensitivity_analysis(
    jobs: pd.DataFrame,
    base_config: ScoringConfig,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    results: dict[str, pd.DataFrame] = {}

    for scenario_name, overrides in SENSITIVITY_SCENARIOS.items():
        scenario_kwargs = base_config.to_init_kwargs()
        scenario_kwargs.update(overrides)
        scenario_kwargs["bootstrap_iterations"] = base_config.bootstrap_iterations
        scenario_kwargs["random_seed"] = base_config.random_seed
        scenario_config = ScoringConfig(**scenario_kwargs)
        results[scenario_name] = build_scored_supplier_frame(
            jobs,
            config=scenario_config,
            use_shrinkage=True,
        )[
            [
                "supplier_id",
                "rank_overall",
                "score_overall",
            ]
        ].copy()

    baseline = results["baseline"].rename(
        columns={
            "rank_overall": "rank_overall_baseline",
            "score_overall": "score_overall_baseline",
        }
    )
    baseline_top_10 = set(results["baseline"].head(10)["supplier_id"].tolist())
    baseline_top_5 = set(results["baseline"].head(5)["supplier_id"].tolist())

    rows: list[dict[str, Any]] = []
    for scenario_name, frame in results.items():
        merged = baseline.merge(frame, on="supplier_id", how="left")
        scenario_top_10 = set(frame.head(10)["supplier_id"].tolist())
        scenario_top_5 = set(frame.head(5)["supplier_id"].tolist())
        moved_out = sorted(baseline_top_10 - scenario_top_10)
        moved_in = sorted(scenario_top_10 - baseline_top_10)

        rows.append(
            {
                "scenario": scenario_name,
                "top_10_overlap_vs_baseline": len(baseline_top_10 & scenario_top_10),
                "top_5_overlap_vs_baseline": len(baseline_top_5 & scenario_top_5),
                "spearman_rank_corr_vs_baseline": round(
                    float(
                        merged["rank_overall_baseline"].corr(
                            merged["rank_overall"],
                            method="spearman",
                        )
                    ),
                    4,
                ),
                "mean_abs_rank_shift": round(
                    float(
                        (merged["rank_overall_baseline"] - merged["rank_overall"])
                        .abs()
                        .mean()
                    ),
                    3,
                ),
                "max_abs_rank_shift": int(
                    (merged["rank_overall_baseline"] - merged["rank_overall"]).abs().max()
                ),
                "baseline_top_10_moved_out": ", ".join(moved_out),
                "baseline_top_10_moved_in": ", ".join(moved_in),
            }
        )

    summary = pd.DataFrame(rows).sort_values("scenario").reset_index(drop=True)
    return summary, results


def build_sensitivity_report_markdown(summary: pd.DataFrame) -> str:
    lines = [
        "# Sensitivity Analysis",
        "",
        "This report compares the baseline ranking against several reasonable methodology variants.",
        "The goal is to show that the leaderboard is not purely an artifact of one arbitrary parameter setting.",
        "",
    ]
    for _, row in summary.iterrows():
        lines.append(f"## {row['scenario']}")
        lines.append(
            f"- Top-10 overlap vs baseline: {row['top_10_overlap_vs_baseline']}/10"
        )
        lines.append(
            f"- Top-5 overlap vs baseline: {row['top_5_overlap_vs_baseline']}/5"
        )
        lines.append(
            f"- Spearman rank correlation vs baseline: {row['spearman_rank_corr_vs_baseline']}"
        )
        lines.append(f"- Mean absolute rank shift: {row['mean_abs_rank_shift']}")
        lines.append(f"- Max absolute rank shift: {row['max_abs_rank_shift']}")
        if row["baseline_top_10_moved_out"]:
            lines.append(
                f"- Baseline top-10 suppliers moved out: {row['baseline_top_10_moved_out']}"
            )
        if row["baseline_top_10_moved_in"]:
            lines.append(
                f"- Suppliers moved into the top 10: {row['baseline_top_10_moved_in']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
