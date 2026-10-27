"""Synthesise each key theme with Sonnet: summary, sub-issues, quotes, causes, opportunity.

Complaint themes see only their negative or mixed reviews; the positive theme sees
all of its reviews. Review ids and quotes are checked in code, and sub-issue counts
and weighted shares are computed in code (weights from insights.py), never taken
from the model. Writes insights/themes/<theme>.json and insights/synthesis.md.

    python synthesize.py                 # call the model for every theme
    python synthesize.py --report-only   # rebuild synthesis.md from the saved JSONs
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from insights import COMPLAINT_SENTIMENTS, add_weights, load
from propose_themes import MODEL, THINKING_OFF, run_step

MAX_TOKENS = 16000

THEMES_PATH = Path("themes/approved_themes.json")
SAMPLE_PATH = Path("sample/reviews_sample.csv")
METRICS_PATH = Path("insights/metrics.json")
OUTPUT_DIR = Path("insights/themes")
SYNTHESIS_PATH = Path("insights/synthesis.md")

COMPLAINT_THEMES = [
    "answer_quality", "crashes_errors", "pricing_limits",
    "login_account", "bias_censorship_privacy", "image_multimodal",
]
POSITIVE_THEMES = ["education"]
MIN_SUB_ISSUES, MAX_SUB_ISSUES = 3, 5
N_QUOTES = 3


# ---------- Inputs ----------

def load_reviews():
    """Classified sample with band x quarter weights (from insights.py), stars and text."""
    df, cleaned = load()
    df, _, _ = add_weights(df, cleaned)
    sample = pd.read_csv(SAMPLE_PATH, dtype={"Review Id": str})[["Review Id", "Ratings", "Review"]]
    df = df.merge(sample, left_on="review_id", right_on="Review Id", validate="one_to_one")
    df["text"] = df["Review"].map(lambda t: " ".join(t.split()))
    df["theme_list"] = df["themes"].str.split(";")
    return df.drop(columns=["Review Id", "Review"])


def theme_reviews(df, theme):
    rows = df[df["theme_list"].apply(lambda t: theme in t)]
    if theme in COMPLAINT_THEMES:
        rows = rows[rows["sentiment"].isin(COMPLAINT_SENTIMENTS)]
    return rows.sort_values(["rating_band", "quarter", "review_id"]).reset_index(drop=True)


# ---------- Prompt ----------

PROMPT = """You are analysing Google Play reviews of the ChatGPT Android app for a product manager.
All {n} reviews below were tagged with the theme "{name}".
{scope}

Theme definition: {definition}
Includes: {includes}
Excludes: {excludes}

Each line is: [id] (star rating) review text.

{task}

Rules:
- "sub_issues": {min_sub}-{max_sub} distinct {sub_kind} within this theme. For each, list the ids of
  the reviews below that mention it. A review can appear under more than one sub-issue.
- "quotes": exactly {n_quotes} short excerpts, each copied word for word from a single review
  (same spelling, case and punctuation; do not fix typos or join separate parts).
  Use {n_quotes} different reviews.
- "likely_causes": hypotheses about what might cause this feedback. These cannot be confirmed
  from reviews alone, so phrase each one as a hypothesis.
- "summary": 2-3 sentences. "opportunity": exactly one sentence.
- Only use ids from the list below.

Return ONLY a JSON object in this format, with no other text:
{{
  "summary": "2-3 sentences",
  "sub_issues": [{{"name": "short name", "review_ids": ["r1", "r2"]}}],
  "quotes": [{{"review_id": "r1", "text": "verbatim excerpt"}}],
  "likely_causes": ["hypothesis"],
  "opportunity": "one sentence on what a PM could do"
}}

Reviews:
{reviews}"""

COMPLAINT_TASK = (
    "Describe what users are complaining about: the main problems, how they show up, "
    "and what a PM could do about them."
)
POSITIVE_TASK = (
    "This is a positive theme. Describe what users value: the main ways they use the app "
    "for this, why it works for them, and what a PM could do to build on it."
)


def build_prompt(theme, rows, short_ids):
    positive = theme["id"] in POSITIVE_THEMES
    lines = [f"[{sid}] ({rating}★) {text}" for sid, rating, text in zip(short_ids, rows["Ratings"], rows["text"])]
    return PROMPT.format(
        n=len(lines),
        name=theme["name"],
        scope=("Reviews of every sentiment are included." if positive
               else "Only reviews whose sentiment is negative or mixed are included."),
        definition=theme["definition"],
        includes="; ".join(theme["includes"]),
        excludes="; ".join(theme["excludes"]) or "–",
        task=POSITIVE_TASK if positive else COMPLAINT_TASK,
        min_sub=MIN_SUB_ISSUES, max_sub=MAX_SUB_ISSUES,
        sub_kind="sub-topics" if positive else "sub-issues",
        n_quotes=N_QUOTES,
        reviews="\n".join(lines),
    )


# ---------- Validation ----------

def count_sentences(text):
    return len([s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", text.strip()) if s])


def is_text(value):
    return isinstance(value, str) and value.strip()


def make_validator(texts_by_short_id):
    def check_ids(ids, label):
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
            raise ValueError(f"{label}: review_ids must be a non-empty list of ids")
        if len(set(ids)) != len(ids):
            raise ValueError(f"{label}: review_ids has duplicates")
        unknown = [x for x in ids if x not in texts_by_short_id]
        if unknown:
            raise ValueError(f"{label}: ids not in this theme's reviews: {unknown}")

    def validate(data):
        if not isinstance(data, dict):
            raise ValueError("answer must be a JSON object")
        for field in ["summary", "opportunity"]:
            if not is_text(data.get(field)):
                raise ValueError(f"'{field}' must be a non-empty string")
        if not 2 <= count_sentences(data["summary"]) <= 3:
            raise ValueError("'summary' must be 2-3 sentences")
        if count_sentences(data["opportunity"]) != 1:
            raise ValueError("'opportunity' must be one sentence")

        subs = data.get("sub_issues")
        if not isinstance(subs, list) or not MIN_SUB_ISSUES <= len(subs) <= MAX_SUB_ISSUES:
            raise ValueError(f"'sub_issues' must be a list of {MIN_SUB_ISSUES}-{MAX_SUB_ISSUES} items, got "
                             f"{len(subs) if isinstance(subs, list) else type(subs).__name__}")
        for i, sub in enumerate(subs, 1):
            if not isinstance(sub, dict) or not is_text(sub.get("name")):
                raise ValueError(f"sub_issue {i} needs a 'name'")
            check_ids(sub.get("review_ids"), f"sub_issue '{sub['name']}'")

        quotes = data.get("quotes")
        if not isinstance(quotes, list) or len(quotes) != N_QUOTES:
            raise ValueError(f"'quotes' must be a list of exactly {N_QUOTES} items, got "
                             f"{len(quotes) if isinstance(quotes, list) else type(quotes).__name__}")
        for i, quote in enumerate(quotes, 1):
            if not isinstance(quote, dict) or not is_text(quote.get("text")) or not isinstance(quote.get("review_id"), str):
                raise ValueError(f"quote {i} needs 'review_id' and 'text'")
            check_ids([quote["review_id"]], f"quote {i}")
            # whitespace is collapsed on both sides; everything else must match exactly
            if " ".join(quote["text"].split()) not in texts_by_short_id[quote["review_id"]]:
                raise ValueError(f"quote {i} is not word for word in review {quote['review_id']}: {quote['text']!r}")
        if len({q["review_id"] for q in quotes}) != N_QUOTES:
            raise ValueError(f"quotes must come from {N_QUOTES} different reviews")

        causes = data.get("likely_causes")
        if not isinstance(causes, list) or not causes or not all(is_text(c) for c in causes):
            raise ValueError("'likely_causes' must be a non-empty list of strings")
    return validate


# ---------- Synthesis ----------

def synthesise(theme, rows):
    short_ids = [f"r{i}" for i in range(1, len(rows) + 1)]  # unpadded: the model drops leading zeros
    to_review_id = dict(zip(short_ids, rows["review_id"]))
    validate = make_validator(dict(zip(short_ids, rows["text"])))
    attempts = 0

    def counted_validate(data):  # run_step validates once per attempt
        nonlocal attempts
        attempts += 1
        validate(data)

    data = run_step(theme["id"], build_prompt(theme, rows, short_ids), counted_validate, MAX_TOKENS)

    weight = dict(zip(rows["review_id"], rows["weight"]))
    theme_weight = rows["weight"].sum()
    sub_issues = []
    for sub in data["sub_issues"]:
        ids = [to_review_id[x] for x in sub["review_ids"]]
        sub_issues.append({
            "name": sub["name"],
            "n_reviews": len(ids),
            "share_of_sample": len(ids) / len(rows),
            "weighted_share": sum(weight[x] for x in ids) / theme_weight,
            "review_ids": ids,
        })
    stars = dict(zip(rows["review_id"], rows["Ratings"]))
    quotes = [{"review_id": to_review_id[q["review_id"]], "stars": int(stars[to_review_id[q["review_id"]]]),
               "text": q["text"]} for q in data["quotes"]]

    return {
        "theme": theme["id"],
        "theme_name": theme["name"],
        "kind": "positive" if theme["id"] in POSITIVE_THEMES else "complaint",
        "sentiments_included": "all" if theme["id"] in POSITIVE_THEMES else sorted(COMPLAINT_SENTIMENTS),
        "model": MODEL,
        "thinking": THINKING_OFF,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retried": attempts > 1,
        "definition": theme["definition"],
        "n_input": len(rows),
        "weighted_input": float(theme_weight),
        "summary": data["summary"],
        "sub_issues": sub_issues,
        "quotes": quotes,
        "likely_causes": data["likely_causes"],
        "opportunity": data["opportunity"],
        "input_review_ids": list(rows["review_id"]),
    }


# ---------- Report ----------

def fmt(v):
    return f"{v['est']:.1%} ({v['lo']:.1%}–{v['hi']:.1%})"


def md_cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def coverage(result, weight):
    """Share of the theme's input reviews that appear under at least one sub-issue."""
    covered = {x for s in result["sub_issues"] for x in s["review_ids"]}
    inputs = result["input_review_ids"]
    weighted = sum(weight[x] for x in covered) / sum(weight[x] for x in inputs)
    return len(covered) / len(inputs), weighted


def theme_section(result, metrics, weight):
    theme = result["theme"]
    covered, covered_weighted = coverage(result, weight)
    rank = next((r["rank"] for r in metrics["complaint_ranking"] if r["theme"] == theme), None)
    trend = metrics["complaint_trend"][theme]
    first, last = metrics["meta"]["trend_compares"]
    by_q = trend["by_quarter"]
    trend_text = (f"**changed ({trend['direction']})**" if trend["changed"] else "no clear change") + (
        f": {by_q[first]['est']:.1%} in {first} → {by_q[last]['est']:.1%} in {last}")
    scope = ("all sentiments" if result["kind"] == "positive" else "negative and mixed reviews only")
    sub_label = "Sub-topic" if result["kind"] == "positive" else "Sub-issue"

    lines = [
        f"## {result['theme_name']} (`{theme}`)" + (" — positive theme" if result["kind"] == "positive" else ""),
        "",
        f"*{result['definition']}*",
        "",
        "| Weighted share of… | Estimate (95% CI) |",
        "|---|---|",
        f"| All reviews | {fmt(metrics['theme_share_all'][theme])} |",
        f"| Complaint reviews | {fmt(metrics['theme_share_complaint'][theme])}"
        + (f" — rank {rank} of {len(metrics['complaint_ranking'])}" if rank else "") + " |",
        f"| 1–2★ reviews | {fmt(metrics['theme_share_low_band'][theme])} |",
        "",
        f"Complaint-share trend: {trend_text}.",
        "",
        f"Synthesised from {result['n_input']} sampled reviews ({scope})"
        + (" after one retry." if result["retried"] else "."),
        "",
        f"**Summary.** {result['summary']}",
        "",
        f"| {sub_label} | Reviews in sample | Weighted share of theme (at least) |",
        "|---|---:|---:|",
        *(f"| {md_cell(s['name'])} | {s['n_reviews']} ({s['share_of_sample']:.0%}) | {s['weighted_share']:.0%} |"
          for s in result["sub_issues"]),
        "",
        f"{sub_label}s cover {covered:.0%} of this theme's sampled reviews ({covered_weighted:.0%} weighted).",
        "",
        "**Quotes**",
        "",
        *(f"> \"{md_cell(q['text'])}\" — {q['stars']}★, `{q['review_id']}`\n" for q in result["quotes"]),
        "**Likely causes (hypotheses, not verified)**",
        "",
        *(f"- {md_cell(c)}" for c in result["likely_causes"]),
        "",
        f"**Opportunity.** {result['opportunity']}",
        "",
    ]
    return lines


def write_report(results, metrics, weight):
    lines = [
        "# Theme synthesis",
        "",
        f"Model: `{MODEL}`. For each theme, the model read the sampled reviews tagged with it "
        "(complaint themes: negative and mixed sentiment only; education: all sentiments) "
        "and wrote a summary, sub-issues, quotes, likely causes and an opportunity. "
        "Weighted shares and intervals come from `insights/metrics.json`.",
        "",
        "Reviews date from July 2023 to August 2024; some issues may have been fixed since.",
        "",
        "How to read this:",
        "",
        "- **Review ids and quotes are checked in code.** Every id belongs to the theme's input, and "
        "every quote appears word for word in its review.",
        "- **Sub-issue counts are computed in code** from the ids the model listed. They are a lower "
        "bound: the model may not list every review that mentions a sub-issue. Each theme shows how "
        "many of its reviews the sub-issues cover.",
        "- **Weighted share of theme** re-weights each sub-issue's reviews by band × quarter (the same "
        "weights as `insights.py`), so it estimates the share across all cleaned reviews in the theme. "
        "The sample column over-represents 1–3★ reviews.",
        "- **Likely causes are hypotheses** drawn from review text, not verified against product data.",
        "- Theme labels come from the classifier; intervals cover sampling error only.",
        "",
    ]
    for result in results:
        lines += theme_section(result, metrics, weight)
    SYNTHESIS_PATH.write_text("\n".join(lines).rstrip() + "\n")


# ---------- Main ----------

def main():
    themes = {t["id"]: t for t in json.loads(THEMES_PATH.read_text())["themes"]}
    metrics = json.loads(METRICS_PATH.read_text())
    df = load_reviews()
    weight = dict(zip(df["review_id"], df["weight"]))
    theme_ids = COMPLAINT_THEMES + POSITIVE_THEMES

    if "--report-only" in sys.argv:  # rebuild synthesis.md from saved JSONs, no model calls
        results = [json.loads((OUTPUT_DIR / f"{t}.json").read_text()) for t in theme_ids]
        write_report(results, metrics, weight)
        print(f"Synthesis (from saved themes) -> {SYNTHESIS_PATH}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for theme_id in theme_ids:
        rows = theme_reviews(df, theme_id)
        print(f"{theme_id}: {len(rows)} reviews...")
        result = synthesise(themes[theme_id], rows)
        path = OUTPUT_DIR / f"{theme_id}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"  -> {path}" + (" (after retry)" if result["retried"] else ""))
        results.append(result)

    write_report(results, metrics, weight)
    print(f"\nSynthesis -> {SYNTHESIS_PATH}")


if __name__ == "__main__":
    main()
