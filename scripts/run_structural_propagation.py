"""Structural origins and propagation of US Treasury yield moves: the MVP run.

Estimates the pre-registered daily sign-restricted BVAR on 1983-2025 (2026 is
sealed), reproduces the Cieslak-Pang decomposition, runs the three propagation
tests with their placebo, the robustness variants and the real-time pseudo
out-of-sample exercise, and writes tables, a JSON summary and the frozen
end-2025 model (with its SHA-256) to ``reports/structural_propagation/``.

Usage:  python scripts/run_structural_propagation.py [--data-dir DIR] [--quick]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.data import load_us_panel
from giltcurve.propagation.identification import (
    SHOCKS, VARIABLES, fixed_sigma, random_rotations, sample_identified_set,
    without_stock_bond_covariance,
)
from giltcurve.propagation.oos import pseudo_oos, summarise
from giltcurve.propagation.predictive import (
    HORIZONS, OUTCOMES, curve_controls, forward_changes, impact_on, own_moves,
    premium_contribution, propagation_ratio_test, reduced_form_test,
    structural_split_test,
)

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261004


def identify(panel, p, lam, n_draws, rng):
    Y = panel[list(VARIABLES)].to_numpy()
    post = fit_bvar(Y, p=p, lam=lam)
    ident = sample_identified_set(post.draw, n_draws, rng)
    return post, ident


def shares_table(ident, label):
    sh = ident.variance_shares()
    rows = []
    for i, v in enumerate(VARIABLES):
        for k, s in enumerate(SHOCKS):
            x = sh[:, i, k]
            rows.append({"set": label, "variable": v, "shock": s, "median": np.median(x),
                         "p05": np.quantile(x, 0.05), "p95": np.quantile(x, 0.95)})
    return pd.DataFrame(rows)


def impact_table(ident, label):
    rows = []
    for i, v in enumerate(VARIABLES):
        for k, s in enumerate(SHOCKS):
            x = ident.B[:, i, k]
            rows.append({"set": label, "variable": v, "shock": s, "median": np.median(x),
                         "p05": np.quantile(x, 0.05), "p95": np.quantile(x, 0.95)})
    return pd.DataFrame(rows)


def draw_shocks(post, ident, panel, p):
    Yd, Xd = design(panel[list(VARIABLES)].to_numpy(), p)
    return [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(len(ident.B))]


def in_sample_tests(panel, post, ident, eps, p, rng, n_placebo, label="baseline"):
    """Tests A, B, C and the placebo on the estimation sample."""
    U = post.residuals()
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = forward_changes(panel)
    Sbar = post.sigma_mean
    Brand = random_rotations(Sbar, n_placebo, rng)
    groups = [rng.choice(4, size=2, replace=False) for _ in range(n_placebo)]
    eps_rand = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    a_rows, b_rows, c_rows, pl_rows = [], [], [], []
    for o in OUTCOMES:
        x_own = own[o].to_numpy()
        b_all = impact_on(ident.B, o)
        b_rand = impact_on(Brand, o)
        for h in HORIZONS:
            r = fwd[(o, h)].iloc[p:].to_numpy()
            a = reduced_form_test(r, x_own, U, Z, o, h)
            a_rows.append({"set": label, **a})
            for j in range(len(eps)):
                bt = propagation_ratio_test(r, eps[j], b_all[j], Z, h)
                b_rows.append({"set": label, "outcome": o, "h": h, "draw": j,
                               **{f"pi_{s}": bt["pi"][k] for k, s in enumerate(SHOCKS)},
                               **{f"gamma_{s}": bt["gamma"][k] for k, s in enumerate(SHOCKS)},
                               **{f"impact_{s}": b_all[j][k] for k, s in enumerate(SHOCKS)},
                               "p_equal_pi": bt["p_equal_pi"]})
                ct = structural_split_test(r, x_own, premium_contribution(eps[j], b_all[j]), Z, h)
                c_rows.append({"set": label, "outcome": o, "h": h, "draw": j, **ct})
            for i in range(n_placebo):
                contrib = premium_contribution(eps_rand[i], b_rand[i], group=list(groups[i]))
                ct = structural_split_test(r, x_own, contrib, Z, h, with_se=False)
                pl_rows.append({"set": label, "outcome": o, "h": h, "draw": i,
                                "incr_r2": ct["incr_r2"], "kappa": ct["kappa"]})
    return (pd.DataFrame(a_rows), pd.DataFrame(b_rows), pd.DataFrame(c_rows),
            pd.DataFrame(pl_rows))


def summarise_b(bdf):
    rows = []
    for (s, o, h), g in bdf.groupby(["set", "outcome", "h"], sort=False):
        row = {"set": s, "outcome": o, "h": h,
               "share_draws_reject_equal_pi": float((g["p_equal_pi"] < 0.05).mean())}
        for k in SHOCKS:
            x = g[f"pi_{k}"]
            row[f"pi_{k}_med"] = x.median()
            row[f"pi_{k}_p05"] = x.quantile(0.05)
            row[f"pi_{k}_p95"] = x.quantile(0.95)
        # The ratio is unstable where a shock barely moves the outcome on impact,
        # so the drift itself (bp per one-standard-deviation shock) is reported too.
        for k in SHOCKS:
            for stat in ("gamma", "impact"):
                x = g[f"{stat}_{k}"]
                row[f"{stat}_{k}_med"] = x.median()
                row[f"{stat}_{k}_p05"] = x.quantile(0.05)
                row[f"{stat}_{k}_p95"] = x.quantile(0.95)
        ranks = g[[f"pi_{k}" for k in SHOCKS]].to_numpy().argsort(axis=1)
        keys = ["".join(map(str, rk)) for rk in ranks]
        modal = pd.Series(keys).mode().iloc[0]
        row["modal_ranking_low_to_high"] = ">".join(SHOCKS[int(c)] for c in modal[::-1])
        row["share_draws_modal_ranking"] = float(np.mean([k == modal for k in keys]))
        rows.append(row)
    return pd.DataFrame(rows)


def summarise_c(cdf, pldf):
    rows = []
    for (s, o, h), g in cdf.groupby(["set", "outcome", "h"], sort=False):
        pl = pldf[(pldf["set"] == s) & (pldf["outcome"] == o) & (pldf["h"] == h)]["incr_r2"]
        p90 = float(pl.quantile(0.90))
        rows.append({"set": s, "outcome": o, "h": h,
                     "theta_eh_med": g["theta_eh"].median(), "theta_tp_med": g["theta_tp"].median(),
                     "kappa_med": g["kappa"].median(), "kappa_p05": g["kappa"].quantile(0.05),
                     "kappa_p95": g["kappa"].quantile(0.95), "t_kappa_med": g["t_kappa"].median(),
                     "share_draws_|t|>1.96": float((g["t_kappa"].abs() > 1.96).mean()),
                     "incr_r2_med": g["incr_r2"].median(), "placebo_incr_r2_med": float(pl.median()),
                     "placebo_incr_r2_p90": p90,
                     "share_draws_beat_placebo_p90": float((g["incr_r2"] > p90).mean())})
    return pd.DataFrame(rows)


def episode_decomposition(panel, ident, eps, p, windows):
    """Cumulative 10y change by shock in named windows, median-target draw."""
    j = ident.median_target()
    b10 = ident.B[j][2]
    dates = panel.index[p:]
    contrib = pd.DataFrame(eps[j] * b10, index=dates, columns=SHOCKS)
    rows = []
    for name, (d0, d1) in windows.items():
        w = contrib.loc[d0:d1]
        actual = panel["dy10"].loc[d0:d1].sum()
        rows.append({"episode": name, "start": d0, "end": d1, "actual_bp": actual,
                     **{f"{s}_bp": w[s].sum() for s in SHOCKS},
                     "predictable_bp": actual - w.sum(axis=1).sum()})
    return pd.DataFrame(rows), contrib


EPISODES = {
    "Taper tantrum (May-Sep 2013)": ("2013-05-01", "2013-09-05"),
    "Hiking cycle (2022)": ("2022-01-03", "2022-10-21"),
    "Post-first-cut selloff (Sep 2024-Jan 2025)": ("2024-09-16", "2025-01-13"),
    "Covid flight to safety (Feb-Mar 2020)": ("2020-02-19", "2020-03-09"),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation"))
    ap.add_argument("--quick", action="store_true", help="few draws, for smoke runs")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_draws, n_placebo, n_oos = (60, 60, 20) if args.quick else (1000, 1000, 200)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    summary = {"seed": SEED, "n_draws": n_draws, "n_placebo": n_placebo, "n_oos_draws": n_oos}

    panel = load_us_panel(args.data_dir)                       # sealed: ends 2025-12-31
    summary["sample"] = [str(panel.index.min().date()), str(panel.index.max().date()), len(panel)]
    summary["daily_sd_bp"] = panel[["dy2", "dy5", "dy10"]].std().round(3).to_dict()
    lv10 = panel["y10"] * 100
    summary["sd_20d_change_10y_bp"] = float((lv10.shift(-20) - lv10).std())

    # 1. Replication on Cieslak-Pang's sample.
    rep_post, rep_ident = identify(panel.loc[:"2017-12-31"], 1, 0.2, n_draws, rng)
    shares = [shares_table(rep_ident, "1983-2017")]
    sh = rep_ident.variance_shares()
    summary["replication_1983_2017"] = {
        "share_2y_growth_plus_monetary": float(np.median(sh[:, 0, 0] + sh[:, 0, 1])),
        "share_equity_premia": float(np.median(sh[:, 3, 2] + sh[:, 3, 3])),
        "share_equity_growth": float(np.median(sh[:, 3, 0])),
        "share_equity_monetary": float(np.median(sh[:, 3, 1])),
        "monetary_impact_2y_bp": float(np.median(rep_ident.B[:, 0, 1])),
        "acceptance_rate": rep_ident.acceptance_rate}

    # 2. Baseline, full sample, and the learned-from-data benchmark.
    post, ident = identify(panel, 1, 0.2, n_draws, rng)
    shares.append(shares_table(ident, "1983-2025"))
    bench = sample_identified_set(fixed_sigma(without_stock_bond_covariance(post.sigma_mean)),
                                  n_draws, rng)
    shares.append(shares_table(bench, "benchmark: no stock-bond covariance"))
    impacts = pd.concat([impact_table(ident, "1983-2025"), impact_table(bench, "benchmark")])
    summary["acceptance_rate_baseline"] = ident.acceptance_rate
    summary["acceptance_rate_benchmark"] = bench.acceptance_rate
    eps = draw_shocks(post, ident, panel, 1)

    # 3. Propagation tests and placebo.
    a, b, c, pl = in_sample_tests(panel, post, ident, eps, 1, rng, n_placebo)
    ep, contrib = episode_decomposition(panel, ident, eps, 1, EPISODES)

    # 4. Robustness: lags and prior tightness (fewer draws).
    n_rob = max(n_draws // 3, 30)
    rob_a, rob_c, rob_pl = [], [], []
    for label, p, lam in [("p=5", 5, 0.2), ("lambda=0.05", 1, 0.05), ("lambda=1", 1, 1.0)]:
        rpost, rident = identify(panel, p, lam, n_rob, rng)
        shares.append(shares_table(rident, label))
        reps = draw_shocks(rpost, rident, panel, p)
        ra, _, rc, rpl = in_sample_tests(panel, rpost, rident, reps, p, rng, n_rob, label=label)
        rob_a.append(ra), rob_c.append(rc), rob_pl.append(rpl)

    # 5. Real-time pseudo out-of-sample.
    fc = pseudo_oos(panel, n_draws=n_oos, seed=SEED + 1)
    oos = summarise(fc)

    # 6. Freeze the end-2025 model for the holdout protocol.
    model_path = out / "model_end2025.npz"
    np.savez_compressed(model_path, B=ident.B, Sigma=ident.Sigma, A=ident.A,
                        A_hat=post.A_hat, variables=np.array(VARIABLES), shocks=np.array(SHOCKS))
    summary["frozen_model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()

    # 7. Write everything.
    pd.concat(shares).to_csv(out / "variance_shares.csv", index=False)
    impacts.to_csv(out / "impact_responses.csv", index=False)
    pd.concat([a] + rob_a).to_csv(out / "test_a_reduced_form.csv", index=False)
    b.to_csv(out / "test_b_draws.csv.gz", index=False)
    summarise_b(b).to_csv(out / "test_b_propagation_ratios.csv", index=False)
    summarise_c(pd.concat([c] + rob_c), pd.concat([pl] + rob_pl)).to_csv(
        out / "test_c_structural_split.csv", index=False)
    pl.to_csv(out / "test_c_placebo.csv.gz", index=False)
    c.to_csv(out / "test_c_draws.csv.gz", index=False)
    ep.to_csv(out / "episodes.csv", index=False)
    contrib.to_csv(out / "daily_10y_contributions_median_target.csv.gz")
    fc.to_csv(out / "oos_forecasts.csv.gz", index=False)
    oos.to_csv(out / "oos_summary.csv", index=False)
    summary["runtime_seconds"] = round(time.time() - t0, 1)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
