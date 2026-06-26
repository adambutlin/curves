#!/usr/bin/env python3
"""Generate the publication-quality figure set for the ACM term-premium model.

Matplotlib only (no seaborn). Reads the decomposed panel
(``data/processed/term_premium_panel.csv``) and the NY Fed published ACM series,
re-fits PCA where diagnostics need it, and writes PNG + SVG (300 dpi) to figures/.

Run:  python3 figures/generate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))

from style import (  # noqa: E402
    set_style, save, OKABE_ITO,
    US_C, UK_C, EXP_C, TP_C, OBS_C, OFFICIAL_C, RESID_C,
)

PANEL_CSV = ROOT / "data" / "processed" / "term_premium_panel.csv"

# ---- recession / QE spans (month resolution) -------------------------------
US_RECESSIONS = [("1969-12", "1970-11"), ("1973-11", "1975-03"), ("1980-01", "1980-07"),
                 ("1981-07", "1982-11"), ("1990-07", "1991-03"), ("2001-03", "2001-11"),
                 ("2007-12", "2009-06"), ("2020-02", "2020-04")]
UK_RECESSIONS = [("1973-09", "1974-03"), ("1980-01", "1981-03"), ("1990-07", "1991-09"),
                 ("2008-04", "2009-06"), ("2020-02", "2020-06"), ("2023-07", "2023-12")]
US_QE = [("2008-11", "2010-03"), ("2010-11", "2011-06"), ("2012-09", "2014-10"),
         ("2020-03", "2022-03")]
UK_QE = [("2009-03", "2010-02"), ("2011-10", "2012-11"), ("2016-08", "2017-02"),
         ("2020-03", "2021-12")]


# ---- helpers ---------------------------------------------------------------
def ser(df: pd.DataFrame, tenor: float, col: str) -> pd.Series:
    """Time series of ``col`` at one maturity, date-indexed and sorted."""
    return df[df["maturity"] == tenor].set_index("date")[col].sort_index()


def monthly(s: pd.Series) -> pd.Series:
    """Re-index a date series by calendar month (timestamp) for robust alignment."""
    s = s.dropna()
    idx = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    return pd.Series(s.to_numpy(float), index=idx).groupby(level=0).last().sort_index()


def shade(ax, spans, color, alpha, label=None):
    for i, (a, b) in enumerate(spans):
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=color, alpha=alpha,
                   lw=0, zorder=0, label=(label if i == 0 else None))


def corr_rmse(ours: pd.Series, official: pd.Series):
    j = ours.index.intersection(official.index)
    o, f = ours.loc[j], official.loc[j]
    c = float(np.corrcoef(o, f)[0, 1])
    rmse = float(np.sqrt(np.mean((o - f) ** 2)) * 1e4)
    return j, o, f, c, rmse


def pca_explained(panel_daily, k=6):
    from giltcurve.premium.acm import resample_to_monthly_grid
    from giltcurve.premium.pca import yield_pca
    eom = panel_daily.resample("ME").last().dropna(how="all")
    res = yield_pca(resample_to_monthly_grid(eom), k=k)
    ev = res.explained_var * 100.0
    return ev, np.cumsum(ev)


# ---- 1. US validation (headline) -------------------------------------------
def fig_us_validation(us, acm):
    ours = monthly(ser(us, 10.0, "term_premium"))
    off = monthly(acm["term_premium"][10.0])
    j, o, f, c, rmse = corr_rmse(ours, off)
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(10, 6.4), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.09})
    ax.plot(j, f * 100, color=OFFICIAL_C, lw=1.7, label="NY Fed ACM (official)")
    ax.plot(j, o * 100, color=US_C, lw=1.2, label="Replicated (this project)")
    ax.set_ylabel("10Y term premium (%)")
    ax.set_title("US 10Y Treasury Term Premium — Replication vs New York Fed (ACM)")
    ax.text(0.012, 0.96,
            f"correlation = {c:.3f}      RMSE = {rmse:.0f} bp      monthly, "
            f"{j.min():%Y}–{j.max():%Y}  (n={len(j)})",
            transform=ax.transAxes, va="top", fontsize=10, color="#333333")
    ax.legend(loc="lower right", ncol=2)
    axr.axhline(0, color="#666666", lw=0.8)
    axr.plot(j, (o - f) * 1e4, color=RESID_C, lw=0.9)
    axr.fill_between(j, (o - f) * 1e4, 0, color=RESID_C, alpha=0.22)
    axr.set_ylabel("Residual (bp)")
    axr.set_xlabel("Date")
    save(fig, "01_us_validation_10y")


# ---- 2. per-tenor validation ----------------------------------------------
def fig_per_tenor(us, acm):
    tenors = [1, 2, 3, 5, 7, 10]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True)
    for idx, (ax, t) in enumerate(zip(axes.ravel(), tenors)):
        ours = monthly(ser(us, float(t), "term_premium"))
        off = monthly(acm["term_premium"][float(t)])
        j, o, f, c, _ = corr_rmse(ours, off)
        ax.plot(j, f * 100, color=OFFICIAL_C, lw=1.3, label="NY Fed (official)")
        ax.plot(j, o * 100, color=US_C, lw=1.0, label="Replicated")
        ax.axhline(0, color="#999999", lw=0.5)
        ax.set_title(f"{t}Y", fontsize=11)
        ax.text(0.04, 0.94, f"r = {c:.2f}", transform=ax.transAxes, va="top",
                fontsize=10, bbox=dict(boxstyle="round,pad=0.25", fc="white",
                                       ec="#cccccc", alpha=0.9))
        if idx % 3 == 0:
            ax.set_ylabel("Term premium (%)")
        if idx >= 3:
            ax.set_xlabel("Date")
    axes.ravel()[0].legend(loc="lower right", fontsize=8.5)
    fig.suptitle("US Treasury Term Premium by Tenor — Replicated vs NY Fed (ACM)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "02_per_tenor_validation")


# ---- 3. decomposition, US & UK 10Y (separate charts) -----------------------
def fig_decomposition(df, label, long_label, name):
    obs = ser(df, 10.0, "observed")
    er = ser(df, 10.0, "expected_rate")
    tp = ser(df, 10.0, "term_premium")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(obs.index, obs * 100, color=OBS_C, lw=1.5, label="Observed 10Y yield")
    ax.plot(er.index, er * 100, color=EXP_C, lw=1.4, label="Expected avg short rate")
    ax.plot(tp.index, tp * 100, color=TP_C, lw=1.4, label="Term premium")
    ax.axhline(0, color="#888888", lw=0.6)
    ax.set_ylabel("Percent")
    ax.set_xlabel("Date")
    ax.set_title(f"{long_label} 10Y: ACM Term-Premium Decomposition")
    ax.legend(loc="upper right", ncol=3)
    ax.margins(x=0.01)
    save(fig, name)


# ---- 4. UK stacked composition --------------------------------------------
def fig_uk_stacked(uk):
    d = uk[uk["maturity"] == 10.0].set_index("date").sort_index()
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.stackplot(d.index, d["expected_rate"] * 100, d["term_premium"] * 100,
                 labels=["Expected avg short rate", "Term premium"],
                 colors=[EXP_C, TP_C], alpha=0.9)
    ax.plot(d.index, d["observed"] * 100, color=OBS_C, lw=1.1,
            label="Observed 10Y gilt yield")
    ax.set_ylabel("Percent")
    ax.set_xlabel("Date")
    ax.set_title("UK 10Y Gilt Yield — Composition: Expected Rate + Term Premium")
    ax.legend(loc="upper right")
    ax.margins(x=0)
    save(fig, "04_uk_yield_decomposition_stacked")


# ---- 5. term premium through time, recessions + QE -------------------------
def fig_tp_through_time(us, uk):
    ust = ser(us, 10.0, "term_premium") * 100
    ukt = ser(uk, 10.0, "term_premium") * 100
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    shade(ax, US_RECESSIONS, "#777777", 0.16, label="US recession (NBER)")
    shade(ax, UK_RECESSIONS, "#777777", 0.09, label="UK recession")
    shade(ax, US_QE + UK_QE, OKABE_ITO["skyblue"], 0.13, label="QE (US / UK)")
    ax.plot(ust.index, ust, color=US_C, lw=1.3, label="US 10Y term premium")
    ax.plot(ukt.index, ukt, color=UK_C, lw=1.3, label="UK 10Y term premium")
    ax.axhline(0, color="#888888", lw=0.6)
    ax.set_ylabel("10Y term premium (%)")
    ax.set_xlabel("Date")
    ax.set_title("10Y Term Premium Through Time — US vs UK")
    ax.legend(loc="upper right", ncol=2, fontsize=8.8)
    ax.margins(x=0)
    save(fig, "05_term_premium_through_time")


# ---- 6. heatmap of term premium across maturities --------------------------
def fig_heatmap(us, uk):
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8))
    for ax, df, lab in zip(axes, [us, uk], ["US Treasury", "UK gilt"]):
        piv = df.pivot_table(index="maturity", columns="date",
                             values="term_premium").sort_index() * 1e4
        xn = mdates.date2num(pd.to_datetime(piv.columns))
        vmax = float(np.nanpercentile(np.abs(piv.values), 99))
        mesh = ax.pcolormesh(xn, piv.index.values, piv.values, cmap="RdBu_r",
                             vmin=-vmax, vmax=vmax, shading="nearest")
        ax.xaxis_date()
        ax.grid(False)
        ax.set_ylabel("Maturity (years)")
        ax.set_title(f"{lab} term premium (bp) across maturities")
        cb = fig.colorbar(mesh, ax=ax, pad=0.01)
        cb.set_label("Term premium (bp)")
    axes[-1].set_xlabel("Date")
    fig.suptitle("Estimated Term Premia Across Maturities Through Time",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "06_term_premium_heatmap")


# ---- 7. cross-country comparison + differential ----------------------------
def fig_cross_country(us, uk):
    ust = ser(us, 10.0, "term_premium") * 100
    ukt = ser(uk, 10.0, "term_premium") * 100
    a, b = monthly(ust), monthly(ukt)
    j = a.index.intersection(b.index)
    diff = b.loc[j] - a.loc[j]
    fig, (ax, axd) = plt.subplots(
        2, 1, figsize=(10.5, 6.6), sharex=True,
        gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.09})
    ax.plot(ust.index, ust, color=US_C, lw=1.3, label="US 10Y")
    ax.plot(ukt.index, ukt, color=UK_C, lw=1.3, label="UK 10Y")
    ax.axhline(0, color="#888888", lw=0.6)
    ax.set_ylabel("Term premium (%)")
    ax.set_title("10Y Term Premium — US vs UK, and the UK–US Differential")
    ax.legend(loc="upper right", ncol=2)
    axd.axhline(0, color="#666666", lw=0.8)
    axd.plot(j, diff, color=RESID_C, lw=1.0)
    axd.fill_between(j, diff, 0, where=diff >= 0, color=UK_C, alpha=0.25, interpolate=True)
    axd.fill_between(j, diff, 0, where=diff < 0, color=US_C, alpha=0.25, interpolate=True)
    axd.set_ylabel("UK − US (%)")
    axd.set_xlabel("Date")
    save(fig, "07_cross_country_comparison")


# ---- 8. PCA diagnostics ----------------------------------------------------
def fig_pca(ev, cum):
    pcs = np.arange(1, len(ev) + 1)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    axes[0].bar(pcs, ev, color=US_C)
    axes[0].set_title("Variance explained by component")
    axes[0].set_xlabel("Principal component")
    axes[0].set_ylabel("Variance explained (%)")
    axes[1].plot(pcs, cum, "-o", color=OFFICIAL_C, lw=1.4)
    axes[1].axhline(100, color="#888888", lw=0.6, ls="--")
    axes[1].set_ylim(98.0, 100.2)
    axes[1].set_title("Cumulative variance explained")
    axes[1].set_xlabel("Principal component")
    axes[1].set_ylabel("Cumulative (%)")
    labels = ["PC1", "PC1–2", "PC1–3"]
    vals = [cum[0], cum[1], cum[2]]
    axes[2].bar(labels, vals, color=[EXP_C, OKABE_ITO["skyblue"], TP_C])
    axes[2].set_ylim(98.5, 100.05)
    axes[2].set_title(f"First 3 PCs ≈ {cum[2]:.3f}%")
    axes[2].set_ylabel("Cumulative variance (%)")
    for i, v in enumerate(vals):
        axes[2].text(i, min(v + 0.01, 100.02), f"{v:.3f}", ha="center",
                     va="bottom", fontsize=9)
    fig.suptitle("PCA Diagnostics — US GSW Zero-Coupon Yields (level / slope / curvature)",
                 fontsize=13.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "08_pca_diagnostics")


# ---- 9. affine pricing diagnostics -----------------------------------------
def fig_affine(us):
    obs = us["observed"].to_numpy(float) * 100
    fit = us["fitted"].to_numpy(float) * 100
    resid = (fit - obs) * 100  # bp
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    axes[0].scatter(obs, fit, s=4, color=US_C, alpha=0.20, edgecolors="none")
    lim = [min(obs.min(), fit.min()), max(obs.max(), fit.max())]
    axes[0].plot(lim, lim, color="#666666", lw=1.0, ls="--")
    axes[0].set_xlabel("Observed yield (%)")
    axes[0].set_ylabel("Model-implied yield (%)")
    axes[0].set_title("Actual vs model-implied")
    axes[1].hist(resid, bins=60, color=OKABE_ITO["skyblue"], edgecolor="white", linewidth=0.4)
    axes[1].axvline(0, color="#666666", lw=0.8)
    axes[1].set_xlabel("Fitting residual (bp)")
    axes[1].set_ylabel("Count")
    axes[1].set_title(f"Residual distribution (RMSE {np.sqrt(np.mean(resid**2)):.1f} bp)")
    rm = (us.assign(e=(us["fitted"] - us["observed"]) ** 2)
            .groupby("maturity")["e"].mean().pow(0.5) * 1e4)
    axes[2].bar(rm.index, rm.values, color=TP_C, width=0.7)
    axes[2].set_xlabel("Maturity (years)")
    axes[2].set_ylabel("RMSE (bp)")
    axes[2].set_title("Pricing-fit RMSE by maturity")
    fig.suptitle("Affine Pricing Diagnostics — US (model-implied vs observed zero yields)",
                 fontsize=13.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "09_affine_pricing_diagnostics")


# ---- 10. pipeline diagram --------------------------------------------------
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(7.6, 9.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.grid(False)
    steps = [
        "Zero-coupon yield panel\n(date × maturity)",
        "PCA  →  K=5 pricing factors\n(level / slope / curvature …)",
        r"VAR(1) factor dynamics" "\n" r"$X_{t+1}=\mu+\Phi X_t+v_{t+1}$",
        "Market price of risk\n" r"$\lambda_0,\ \lambda_1$  (3-step OLS on excess returns)",
        "Affine recursions\n" r"$A_n,\ B_n$",
    ]
    ys = np.linspace(0.93, 0.34, len(steps))
    for s, yy in zip(steps, ys):
        ax.text(0.5, yy, s, ha="center", va="center", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.5", fc="#eaf2f8", ec=US_C, lw=1.5))
    for y0, y1 in zip(ys[:-1], ys[1:]):
        ax.annotate("", xy=(0.5, y1 + 0.045), xytext=(0.5, y0 - 0.045),
                    arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.8))
    ax.text(0.27, 0.13, "Expected-rate component\n(risk-neutral yield)",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", fc="#e8f6f0", ec=OFFICIAL_C, lw=1.5))
    ax.text(0.73, 0.13, "Term premium\n(fitted − risk-neutral)",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", fc="#fdf0e3", ec=TP_C, lw=1.5))
    ax.annotate("", xy=(0.27, 0.19), xytext=(0.45, 0.285),
                arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.8))
    ax.annotate("", xy=(0.73, 0.19), xytext=(0.55, 0.285),
                arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.8))
    ax.set_title("ACM Term-Premium Model — Pipeline", fontsize=14, fontweight="bold")
    save(fig, "10_model_pipeline")


# ---- 11. README summary (4-panel) ------------------------------------------
def fig_summary(us, uk, acm, ev, cum):
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))

    ax = axes[0, 0]
    ours = monthly(ser(us, 10.0, "term_premium"))
    off = monthly(acm["term_premium"][10.0])
    j, o, f, c, rmse = corr_rmse(ours, off)
    ax.plot(j, f * 100, color=OFFICIAL_C, lw=1.4, label="NY Fed")
    ax.plot(j, o * 100, color=US_C, lw=1.0, label="Replicated")
    ax.set_title(f"US 10Y validation   (r = {c:.3f}, RMSE = {rmse:.0f} bp)")
    ax.set_ylabel("Term premium (%)")
    ax.legend(loc="lower right", fontsize=8.5)

    ax = axes[0, 1]
    d = uk[uk["maturity"] == 10.0].set_index("date").sort_index()
    ax.plot(d.index, d["observed"] * 100, color=OBS_C, lw=1.1, label="Observed")
    ax.plot(d.index, d["expected_rate"] * 100, color=EXP_C, lw=1.1, label="Exp. short rate")
    ax.plot(d.index, d["term_premium"] * 100, color=TP_C, lw=1.1, label="Term premium")
    ax.set_title("UK 10Y gilt decomposition")
    ax.set_ylabel("Percent")
    ax.legend(loc="upper right", fontsize=8.5, ncol=3)

    ax = axes[1, 0]
    pcs = np.arange(1, len(ev) + 1)
    ax.bar(pcs, ev, color=US_C)
    ax.set_title(f"PCA: variance explained (first 3 PCs ≈ {cum[2]:.2f}%)")
    ax.set_xlabel("Principal component")
    ax.set_ylabel("Variance explained (%)")

    ax = axes[1, 1]
    ust = ser(us, 10.0, "term_premium") * 100
    ukt = ser(uk, 10.0, "term_premium") * 100
    ax.plot(ust.index, ust, color=US_C, lw=1.1, label="US 10Y")
    ax.plot(ukt.index, ukt, color=UK_C, lw=1.1, label="UK 10Y")
    ax.axhline(0, color="#888888", lw=0.6)
    ax.set_title("Cross-country: 10Y term premium")
    ax.set_ylabel("Term premium (%)")
    ax.legend(loc="upper right", fontsize=8.5, ncol=2)

    fig.suptitle("ACM Term-Premium Model — US Treasuries & UK Gilts (from scratch)",
                 fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "11_readme_summary")


def main() -> int:
    set_style()
    if not PANEL_CSV.exists():
        print(f"[!] {PANEL_CSV} not found — run scripts/run_term_premium.py first.")
        return 1
    panel = pd.read_csv(PANEL_CSV, parse_dates=["date"])
    us = panel[panel["currency"] == "USD"].copy()
    uk = panel[panel["currency"] == "GBP"].copy()

    from giltcurve.ingest import fed
    acm = fed.load_nyfed_acm()
    ev, cum = pca_explained(fed.load_gsw_panel(), k=6)

    print("Generating figures into figures/ :")
    fig_us_validation(us, acm)
    fig_per_tenor(us, acm)
    fig_decomposition(us, "US", "US 10Y Treasury", "03a_us_decomposition_10y")
    fig_decomposition(uk, "UK", "UK 10Y Gilt", "03b_uk_decomposition_10y")
    fig_uk_stacked(uk)
    fig_tp_through_time(us, uk)
    fig_heatmap(us, uk)
    fig_cross_country(us, uk)
    fig_pca(ev, cum)
    fig_affine(us)
    fig_pipeline()
    fig_summary(us, uk, acm, ev, cum)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
