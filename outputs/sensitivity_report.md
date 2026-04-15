# Sensitivity Analysis

This report compares the baseline ranking against several reasonable methodology variants.
The goal is to show that the leaderboard is not purely an artifact of one arbitrary parameter setting.

## baseline
- Top-10 overlap vs baseline: 10/10
- Top-5 overlap vs baseline: 5/5
- Spearman rank correlation vs baseline: 1.0
- Mean absolute rank shift: 0.0
- Max absolute rank shift: 0

## heavier_shrinkage
- Top-10 overlap vs baseline: 10/10
- Top-5 overlap vs baseline: 3/5
- Spearman rank correlation vs baseline: 0.9949
- Mean absolute rank shift: 1.171
- Max absolute rank shift: 10

## lighter_shrinkage
- Top-10 overlap vs baseline: 10/10
- Top-5 overlap vs baseline: 5/5
- Spearman rank correlation vs baseline: 0.9986
- Mean absolute rank shift: 0.657
- Max absolute rank shift: 4

## more_conservative_local_comparison
- Top-10 overlap vs baseline: 7/10
- Top-5 overlap vs baseline: 4/5
- Spearman rank correlation vs baseline: 0.8927
- Mean absolute rank shift: 5.114
- Max absolute rank shift: 37
- Baseline top-10 suppliers moved out: SUP-001, SUP-017, SUP-026
- Suppliers moved into the top 10: SUP-041, SUP-052, SUP-061

## more_local_comparison
- Top-10 overlap vs baseline: 9/10
- Top-5 overlap vs baseline: 4/5
- Spearman rank correlation vs baseline: 0.8595
- Mean absolute rank shift: 5.429
- Max absolute rank shift: 39
- Baseline top-10 suppliers moved out: SUP-030
- Suppliers moved into the top 10: SUP-039

## quality_emphasis
- Top-10 overlap vs baseline: 8/10
- Top-5 overlap vs baseline: 3/5
- Spearman rank correlation vs baseline: 0.9367
- Mean absolute rank shift: 4.743
- Max absolute rank shift: 23
- Baseline top-10 suppliers moved out: SUP-014, SUP-056
- Suppliers moved into the top 10: SUP-029, SUP-061

## speed_emphasis
- Top-10 overlap vs baseline: 8/10
- Top-5 overlap vs baseline: 4/5
- Spearman rank correlation vs baseline: 0.9834
- Mean absolute rank shift: 2.486
- Max absolute rank shift: 12
- Baseline top-10 suppliers moved out: SUP-001, SUP-026
- Suppliers moved into the top 10: SUP-029, SUP-057
