"""Figures for the 2026 Treasury selloff note, drawn from ``output/data/`` only.

Each figure is written twice: ``output/figures/<name>.png`` (200 dpi) and ``.svg``, both
with the conclusion title and one-sentence caption baked in, so the image stands alone.
The research page embeds untitled versions (its own headings carry the titles).
"""
from __future__ import annotations

import io
import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
COLOR = {"us_news": "#2a78d6", "global_risk": "#eb6834", "euro_area": "#1baf7a",
         "unspanned": "#b3b1a9", "all_shocks": "#52514e", "us_macro": "#2a78d6", "us_monetary": "#2a78d6"}
LABEL = {"us_news": "US news", "global_risk": "Global risk sentiment", "euro_area": "Euro-area news",
         "unspanned": "Unspanned (curve-specific news)", "all_shocks": "All cross-asset shocks",
         "us_macro": "US macro news", "us_monetary": "US monetary news"}
ORIGINS = ("us_news", "global_risk", "euro_area")
MATURITY_NAME = {"2y": "2-year", "5y": "5-year", "10y": "10-year", "30y": "30-year",
                 "2s10s": "2s10s slope", "10s30s": "10s30s slope"}
FULL = "30 Dec 2025 to 5 Oct 2026"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "treasury-selloff-2026",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2, "axes.labelsize": 9.5,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 5, "ytick.major.pad": 5,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "legend.frameon": False, "legend.fontsize": 9, "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round", "axes.axisbelow": True})

TITLES = {
    "fig1_10y_decomposition":
        "The 2026 rise in the 10-year Treasury yield tracked US news",
    "fig2_curve":
        "Long maturities moved with cross-asset news; the front end added a repricing of its own",
    "fig3_monthly":
        "The selloff came in three up-legs, March, July and September, each led by US news",
    "fig4_identification":
        "What the data pin down: the front-end gap and the US origin, not macro versus monetary",
    "fig5_forecasting":
        "The decomposition explains each day's move but says nothing about the next",
}
CAPTIONS = {
    "fig1_10y_decomposition":
        "Cumulative change in the 10-year H.15 yield since the close of 30 December 2025 and the contributions of the "
        "identified cross-asset shocks in the median-target model; the shaded band is the 5\u201395% range of the "
        "US-news contribution across the 1,000 admissible models, which by 5 October spans {us05:.0f}\u2013{us95:.0f}bp "
        "of the {actual:.0f}bp rise.",
    "fig2_curve":
        "Contributions to each yield and slope between the closes of 30 December 2025 and 5 October 2026 (median-target model; "
        "diamond = actual change): the part no cross-asset shock explains is {u2:.0f}bp of the 2-year's rise "
        "({u2lo:.0f}\u2013{u2hi:.0f} across admissible models) and the whole of the 2s10s flattening, which the shocks "
        "themselves steepened by {s2:.0f}bp ({s2lo:.0f}\u2013{s2hi:.0f}).",
    "fig3_monthly":
        "Monthly contributions to the 10-year and 2-year yields (median-target model; dot = actual change; "
        "January from the 30 December close, October to the 5th); the percentages are the share of admissible models in which US news is the largest "
        "of the three origins, high in the months that carried the selloff; at the 2-year the unspanned front-end "
        "repricing (grey) added to the March, June and September rises.",
    "fig4_identification":
        "Contributions to the change from 30 December 2025 to 5 October 2026 across the 1,000 admissible models "
        "(dot = median, line = 5\u201395%, open diamond = the median-target model used in Figures 1\u20133): the split "
        "between spanned and unspanned news does not depend on the sign restrictions at all, US news is positive in "
        "every model, but US macro news exceeds US monetary news in only {pm:.0f}% of them.",
    "fig5_forecasting":
        "Left: share of the daily variance of each yield explained by the five shocks, with loadings frozen at "
        "end-2025; right: real-time out-of-sample R\u00b2 against a no-change forecast for the change over the next "
        "1, 5 and 20 days from the next close: knowing the origin of today's news adds nothing to the day's own move "
        "and the curve state, and neither beats no change (2026 gives the same answer); the one positive value is "
        "an artefact of H.15 yields being recorded before the New York close.",
}


# ---------------------------------------------------------------- helpers
def _finish(fig, name: str, standalone: bool, fmt: dict | None = None, title_y: float = 0.995):
    if standalone:
        fig.suptitle(TITLES[name], x=0.012, y=title_y, ha="left", va="top", fontsize=13,
                     fontweight="bold", color=INK)
        cap = CAPTIONS[name].format(**(fmt or {}))
        width = int(fig.get_size_inches()[0] * 13.2)
        fig.text(0.012, -0.01, textwrap.fill(cap, width), ha="left", va="top", fontsize=8.8,
                 style="italic", color=INK2)
    return fig


def _save(fig, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.15, metadata={"Software": None})
    fig.savefig(out / f"{name}.svg", bbox_inches="tight", pad_inches=0.15, metadata={"Date": None})
    plt.close(fig)


def svg_string(fig, prefix: str) -> str:
    """Inline SVG for the research page: ids prefixed so several figures can share one page,
    sized by the page rather than in points."""
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.05, metadata={"Date": None})
    plt.close(fig)
    s = buf.getvalue()
    s = s[s.index("<svg"):]
    s = re.sub(r"<metadata>.*?</metadata>\s*", "", s, flags=re.S)
    s = re.sub(r'id="([^"]+)"', rf'id="{prefix}-\1"', s)
    s = re.sub(r"url\(#([^)]+)\)", rf"url(#{prefix}-\1)", s)
    s = re.sub(r'xlink:href="#([^"]+)"', rf'xlink:href="#{prefix}-\1"', s)
    s = re.sub(r'<svg([^>]*?) width="[^"]+" height="[^"]+"', r'<svg\1', s, count=1)
    return s.replace("<svg", '<svg role="img" preserveAspectRatio="xMidYMid meet"', 1)


def _spread_labels(values: list[float], gap: float, lo: float) -> list[float]:
    """Vertical label positions: as close to ``values`` as possible, at least ``gap`` apart."""
    order = np.argsort(values)[::-1]
    pos = np.empty(len(values))
    prev = np.inf
    for i in order:
        pos[i] = min(values[i], prev - gap)
        prev = pos[i]
    shift = max(0.0, lo - pos.min())
    return list(pos + shift)


def _bp(x: float) -> str:
    return f"{x:+.0f}".replace("-", "−")


# ---------------------------------------------------------------- figure 1
def fig1(daily: pd.DataFrame, standalone: bool = True):
    x = pd.to_datetime(daily["date"])
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.fill_between(x, daily["us_news_p05"], daily["us_news_p95"], color=COLOR["us_news"], alpha=0.13, lw=0,
                    zorder=1)
    ax.axhline(0, color=AXIS, lw=1, zorder=1)
    for key, lw in (("unspanned", 1.8), ("euro_area", 2), ("global_risk", 2), ("us_news", 2.2)):
        ax.plot(x, daily[key], color=COLOR[key], lw=lw, zorder=3)
    ax.plot(x, daily["actual"], color=INK, lw=2.6, zorder=4)
    lo, hi = -40, 135
    ax.set_ylim(lo, hi)
    for d, txt in (("2026-02-27", "27 Feb: yields at their 2026 low"), ("2026-08-19", "19 Aug: second leg")):
        ax.axvline(pd.Timestamp(d), color=AXIS, lw=1, zorder=0)
        ax.text(pd.Timestamp(d) + pd.Timedelta(days=2), hi - 4, txt, fontsize=8.6, color=INK2, va="top")
    # end labels with leader lines
    end = daily.iloc[-1]
    keys = ["actual", "us_news", "global_risk", "unspanned", "euro_area"]
    names = {"actual": "Actual", "us_news": "US news", "global_risk": "Global risk sentiment",
             "unspanned": "Unspanned", "euro_area": "Euro-area news"}
    vals = [float(end[k]) for k in keys]
    pos = _spread_labels(vals, gap=10.5, lo=lo + 6)
    x_end = x.iloc[-1]
    x_lab = x_end + pd.Timedelta(days=9)
    for k, v, p in zip(keys, vals, pos):
        ax.plot([x_end, x_end + pd.Timedelta(days=6), x_lab], [v, p, p], color=AXIS, lw=0.8, zorder=2,
                clip_on=False)
        ax.plot([x_end], [v], marker="o", ms=5.5, color=COLOR.get(k, INK), mec=SURFACE, mew=1.5, zorder=5,
                clip_on=False)
        ax.text(x_lab + pd.Timedelta(days=1.5), p, f"{names[k]}  {_bp(v)}", va="center", fontsize=9.2,
                color=INK, fontweight="bold" if k in ("actual", "us_news") else "normal")
    ax.text(x_lab + pd.Timedelta(days=1.5), pos[1] - 6.2,
            f"5\u201395% of models: {end['us_news_p05']:.0f} to {end['us_news_p95']:.0f}", va="center",
            fontsize=8.2, color=INK2)
    ax.set_xlim(pd.Timestamp("2025-12-27"), pd.Timestamp("2026-10-08"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_ylabel("Change since the close of 30 Dec 2025, bp")
    ax.grid(axis="x", visible=False)
    handles = [plt.Line2D([], [], color=INK, lw=2.6),
               (plt.Rectangle((0, 0), 1, 1, fc=COLOR["us_news"], alpha=0.13, lw=0),
                plt.Line2D([], [], color=COLOR["us_news"], lw=2.2)),
               plt.Line2D([], [], color=COLOR["global_risk"], lw=2),
               plt.Line2D([], [], color=COLOR["euro_area"], lw=2),
               plt.Line2D([], [], color=COLOR["unspanned"], lw=1.8)]
    labels = ["Actual 10-year yield", "US news (band: 5\u201395% of admissible models)", LABEL["global_risk"],
              LABEL["euro_area"], LABEL["unspanned"]]
    ax.legend(handles, labels, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=9,
              handlelength=2.2, columnspacing=1.6)
    fig.subplots_adjust(left=0.07, right=0.76, top=0.86 if standalone else 0.9, bottom=0.08)
    return _finish(fig, "fig1_10y_decomposition", standalone,
                   {"us05": end["us_news_p05"], "us95": end["us_news_p95"], "actual": end["actual"]})


# ---------------------------------------------------------------- figure 2
def _stacked_row(ax, y, parts: dict, actual: float, height=0.5, label_min=11.0):
    pos = neg = 0.0
    for key, v in parts.items():
        left = pos if v >= 0 else neg
        ax.barh(y, v, left=left, color=COLOR[key], height=height, lw=1.6, edgecolor=SURFACE, zorder=2)
        if abs(v) >= label_min:
            ax.text(left + v / 2, y, f"{abs(v):.0f}", ha="center", va="center", fontsize=8.6, zorder=4,
                    color="white" if key in ("us_news", "all_shocks") else INK)
        if v >= 0:
            pos += v
        else:
            neg += v
    ax.plot([actual], [y], marker="D", ms=7.5, color=INK, mec=SURFACE, mew=1.6, zorder=5)
    ax.text(max(pos, actual) + 4, y, _bp(actual), va="center", ha="left", fontsize=9.5, fontweight="bold")


def fig2(dec: pd.DataFrame, standalone: bool = True):
    w = dec[dec["window"] == FULL].set_index("maturity")
    rows = ["2y", "5y", "10y", "30y", "2s10s", "10s30s"]
    ys = [0, -1, -2, -3, -4.5, -5.5]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for m, y in zip(rows, ys):
        r = w.loc[m]
        parts = {k: r[f"{k}_mt"] for k in (*ORIGINS, "unspanned")}
        _stacked_row(ax, y, parts, r["actual_bp"])
    ax.axvline(0, color=INK2, lw=1, zorder=3)
    ax.set_yticks(ys, [MATURITY_NAME[m] for m in rows])
    ax.tick_params(axis="y", labelsize=9.8, labelcolor=INK)
    ax.set_ylim(-6.1, 0.55)
    ax.set_xlim(-80, 175)
    ax.set_xlabel("Change from 30 Dec 2025 to 5 Oct 2026, bp")
    ax.grid(axis="y", visible=False)
    ax.axhline(-3.75, color=GRID, lw=1)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLOR[k]) for k in (*ORIGINS, "unspanned")]
    handles.append(plt.Line2D([], [], marker="D", ms=7, color=INK, ls=""))
    labels = [LABEL[k] for k in (*ORIGINS, "unspanned")] + ["Actual change"]
    ax.legend(handles, labels, ncol=5, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=8.8,
              handlelength=1.3, columnspacing=1.3)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.86 if standalone else 0.9, bottom=0.11)
    u2, s2 = w.loc["2y"], w.loc["2s10s"]
    return _finish(fig, "fig2_curve", standalone,
                   {"u2": u2["unspanned_p50"], "u2lo": u2["unspanned_p05"], "u2hi": u2["unspanned_p95"],
                    "s2": s2["all_shocks_p50"], "s2lo": s2["all_shocks_p05"], "s2hi": s2["all_shocks_p95"]})


# ---------------------------------------------------------------- figure 3
def fig3(mon: pd.DataFrame, standalone: bool = True):
    fig, axes = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True)
    months = list(mon["month"].unique())
    xs = np.arange(len(months))
    for ax, mat in zip(axes, ("10y", "2y")):
        g = mon[mon["maturity"] == mat].set_index("month").loc[months]
        pos = np.zeros(len(xs))
        neg = np.zeros(len(xs))
        for key in (*ORIGINS, "unspanned"):
            v = g[f"{key}_mt"].to_numpy()
            base = np.where(v >= 0, pos, neg)
            ax.bar(xs, v, bottom=base, width=0.56, color=COLOR[key], lw=1.4, edgecolor=SURFACE, zorder=2)
            pos += np.where(v >= 0, v, 0)
            neg += np.where(v < 0, v, 0)
        ax.plot(xs, g["actual_bp"], ls="", marker="o", ms=7, color=INK, mec=SURFACE, mew=1.6, zorder=5)
        for i, (a, p) in enumerate(zip(g["actual_bp"], g["p_us_largest"])):
            if abs(a) >= 25:
                top = max(pos[i], a) if a > 0 else min(neg[i], a)
                ax.text(i, top + (4 if a > 0 else -4), f"US news largest\nin {p:.0%} of models",
                        ha="center", va="bottom" if a > 0 else "top", fontsize=8, color=INK2, linespacing=1.15)
        ax.axhline(0, color=INK2, lw=1, zorder=3)
        ax.set_ylim(-56, 84)
        ax.set_ylabel("bp")
        ax.grid(axis="x", visible=False)
        ax.set_title(f"{MATURITY_NAME[mat]} yield, change in month", loc="left", fontsize=10.5,
                     fontweight="bold", color=INK, pad=6)
    labels = [pd.Period(m).strftime("%b") for m in months]
    labels[0] += "\n(from 30 Dec)"
    labels[-1] += "\n(to 5th)"
    axes[1].set_xticks(xs, labels)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLOR[k]) for k in (*ORIGINS, "unspanned")]
    handles.append(plt.Line2D([], [], marker="o", ms=7, color=INK, ls=""))
    names = [LABEL[k] for k in (*ORIGINS, "unspanned")] + ["Actual change"]
    fig.legend(handles, names, ncol=5, loc="upper left", bbox_to_anchor=(0.06, 0.935 if standalone else 0.985),
               fontsize=8.8, handlelength=1.3, columnspacing=1.3)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86 if standalone else 0.91, bottom=0.08, hspace=0.28)
    return _finish(fig, "fig3_monthly", standalone)


# ---------------------------------------------------------------- figure 4
TIERS = [("Identification-free", ["all_shocks", "unspanned"]),
         ("Robust in sign", ["us_news"]),
         ("Weakly identified", ["global_risk", "euro_area"]),
         ("Not pinned down", ["us_macro", "us_monetary"])]


def fig4(dec: pd.DataFrame, standalone: bool = True):
    w = dec[dec["window"] == FULL].set_index("maturity")
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.6), sharey=True)
    ys, labels, y = [], [], 0.0
    layout = []
    for tier, keys in TIERS:
        layout.append(("tier", tier, y))
        y -= 0.75
        for k in keys:
            layout.append(("row", k, y))
            ys.append(y)
            labels.append(LABEL[k])
            y -= 1.0
        y -= 0.35
    for ax, mat in zip(axes, ("10y", "2y")):
        r = w.loc[mat]
        for kind, key, yy in layout:
            if kind == "tier":
                if ax is axes[0]:
                    ax.text(-0.02, yy, key.upper(), transform=ax.get_yaxis_transform(), ha="right", va="center",
                            fontsize=8, color=MUTED, fontweight="bold")
                continue
            c = COLOR[key]
            ax.plot([r[f"{key}_p05"], r[f"{key}_p95"]], [yy, yy], color=c, lw=2.4, alpha=0.85, zorder=2,
                    solid_capstyle="round")
            ax.plot([r[f"{key}_p50"]], [yy], marker="o", ms=8, color=c, mec=SURFACE, mew=1.8, zorder=4)
            ax.plot([r[f"{key}_mt"]], [yy], marker="D", ms=6.5, mfc=SURFACE, mec=INK, mew=1.3, zorder=5)
        ax.axvline(0, color=INK2, lw=1, zorder=1)
        ax.axvline(r["actual_bp"], color=INK, lw=1.1, zorder=1)
        ax.text(r["actual_bp"] - 2.5, 0.75, f"actual {_bp(r['actual_bp'])}", ha="right", va="center", fontsize=8.6,
                color=INK, fontweight="bold")
        ax.set_xlim(-35, 165)
        ax.set_ylim(y + 0.6, 1.1)
        ax.grid(axis="y", visible=False)
        ax.set_title(f"{MATURITY_NAME[mat]} yield", loc="left", fontsize=10.5, fontweight="bold", color=INK, pad=18)
        ax.set_xlabel("bp")
        p = r["p_us_largest"]
        ax.text(max(r["us_news_p95"], r["actual_bp"]) + 4, ys[2], f"largest origin in\n{p:.0%} of models", va="center", fontsize=8,
                color=INK2, linespacing=1.1)
        ax.text(max(r["us_macro_p95"], r["us_monetary_p95"], r["actual_bp"]) + 4, (ys[5] + ys[6]) / 2,
                f"macro > monetary\nin {r['p_macro_gt_monetary']:.0%} of models", va="center", fontsize=8,
                color=INK2, linespacing=1.1)
    axes[0].set_yticks(ys, labels)
    axes[0].tick_params(axis="y", labelsize=9.4, labelcolor=INK)
    handles = [plt.Line2D([], [], marker="o", ms=8, color=INK2, lw=2.4),
               plt.Line2D([], [], marker="D", ms=6.5, mfc=SURFACE, mec=INK, mew=1.3, ls="")]
    fig.legend(handles, ["Median and 5\u201395% across the 1,000 admissible models", "Median-target model"],
               ncol=2, loc="upper left", bbox_to_anchor=(0.25, 0.925 if standalone else 0.99), fontsize=8.8)
    fig.subplots_adjust(left=0.25, right=0.97, top=0.8 if standalone else 0.86, bottom=0.1, wspace=0.08)
    return _finish(fig, "fig4_identification", standalone, {"pm": 100 * w.loc["10y", "p_macro_gt_monetary"]})


# ---------------------------------------------------------------- figure 5
def fig5(fit: pd.DataFrame, fc: pd.DataFrame, standalone: bool = True):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 5.6), gridspec_kw={"width_ratios": [1, 1.45]})
    mats = ["2y", "5y", "10y", "30y"]
    f = fit.set_index("maturity").loc[mats]
    yy = -np.arange(len(mats), dtype=float) * 1.2
    h = 0.34
    a1.barh(yy + h / 2, 100 * f["r2_daily_2007_2025"], height=h, color="#86b6ef", lw=1.2, edgecolor=SURFACE, zorder=2)
    a1.barh(yy - h / 2, 100 * f["r2_daily_2026"], height=h, color=COLOR["us_news"], lw=1.2, edgecolor=SURFACE,
            zorder=2)
    for y, v0, v1 in zip(yy, f["r2_daily_2007_2025"], f["r2_daily_2026"]):
        a1.text(100 * v0 + 1.5, y + h / 2, f"{100 * v0:.0f}%", va="center", fontsize=8.4, color=INK2)
        a1.text(100 * v1 + 1.5, y - h / 2, f"{100 * v1:.0f}%", va="center", fontsize=8.4, color=INK,
                fontweight="bold")
    a1.set_yticks(yy, [MATURITY_NAME[m] for m in mats])
    a1.tick_params(axis="y", labelsize=9.6, labelcolor=INK)
    a1.set_xlim(0, 108)
    a1.set_ylim(yy[-1] - 0.65, 0.65)
    a1.set_xlabel("Daily R\u00b2, %")
    a1.grid(axis="y", visible=False)
    a1.set_title("Explains the day", loc="left", fontsize=10.5, fontweight="bold", color=INK, pad=22)
    a1.legend([plt.Rectangle((0, 0), 1, 1, color="#86b6ef"), plt.Rectangle((0, 0), 1, 1, color=COLOR["us_news"])],
              ["2007\u20132025, in sample", "2026, frozen loadings"], loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=2, fontsize=8.4, handlelength=1.2, handletextpad=0.4, columnspacing=1.0)

    g = fc[(fc["period"] == "2012-2025 real time")]
    rows = []
    for m in mats:
        for h in (1, 5, 20):
            rows.append((f"{MATURITY_NAME[m]}, {h} day{'s' if h > 1 else ''}",
                         g[(g.maturity == m) & (g.horizon_days == h) & (g.measured_from == "next close")].iloc[0]))
    art = g[(g.maturity == "10y") & (g.horizon_days == 1) & (g.measured_from == "same close")].iloc[0]
    ys, y = [], 0.0
    for i in range(len(rows)):
        ys.append(y)
        y -= 1.0 if (i + 1) % 3 else 1.5
    y_art = y - 0.3
    off = 0.17                                   # the two models sit almost on top of each other
    for (lab, r), y in zip(rows, ys):
        a2.plot([100 * r["r2_curve_state"]], [y + off], "o", ms=7, color=MUTED, mec=SURFACE, mew=1.4, zorder=3)
        a2.plot([100 * r["r2_origin"]], [y - off], "o", ms=7, color=COLOR["us_news"], mec=SURFACE, mew=1.4, zorder=4)
    a2.plot([100 * art["r2_curve_state"]], [y_art + off], "o", ms=7, color=MUTED, mec=SURFACE, mew=1.4, zorder=3)
    a2.plot([100 * art["r2_origin"]], [y_art - off], "o", ms=7, mfc=SURFACE, mec=COLOR["us_news"], mew=1.6, zorder=4)
    a2.text(100 * art["r2_origin"] + 1.2, y_art - off, f"+{100 * art['r2_origin']:.1f}% (timing artefact)",
            va="center", fontsize=8.4, color=INK2)
    a2.axvline(0, color=INK, lw=1.1, zorder=1)
    a2.text(0.6, ys[0] + 0.85, "no-change forecast", fontsize=8.4, color=INK, va="bottom")
    a2.set_yticks(ys + [y_art], [lab for lab, _ in rows] + ["10-year, 1 day, same close"])
    a2.tick_params(axis="y", labelsize=8.8, labelcolor=INK)
    a2.set_xlim(-34, 12)
    a2.set_ylim(y_art - 0.8, ys[0] + 1.4)
    a2.set_xlabel("Out-of-sample R² against no change, %")
    a2.grid(axis="y", visible=False)
    a2.set_title("Predicts nothing (real time, 2012\u20132025)", loc="left", fontsize=10.5, fontweight="bold",
                 color=INK, pad=22)
    a2.legend([plt.Line2D([], [], marker="o", ms=7.5, color=MUTED, ls=""),
               plt.Line2D([], [], marker="o", ms=7.5, color=COLOR["us_news"], ls="")],
              ["Own move and curve state", "Plus origin of today's news"], loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8.4, handletextpad=0.3, columnspacing=1.0)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82 if standalone else 0.88, bottom=0.1, wspace=0.42)
    return _finish(fig, "fig5_forecasting", standalone)


# ---------------------------------------------------------------- build
def load(data: Path) -> dict:
    return {"daily": pd.read_csv(data / "us10y_daily_cumulative_2026.csv"),
            "dec": pd.read_csv(data / "decomposition_2026.csv"),
            "mon": pd.read_csv(data / "monthly_2026.csv"),
            "fit": pd.read_csv(data / "explanatory_fit.csv"),
            "fc": pd.read_csv(data / "forecast_oos.csv")}


def figures(d: dict, standalone: bool = True) -> dict:
    return {"fig1_10y_decomposition": fig1(d["daily"], standalone),
            "fig2_curve": fig2(d["dec"], standalone),
            "fig3_monthly": fig3(d["mon"], standalone),
            "fig4_identification": fig4(d["dec"], standalone),
            "fig5_forecasting": fig5(d["fit"], d["fc"], standalone)}


def build(data: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, fig in figures(load(data)).items():
        _save(fig, out, name)
    emitted = {p.stem for p in out.glob("*.png")}
    assert emitted == set(CAPTIONS) == set(TITLES), (emitted ^ set(CAPTIONS))
    print(f"figures: wrote {len(emitted)} figures (PNG and SVG) to {out.relative_to(out.parents[1])}")
