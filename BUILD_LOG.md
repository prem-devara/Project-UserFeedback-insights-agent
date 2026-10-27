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
