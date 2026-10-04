"""Cross-Atlantic model (Brandt et al., 2021) on free data: replication, propagation, freeze.

Follows pre-registration 08. Writes to ``reports/structural_propagation/brandt/`` and
freezes the end-2025 model (``model_brandt_end2025.npz`` with its SHA-256) before any
2026 observation is used.

Usage:  python scripts/run_brandt.py [--data-dir DIR] [--quick]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.ingest.market import load_fred, load_yahoo_close
from giltcurve.propagation import brandt
from giltcurve.propagation.identification import random_rotations
from giltcurve.propagation.oos import summarise
from giltcurve.propagation.predictive import propagation_ratio_test, reduced_form_test_generic

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261008
P = brandt.LAGS
PERIODS = {"2004-2025": (2004, 2025), "2004-2007": (2004, 2007),
           "2008-2019": (2008, 2019), "2020-2025": (2020, 2025)}


def event_study(panel, ident, eps):
    """Two-day euro-area 10-year change around Brandt et al.'s events, by shock."""
    dates = panel.index[P:]
    b = ident.B[:, 0, :]                                          # impact on the EA 10y
    j_mt = ident.median_target()
    rows = []
    for day, name, expected in brandt.EVENTS:
        i = int(np.searchsorted(dates, pd.Timestamp(day)))
        if i + 1 >= len(dates):
            continue
        win = [i, i + 1]
        contrib = np.array([(eps[j][win] * b[j]).sum(axis=0) for j in range(len(eps))])  # (J, K)
        exp_idx = [brandt.SHOCKS.index(s) for s in expected]
        top = np.abs(contrib).argmax(axis=1)
        rows.append({"date": str(dates[i].date()), "event": name, "expected": "/".join(expected),
                     "actual_2d_bp": float(panel["d_ea10"].iloc[P + i] + panel["d_ea10"].iloc[P + i + 1]),
                     **{f"{s}_bp": float(contrib[j_mt, k]) for k, s in enumerate(brandt.SHOCKS)},
                     "dominant_mt": brandt.SHOCKS[int(top[j_mt])],
                     "hit_mt": bool(top[j_mt] in exp_idx),
                     "share_draws_hit": float(np.isin(top, exp_idx).mean())})
    return pd.DataFrame(rows)


def risk_validation(panel, eps, data_dir):
    """Correlation of the global-risk shock with daily changes in VIX and MOVE."""
    dates = panel.index[P:]
    out = {}
    for name, series in (("VIX", load_fred("VIXCLS", data_dir)),
                         ("MOVE", load_yahoo_close("^MOVE", data_dir))):
        lv = series.reindex(panel.index).ffill()
        d = lv.diff().iloc[P:].to_numpy()
        corr = [np.corrcoef(e[:, 4][np.isfinite(d)], d[np.isfinite(d)])[0, 1] for e in eps]
        out[name] = {"median_corr": float(np.median(corr)), "p05": float(np.quantile(corr, 0.05)),
                     "p95": float(np.quantile(corr, 0.95)), "days": int(np.isfinite(d).sum())}
    return out


def propagation(panel, post, ident, eps, rng, n_placebo, label):
    U = post.residuals()
    own = brandt.own_moves(panel).iloc[P:]
    Z = brandt.controls(panel).iloc[P:].to_numpy()
    fwd = brandt.forward_changes(panel)
    Brand = random_rotations(post.sigma_mean, n_placebo, rng)
    perms = [rng.permutation(5) for _ in range(n_placebo)]
    eps_rand = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    a_rows, b_rows, c_rows = [], [], []
    for o in brandt.OUTCOMES:
        x = own[o].to_numpy()
        others = brandt.other_innovations(U, o)
        b_all = brandt.impact_on(ident.B, o)
        b_rand = brandt.impact_on(Brand, o)
        parts = [brandt.origin_contributions(eps[j], b_all[j], o) for j in range(len(eps))]
        parts_r = [brandt.origin_contributions(
            eps_rand[i], b_rand[i], o, groups=(list(perms[i][:2]), list(perms[i][2:4]), [perms[i][4]]))
            for i in range(n_placebo)]
        for h in brandt.HORIZONS:
            r = fwd[(o, h)].iloc[P:].to_numpy()
            a_rows.append({"set": label, "outcome": o, "h": h,
                           **reduced_form_test_generic(r, x, others, Z, h)})
            for j in range(len(eps)):
                bt = propagation_ratio_test(r, eps[j], b_all[j], Z, h)
                b_rows.append({"set": label, "outcome": o, "h": h, "draw": j,
                               **{f"gamma_{s}": bt["gamma"][k] for k, s in enumerate(brandt.SHOCKS)},
                               **{f"impact_{s}": b_all[j][k] for k, s in enumerate(brandt.SHOCKS)}})
            cs = pd.DataFrame([brandt.origin_split_test(r, x, cf, cg, Z, h) for cf, cg in parts])
            pl = np.array([brandt.origin_split_test(r, x, cf, cg, Z, h, with_se=False)["incr_r2"]
                           for cf, cg in parts_r])
            p90 = float(np.quantile(pl, 0.9))
            c_rows.append({
                "set": label, "outcome": o, "h": h,
                "theta_domestic_med": cs["theta_domestic"].median(),
                "kappa_foreign_med": cs["kappa_foreign"].median(),
                "kappa_foreign_p05": cs["kappa_foreign"].quantile(0.05),
                "kappa_foreign_p95": cs["kappa_foreign"].quantile(0.95),
                "kappa_global_med": cs["kappa_global"].median(),
                "kappa_global_p05": cs["kappa_global"].quantile(0.05),
                "kappa_global_p95": cs["kappa_global"].quantile(0.95),
                "share_draws_p_lt_0.05": float((cs["p"] < 0.05).mean()),
                "incr_r2_med": cs["incr_r2"].median(), "placebo_incr_r2_p90": p90,
                "share_draws_beat_placebo_p90": float((cs["incr_r2"] > p90).mean())})
    return pd.DataFrame(a_rows), pd.DataFrame(b_rows), pd.DataFrame(c_rows)


def summarise_b(bdf):
    rows = []
    for (s, o, h), g in bdf.groupby(["set", "outcome", "h"], sort=False):
        row = {"set": s, "outcome": o, "h": h}
        for k in brandt.SHOCKS:
            for stat in ("gamma", "impact"):
                x = g[f"{stat}_{k}"]
                row[f"{stat}_{k}_med"] = x.median()
                row[f"{stat}_{k}_p05"] = x.quantile(0.05)
                row[f"{stat}_{k}_p95"] = x.quantile(0.95)
            row[f"share_gamma_{k}_pos"] = float((g[f"gamma_{k}"] > 0).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation" / "brandt"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_draws, n_placebo, n_oos = (40, 40, 10) if args.quick else (1000, 1000, 200)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    panel = brandt.load_panel(args.data_dir)                 # sealed: ends 2025-12-31
    summary = {"seed": SEED, "n_draws": n_draws, "sample": [str(panel.index.min().date()),
               str(panel.index.max().date()), len(panel)],
               "daily_corr": panel[list(brandt.VARIABLES)].corr().round(3).to_dict()}

    post, ident = brandt.identify(panel, n_draws, rng)
    summary["acceptance_rate"] = ident.acceptance_rate
    eps = brandt.shocks_by_draw(panel, ident)
    summary["origin_shares_1999_2025"] = brandt.origin_variance_shares(ident)
    _, ident23 = brandt.identify(panel.loc[:"2023-12-31"], max(n_draws // 2, 30), rng)
    summary["origin_shares_1999_2023"] = brandt.origin_variance_shares(ident23)
    post07, ident07 = brandt.identify(panel.loc["2007-04-02":], max(n_draws // 2, 30), rng)
    summary["origin_shares_2007_2025"] = brandt.origin_variance_shares(ident07)

    ev = event_study(panel, ident, eps)
    ev.to_csv(out / "event_study.csv", index=False)
    summary["event_hit_rate_mt"] = float(ev["hit_mt"].mean())
    summary["event_mean_share_draws_hit"] = float(ev["share_draws_hit"].mean())
    eps07 = brandt.shocks_by_draw(panel.loc["2007-04-02":], ident07)
    ev07 = event_study(panel.loc["2007-04-02":], ident07, eps07)
    summary["event_hit_rate_mt_2007_2025"] = float(ev07["hit_mt"].mean())
    summary["risk_validation"] = risk_validation(panel, eps, args.data_dir)

    a, b, c = propagation(panel, post, ident, eps, rng, n_placebo, "baseline")
    a.to_csv(out / "test_a.csv", index=False)
    summarise_b(b).to_csv(out / "test_b.csv", index=False)
    c.to_csv(out / "test_c_origin.csv", index=False)

    fc = brandt.pseudo_oos(panel, n_draws=n_oos)
    summarise(fc, periods=PERIODS).to_csv(out / "oos_summary.csv", index=False)

    model_path = out / "model_brandt_end2025.npz"
    np.savez_compressed(model_path, B=ident.B, Sigma=ident.Sigma, A=ident.A, A_hat=post.A_hat,
                        variables=np.array(brandt.VARIABLES), shocks=np.array(brandt.SHOCKS), p=P)
    summary["frozen_model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    summary["runtime_seconds"] = round(time.time() - t0, 1)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps({k: v for k, v in summary.items() if k != "daily_corr"}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
