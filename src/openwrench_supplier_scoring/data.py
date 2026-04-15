from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "work_order_id",
    "supplier_id",
    "category",
    "region",
    "response_time_hours",
    "completion_time_hours",
    "cost_usd",
    "nte_compliance",
    "customer_rating",
    "reopened",
    "job_count_for_supplier",
]


def _coerce_boolean(series: pd.Series, column: str) -> pd.Series:
    mapped = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0})
    )
    if mapped.isna().any():
        bad_values = sorted(series[mapped.isna()].astype(str).unique().tolist())
        raise ValueError(f"Unexpected boolean values in {column}: {bad_values}")
    return mapped


def load_supplier_jobs(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    jobs = pd.read_csv(csv_path)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in jobs.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    for column in [
        "response_time_hours",
        "completion_time_hours",
        "cost_usd",
        "customer_rating",
        "job_count_for_supplier",
    ]:
        jobs[column] = pd.to_numeric(jobs[column], errors="coerce")

    jobs["nte_compliance"] = _coerce_boolean(jobs["nte_compliance"], "nte_compliance")
    jobs["reopened"] = _coerce_boolean(jobs["reopened"], "reopened")

    required_non_null = [
        "work_order_id",
        "supplier_id",
        "category",
        "region",
        "response_time_hours",
        "completion_time_hours",
        "cost_usd",
        "nte_compliance",
        "reopened",
        "job_count_for_supplier",
    ]
    if jobs[required_non_null].isna().any().any():
        missing = jobs[required_non_null].isna().sum()
        missing = missing[missing > 0].to_dict()
        raise ValueError(f"Unexpected nulls in required fields: {missing}")

    if jobs[["supplier_id", "category", "region"]].drop_duplicates()["supplier_id"].nunique() != jobs["supplier_id"].nunique():
        raise ValueError("A supplier_id appears in multiple category/region combinations.")

    return jobs
