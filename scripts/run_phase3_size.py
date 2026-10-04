"""Phase 3: does propagation depend on the size of the news? (pre-registered)

MVP identification; the expectations-shock and premium-shock parts of each day's
innovation are split into ordinary and large days (beyond k standard
deviations) and the large parts may propagate differently. Writes to
``reports/structural_propagation/phase3/``.

Usage:  python scripts/run_phase3_size.py [--data-dir DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.data import load_us_panel
from giltcurve.propagation.identification import VARIABLES, random_rotations, sample_identified_set
from giltcurve.propagation.oos import pseudo_oos_size, summarise_size
from giltcurve.propagation.predictive import (
    EXPECTATIONS_IDX, HORIZONS, OUTCOMES, curve_controls, forward_changes, impact_on,
    large_part, own_moves, premium_contribution, size_split_test,
)

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261007


def components(eps, b, tp_group, eh_group):
    return eps[:, tp_group] @ b[tp_group], eps[:, eh_group] @ b[eh_group]


def in_sample(panel, post, ident, k, n_placebo, rng, label):
    p = 1
    Yd, Xd = design(panel[list(VARIABLES)].to_numpy(), p)
    U = post.residuals()
    eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(len(ident.B))]
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = forward_changes(panel)
    Brand = random_rotations(post.sigma_mean, n_placebo, rng)
    groups = [rng.permutation(4) for _ in range(n_placebo)]
    eps_rand = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    tp_idx = [i for i in range(4) if i not in EXPECTATIONS_IDX]
    rows = []
    for o in OUTCOMES:
        x = own[o].to_numpy()
        b_all = impact_on(ident.B, o)
        b_rand = impact_on(Brand, o)
        comp = [components(eps[j], b_all[j], tp_idx, EXPECTATIONS_IDX) for j in range(len(eps))]
        comp_r = [components(eps_rand[i], b_rand[i], list(groups[i][:2]), list(groups[i][2:]))
                  for i in range(n_placebo)]
        for h in HORIZONS:
            r = fwd[(o, h)].iloc[p:].to_numpy()
            res = pd.DataFrame([size_split_test(r, x, c_tp, large_part(c_eh, c_eh.std(), k),
                                                large_part(c_tp, c_tp.std(), k), Z, h)
                                for c_tp, c_eh in comp])
            pl = np.array([size_split_test(r, x, c_tp, large_part(c_eh, c_eh.std(), k),
                                           large_part(c_tp, c_tp.std(), k), Z, h,
                                           with_se=False)["incr_r2"] for c_tp, c_eh in comp_r])
            p90 = float(np.quantile(pl, 0.9))
            rows.append({
                "set": label, "k": k, "outcome": o, "h": h,
                "lambda_eh_med": res["lambda_eh"].median(),
                "lambda_eh_p05": res["lambda_eh"].quantile(0.05),
                "lambda_eh_p95": res["lambda_eh"].quantile(0.95),
                "share_t_eh_gt_1.96": float((res["t_eh"] > 1.96).mean()),
                "lambda_tp_med": res["lambda_tp"].median(),
                "share_t_tp_lt_-1.96": float((res["t_tp"] < -1.96).mean()),
                "incr_r2_med": res["incr_r2"].median(), "placebo_incr_r2_p90": p90,
                "share_draws_beat_placebo_p90": float((res["incr_r2"] > p90).mean()),
                "large_eh_days_med": float(res["large_eh_days"].median()),
                "large_tp_days_med": float(res["large_tp_days"].median())})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation" / "phase3"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_draws, n_placebo, n_oos = (40, 40, 10) if args.quick else (1000, 1000, 200)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    panel = load_us_panel(args.data_dir)                     # sealed: ends 2025-12-31
    post = fit_bvar(panel[list(VARIABLES)].to_numpy(), p=1, lam=0.2)
    ident = sample_identified_set(post.draw, n_draws, rng)
    tabs = [in_sample(panel, post, ident, 2.0, n_placebo, rng, "baseline k=2")]
    n_rob = max(n_draws // 3, 30)
    sub = type(ident)(B=ident.B[:n_rob], Sigma=ident.Sigma[:n_rob], A=ident.A[:n_rob],
                      candidates=ident.candidates, accepted=ident.accepted)
    for k in (1.5, 2.5):
        tabs.append(in_sample(panel, post, sub, k, n_rob, rng, f"robustness k={k}"))
    pd.concat(tabs).to_csv(out / "test_size.csv", index=False)
    fc = pseudo_oos_size(panel, n_draws=n_oos)
    fc.to_csv(out / "oos_forecasts_size.csv.gz", index=False)
    summarise_size(fc).to_csv(out / "oos_summary_size.csv", index=False)
    summary = {"seed": SEED, "n_draws": n_draws, "n_placebo": n_placebo, "n_oos_draws": n_oos,
               "runtime_seconds": round(time.time() - t0, 1)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
