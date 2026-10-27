"""Weighted estimates for the full cleaned review set, with bootstrap intervals.

No LLM calls. Reads outputs/classified_all.csv, sample/reviews_sample.csv and
sample/prep_summary.json, and writes insights/metrics.json and insights/metrics.md.

The sample is stratified: 100 reviews per rating band x quarter cell. Each sampled
review stands for (cleaned count / sampled count) reviews in its cell. Intervals
come from resampling within each cell; they cover sampling error only.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

CLASSIFIED_PATH = Path("outputs/classified_all.csv")
SAMPLE_PATH = Path("sample/reviews_sample.csv")
PREP_PATH = Path("sample/prep_summary.json")
OUTPUT_DIR = Path("insights")

SEED = 42
N_BOOT = 1000
QUARTERS = ["2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3"]
PARTIAL_QUARTERS = {"2023Q3": "data starts 2023-07-25", "2024Q3": "data ends 2024-08-23"}
FULL_QUARTERS = [q for q in QUARTERS if q not in PARTIAL_QUARTERS]
SENTIMENTS = ["positive", "negative", "mixed", "neutral"]
COMPLAINT_SENTIMENTS = {"negative", "mixed"}
NOT_COMPLAINT_THEMES = {"general_praise", "other"}

NOTES = {
    "intervals": "95% intervals come from a bootstrap (1,000 resamples within each "
    "band x quarter cell, seed 42). They cover sampling error only, not classifier "
    "error: theme labels themselves are imperfect (see BUILD_LOG.md).",
    "multi_label": "A review can have several themes, so theme shares add up to more than 100%.",
    "complaint": "Complaint reviews are those with sentiment negative or mixed.",
    "missing_features": "missing_features is likely over-counted: the classifier tags "
    "any 'please add X' request as missing_features, even when X belongs to another "
    "theme (known limitation, see BUILD_LOG.md).",
    "not_complaint_themes": "general_praise and other appear in the tables but are left "
    "out of the complaint ranking because they are not complaint themes.",
    "partial_quarters": "2023Q3 and 2024Q3 are partial quarters (" + "; ".join(
        f"{q}: {why}" for q, why in PARTIAL_QUARTERS.items()) + "). Trend changes compare "
    f"the first and last full quarters ({FULL_QUARTERS[0]} vs {FULL_QUARTERS[-1]}).",
}


def load():
    classified = pd.read_csv(CLASSIFIED_PATH)
    sample = pd.read_csv(SAMPLE_PATH)[["Review Id", "rating_band", "quarter"]]
    df = classified.merge(sample, left_on="review_id", right_on="Review Id", validate="one_to_one")
    if len(df) != len(classified) or len(df) != len(sample):
        raise SystemExit(f"join mismatch: {len(classified)} classified, {len(sample)} sampled, {len(df)} joined")
    cleaned = json.loads(PREP_PATH.read_text())
    return df.drop(columns="Review Id").reset_index(drop=True), cleaned


def add_weights(df, cleaned):
    sampled = df.groupby(["rating_band", "quarter"]).size()
    by_cell = cleaned["cleaned_by_band_quarter"]
    weights = {(b, q): by_cell[b][q] / n for (b, q), n in sampled.items()}
    df["weight"] = [weights[(b, q)] for b, q in zip(df.rating_band, df.quarter)]
    total = df.weight.sum()
    if not np.isclose(total, cleaned["cleaned_total"]):
        raise SystemExit(f"weights sum to {total:.1f}, expected {cleaned['cleaned_total']}")
    table = {b: {q: round(weights[(b, q)], 3) for q in QUARTERS} for b in by_cell}
    return df, table, total


def bootstrap_counts(df, rng):
    """Matrix of how often each row is drawn: shape (N_BOOT, n_rows).

    Each resample draws, with replacement, as many rows as each cell holds, from
    that cell only.
    """
    counts = np.zeros((N_BOOT, len(df)))
    for _, rows in df.groupby(["rating_band", "quarter"]).indices.items():
        draws = rows[rng.integers(0, len(rows), size=(N_BOOT, len(rows)))]
        np.add.at(counts, (np.repeat(np.arange(N_BOOT), len(rows)), draws.ravel()), 1)
    return counts


def shares(weights, mask, indicators):
    """Weighted share of rows in `mask` that have each indicator column.

    `weights` is (n_rows,) for the point estimate or (N_BOOT, n_rows) for the
    bootstrap; returns (n_cols,) or (N_BOOT, n_cols).
    """
    masked = weights * mask
    return (masked @ indicators) / masked.sum(axis=-1, keepdims=True)


def with_interval(point, boot, labels):
    lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
    return {label: {"est": float(p), "lo": float(l), "hi": float(h)}
            for label, p, l, h in zip(labels, point, lo, hi)}


def estimate(weights, boot_weights, mask, indicators, labels):
    return with_interval(shares(weights, mask, indicators),
                         shares(boot_weights, mask, indicators), labels)


def build_metrics(df, weight_table, weight_total):
    themes = sorted(df.themes.str.split(";").explode().unique())
    theme_matrix = np.column_stack([df.themes.str.split(";").apply(lambda t, th=th: th in t) for th in themes]).astype(float)
    sentiment_matrix = np.column_stack([df.sentiment == s for s in SENTIMENTS]).astype(float)

    w = df.weight.to_numpy()
    boot_w = bootstrap_counts(df, np.random.default_rng(SEED)) * w
    everyone = np.ones(len(df))
    complaint = df.sentiment.isin(COMPLAINT_SENTIMENTS).to_numpy(dtype=float)
    low_band = (df.rating_band == "low").to_numpy(dtype=float)

    by_quarter = {
        q: estimate(w, boot_w, complaint * (df.quarter == q).to_numpy(), theme_matrix, themes)
        for q in QUARTERS
    }
    trend = {}
    first, last = FULL_QUARTERS[0], FULL_QUARTERS[-1]
    for theme in themes:
        a, b = by_quarter[first][theme], by_quarter[last][theme]
        changed = a["hi"] < b["lo"] or b["hi"] < a["lo"]
        trend[theme] = {
            "by_quarter": {q: by_quarter[q][theme] for q in QUARTERS},
            "changed": changed,
            "direction": ("up" if b["est"] > a["est"] else "down") if changed else None,
        }

    complaint_share = estimate(w, boot_w, complaint, theme_matrix, themes)
    ranked = sorted((t for t in themes if t not in NOT_COMPLAINT_THEMES),
                    key=lambda t: complaint_share[t]["est"], reverse=True)

    return {
        "meta": {
            "seed": SEED,
            "n_bootstrap": N_BOOT,
            "n_sampled": len(df),
            "n_complaint_sampled": int(complaint.sum()),
            "n_low_band_sampled": int(low_band.sum()),
            "cleaned_total": float(weight_total),
            "weighted_complaint_total": float((w * complaint).sum()),
            "weighted_low_band_total": float((w * low_band).sum()),
            "quarters": QUARTERS,
            "partial_quarters": PARTIAL_QUARTERS,
            "trend_compares": [first, last],
        },
        "notes": NOTES,
        "weights": weight_table,
        "sentiment": estimate(w, boot_w, everyone, sentiment_matrix, SENTIMENTS),
        "theme_share_all": estimate(w, boot_w, everyone, theme_matrix, themes),
        "theme_share_complaint": complaint_share,
        "theme_share_low_band": estimate(w, boot_w, low_band, theme_matrix, themes),
        "complaint_trend": trend,
        "complaint_ranking": [{"rank": i, "theme": t, **complaint_share[t]} for i, t in enumerate(ranked, 1)],
        "not_complaint_themes": sorted(NOT_COMPLAINT_THEMES),
    }


def fmt(v):
    return f"{v['est']:.1%} ({v['lo']:.1%}–{v['hi']:.1%})"


def ranking_table(metrics):
    complaint = metrics["theme_share_complaint"]
    lines = ["| Rank | Theme | Share of complaint reviews (95% CI) |", "|---:|---|---|"]
    for row in metrics["complaint_ranking"]:
        flag = " †" if row["theme"] == "missing_features" else ""
        lines.append(f"| {row['rank']} | `{row['theme']}`{flag} | {fmt(row)} |")
    for theme in metrics["not_complaint_themes"]:
        lines.append(f"| – | `{theme}` | {fmt(complaint[theme])} — not a complaint theme |")
    return lines


def write_report(metrics):
    meta, notes = metrics["meta"], metrics["notes"]
    themes = list(metrics["theme_share_all"])
    lines = [
        "# Review insights: weighted estimates",
        "",
        f"Estimates for all {meta['cleaned_total']:,.0f} cleaned reviews, from a stratified sample "
        f"of {meta['n_sampled']:,} classified reviews weighted back to the cleaned counts.",
        "",
        f"> **{notes['intervals']}**",
        "",
        f"- {notes['multi_label']}",
        f"- {notes['complaint']} About {meta['weighted_complaint_total']:,.0f} cleaned reviews "
        f"({meta['n_complaint_sampled']} sampled).",
        f"- 1–2★ reviews: {meta['weighted_low_band_total']:,.0f} cleaned ({meta['n_low_band_sampled']} sampled).",
        "",
        "## Ranked complaint themes",
        "",
        *ranking_table(metrics),
        "",
        f"† {notes['missing_features']}",
        "",
        notes["not_complaint_themes"],
        "",
        "## Sentiment distribution",
        "",
        "| Sentiment | Share of reviews (95% CI) |",
        "|---|---|",
        *(f"| {s} | {fmt(v)} |" for s, v in metrics["sentiment"].items()),
        "",
        "## Theme shares",
        "",
        "| Theme | All reviews | Complaint reviews | 1–2★ reviews |",
        "|---|---|---|---|",
        *(f"| `{t}` | {fmt(metrics['theme_share_all'][t])} | {fmt(metrics['theme_share_complaint'][t])} "
          f"| {fmt(metrics['theme_share_low_band'][t])} |" for t in themes),
        "",
        "## Quarterly trend: share of complaint reviews",
        "",
        notes["partial_quarters"],
        "",
        "| Theme | " + " | ".join(q + (" (partial)" if q in meta["partial_quarters"] else "")
                               for q in meta["quarters"]) + " | Changed? |",
        "|---|" + "---|" * (len(meta["quarters"]) + 1),
    ]
    for theme, t in metrics["complaint_trend"].items():
        changed = f"**yes, {t['direction']}**" if t["changed"] else "no"
        lines.append(f"| `{theme}` | " + " | ".join(fmt(v) for v in t["by_quarter"].values()) + f" | {changed} |")
    lines += [
        "",
        f"\"Changed\" means the {meta['trend_compares'][0]} and {meta['trend_compares'][1]} "
        "intervals do not overlap.",
        "",
        "## Weights",
        "",
        "Each sampled review counts as this many cleaned reviews (cleaned ÷ sampled in its cell).",
        "",
        "| Band | " + " | ".join(meta["quarters"]) + " |",
        "|---|" + "---:|" * len(meta["quarters"]),
        *(f"| {band} | " + " | ".join(f"{w:.2f}" for w in row.values()) + " |"
          for band, row in metrics["weights"].items()),
        "",
    ]
    (OUTPUT_DIR / "metrics.md").write_text("\n".join(lines))


def main():
    df, cleaned = load()
    df, weight_table, weight_total = add_weights(df, cleaned)
    print(f"weights sum to {weight_total:,.1f} (cleaned total {cleaned['cleaned_total']:,})")
    metrics = build_metrics(df, weight_table, weight_total)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    write_report(metrics)
    print("\n".join(ranking_table(metrics)))
    print(f"\nwrote {OUTPUT_DIR / 'metrics.json'} and {OUTPUT_DIR / 'metrics.md'}")


if __name__ == "__main__":
    main()
