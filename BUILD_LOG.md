# Build Log

## Data preparation

Script: [`prepare.py`](prepare.py) (pure pandas, no LLM calls). Outputs: [`sample/reviews_sample.csv`](sample/reviews_sample.csv) and [`sample/prep_summary.json`](sample/prep_summary.json).

**Source.** `data/ChatGPT_Reviews.csv`: 196,727 raw reviews, dated 2023-07-25 to 2024-08-23 (2023Q3–2024Q3). Ratings are heavily skewed toward 5★ (150k of 197k).

**Cleaning.**

| Step | Removed | Rows left |
|---|---:|---:|
| Raw | – | 196,727 |
| Empty reviews | 6 | 196,721 |
| Duplicate Review Ids | 3,573 | 193,148 |
| Duplicate texts (case/whitespace normalized) | 73,028 | 120,120 |
| Under 15 words | 88,893 | 31,227 |
| Mostly non-Latin script (< 80% Latin letters) | 372 | 30,855 |
| English-word check (< 2 common English words) | 547 | 30,308 |

- Most reviews are very short. Only ~16% of raw reviews (32,158) have 15+ words, and most of the 73k duplicate texts are short repeats like "good" or "nice app".
- The script filter catches Arabic, Persian, Bengali, Devanagari and similar scripts, but not Latin-script languages. Without a language-detection library, the English-word check covers those (romanized Hindi/Urdu, Tagalog, French, Portuguese).
- The first English word list dropped short English complaints such as "Very very … bad app don't install". I expanded it once (adding very, good, my, of, in, can, don), which cut drops from 823 to 547. Spot checks suggest about 1 in 5 drops is still English. I accepted this, since it's roughly 100 reviews, or 0.3% of the cleaned set.

**Sample.** 1,500 reviews: 500 per rating band (low = 1–2★, mid = 3★, high = 4–5★) and 100 per quarter within each band. Every band × quarter group had enough reviews, so no reallocation was needed. Seed 42. Two runs produce byte-identical output.

**Reweighting.** The sample over-represents low and mid ratings. `prep_summary.json` stores the cleaned set's size per band (low 5,059 / mid 2,168 / high 23,081) and `band_weights` (cleaned ÷ sampled): low 10.12, mid 4.34, high 46.16. Multiply a theme's sampled count by its band weight to estimate its frequency in the full cleaned set. Each high-band review stands for ~46 real ones.

## Theme proposal

Script: [`propose_themes.py`](propose_themes.py) (`anthropic:claude-sonnet-5-5` via aisuite). Outputs: [`themes/proposed_run1.json`](themes/proposed_run1.json), [`themes/proposed_run2.json`](themes/proposed_run2.json), [`themes/comparison.md`](themes/comparison.md). Approved list: [`themes/approved_themes.json`](themes/approved_themes.json).

**Eval set held out first.** 200 of the 1,500 sampled reviews, stratified by rating band and quarter (13–14 per group, seed 42), are saved to [`eval/eval_ids.json`](eval/eval_ids.json) and never shown to the model during theme proposal. If the file exists, the script checks that a fresh draw matches it, and stops if it doesn't.

**Two non-overlapping slices.** From the remaining 1,300, two slices of 200 (67 low / 67 mid / 66 high, spread across quarters) were drawn with seeds 42 and 43. The second slice was drawn from what the first left, so the runs share no reviews. Each run asked for 8–15 themes (always including "Other") with definitions, includes/excludes and 2–3 example reviews. The code validates the JSON shape, the theme count, the presence of "Other", and that every example ID is in that run's slice. Both runs passed on the first try.

**Result.** Run 1 proposed 14 themes and run 2 proposed 13. Even with entirely different reviews, 11 themes (including Other) came out essentially the same in both runs. The differences were in how reliability and interface issues were split, plus one theme unique to each run.

**Decisions** (12 approved themes):

1. **Merged run 1's "Crashes, freezing and app won't open" and "Error messages and connectivity failures", and run 2's "App errors, crashes and unreliability", into "Crashes, errors and connectivity".** Run 1 split crashes from error messages and run 2 didn't. For the user, both mean the app isn't working. One theme avoids a boundary the model itself couldn't settle, which would make labels inconsistent.
2. **Folded "Language and regional support" (run 1 only) into Other.** It appeared in only one run. The data preparation step's English filter also removes most of the reviews where language support matters, so this sample can't measure it reliably.
3. **Folded "Math, LaTeX and formula rendering" (run 2 only) into UI, UX and accessibility.** Raw LaTeX and unreadable formulas are display problems. Wrong math answers stay in "Wrong, unreliable or outdated answers".
4. **Kept "UI, UX and accessibility" separate from performance.** Run 2 mixed speed, design and chat history into one theme. Chat history behavior (not loading, syncing, disappearing) moved to UI. Slowness and lag moved to "Crashes, errors and connectivity", because they're reliability problems rather than design problems.

For the other themes, the approved list uses whichever run's definition was clearer and keeps both runs' includes/excludes. Each theme records `source_runs` and the original `source_themes` it came from.

## Hand labels

Answer key: [`eval/eval_labels.xlsx`](eval/eval_labels.xlsx).

- I hand-labelled 100 eval reviews against the approved themes.
- The sheet holds all 200 held-out eval reviews; I labelled the first 100. The other 100 stay held out and unscored.
- The labels were then checked against the theme definitions with AI assistance. 49 of 100 rows were corrected, mostly wrong or outdated answers and image requests that had been labelled as missing features.
- Every change is listed in the Changes sheet of `eval/eval_labels.xlsx`.
- The "General praise" theme now includes clear praise even when the review also complains, and no longer excludes praise paired with a specific bug or feature request.

**Limitation.** The answer key was partly AI-corrected, so it is not fully independent of the model being evaluated.

## Classifier

Scripts: [`classify.py`](classify.py) (`anthropic:claude-haiku-5-5` via aisuite, thinking disabled) and [`score_classifier.py`](score_classifier.py) (no LLM calls). Outputs: [`outputs/scores.md`](outputs/scores.md) (baseline), [`outputs/scores_v2.md`](outputs/scores_v2.md), [`outputs/scores_v2_runs.md`](outputs/scores_v2_runs.md), and a `disagreements*.csv` for each scored run.

**Setup.** Reviews go to the model in batches of 20, shuffled with seed 42 so each batch mixes rating bands. Each batch carries the full approved theme list (definition, includes, excludes). For every review the model returns one or more theme ids and a sentiment (positive, negative, mixed or neutral). "Other" can be combined with other themes, but only for content no other theme covers. The code checks that every review in the batch comes back exactly once with valid theme ids and a valid sentiment, and retries the batch once if not. Scoring compares the model with the 100 hand-labelled eval reviews: sentiment accuracy and a confusion table, per-theme precision, recall and F1, micro and macro F1, and how often the theme sets match exactly. Themes with fewer than 10 hand labels are marked low support (`ui_ux`, `other`, `image_multimodal`, `voice`, `login_account`).

**Fixes (round 1).** The baseline disagreements came mostly from rules that I applied when labelling but that were missing from the prompt:

1. **Praise definition.** The hand labels count praise even when the same review complains, but the theme definition still described "enthusiastic, mostly generic positive reviews". The model tagged praise on 36 reviews against my 50. The `general_praise` definition now reads: "Clear positive statements about ChatGPT or the app, including praise that appears alongside a complaint or request."
2. **Sentiment rules.** The prompt had only a one-line description of "mixed". I added the rules I labelled by:
   - **positive:** praise, or praise plus a wish, with no complaint
   - **negative:** complaints only; negated praise ("not great") is not praise
   - **mixed:** praise plus a real complaint
   - **neutral:** neither praise nor complaint

   Baseline errors were mostly positive reviews called mixed (7) and mixed reviews called negative (6).

| Metric | Baseline (1 run) | v2 (run 1) | v2 mean of 4 runs (min–max) |
|---|---:|---:|---:|
| Sentiment accuracy | 81% | 83% | 81% (79–83%) |
| Theme micro F1 | 0.78 | 0.78 | 0.79 (0.78–0.80) |
| Theme macro F1 | 0.77 | 0.75 | 0.77 (0.75–0.78) |
| Theme sets match exactly | 47% | 50% | 50% (49–52%) |
| `general_praise` F1 (recall) | 0.79 (0.68) | 0.85 (0.80) | 0.84 (0.81–0.86) |
| `missing_features` F1 | 0.57 | 0.53 | 0.60 (0.53–0.62) |
| `ui_ux` F1 | 0.53 | 0.59 | 0.57 (0.50–0.59) |

**Run-to-run spread.** The model doesn't give identical answers on every run. I ran the unchanged v2 prompt 4 times. Sentiment accuracy ranged from 79% to 83%, micro F1 from 0.78 to 0.80 and macro F1 from 0.75 to 0.78. Low-support themes move most, because one review changes their F1 by a lot.
- **Praise:** the gain is the only change clearly larger than this spread. F1 was 0.79 in the baseline and 0.81–0.86 across the v2 runs.
- **Sentiment:** the baseline's 81% equals the v2 mean, so I can't say whether the sentiment rules helped overall. They did reduce positive reviews called mixed (7 → 4 in run 1).
- **Caveat:** the baseline was run only once, so its own spread is unknown.

**No further prompt tuning.** The same 100 reviews are both the answer key and the only scored set. Tuning the prompt to each remaining disagreement would fit it to these labels and overstate accuracy. I stopped after round 1, which only added rules that were already part of how I labelled. The 100 unlabelled eval reviews are still held out.

**Known limitations.**

- **Missing features vs UI/UX.** The model confuses features that exist but display or behave badly (e.g. "the upload button is missing", which I labelled as UI) with features that are absent (e.g. "no copy code button", which I labelled as a missing feature). Across the 4 v2 runs, `missing_features` F1 averaged 0.60 and `ui_ux` 0.57.
- **"Please add X" requests over-tagged as missing features.** The model tags any request as `missing_features`, even when X belongs to another theme: a voice feature (`voice`), Bangla language support (`other`), a newer model (`pricing_limits`).

### Full run (1,500 reviews)

Output: [`outputs/classified_all.csv`](outputs/classified_all.csv) and [`outputs/classified_all_meta.json`](outputs/classified_all_meta.json). This run used the v2 prompt unchanged.

**Two attempts.**
- **First attempt:** stopped at batch 30 of 75. Haiku returned a theme id that isn't in the approved list ("chat_history_placeholder_remove"), both on the first try and on the retry. Validation rejected it, and nothing was saved.
  - The two reviews involved mention chat history. One copies ChatGPT's "As an AI language model…" wording. Neither contains anything that looks like instructions to the model.
- **Second attempt:** no code changes. All 75 batches passed with 0 retries.
- The meta file records only the second attempt.

**Known limitation.** Completed batches aren't saved before a failure, so a failed run has to restart from batch 1.

**Raw counts by rating band.** These are sample counts: 500 reviews per band, with no band weights applied. A review can have several themes (1.74 on average), so the theme columns add up to more than 500. 28 reviews have only `other`.

| Theme | Low (1–2★) | Mid (3★) | High (4–5★) | Total |
|---|---:|---:|---:|---:|
| `general_praise` | 52 | 242 | 453 | 747 |
| `answer_quality` | 144 | 165 | 57 | 366 |
| `crashes_errors` | 133 | 94 | 27 | 254 |
| `missing_features` | 48 | 99 | 48 | 195 |
| `education` | 15 | 44 | 119 | 178 |
| `pricing_limits` | 86 | 53 | 35 | 174 |
| `login_account` | 117 | 21 | 8 | 146 |
| `ui_ux` | 41 | 65 | 28 | 134 |
| `voice` | 40 | 55 | 32 | 127 |
| `image_multimodal` | 28 | 46 | 39 | 113 |
| `bias_censorship_privacy` | 60 | 27 | 7 | 94 |
| `other` | 33 | 29 | 26 | 88 |

| Sentiment | Low | Mid | High | Total |
|---|---:|---:|---:|---:|
| positive | 6 | 31 | 351 | 388 |
| mixed | 54 | 280 | 120 | 454 |
| negative | 434 | 158 | 12 | 604 |
| neutral | 6 | 31 | 17 | 54 |

`missing_features` counts are probably too high, because the model over-tags "please add X" requests (see Known limitations above).
