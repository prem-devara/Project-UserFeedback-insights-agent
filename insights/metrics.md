# Review insights: weighted estimates

Estimates for all 30,308 cleaned reviews, from a stratified sample of 1,500 classified reviews weighted back to the cleaned counts.

> **95% intervals come from a bootstrap (1,000 resamples within each band x quarter cell, seed 42). They cover sampling error only, not classifier error: theme labels themselves are imperfect (see BUILD_LOG.md).**

- A review can have several themes, so theme shares add up to more than 100%.
- Complaint reviews are those with sentiment negative or mixed. About 13,014 cleaned reviews (1058 sampled).
- 1–2 star reviews: 5,059 cleaned (500 sampled).

## Ranked complaint themes

| Rank | Theme | Share of complaint reviews (95% CI) |
|---:|---|---|
| 1 | `answer_quality` | 30.8% (26.8%–35.2%) |
| 2 | `crashes_errors` | 20.4% (17.4%–23.7%) |
| 3 | `missing_features` † | 16.6% (13.0%–20.1%) |
| 4 | `pricing_limits` | 15.3% (12.3%–18.8%) |
| 5 | `image_multimodal` | 13.4% (10.0%–16.9%) |
| 6 | `login_account` | 11.4% (9.4%–13.8%) |
| 7 | `ui_ux` | 10.8% (8.2%–13.5%) |
| 8 | `voice` | 10.8% (8.0%–14.1%) |
| 9 | `education` | 7.5% (4.9%–10.5%) |
| 10 | `bias_censorship_privacy` | 7.1% (5.3%–9.1%) |
| – | `general_praise` | 49.9% (45.2%–53.9%) — not a complaint theme |
| – | `other` | 3.9% (2.7%–5.4%) — not a complaint theme |

† missing_features is likely over-counted: the classifier tags any 'please add X' request as missing_features, even when X belongs to another theme (known limitation, see BUILD_LOG.md).

general_praise and other appear in the tables but are left out of the complaint ranking because they are not complaint themes.

## Sentiment distribution

| Sentiment | Share of reviews (95% CI) |
|---|---|
| positive | 53.9% (51.0%–57.3%) |
| negative | 18.6% (17.4%–19.9%) |
| mixed | 24.4% (21.2%–27.2%) |
| neutral | 3.1% (2.0%–4.4%) |

## Theme shares

| Theme | All reviews | Complaint reviews | 1–2 star reviews |
|---|---|---|---|
| `answer_quality` | 15.8% (13.5%–18.3%) | 30.8% (26.8%–35.2%) | 29.0% (24.8%–33.0%) |
| `bias_censorship_privacy` | 3.3% (2.5%–4.3%) | 7.1% (5.3%–9.1%) | 11.8% (9.0%–14.8%) |
| `crashes_errors` | 10.0% (8.5%–11.8%) | 20.4% (17.4%–23.7%) | 27.3% (23.1%–31.1%) |
| `education` | 19.3% (16.5%–22.5%) | 7.5% (4.9%–10.5%) | 3.0% (1.6%–4.5%) |
| `general_praise` | 74.3% (72.2%–76.4%) | 49.9% (45.2%–53.9%) | 10.6% (7.9%–13.3%) |
| `image_multimodal` | 7.8% (6.0%–9.8%) | 13.4% (10.0%–16.9%) | 5.6% (3.6%–7.7%) |
| `login_account` | 5.4% (4.4%–6.5%) | 11.4% (9.4%–13.8%) | 22.5% (19.0%–26.1%) |
| `missing_features` | 10.2% (8.2%–12.3%) | 16.6% (13.0%–20.1%) | 9.6% (7.0%–12.3%) |
| `other` | 5.7% (4.1%–7.4%) | 3.9% (2.7%–5.4%) | 6.4% (4.4%–8.7%) |
| `pricing_limits` | 9.1% (7.2%–11.2%) | 15.3% (12.3%–18.8%) | 17.6% (14.3%–21.2%) |
| `ui_ux` | 6.6% (5.0%–8.1%) | 10.8% (8.2%–13.5%) | 8.9% (6.4%–11.5%) |
| `voice` | 6.9% (5.2%–8.7%) | 10.8% (8.0%–14.1%) | 8.4% (6.0%–11.0%) |

## Quarterly trend: share of complaint reviews

2023Q3 and 2024Q3 are partial quarters (2023Q3: data starts 2023-07-25; 2024Q3: data ends 2024-08-23). Trend changes compare the first and last full quarters (2023Q4 vs 2024Q2).

| Theme | 2023Q3 (partial) | 2023Q4 | 2024Q1 | 2024Q2 | 2024Q3 (partial) | Changed? |
|---|---|---|---|---|---|---|
| `answer_quality` | 21.8% (14.5%–29.8%) | 36.1% (26.4%–45.7%) | 33.7% (24.0%–42.7%) | 31.5% (23.0%–40.9%) | 32.2% (23.5%–42.0%) | no |
| `bias_censorship_privacy` | 9.6% (5.8%–15.0%) | 9.7% (4.3%–17.2%) | 6.0% (3.5%–9.1%) | 5.4% (2.3%–9.8%) | 5.9% (2.4%–10.7%) | no |
| `crashes_errors` | 18.4% (11.5%–26.1%) | 19.0% (11.8%–27.7%) | 18.8% (13.1%–26.3%) | 23.9% (16.9%–31.9%) | 19.5% (13.8%–26.6%) | no |
| `education` | 4.3% (0.7%–9.6%) | 10.1% (3.4%–17.8%) | 9.2% (2.9%–16.2%) | 5.7% (1.6%–11.0%) | 10.1% (4.0%–17.5%) | no |
| `general_praise` | 51.0% (41.1%–58.7%) | 41.2% (31.0%–50.8%) | 56.0% (46.7%–63.8%) | 49.7% (39.5%–57.4%) | 49.4% (38.8%–57.0%) | no |
| `image_multimodal` | 3.6% (0.2%–8.7%) | 11.3% (4.3%–19.5%) | 17.2% (9.1%–26.3%) | 17.4% (9.2%–26.2%) | 14.9% (7.8%–22.7%) | no |
| `login_account` | 20.1% (15.3%–26.4%) | 11.8% (8.2%–16.3%) | 10.8% (6.4%–16.3%) | 9.1% (4.5%–15.1%) | 5.5% (2.0%–10.4%) | no |
| `missing_features` | 25.0% (16.7%–33.6%) | 15.2% (7.3%–23.6%) | 15.8% (8.3%–24.8%) | 12.3% (6.2%–19.5%) | 16.6% (9.1%–25.0%) | no |
| `other` | 5.6% (1.6%–10.7%) | 4.7% (2.4%–7.4%) | 4.2% (1.1%–8.5%) | 2.7% (1.1%–4.9%) | 3.1% (1.3%–5.3%) | no |
| `pricing_limits` | 8.1% (2.7%–15.0%) | 12.5% (6.7%–18.7%) | 9.8% (5.9%–15.1%) | 21.1% (14.1%–29.3%) | 22.8% (15.1%–30.8%) | no |
| `ui_ux` | 18.8% (11.2%–26.3%) | 10.7% (5.7%–16.8%) | 6.9% (1.6%–13.3%) | 12.0% (6.6%–18.2%) | 3.6% (1.8%–6.1%) | no |
| `voice` | 3.0% (0.6%–7.3%) | 14.7% (7.9%–23.2%) | 15.7% (7.9%–25.1%) | 13.2% (7.0%–21.3%) | 6.1% (2.7%–11.0%) | no |

"Changed" means the 2023Q4 and 2024Q2 intervals do not overlap.

## Weights

Each sampled review counts as this many cleaned reviews (cleaned ÷ sampled in its cell).

| Band | 2023Q3 | 2023Q4 | 2024Q1 | 2024Q2 | 2024Q3 |
|---|---:|---:|---:|---:|---:|
| low | 9.54 | 7.76 | 9.65 | 14.65 | 8.99 |
| mid | 4.17 | 3.41 | 4.09 | 6.42 | 3.59 |
| high | 41.37 | 38.61 | 46.21 | 66.79 | 37.83 |
