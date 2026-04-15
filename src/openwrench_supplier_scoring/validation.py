from __future__ import annotations

from typing import Any

import pandas as pd


def build_validation_summary(
    jobs: pd.DataFrame,
    scored: pd.DataFrame,
    naive: pd.DataFrame,
    bootstrap_scores: pd.DataFrame,
) -> dict[str, Any]:
    merged = scored.merge(
        naive[["supplier_id", "score_overall", "rank_overall"]],
        on="supplier_id",
        how="left",
        suffixes=("", "_naive"),
    )
    merged["score_change_vs_naive"] = merged["score_overall"] - merged["score_overall_naive"]
    merged["rank_change_vs_naive"] = merged["rank_overall_naive"] - merged["rank_overall"]

    largest_shrinkage = (
        merged.assign(
            absolute_score_change=lambda frame: frame["score_change_vs_naive"].abs()
        )
        .sort_values(
            ["absolute_score_change", "jobs_observed"],
            ascending=[False, True],
        )
        .head(8)
    )

    bootstrap_summary = (
        bootstrap_scores.groupby("supplier_id")
        .agg(
            score_std=("score_overall", "std"),
            median_rank=("rank_overall", "median"),
        )
        .reset_index()
    )

    top_ten_overlap = len(
        set(scored.head(10)["supplier_id"]).intersection(set(naive.head(10)["supplier_id"]))
    )

    return {
        "input_rows": int(len(jobs)),
        "supplier_count": int(scored["supplier_id"].nunique()),
        "missing_customer_rating_rows": int(jobs["customer_rating"].isna().sum()),
        "suppliers_without_ratings": int((scored["ratings_observed"] == 0).sum()),
        "low_support_suppliers_jobs_le_3": int((scored["jobs_observed"] <= 3).sum()),
        "low_support_suppliers_jobs_le_5": int((scored["jobs_observed"] <= 5).sum()),
        "comparison_levels": {
            key: int(value)
            for key, value in scored["comparison_level"].value_counts().to_dict().items()
        },
        "confidence_labels": {
            key: int(value)
            for key, value in scored["confidence_label"].value_counts().to_dict().items()
        },
        "top_10_overlap_with_naive": int(top_ten_overlap),
        "median_bootstrap_rank_interval_width": round(
            float(scored["bootstrap_rank_interval_width"].median()),
            3,
        ),
        "median_bootstrap_score_interval_width": round(
            float(scored["bootstrap_score_interval_width"].median()),
            3,
        ),
        "largest_shrinkage_examples": largest_shrinkage[
            [
                "supplier_id",
                "category",
                "region",
                "jobs_observed",
                "score_overall",
                "score_overall_naive",
                "score_change_vs_naive",
                "rank_overall",
                "rank_overall_naive",
            ]
        ]
        .round(3)
        .to_dict(orient="records"),
        "top_suppliers": scored[
            [
                "rank_overall",
                "supplier_id",
                "category",
                "region",
                "score_overall",
                "confidence_label",
                "jobs_observed",
            ]
        ]
        .head(10)
        .round(3)
        .to_dict(orient="records"),
        "top_suppliers_conservative": scored[
            [
                "rank_conservative",
                "supplier_id",
                "category",
                "region",
                "score_conservative",
                "confidence_label",
                "jobs_observed",
            ]
        ]
        .sort_values(["rank_conservative", "supplier_id"])
        .head(10)
        .round(3)
        .to_dict(orient="records"),
        "bootstrap_score_std_examples": bootstrap_summary.sort_values(
            "score_std",
            ascending=False,
        )
        .head(10)
        .round(3)
        .to_dict(orient="records"),
    }


def build_validation_report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Validation Report",
        "",
        "## Coverage",
        f"- Input rows: {summary['input_rows']}",
        f"- Suppliers scored: {summary['supplier_count']}",
        f"- Missing customer-rating rows: {summary['missing_customer_rating_rows']}",
        f"- Suppliers with no ratings: {summary['suppliers_without_ratings']}",
        f"- Suppliers with <=3 observed jobs: {summary['low_support_suppliers_jobs_le_3']}",
        f"- Suppliers with <=5 observed jobs: {summary['low_support_suppliers_jobs_le_5']}",
        "",
        "## Comparison Levels",
    ]

    for label, count in summary["comparison_levels"].items():
        lines.append(f"- {label}: {count}")

    lines.extend(
        [
            "",
            "## Confidence Labels",
        ]
    )
    for label, count in summary["confidence_labels"].items():
        lines.append(f"- {label}: {count}")

    lines.extend(
        [
            "",
            "## Stability",
            f"- Top-10 overlap with naive ranking: {summary['top_10_overlap_with_naive']}",
            f"- Median bootstrap rank interval width: {summary['median_bootstrap_rank_interval_width']}",
            f"- Median bootstrap score interval width: {summary['median_bootstrap_score_interval_width']}",
            "",
            "## Largest Shrinkage Examples",
        ]
    )

    for example in summary["largest_shrinkage_examples"]:
        lines.append(
            "- {supplier_id} ({category}, {region}): score {score_overall} vs naive "
            "{score_overall_naive}, rank {rank_overall} vs naive {rank_overall_naive}".format(
                **example
            )
        )

    lines.extend(["", "## Top Suppliers"])
    for supplier in summary["top_suppliers"]:
        lines.append(
            "- #{rank_overall} {supplier_id} ({category}, {region}) score {score_overall} "
            "[{confidence_label}] across {jobs_observed} jobs".format(**supplier)
        )

    lines.extend(["", "## Conservative Top Suppliers"])
    for supplier in summary["top_suppliers_conservative"]:
        lines.append(
            "- #{rank_conservative} {supplier_id} ({category}, {region}) conservative score "
            "{score_conservative} [{confidence_label}] across {jobs_observed} jobs".format(
                **supplier
            )
        )

    return "\n".join(lines) + "\n"
