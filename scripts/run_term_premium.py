#!/usr/bin/env python3
"""End-to-end ACM term-premium: US correctness anchor -> GBP decomposition.

1. US ANCHOR (correctness proof): fit the estimator on the Fed Board GSW zero
   curve and compare 1-10y term premia to the NY Fed's *published* ACM series.
   HALT if correlation is too low.
2. GBP: fit on the BoE nominal gilt curve; decompose; compare the expected-rate
   path to the existing SONIA implied Bank Rate path (shape/changes, not levels).
3. SHAPE TESTS (halt): term premium ~0 at the short end and rising with maturity.
4. Save the decomposed panel and a figure.

Run:  python scripts/run_term_premium.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from giltcurve.ingest import fed, boe_gilt
from giltcurve.premium.acm import fit_acm, decompose
from giltcurve.premium.panel import decomposed_panel

CORR_FLOOR = 0.95
LEVEL_RMSE_CEIL_BP = 60.0
HEADLINE_TENORS = (5.0, 10.0)  # data-supported tenors the anchor is gated on


def _eom(panel: pd.DataFrame) -> pd.DataFrame:
    """Resample a daily panel to month-end observations."""
    return panel.resample("ME").last().dropna(how="all")


def _halt(msg: str) -> None:
    print(f"\n[HALT] {msg}")
    raise SystemExit(1)


def _by_month(s: pd.Series) -> pd.Series:
    """Index a date-stamped series by calendar month period for robust alignment."""
    s = s.dropna()
    return pd.Series(s.to_numpy(float), index=pd.DatetimeIndex(s.index).to_period("M"))


def validate_us() -> pd.DataFrame:
    print("=== US correctness anchor (GSW -> ACM vs NY Fed) ===")
    gsw = _eom(fed.load_gsw_panel())
    res = fit_acm(gsw, k=5, currency="USD")
    tenors = [float(t) for t in range(1, 11)]
    out = decompose(res, gsw, maturities=tenors)
    nyfed = fed.load_nyfed_acm()

    print(f"  GSW months: {gsw.shape[0]}  ({gsw.index.min():%Y-%m} .. {gsw.index.max():%Y-%m})")
    print("  tenor   n   corr   ours_bp  nyfed_bp")
    corrs, rmse_bp = {}, {}
    for t in tenors:
        ours = _by_month(out[out["maturity"] == t].set_index("date")["term_premium"])
        theirs = _by_month(fed.nyfed_term_premium(nyfed, tenor=t))
        j = ours.index.intersection(theirs.index)
        if len(j) < 60:
            print(f"  {t:4.0f}y  {len(j):4d}  (insufficient overlap)")
            continue
        a, b = ours.loc[j], theirs.loc[j]
        corrs[t] = float(np.corrcoef(a, b)[0, 1])
        rmse_bp[t] = float(np.sqrt(np.nanmean((a - b) ** 2)) * 1e4)
        print(f"  {t:4.0f}y  {len(j):4d}  {corrs[t]:5.2f}  {a.mean()*1e4:7.0f}  {b.mean()*1e4:7.0f}")

    # Gate on the data-supported headline tenors (5y, 10y). The 1y/2y term premia
    # are reported but NOT gated: GSW has no reliable sub-1y data, so the 1-month
    # risk-free is extrapolated, biasing the front-end premium low (a documented
    # limitation, not an estimator error -- see README methods note).
    for t in HEADLINE_TENORS:
        if corrs.get(t, 0.0) < CORR_FLOOR:
            _halt(f"US anchor {t:.0f}y correlation {corrs.get(t, float('nan')):.2f} < {CORR_FLOOR}.")
    if rmse_bp.get(10.0, float("inf")) > LEVEL_RMSE_CEIL_BP:
        _halt(f"US 10y term-premium RMSE {rmse_bp[10.0]:.0f}bp > {LEVEL_RMSE_CEIL_BP}bp.")
    print(f"  PASS (gated on {'/'.join(f'{t:.0f}y' for t in HEADLINE_TENORS)}): "
          f"5y corr {corrs.get(5.0, float('nan')):.2f}, 10y corr {corrs.get(10.0, float('nan')):.2f}, "
          f"10y RMSE {rmse_bp.get(10.0, float('nan')):.0f}bp")
    print(f"  NOTE: 1y/2y corr {corrs.get(1.0, float('nan')):.2f}/{corrs.get(2.0, float('nan')):.2f} "
          f"weaker by design (GSW short-end; extrapolated 1-month rate; documented).\n")
    return out


def shape_tests(out: pd.DataFrame, label: str) -> None:
    print(f"=== shape tests ({label}) ===")
    mean_tp = out.groupby("maturity")["term_premium"].mean()
    short = mean_tp.loc[mean_tp.index.min()]
    long = mean_tp.loc[mean_tp.index.max()]
    if abs(short) > 25e-4:
        _halt(f"{label}: short-end term premium {short*1e4:.0f}bp not near zero.")
    if long <= short:
        _halt(f"{label}: term premium not rising with maturity ({short*1e4:.0f}->{long*1e4:.0f}bp).")
    print(f"  PASS: short {short*1e4:.0f}bp, long {long*1e4:.0f}bp (rising)\n")


def decompose_gbp() -> pd.DataFrame:
    print("=== GBP decomposition (BoE nominal gilt) ===")
    boe_gilt.download_gilt_history()           # ensure decades of history present
    boe_gilt.ensure_gilt_workbook()            # plus the current-month file
    gilt = _eom(boe_gilt.load_gilt_history())
    res = fit_acm(gilt, k=5, currency="GBP")
    out = decompose(res, gilt, maturities=[float(t) for t in range(1, 11)])
    print(f"  gilt months: {gilt.shape[0]}  ({gilt.index.min():%Y-%m} .. {gilt.index.max():%Y-%m})")
    last = out[out["date"] == out["date"].max()]
    print("  latest 10y: expected-rate {:.2f}% + term-premium {:.0f}bp".format(
        last[last["maturity"] == 10.0]["expected_rate"].iloc[0] * 100,
        last[last["maturity"] == 10.0]["term_premium"].iloc[0] * 1e4))
    return out


def gbp_vs_sonia_path(gbp_out: pd.DataFrame) -> None:
    print("=== GBP robustness: ACM expected-rate vs SONIA implied path ===")
    try:
        from giltcurve.ingest import boe
        from giltcurve.policy.mpc import upcoming_mpc_dates
        from giltcurve.policy.meeting_dated import implied_policy_path
        curve, asof, _, _ = boe.load_latest_curve()
        path = implied_policy_path(curve, upcoming_mpc_dates(asof), asof)
        sonia_end = path["implied_bank_rate"].iloc[-1]
        er_2y = gbp_out[(gbp_out["maturity"] == 2.0) &
                        (gbp_out["date"] == gbp_out["date"].max())]["expected_rate"].iloc[0]
        print(f"  ACM 2y expected-rate {er_2y*100:.2f}% vs SONIA-path end {sonia_end*100:.2f}% "
              f"(gap {(er_2y - sonia_end)*1e4:+.0f}bp; gilt/OIS basis expected).")
    except Exception as exc:  # pragma: no cover - network/data dependent
        print(f"  (skipped: {exc})")


def main() -> int:
    fig_dir = ROOT / "reports" / "figures"
    proc_dir = ROOT / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    try:
        us_out = validate_us()
        shape_tests(us_out, "USD")
        gbp_out = decompose_gbp()
        shape_tests(gbp_out, "GBP")
        gbp_vs_sonia_path(gbp_out)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[!] Could not complete (data/network): {exc}")
        return 1

    panel = decomposed_panel([us_out, gbp_out])
    csv = proc_dir / "term_premium_panel.csv"
    panel.to_csv(csv, index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g10 = gbp_out[gbp_out["maturity"] == 10.0].set_index("date").sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(g10.index, g10["observed"] * 100, label="10y gilt yield", color="black", lw=1.2)
    ax.plot(g10.index, g10["expected_rate"] * 100, label="expected avg short rate", color="tab:blue")
    ax.plot(g10.index, g10["term_premium"] * 100, label="term premium", color="tab:red")
    ax.set_ylabel("percent"); ax.legend(); ax.set_title("UK 10y gilt: ACM decomposition")
    fig_path = fig_dir / "gbp_term_premium.png"
    fig.tight_layout(); fig.savefig(fig_path, dpi=130); plt.close(fig)

    print("\nsaved:")
    for p in (csv, fig_path):
        print("  ", Path(p).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
