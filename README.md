# OpenWrench Supplier Scoring Assessment

This submission implements a fair, explainable supplier ranking system for the OpenWrench data science assessment.

## What The Prompt Asked For

The assessment asked for:
- a supplier scoring methodology
- a Python implementation
- a ranked supplier output with per-supplier scores and short explanations
- a brief methodology document

This submission includes all four.

## Start Here

If I were reviewing this quickly, I would open these files first:
- `METHODOLOGY.md`
- `outputs/supplier_rankings.csv`
- `outputs/market_recommendations.csv`
- `outputs/validation_report.md`

## Approach In Brief

I built the score around three ideas:
- compare suppliers against the right peers
- shrink sparse samples toward a defensible baseline
- separate performance from confidence

The score uses six components:
- response time
- completion time
- cost efficiency
- NTE compliance
- customer rating
- reopen rate

I prefer `category + region` comparisons when the market has enough support and fall back to `category` when it does not. I also add bootstrap-based uncertainty, confidence labels, and a conservative score for more cautious routing decisions.

## How To Run

Use Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_submission.py
```

Optional:

```bash
python run_submission.py \
  --input ../openwrench_supplier_scoring_sample_500/openwrench_supplier_scoring_sample_500.csv \
  --output-dir outputs \
  --bootstrap-iterations 300 \
  --seed 42
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Main Output Files

`outputs/supplier_rankings.csv`
- full supplier leaderboard with scores, confidence, and explanations

`outputs/market_recommendations.csv`
- market-level recommendation view with routing posture

`outputs/validation_report.md`
- short summary of validation checks and uncertainty behavior

`outputs/sensitivity_report.md`
- short summary of ranking robustness under reasonable parameter changes

## Notes

- `score_overall` is the main ranking score.
- `score_conservative` is the bootstrap lower-bound score for cautious routing.
- `confidence_label` is separate from performance.
- `job_count_for_supplier` is used only as a weak confidence signal, not as pseudo-observations in the score.
