from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openwrench_supplier_scoring.config import ScoringConfig
from openwrench_supplier_scoring.data import load_supplier_jobs
from openwrench_supplier_scoring.scoring import (
    attach_uncertainty,
    build_market_recommendations,
    build_scored_supplier_frame,
    bootstrap_supplier_scores,
)
from openwrench_supplier_scoring.validation import (
    build_validation_report_markdown,
    build_validation_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the OpenWrench supplier scoring submission."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT.parent
        / "openwrench_supplier_scoring_sample_500"
        / "openwrench_supplier_scoring_sample_500.csv",
        help="Path to the candidate-facing supplier scoring CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs",
        help="Directory where rankings and validation artifacts will be written.",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=300,
        help="Number of stratified bootstrap iterations for uncertainty estimates.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible bootstrapping.",
    )
    return parser.parse_args()


def write_csv(frame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def write_text(contents: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = ScoringConfig(
        bootstrap_iterations=args.bootstrap_iterations,
        random_seed=args.seed,
    )

    jobs = load_supplier_jobs(args.input)

    scored = build_scored_supplier_frame(jobs, config=config, use_shrinkage=True)
    naive = build_scored_supplier_frame(
        jobs,
        config=config,
        use_shrinkage=False,
        use_evidence_adjustment=False,
    )
    bootstrap_scores = bootstrap_supplier_scores(jobs, config=config)
    scored = attach_uncertainty(scored, bootstrap_scores, config=config)

    rankings_path = args.output_dir / "supplier_rankings.csv"
    market_path = args.output_dir / "market_recommendations.csv"
    validation_json_path = args.output_dir / "validation_summary.json"
    validation_md_path = args.output_dir / "validation_report.md"

    write_csv(scored, rankings_path)
    write_csv(build_market_recommendations(scored), market_path)

    validation_summary = build_validation_summary(
        jobs=jobs,
        scored=scored,
        naive=naive,
        bootstrap_scores=bootstrap_scores,
    )
    write_text(json.dumps(validation_summary, indent=2), validation_json_path)
    write_text(
        build_validation_report_markdown(validation_summary),
        validation_md_path,
    )

    print("Wrote:")
    print(f"  {rankings_path}")
    print(f"  {market_path}")
    print(f"  {validation_json_path}")
    print(f"  {validation_md_path}")
    print()
    print("Top 10 suppliers:")
    display_columns = [
        "rank_overall",
        "supplier_id",
        "category",
        "region",
        "score_overall",
        "confidence_label",
        "jobs_observed",
        "short_explanation",
    ]
    top_ten = scored.loc[:, display_columns].head(10).copy()
    top_ten["score_overall"] = top_ten["score_overall"].round(1)
    print(top_ten.to_string(index=False))


if __name__ == "__main__":
    main()
