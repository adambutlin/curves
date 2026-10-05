"""Figures for the cross-Atlantic replication and the 2026 application.

Reads ``reports/structural_propagation/{brandt,application_2026}`` and writes
``fig7``-``fig11`` beside the earlier figures, each with its conclusion baked in.
Colours: the US model's four shocks keep their hues from figures 1-5; the five
cross-Atlantic shocks use a separately validated set, with solid lines for euro-area
shocks and dashed lines for US shocks as a second cue.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GREY, INK, INK2, GRID, AXIS, SURFACE = "#898781", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
US_SHOCKS = {"growth": ("Growth news", "#2a78d6"), "monetary": ("Monetary news", "#eb6834"),
             "common_premium": ("Common premium", "#1baf7a"),
             "hedging_premium": ("Hedging premium", "#eda100")}
BR_SHOCKS = {"ea_monetary": ("Euro-area monetary", "#2a78d6", "-"),
             "ea_macro": ("Euro-area macro", "#1baf7a", "-"),
             "us_monetary": ("US monetary", "#4a3aa7", "--"),
             "us_macro": ("US macro", "#eda100", "--"),
             "global_risk": ("Global risk", "#e34948", "-")}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
})


def _finish(fig, out, name, title, caption):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.01, 0.01, caption, ha="left", va="bottom", fontsize=9, color=INK2, wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    fig.savefig(out / name, dpi=200)
    plt.close(fig)


def fig_replication(rep: Path, out: Path):
    s = json.loads((rep / "summary.json").read_text())
    low = json.loads((rep / "exploratory_lower_frequency_shares.json").read_text())
    windows = [("Daily", s["origin_shares_1999_2025"]), ("2-day", low["2-day changes"]),
               ("Weekly", low["5-day changes"])]
    items = [("US shocks in\nBund 10y variance", "d_ea10", "us", 0.40),
             ("US shocks in\neuro-equity variance", "r_eq_ea", "us", 0.40),
             ("Euro-area shocks in\nUS-equity variance", "r_eq_us", "ea", 0.30)]
    ev = pd.read_csv(rep / "event_study.csv")
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})
    x = np.arange(len(items))
    shades = ["#9ec5f4", "#5598e7", "#1c5cab"]                    # one hue, light to dark
    for i, (lab, d) in enumerate(windows):
        vals = [d[v][o] * 100 for _, v, o, _ in items]
        ax.bar(x + (i - 1) * 0.26, vals, width=0.24, color=shades[i], label=f"{lab} changes", zorder=2)
    for k, (_, _, _, target) in enumerate(items):
        ax.plot([k - 0.42, k + 0.42], [target * 100] * 2, color=INK, lw=1.4, ls="--", zorder=3)
    ax.plot([], [], color=INK, lw=1.4, ls="--", label="Brandt et al. (2021)")
    ax.set_xticks(x)
    ax.set_xticklabels([i[0] for i in items])
    ax.set_ylabel("Share of variance, %")
    ax.set_ylim(0, 48)
    ax.set_title("Spillover shares", loc="left")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", ncol=4, fontsize=8.5, bbox_to_anchor=(0.01, 0.93))
    ax.grid(axis="x", visible=False)
    ev = ev.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(ev))
    bx.barh(y, ev["share_draws_hit"] * 100, color="#5598e7", height=0.6, zorder=2)
    for i, row in ev.iterrows():
        bx.text(101, i, "hit" if row["hit_mt"] else "miss", va="center", fontsize=7.5,
                color=INK if row["hit_mt"] else "#d03b3b")
    bx.set_yticks(y)
    bx.set_yticklabels([f"{r.date}  {r.event}" for r in ev.itertuples()], fontsize=7.5)
    bx.set_xlim(0, 112)
    bx.set_xlabel("Admissible models attributing the event to the expected shock, %")
    bx.set_title("Brandt et al.'s 18 events (label: median-target model)", loc="left")
    bx.grid(axis="y", visible=False)
    _finish(fig, out, "fig7_brandt_replication.png",
            "Replicating Brandt et al. on free data",
            "US-to-euro-area spillovers come close to the published 40% once changes are measured over "
            "two days or a week, because European prices close before US prices; the median-target "
            "model attributes 13 of the 18 events as the authors expected.")


def fig_closing_time(rep: Path, out: Path):
    ll = pd.read_csv(rep / "exploratory_lead_lag.csv")
    low = json.loads((rep / "exploratory_lower_frequency_shares.json").read_text())
    oos = pd.read_csv(rep / "oos_summary.csv")
    sk = pd.read_csv(rep / "exploratory_skipday_oos.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9))
    ax = axes[0]
    pairs = [("Bund 10y, next day", "Treasury 10y today", "Treasury today\n→ Bund tomorrow"),
             ("Treasury 10y, next day", "Bund 10y today", "Bund today\n→ Treasury tomorrow")]
    vals = [float(ll[(ll.outcome == a) & (ll.regressor == b)]["coef"].iloc[0]) for a, b, _ in pairs]
    ax.bar([0, 1], vals, color=["#1c5cab", "#9ec5f4"], width=0.55, zorder=2)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.012, f"{v:+.2f}", ha="center", fontsize=9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([p[2] for p in pairs])
    ax.set_ylim(min(vals) - 0.05, max(vals) * 1.18)
    ax.set_ylabel("bp of next-day move per bp today")
    ax.set_title("Who catches up with whom", loc="left")
    ax.grid(axis="x", visible=False)
    ax = axes[1]
    daily_corr = 0.247
    corrs = [daily_corr, low["2-day changes"]["corr_bund_ust"], low["5-day changes"]["corr_bund_ust"]]
    ax.bar([0, 1, 2], corrs, color=["#9ec5f4", "#5598e7", "#1c5cab"], width=0.55, zorder=2)
    for i, v in enumerate(corrs):
        ax.text(i, v + 0.015, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["Daily", "2-day", "Weekly"])
    ax.set_ylim(0, max(corrs) * 1.15)
    ax.set_ylabel("Correlation of Bund and Treasury changes")
    ax.set_title("Co-movement by measurement window", loc="left")
    ax.grid(axis="x", visible=False)
    ax = axes[2]
    cc = oos[(oos.outcome == "ea10") & (oos.period == "2004-2025")].set_index("h")
    nk = sk[(sk.outcome == "ea10") & (sk.period == "2004-2025")].set_index("h")
    labels = ["Close-to-close,\n1 day", "From next close,\nto day 2", "From next close,\nto day 5"]
    m3 = [cc.loc[1, "r2_m3_vs_m0"], nk.loc[2, "r2_m3_vs_m0"], nk.loc[5, "r2_m3_vs_m0"]]
    m4 = [cc.loc[1, "r2_m4_vs_m0"], nk.loc[2, "r2_m4_vs_m0"], nk.loc[5, "r2_m4_vs_m0"]]
    xx = np.arange(3)
    ax.bar(xx - 0.15, np.array(m3) * 100, width=0.3, color="#1baf7a", label="+ origin split", zorder=2)
    ax.bar(xx + 0.15, np.array(m4) * 100, width=0.3, color="#4a3aa7", label="+ all cross-asset news", zorder=2)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(xx)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Real-time R² vs no change, %")
    ax.set_title("Bund 10y forecasts, 2004-2025", loc="left")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", visible=False)
    _finish(fig, out, "fig8_closing_time.png",
            "The closing-time artefact in the daily cross-Atlantic data",
            "Forty per cent of a day's Treasury move reaches the Bund the next day and nothing flows back; "
            "that catch-up alone produces the apparent 22-27% real-time R² at one day, which vanishes "
            "once the forecast starts at the next close.")


def _spread_labels(values, min_gap):
    """Nudge label heights apart so end-of-line labels never overlap."""
    order = np.argsort(values)
    pos = np.array(values, dtype=float)
    for a, b in zip(order[:-1], order[1:]):
        if pos[b] - pos[a] < min_gap:
            pos[b] = pos[a] + min_gap
    return pos


def _cum_panel(ax, df, shocks, title, styles=None):
    days = df.index
    ends = []
    for s, spec in shocks.items():
        label, colour = spec[0], spec[1]
        ls = spec[2] if len(spec) > 2 else "-"
        series = df[s].cumsum()
        ax.plot(days, series, color=colour, lw=2, ls=ls, label=label)
        ends.append((series.iloc[-1], colour))
    span = max(df["actual"].cumsum().max(), max(e[0] for e in ends)) - min(
        df["actual"].cumsum().min(), min(e[0] for e in ends))
    ys = _spread_labels([e[0] for e in ends], span * 0.045)
    for (v, colour), yv in zip(ends, ys):
        ax.text(days[-1] + pd.Timedelta(days=4), float(yv), f"{v:+.0f}", va="center", fontsize=8,
                color=INK2)
    ax.plot(days, df["actual"].cumsum(), color=INK, lw=2.6, label="Actual change")
    ax.plot(days, df["other"].cumsum(), color=GREY, lw=1.4, ls=":", label="Other (intercepts, older shocks)")
    ax.axhline(0, color=AXIS, lw=1)
    for d in ("2026-02-27", "2026-08-19"):
        ax.axvline(pd.Timestamp(d), color=AXIS, lw=1, ls="--")
    ax.set_title(title, loc="left")
    ax.set_ylabel("Cumulative change since 31 Dec 2025, bp")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))


def fig_2026_us(app: Path, out: Path):
    y10 = pd.read_csv(app / "daily_us_y10.csv", index_col=0, parse_dates=True)
    y2 = pd.read_csv(app / "daily_us_y2.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    _cum_panel(axes[0], y10, US_SHOCKS, "10-year Treasury")
    _cum_panel(axes[1], y2, US_SHOCKS, "2-year Treasury")
    axes[1].set_ylabel("")
    axes[0].legend(loc="upper left", fontsize=7.5)
    _finish(fig, out, "fig9_2026_us_model.png",
            "The 2026 Treasury selloff through the frozen US model (Cieslak-Pang shocks)",
            "Growth and monetary news drove the 2-year up 79bp; the 10-year rose less, and over the selloff "
            "window (dashed lines) most of its rise came with the long-end-heavy pattern the model reads as "
            "risk-premium shocks, especially a fall in Treasuries' value as a hedge.")


def fig_2026_crossatlantic(app: Path, out: Path):
    ea = pd.read_csv(app / "daily_brandt_ea10.csv", index_col=0, parse_dates=True)
    us = pd.read_csv(app / "daily_brandt_us10.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    _cum_panel(axes[0], ea, BR_SHOCKS, "10-year Bund")
    _cum_panel(axes[1], us, BR_SHOCKS, "10-year Treasury")
    axes[1].set_ylabel("")
    axes[0].legend(loc="upper left", fontsize=7.5)
    _finish(fig, out, "fig10_2026_crossatlantic.png",
            "The 2026 selloff through the frozen cross-Atlantic model (Brandt et al. shocks)",
            "The Bund selloff was largely imported: US monetary and macro news account for 59bp of its "
            "69bp rise in 2026 to date; euro-area monetary news pulled Bund yields down early in the year "
            "and pushed them up from March. The Treasury rise is overwhelmingly US news.")


def fig_2026_window(app: Path, out: Path):
    w = pd.read_csv(app / "decomposition_windows.csv")
    w = w[w["window"] == "27 Feb-19 Aug 2026"]
    panels = [("US (Cieslak-Pang)", "y10", "Treasury 10y, US model", US_SHOCKS),
              ("Cross-Atlantic (Brandt et al.)", "us10", "Treasury 10y, cross-Atlantic", BR_SHOCKS),
              ("Cross-Atlantic (Brandt et al.)", "ea10", "Bund 10y, cross-Atlantic", BR_SHOCKS)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharex=True)
    for ax, (model, o, title, shocks) in zip(axes, panels):
        r = w[(w["model"] == model) & (w["outcome"] == o)].iloc[0]
        names = list(shocks)
        y = np.arange(len(names))[::-1]
        for yi, s in zip(y, names):
            v, lo, hi = r[f"{s}_bp"], r[f"{s}_p05"], r[f"{s}_p95"]
            ax.barh(yi, v, color=shocks[s][1], height=0.6, zorder=2)
            ax.plot([lo, hi], [yi, yi], color=INK, lw=1.2, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([shocks[s][0] for s in names])
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(f"{title}\nactual {r['actual_bp']:+.0f}bp, other {r['other_bp']:+.0f}bp", loc="left")
        ax.set_xlabel("Contribution, bp")
        ax.grid(axis="y", visible=False)
    _finish(fig, out, "fig11_2026_window.png",
            "27 February to 19 August 2026: who moved yields (bars: median-target model; lines: 90% of identified set)",
            "The cross-Atlantic model puts US news at the centre (about 60% of both the Treasury and the "
            "Bund rise) with euro-area monetary news adding over a third of the Bund's; the US model reads "
            "much of the Treasury rise as premium shocks, a different slicing of the same moves. Bands are wide.")


def fig_synchronisation(rep: Path, out: Path):
    """What recording prices at the New York close changes."""
    chk = json.loads((rep / "brandt_sync" / "synchronisation_check.json").read_text())
    free = json.loads((rep / "brandt" / "summary.json").read_text())["origin_shares_2007_2025"]
    sync = json.loads((rep / "brandt_sync" / "summary.json").read_text())["origin_shares_full_sample"]
    bfut = json.loads((rep / "brandt_sync_bf" / "summary.json").read_text())["origin_shares_full_sample"]
    r2 = [float(pd.read_csv(rep / d / "test_a.csv").query("outcome == 'ea10' and h == 1")["incr_r2"].iloc[0])
          for d in ("brandt", "brandt_sync", "brandt_sync_bf")]
    labels = ["Free data\n(European closes)", "LSEG OIS\n(near NY close)", "LSEG Bund future\n(NY close)"]
    shades = ["#9ec5f4", "#5598e7", "#1c5cab"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    ax = axes[0]
    keys = list(chk)
    vals = [chk[k]["next_day_ea10_on_us10"]["coef"] for k in keys]
    ax.bar(range(3), vals, color=shades, width=0.6, zorder=2)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.012, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_ylabel("bp of next-day euro-area rate move\nper bp of today's Treasury move")
    ax.set_title("Overnight catch-up", loc="left")
    ax.grid(axis="x", visible=False)
    ax = axes[1]
    items = [("US shocks in\neuro-area rate", "d_ea10", "us", 0.40), ("US shocks in\neuro equity", "r_eq_ea", "us", 0.40),
             ("Euro-area shocks\nin US equity", "r_eq_us", "ea", 0.30)]
    x = np.arange(3)
    for i, d in enumerate((free, sync, bfut)):
        ax.bar(x + (i - 1) * 0.26, [d[v][o] * 100 for _, v, o, _ in items], width=0.24, color=shades[i], zorder=2)
    for k, (_, _, _, tgt) in enumerate(items):
        ax.plot([k - 0.42, k + 0.42], [tgt * 100] * 2, color=INK, lw=1.4, ls="--", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([i[0] for i in items], fontsize=8)
    ax.set_ylim(0, 50)
    ax.set_ylabel("Share of daily variance, %")
    ax.set_title("Spillovers", loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in shades]
    handles.append(plt.Line2D([], [], color=INK, lw=1.4, ls="--"))
    fig.legend(handles, ["Free data (European closes)", "LSEG OIS (near NY close)",
                         "LSEG Bund future (NY close)", "Brandt et al. (2021)"],
               loc="upper left", ncol=4, fontsize=8.5, bbox_to_anchor=(0.01, 0.93))
    ax.grid(axis="x", visible=False)
    ax = axes[2]
    ax.bar(range(3), np.array(r2) * 100, color=shades, width=0.6, zorder=2)
    for i, v in enumerate(r2):
        ax.text(i, v * 100 + 0.5, f"{v * 100:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, max(r2) * 100 * 1.2)
    ax.set_ylabel("Extra R² for next-day euro-area rate, %")
    ax.set_title("Apparent next-day predictability", loc="left")
    ax.grid(axis="x", visible=False)
    _finish(fig, out, "fig12_synchronisation.png",
            "Recording euro-area prices at the New York close (2007-2025)",
            "With prices synchronised the overnight catch-up disappears, the US share of euro-area rate "
            "variance rises to 35% (OIS) and 40% (Bund future) against the published 40%, and the "
            "'predictability' of next-day euro-area moves shrinks from 28% of R-squared to 0.5%.")


def fig_2026_synchronised(app: Path, out: Path):
    priv = app / "lseg_private"
    if not (priv / "daily_brandt_sync_ea10.csv").exists():
        return
    ea = pd.read_csv(priv / "daily_brandt_sync_ea10.csv", index_col=0, parse_dates=True)
    us = pd.read_csv(priv / "daily_brandt_sync_us10.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
    _cum_panel(axes[0], ea, BR_SHOCKS, "Euro-area 10-year OIS")
    _cum_panel(axes[1], us, BR_SHOCKS, "10-year Treasury")
    axes[1].set_ylabel("")
    axes[0].legend(loc="upper left", fontsize=7.5)
    _finish(fig, out, "fig13_2026_synchronised.png",
            "The 2026 selloff through the frozen synchronised cross-Atlantic model (LSEG prices at the NY close)",
            "With synchronised prices the euro-area rise is imported: US macro and monetary news add 67bp to "
            "the euro-area 10-year rate in 2026 while euro-area news subtracts 7bp; the Treasury's 118bp rise "
            "is mostly US macro news.")


def fig_2026_models(app: Path, out: Path):
    w = pd.read_csv(app / "decomposition_windows.csv")
    w = w[w["window"] == "27 Feb-19 Aug 2026"]
    panels = [("US (Cieslak-Pang)", "y10", "Treasury 10y: US model", US_SHOCKS),
              ("Cross-Atlantic, synchronised (LSEG)", "us10", "Treasury 10y: synchronised", BR_SHOCKS),
              ("Cross-Atlantic (Brandt et al.)", "ea10", "Bund 10y: free data", BR_SHOCKS),
              ("Cross-Atlantic, synchronised (LSEG)", "ea10", "Euro OIS 10y: synchronised", BR_SHOCKS)]
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.3), sharex=True)
    for ax, (model, o, title, shocks) in zip(axes, panels):
        r = w[(w["model"] == model) & (w["outcome"] == o)].iloc[0]
        names = list(shocks)
        y = np.arange(len(names))[::-1]
        for yi, s in zip(y, names):
            ax.barh(yi, r[f"{s}_bp"], color=shocks[s][1], height=0.6, zorder=2)
            ax.plot([r[f"{s}_p05"], r[f"{s}_p95"]], [yi, yi], color=INK, lw=1.2, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([shocks[s][0] for s in names], fontsize=8)
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(f"{title}\nactual {r['actual_bp']:+.0f}bp", loc="left", fontsize=9)
        ax.set_xlabel("Contribution, bp")
        ax.grid(axis="y", visible=False)
    _finish(fig, out, "fig14_2026_models.png",
            "27 February to 19 August 2026 across the frozen models (bars: median-target model; lines: 90% of identified set)",
            "Synchronising the data moves the euro-area story from domestic monetary news to imported US news; "
            "on the Treasury side the models agree on US origin but split it differently between macro, monetary "
            "and premium news, and the bands are wide.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=str(ROOT / "reports" / "structural_propagation"))
    args = ap.parse_args(argv)
    rep = Path(args.reports)
    fig_replication(rep / "brandt", rep)
    fig_closing_time(rep / "brandt", rep)
    fig_2026_us(rep / "application_2026", rep)
    fig_2026_crossatlantic(rep / "application_2026", rep)
    fig_2026_window(rep / "application_2026", rep)
    if (rep / "brandt_sync" / "synchronisation_check.json").exists():
        fig_synchronisation(rep, rep)
        fig_2026_synchronised(rep / "application_2026", rep)
        fig_2026_models(rep / "application_2026", rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
