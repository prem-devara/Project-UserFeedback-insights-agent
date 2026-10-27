# Classifier scores (eval-labelled)

Model `anthropic:claude-haiku-5-5`, thinking `disabled`, run 2026-10-27T04:23:23+00:00. Compared with my hand labels on 100 reviews.

## Summary

| Metric | Value |
|---|---:|
| Sentiment accuracy | 81% |
| Theme micro F1 | 0.78 |
| Theme macro F1 | 0.77 |
| Theme sets match exactly | 47% |

## Sentiment confusion

Rows are my label, columns are the model's.

| mine \ model | positive | negative | mixed | neutral | total |
|---|---:|---:|---:|---:|---:|
| positive | **20** | 0 | 7 | 0 | 27 |
| negative | 0 | **38** | 1 | 1 | 40 |
| mixed | 0 | 6 | **20** | 0 | 26 |
| neutral | 0 | 3 | 1 | **3** | 7 |

## Themes

Support is my count. ⚠ marks low support (fewer than 10 labels): treat those scores as rough.

| Theme | Support | Model count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| General praise and everyday usefulness (`general_praise`) | 50 | 36 | 0.94 | 0.68 | 0.79 |
| Wrong, unreliable or outdated answers (`answer_quality`) | 18 | 24 | 0.75 | 1.00 | 0.86 |
| Crashes, errors and connectivity (`crashes_errors`) | 15 | 17 | 0.76 | 0.87 | 0.81 |
| Pricing, subscription and usage limits (`pricing_limits`) | 15 | 18 | 0.67 | 0.80 | 0.73 |
| Missing features compared with the web version (`missing_features`) | 14 | 14 | 0.57 | 0.57 | 0.57 |
| Education and homework help (`education`) | 13 | 9 | 1.00 | 0.69 | 0.82 |
| Bias, censorship and privacy concerns (`bias_censorship_privacy`) | 10 | 10 | 0.90 | 0.90 | 0.90 |
| UI, UX and accessibility (`ui_ux`) ⚠ | 9 | 6 | 0.67 | 0.44 | 0.53 |
| Other (`other`) ⚠ | 8 | 6 | 0.67 | 0.50 | 0.57 |
| Image generation and multimodal requests (`image_multimodal`) ⚠ | 7 | 10 | 0.70 | 1.00 | 0.82 |
| Voice chat and audio (`voice`) ⚠ | 7 | 10 | 0.70 | 1.00 | 0.82 |
| Login, sign-up and account problems (`login_account`) ⚠ | 6 | 6 | 1.00 | 1.00 | 1.00 |

Micro: precision 0.79, recall 0.76, F1 0.78. Macro F1 is the plain average over all 12 themes.

Every disagreement is listed in `outputs/disagreements.csv`.
