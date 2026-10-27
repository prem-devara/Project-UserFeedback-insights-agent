"""Classify reviews into the approved themes and a sentiment with Haiku.

--subset eval-labelled: the eval reviews with a hand-labelled sentiment in
eval/eval_labels.xlsx. --subset all: all reviews in sample/reviews_sample.csv.
Writes outputs/classified_<subset>.csv and outputs/classified_<subset>_meta.json.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import aisuite as ai
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # reads the API key from .env (never printed)

MODEL = "anthropic:claude-haiku-5-5"
THINKING_OFF = {"type": "disabled"}  # Haiku 5.5 accepts this at the default effort
MAX_TOKENS = 4000

SAMPLE_PATH = Path("sample/reviews_sample.csv")
LABELS_PATH = Path("eval/eval_labels.xlsx")
THEMES_PATH = Path("themes/approved_themes.json")
OUTPUT_DIR = Path("outputs")

SUBSETS = ["eval-labelled", "all"]
BATCH_SIZE = 20
SHUFFLE_SEED = 42  # the sample is sorted by rating band; shuffle so batches mix ratings
SENTIMENTS = ["positive", "negative", "mixed", "neutral"]
OTHER = "other"

client = ai.Client()


# ---------- LLM helpers ----------

class TruncatedResponseError(RuntimeError):
    """The model hit max_tokens, so its reply is cut off."""


def ask_llm(prompt, max_tokens=MAX_TOKENS):
    """Send one prompt to the model and return its text reply."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        thinking=THINKING_OFF,
    )
    # aisuite maps Anthropic's stop_reason "max_tokens" to finish_reason "length"
    if response.choices[0].finish_reason == "length":
        raise TruncatedResponseError(
            f"{MODEL} reply was cut off at max_tokens={max_tokens}. "
            "Raise MAX_TOKENS; retrying with the same limit would be cut off again."
        )
    return response.choices[0].message.content


def parse_json(text):
    """Parse JSON from the model, removing ```json fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]      # drop the opening ``` line
        text = text.rsplit("```", 1)[0]    # drop the closing ```
    return json.loads(text)


def run_step(name, prompt, validate, max_tokens=MAX_TOKENS):
    """Ask the model, parse and validate the JSON. Retry once on failure.

    Returns (data, retried). A truncated reply is not retried: the same limit
    would truncate it again.
    """
    try:
        reply = ask_llm(prompt, max_tokens)
        try:
            data = parse_json(reply)
            validate(data)
            return data, False
        except (json.JSONDecodeError, ValueError) as error:
            problem = str(error)
            print(f"  {name}: validation failed ({problem}). Retrying once...")

        retry_prompt = (
            prompt
            + "\n\nYour previous answer was invalid because: " + problem
            + "\nReturn ONLY valid JSON in the exact format requested."
        )
        reply = ask_llm(retry_prompt, max_tokens)
    except TruncatedResponseError as error:
        raise TruncatedResponseError(f"{name}: {error}") from None
    data = parse_json(reply)  # raises if still invalid
    validate(data)
    return data, True


# ---------- Inputs ----------

def load_reviews(subset):
    sample = pd.read_csv(SAMPLE_PATH, dtype={"Review Id": str, "Review": str})
    if subset == "all":
        return sample
    labels = pd.read_excel(LABELS_PATH, sheet_name="Labels", dtype={"review_id": str})
    ids = set(labels.loc[labels["sentiment"].notna(), "review_id"])
    reviews = sample[sample["Review Id"].isin(ids)]
    if len(reviews) != len(ids):
        raise SystemExit(f"{len(ids) - len(reviews)} labelled ids not found in {SAMPLE_PATH}")
    return reviews


# ---------- Classification ----------

PROMPT = """You are classifying Google Play reviews of the ChatGPT Android app.

Themes (use the id in your answer):
{themes}

For each review below, choose:
- "themes": every theme id that applies (at least one). A review can belong to more than one theme.
  Use "{other}" only for content that no other theme covers; it can be combined with other themes.
- "sentiment": one of {sentiments}. Use "mixed" when the review clearly contains both praise and complaints.

Each review line is: [id] (star rating) review text.

Return ONLY a JSON object in this format, with no other text, and one entry per review:
{{
  "reviews": [
    {{"id": "r01", "themes": ["theme_id"], "sentiment": "positive"}}
  ]
}}

Reviews:
{reviews}"""


def format_themes(themes):
    blocks = []
    for theme in themes:
        lines = [f"- {theme['id']}: {theme['name']}. {theme['definition']}"]
        lines.append("  Includes: " + "; ".join(theme["includes"]))
        if theme["excludes"]:
            lines.append("  Excludes: " + "; ".join(theme["excludes"]))
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def build_prompt(batch, short_ids, themes_text):
    lines = [
        f"[{sid}] ({rating}★) {' '.join(text.split())}"
        for sid, rating, text in zip(short_ids, batch["Ratings"], batch["Review"])
    ]
    return PROMPT.format(
        themes=themes_text, other=OTHER, sentiments=", ".join(f'"{s}"' for s in SENTIMENTS),
        reviews="\n".join(lines),
    )


def make_validator(short_ids, theme_ids):
    def validate(data):
        if not isinstance(data, dict) or not isinstance(data.get("reviews"), list):
            raise ValueError("answer must be a JSON object with a 'reviews' list")
        seen = []
        for i, item in enumerate(data["reviews"]):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError(f"entry {i + 1} must be an object with a string 'id'")
            label = f"review {item['id']}"
            if item["id"] not in short_ids:
                raise ValueError(f"{label} is not in the review list")
            seen.append(item["id"])
            themes = item.get("themes")
            if not isinstance(themes, list) or not themes:
                raise ValueError(f"{label}: 'themes' must be a non-empty list")
            unknown = [t for t in themes if t not in theme_ids]
            if unknown:
                raise ValueError(f"{label}: unknown theme ids {unknown}")
            if len(set(themes)) != len(themes):
                raise ValueError(f"{label}: repeated theme ids")
            if item.get("sentiment") not in SENTIMENTS:
                raise ValueError(f"{label}: sentiment must be one of {SENTIMENTS}")
        duplicates = sorted({x for x in seen if seen.count(x) > 1})
        if duplicates:
            raise ValueError(f"ids returned more than once: {duplicates}")
        missing = [x for x in short_ids if x not in seen]
        if missing:
            raise ValueError(f"ids missing from the answer: {missing}")
    return validate


def classify_batch(number, batch, themes_text, theme_ids):
    short_ids = [f"r{i:02d}" for i in range(1, len(batch) + 1)]
    to_review_id = dict(zip(short_ids, batch["Review Id"]))
    prompt = build_prompt(batch, short_ids, themes_text)
    data, retried = run_step(f"batch {number}", prompt, make_validator(short_ids, theme_ids))
    rows = []
    for item in data["reviews"]:
        ordered = [t for t in theme_ids if t in item["themes"]]  # approved-list order
        rows.append({
            "review_id": to_review_id[item["id"]],
            "themes": ";".join(ordered),
            "sentiment": item["sentiment"],
        })
    return rows, retried


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subset", choices=SUBSETS, required=True)
    subset = parser.parse_args().subset

    themes = json.loads(THEMES_PATH.read_text())["themes"]
    theme_ids = [t["id"] for t in themes]
    themes_text = format_themes(themes)

    reviews = load_reviews(subset).sample(frac=1, random_state=SHUFFLE_SEED)
    batches = [reviews.iloc[i:i + BATCH_SIZE] for i in range(0, len(reviews), BATCH_SIZE)]
    print(f"Subset {subset}: {len(reviews)} reviews in {len(batches)} batches of up to {BATCH_SIZE}")

    rows, retries = [], 0
    for number, batch in enumerate(batches, start=1):
        batch_rows, retried = classify_batch(number, batch, themes_text, theme_ids)
        rows += batch_rows
        retries += retried
        print(f"  batch {number}/{len(batches)} done" + (" (after retry)" if retried else ""))

    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / f"classified_{subset}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    meta = {
        "model": MODEL,
        "thinking": THINKING_OFF,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subset": subset,
        "n_reviews": len(rows),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "retried_batches": retries,
        "shuffle_seed": SHUFFLE_SEED,
        "themes_source": str(THEMES_PATH),
    }
    meta_path = OUTPUT_DIR / f"classified_{subset}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"\n{len(rows)} reviews -> {csv_path}\nMeta -> {meta_path}")


if __name__ == "__main__":
    main()
