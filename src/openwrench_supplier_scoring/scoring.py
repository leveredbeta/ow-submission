from __future__ import annotations

from math import ceil, floor

import numpy as np
import pandas as pd

from .config import MetricSpec, ScoringConfig


def aggregate_supplier_metrics(jobs: pd.DataFrame) -> pd.DataFrame:
    suppliers = (
        jobs.groupby(["supplier_id", "category", "region"], as_index=False)
        .agg(
            jobs_observed=("work_order_id", "count"),
            response_time_hours_raw=("response_time_hours", "mean"),
            completion_time_hours_raw=("completion_time_hours", "mean"),
            cost_usd_raw=("cost_usd", "mean"),
            nte_compliance_raw=("nte_compliance", "mean"),
            nte_successes=("nte_compliance", "sum"),
            customer_rating_raw=("customer_rating", "mean"),
            ratings_observed=("customer_rating", lambda series: int(series.notna().sum())),
            reopened_raw=("reopened", "mean"),
            reopened_events=("reopened", "sum"),
            historical_job_count_for_supplier=("job_count_for_supplier", "median"),
        )
        .sort_values(["category", "region", "supplier_id"])
        .reset_index(drop=True)
    )
    return suppliers


def _job_level_baselines(jobs: pd.DataFrame, prefix: str, group_columns: list[str]) -> pd.DataFrame:
    baseline_columns = {
        "response_time_hours": f"{prefix}_response_time_hours",
        "completion_time_hours": f"{prefix}_completion_time_hours",
        "cost_usd": f"{prefix}_cost_usd",
        "nte_compliance": f"{prefix}_nte_compliance",
        "customer_rating": f"{prefix}_customer_rating",
        "reopened": f"{prefix}_reopened",
        "work_order_id": f"{prefix}_jobs",
        "supplier_id": f"{prefix}_suppliers",
    }
    return (
        jobs.groupby(group_columns, as_index=False)
        .agg(
            response_time_hours=("response_time_hours", "mean"),
            completion_time_hours=("completion_time_hours", "mean"),
            cost_usd=("cost_usd", "mean"),
            nte_compliance=("nte_compliance", "mean"),
            customer_rating=("customer_rating", "mean"),
            reopened=("reopened", "mean"),
            work_order_id=("work_order_id", "count"),
            supplier_id=("supplier_id", "nunique"),
        )
        .rename(columns=baseline_columns)
    )


def add_group_context(
    jobs: pd.DataFrame,
    suppliers: pd.DataFrame,
    config: ScoringConfig,
) -> pd.DataFrame:
    peer_stats = _job_level_baselines(jobs, "peer", ["category", "region"])
    category_stats = _job_level_baselines(jobs, "category", ["category"])

    suppliers = suppliers.merge(peer_stats, on=["category", "region"], how="left")
    suppliers = suppliers.merge(category_stats, on=["category"], how="left")

    peer_blend_weight = np.minimum.reduce(
        [
            suppliers["peer_suppliers"] / config.peer_blend_supplier_target,
            suppliers["peer_jobs"] / config.peer_blend_job_target,
            np.ones(len(suppliers)),
        ]
    )
    suppliers["peer_blend_weight"] = peer_blend_weight

    local_enough = (
        (suppliers["peer_suppliers"] >= config.min_peer_suppliers)
        & (suppliers["peer_jobs"] >= config.min_peer_jobs)
    )
    suppliers["comparison_level"] = np.where(local_enough, "category_region", "category")
    suppliers["comparison_group"] = np.where(
        local_enough,
        "category_region|"
        + suppliers["category"].astype(str)
        + "|"
        + suppliers["region"].astype(str),
        "category|" + suppliers["category"].astype(str),
    )
    suppliers["comparison_label"] = np.where(
        local_enough,
        suppliers["category"].astype(str) + " suppliers in " + suppliers["region"].astype(str),
        suppliers["category"].astype(str) + " suppliers overall",
    )
    suppliers["comparison_group_suppliers"] = np.where(
        local_enough,
        suppliers["peer_suppliers"],
        suppliers["category_suppliers"],
    )
    suppliers["comparison_group_jobs"] = np.where(
        local_enough,
        suppliers["peer_jobs"],
        suppliers["category_jobs"],
    )

    for metric in config.metrics:
        peer_column = f"peer_{metric.name}"
        category_column = f"category_{metric.name}"
        suppliers[f"{metric.name}_baseline"] = (
            suppliers["peer_blend_weight"] * suppliers[peer_column]
            + (1.0 - suppliers["peer_blend_weight"]) * suppliers[category_column]
        )

    return suppliers


def _apply_metric_shrinkage(suppliers: pd.DataFrame, metric: MetricSpec) -> pd.DataFrame:
    raw = suppliers[metric.raw_column]
    baseline = suppliers[f"{metric.name}_baseline"]
    support = suppliers[metric.support_column].astype(float)

    raw_filled = raw.fillna(baseline)
    suppliers[f"{metric.name}_raw_filled"] = raw_filled

    if metric.kind == "binary":
        successes = suppliers[metric.count_column].astype(float)
        shrunk = (successes + baseline * metric.prior_strength) / (
            support + metric.prior_strength
        )
    else:
        shrunk = (raw_filled * support + baseline * metric.prior_strength) / (
            support + metric.prior_strength
        )

    suppliers[f"{metric.name}_shrunk"] = shrunk
    suppliers[f"{metric.name}_shrinkage_delta"] = shrunk - raw_filled
    return suppliers


def add_shrunk_metrics(suppliers: pd.DataFrame, config: ScoringConfig) -> pd.DataFrame:
    for metric in config.metrics:
        suppliers = _apply_metric_shrinkage(suppliers, metric)
    return suppliers


def _percentiles_within_group(
    suppliers: pd.DataFrame,
    group_column: str,
    value_column: str,
    direction: int,
) -> pd.Series:
    oriented = direction * suppliers[value_column]
    ranks = oriented.groupby(suppliers[group_column]).rank(method="average", ascending=True)
    group_sizes = suppliers.groupby(group_column)[value_column].transform("size")
    percentiles = np.where(
        group_sizes <= 1,
        50.0,
        ((ranks - 1.0) / (group_sizes - 1.0)) * 100.0,
    )
    return pd.Series(percentiles, index=suppliers.index)


def add_component_scores(
    suppliers: pd.DataFrame,
    config: ScoringConfig,
    use_shrinkage: bool,
) -> pd.DataFrame:
    score_source = "shrunk" if use_shrinkage else "raw_filled"

    for metric in config.metrics:
        value_column = f"{metric.name}_{score_source}"
        group_mean = suppliers.groupby("comparison_group")[value_column].transform("mean")
        group_std = suppliers.groupby("comparison_group")[value_column].transform(
            lambda series: series.std(ddof=0)
        )
        safe_std = group_std.where(group_std > 1e-9, 1.0)
        z_score = metric.direction * ((suppliers[value_column] - group_mean) / safe_std)

        suppliers[f"{metric.name}_z"] = z_score.fillna(0.0)
        suppliers[f"{metric.name}_component_score"] = _percentiles_within_group(
            suppliers,
            group_column="comparison_group",
            value_column=value_column,
            direction=metric.direction,
        )
        suppliers[f"{metric.name}_contribution"] = (
            suppliers[f"{metric.name}_z"] * metric.weight
        )

    return suppliers


def add_overall_scores(suppliers: pd.DataFrame, config: ScoringConfig) -> pd.DataFrame:
    contribution_columns = [f"{metric.name}_contribution" for metric in config.metrics]
    suppliers["score_latent"] = suppliers[contribution_columns].sum(axis=1)
    suppliers["score_performance"] = (
        config.score_center + config.score_scale * suppliers["score_latent"]
    )
    suppliers["score_evidence_weight"] = np.sqrt(
        suppliers["jobs_observed"]
        / (suppliers["jobs_observed"] + config.final_score_prior_strength)
    )
    suppliers["score_overall"] = (
        config.score_center
        + suppliers["score_evidence_weight"]
        * (suppliers["score_performance"] - config.score_center)
    ).clip(0.0, 100.0)
    suppliers = suppliers.sort_values(
        ["score_overall", "jobs_observed", "supplier_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    suppliers["rank_overall"] = suppliers["score_overall"].rank(
        method="min",
        ascending=False,
    ).astype(int)
    return suppliers


def _join_phrases(phrases: list[str]) -> str:
    if not phrases:
        return "balanced performance"
    if len(phrases) == 1:
        return phrases[0]
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]


def _sentence_case(phrase: str) -> str:
    if not phrase:
        return phrase
    return phrase[0].upper() + phrase[1:]


def add_explanations(suppliers: pd.DataFrame, config: ScoringConfig) -> pd.DataFrame:
    explanations: list[str] = []
    for _, row in suppliers.iterrows():
        positive_metrics = sorted(
            config.metrics,
            key=lambda metric: row[f"{metric.name}_contribution"],
            reverse=True,
        )
        negative_metrics = sorted(
            config.metrics,
            key=lambda metric: row[f"{metric.name}_contribution"],
        )

        positive_phrases = [
            metric.positive_phrase
            for metric in positive_metrics[:3]
            if row[f"{metric.name}_contribution"] > 0.03
        ][:2]

        negative_metric = next(
            (
                metric
                for metric in negative_metrics
                if row[f"{metric.name}_contribution"] < -0.03
            ),
            None,
        )

        base = (
            f"Compared with {row['comparison_label']}, this supplier stands out for "
            f"{_join_phrases(positive_phrases)} across {int(row['jobs_observed'])} jobs."
        )

        if negative_metric is not None:
            base += f" {_sentence_case(negative_metric.negative_phrase)} reduced the score."

        if row["ratings_observed"] == 0:
            base += " Customer-rating evidence is unavailable in this sample."
        elif row["confidence_label"] == "Low":
            base += " Confidence is lower because the observed history is limited."

        explanations.append(base)

    suppliers["short_explanation"] = explanations
    return suppliers


def build_scored_supplier_frame(
    jobs: pd.DataFrame,
    config: ScoringConfig,
    use_shrinkage: bool,
    use_evidence_adjustment: bool = True,
) -> pd.DataFrame:
    suppliers = aggregate_supplier_metrics(jobs)
    suppliers = add_group_context(jobs, suppliers, config=config)
    suppliers = add_shrunk_metrics(suppliers, config=config)
    suppliers = add_component_scores(
        suppliers,
        config=config,
        use_shrinkage=use_shrinkage,
    )
    suppliers = add_overall_scores(suppliers, config=config)
    if not use_evidence_adjustment:
        suppliers["score_evidence_weight"] = 1.0
        suppliers["score_overall"] = suppliers["score_performance"].clip(0.0, 100.0)
        suppliers = suppliers.sort_values(
            ["score_overall", "jobs_observed", "supplier_id"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
        suppliers["rank_overall"] = suppliers["score_overall"].rank(
            method="min",
            ascending=False,
        ).astype(int)

    suppliers["methodology_variant"] = "shrunk" if use_shrinkage else "naive"
    if use_shrinkage:
        suppliers["confidence_score"] = 0.0
        suppliers["confidence_label"] = "Pending"
    return suppliers


def bootstrap_supplier_scores(
    jobs: pd.DataFrame,
    config: ScoringConfig,
) -> pd.DataFrame:
    grouped_jobs = {
        supplier_id: frame.reset_index(drop=True)
        for supplier_id, frame in jobs.groupby("supplier_id")
    }
    rng = np.random.default_rng(config.random_seed)
    bootstrap_frames: list[pd.DataFrame] = []

    for iteration in range(config.bootstrap_iterations):
        sampled_groups = []
        for supplier_id, group in grouped_jobs.items():
            indices = rng.integers(0, len(group), len(group))
            sampled = group.iloc[indices].copy()
            sampled["supplier_id"] = supplier_id
            sampled_groups.append(sampled)
        sampled_jobs = pd.concat(sampled_groups, ignore_index=True)
        scored = build_scored_supplier_frame(
            sampled_jobs,
            config=config,
            use_shrinkage=True,
        )[["supplier_id", "score_overall"]]
        scored["iteration"] = iteration
        scored["rank_overall"] = scored["score_overall"].rank(
            method="average",
            ascending=False,
        )
        bootstrap_frames.append(scored)

    return pd.concat(bootstrap_frames, ignore_index=True)


def attach_uncertainty(
    suppliers: pd.DataFrame,
    bootstrap_scores: pd.DataFrame,
    config: ScoringConfig,
) -> pd.DataFrame:
    summary = (
        bootstrap_scores.groupby("supplier_id")
        .agg(
            bootstrap_score_p10=("score_overall", lambda series: series.quantile(0.10)),
            bootstrap_score_p50=("score_overall", "median"),
            bootstrap_score_p90=("score_overall", lambda series: series.quantile(0.90)),
            bootstrap_rank_p10=("rank_overall", lambda series: series.quantile(0.10)),
            bootstrap_rank_p50=("rank_overall", "median"),
            bootstrap_rank_p90=("rank_overall", lambda series: series.quantile(0.90)),
            bootstrap_score_std=("score_overall", "std"),
            bootstrap_top_10_share=("rank_overall", lambda series: float((series <= 10).mean())),
        )
        .reset_index()
    )

    suppliers = suppliers.merge(summary, on="supplier_id", how="left")
    suppliers["bootstrap_rank_interval_width"] = (
        suppliers["bootstrap_rank_p90"] - suppliers["bootstrap_rank_p10"]
    )
    suppliers["bootstrap_score_interval_width"] = (
        suppliers["bootstrap_score_p90"] - suppliers["bootstrap_score_p10"]
    )

    supplier_count = max(len(suppliers), 1)
    jobs_factor = (suppliers["jobs_observed"] / config.confidence_jobs_target).clip(0.0, 1.0)
    ratings_factor = (
        suppliers["ratings_observed"] / config.confidence_rating_target
    ).clip(0.0, 1.0)
    comparison_factor = (
        suppliers["comparison_group_suppliers"] / config.confidence_group_supplier_target
    ).clip(0.0, 1.0)
    history_factor = (
        np.log1p(suppliers["historical_job_count_for_supplier"])
        / np.log1p(config.confidence_history_target)
    ).clip(0.0, 1.0)
    rank_stability_factor = (
        1.0 - (suppliers["bootstrap_rank_interval_width"] / supplier_count)
    ).clip(0.0, 1.0)
    score_stability_factor = (
        1.0 - (suppliers["bootstrap_score_interval_width"] / 20.0)
    ).clip(0.0, 1.0)

    suppliers["confidence_score"] = (
        0.30 * jobs_factor
        + 0.10 * ratings_factor
        + 0.10 * comparison_factor
        + 0.10 * history_factor
        + 0.20 * rank_stability_factor
        + 0.20 * score_stability_factor
    )
    suppliers["confidence_label"] = np.select(
        [
            suppliers["confidence_score"] >= 0.72,
            suppliers["confidence_score"] >= 0.52,
        ],
        [
            "High",
            "Medium",
        ],
        default="Low",
    )
    suppliers.loc[
        suppliers["jobs_observed"] <= config.confidence_low_job_cap,
        "confidence_label",
    ] = "Low"
    suppliers.loc[
        (suppliers["jobs_observed"] <= config.confidence_medium_job_cap)
        & (suppliers["confidence_label"] == "High"),
        "confidence_label",
    ] = "Medium"

    suppliers["score_conservative"] = suppliers["bootstrap_score_p10"]
    suppliers["rank_conservative"] = suppliers["score_conservative"].rank(
        method="min",
        ascending=False,
    ).astype(int)

    suppliers = add_explanations(suppliers, config=config)
    suppliers["rank_range"] = suppliers.apply(
        lambda row: f"{max(1, floor(row['bootstrap_rank_p10']))}-{ceil(row['bootstrap_rank_p90'])}",
        axis=1,
    )
    return suppliers.sort_values(
        ["score_overall", "jobs_observed", "supplier_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_market_recommendations(
    suppliers: pd.DataFrame,
    top_k: int = 3,
) -> pd.DataFrame:
    suppliers = suppliers.copy()
    suppliers["confidence_priority"] = suppliers["confidence_label"].map(
        {"High": 2, "Medium": 1, "Low": 0}
    ).fillna(0)
    suppliers["routing_recommendation"] = np.select(
        [
            (suppliers["confidence_label"] == "High")
            & (suppliers["score_conservative"] >= 50.0),
            (suppliers["confidence_label"] == "Medium")
            & (suppliers["score_conservative"] >= 50.0),
            suppliers["score_conservative"] >= 50.0,
        ],
        [
            "Preferred",
            "Consider",
            "Review",
        ],
        default="Fallback",
    )
    suppliers["routing_priority"] = suppliers["routing_recommendation"].map(
        {"Preferred": 3, "Consider": 2, "Review": 1, "Fallback": 0}
    ).fillna(0)

    ranking_columns = ["score_overall", "jobs_observed"]
    ascending = [False, False]
    if "score_conservative" in suppliers.columns:
        ranking_columns = [
            "routing_priority",
            "confidence_priority",
            "score_conservative",
            "score_overall",
            "jobs_observed",
        ]
        ascending = [False, False, False, False, False]

    recommendations = (
        suppliers.sort_values(
            ["category", "region", *ranking_columns],
            ascending=[True, True, *ascending],
        )
        .groupby(["category", "region"], as_index=False, group_keys=False)
        .head(top_k)
        .copy()
    )
    recommendations["market_rank"] = recommendations.groupby(
        ["category", "region"]
    ).cumcount() + 1
    ordered_columns = [
        "category",
        "region",
        "market_rank",
        "supplier_id",
        "score_overall",
        "score_conservative",
        "confidence_label",
        "routing_recommendation",
        "jobs_observed",
        "rank_range",
        "short_explanation",
    ]
    available_columns = [column for column in ordered_columns if column in recommendations.columns]
    return recommendations.loc[:, available_columns]
