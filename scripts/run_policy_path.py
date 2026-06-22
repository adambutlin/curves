#!/usr/bin/env python3
"""End-to-end: real BoE SONIA OIS curve -> implied Bank Rate path + validations.

Pipeline
--------
1. Download + parse the Bank of England's published SONIA OIS curve.
2. Build the discount curve and read the market-implied Bank Rate path,
   sliced at MPC meeting dates.
3. Validate the engine two ways on real data:
     (a) bootstrap round-trip: derive par OIS quotes from the published curve,
         bootstrap them back, compare discount factors (engine algebra);
     (b) forward match: our instantaneous forwards vs BoE's *published*
         instantaneous-forward curve (compounding-convention correctness).
4. Save desk-style charts and the path table.

Run:  python scripts/run_policy_path.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # run without installing

from giltcurve.ingest import boe
from giltcurve.curves.ois_bootstrap import par_ois_rate, bootstrap_ois
from giltcurve.policy.mpc import upcoming_mpc_dates
from giltcurve.policy.meeting_dated import implied_policy_path, implied_cut_probability
from giltcurve.viz.plots import plot_implied_path, plot_curve

BANK_RATE_MINUS_SONIA_BP = 0.0  # set to a few bp to translate implied SONIA -> Bank Rate


def main() -> int:
    data_dir = ROOT / "data" / "raw"
    fig_dir = ROOT / "reports" / "figures"
    proc_dir = ROOT / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)

    try:
        xlsx = boe.ensure_ois_workbook(data_dir)
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[!] Could not fetch BoE data ({exc}).")
        print(f"    Manually download {boe.BOE_LATEST_URL}")
        print(f"    and place '{boe.OIS_WORKBOOK}' in {data_dir}.")
        return 1

    # --- short-end curve -> implied policy path -----------------------------
    short = boe.parse_ois_sheet(xlsx, boe.SHORT_END_SPOT)
    asof, mats, spots = boe.latest_spot_curve(short)
    curve = boe.build_curve_from_spot(mats, spots, asof)

    meetings = upcoming_mpc_dates(asof)
    path = implied_policy_path(
        curve, meetings, asof, bank_rate_minus_sonia_bp=BANK_RATE_MINUS_SONIA_BP
    )

    print(f"\n=== UK SONIA OIS — market-implied Bank Rate path ===")
    print(f"Data as of : {asof:%d %b %Y}  (BoE published OIS curve)")
    print(f"Curve nodes: {len(mats)} maturities to {mats.max():.2f}y (short end)\n")

    show = path.copy()
    show["window"] = [
        f"{a:%d-%b}->{b:%d-%b}" for a, b in zip(show["window_start"], show["window_end"])
    ]
    show["meeting"] = show["meeting"].apply(lambda d: "spot" if d is None else f"{d:%d-%b-%y}")
    show["fwd_SONIA_%"] = (show["fwd_sonia"] * 100).round(3)
    show["impl_BankRate_%"] = (show["implied_bank_rate"] * 100).round(3)
    show["step_bp"] = show["step_bp"].round(1)
    show["cum_bp"] = show["cum_change_bp"].round(1)
    print(show[["meeting", "window", "fwd_SONIA_%", "impl_BankRate_%", "step_bp", "cum_bp"]]
          .to_string(index=False))

    spot_rate = path["implied_bank_rate"].iloc[0]
    if len(path) > 1:
        p1 = implied_cut_probability(path["implied_bank_rate"].iloc[1], spot_rate)
        nxt = path["meeting"].iloc[1]
        print(f"\nNext meeting ({nxt:%d %b %Y}): {p1*100:+.0f}% of a 25bp move priced "
              f"({'cut' if p1 > 0 else 'hike'}).")
    print(f"Cumulative to {path['window_end'].iloc[-1]:%b %Y}: "
          f"{path['cum_change_bp'].iloc[-1]:+.0f}bp "
          f"({path['cum_change_bp'].iloc[-1]/25:+.1f} x 25bp).")

    # --- validation (a): bootstrap round-trip on real data ------------------
    full = boe.parse_ois_sheet(xlsx, boe.FULL_SPOT)
    _, fmats, fspots = boe.latest_spot_curve(full)
    grid = np.arange(1, 16)
    sel = np.isin(fmats, grid.astype(float))
    ref = boe.build_curve_from_spot(fmats[sel], fspots[sel], asof)
    tenors = fmats[sel].astype(int)
    pars = np.array([par_ois_rate(ref, int(T)) for T in tenors])
    booted = bootstrap_ois(tenors, pars)
    max_df_err = float(np.max(np.abs(booted.df(tenors) - ref.df(tenors))))

    # --- validation (b): match BoE's published instantaneous forwards -------
    fwd_sheet = boe.parse_ois_sheet(xlsx, boe.SHORT_END_FWD)
    boe_fwd = fwd_sheet.loc[fwd_sheet.index[-1]].dropna()
    ours = curve.inst_forward(boe_fwd.index.to_numpy(float))
    fwd_rmse_bp = float(np.sqrt(np.nanmean((ours - boe_fwd.to_numpy(float)) ** 2)) * 1e4)

    print("\n--- validation ---")
    print(f"(a) bootstrap round-trip (par->DF->bootstrap): max |dDF| = {max_df_err:.2e}")
    print(f"(b) vs BoE published instantaneous forwards   : RMSE   = {fwd_rmse_bp:.2f} bp")

    # --- artefacts ----------------------------------------------------------
    inst_fwd = curve.inst_forward(mats)
    p1 = plot_implied_path(path, asof, fig_dir / "implied_policy_path.png")
    p2 = plot_curve(mats, spots, inst_fwd, asof, fig_dir / "ois_curve.png")
    csv = proc_dir / "implied_policy_path.csv"
    path.to_csv(csv, index=False)

    print("\nsaved:")
    for p in (p1, p2, csv):
        print("  ", Path(p).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
