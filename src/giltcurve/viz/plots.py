"""Desk-style charts: the implied policy path and the OIS curve.

Kept deliberately presentational (no display side effects) so it renders in
headless/CI runs. Styling aims at a research-note look rather than defaults.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe
import matplotlib.pyplot as plt
import numpy as np

NAVY = "#1f4e79"
RUST = "#a6321e"
_SOURCE = "Source: Bank of England SONIA OIS curve; author's calculations."


def _style(ax):
    ax.grid(True, alpha=0.25, lw=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def plot_implied_path(path_df, asof, outpath, current_rate=None):
    """Step chart of the market-implied Bank Rate path by MPC window."""
    starts = list(path_df["window_start"])
    ends = list(path_df["window_end"])
    rates = path_df["implied_bank_rate"].to_numpy(float) * 100.0

    xs = starts + [ends[-1]]
    ys = list(rates) + [rates[-1]]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.step(xs, ys, where="post", lw=2.2, color=NAVY)
    ax.scatter(starts[1:], rates[1:], color=NAVY, zorder=3, s=28)

    for i, row in path_df.iterrows():
        if row["meeting"] is not None:
            ax.annotate(
                f"{row['cum_change_bp']:+.0f}bp",
                (row["window_start"], rates[i]),
                textcoords="offset points", xytext=(4, 8), fontsize=8, color=RUST,
            )

    total = path_df["cum_change_bp"].iloc[-1]
    direction = "easing" if total < 0 else "tightening"
    ax.set_title(
        f"UK market-implied Bank Rate path (SONIA OIS) — as of {asof:%d %b %Y}\n"
        f"{abs(total):.0f}bp of {direction} priced to {ends[-1]:%b %Y}",
        fontsize=11, loc="left",
    )
    ax.set_ylabel("Implied Bank Rate (%)")
    _style(ax)
    fig.text(0.01, -0.02, _SOURCE, fontsize=7.5, color="grey")
    fig.autofmt_xdate()
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return outpath


def plot_curve(maturities, spot, inst_fwd, asof, outpath):
    """Overlay the OIS spot (zero) curve and the instantaneous-forward curve."""
    m = np.asarray(maturities, float)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(m, np.asarray(spot, float) * 100, color=NAVY, lw=2, label="OIS spot (zero) rate")
    ax.plot(m, np.asarray(inst_fwd, float) * 100, color=RUST, lw=1.8, ls="--",
            label="Instantaneous forward")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Rate (%)")
    ax.set_title(f"UK SONIA OIS curve — as of {asof:%d %b %Y}", fontsize=11, loc="left")
    ax.legend(frameon=False)
    _style(ax)
    fig.text(0.01, -0.02, _SOURCE, fontsize=7.5, color="grey")
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return outpath
