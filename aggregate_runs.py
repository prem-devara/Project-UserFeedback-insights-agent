"""Summarise repeated classifier runs: mean and min–max across runs.

No LLM calls. Reads outputs/v2_runs/scores_run<N>.json and
classified_run<N>_meta.json for every run found, and writes
outputs/scores_v2_runs.md.
"""

import json
import statistics
from pathlib import Path

RUNS_DIR = Path("outputs/v2_runs")
OUTPUT_PATH = Path("outputs/scores_v2_runs.md")


def load_runs():
    count = len(list(RUNS_DIR.glob("scores_run*.json")))
    if count == 0:
        raise SystemExit(f"no scores_run*.json files in {RUNS_DIR}")
    numbers = range(1, count + 1)
    runs = [json.loads((RUNS_DIR / f"scores_run{i}.json").read_text()) for i in numbers]
    metas = [json.loads((RUNS_DIR / f"classified_run{i}_meta.json").read_text()) for i in numbers]
    return runs, metas


def table_row(label, values, pct=False):
    fmt = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:.2f}")
    return (
        f"| {label} | " + " | ".join(fmt(v) for v in values)
        + f" | {fmt(statistics.mean(values))} | {fmt(min(values))}–{fmt(max(values))} |"
    )


def table_header(first, n_runs):
    runs = " | ".join(f"Run {i}" for i in range(1, n_runs + 1))
    return [f"| {first} | {runs} | Mean | Min–max |", "|---|" + "---:|" * (n_runs + 2)]


def write_report(runs, metas):
    lines = [
        "# Classifier v2: run-to-run spread",
        "",
        f"Same prompt, themes and model (`{metas[0]['model']}`, thinking `{metas[0]['thinking']['type']}`) "
        f"run {len(runs)} times on the {runs[0]['n_reviews']} labelled eval reviews. "
        "Run 1 is the committed v2 run (`outputs/scores_v2.md`). "
        f"Per-run classifications and scores are in `{RUNS_DIR}/`. "
        f"Retried batches per run: {', '.join(str(m['retried_batches']) for m in metas)} (all passed).",
        "",
        "## Overall",
        "",
        *table_header("Metric", len(runs)),
        table_row("Sentiment accuracy", [r["sentiment"]["accuracy"] for r in runs], pct=True),
        table_row("Theme micro F1", [r["themes"]["micro_f1"] for r in runs]),
        table_row("Theme macro F1", [r["themes"]["macro_f1"] for r in runs]),
        table_row("Theme sets match exactly", [r["themes"]["exact_match_share"] for r in runs], pct=True),
        "",
        "## Per-theme F1",
        "",
        "⚠ marks low support (fewer than 10 hand labels).",
        "",
        *table_header("Theme (support)", len(runs)),
    ]
    per_run = [{t["theme"]: t for t in r["themes"]["per_theme"]} for r in runs]
    for theme in sorted(runs[0]["themes"]["per_theme"], key=lambda t: -t["support"]):
        flag = " ⚠" if theme["low_support"] else ""
        label = f"`{theme['theme']}` ({theme['support']}){flag}"
        lines.append(table_row(label, [p[theme["theme"]]["f1"] for p in per_run]))
    OUTPUT_PATH.write_text("\n".join(lines) + "\n")


def main():
    runs, metas = load_runs()
    write_report(runs, metas)
    print(f"{len(runs)} runs -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
