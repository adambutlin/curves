"""Figures for the structural-propagation MVP note.

Reads the tables written by ``run_structural_propagation.py`` and draws five
static figures, each with its one-sentence conclusion baked into the image.
Colours: one fixed hue per shock (validated categorical palette), grey for
benchmarks and placebos.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHOCKS = ("growth", "monetary", "common_premium", "hedging_premium")
LABEL = {"growth": "Growth news", "monetary": "Monetary news",
         "common_premium": "Common premium", "hedging_premium": "Hedging premium"}
COLOR = {"growth": "#2a78d6", "monetary": "#eb6834",
         "common_premium": "#1baf7a", "hedging_premium": "#eda100"}
GREY, INK, INK2, GRID, AXIS, SURFACE = "#898781", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
VAR_LABEL = {"dy2": "2-year yield", "dy5": "5-year yield", "dy10": "10-year yield",
             "req": "Equity return"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
})


def _caption(fig, text, title):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=9, color=INK2, wrap=True)


def fig_variance_shares(out: Path, caption: str):
    df = pd.read_csv(out / "variance_shares.csv")
    post = df[df["set"] == "1983-2025"]
    bench = df[df["set"] == "benchmark: no stock-bond covariance"]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.8), sharex=True)
    for ax, v in zip(axes, ("dy2", "dy5", "dy10", "req")):
        for i, s in enumerate(SHOCKS):
            r = post[(post["variable"] == v) & (post["shock"] == s)].iloc[0]
            rb = bench[(bench["variable"] == v) & (bench["shock"] == s)].iloc[0]
            y = len(SHOCKS) - 1 - i
            ax.barh(y, r["median"], height=0.55, color=COLOR[s], zorder=2)
            ax.plot([r["p05"], r["p95"]], [y, y], color=INK, lw=1.2, zorder=3)
            ax.plot(rb["median"], y - 0.38, marker="v", ms=7, color=GREY, zorder=4,
                    markeredgecolor=SURFACE, markeredgewidth=1.0)
        ax.set_title(VAR_LABEL[v], loc="left")
        ax.set_yticks(range(len(SHOCKS)))
        ax.set_yticklabels([LABEL[s] for s in SHOCKS[::-1]] if v == "dy2" else [])
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.grid(axis="y", visible=False)
    h1, = axes[-1].plot([], [], marker="v", ls="", color=GREY, label="Median without stock-bond covariance")
    h2, = axes[-1].plot([], [], color=INK, lw=1.2, label="90% of identified set")
    fig.legend(handles=[h1, h2], loc="upper right", ncol=2, fontsize=8.5, bbox_to_anchor=(0.99, 0.95))
    _caption(fig, caption, "Share of daily innovation variance by structural shock, 1983-2025")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig1_variance_shares.png", dpi=200)
    plt.close(fig)


def fig_propagation(out: Path, caption: str):
    df = pd.read_csv(out / "test_b_propagation_ratios.csv")
    df = df[df["set"] == "baseline"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=False)
    for ax, o, ttl in zip(axes, ("y10", "y2", "slope"),
                          ("10-year yield", "2-year yield", "2s10s slope")):
        g = df[df["outcome"] == o].sort_values("h")
        h = g["h"].to_numpy()
        for s in SHOCKS:
            ax.fill_between(h, g[f"gamma_{s}_p05"], g[f"gamma_{s}_p95"], color=COLOR[s],
                            alpha=0.15, lw=0)
            ax.plot(h, g[f"gamma_{s}_med"], color=COLOR[s], lw=2, marker="o", ms=4,
                    label=LABEL[s])
        ax.axhline(0, color=AXIS, lw=1)
        ax.set_xticks([1, 5, 10, 20])
        ax.set_xlabel("Trading days after the shock (day-t move excluded)")
        ax.set_title(ttl, loc="left")
    axes[0].set_ylabel("Subsequent change, bp per 1-s.d. shock")
    axes[0].legend(loc="best", fontsize=8)
    _caption(fig, caption, "What follows a one-standard-deviation shock: subsequent drift by origin")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig2_propagation_by_origin.png", dpi=200)
    plt.close(fig)


def fig_split_vs_placebo(out: Path, caption: str):
    c = pd.read_csv(out / "test_c_draws.csv.gz")
    pl = pd.read_csv(out / "test_c_placebo.csv.gz")
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.6))
    for ax, h in zip(axes, (1, 5, 10, 20)):
        a = c[(c["outcome"] == "y10") & (c["h"] == h)]["incr_r2"] * 100
        b = pl[(pl["outcome"] == "y10") & (pl["h"] == h)]["incr_r2"] * 100
        bins = np.linspace(0, max(a.max(), b.quantile(0.99)) * 1.05, 40)
        ax.hist(b, bins=bins, color=GREY, alpha=0.55, label="Random rotation and split")
        ax.hist(a, bins=bins, color=COLOR["common_premium"], alpha=0.75,
                label="Sign-identified expectations/premium split")
        ax.axvline(np.quantile(b, 0.9), color=INK2, lw=1, ls="--")
        ax.set_title(f"h = {h} day{'s' if h > 1 else ''}", loc="left")
        ax.set_xlabel("Incremental R² over own move, %")
        ax.set_yticks([])
    axes[0].legend(loc="upper right", fontsize=7.5)
    _caption(fig, caption, "Does the expectations/premium split of today's 10-year move predict what follows?")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig3_split_vs_placebo.png", dpi=200)
    plt.close(fig)


def fig_oos(out: Path, caption: str):
    s = pd.read_csv(out / "oos_summary.csv")
    s = s[s["period"] == "2000-2025"]
    models = [("r2_m1_vs_m0", "Own move", "#2a78d6"), ("r2_m2_vs_m0", "+ curve state", "#eb6834"),
              ("r2_m3_vs_m0", "+ structural split", "#1baf7a"),
              ("r2_m4_vs_m0", "+ all innovations", "#eda100")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, o, ttl in zip(axes, ("y10", "y2", "slope"),
                          ("10-year yield", "2-year yield", "2s10s slope")):
        g = s[s["outcome"] == o].sort_values("h")
        x = np.arange(len(g))
        w = 0.19
        for i, (col, lab, colr) in enumerate(models):
            ax.bar(x + (i - 1.5) * w, g[col] * 100, width=w * 0.9, color=colr, label=lab, zorder=2)
        ax.axhline(0, color=INK2, lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels([f"h={h}" for h in g["h"]])
        ax.set_title(ttl, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Out-of-sample R² vs no-change forecast, %")
    axes[0].legend(loc="lower left", fontsize=8)
    _caption(fig, caption, "Real-time forecasts, 2000-2025: out-of-sample R-squared against a no-change forecast")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig4_oos.png", dpi=200)
    plt.close(fig)


def fig_episodes(out: Path, caption: str):
    ep = pd.read_csv(out / "episodes.csv")
    fig, ax = plt.subplots(figsize=(12, 3.9))
    for i, row in ep.iterrows():
        y = len(ep) - 1 - i
        pos_left = neg_left = 0.0
        for s in SHOCKS:
            v = row[f"{s}_bp"]
            left = pos_left if v >= 0 else neg_left + v
            ax.barh(y, abs(v), left=left, height=0.55, color=COLOR[s],
                    edgecolor=SURFACE, linewidth=1.5, label=LABEL[s] if i == 0 else None, zorder=2)
            if v >= 0:
                pos_left += v
            else:
                neg_left += v
        ax.plot(row["actual_bp"], y, marker="D", color=INK, ms=6, zorder=4,
                label="Actual 10-year change" if i == 0 else None)
        ax.text(max(pos_left, row["actual_bp"]) + 9, y, f"{row['actual_bp']:+.0f}bp",
                va="center", fontsize=8.5, color=INK)
    ax.set_yticks(range(len(ep)))
    ax.set_yticklabels(list(ep["episode"])[::-1])
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel("Cumulative contribution to the 10-year yield change, bp (median-target model)")
    fig.legend(loc="upper right", fontsize=8.5, ncol=5, bbox_to_anchor=(0.99, 0.95))
    ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + 25)
    ax.grid(axis="y", visible=False)
    _caption(fig, caption, "Why the 10-year moved: four pre-2026 episodes")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig5_episodes.png", dpi=200)
    plt.close(fig)


def fig_phase2(out: Path, caption: str):
    """Phase 2: does regime-specific identification make the split special?"""
    mvp = pd.read_csv(out / "test_c_structural_split.csv")
    mvp = mvp[mvp["set"] == "baseline"]
    p2 = pd.read_csv(out / "phase2" / "test_c_by_regime.csv")
    p2 = p2[p2["set"] == "window=250"]
    oos = pd.read_csv(out / "phase2" / "oos_summary_regime.csv")
    oos = oos[(oos["sample"] == "2000-2025") & (oos["outcome"] == "y2")].sort_values("h")
    series = [("Regimes pooled (MVP)", None, GREY), ("Hedge regime", "hedge", "#4a3aa7"),
              ("Co-movement regime", "co-movement", "#e87ba4")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9))
    for ax, o, ttl in zip(axes[:2], ("y10", "slope"), ("10-year yield", "2s10s slope")):
        x = np.arange(4)
        for i, (lab, reg, col) in enumerate(series):
            if reg is None:
                g = mvp[mvp["outcome"] == o].sort_values("h")
            else:
                g = p2[(p2["outcome"] == o) & (p2["regime"] == reg)].sort_values("h")
            ax.bar(x + (i - 1) * 0.27, g["share_draws_beat_placebo_p90"] * 100, width=0.25,
                   color=col, hatch="///" if reg is None else None, edgecolor=SURFACE,
                   label=lab, zorder=2)
        ax.axhline(50, color=INK2, lw=1, ls="--")
        ax.text(3.45, 51.5, "pre-registered bar", ha="right", fontsize=7.5, color=INK2)
        ax.set_xticks(x)
        ax.set_xticklabels(["h=1", "h=5", "h=10", "h=20"])
        ax.set_ylim(0, 60)
        ax.set_title(ttl, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Admissible draws beating random splits, %")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, fontsize=8.5, bbox_to_anchor=(0.99, 0.95))
    ax = axes[2]
    gain = oos["r2_m3r_vs_m2"].to_numpy() * 100
    ax.bar(np.arange(len(oos)), gain, width=0.55, color=INK2, zorder=2)
    for i, (gv, pv) in enumerate(zip(gain, oos["cw_p_m3r"])):
        ax.text(i, gv + 0.015, f"p={pv:.3f}" if pv >= 0.001 else "p<0.001", ha="center",
                fontsize=8, color=INK)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_ylim(min(0.0, gain.min() * 1.2), gain.max() * 1.2)
    ax.set_xticks(np.arange(len(oos)))
    ax.set_xticklabels([f"h={h}" for h in oos["h"]])
    ax.set_ylabel("Real-time R² gain over curve-state model, pp")
    ax.set_title("2-year yield, 2000-2025", loc="left")
    ax.grid(axis="x", visible=False)
    _caption(fig, caption, "Phase 2: identifying the shocks within each stock-bond regime")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig6_phase2_regimes.png", dpi=200)
    plt.close(fig)


CAPTIONS = {
    "fig1": ("Monetary and growth news explain about 70% of daily 2-year variance and the two premium shocks "
             "about 75% of 10-year variance; over 1983-2025 removing the stock-bond co-movement (grey "
             "triangles) barely moves these shares, because two stock-bond regimes of opposite sign cancel."),
    "fig2": ("News about the policy path keeps moving the front end: a one-standard-deviation growth or "
             "monetary shock adds roughly another 1bp to the 2-year over 20 days (a quarter to a third of its "
             "impact) and a flight to quality keeps pulling it down; at the 10-year only growth news "
             "keeps moving it over a month. Bands: 90% of the identified set."),
    "fig3": ("Splitting today's 10-year move into its expectations and premium parts adds a median of "
             "0.01-0.08% of R-squared and beats the 90th percentile of random splits (dashed) in at most 5% "
             "of admissible draws: the direction is coherent, but the split is not special."),
    "fig4": ("No model reliably beats a no-change forecast of yields in real time; adding the structural split "
             "changes out-of-sample R-squared by less than 0.1 percentage point."),
    "fig6": ("Within the co-movement regime the expectations/premium split beats random splits in 26-39% of "
             "admissible draws for the slope at 5-20 days (44% for the 10-year at one day), against at most 9% with "
             "regimes pooled, but never in a majority; in real time it improves 2-year forecasts at every "
             "horizon, though no model beats a no-change forecast."),
    "fig5": ("The model reads the 2013 taper tantrum and the late-2024 selloff as risk-premium episodes, 2022 as "
             "monetary news plus a loss of Treasuries' hedging value, and early 2020 as a flight to quality."),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    fig_variance_shares(out, CAPTIONS["fig1"])
    fig_propagation(out, CAPTIONS["fig2"])
    fig_split_vs_placebo(out, CAPTIONS["fig3"])
    fig_oos(out, CAPTIONS["fig4"])
    fig_episodes(out, CAPTIONS["fig5"])
    if (out / "phase2" / "test_c_by_regime.csv").exists():
        fig_phase2(out, CAPTIONS["fig6"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
