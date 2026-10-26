"""Propose review themes with Sonnet on two separate slices of the sample.

Sets aside a stratified eval set first (eval/eval_ids.json) so those reviews are
never used here. Writes themes/proposed_run1.json, themes/proposed_run2.json and
themes/comparison.md. The approved theme list is written by hand afterwards.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import aisuite as ai
import pandas as pd
from dotenv import load_dotenv

from prepare import BANDS, allocate

load_dotenv()  # reads the API key from .env (never printed)

MODEL = "anthropic:claude-sonnet-5-5"
THINKING_OFF = {"type": "between_tools"}  # aisuite only reads the first text block
MAX_TOKENS = 6000

SAMPLE_PATH = Path("sample/reviews_sample.csv")
EVAL_PATH = Path("eval/eval_ids.json")
THEMES_DIR = Path("themes")
COMPARISON_PATH = THEMES_DIR / "comparison.md"

EVAL_SEED = 42
EVAL_SIZE = 200
SLICE_SIZE = 200
SLICE_SEEDS = [42, 43]  # run 1, run 2
MIN_THEMES, MAX_THEMES = 8, 15
OTHER = "Other"
SNIPPET_CHARS = 150

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

    A truncated reply is not retried: the same limit would truncate it again.
    """
    try:
        reply = ask_llm(prompt, max_tokens)
        try:
            data = parse_json(reply)
            validate(data)
            return data
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
    return data


# ---------- Splitting ----------

def band_targets(total):
    """Split `total` across bands as evenly as possible (e.g. 200 -> 67/67/66)."""
    share, extra = divmod(total, len(BANDS))
    return {band: share + (1 if i < extra else 0) for i, band in enumerate(BANDS)}


def stratified_draw(df, total, seed):
    """Draw `total` reviews, even across bands, then even across quarters within each band."""
    parts = []
    for band, band_total in band_targets(total).items():
        band_df = df[df["rating_band"] == band]
        alloc = allocate(band_df["quarter"].value_counts().to_dict(), band_total)
        for quarter, n in sorted(alloc.items()):
            if n > 0:
                group = band_df[band_df["quarter"] == quarter]
                parts.append(group.sample(n=n, random_state=seed))
    return pd.concat(parts)


def split_eval(sample):
    """Draw the eval set. If eval_ids.json exists, it must match the fresh draw."""
    eval_ids = sorted(stratified_draw(sample, EVAL_SIZE, EVAL_SEED)["Review Id"])
    if EVAL_PATH.exists():
        saved = json.loads(EVAL_PATH.read_text())["review_ids"]
        if saved != eval_ids:
            raise RuntimeError(
                f"{EVAL_PATH} does not match a fresh draw. The sample or seed changed; "
                "resolve this before proposing themes so eval reviews cannot leak."
            )
    else:
        EVAL_PATH.parent.mkdir(exist_ok=True)
        record = {
            "seed": EVAL_SEED,
            "n": len(eval_ids),
            "source": str(SAMPLE_PATH),
            "stratified_by": ["rating_band", "quarter"],
            "review_ids": eval_ids,
        }
        EVAL_PATH.write_text(json.dumps(record, indent=2) + "\n")
    return set(eval_ids)


def draw_slices(pool):
    """Draw non-overlapping slices: each slice comes from what earlier slices left."""
    slices = []
    for seed in SLICE_SEEDS:
        drawn = stratified_draw(pool, SLICE_SIZE, seed)
        drawn = drawn.sort_values(["rating_band", "quarter", "Review Id"]).reset_index(drop=True)
        slices.append(drawn)
        pool = pool[~pool["Review Id"].isin(drawn["Review Id"])]
    return slices


# ---------- Theme proposal ----------

PROMPT = """You are analysing Google Play reviews of the ChatGPT Android app.
Below are {n} reviews. Each line is: [id] (star rating) review text.

Propose between {min_themes} and {max_themes} themes that together describe what these reviews talk about.
- Themes should be distinct, with as little overlap as possible.
- A review can belong to more than one theme.
- Always include a theme named exactly "{other}" for reviews that fit no other theme.
- For each theme give 2-3 example_ids: ids of reviews from the list below that clearly belong to it.

Return ONLY a JSON object in this format, with no other text:
{{
  "themes": [
    {{
      "name": "short theme name",
      "definition": "one or two sentences on what the theme covers",
      "includes": ["kinds of feedback that belong here"],
      "excludes": ["nearby feedback that belongs in another theme"],
      "example_ids": ["r001", "r002"]
    }}
  ]
}}

Reviews:
{reviews}"""


def build_prompt(slice_df, short_ids):
    lines = [
        f"[{sid}] ({rating}★) {' '.join(text.split())}"
        for sid, rating, text in zip(short_ids, slice_df["Ratings"], slice_df["Review"])
    ]
    return PROMPT.format(
        n=len(lines), min_themes=MIN_THEMES, max_themes=MAX_THEMES,
        other=OTHER, reviews="\n".join(lines),
    )


def is_text_list(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def make_validator(valid_ids):
    def validate(data):
        if not isinstance(data, dict) or not isinstance(data.get("themes"), list):
            raise ValueError("answer must be a JSON object with a 'themes' list")
        themes = data["themes"]
        if not MIN_THEMES <= len(themes) <= MAX_THEMES:
            raise ValueError(f"expected {MIN_THEMES}-{MAX_THEMES} themes, got {len(themes)}")
        names = []
        for i, theme in enumerate(themes):
            label = f"theme {i + 1}"
            if not isinstance(theme, dict):
                raise ValueError(f"{label} is not an object")
            for field in ["name", "definition"]:
                if not isinstance(theme.get(field), str) or not theme[field].strip():
                    raise ValueError(f"{label} is missing '{field}'")
            label = f"theme '{theme['name']}'"
            if not is_text_list(theme.get("includes")) or not theme["includes"]:
                raise ValueError(f"{label}: 'includes' must be a non-empty list of strings")
            if not is_text_list(theme.get("excludes")):
                raise ValueError(f"{label}: 'excludes' must be a list of strings")
            ids = theme.get("example_ids")
            if not is_text_list(ids) or not 2 <= len(ids) <= 3 or len(set(ids)) != len(ids):
                raise ValueError(f"{label}: 'example_ids' must be 2-3 distinct ids")
            unknown = [x for x in ids if x not in valid_ids]
            if unknown:
                raise ValueError(f"{label}: example_ids not in the review list: {unknown}")
            names.append(theme["name"].strip().lower())
        if len(set(names)) != len(names):
            raise ValueError("theme names must be unique")
        if names.count(OTHER.lower()) != 1:
            raise ValueError(f"exactly one theme must be named '{OTHER}'")
    return validate


def propose(run, slice_df, seed):
    short_ids = [f"r{i:03d}" for i in range(1, len(slice_df) + 1)]
    to_review_id = dict(zip(short_ids, slice_df["Review Id"]))
    data = run_step(f"run {run}", build_prompt(slice_df, short_ids), make_validator(set(short_ids)))
    for theme in data["themes"]:
        theme["example_ids"] = [to_review_id[x] for x in theme["example_ids"]]
    return {
        "run": run,
        "model": MODEL,
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "slice_size": len(slice_df),
        "slice_by_band": slice_df["rating_band"].value_counts().reindex(BANDS).astype(int).to_dict(),
        "themes": data["themes"],
        "slice_review_ids": list(slice_df["Review Id"]),
    }


# ---------- Comparison ----------

def md_cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def write_comparison(results, reviews_by_id):
    lines = [
        "# Proposed themes: run 1 vs run 2",
        "",
        f"Model: `{MODEL}`. Each run saw a different, non-overlapping slice of "
        f"{SLICE_SIZE} reviews (seeds {', '.join(map(str, SLICE_SEEDS))}). "
        "Themes are listed in the order the model gave them; rows are not matched.",
        "",
        "| # | Run 1 theme | Run 1 definition | Run 2 theme | Run 2 definition |",
        "|---|---|---|---|---|",
    ]
    themes = [r["themes"] for r in results]
    for i in range(max(len(t) for t in themes)):
        cells = []
        for run_themes in themes:
            if i < len(run_themes):
                cells += [f"**{md_cell(run_themes[i]['name'])}**", md_cell(run_themes[i]["definition"])]
            else:
                cells += ["", ""]
        lines.append(f"| {i + 1} | " + " | ".join(cells) + " |")

    for result in results:
        lines += ["", f"## Run {result['run']} details", ""]
        for theme in result["themes"]:
            lines += [f"### {theme['name']}", "", theme["definition"], ""]
            lines.append("- **Includes:** " + "; ".join(theme["includes"]))
            lines.append("- **Excludes:** " + ("; ".join(theme["excludes"]) or "–"))
            lines.append("- **Examples:**")
            for review_id in theme["example_ids"]:
                rating, text = reviews_by_id[review_id]
                snippet = " ".join(text.split())
                if len(snippet) > SNIPPET_CHARS:
                    snippet = snippet[:SNIPPET_CHARS].rstrip() + "…"
                lines.append(f"  - ({rating}★) {snippet} `{review_id}`")
            lines.append("")
    COMPARISON_PATH.write_text("\n".join(lines).rstrip() + "\n")


# ---------- Main ----------

def main():
    sample = pd.read_csv(SAMPLE_PATH, dtype={"Review Id": str})
    eval_ids = split_eval(sample)
    pool = sample[~sample["Review Id"].isin(eval_ids)]
    slices = draw_slices(pool)

    # Guard: no eval review and no shared review between slices
    slice_ids = [set(s["Review Id"]) for s in slices]
    assert all(not (ids & eval_ids) for ids in slice_ids), "eval review leaked into a slice"
    assert not (slice_ids[0] & slice_ids[1]), "slices overlap"

    print(f"Eval set: {len(eval_ids)} reviews -> {EVAL_PATH}")
    print(f"Pool for proposal: {len(pool)} reviews")

    THEMES_DIR.mkdir(exist_ok=True)
    results = []
    for run, (slice_df, seed) in enumerate(zip(slices, SLICE_SEEDS), start=1):
        result = propose(run, slice_df, seed)
        print(f"\nRun {run} (seed {seed}): slice by band {result['slice_by_band']}")
        path = THEMES_DIR / f"proposed_run{run}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"  {len(result['themes'])} themes -> {path}")
        for theme in result["themes"]:
            print(f"    - {theme['name']}")
        results.append(result)

    reviews_by_id = dict(zip(sample["Review Id"], zip(sample["Ratings"], sample["Review"])))
    write_comparison(results, reviews_by_id)
    print(f"\nComparison -> {COMPARISON_PATH}")


if __name__ == "__main__":
    main()
