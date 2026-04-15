# OpenWrench Supplier Scoring Submission

This project implements a fair, explainable supplier scoring system for the OpenWrench data science assessment.

The solution is designed around four principles:
- compare suppliers against the right peers
- shrink thin-history suppliers toward a neutral baseline
- separate point performance from confidence
- produce outputs that an ops team could actually use

## Project Layout

```text
problem2_supplier_scoring_submission/
├── README.md
├── METHODOLOGY.md
├── requirements.txt
├── run_submission.py
├── outputs/
│   ├── supplier_rankings.csv
│   ├── market_recommendations.csv
│   ├── validation_summary.json
│   └── validation_report.md
├── src/openwrench_supplier_scoring/
│   ├── __init__.py
│   ├── config.py
│   ├── data.py
│   ├── scoring.py
│   └── validation.py
└── tests/
    └── test_scoring.py
```

## Method Summary

The pipeline scores each supplier on six components:
- response time
- completion time
- cost efficiency
- NTE compliance
- customer rating
- reopen rate

The implementation uses `category + region` as the preferred peer group when there is enough local support. When a market is too thin, it falls back to `category` so the ranking is still stable and explainable.

Each component is shrunk toward a blended peer baseline before scoring. That prevents suppliers with one or two jobs from dominating the leaderboard on noise alone. After that, the weighted composite score is itself pulled back toward a neutral score of `50` when observed history is thin. Confidence labels come from bootstrap rank stability, support size, and a discounted historical experience signal from `job_count_for_supplier`.

Full methodology details are in [METHODOLOGY.md](./METHODOLOGY.md).

## Setup

Use Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

By default, the script reads the sample CSV from the sibling dataset folder already present in this workspace.

```bash
python run_submission.py
```

Optional flags:

```bash
python run_submission.py \
  --input ../openwrench_supplier_scoring_sample_500/openwrench_supplier_scoring_sample_500.csv \
  --output-dir outputs \
  --bootstrap-iterations 300 \
  --seed 42
```

## Test

```bash
python -m unittest discover -s tests -v
```

The tests cover:
- required output columns
- shrinkage of low-volume suppliers
- handling of missing customer ratings
- fallback from tiny local markets to category-level comparisons
- bootstrap uncertainty attachment

## Output Files

`outputs/supplier_rankings.csv`
- full supplier leaderboard
- overall score, confidence, rank range, component scores, and short explanation

`outputs/market_recommendations.csv`
- top supplier recommendations by market (`category`, `region`) using conservative score and confidence-aware routing posture

`outputs/validation_summary.json`
- machine-readable validation summary

`outputs/validation_report.md`
- human-readable validation notes

`outputs/sensitivity_analysis.csv`
- ranking robustness under reasonable parameter and weighting changes

`outputs/sensitivity_report.md`
- human-readable sensitivity summary

## Notes

- `score_overall` is the final ranking score. It is intentionally conservative for thin-history suppliers.
- `score_conservative` is the bootstrap lower-bound score intended for more cautious routing decisions.
- `confidence_label` is separate from the score and reflects support plus bootstrap stability.
- `job_count_for_supplier` is used only as a weak confidence signal, not as pseudo-observations in the score.
- `routing_recommendation` in the market output prevents low-confidence suppliers from being presented like clean first-choice routes.
- `short_explanation` is generated from the strongest positive and negative component contributions.
