# Validation Report

## Coverage
- Input rows: 500
- Suppliers scored: 70
- Missing customer-rating rows: 97
- Suppliers with no ratings: 2
- Suppliers with <=3 observed jobs: 24
- Suppliers with <=5 observed jobs: 41

## Comparison Levels
- category: 38
- category_region: 32

## Confidence Labels
- Low: 25
- Medium: 23
- High: 22

## Stability
- Top-10 overlap with naive ranking: 6
- Median bootstrap rank interval width: 18.05
- Median bootstrap score interval width: 4.319

## Largest Shrinkage Examples
- SUP-055 (General, Dallas): score 46.921 vs naive 38.567, rank 58 vs naive 70
- SUP-003 (HVAC, Orlando): score 52.281 vs naive 59.655, rank 18 vs naive 2
- SUP-033 (Electrical, Dallas): score 50.517 vs naive 57.476, rank 31 vs naive 4
- SUP-064 (Doors, Orlando): score 48.155 vs naive 43.789, rank 52 vs naive 60
- SUP-008 (HVAC, Dallas): score 50.36 vs naive 54.476, rank 35 vs naive 15
- SUP-068 (Pool, Phoenix): score 55.605 vs naive 59.513, rank 4 vs naive 3
- SUP-004 (HVAC, Dallas): score 45.98 vs naive 42.152, rank 60 vs naive 67
- SUP-016 (Plumbing, Charlotte): score 46.529 vs naive 42.716, rank 59 vs naive 64

## Top Suppliers
- #1 SUP-023 (Plumbing, Houston) score 60.116 [High] across 14 jobs
- #2 SUP-030 (Electrical, Phoenix) score 56.848 [High] across 11 jobs
- #3 SUP-014 (HVAC, Dallas) score 56.494 [High] across 12 jobs
- #4 SUP-068 (Pool, Phoenix) score 55.605 [Medium] across 4 jobs
- #5 SUP-056 (General, Dallas) score 55.214 [High] across 7 jobs
- #6 SUP-017 (Plumbing, Charlotte) score 55.2 [High] across 13 jobs
- #7 SUP-047 (General, Atlanta) score 55.007 [Medium] across 7 jobs
- #8 SUP-026 (Plumbing, Denver) score 54.935 [High] across 22 jobs
- #9 SUP-062 (Doors, Orlando) score 54.53 [Medium] across 5 jobs
- #10 SUP-001 (HVAC, Dallas) score 54.308 [Medium] across 5 jobs
