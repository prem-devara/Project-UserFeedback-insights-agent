"""Clean the ChatGPT reviews dataset and draw a stratified, reproducible sample.

Pure pandas, no LLM calls. Writes:
  sample/reviews_sample.csv  - 500 reviews per rating band, spread across quarters
  sample/prep_summary.json   - counts per cleaning step, cleaned band sizes, seed
"""

import json
import re
from pathlib import Path

import pandas as pd

SEED = 42
PER_BAND = 500
MIN_WORDS = 15
LATIN_THRESHOLD = 0.8
MIN_ENGLISH_HITS = 2
ENGLISH_WORDS = frozenset(
    [
        "the", "and", "is", "it", "to", "a", "i", "this", "not", "app", "but", "you", "for", "with",
        "very", "good", "my", "of", "in", "can", "don",
    ]
)
N_EXAMPLES = 5

INPUT_PATH = Path("data/ChatGPT_Reviews.csv")
OUTPUT_DIR = Path("sample")
SAMPLE_PATH = OUTPUT_DIR / "reviews_sample.csv"
SUMMARY_PATH = OUTPUT_DIR / "prep_summary.json"

DATE_FORMAT = "%m/%d/%Y %H:%M"
BANDS = ["low", "mid", "high"]
WORD_RE = re.compile(r"[a-z]+")


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"Review Id": str, "Review": str})


def latin_share(text: str) -> float:
    """Share of alphabetic characters that are Latin script (ASCII + U+00C0-U+024F)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    latin = sum(1 for c in letters if c.isascii() or "À" <= c <= "ɏ")
    return latin / len(letters)


def english_hits(text: str) -> int:
    """Number of distinct common English words present in the text."""
    return len(ENGLISH_WORDS.intersection(WORD_RE.findall(text.lower())))


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], dict[str, pd.Series]]:
    steps = [{"step": "raw", "rows": len(df), "removed": 0}]
    dropped_examples = {}

    def record(name: str, before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
        steps.append({"step": name, "rows": len(after), "removed": len(before) - len(after)})
        return after

    text = df["Review"].fillna("").str.strip()
    df = record("drop_empty", df, df[text != ""])

    df = record("drop_duplicate_ids", df, df.drop_duplicates(subset="Review Id", keep="first"))

    normalized = df["Review"].str.lower().str.split().str.join(" ")
    df = record("drop_duplicate_texts", df, df[~normalized.duplicated(keep="first")])

    word_counts = df["Review"].str.split().str.len()
    df = record(f"drop_under_{MIN_WORDS}_words", df, df[word_counts >= MIN_WORDS])

    is_latin = df["Review"].map(latin_share) >= LATIN_THRESHOLD
    dropped_examples["drop_non_latin"] = df.loc[~is_latin, "Review"]
    df = record("drop_non_latin", df, df[is_latin])

    is_english = df["Review"].map(english_hits) >= MIN_ENGLISH_HITS
    dropped_examples["drop_non_english"] = df.loc[~is_english, "Review"]
    df = record("drop_non_english", df, df[is_english])

    return df, steps, dropped_examples


def add_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rating_band"] = pd.cut(df["Ratings"], bins=[0, 2, 3, 5], labels=BANDS).astype(str)
    dates = pd.to_datetime(df["Review Date"], format=DATE_FORMAT)
    df["quarter"] = dates.dt.to_period("Q").astype(str)
    return df


def allocate(available: dict[str, int], total: int) -> dict[str, int]:
    """Split `total` evenly across quarters; quarters that run short pass the remainder on."""
    alloc = {q: 0 for q in available}
    open_quarters = sorted(q for q, n in available.items() if n > 0)
    remaining = total
    while remaining > 0 and open_quarters:
        share, extra = divmod(remaining, len(open_quarters))
        for i, q in enumerate(open_quarters):
            alloc[q] += min(share + (1 if i < extra else 0), available[q] - alloc[q])
        remaining = total - sum(alloc.values())
        open_quarters = [q for q in open_quarters if alloc[q] < available[q]]
    return alloc


def stratified_sample(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for band in BANDS:
        band_df = df[df["rating_band"] == band]
        available = band_df["quarter"].value_counts().to_dict()
        alloc = allocate(available, PER_BAND)
        for quarter, n in sorted(alloc.items()):
            if n > 0:
                group = band_df[band_df["quarter"] == quarter]
                parts.append(group.sample(n=n, random_state=SEED))
    sample = pd.concat(parts)
    sample["rating_band"] = pd.Categorical(sample["rating_band"], categories=BANDS, ordered=True)
    sample = sample.sort_values(["rating_band", "quarter", "Review Id"]).reset_index(drop=True)
    sample["rating_band"] = sample["rating_band"].astype(str)
    return sample


def band_quarter_counts(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    table = pd.crosstab(df["rating_band"], df["quarter"]).reindex(BANDS, fill_value=0)
    return {band: {q: int(n) for q, n in row.items()} for band, row in table.iterrows()}


def write_outputs(cleaned: pd.DataFrame, sample: pd.DataFrame, steps: list[dict]) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    sample.to_csv(SAMPLE_PATH, index=False)

    cleaned_by_band = {b: int((cleaned["rating_band"] == b).sum()) for b in BANDS}
    sample_by_band = {b: int((sample["rating_band"] == b).sum()) for b in BANDS}
    summary = {
        "seed": SEED,
        "input_file": str(INPUT_PATH),
        "params": {
            "per_band": PER_BAND,
            "min_words": MIN_WORDS,
            "latin_threshold": LATIN_THRESHOLD,
            "min_english_hits": MIN_ENGLISH_HITS,
            "english_words": sorted(ENGLISH_WORDS),
        },
        "cleaning_steps": steps,
        "cleaned_total": len(cleaned),
        "cleaned_by_band": cleaned_by_band,
        "cleaned_by_band_quarter": band_quarter_counts(cleaned),
        "sample_total": len(sample),
        "sample_by_band": sample_by_band,
        "sample_by_band_quarter": band_quarter_counts(sample),
        # Multiply a sampled theme count by its band's weight to estimate the full-set count.
        "band_weights": {b: cleaned_by_band[b] / sample_by_band[b] for b in BANDS if sample_by_band[b]},
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def print_summary(summary: dict, dropped_examples: dict[str, pd.Series]) -> None:
    print("Cleaning steps")
    print(pd.DataFrame(summary["cleaning_steps"]).to_string(index=False))

    for step, reviews in dropped_examples.items():
        print(f"\n{step}: {N_EXAMPLES} dropped examples (of {len(reviews)})")
        for text in reviews.sample(n=min(N_EXAMPLES, len(reviews)), random_state=SEED):
            print(f"  - {text[:200]!r}")

    cleaned = pd.DataFrame(summary["cleaned_by_band_quarter"]).T
    sampled = pd.DataFrame(summary["sample_by_band_quarter"]).T
    table = cleaned.astype(str) + " / " + sampled.astype(str)
    table["total"] = [
        f"{summary['cleaned_by_band'][b]} / {summary['sample_by_band'][b]}" for b in table.index
    ]
    print("\nCleaned / sampled by band and quarter")
    print(table.to_string())
    print(f"\nSeed {summary['seed']}. Wrote {SAMPLE_PATH} ({summary['sample_total']} rows) and {SUMMARY_PATH}.")


def main() -> None:
    raw = load(INPUT_PATH)
    cleaned, steps, dropped_examples = clean(raw)
    cleaned = add_columns(cleaned)
    sample = stratified_sample(cleaned)
    summary = write_outputs(cleaned, sample, steps)
    print_summary(summary, dropped_examples)


if __name__ == "__main__":
    main()
