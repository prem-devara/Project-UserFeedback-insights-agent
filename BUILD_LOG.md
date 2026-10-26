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
