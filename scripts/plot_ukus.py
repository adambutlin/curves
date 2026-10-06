"""Figures for the UK-US models and the 2026 gilt selloff (figures 15-17)."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import plot_brandt_2026 as base  # noqa: E402  (shared style, caption and cumulative-panel helpers)

ROOT = Path(__file__).resolve().parents[1]
INK, INK2, SURFACE = base.INK, base.INK2, base.SURFACE
UK_SHOCKS = {"uk_monetary": ("UK monetary", "#2a78d6", "-"),
             "uk_macro": ("UK macro", "#1baf7a", "-"),
             "uk_risk_premium": ("UK risk premium", "#008300", "-."),
             "us_monetary": ("US monetary", "#4a3aa7", "--"),
             "us_macro": ("US macro", "#eda100", "--"),
             "global_risk": ("Global risk", "#e34948", "-")}
EPISODE = ["2016-06-24", "2016-08-04", "2022-09-23", "2022-09-26", "2022-09-28", "2022-10-17"]


def _stacked(ax, ev, shocks):
    ev = ev.iloc[::-1].reset_index(drop=True)
    for i, row in ev.iterrows():
        pos = neg = 0.0
        for s in shocks:
            col = f"{s}_bp"
            if col not in row or pd.isna(row[col]):
                continue
            v = row[col]
            left = pos if v >= 0 else neg + v
            ax.barh(i, abs(v), left=left, height=0.6, color=UK_SHOCKS[s][1], edgecolor=SURFACE,
                    linewidth=1.2, zorder=2)
            pos, neg = (pos + v, neg) if v >= 0 else (pos, neg + v)
        ax.plot(row["actual_2d_bp"], i, marker="D", color=INK, ms=6, zorder=4)
    ax.set_yticks(range(len(ev)))
    ax.set_yticklabels([f"{r.date}  {r.event}" for r in ev.itertuples()], fontsize=8)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel("Two-day 10-year gilt change by shock, bp (median-target model)")
    ax.grid(axis="y", visible=False)


def fig_minibudget(rep: Path, out: Path):
    evA = pd.read_csv(rep / "ukus_A" / "event_study.csv")
    evB = pd.read_csv(rep / "ukus_B" / "event_study.csv")
    evA, evB = evA[evA["date"].isin(EPISODE)], evB[evB["date"].isin(EPISODE)]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.4), sharex=True)
    _stacked(a, evA, [s for s in UK_SHOCKS if s != "uk_risk_premium"])
    _stacked(b, evB, list(UK_SHOCKS))
    b.set_yticklabels([])
    a.set_title("Model A: Brandt et al.'s five shocks", loc="left")
    b.set_title("Model B: plus a UK risk-premium shock", loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=UK_SHOCKS[s][1]) for s in UK_SHOCKS]
    handles.append(plt.Line2D([], [], marker="D", ls="", color=INK))
    fig.legend(handles, [UK_SHOCKS[s][0] for s in UK_SHOCKS] + ["Actual"], loc="upper left", ncol=7,
               fontsize=8, bbox_to_anchor=(0.01, 0.93))
    base._finish(fig, out, "fig15_uk_minibudget.png", "Can the model see a fiscal scare? The 2022 mini-budget",
                 "Without a shock in which gilts sell off while sterling falls, Model A reads the mini-budget as UK "
                 "growth and policy news; in Model B the UK risk premium is the largest component of every "
                 "mini-budget day, while Brexit reads as UK monetary easing plus a global risk-off.")


def fig_2026_gilts(app: Path, out: Path):
    priv = app / "lseg_private"
    g10 = pd.read_csv(priv / "daily_ukus_B_uk10.csv", index_col=0, parse_dates=True)
    g2 = pd.read_csv(priv / "daily_ukus_B_uk2.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    base._cum_panel(axes[0], g10, UK_SHOCKS, "10-year gilt")
    base._cum_panel(axes[1], g2, UK_SHOCKS, "2-year gilt")
    axes[1].set_ylabel("")
    axes[0].legend(loc="upper left", fontsize=7.5)
    base._finish(fig, out, "fig16_2026_gilts.png",
                 "The 2026 gilt selloff through the frozen UK-US model with a risk-premium shock (Model B)",
                 "US news and global risk sentiment drove most of the gilt selloff; the UK risk-premium shock, the "
                 "signature of a fiscal-credibility scare, subtracted 7bp from the 10-year gilt over 2026 to date.")


def fig_2026_window(app: Path, out: Path):
    w = pd.read_csv(app / "ukus_decomposition_windows.csv")
    panels = [("UK-US model A", "27 Feb-19 Aug 2026", "Model A, 27 Feb-19 Aug"),
              ("UK-US model B", "27 Feb-19 Aug 2026", "Model B, 27 Feb-19 Aug"),
              ("UK-US model B", "2026 to date", "Model B, 2026 to date")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.4), sharex=True)
    for ax, (model, window, title) in zip(axes, panels):
        r = w[(w["model"] == model) & (w["window"] == window) & (w["outcome"] == "uk10")].iloc[0]
        names = [s for s in UK_SHOCKS if f"{s}_bp" in r and pd.notna(r[f"{s}_bp"])]
        y = np.arange(len(names))[::-1]
        for yi, s in zip(y, names):
            ax.barh(yi, r[f"{s}_bp"], color=UK_SHOCKS[s][1], height=0.6, zorder=2)
            ax.plot([r[f"{s}_p05"], r[f"{s}_p95"]], [yi, yi], color=INK, lw=1.2, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([UK_SHOCKS[s][0] for s in names], fontsize=8)
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(f"{title}\n10-year gilt {r['actual_bp']:+.0f}bp", loc="left", fontsize=9.5)
        ax.set_xlabel("Contribution, bp")
        ax.grid(axis="y", visible=False)
    base._finish(fig, out, "fig17_2026_gilt_window.png",
                 "Who moved gilts in 2026 (bars: median-target model; lines: 90% of identified set)",
                 "Imported news dominates in both models; the domestic part of the selloff-window rise is Bank of "
                 "England repricing of the sterling-strengthening kind, and the UK risk premium's band includes zero.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=str(ROOT / "reports" / "structural_propagation"))
    args = ap.parse_args(argv)
    rep = Path(args.reports)
    fig_minibudget(rep, rep)
    if (rep / "application_2026" / "lseg_private" / "daily_ukus_B_uk10.csv").exists():
        fig_2026_gilts(rep / "application_2026", rep)
    fig_2026_window(rep / "application_2026", rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
