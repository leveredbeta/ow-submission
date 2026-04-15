# Methodology

## Objective

The goal is to rank suppliers in a way that is fair enough to trust, simple enough to explain, and stable enough to use in operational routing decisions.

The main risk in this dataset is not model complexity. It is false precision. Many suppliers have very few observed jobs, some peer groups are thin, and customer ratings are missing for a meaningful share of the data. A naive weighted average would over-rank tiny samples and overstate certainty.

## 1. Fair Comparison Groups

The preferred peer group is `category + region`, because that is the fairest apples-to-apples comparison for supplier selection.

That local comparison is only used when the market has enough support:
- at least 4 suppliers
- at least 25 jobs

If the local market is thinner than that, the scoring system falls back to `category`-level comparisons. This avoids unstable rankings driven by one or two suppliers in a tiny region.

For shrinkage baselines, the method still uses local information through a blend:

`baseline = w * (category-region mean) + (1 - w) * (category mean)`

where `w` grows with local market support. This preserves regional signal without overreacting to tiny peer groups.

## 2. Component Metrics

Each supplier is scored on six interpretable components:

| Component | Direction | Weight |
| --- | --- | --- |
| Response time | Lower is better | 20% |
| Completion time | Lower is better | 20% |
| Cost efficiency | Lower is better | 15% |
| NTE compliance | Higher is better | 15% |
| Customer rating | Higher is better | 10% |
| Reopen rate | Lower is better | 20% |

These weights are intentionally simple. Reopen rate and speed carry the most influence because a supplier that is cheap or highly rated but repeatedly fails jobs should not rank as top-tier.

## 3. Sparse-Data Adjustment

### Metric-level shrinkage

Each metric is pulled toward its blended baseline before ranking:
- continuous metrics use a weighted mean between the supplier estimate and the baseline
- binary metrics use a beta-binomial style update against the baseline rate
- customer rating uses the number of observed ratings rather than total jobs

This means a supplier with 1 excellent job does not rank as confidently as a supplier with 20 strong jobs.

### Final-score shrinkage

After combining the components, the composite score is also shrunk back toward a neutral score of `50` based on observed job count:

`score_overall = 50 + evidence_weight * (score_performance - 50)`

This extra step is deliberate. It prevents low-volume suppliers from surfacing too high even when a few component metrics still look strong after metric-level shrinkage.

## 4. Standardization and Composite Score

For each supplier, shrunk component values are compared against the chosen comparison group. The system computes:
- a standardized contribution for the weighted composite score
- a percentile-style component score for human-readable output

The weighted standardized contributions are summed into a latent performance score, then mapped to a `0-100` style scale centered at `50`.

Interpretation:
- around `50` means near-peer performance
- meaningfully above `50` means above-peer performance
- meaningfully below `50` means below-peer performance

## 5. Confidence and Uncertainty

Point estimates alone are not enough for supplier ranking, so the submission adds uncertainty in two ways.

### Stratified bootstrap

The pipeline resamples jobs within each supplier multiple times and recomputes the full ranking. This produces:
- score intervals
- rank intervals
- top-10 inclusion frequency

### Confidence labels

The final confidence label combines:
- observed job count
- observed rating count
- comparison-group support
- bootstrap rank stability
- bootstrap score stability

Suppliers with one or two jobs are explicitly capped at `Low` confidence. Suppliers with three or four jobs can be at most `Medium`.

## 6. Explanations

Each supplier gets a short explanation generated from the strongest positive and negative component contributions.

Example structure:
- strongest strengths relative to peers
- main weakness if material
- caveat when rating data is missing or evidence is limited

This keeps the output useful for non-technical stakeholders.

## 7. Validation

The implementation validates the scoring system in four ways:

1. Structural checks
The pipeline verifies required columns, types, and supplier uniqueness by market.

2. Sparse-data checks
Tests confirm that low-volume suppliers are pulled toward baseline rather than dominating the ranking.

3. Fallback checks
Tests confirm that tiny local peer groups fall back to category-level comparisons.

4. Stability checks
Bootstrap intervals and confidence labels are written to the output so the ranking is never presented as exact.

The repository also includes a naive comparison run without shrinkage so it is easy to see where the robust methodology materially changes the ranking.

## 8. Limitations

This sample does not include job complexity, asset age, customer priority, or seasonality. Because of that:
- cost may partly reflect harder jobs rather than worse supplier performance
- completion time may be affected by part availability
- reopen rate can be noisy for low-volume suppliers even after shrinkage

The current score is therefore best interpreted as a fair operational ranking from limited observed outcomes, not as a causal estimate of supplier quality.

## 9. Production-Ready Improvements

With more time or data, I would add:
- job complexity controls
- time-decay weighting so recent performance matters more
- separate emergency vs. routine supplier scorecards
- richer calibration of uncertainty thresholds with business feedback
- backtesting on future jobs to see whether top-ranked suppliers actually outperform
