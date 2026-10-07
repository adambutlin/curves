"""Research output for "What drove the 2026 Treasury selloff?".

Turns the frozen model's existing results into the public research note. Nothing is
estimated here: estimation lives in ``run_brandt.py --sync ois`` (the end-2025 model) and
``run_us_curve.py freeze`` (the Treasury-curve loadings), both frozen and hashed before
2026 data were used. Three steps:

  extract   apply the frozen model and loadings, draw by draw, to the 2026 data and
            write aggregate tables to ``output/data/``. Needs the licensed LSEG cache in
            ``data/raw/`` (see ``data/README.md``); skipped, with a message, without it.
            Before writing anything it checks that the median-target model reproduces
            the committed 2026 totals (``reports/structural_propagation/us_curve/``).
  tables    summary tables that need only committed results (curve signatures, fit,
            forecasting, replication record)
  figures   ``output/figures/`` from ``output/data/`` alone
  page      ``output/2026_treasury_selloff.html`` from ``output/data/`` alone

Usage:  python scripts/build_research_output.py               # every step it can run
        python scripts/build_research_output.py --skip-extract
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "structural_propagation"
US_CURVE = REPORTS / "us_curve"
OUT = ROOT / "output"
DATA = OUT / "data"

LOADINGS_SHA = "3015f33ca4af04410116fd5f53227b1a508f864b5be923e314588ddd43467158"
LAST_DAY = "2026-10-05"            # end of the committed 2026 application (apply_summary.json)
# Windows run from close to close: (exclusive start, inclusive end). The first starts at the
# close of 30 December 2025, the model's last day of 2025 (Eurex was shut on 31 December), so
# 31 December's moves fall into the first 2026 day. 27 Feb and 19 Aug are pre-registered.
WINDOWS = {
    "30 Dec 2025 to 5 Oct 2026": ("2025-12-30", LAST_DAY),
    "30 Dec 2025 to 27 Feb 2026": ("2025-12-30", "2026-02-27"),
    "27 Feb to 19 Aug 2026": ("2026-02-27", "2026-08-19"),
    "19 Aug to 5 Oct 2026": ("2026-08-19", LAST_DAY),
}
MATURITIES = {"2y": {"y2": 1.0}, "5y": {"y5": 1.0}, "10y": {"y10": 1.0}, "30y": {"y30": 1.0},
              "2s10s": {"y10": 1.0, "y2": -1.0}, "10s30s": {"y30": 1.0, "y10": -1.0}}
ACM = {"2y": ("acm2", "rn2", "tp2"), "5y": ("acm5", "rn5", "tp5"), "10y": ("acm10", "rn10", "tp10")}
ACM_LABEL = {"acm": "ACM fitted yield", "rn": "ACM expected short rates", "tp": "ACM term premium"}
# shock order in the model: ea_monetary, ea_macro, us_monetary, us_macro, global_risk
COMPONENTS = {"us_news": [2, 3], "us_macro": [3], "us_monetary": [2], "global_risk": [4],
              "euro_area": [0, 1], "ea_monetary": [0], "ea_macro": [1], "all_shocks": [0, 1, 2, 3, 4]}
ORIGINS = ("us_news", "global_risk", "euro_area")
FULL = "30 Dec 2025 to 5 Oct 2026"
TENOR_NAME = {"y2": "2y", "y5": "5y", "y10": "10y", "y30": "30y"}


def q(x: np.ndarray, p: float) -> float:
    return float(np.percentile(x, p))


# ---------------------------------------------------------------- extract (licensed inputs)
def licensed_inputs_present(data_dir: Path) -> bool:
    need = ["lseg_EUREON10Y_.csv", "lseg_EUREST10Y_.csv", "lseg_STXEc1.csv", "lseg_STXEc2.csv",
            "lseg_EUR_.csv", "lseg_US10YT_RR.csv"]
    return all((data_dir / f).exists() for f in need)


def contributions_2026(data_dir: Path):
    """Per-draw daily contributions in 2026 from the frozen model and loadings.

    Returns ``dates`` (2026 model days to LAST_DAY), ``C`` {outcome: (J, T, K)}, ``A``
    {outcome: (T,) actual changes, bp}, the median-target draw and the last model day of
    2025, whose close the first 2026 change is measured from.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_us_curve as R                                  # frozen paths, SHA checks
    from giltcurve.propagation import brandt, uscurve as uc

    model = R.load_frozen(*R.MODEL)
    theta = R.load_frozen(R.LOADINGS, LOADINGS_SHA)["theta"]
    panel = brandt.load_panel_sync(str(data_dir), end="2026-12-31", unseal_holdout=True)
    panel = panel.loc[panel.index <= pd.Timestamp(LAST_DAY)]
    dates, eps = R.model_shocks(panel, model)
    dy = R.outcome_changes(dates, str(data_dir), unseal=True)
    first = int(np.searchsorted(dates, R.START_2026))
    idx = {o: i for i, o in enumerate(R.OUTCOMES)}
    C = {o: np.stack([uc.contributions(e, theta[j, idx[o]])[first:] for j, e in enumerate(eps)])
         for o in R.OUTCOMES}
    A = {o: dy[o].to_numpy()[first:] for o in R.OUTCOMES}
    return dates[first:], C, A, R.median_target(model), dates[first - 1]


def verify_against_committed(dates, C, A, mt) -> float:
    """Largest gap (bp) between the median-target totals and the committed application."""
    win = pd.read_csv(US_CURVE / "decomposition_windows.csv")
    shocks = ["ea_monetary", "ea_macro", "us_monetary", "us_macro", "global_risk"]
    committed = {"2026 to date": ("2025-12-31", LAST_DAY), "27 Feb-19 Aug 2026": ("2026-02-27", "2026-08-19")}
    gap = 0.0
    for o in ("y2", "y5", "y10", "y30", "acm10", "rn10", "tp10"):
        for label, (a, z) in committed.items():
            m = window(dates, a, z)
            row = win[(win.outcome == o) & (win.window == label)].iloc[0]
            tot = C[o][mt][m].sum(axis=0)
            gap = max(gap, abs(np.nansum(A[o][m]) - row["actual_bp"]),
                      *(abs(tot[k] - row[f"{s}_bp"]) for k, s in enumerate(shocks)))
    return gap


def window(dates, a, z) -> np.ndarray:
    return np.asarray((dates > pd.Timestamp(a)) & (dates <= pd.Timestamp(z)))


def combine(arrs: dict, weights: dict):
    return sum(w * arrs[o] for o, w in weights.items())


def component_stats(tot: np.ndarray, actual: float, mt: int) -> dict:
    """tot (J, K) window totals by shock -> median-target value, quantiles and probabilities."""
    row = {}
    comp = {c: tot[:, ix].sum(axis=1) for c, ix in COMPONENTS.items()}
    comp["unspanned"] = actual - comp["all_shocks"]
    for c, x in comp.items():
        row.update({f"{c}_mt": float(x[mt]), f"{c}_p05": q(x, 5), f"{c}_p50": q(x, 50), f"{c}_p95": q(x, 95)})
    lead = np.abs(np.column_stack([comp[o] for o in ORIGINS])).argmax(axis=1)
    row.update({"p_us_largest": float(np.mean(lead == 0)), "p_global_largest": float(np.mean(lead == 1)),
                "p_euro_largest": float(np.mean(lead == 2)),
                "p_us_news_positive": float(np.mean(comp["us_news"] > 0)),
                "p_all_shocks_positive": float(np.mean(comp["all_shocks"] > 0)),
                "p_macro_gt_monetary": float(np.mean(comp["us_macro"] > comp["us_monetary"]))})
    return row


def extract(data_dir: Path) -> None:
    dates, C, A, mt, start_day = contributions_2026(data_dir)
    gap = verify_against_committed(dates, C, A, mt)
    if gap > 0.05:
        raise RuntimeError(f"the frozen model no longer reproduces the committed 2026 totals "
                           f"(largest gap {gap:.3f}bp): has the data cache changed?")
    print(f"extract: median-target model reproduces the committed totals (largest gap {gap:.4f}bp)")
    DATA.mkdir(parents=True, exist_ok=True)
    A0 = {o: np.nan_to_num(a) for o, a in A.items()}       # bond holidays fold into the next day

    # 0. context from public series: H.15 yield levels and the S&P 500 over the same window
    from giltcurve.ingest.market import load_fred, load_yahoo_close
    end = pd.Timestamp(LAST_DAY)
    rows = []
    for o, mat in TENOR_NAME.items():
        s = load_fred(f"DGS{o[1:]}", data_dir, max_age_days=None)
        s26 = s.loc[(s.index > start_day) & (s.index <= end)]
        rows.append({"series": f"{mat} Treasury yield, H.15 (%)", "start_close": float(s.loc[:start_day].iloc[-1]),
                     "close_31dec2025": float(s.loc[:"2025-12-31"].iloc[-1]), "close_5oct2026": float(s.loc[:end].iloc[-1]),
                     "low_2026": float(s26.min()), "low_date": str(s26.idxmin().date()),
                     "high_2026": float(s26.max()), "high_date": str(s26.idxmax().date())})
    spx = load_yahoo_close("^GSPC", data_dir, max_age_days=None)
    rows.append({"series": "S&P 500 index", "start_close": float(spx.loc[:start_day].iloc[-1]),
                 "close_31dec2025": float(spx.loc[:"2025-12-31"].iloc[-1]), "close_5oct2026": float(spx.loc[:end].iloc[-1])})
    ctx = pd.DataFrame(rows)
    ctx.insert(1, "start_date", str(start_day.date()))
    ctx.round(4).to_csv(DATA / "market_context_2026.csv", index=False)

    # 1. window decomposition by maturity and slope
    rows = []
    for mat, w in MATURITIES.items():
        c, a = combine(C, w), combine(A0, w)
        for label, (s, z) in WINDOWS.items():
            m = window(dates, s, z)
            actual = float(a[m].sum())
            row = {"maturity": mat, "window": label, "actual_bp": actual}
            row.update(component_stats(c[:, m].sum(axis=1), actual, mt))
            row["p_us_more_than_half"] = (float(np.mean(c[:, m][:, :, [2, 3]].sum(axis=(1, 2)) > 0.5 * actual))
                                          if mat in ("2y", "5y", "10y", "30y") else np.nan)
            rows.append(row)
    pd.DataFrame(rows).round(3).to_csv(DATA / "decomposition_2026.csv", index=False)

    # 2. ACM expected rates and term premium, decomposed the same way (2026 to date)
    rows = []
    m = window(dates, *WINDOWS[FULL])
    for mat, outs in ACM.items():
        for o in outs:
            actual = float(A0[o][m].sum())
            row = {"maturity": mat, "series": ACM_LABEL[o.rstrip("0123456789")], "actual_bp": actual}
            row.update(component_stats(C[o][:, m].sum(axis=1), actual, mt))
            rows.append(row)
    pd.DataFrame(rows).round(3).to_csv(DATA / "acm_comparison_2026.csv", index=False)

    # 3. monthly contributions by origin
    rows = []
    per = dates.to_period("M")
    for o, mat in TENOR_NAME.items():
        for p in per.unique():
            mm = np.asarray(per == p)
            actual = float(A0[o][mm].sum())
            st = component_stats(C[o][:, mm].sum(axis=1), actual, mt)
            row = {"maturity": mat, "month": str(p), "days": int(mm.sum()), "actual_bp": actual}
            row.update({k: st[k] for k in ("us_news_mt", "global_risk_mt", "euro_area_mt", "unspanned_mt",
                                           "us_news_p05", "us_news_p50", "us_news_p95",
                                           "p_us_largest", "p_global_largest", "p_euro_largest")})
            rows.append(row)
    pd.DataFrame(rows).round(3).to_csv(DATA / "monthly_2026.csv", index=False)

    # 4. the 10-year, day by day: cumulative contributions by origin. Only origin groups are
    # published daily, and only for one maturity, so the licensed daily series cannot be
    # recovered from these tables (see data/README.md).
    c10 = np.cumsum(C["y10"], axis=1)                                   # (J, T, K)
    grp = {g: c10[:, :, COMPONENTS[g]].sum(axis=2) for g in (*ORIGINS, "all_shocks")}
    act = np.cumsum(A0["y10"])
    daily = pd.DataFrame({"actual": act, "us_news": grp["us_news"][mt], "global_risk": grp["global_risk"][mt],
                          "euro_area": grp["euro_area"][mt], "unspanned": act - grp["all_shocks"][mt]},
                         index=pd.Index(dates.date, name="date"))
    for g in (*ORIGINS, "all_shocks"):
        for p in (5, 50, 95):
            daily[f"{g}_p{p:02d}"] = np.percentile(grp[g], p, axis=0)
    start = pd.DataFrame(0.0, index=pd.Index([start_day.date()], name="date"), columns=daily.columns)
    pd.concat([start, daily]).round(2).to_csv(DATA / "us10y_daily_cumulative_2026.csv")
    print(f"extract: wrote 4 tables to {DATA.relative_to(ROOT)} ({len(dates)} days of 2026, {C['y10'].shape[0]} draws)")


# ---------------------------------------------------------------- tables from committed results
def tables() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    # curve signature of each shock: total loading (lags 0-2) per one-standard-deviation shock
    lz = np.load(US_CURVE / "loadings_end2025.npz")
    theta, outs = lz["theta"], list(lz["outcomes"])
    J, _, n = theta.shape
    K = 5
    sig = theta[:, :, 1:].reshape(J, len(outs), (n - 1) // K, K).sum(axis=2)        # (J, out, K)
    mt = json.loads((US_CURVE / "freeze_summary.json").read_text())["median_target_draw"]
    names = ["ea_monetary", "ea_macro", "us_monetary", "us_macro", "global_risk"]
    i2, i10 = outs.index("y2"), outs.index("y10")
    rows = []
    for k, s in enumerate(names):
        steep = np.sign(sig[:, i10, k]) * (sig[:, i10, k] - sig[:, i2, k]) > 0
        for o, mat in TENOR_NAME.items():
            x = sig[:, outs.index(o), k]
            rows.append({"shock": s, "maturity": mat, "bp_per_sd_mt": float(x[mt]), "p05": q(x, 5),
                         "p50": q(x, 50), "p95": q(x, 95), "p_steepens_2s10s": float(steep.mean())})
    pd.DataFrame(rows).round(3).to_csv(DATA / "curve_signatures.csv", index=False)

    # explanatory fit, in sample (2007-2025) and with the frozen loadings in 2026
    fz = json.loads((US_CURVE / "freeze_summary.json").read_text())["in_sample_fit"]
    ap = json.loads((US_CURVE / "apply_summary.json").read_text())["fit_2026"]
    rows = [{"maturity": mat, "r2_daily_2007_2025": fz[o]["r2_daily_mt"], "r2_daily_2026": ap[o]["daily"]["r2"],
             "rmse_daily_2026_bp": ap[o]["daily"]["rmse_bp"], "sd_daily_2026_bp": ap[o]["daily"]["sd_bp"],
             "r2_5day_2007_2025": fz[o]["r2_5d_mt"], "r2_5day_2026": ap[o]["5d"]["r2"]}
            for o, mat in TENOR_NAME.items()]
    pd.DataFrame(rows).round(4).to_csv(DATA / "explanatory_fit.csv", index=False)

    # forecasting from the next close (and the same-close artefact), out of sample
    fs = pd.read_csv(US_CURVE / "forecast_summary.csv")
    fs = fs.rename(columns={"outcome": "maturity", "h": "horizon_days", "from": "measured_from",
                            "r2_m1": "r2_own_move", "r2_m2": "r2_curve_state", "r2_m3": "r2_origin",
                            "r2_m4": "r2_all_innovations", "cw_p_m3_vs_m2": "cw_p_origin_vs_curve_state",
                            "cw_p_m4_vs_m2": "cw_p_innovations_vs_curve_state",
                            "cw_p_m3_vs_m0": "cw_p_origin_vs_no_change", "rmse_m0": "rmse_no_change_bp"})
    fs["maturity"] = fs["maturity"].map(TENOR_NAME)
    fs["period"] = fs["period"].map({"2012-2025": "2012-2025 real time", "2026": "2026 frozen model"})
    keep = ["maturity", "horizon_days", "measured_from", "period", "n", "rmse_no_change_bp", "r2_own_move",
            "r2_curve_state", "r2_origin", "r2_all_innovations", "cw_p_origin_vs_curve_state",
            "cw_p_innovations_vs_curve_state", "cw_p_origin_vs_no_change"]
    fs[keep].round(4).to_csv(DATA / "forecast_oos.csv", index=False)

    # replication record of the frozen model (2007-2025)
    sm = json.loads((REPORTS / "brandt_sync" / "summary.json").read_text())
    ev = pd.read_csv(REPORTS / "brandt_sync" / "event_study.csv")
    sh = sm["origin_shares_full_sample"]
    rec = {"sample": sm["sample"], "admissible_draws": sm["n_draws"], "acceptance_rate": sm["acceptance_rate"],
           "us_share_of_euro_rate_variance": sh["d_ea10"]["us"],
           "us10_variance_shares": sh["d_us10"],
           "events": len(ev), "events_hit_median_target": int(ev["hit_mt"].sum()),
           "events_mean_share_of_draws_hit": float(ev["share_draws_hit"].mean())}
    (DATA / "model_record.json").write_text(json.dumps(rec, indent=2))
    print(f"tables: wrote curve signatures, fit, forecasting and replication record to {DATA.relative_to(ROOT)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--skip-extract", action="store_true", help="use the committed tables in output/data/")
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir)
    if args.skip_extract:
        print("extract: skipped on request; using the committed tables in output/data/")
    elif licensed_inputs_present(data_dir):
        extract(data_dir)
    else:
        print("extract: the licensed LSEG cache is not in data/raw/ (see data/README.md); "
              "using the committed tables in output/data/")
    tables()
    sys.path.insert(0, str(ROOT / "scripts"))
    import research_figures
    import research_page
    research_figures.build(DATA, OUT / "figures")
    research_page.build(DATA, OUT / "2026_treasury_selloff.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
