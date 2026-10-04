"""Exploratory checks on the frozen end-2025 model (NOT pre-registered).

1. Closing-time mismatch. Treasury closing marks are typically taken in the
   mid-afternoon, before the 4pm equity close, so equity news from the last
   part of the day can reach bond yields only on the next day. That would make
   today's equity innovation "predict" tomorrow's yield change mechanically.
   The diagnostic regresses the next-day 10y change on today's equity return,
   by decade.
2. Skip-the-first-day outcomes. Re-run Test A and Test C on r_{t+1,t+h},
   which removes any one-day timing effect, with the same placebo design.
3. The learned-from-data benchmark within each stock-bond correlation regime
   (before and after 2000).
4. Test A on the Treasury's constant-maturity yields instead of the fitted
   zero-coupon curve.
5. (``--phase2``) The Phase 2 real-time comparison without curve-state controls.
6. (``--phase3``) The Phase 3 size test with "large" measured against trailing
   volatility rather than the full sample.

Results go to ``reports/structural_propagation/exploratory_*.csv``.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.data import (
    build_panel, load_french_market_return, load_us_panel, seal,
)
from giltcurve.propagation.identification import (
    SHOCKS, VARIABLES, fixed_sigma, sample_identified_set, without_stock_bond_covariance,
)
from giltcurve.propagation.predictive import (
    curve_controls, forward_changes, impact_on, ols_nw, outcome_levels, own_moves,
    premium_contribution, reduced_form_test, structural_split_test,
)

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261005


def lead_lag(panel: pd.DataFrame) -> pd.DataFrame:
    """Next-day 10y change on today's equity return and 10y change, by decade."""
    nxt = panel["dy10"].shift(-1)
    rows = []
    for label, (a, b) in {"1983-1989": ("1983", "1989"), "1990-1999": ("1990", "1999"),
                          "2000-2009": ("2000", "2009"), "2010-2019": ("2010", "2019"),
                          "2020-2025": ("2020", "2025"), "1983-2025": ("1983", "2025")}.items():
        s = panel.loc[a:b]
        y = nxt.loc[a:b].to_numpy()
        X = np.column_stack([np.ones(len(s)), s["req"], s["dy10"]])
        m = np.isfinite(y)
        beta, V, r2 = ols_nw(y[m], X[m], 1)
        rows.append({"period": label, "n": int(m.sum()),
                     "bp_next_day_per_1pct_equity": beta[1], "t": beta[1] / np.sqrt(V[1, 1]),
                     "own_lag_coef": beta[2], "own_lag_t": beta[2] / np.sqrt(V[2, 2]), "r2": r2})
    return pd.DataFrame(rows)


def skip_day(panel, model, rng, n_placebo=1000, horizons=(2, 5, 10, 20)):
    p = 1
    Yd, Xd = design(panel[list(VARIABLES)].to_numpy(), p)
    U = Yd - Xd @ model["A_hat"]
    lv = outcome_levels(panel).iloc[p:]
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    B, A = model["B"], model["A"]
    eps = [np.linalg.solve(B[j], (Yd - Xd @ A[j]).T).T for j in range(len(B))]
    Sbar = model["Sigma"].mean(axis=0)
    L = np.linalg.cholesky(Sbar)
    z = rng.standard_normal((n_placebo, 4, 4))
    q, r = np.linalg.qr(z)
    Brand = L[None] @ (q * np.sign(np.diagonal(r, axis1=1, axis2=2))[:, None, :])
    groups = [rng.choice(4, size=2, replace=False) for _ in range(n_placebo)]
    eps_rand = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    a_rows, c_rows = [], []
    for o in ("y10", "y2", "slope"):
        x = own[o].to_numpy()
        b_all = impact_on(B, o)
        b_rand = impact_on(Brand, o)
        for h in horizons:
            r_skip = (lv[o].shift(-h) - lv[o].shift(-1)).to_numpy()
            a = reduced_form_test(r_skip, x, U, Z, o, h)
            a_rows.append({"design": "skip first day", **a})
            cs = [structural_split_test(r_skip, x, premium_contribution(eps[j], b_all[j]), Z, h)
                  for j in range(len(B))]
            pl = np.array([structural_split_test(
                r_skip, x, premium_contribution(eps_rand[i], b_rand[i], group=list(groups[i])),
                Z, h, with_se=False)["incr_r2"] for i in range(n_placebo)])
            cdf = pd.DataFrame(cs)
            p90 = float(np.quantile(pl, 0.9))
            c_rows.append({"design": "skip first day", "outcome": o, "h": h,
                           "theta_eh_med": cdf["theta_eh"].median(),
                           "theta_tp_med": cdf["theta_tp"].median(),
                           "kappa_med": cdf["kappa"].median(),
                           "kappa_p05": cdf["kappa"].quantile(0.05),
                           "kappa_p95": cdf["kappa"].quantile(0.95),
                           "t_kappa_med": cdf["t_kappa"].median(),
                           "share_draws_|t|>1.96": float((cdf["t_kappa"].abs() > 1.96).mean()),
                           "incr_r2_med": cdf["incr_r2"].median(),
                           "placebo_incr_r2_p90": p90,
                           "share_draws_beat_placebo_p90": float((cdf["incr_r2"] > p90).mean())})
    return pd.DataFrame(a_rows), pd.DataFrame(c_rows)


def regime_benchmark(panel, rng, n_draws=500):
    """Variance shares with and without stock-bond covariance, by stock-bond regime.

    The full-sample stock-bond covariance is close to zero because the sign of
    the correlation flipped around 2000; the benchmark comparison is only
    informative within a regime.
    """
    rows = []
    for label, (a, b) in {"1983-1999": ("1983", "1999"), "2000-2025": ("2000", "2025")}.items():
        sub = panel.loc[a:b]
        post = fit_bvar(sub[list(VARIABLES)].to_numpy(), p=1, lam=0.2)
        ident = sample_identified_set(post.draw, n_draws, rng)
        bench = sample_identified_set(
            fixed_sigma(without_stock_bond_covariance(post.sigma_mean)), n_draws, rng)
        corr = sub[["dy2", "dy10", "req"]].corr()
        for name, s in (("estimated", ident), ("no stock-bond covariance", bench)):
            sh = np.median(s.variance_shares(), axis=0)
            for i, v in enumerate(VARIABLES):
                rows.append({"period": label, "set": name, "variable": v,
                             "corr_dy10_req": corr.loc["dy10", "req"],
                             **{k: sh[i, j] for j, k in enumerate(SHOCKS)}})
    return pd.DataFrame(rows)


def _fred(data_dir, sid):
    df = pd.read_csv(Path(data_dir) / f"fred_{sid}.csv", na_values=["."])
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    return seal(df.set_index("observation_date")[sid].astype(float))


def cmt_robustness(data_dir, horizons=(1, 5, 10, 20)):
    """Test A on Treasury constant-maturity par yields instead of GSW zero yields.

    GSW yields are a smoothed Svensson fit; if maturity-specific moves reverse
    only because fitting errors mean-revert, the result should weaken on the
    Treasury's own constant-maturity series.
    """
    ylds = pd.concat({f"y{n}": _fred(data_dir, f"DGS{n}") for n in (2, 5, 10)}, axis=1).dropna()
    panel = build_panel(ylds, load_french_market_return(data_dir))
    post = fit_bvar(panel[list(VARIABLES)].to_numpy(), p=1, lam=0.2)
    U = post.residuals()
    own = own_moves(panel).iloc[1:]
    Z = curve_controls(panel).iloc[1:].to_numpy()
    fwd = forward_changes(panel, horizons)
    rows = []
    for o in ("y10", "y2", "slope"):
        for h in horizons:
            r = fwd[(o, h)].iloc[1:].to_numpy()
            rows.append({"curve": "Treasury constant maturity",
                         **reduced_form_test(r, own[o].to_numpy(), U, Z, o, h)})
    return pd.DataFrame(rows)


def phase2_without_curve_state(data_dir, out_dir, n_draws=200):
    """Exploratory: the Phase 2 real-time comparison without curve-state controls.

    The pre-registered benchmark includes curve-state variables that damage
    real-time forecasts; this asks whether the regime-specific structural split
    has any value against a no-change forecast once they are dropped.
    """
    from giltcurve.propagation.oos import pseudo_oos_regime, summarise_regime
    from giltcurve.propagation.regimes import regime_indicator
    panel = load_us_panel(data_dir)
    fc = pseudo_oos_regime(panel, regime_indicator(panel, 250), n_draws=n_draws,
                           curve_state=False)
    s = summarise_regime(fc)
    s.to_csv(Path(out_dir) / "exploratory_phase2_no_curve_state.csv", index=False)
    return s


def size_relative_to_trailing_vol(panel, model, k=2.0, window=250, horizons=(1, 5, 10, 20)):
    """Exploratory: Phase 3 with "large" defined relative to trailing volatility.

    A full-sample threshold makes large days cluster in the volatile 1980s and in
    crises; measuring size against the previous ``window`` days' standard deviation
    separates the size of the news from the volatility of the era.
    """
    from giltcurve.propagation.predictive import EXPECTATIONS_IDX, size_split_test
    p = 1
    Yd, Xd = design(panel[list(VARIABLES)].to_numpy(), p)
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    lv = outcome_levels(panel).iloc[p:]
    B, A = model["B"], model["A"]
    tp_idx = [i for i in range(4) if i not in EXPECTATIONS_IDX]
    rows = []
    for o in ("y10", "y2", "slope"):
        x = own[o].to_numpy()
        b_all = impact_on(B, o)
        res = {h: [] for h in horizons}
        for j in range(len(B)):
            eps = np.linalg.solve(B[j], (Yd - Xd @ A[j]).T).T
            c_tp = eps[:, tp_idx] @ b_all[j][tp_idx]
            c_eh = eps[:, EXPECTATIONS_IDX] @ b_all[j][EXPECTATIONS_IDX]
            sd_eh = pd.Series(c_eh).rolling(window).std().shift(1).to_numpy()
            sd_tp = pd.Series(c_tp).rolling(window).std().shift(1).to_numpy()
            big_eh = np.where(np.abs(c_eh) > k * sd_eh, c_eh, 0.0)
            big_tp = np.where(np.abs(c_tp) > k * sd_tp, c_tp, 0.0)
            big_eh[np.isnan(sd_eh)] = np.nan
            big_tp[np.isnan(sd_tp)] = np.nan
            for h in horizons:
                r = (lv[o].shift(-h) - lv[o]).to_numpy()
                res[h].append(size_split_test(r, x, c_tp, big_eh, big_tp, Z, h))
        for h in horizons:
            d = pd.DataFrame(res[h])
            rows.append({"threshold": f"{k} x trailing {window}-day s.d.", "outcome": o, "h": h,
                         "lambda_eh_med": d["lambda_eh"].median(),
                         "lambda_eh_p05": d["lambda_eh"].quantile(0.05),
                         "lambda_eh_p95": d["lambda_eh"].quantile(0.95),
                         "share_t_eh_gt_1.96": float((d["t_eh"] > 1.96).mean()),
                         "share_t_eh_lt_-1.96": float((d["t_eh"] < -1.96).mean()),
                         "large_eh_days_med": float(d["large_eh_days"].median())})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation"))
    ap.add_argument("--phase2", action="store_true",
                    help="only the Phase 2 comparison without curve-state controls")
    ap.add_argument("--phase3", action="store_true",
                    help="only the Phase 3 size test with a trailing-volatility threshold")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    if args.phase2:
        print(phase2_without_curve_state(args.data_dir, out / "phase2").round(4).to_string())
        return 0
    if args.phase3:
        s = size_relative_to_trailing_vol(load_us_panel(args.data_dir),
                                          dict(np.load(out / "model_end2025.npz")))
        (out / "phase3").mkdir(parents=True, exist_ok=True)
        s.to_csv(out / "phase3" / "exploratory_size_trailing_vol.csv", index=False)
        print(s.round(4).to_string())
        return 0
    panel = load_us_panel(args.data_dir)
    model = dict(np.load(out / "model_end2025.npz"))
    rng = np.random.default_rng(SEED)
    pd.set_option("display.width", 250)
    ll = lead_lag(panel)
    ll.to_csv(out / "exploratory_lead_lag.csv", index=False)
    a, c = skip_day(panel, model, rng)
    a.to_csv(out / "exploratory_skip_day_test_a.csv", index=False)
    c.to_csv(out / "exploratory_skip_day_test_c.csv", index=False)
    rb = regime_benchmark(panel, rng)
    rb.to_csv(out / "exploratory_regime_benchmark.csv", index=False)
    cmt = cmt_robustness(args.data_dir)
    cmt.to_csv(out / "exploratory_cmt_test_a.csv", index=False)
    for t in (ll, a, c, rb, cmt):
        print(t.round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

