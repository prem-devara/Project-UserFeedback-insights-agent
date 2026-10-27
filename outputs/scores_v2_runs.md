# Classifier v2: run-to-run spread

Same prompt, themes and model (`anthropic:claude-haiku-5-5`, thinking `disabled`) run 4 times on the 100 labelled eval reviews. Run 1 is the committed v2 run (`outputs/scores_v2.md`). Per-run classifications and scores are in `outputs/v2_runs/`. Retried batches per run: 0, 1, 0, 0 (all passed).

## Overall

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Mean | Min–max |
|---|---:|---:|---:|---:|---:|---:|
| Sentiment accuracy | 83% | 81% | 79% | 82% | 81% | 79%–83% |
| Theme micro F1 | 0.78 | 0.79 | 0.79 | 0.80 | 0.79 | 0.78–0.80 |
| Theme macro F1 | 0.75 | 0.77 | 0.77 | 0.78 | 0.77 | 0.75–0.78 |
| Theme sets match exactly | 50% | 52% | 49% | 50% | 50% | 49%–52% |

## Per-theme F1

⚠ marks low support (fewer than 10 hand labels).

| Theme (support) | Run 1 | Run 2 | Run 3 | Run 4 | Mean | Min–max |
|---|---:|---:|---:|---:|---:|---:|
| `general_praise` (50) | 0.85 | 0.86 | 0.81 | 0.82 | 0.84 | 0.81–0.86 |
| `answer_quality` (18) | 0.86 | 0.84 | 0.86 | 0.90 | 0.86 | 0.84–0.90 |
| `crashes_errors` (15) | 0.76 | 0.81 | 0.82 | 0.80 | 0.80 | 0.76–0.82 |
| `pricing_limits` (15) | 0.75 | 0.75 | 0.79 | 0.77 | 0.77 | 0.75–0.79 |
| `missing_features` (14) | 0.53 | 0.62 | 0.62 | 0.62 | 0.60 | 0.53–0.62 |
| `education` (13) | 0.83 | 0.78 | 0.83 | 0.88 | 0.83 | 0.78–0.88 |
| `bias_censorship_privacy` (10) | 0.84 | 0.86 | 0.90 | 0.95 | 0.89 | 0.84–0.95 |
| `ui_ux` (9) ⚠ | 0.59 | 0.50 | 0.59 | 0.59 | 0.57 | 0.50–0.59 |
| `other` (8) ⚠ | 0.43 | 0.50 | 0.43 | 0.43 | 0.45 | 0.43–0.50 |
| `image_multimodal` (7) ⚠ | 0.78 | 0.82 | 0.71 | 0.78 | 0.77 | 0.71–0.82 |
| `voice` (7) ⚠ | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88–0.88 |
| `login_account` (6) ⚠ | 0.92 | 1.00 | 1.00 | 1.00 | 0.98 | 0.92–1.00 |
