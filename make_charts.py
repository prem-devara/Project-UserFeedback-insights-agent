"""Charts of the weighted complaint estimates, with 95% bootstrap intervals.

No LLM calls. Reads insights/metrics.json (and theme names from
themes/approved_themes.json), and writes PNGs to insights/charts/.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

METRICS_PATH = Path("insights/metrics.json")
THEMES_PATH = Path("themes/approved_themes.json")
CHARTS_DIR = Path("insights/charts")

OVER_COUNTED = "missing_features"

# one neutral, one accent; text in ink colours, never the series colour
SURFACE = "#fcfcfb"
NEUTRAL = "#b4b2ab"
ACCENT = "#2a78d6"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e6e5e0"
INTERVAL = "#3d3c39"

SOURCE_NOTE = (
    "Weighted estimates for 30,308 cleaned reviews (Jul 2023–Aug 2024), from 1,500 classified sample reviews. "
    "Lines show 95% bootstrap intervals (sampling error only, not classifier error)."
)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def theme_label(theme, names):
    return names[theme] + (" †" if theme == OVER_COUNTED else "")


def errors(values):
    """matplotlib xerr from {est, lo, hi} dicts: distances below and above the estimate."""
    return [[v["est"] - v["lo"] for v in values], [v["hi"] - v["est"] for v in values]]


def style_axes(ax, xmax):
    ax.set_xlim(0, xmax)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)


def add_title(fig, title, subtitle):
    fig.text(0.02, 0.97, title, fontsize=14, fontweight="bold", va="top")
    fig.text(0.02, 0.915, subtitle, fontsize=10, color=INK_SECONDARY, va="top")


def add_footer(fig, extra=""):
    fig.text(0.02, 0.02, SOURCE_NOTE + (" " + extra if extra else ""), fontsize=8,
             color=INK_SECONDARY, va="bottom", wrap=True)


def complaint_ranking(metrics, names):
    rows = metrics["complaint_ranking"][::-1]  # largest at the top
    labels = [theme_label(r["theme"], names) for r in rows]
    y = range(len(rows))

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.subplots_adjust(left=0.40, right=0.95, top=0.84, bottom=0.17)
    bars = ax.barh(y, [r["est"] for r in rows], height=0.62, color=ACCENT)
    for bar, row in zip(bars, rows):
        if row["theme"] == OVER_COUNTED:
            bar.set_facecolor(NEUTRAL)
    ax.errorbar([r["est"] for r in rows], y, xerr=errors(rows), fmt="none",
                ecolor=INTERVAL, elinewidth=1.2, capsize=0)
    for i, row in enumerate(rows):
        ax.text(row["hi"] + 0.006, i, f"{row['est']:.0%}", va="center", fontsize=9, color=INK_SECONDARY)

    ax.set_yticks(list(y), labels)
    style_axes(ax, max(r["hi"] for r in rows) + 0.05)
    add_title(fig, "Incorrect, hallucinated or outdated answers are the most common complaint",
              "Share of complaint reviews (negative or mixed sentiment) that mention each theme")
    add_footer(fig, "† Likely over-counted: the classifier tags any “please add X” request as a "
                    "missing feature. A review can mention several themes.")
    path = CHARTS_DIR / "complaint_ranking.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def severity(metrics, names):
    ranked = [r["theme"] for r in metrics["complaint_ranking"]]
    all_share, low_share = metrics["theme_share_all"], metrics["theme_share_low_band"]
    themes = sorted(ranked, key=lambda t: low_share[t]["est"])  # largest 1–2★ share at the top
    height = 0.36

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.subplots_adjust(left=0.40, right=0.95, top=0.85, bottom=0.14)
    series = [
        ("Share of all reviews", all_share, NEUTRAL, height / 2 + 0.02),
        ("Share of 1–2★ reviews", low_share, ACCENT, -height / 2 - 0.02),
    ]
    for label, shares, colour, offset in series:
        y = [i + offset for i in range(len(themes))]
        values = [shares[t] for t in themes]
        ax.barh(y, [v["est"] for v in values], height=height, color=colour, label=label)
        ax.errorbar([v["est"] for v in values], y, xerr=errors(values), fmt="none",
                    ecolor=INTERVAL, elinewidth=1.0, capsize=0)

    ax.set_yticks(range(len(themes)), [theme_label(t, names) for t in themes])
    style_axes(ax, max(low_share[t]["hi"] for t in themes) + 0.03)
    ax.legend(loc="lower right", frameon=False, fontsize=9)  # same order as the bars in each pair
    add_title(fig, "Some issues are rare but drive 1–2★ ratings",
              "Login and crash problems are a small share of all reviews but a large share of 1–2★ reviews")
    add_footer(fig, "† Likely over-counted.")
    path = CHARTS_DIR / "severity.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main():
    metrics = json.loads(METRICS_PATH.read_text())
    names = {t["id"]: t["name"] for t in json.loads(THEMES_PATH.read_text())["themes"]}
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in [complaint_ranking(metrics, names), severity(metrics, names)]:
        print(f"-> {path}")


if __name__ == "__main__":
    main()
