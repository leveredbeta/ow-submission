# OpenWrench Supplier Scoring Assessment

I approached this take-home as a decision-system design problem, not just a ranking exercise.

The main issue in this dataset is false precision. There are only 500 sampled jobs, many suppliers have very thin coverage in the sample, customer ratings are missing for a meaningful share of rows, and some markets are too small for clean local comparisons. A naive weighted average would produce a leaderboard, but I would not trust it.

So I built a scoring system with three goals:
- compare suppliers against the right peer set
- shrink thin evidence toward a reasonable baseline
- separate point performance from confidence

I also packaged the solution as a small Python project instead of a notebook so it is easy to run, inspect, and extend.

## Primary Deliverables

If I were reviewing this submission quickly, I would open these files first:
- `README.md` for the project overview and how to run it
- `METHODOLOGY.md` for the scoring logic and tradeoffs
- `outputs/supplier_rankings.csv` for the main ranked output
- `outputs/market_recommendations.csv` for the market-level recommendation view
- `outputs/validation_report.md` and `outputs/sensitivity_report.md` for supporting checks

## What I Built

The scoring pipeline evaluates each supplier on six components:
- response time
- completion time
- cost efficiency
- NTE compliance
- customer rating
- reopen rate

The implementation prefers `category + region` comparisons when the local market has enough support. When a market is too thin, it falls back to `category`-level comparisons. Each metric is shrunk toward a blended baseline before scoring, and the final composite score is pulled back toward a neutral midpoint when observed history is limited.

I also added:
- bootstrap-based score and rank intervals
- confidence labels
- a conservative score for more cautious routing decisions
- market-level recommendations with a routing posture (`Preferred`, `Consider`, `Review`, `Fallback`)
- sensitivity analysis so the ranking can be checked against reasonable parameter changes

The full methodology is in [METHODOLOGY.md](./METHODOLOGY.md).

## Repository Layout

```text
problem2_supplier_scoring_submission/
├── README.md
├── METHODOLOGY.md
├── requirements.txt
├── run_submission.py
├── outputs/
│   ├── supplier_rankings.csv
│   ├── market_recommendations.csv
│   ├── validation_report.md
│   └── sensitivity_report.md
├── src/openwrench_supplier_scoring/
│   ├── __init__.py
│   ├── config.py
│   ├── data.py
│   ├── scoring.py
│   ├── sensitivity.py
│   └── validation.py
└── tests/
    └── test_scoring.py
```

## How To Run It

Use Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_submission.py
```

By default, the script reads the sample CSV from the sibling dataset folder in this workspace.

Optional flags:

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

The tests cover:
- expected output columns
- shrinkage of low-volume suppliers
- handling of missing customer ratings
- fallback from tiny local markets to category-level comparisons
- uncertainty attachment
- the rule that historical supplier volume should not override weak observed support

## Output Files

`outputs/supplier_rankings.csv`
- full supplier leaderboard
- point score, conservative score, confidence label, rank range, component scores, and short explanation

`outputs/market_recommendations.csv`
- top market-level recommendations by `category` and `region`
- uses conservative score plus confidence-aware routing posture

`outputs/validation_report.md`
- human-readable validation summary

`outputs/sensitivity_report.md`
- readable summary of the sensitivity analysis

## Notes On Design Choices

- `score_overall` is the main ranking score.
- `score_conservative` is the bootstrap lower-bound score that I would use when routing decisions should be cautious.
- `confidence_label` is intentionally separate from performance. A supplier can look good on the point estimate and still have weak evidence.
- I used `job_count_for_supplier` only as a weak experience signal in confidence. I did not treat it as extra pseudo-observations in the score because the unseen historical jobs do not come with the outcome fields needed for this ranking task.
- The short explanation is generated from the strongest positive and negative component contributions so the output is still readable by a non-technical ops user.
