"""Phase 2: regime-dependent identification and propagation (pre-registered).

Same data, VAR and sign restrictions as the MVP; the innovation covariance and
hence the impact matrix differ between the real-time stock-bond regimes. Writes
to ``reports/structural_propagation/phase2/``.

Usage:  python scripts/run_phase2_regimes.py [--data-dir DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import fit_bvar
from giltcurve.propagation.data import load_us_panel
from giltcurve.propagation.identification import SHOCKS, VARIABLES
from giltcurve.propagation.oos import pseudo_oos_regime, summarise_regime
from giltcurve.propagation.predictive import (
    HORIZONS, OUTCOMES, curve_controls, forward_changes, own_moves, reduced_form_test,
    structural_split_test,
)
from giltcurve.propagation.regimes import (
    COMOVE, HEDGE, placebo_contributions, regime_identified_sets, regime_indicator,
    regime_premium_contribution,
)

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261006
NAME = {HEDGE: "hedge", COMOVE: "co-movement"}


def in_sample(panel, window, n_draws, n_placebo, rng, label):
    p = 1
    post = fit_bvar(panel[list(VARIABLES)].to_numpy(), p=p, lam=0.2)
    U = post.residuals()
    reg = regime_indicator(panel, window).iloc[p:].to_numpy()
    sets = regime_identified_sets(U, reg, n_draws, rng)
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = forward_changes(panel)
    shares, a_rows, c_rows = [], [], []
    for R, ident in sets.items():
        sh = ident.variance_shares()
        for i, v in enumerate(VARIABLES):
            for k, s in enumerate(SHOCKS):
                shares.append({"set": label, "regime": NAME[R], "variable": v, "shock": s,
                               "median": float(np.median(sh[:, i, k])),
                               "p05": float(np.quantile(sh[:, i, k], 0.05)),
                               "p95": float(np.quantile(sh[:, i, k], 0.95))})
    for o in OUTCOMES:
        x = own[o].to_numpy()
        contrib = [regime_premium_contribution(U, reg, sets, j, o) for j in range(n_draws)]
        plac = {R: placebo_contributions(U, sets[R].Sigma.mean(axis=0), o, n_placebo, rng)
                for R in sets}
        for h in HORIZONS:
            r_all = fwd[(o, h)].iloc[p:].to_numpy()
            for R in sets:
                r = np.where(reg == R, r_all, np.nan)
                a = reduced_form_test(r, x, U, Z, o, h)
                a_rows.append({"set": label, "regime": NAME[R], **a})
                cs = pd.DataFrame([structural_split_test(r, x, contrib[j], Z, h)
                                   for j in range(n_draws)])
                pl = np.array([structural_split_test(r, x, c, Z, h, with_se=False)["incr_r2"]
                               for c in plac[R]])
                p90 = float(np.quantile(pl, 0.9))
                c_rows.append({
                    "set": label, "regime": NAME[R], "outcome": o, "h": h,
                    "days": int(np.isfinite(r).sum()),
                    "theta_eh_med": cs["theta_eh"].median(), "theta_tp_med": cs["theta_tp"].median(),
                    "kappa_med": cs["kappa"].median(), "kappa_p05": cs["kappa"].quantile(0.05),
                    "kappa_p95": cs["kappa"].quantile(0.95),
                    "share_kappa_neg": float((cs["kappa"] < 0).mean()),
                    "t_kappa_med": cs["t_kappa"].median(),
                    "incr_r2_med": cs["incr_r2"].median(), "placebo_incr_r2_p90": p90,
                    "share_draws_beat_placebo_p90": float((cs["incr_r2"] > p90).mean())})
    return pd.DataFrame(shares), pd.DataFrame(a_rows), pd.DataFrame(c_rows), reg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation" / "phase2"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_draws, n_placebo, n_oos = (40, 40, 10) if args.quick else (1000, 1000, 200)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    panel = load_us_panel(args.data_dir)                     # sealed: ends 2025-12-31
    summary = {"seed": SEED, "n_draws": n_draws, "n_placebo": n_placebo, "n_oos_draws": n_oos}

    reg250 = regime_indicator(panel, 250)
    by = pd.DataFrame({"regime": reg250, "year": panel.index.year}).dropna()
    summary["share_hedge_days"] = {
        f"{a}-{b}": float((by[(by.year >= a) & (by.year <= b)]["regime"] == HEDGE).mean())
        for a, b in [(1984, 1999), (2000, 2019), (2020, 2025), (2022, 2023)]}
    summary["corr_dy10_req_by_regime"] = {
        NAME[R]: float(panel.loc[reg250 == R, ["dy10", "req"]].corr().iloc[0, 1])
        for R in (HEDGE, COMOVE)}

    sh, a, c, _ = in_sample(panel, 250, n_draws, n_placebo, rng, "window=250")
    n_rob = max(n_draws // 3, 30)
    sh2, a2, c2, _ = in_sample(panel, 125, n_rob, n_rob, rng, "window=125")
    pd.concat([sh, sh2]).to_csv(out / "variance_shares_by_regime.csv", index=False)
    pd.concat([a, a2]).to_csv(out / "test_a_by_regime.csv", index=False)
    pd.concat([c, c2]).to_csv(out / "test_c_by_regime.csv", index=False)

    fc = pseudo_oos_regime(panel, reg250, n_draws=n_oos)
    fc.to_csv(out / "oos_forecasts_regime.csv.gz", index=False)
    oos = summarise_regime(fc)
    oos.to_csv(out / "oos_summary_regime.csv", index=False)
    summary["runtime_seconds"] = round(time.time() - t0, 1)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
