# Methodology

## Goal

The goal of this assignment is to rank suppliers in a way that is fair, explainable, and useful for operational decisions.

The main challenge in this dataset is sparse evidence. Many suppliers have only a few sampled jobs, some local markets are thin, and customer ratings are missing for many rows. A naive weighted average would over-rank tiny samples and overstate certainty, so I designed the score to be deliberately conservative.

## 1. Comparison Groups

My preferred comparison group is `category + region`, because that is the fairest apples-to-apples view for supplier choice.

I only use the local market when it has enough support:
- at least 4 suppliers
- at least 25 jobs

If a market is thinner than that, I fall back to `category`.

For shrinkage baselines, I still keep some local signal by blending the local market mean with the category mean.

## 2. Score Components

I score each supplier on six components:

| Component | Direction | Weight |
| --- | --- | --- |
| Response time | Lower is better | 20% |
| Completion time | Lower is better | 20% |
| Cost efficiency | Lower is better | 15% |
| NTE compliance | Higher is better | 15% |
| Customer rating | Higher is better | 10% |
| Reopen rate | Lower is better | 20% |

I weighted reopen rate and speed most heavily because a supplier who is cheap but repeatedly causes follow-up work is not truly strong in an operations context.

## 3. Sparse-Data Adjustment

This is the most important part of the solution.

For each metric, I shrink the observed supplier value toward a blended peer baseline:
- continuous metrics use a weighted mean against the baseline
- binary metrics use a beta-binomial style update
- customer rating uses the number of observed ratings, not total sampled jobs

After combining the components, I also shrink the final score back toward `50` when observed support is thin. This prevents very low-volume suppliers from floating too high in the ranking.

## 4. Why I Did Not Use `job_count_for_supplier` As Direct Support

The dataset includes `job_count_for_supplier`, but I use it conservatively.

I do not treat it as extra pseudo-observations in the performance score because I do not have the outcome metrics for those unseen historical jobs. I know the count, but I do not know their response times, completion times, costs, reopen behavior, or ratings.

Instead, I use `job_count_for_supplier` only as a weak experience signal in the confidence label.

## 5. Composite Score

Once the shrunk metric values are computed, I compare each supplier against its selected peer group. For each component I calculate:
- a standardized contribution used in the weighted composite score
- a percentile-style component score used in the output

The weighted standardized contributions are summed into a latent performance score and mapped onto a `0-100` style scale centered at `50`.

Interpretation:
- around `50` means roughly peer-level performance
- above `50` means above-peer performance
- below `50` means below-peer performance

## 6. Confidence And Uncertainty

I wanted to separate “looks strong” from “is strongly supported by evidence.”

To do that, I bootstrap sampled jobs within each supplier and recompute the ranking repeatedly. This gives:
- score intervals
- rank intervals
- a conservative score based on the bootstrap 10th percentile

The final confidence label combines:
- observed job count
- observed rating count
- comparison-group support
- discounted historical supplier experience
- bootstrap score stability
- bootstrap rank stability

I also cap very small samples:
- 1-2 observed jobs cannot score above `Low` confidence
- 3-4 observed jobs cannot score above `Medium`

## 7. Recommendations

In addition to the full leaderboard, I produce market-level recommendations.

These use the conservative score together with confidence:
- `Preferred` for high-confidence suppliers with a positive conservative score
- `Consider` for medium-confidence suppliers with a positive conservative score
- `Review` when the score is positive but evidence is weak
- `Fallback` otherwise

This keeps the output more operational than a flat ranked list.

## 8. Validation

I validated the solution in four ways:
- structural checks on inputs and expected data types
- behavioral tests for shrinkage, missing ratings, and fallback logic
- bootstrap-based uncertainty reporting
- sensitivity analysis over reasonable changes to shrinkage strength, peer thresholds, and weights

I also compare the final ranking against a naive version without shrinkage so it is easy to see where the more careful methodology changes the leaderboard.

## 9. Limitations

This sample does not include job complexity, asset age, urgency mix, seasonality, or part availability. Because of that:
- higher cost can partly reflect harder work
- longer completion time can partly reflect supply constraints
- reopen rate can still be noisy even after shrinkage

So I would treat this score as a fair operational ranking from limited observed outcomes, not as a complete model of supplier quality.

## 10. Next Steps

With more time or richer data, I would add:
- job-complexity controls
- recency weighting
- separate emergency vs routine scorecards
- backtesting on future jobs
