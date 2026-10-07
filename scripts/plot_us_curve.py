"""Figures 18-22: the US Treasury curve through the frozen cross-Atlantic model.

Reads ``reports/structural_propagation/us_curve/`` (written by ``run_us_curve.py``) and
writes the figures beside the earlier ones in ``reports/structural_propagation/``.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "reports" / "structural_propagation"
D = REP / "us_curve"
PRIV = D / "lseg_private"

GREY, INK, INK2, GRID, AXIS, SURFACE = "#898781", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
GROUPS = {"us_macro": ("US macro", "#eda100"), "us_monetary": ("US monetary", "#4a3aa7"),
          "global_risk": ("Global risk", "#e34948"), "ea": ("Euro area", "#2a78d6")}
UNSP = ("Unspanned (curve-specific)", "#b9b7ae")
TENORS = {"y2": "2-year", "y5": "5-year", "y10": "10-year", "y30": "30-year"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9.5,
    "legend.frameon": False, "axes.titlesize": 10.5, "axes.titleweight": "bold"})


def finish(fig, title, caption, name):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=INK)
    caption = textwrap.fill(caption.replace("\n", " "), 175)
    fig.text(0.01, 0.012, caption, ha="left", va="bottom", fontsize=8.6, color=INK2)
    fig.savefig(REP / name, dpi=200)
    plt.close(fig)
    print("wrote", name)


def grouped(row, suffix="_bp"):
    return {"us_macro": row[f"us_macro{suffix}"], "us_monetary": row[f"us_monetary{suffix}"],
            "global_risk": row[f"global_risk{suffix}"],
            "ea": row[f"ea_monetary{suffix}"] + row[f"ea_macro{suffix}"]}


def stacked_bar(ax, y, parts, unsp, actual, height=0.62):
    pos, neg = 0.0, 0.0
    for g, v in parts.items():
        left = pos if v >= 0 else neg
        ax.barh(y, v, left=left, color=GROUPS[g][1], height=height, edgecolor=SURFACE, lw=1.2, zorder=2)
        if abs(v) >= 9:
            ax.text(left + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=8,
                    color=INK if g in ("us_macro", "global_risk") else "white", zorder=4)
        if v >= 0:
            pos += v
        else:
            neg += v
    left = pos if unsp >= 0 else neg
    ax.barh(y, unsp, left=left, color=UNSP[1], height=height, edgecolor=SURFACE, lw=1.2, zorder=2, hatch="///")
    ax.plot([actual], [y], marker="D", ms=7, color=INK, zorder=5, mec=SURFACE, mew=1.2)
    ax.text(max(pos + max(unsp, 0), actual) + 7, y, f"{actual:+.0f}bp", va="center", fontsize=9,
            fontweight="bold", color=INK)


# ---------------------------------------------------------------- 18: cumulative
def fig_cumulative(win):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharex=True)
    for ax, wlab in zip(axes, ("2026 to date", "27 Feb-19 Aug 2026")):
        w = win[win.window == wlab].set_index("outcome")
        for i, (o, lab) in enumerate(TENORS.items()):
            r = w.loc[o]
            stacked_bar(ax, -i, grouped(r), r["unspanned_bp"], r["actual_bp"])
            ax.plot([r["us_p05"], r["us_p95"]], [-i - 0.42] * 2, color=INK2, lw=1.4, zorder=3)
            ax.plot([r["us_p05"]] * 2 + [r["us_p95"]] * 2, [-i - 0.37, -i - 0.47, -i - 0.37, -i - 0.47],
                    color=INK2, lw=0)
        ax.set_yticks([-i for i in range(4)], list(TENORS.values()) if ax is axes[0] else [""] * 4)
        ax.set_xlim(-30, 172)
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(f"{wlab} (to {LAST})" if wlab.startswith("2026") else wlab, loc="left")
        ax.set_xlabel("Change in yield, bp")
        ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in GROUPS.values()]
    handles += [plt.Rectangle((0, 0), 1, 1, fc=UNSP[1], hatch="///", ec=SURFACE),
                plt.Line2D([], [], marker="D", color=INK, ls="", ms=7),
                plt.Line2D([], [], color=INK2, lw=1.4)]
    labels = [l for l, _ in GROUPS.values()] + [UNSP[0], "Actual change", "US news, 90% of identified set"]
    fig.legend(handles, labels, ncol=7, loc="upper left", bbox_to_anchor=(0.01, 0.93), fontsize=8.6)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.80, bottom=0.2, wspace=0.12)
    finish(fig, "18. The 2026 Treasury selloff was US news, plus a front-end move the cross-asset shocks cannot see",
           "Frozen synchronised cross-Atlantic model (Brandt et al. shocks, 2007-2025) with Treasury maturities attached by "
           "projection on the shocks.\nMedian-target model; whisker under each bar: 90% of the identified set for the US-news "
           "total. Unspanned: the part of the move that is not a linear function of the five shocks. H.15 constant-maturity yields.",
           "fig18_us_curve_cumulative.png")


# ---------------------------------------------------------------- 19: time variation
def fig_time(roll):
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.2), sharex=True)
    for ax, (o, lab) in zip(axes.flat, TENORS.items()):
        df = pd.read_csv(PRIV / f"daily_{o}.csv", index_col=0, parse_dates=True)
        df["ea"] = df["ea_monetary"] + df["ea_macro"]
        cum = df.fillna(0).cumsum()
        for g, (gl, c) in GROUPS.items():
            ax.plot(cum.index, cum[g], color=c, lw=2, label=gl, ls="-" if g != "ea" else (0, (4, 2)))
        ax.plot(cum.index, cum["unspanned"], color=GREY, lw=1.4, ls=":", label=UNSP[0])
        ax.plot(cum.index, cum["actual"], color=INK, lw=2.6, label="Actual change")
        ax.axvspan(pd.Timestamp("2026-02-27"), pd.Timestamp("2026-08-19"), color=GRID, alpha=0.45, lw=0, zorder=0)
        # leader strip: rolling 20-day leading shock
        r = roll[roll.outcome == o]
        y0 = ax.get_ylim()[0]
        ds = list(r["date"]) + [r["date"].iloc[-1] + pd.Timedelta(days=1)]
        for i, lead in enumerate(r["leader_mt"]):
            ax.plot([ds[i], ds[i + 1]], [y0] * 2, color=GROUPS["ea" if lead.startswith("ea") else lead][1],
                    lw=7, solid_capstyle="butt")
        ax.axhline(0, color=AXIS, lw=1)
        ax.set_title(lab, loc="left")
        ax.set_ylabel("Cumulative change since 31 Dec 2025, bp")
        end = cum.iloc[-1]
        ax.text(cum.index[-1] + pd.Timedelta(days=3), end["actual"], f"{end['actual']:+.0f}", va="center",
                fontsize=9, fontweight="bold")
    axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=6, loc="upper left", bbox_to_anchor=(0.01, 0.945), fontsize=8.6)
    fig.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.11, hspace=0.18, wspace=0.14)
    finish(fig, "19. US macro news led for most of the year; monetary news in late June, risk sentiment in August",
           "Cumulative contributions, median-target model. Thick strip along the bottom of each panel: the shock with the largest "
           "absolute contribution over the trailing 20 trading days. Shaded: 27 Feb-19 Aug. The leader within US news (macro "
           "versus monetary) is not robust across the identified set; US origin is.",
           "fig19_us_curve_time.png")


# ---------------------------------------------------------------- 20: cross-section
def fig_cross(win, sig):
    fig = plt.figure(figsize=(13, 5.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.1, 1.0], wspace=0.28)
    ax = fig.add_subplot(gs[0])
    w = win[win.window == "2026 to date"].set_index("outcome")
    mats = [2, 5, 10, 30]
    xs = np.arange(4)
    actual = [w.loc[f"y{m}", "actual_bp"] for m in mats]
    explained = [w.loc[f"y{m}", "actual_bp"] - w.loc[f"y{m}", "unspanned_bp"] for m in mats]
    us = [w.loc[f"y{m}", "us_bp"] for m in mats]
    ax.plot(xs, actual, color=INK, lw=2.6, marker="D", ms=7, label="Actual change")
    ax.plot(xs, explained, color="#4a3aa7", lw=2, marker="o", ms=7, label="Explained by the five shocks")
    ax.plot(xs, us, color="#eda100", lw=2, marker="s", ms=6, ls="--", label="of which US news")
    ax.fill_between(xs, explained, actual, color=UNSP[1], alpha=0.5, lw=0, label="Unspanned")
    for x, a in zip(xs, actual):
        ax.text(x, a + 5, f"{a:+.0f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(xs, ["2y", "5y", "10y", "30y"])
    ax.set_ylabel("Change in 2026 to date, bp")
    ax.set_ylim(0, 165)
    ax.set_title("The 2026 change along the curve", loc="left")
    ax.legend(loc="lower left", fontsize=8.4)

    bx = fig.add_subplot(gs[1])
    for g in ("us_macro", "us_monetary", "global_risk", "ea_monetary"):
        s = sig[sig.shock == g].set_index("outcome").loc[[f"y{m}" for m in mats]]
        c = GROUPS["ea" if g.startswith("ea") else g][1]
        bx.plot(xs, s["bp_per_sd_mt"], color=c, lw=2, marker="o", ms=6,
                label={"ea_monetary": "Euro-area monetary"}.get(g, GROUPS.get(g, ("", ""))[0]))
        bx.fill_between(xs, s["p05"], s["p95"], color=c, alpha=0.12, lw=0)
    bx.axhline(0, color=INK2, lw=1)
    bx.set_xticks(xs, ["2y", "5y", "10y", "30y"])
    bx.set_ylabel("bp per one-standard-deviation shock")
    bx.set_title("Each shock's curve signature, 2007-2025", loc="left")
    bx.legend(fontsize=8.4, loc="lower left")

    cx = fig.add_subplot(gs[2])
    for i, (o, lab) in enumerate((("s2s10", "2s10s"), ("s10s30", "10s30s"))):
        r = w.loc[o]
        stacked_bar(cx, -i, grouped(r), r["unspanned_bp"], r["actual_bp"], height=0.5)
    cx.set_yticks([0, -1], ["2s10s", "10s30s"])
    cx.axvline(0, color=INK2, lw=1)
    cx.set_xlabel("Change in slope, bp")
    cx.set_title("Slopes, 2026 to date", loc="left")
    cx.grid(axis="y", visible=False)
    cx.set_xlim(-95, 75)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.85, bottom=0.2)
    finish(fig, "20. The long end is explained; the front end's extra rise, and so the flattening, is not",
           "Left: 2026 to date, median-target model. Middle: total loading (impact plus two days) of each Treasury maturity on a "
           "one-standard-deviation shock, median-target model with 90% of the identified set shaded. Every shock moves the 10-year "
           "more than the 2-year: the shocks are identified from 10-year rates, so all of them steepen. Right: slope "
           "decompositions; diamonds are actual changes, colours as in figure 18.",
           "fig20_us_curve_cross_section.png")


# ---------------------------------------------------------------- 21: Brandt vs ACM
def fig_acm(win, monthly):
    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.22)
    ax = fig.add_subplot(gs[0])
    w = win[win.window == "2026 to date"].set_index("outcome")
    xs = np.arange(3)
    width = 0.36
    for i, m in enumerate((2, 5, 10)):
        rn, tp = w.loc[f"rn{m}", "actual_bp"], w.loc[f"tp{m}", "actual_bp"]
        ax.bar(i - width / 2, rn, width, color="#1c5cab", zorder=2, edgecolor=SURFACE)
        ax.bar(i - width / 2, tp, width, bottom=rn, color="#9ec5f4", zorder=2, edgecolor=SURFACE)
        r = w.loc[f"acm{m}"]
        parts = grouped(r)
        bottom = 0.0
        for g in ("us_macro", "us_monetary", "global_risk", "ea"):
            v = parts[g]
            ax.bar(i + width / 2, v, width, bottom=bottom if v >= 0 else 0, color=GROUPS[g][1], zorder=2,
                   edgecolor=SURFACE)
            bottom += max(v, 0)
        u = r["unspanned_bp"]
        ax.bar(i + width / 2, u, width, bottom=bottom if u >= 0 else 0, color=UNSP[1], hatch="///",
               zorder=2, edgecolor=SURFACE)
        ax.text(i - width / 2, rn / 2, f"{rn:.0f}", ha="center", va="center", color="white", fontsize=8.5)
        ax.text(i - width / 2, rn + tp / 2, f"{tp:.0f}", ha="center", va="center", color=INK, fontsize=8.5)
        ax.text(i - width / 2, rn + tp + 3, "NY Fed ACM", ha="center", fontsize=8, color=INK2)
        ax.text(i + width / 2, max(bottom + max(u, 0), r["actual_bp"]) + 3, "Structural", ha="center",
                fontsize=8, color=INK2)
    ax.set_xticks(xs, ["2-year", "5-year", "10-year"])
    ax.set_ylabel("Change in 2026 to date, bp (ACM fitted yield)")
    ax.set_title("Two decompositions of the same yield change", loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color="#1c5cab"), plt.Rectangle((0, 0), 1, 1, color="#9ec5f4")]
    handles += [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in GROUPS.values()]
    handles += [plt.Rectangle((0, 0), 1, 1, fc=UNSP[1], hatch="///", ec=SURFACE)]
    ax.legend(handles, ["ACM expected rates", "ACM term premium"] + [l for l, _ in GROUPS.values()] + ["Unspanned"],
              fontsize=8.2, ncol=4, loc="upper left")
    ax.set_ylim(-20, 205)
    ax.grid(axis="x", visible=False)

    bx = fig.add_subplot(gs[1])
    m = monthly
    for col, c, lab in (("rn10", "#1c5cab", "ACM expected rates"), ("tp10", "#9ec5f4", "ACM term premium")):
        for per, mk, a in (("2007-2025", "o", 0.25 if col == "rn10" else 0.6), ("2026", "D", 1.0)):
            s = m[m.period == per]
            bx.scatter(s["us_part"], s[col], s=18 if per != "2026" else 46, marker=mk, color=c, alpha=a,
                       edgecolor=INK if per == "2026" else "none", lw=0.6,
                       label=f"{lab}, {per}")
    lim = 80
    bx.plot([-lim, lim], [-lim, lim], color=AXIS, lw=1, ls="--")
    bx.set_xlim(-lim, lim)
    bx.set_ylim(-lim, lim)
    bx.set_xlabel("US-news contribution to the 10-year, monthly, bp")
    bx.set_ylabel("Monthly change in ACM component, bp")
    bx.set_title("Which ACM component moves with US news (10-year)", loc="left")
    bx.legend(fontsize=8, loc="upper left")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.85, bottom=0.2)
    finish(fig, "21. Both decompositions agree that 2026 was mostly an expected-rate selloff",
           "Left: NY Fed daily ACM split of its fitted yield (expected rates plus term premium) beside the structural decomposition of "
           "the same fitted yield. Right: monthly sums. In 2026 the US-news contribution moves one for one with ACM expected rates "
           "(correlation 0.86) and less with the term premium (0.49); in 2007-2025, when policy rates were near zero for "
           "much of the sample, the same news moved the term premium more (0.65 against 0.43). Right panel exploratory.",
           "fig21_us_curve_vs_acm.png")


# ---------------------------------------------------------------- 22: forecasting
def fig_forecast(fs, fz, ap):
    fig = plt.figure(figsize=(13, 5.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.25)
    ax = fig.add_subplot(gs[0])
    mats = ["y2", "y5", "y10", "y30"]
    xs = np.arange(4)
    ins = [fz["in_sample_fit"][o]["r2_daily_mt"] * 100 for o in mats]
    oos = [ap["fit_2026"][o]["daily"]["r2"] * 100 for o in mats]
    ax.bar(xs - 0.19, ins, 0.36, color="#9ec5f4", label="2007-2025 (in sample)", zorder=2)
    ax.bar(xs + 0.19, oos, 0.36, color="#1c5cab", label="2026 (frozen loadings)", zorder=2)
    for x, a, b in zip(xs, ins, oos):
        ax.text(x - 0.19, a + 1.5, f"{a:.0f}", ha="center", fontsize=8.5)
        ax.text(x + 0.19, b + 1.5, f"{b:.0f}", ha="center", fontsize=8.5)
        ap_rmse = ap["fit_2026"][mats[x]]["daily"]["rmse_bp"]
        ax.text(x + 0.19, 5, f"RMSE\n{ap_rmse:.1f}bp", ha="center", fontsize=7.5, color="white")
    ax.set_xticks(xs, ["2y", "5y", "10y", "30y"])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Share of daily variance explained, %")
    ax.set_title("Explaining today's move: high, and stable in 2026", loc="left")
    ax.legend(fontsize=8.4, loc="upper left")
    ax.grid(axis="x", visible=False)

    bx = fig.add_subplot(gs[1])
    s = fs[(fs["from"] == "next close")]
    models = (("r2_m1", "Own move", "#9ec5f4"), ("r2_m2", "+ curve state", "#5598e7"),
              ("r2_m3", "+ origin of today's news", "#eda100"), ("r2_m4", "+ all cross-asset news", "#4a3aa7"))
    labels, y = [], 0
    for o in mats:
        for h in (1, 5, 20):
            row = s[(s.outcome == o) & (s.h == h) & (s.period == "2012-2025")].iloc[0]
            row26 = s[(s.outcome == o) & (s.h == h) & (s.period == "2026")].iloc[0]
            for k, (col, lab, c) in enumerate(models):
                bx.scatter(row[col] * 100, -y, color=c, s=34, zorder=3, label=lab if y == 0 else None)
                bx.scatter(row26[col] * 100, -y - 0.3, color=c, s=20, marker="D", zorder=3, alpha=0.7,
                           edgecolor=INK, lw=0.4, label="2026 (diamonds, same colours)" if (y == 0 and k == 3) else None)
            labels.append((-y - 0.15, f"{o[1:]}y, {h}d"))
            y += 1
        y += 0.4
    bx.axvline(0, color=INK, lw=1.2)
    bx.set_yticks([p for p, _ in labels], [l for _, l in labels], fontsize=8)
    bx.set_xlabel("Out-of-sample R² against a no-change forecast (vertical line), % (from the next close)")
    bx.set_xlim(-45, 5)
    bx.set_title("Forecasting the next move: nothing beats no change", loc="left")
    bx.legend(fontsize=7.8, loc="lower left", ncol=1)
    bx.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.85, bottom=0.2)
    finish(fig, "22. The structure explains each day's curve move but does not predict the next one",
           "Left: explanatory R² of the five shocks (impact plus two days) for daily H.15 yield changes, and 2026 RMSE with the "
           "loadings frozen at end-2025. Right: real-time forecasts, expanding window, model and loadings re-estimated each year "
           "(circles, 2012-2025) and frozen (diamonds, 2026). Changes start at the next close. Values below -45% clipped.",
           "fig22_us_curve_forecasting.png")


def main() -> int:
    global LAST
    win = pd.read_csv(D / "decomposition_windows.csv")
    sig = pd.read_csv(D / "signatures.csv")
    roll = pd.read_csv(PRIV / "rolling20_leaders.csv", parse_dates=["date"])
    ap = json.loads((D / "apply_summary.json").read_text())
    fz = json.loads((D / "freeze_summary.json").read_text())
    LAST = pd.Timestamp(ap["last_day"]).strftime("%-d %b")
    fs = pd.read_csv(D / "forecast_summary.csv")
    monthly = pd.read_csv(PRIV / "monthly_bridge.csv")
    fig_cumulative(win)
    fig_time(roll)
    fig_cross(win, sig)
    fig_acm(win, monthly)
    fig_forecast(fs, fz, ap)
    return 0


LAST = ""
if __name__ == "__main__":
    raise SystemExit(main())
