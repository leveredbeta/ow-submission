# Methodology

## Framing

I treated this assignment as a supplier-selection problem under limited evidence.

The dataset is large enough to build a reasonable score, but not large enough to justify a naive leaderboard. Many suppliers only appear a handful of times in the sample, some markets are thin, and customer ratings are missing often enough that a simple weighted average would give a false sense of certainty.

So my objective was not to find the most complicated model. It was to build a ranking that I would actually be comfortable putting in front of an ops team.

That led me to four design decisions:
- compare suppliers against the right peers
- shrink sparse observations toward a defensible baseline
- keep performance and confidence separate
- show uncertainty instead of pretending the ranking is exact

## 1. Peer Groups

My preferred comparison unit is `category + region`.

That is the fairest apples-to-apples view for supplier choice. An HVAC supplier in Dallas should be compared with other Dallas HVAC suppliers before being compared with the entire dataset.

I only use the local market as the comparison group when there is enough support:
- at least 4 suppliers
- at least 25 jobs

If a market is thinner than that, I fall back to `category`.

I still keep some local information in the shrinkage baseline. For each metric, I blend the local market mean with the category mean:

`baseline = w * local_mean + (1 - w) * category_mean`

where `w` increases with local market support. This lets me preserve regional signal without letting tiny peer groups dominate the result.

## 2. Score Components

I used six components because they cover the operational trade-offs in the prompt without making the score hard to explain.

| Component | Direction | Weight |
| --- | --- | --- |
| Response time | Lower is better | 20% |
| Completion time | Lower is better | 20% |
| Cost efficiency | Lower is better | 15% |
| NTE compliance | Higher is better | 15% |
| Customer rating | Higher is better | 10% |
| Reopen rate | Lower is better | 20% |

I weighted reopen rate and speed most heavily because a supplier who is cheap but slow, or fast but frequently reopened, is not truly strong in an operations setting.

I kept the weights intentionally simple. I would rather have a transparent weighting scheme I can defend than a more complicated optimization that looks precise but is harder to trust.

## 3. Sparse Data Handling

This is the most important part of the solution.

### Metric-level shrinkage

For each supplier and each metric, I shrink the observed value toward the blended baseline.

- Continuous metrics use a weighted average of the observed value and the baseline.
- Binary metrics use a beta-binomial style update against the baseline rate.
- Customer rating uses the number of observed ratings, not the total number of sampled jobs.

This prevents a supplier with one unusually good sampled job from ranking like a proven top performer.

### Final-score shrinkage

After computing the weighted composite performance score, I shrink the final score back toward `50` when observed support is thin:

`score_overall = 50 + evidence_weight * (score_performance - 50)`

I added this second layer deliberately. In early iterations, metric-level shrinkage alone still allowed some very low-volume suppliers to surface too high. Pulling the final score toward neutral made the leaderboard line up better with the caution I wanted the write-up to express.

## 4. Why I Did Not Use `job_count_for_supplier` As Direct Support

The dataset includes `job_count_for_supplier`, which is clearly informative, but I chose to use it conservatively.

I did **not** treat it as extra pseudo-observations in the performance score.

The reason is simple: I do not have the outcome metrics for those unseen historical jobs. I know the count, but I do not know the response times, completion times, costs, reopen behavior, or customer ratings for the missing history. If I used that field as if it were labeled support, I would be overstating the amount of evidence I actually have.

Instead, I use `job_count_for_supplier` only as a weak experience signal in the confidence label. That lets the system acknowledge that a supplier with broader historical exposure may be less fragile than a completely new supplier, without pretending I observed more outcome data than I really did.

## 5. Standardization And Composite Score

Once the shrunk metric values are computed, I compare each supplier against its selected comparison group.

For every component I produce:
- a standardized contribution used in the weighted composite score
- a percentile-style component score that is easier to read in the final output

I sum the weighted standardized contributions into a latent performance score and map it onto a `0-100` style scale centered at `50`.

Interpretation:
- around `50` means roughly peer-level performance
- above `50` means above-peer performance
- below `50` means below-peer performance

I do not interpret this as a causal measure of supplier quality. It is a comparative operational score based on the observed sample.

## 6. Confidence And Uncertainty

I wanted the output to make a clear distinction between “this supplier looks strong” and “I am confident that signal is real.”

### Bootstrap uncertainty

I bootstrap sampled jobs within each supplier and recompute the ranking repeatedly. That gives me:
- score intervals
- rank intervals
- top-10 inclusion behavior

This is important because the sample is sparse enough that point estimates alone are not trustworthy.

### Confidence label

The final confidence label combines:
- observed job count
- observed rating count
- comparison-group support
- discounted historical experience from `job_count_for_supplier`
- bootstrap rank stability
- bootstrap score stability

I also impose explicit caps:
- suppliers with one or two observed jobs cannot score above `Low` confidence
- suppliers with three or four observed jobs cannot score above `Medium`

I added those caps because I wanted the system behavior to match the narrative. If evidence is genuinely thin, the label should say so clearly.

### Conservative routing view

Alongside the point score, I output a conservative score based on the bootstrap 10th percentile.

This is the number I would reach for when decisions need to be more risk-aware. A supplier can have a solid point score and still deserve caution if the lower bound is weak.

For the market recommendation output, I combine the conservative score with confidence:
- `Preferred` for high-confidence suppliers with a positive conservative score
- `Consider` for medium-confidence suppliers with a positive conservative score
- `Review` for suppliers whose score is positive but evidence is weak
- `Fallback` otherwise

That gives the final output more operational meaning than a flat ranked list.

## 7. Explanations

I generate a short explanation for each supplier from the strongest positive and negative component contributions.

The structure is simple:
- what this supplier does well relative to peers
- what held the score back, if anything
- whether the evidence is limited or rating coverage is missing

I wanted the explanations to be short enough for an ops user to skim, but grounded enough that the ranking does not feel opaque.

## 8. Validation

I validated the solution in five ways.

### Structural checks

The pipeline checks required columns, expected types, and supplier uniqueness by market.

### Behavioral tests

The test suite covers:
- expected output columns
- sparse-data shrinkage
- missing customer ratings
- fallback from tiny local markets to category comparisons
- uncertainty attachment
- the rule that historical supplier volume should not overpower weak observed support

### Naive comparison

I also generate a naive comparison without shrinkage. This makes it easy to show where the more careful methodology materially changes the leaderboard.

### Bootstrap stability

The output includes score intervals, rank intervals, and confidence labels so the ranking is never presented as exact.

### Sensitivity analysis

Finally, I compare the baseline ranking against several reasonable methodology variants:
- lighter shrinkage
- heavier shrinkage
- more local comparison thresholds
- more conservative local comparison thresholds
- quality-heavy weighting
- speed-heavy weighting

This matters because I do not want the final leaderboard to depend entirely on one arbitrary parameter setting.

## 9. Limitations

There are several things this sample does not capture:
- job complexity
- asset age
- urgency mix
- seasonality
- part availability

Because of that:
- a higher cost can reflect harder work, not worse performance
- longer completion time can reflect supply constraints, not poor execution
- reopen rate can still be noisy even after shrinkage

So I would treat this score as a fair operational ranking from limited observed outcomes, not as a complete model of supplier quality.

## 10. What I Would Do Next

With more time or richer data, I would extend this in four directions:
- add job-complexity controls
- add recency weighting so newer performance matters more
- separate routine and emergency supplier scorecards
- backtest whether higher-ranked suppliers actually outperform on future jobs
