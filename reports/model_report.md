# Baseline model report

Training data: 45 seasons x 10 towns = 450 town-seasons. Validation: leave-one-season-out.

| Metric | Model | No-skill (always 33%) |
|---|---|---|
| Brier score (lower is better) | 0.186 | 0.233 |
| Brier skill score | +0.20 | 0 |
| ROC AUC | 0.78 | 0.50 |

## Reliability (held-out predictions)

| Predicted chance | Town-seasons | Mean predicted | Actually below normal |
|---|---|---|---|
| < 25% | 194.0 | 16% | 13% |
| 25-45% | 114.0 | 34% | 39% |
| > 45% | 142.0 | 67% | 66% |

## Outlook for 2026/27 (latest ONI, JAS 2026 = +2.16°C)

| Province | Chance of below-normal rainfall |
|---|---|
| Matabeleland South | 95% |
| Masvingo | 94% |
| Matabeleland North | 94% |
| Harare | 93% |
| Bulawayo | 93% |
| Manicaland | 93% |
| Mashonaland Central | 93% |
| Mashonaland West | 93% |
| Midlands | 93% |
| Mashonaland East | 92% |

A single climate index explains only part of the rainfall story. Treat this as a baseline to beat, not a forecast to act on.
