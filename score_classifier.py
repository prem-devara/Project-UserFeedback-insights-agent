"""Score classify.py against the hand labels in eval/eval_labels.xlsx.

No LLM calls. Reads the Labels sheet (rows with a sentiment only) and
outputs/classified_eval-labelled.csv. Writes outputs/scores.json,
outputs/scores.md and outputs/disagreements.csv.
"""

import json
from pathlib import Path

import pandas as pd

LABELS_PATH = Path("eval/eval_labels.xlsx")
THEMES_PATH = Path("themes/approved_themes.json")
CLASSIFIED_PATH = Path("outputs/classified_eval-labelled.csv")
META_PATH = Path("outputs/classified_eval-labelled_meta.json")
SCORES_JSON = Path("outputs/scores.json")
SCORES_MD = Path("outputs/scores.md")
DISAGREEMENTS_PATH = Path("outputs/disagreements.csv")

SENTIMENTS = ["positive", "negative", "mixed", "neutral"]
LOW_SUPPORT = 10  # themes with fewer hand labels than this are flagged


# ---------- Inputs ----------

def load_labels(theme_ids):
    labels = pd.read_excel(LABELS_PATH, sheet_name="Labels", dtype={"review_id": str})
    labels = labels[labels["sentiment"].notna()].reset_index(drop=True)
    theme_cols = labels.columns[3:3 + len(theme_ids)]
    # Theme columns are "1 Praise", "2 Education", ... in approved-list order
    numbers = [int(c.split()[0]) for c in theme_cols]
    if numbers != list(range(1, len(theme_ids) + 1)):
        raise SystemExit(f"unexpected theme columns in {LABELS_PATH}: {list(theme_cols)}")
    unknown = set(labels["sentiment"]) - set(SENTIMENTS)
    if unknown:
        raise SystemExit(f"unknown sentiments in {LABELS_PATH}: {unknown}")
    labels["my_themes"] = [
        {tid for tid, col in zip(theme_ids, theme_cols) if row[col] == 1}
        for _, row in labels.iterrows()
    ]
    return labels.rename(columns={"sentiment": "my_sentiment"})


def load_predictions():
    preds = pd.read_csv(CLASSIFIED_PATH, dtype={"review_id": str})
    preds["model_themes"] = [set(t.split(";")) for t in preds["themes"]]
    return preds.rename(columns={"sentiment": "model_sentiment"})


# ---------- Metrics ----------

def ratio(num, den):
    return num / den if den else 0.0


def f1(precision, recall):
    return ratio(2 * precision * recall, precision + recall)


def theme_scores(df, themes):
    rows = []
    for theme in themes:
        tid = theme["id"]
        mine = df["my_themes"].apply(lambda s: tid in s)
        model = df["model_themes"].apply(lambda s: tid in s)
        tp, fp, fn = int((mine & model).sum()), int((~mine & model).sum()), int((mine & ~model).sum())
        precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
        rows.append({
            "theme": tid, "name": theme["name"], "support": tp + fn, "predicted": tp + fp,
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1(precision, recall),
            "low_support": tp + fn < LOW_SUPPORT,
        })
    return rows


def score(df, themes):
    per_theme = theme_scores(df, themes)
    tp = sum(r["tp"] for r in per_theme)
    fp = sum(r["fp"] for r in per_theme)
    fn = sum(r["fn"] for r in per_theme)
    micro_p, micro_r = ratio(tp, tp + fp), ratio(tp, tp + fn)

    confusion = pd.crosstab(df["my_sentiment"], df["model_sentiment"]).reindex(
        index=SENTIMENTS, columns=SENTIMENTS, fill_value=0
    )
    return {
        "n_reviews": len(df),
        "sentiment": {
            "accuracy": float((df["my_sentiment"] == df["model_sentiment"]).mean()),
            "confusion": {
                "rows": "my label", "columns": "model label",
                "matrix": {mine: {model: int(confusion.loc[mine, model]) for model in SENTIMENTS}
                           for mine in SENTIMENTS},
            },
        },
        "themes": {
            "micro_precision": micro_p,
            "micro_recall": micro_r,
            "micro_f1": f1(micro_p, micro_r),
            "macro_f1": sum(r["f1"] for r in per_theme) / len(per_theme),
            "exact_match_share": float((df["my_themes"] == df["model_themes"]).mean()),
            "low_support_threshold": LOW_SUPPORT,
            "per_theme": per_theme,
        },
    }


# ---------- Reports ----------

def write_markdown(scores, meta):
    s, t = scores["sentiment"], scores["themes"]
    lines = [
        "# Classifier scores (eval-labelled)",
        "",
        f"Model `{meta['model']}`, thinking `{meta['thinking']['type']}`, run {meta['created_at']}. "
        f"Compared with my hand labels on {scores['n_reviews']} reviews.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Sentiment accuracy | {s['accuracy']:.0%} |",
        f"| Theme micro F1 | {t['micro_f1']:.2f} |",
        f"| Theme macro F1 | {t['macro_f1']:.2f} |",
        f"| Theme sets match exactly | {t['exact_match_share']:.0%} |",
        "",
        "## Sentiment confusion",
        "",
        "Rows are my label, columns are the model's.",
        "",
        "| mine \\ model | " + " | ".join(SENTIMENTS) + " | total |",
        "|---|" + "---:|" * (len(SENTIMENTS) + 1),
    ]
    matrix = s["confusion"]["matrix"]
    for mine in SENTIMENTS:
        counts = [matrix[mine][model] for model in SENTIMENTS]
        cells = [f"**{c}**" if model == mine else str(c) for c, model in zip(counts, SENTIMENTS)]
        lines.append(f"| {mine} | " + " | ".join(cells) + f" | {sum(counts)} |")

    lines += [
        "",
        "## Themes",
        "",
        f"Support is my count. ⚠ marks low support (fewer than {LOW_SUPPORT} labels): "
        "treat those scores as rough.",
        "",
        "| Theme | Support | Model count | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(t["per_theme"], key=lambda r: -r["support"]):
        flag = " ⚠" if r["low_support"] else ""
        lines.append(
            f"| {r['name']} (`{r['theme']}`){flag} | {r['support']} | {r['predicted']} | "
            f"{r['precision']:.2f} | {r['recall']:.2f} | {r['f1']:.2f} |"
        )
    lines += [
        "",
        f"Micro: precision {t['micro_precision']:.2f}, recall {t['micro_recall']:.2f}, "
        f"F1 {t['micro_f1']:.2f}. Macro F1 is the plain average over all {len(t['per_theme'])} themes.",
        "",
        f"Every disagreement is listed in `{DISAGREEMENTS_PATH}`.",
    ]
    SCORES_MD.write_text("\n".join(lines) + "\n")


def write_disagreements(df, theme_ids):
    def ordered(ids):
        return ";".join(t for t in theme_ids if t in ids)

    differ = df[(df["my_themes"] != df["model_themes"]) | (df["my_sentiment"] != df["model_sentiment"])]
    out = pd.DataFrame({
        "review_id": differ["review_id"],
        "rating": differ["rating"],
        "my_themes": differ["my_themes"].apply(ordered),
        "model_themes": differ["model_themes"].apply(ordered),
        "missed": [ordered(m - p) for m, p in zip(differ["my_themes"], differ["model_themes"])],
        "extra": [ordered(p - m) for m, p in zip(differ["my_themes"], differ["model_themes"])],
        "my_sentiment": differ["my_sentiment"],
        "model_sentiment": differ["model_sentiment"],
        "review": differ["review"],
    })
    out.to_csv(DISAGREEMENTS_PATH, index=False)
    return len(out)


# ---------- Main ----------

def main():
    themes = json.loads(THEMES_PATH.read_text())["themes"]
    theme_ids = [t["id"] for t in themes]
    labels = load_labels(theme_ids)
    preds = load_predictions()

    missing = set(labels["review_id"]) ^ set(preds["review_id"])
    if missing:
        raise SystemExit(f"{len(missing)} review ids are in only one of the labels and {CLASSIFIED_PATH}")
    df = labels.merge(preds[["review_id", "model_themes", "model_sentiment"]], on="review_id")

    scores = score(df, themes)
    meta = json.loads(META_PATH.read_text())
    scores["classifier"] = meta
    SCORES_JSON.write_text(json.dumps(scores, indent=2) + "\n")
    write_markdown(scores, meta)
    n_differ = write_disagreements(df, theme_ids)

    print(f"Sentiment accuracy {scores['sentiment']['accuracy']:.0%}, "
          f"theme micro F1 {scores['themes']['micro_f1']:.2f}, macro F1 {scores['themes']['macro_f1']:.2f}")
    print(f"Scores -> {SCORES_JSON}, {SCORES_MD}\n{n_differ} disagreements -> {DISAGREEMENTS_PATH}")


if __name__ == "__main__":
    main()
