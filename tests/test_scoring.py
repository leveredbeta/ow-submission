from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openwrench_supplier_scoring.config import ScoringConfig
from openwrench_supplier_scoring.scoring import (
    attach_uncertainty,
    bootstrap_supplier_scores,
    build_scored_supplier_frame,
)


def build_test_frame() -> pd.DataFrame:
    rows = [
        ("WO-1", "SUP-A", "HVAC", "Dallas", 1.0, 8.0, 400.0, 1, 5.0, 0, 100),
        ("WO-2", "SUP-B", "HVAC", "Dallas", 5.0, 24.0, 620.0, 1, 4.4, 0, 20),
        ("WO-3", "SUP-B", "HVAC", "Dallas", 4.0, 26.0, 630.0, 1, 4.5, 0, 20),
        ("WO-4", "SUP-B", "HVAC", "Dallas", 5.0, 25.0, 640.0, 1, 4.4, 0, 20),
        ("WO-5", "SUP-B", "HVAC", "Dallas", 4.0, 23.0, 610.0, 1, 4.5, 0, 20),
        ("WO-6", "SUP-C", "HVAC", "Dallas", 9.0, 35.0, 850.0, 0, 3.5, 1, 25),
        ("WO-7", "SUP-C", "HVAC", "Dallas", 8.0, 38.0, 830.0, 0, 3.0, 1, 25),
        ("WO-8", "SUP-C", "HVAC", "Dallas", 10.0, 32.0, 810.0, 0, 3.5, 0, 25),
        ("WO-9", "SUP-C", "HVAC", "Dallas", 9.0, 36.0, 845.0, 0, None, 1, 25),
        ("WO-10", "SUP-D", "HVAC", "Austin", 6.0, 27.0, 650.0, 1, 4.0, 0, 14),
        ("WO-11", "SUP-D", "HVAC", "Austin", 6.0, 28.0, 640.0, 1, None, 0, 14),
        ("WO-12", "SUP-E", "HVAC", "Austin", 7.0, 28.0, 700.0, 1, 4.1, 0, 14),
        ("WO-13", "SUP-E", "HVAC", "Austin", 7.0, 29.0, 690.0, 1, 4.2, 0, 14),
        ("WO-14", "SUP-F", "Plumbing", "Houston", 4.0, 20.0, 500.0, 1, None, 0, 9),
        ("WO-15", "SUP-G", "Plumbing", "Houston", 8.0, 34.0, 900.0, 0, 3.5, 1, 11),
        ("WO-16", "SUP-H", "Plumbing", "Denver", 5.0, 25.0, 650.0, 1, 4.0, 0, 10),
        ("WO-17", "SUP-I", "Plumbing", "Denver", 7.0, 28.0, 750.0, 1, 3.8, 0, 10),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
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
        ],
    )
    frame["nte_compliance"] = frame["nte_compliance"].astype(float)
    frame["reopened"] = frame["reopened"].astype(float)
    return frame


class SupplierScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = build_test_frame()
        self.config = ScoringConfig(
            bootstrap_iterations=12,
            random_seed=7,
            min_peer_suppliers=4,
            min_peer_jobs=5,
            peer_blend_supplier_target=4,
            peer_blend_job_target=5,
        )

    def test_scored_frame_contains_expected_columns(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        required_columns = {
            "supplier_id",
            "category",
            "region",
            "score_overall",
            "rank_overall",
            "comparison_level",
            "response_time_hours_component_score",
            "reopened_component_score",
        }
        self.assertTrue(required_columns.issubset(scored.columns))
        self.assertEqual(len(scored), self.jobs["supplier_id"].nunique())

    def test_shrinkage_pulls_low_volume_supplier_toward_peer_baseline(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        naive = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=False)

        shrunk_score = float(scored.loc[scored["supplier_id"] == "SUP-A", "score_overall"].iloc[0])
        naive_score = float(naive.loc[naive["supplier_id"] == "SUP-A", "score_overall"].iloc[0])
        self.assertLess(shrunk_score, naive_score)

    def test_missing_ratings_do_not_break_scoring(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        supplier = scored.loc[scored["supplier_id"] == "SUP-F"].iloc[0]
        self.assertEqual(int(supplier["ratings_observed"]), 0)
        self.assertFalse(pd.isna(supplier["customer_rating_shrunk"]))
        self.assertFalse(pd.isna(supplier["score_overall"]))

    def test_small_local_market_falls_back_to_category_comparison(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        supplier = scored.loc[scored["supplier_id"] == "SUP-H"].iloc[0]
        self.assertEqual(supplier["comparison_level"], "category")

    def test_bootstrap_uncertainty_attaches_confidence(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        bootstrap_scores = bootstrap_supplier_scores(self.jobs, config=self.config)
        scored = attach_uncertainty(scored, bootstrap_scores, config=self.config)
        supplier = scored.loc[scored["supplier_id"] == "SUP-B"].iloc[0]
        self.assertIn(supplier["confidence_label"], {"High", "Medium", "Low"})
        self.assertLessEqual(supplier["bootstrap_rank_p10"], supplier["bootstrap_rank_p90"])
        self.assertGreaterEqual(supplier["confidence_score"], 0.0)
        self.assertLessEqual(supplier["confidence_score"], 1.0)

    def test_historical_volume_does_not_override_low_observed_support(self) -> None:
        scored = build_scored_supplier_frame(self.jobs, config=self.config, use_shrinkage=True)
        bootstrap_scores = bootstrap_supplier_scores(self.jobs, config=self.config)
        scored = attach_uncertainty(scored, bootstrap_scores, config=self.config)
        supplier = scored.loc[scored["supplier_id"] == "SUP-A"].iloc[0]
        self.assertEqual(int(supplier["historical_job_count_for_supplier"]), 100)
        self.assertEqual(int(supplier["jobs_observed"]), 1)
        self.assertEqual(supplier["confidence_label"], "Low")


if __name__ == "__main__":
    unittest.main()
