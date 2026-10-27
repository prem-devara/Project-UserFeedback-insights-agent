# Classifier scores (eval-labelled)

Model `anthropic:claude-haiku-5-5`, thinking `disabled`, run 2026-10-27T04:35:06+00:00. Compared with my hand labels on 100 reviews.

## Summary

| Metric | Value |
|---|---:|
| Sentiment accuracy | 83% |
| Theme micro F1 | 0.78 |
| Theme macro F1 | 0.75 |
| Theme sets match exactly | 50% |

## Sentiment confusion

Rows are my label, columns are the model's.

| mine \ model | positive | negative | mixed | neutral | total |
|---|---:|---:|---:|---:|---:|
| positive | **21** | 0 | 4 | 2 | 27 |
| negative | 0 | **37** | 2 | 1 | 40 |
| mixed | 0 | 4 | **22** | 0 | 26 |
| neutral | 0 | 2 | 2 | **3** | 7 |

## Themes

Support is my count. ⚠ marks low support (fewer than 10 labels): treat those scores as rough.

| Theme | Support | Model count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| General praise and everyday usefulness (`general_praise`) | 50 | 44 | 0.91 | 0.80 | 0.85 |
| Wrong, unreliable or outdated answers (`answer_quality`) | 18 | 24 | 0.75 | 1.00 | 0.86 |
| Crashes, errors and connectivity (`crashes_errors`) | 15 | 19 | 0.68 | 0.87 | 0.76 |
| Pricing, subscription and usage limits (`pricing_limits`) | 15 | 17 | 0.71 | 0.80 | 0.75 |
| Missing features compared with the web version (`missing_features`) | 14 | 16 | 0.50 | 0.57 | 0.53 |
| Education and homework help (`education`) | 13 | 11 | 0.91 | 0.77 | 0.83 |
| Bias, censorship and privacy concerns (`bias_censorship_privacy`) | 10 | 9 | 0.89 | 0.80 | 0.84 |
| UI, UX and accessibility (`ui_ux`) ⚠ | 9 | 8 | 0.62 | 0.56 | 0.59 |
| Other (`other`) ⚠ | 8 | 6 | 0.50 | 0.38 | 0.43 |
| Image generation and multimodal requests (`image_multimodal`) ⚠ | 7 | 11 | 0.64 | 1.00 | 0.78 |
| Voice chat and audio (`voice`) ⚠ | 7 | 9 | 0.78 | 1.00 | 0.88 |
| Login, sign-up and account problems (`login_account`) ⚠ | 6 | 7 | 0.86 | 1.00 | 0.92 |

Micro: precision 0.76, recall 0.80, F1 0.78. Macro F1 is the plain average over all 12 themes.

Every disagreement is listed in `outputs/disagreements_v2.csv`.
