"""Exploratory: the closing-time problem in the cross-Atlantic model (deviation log, doc 08).

Euro-area prices are recorded at the European close, about five and a half hours before
US prices. US news from the New York afternoon therefore reaches Bund yields and
European equities only the next day. This script measures the effect and re-runs the
cross-Atlantic tests in forms that are immune to it:

1. lead-lag regressions of next-day changes on today's moves in the other market;
2. variance shares by origin at one, two and five days (the multi-day shares count the
   next-day catch-up, which the one-day shares miss);
3. the propagation tests on changes that start at the next close (skip the first day);
4. the real-time evaluation on the same skip-the-first-day outcomes;
5. the variance shares re-estimated on non-overlapping 2-day and 5-day changes.

Uses the frozen end-2025 model; writes ``reports/structural_propagation/brandt/exploratory_*``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation import brandt
from giltcurve.propagation.bvar import design
from giltcurve.propagation.identification import IdentifiedSet, random_rotations
from giltcurve.propagation.oos import summarise
from giltcurve.propagation.predictive import ols_nw, reduced_form_test_generic

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261009
P = brandt.LAGS
SKIP_HORIZONS = (2, 5, 10, 20)


def lead_lag(panel):
    rows = []
    for target, label_t in (("d_ea10", "Bund 10y, next day"), ("d_us10", "Treasury 10y, next day")):
        nxt = panel[target].shift(-1)
        for col, label_c in (("d_us10", "Treasury 10y today"), ("r_eq_us", "S&P 500 today"),
                             ("d_ea10", "Bund 10y today"), ("r_eq_ea", "euro equity today")):
            m = nxt.notna().to_numpy()
            X = np.column_stack([np.ones(m.sum()), panel[col].to_numpy()[m]])
            b, V, r2 = ols_nw(nxt.to_numpy()[m], X, 1)
            rows.append({"outcome": label_t, "regressor": label_c, "coef": b[1],
                         "t": b[1] / np.sqrt(V[1, 1]), "r2": r2})
    return pd.DataFrame(rows)


def skip_day_tests(panel, model, rng, n_placebo=1000):
    Yd, Xd = design(panel[list(brandt.VARIABLES)].to_numpy(), P)
    U = Yd - Xd @ model["A_hat"]
    B, A = model["B"], model["A"]
    eps = [np.linalg.solve(B[j], (Yd - Xd @ A[j]).T).T for j in range(len(B))]
    own = brandt.own_moves(panel).iloc[P:]
    Z = brandt.controls(panel).iloc[P:].to_numpy()
    fwd = brandt.forward_changes(panel, SKIP_HORIZONS, skip=1)
    Brand = random_rotations(model["Sigma"].mean(axis=0), n_placebo, rng)
    perms = [rng.permutation(5) for _ in range(n_placebo)]
    eps_r = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    a_rows, c_rows = [], []
    for o in brandt.OUTCOMES:
        x = own[o].to_numpy()
        b_all = brandt.impact_on(B, o)
        b_r = brandt.impact_on(Brand, o)
        parts = [brandt.origin_contributions(eps[j], b_all[j], o) for j in range(len(B))]
        parts_r = [brandt.origin_contributions(eps_r[i], b_r[i], o, groups=(
            list(perms[i][:2]), list(perms[i][2:4]), [perms[i][4]])) for i in range(n_placebo)]
        for h in SKIP_HORIZONS:
            r = fwd[(o, h)].iloc[P:].to_numpy()
            a_rows.append({"design": "skip first day", "outcome": o, "h": h,
                           **reduced_form_test_generic(r, x, brandt.other_innovations(U, o), Z, h)})
            cs = pd.DataFrame([brandt.origin_split_test(r, x, cf, cg, Z, h) for cf, cg in parts])
            pl = np.array([brandt.origin_split_test(r, x, cf, cg, Z, h, with_se=False)["incr_r2"]
                           for cf, cg in parts_r])
            p90 = float(np.quantile(pl, 0.9))
            c_rows.append({"design": "skip first day", "outcome": o, "h": h,
                           "kappa_foreign_med": cs["kappa_foreign"].median(),
                           "kappa_foreign_p05": cs["kappa_foreign"].quantile(0.05),
                           "kappa_foreign_p95": cs["kappa_foreign"].quantile(0.95),
                           "kappa_global_med": cs["kappa_global"].median(),
                           "kappa_global_p05": cs["kappa_global"].quantile(0.05),
                           "kappa_global_p95": cs["kappa_global"].quantile(0.95),
                           "share_draws_p_lt_0.05": float((cs["p"] < 0.05).mean()),
                           "incr_r2_med": cs["incr_r2"].median(), "placebo_incr_r2_p90": p90,
                           "share_draws_beat_placebo_p90": float((cs["incr_r2"] > p90).mean())})
    return pd.DataFrame(a_rows), pd.DataFrame(c_rows)


def lower_frequency_shares(panel, rng, n_draws=300):
    """Variance shares by origin on non-overlapping 2-day and 5-day changes.

    Summing changes over k days shrinks the misaligned part of each window (the US
    afternoon of the last day) relative to the whole, so if the closing-time mismatch
    is what depresses the US share of Bund variance, the share should rise with k.
    """
    out = {}
    lv_cols = ["ea10", "us10", "eq_ea", "eq_us", "fx"]
    for k, lags in ((2, 2), (5, 1)):
        lv = panel[lv_cols].iloc[::k]
        q = pd.DataFrame(index=lv.index[1:])
        q["d_ea10"] = lv["ea10"].diff().iloc[1:] * 100
        q["r_eq_ea"] = lv["eq_ea"].diff().iloc[1:]
        q["r_eq_us"] = lv["eq_us"].diff().iloc[1:]
        q["d_fx"] = lv["fx"].diff().iloc[1:]
        q["d_spread"] = (lv["ea10"] - lv["us10"]).diff().iloc[1:] * 100
        _, ident = brandt.identify(q, n_draws, rng, p=lags)
        out[f"{k}-day changes"] = brandt.origin_variance_shares(ident)
        out[f"{k}-day changes"]["corr_bund_ust"] = float(
            (q["d_ea10"]).corr(q["d_ea10"] - q["d_spread"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "structural_propagation" / "brandt"))
    ap.add_argument("--n-oos-draws", type=int, default=200)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    panel = brandt.load_panel(args.data_dir)                     # sealed: ends 2025-12-31
    model = dict(np.load(out / "model_brandt_end2025.npz"))
    ident = IdentifiedSet(B=model["B"], Sigma=model["Sigma"], A=model["A"],
                          candidates=len(model["B"]), accepted=len(model["B"]))
    rng = np.random.default_rng(SEED)
    pd.set_option("display.width", 250)

    ll = lead_lag(panel)
    ll.to_csv(out / "exploratory_lead_lag.csv", index=False)
    fevd = {f"{h}d": brandt.fevd_by_origin(ident, h) for h in (1, 2, 5)}
    (out / "exploratory_fevd_by_horizon.json").write_text(json.dumps(fevd, indent=2))
    lowf = lower_frequency_shares(panel, rng)
    (out / "exploratory_lower_frequency_shares.json").write_text(json.dumps(lowf, indent=2))
    for k, d in lowf.items():
        print(k, json.dumps(d, indent=1))
    a, c = skip_day_tests(panel, model, rng)
    a.to_csv(out / "exploratory_skipday_test_a.csv", index=False)
    c.to_csv(out / "exploratory_skipday_test_c.csv", index=False)
    fc = brandt.pseudo_oos(panel, n_draws=args.n_oos_draws, horizons=SKIP_HORIZONS, skip=1,
                           seed=SEED)
    oos = summarise(fc, periods={"2004-2025": (2004, 2025), "2020-2025": (2020, 2025)})
    oos.to_csv(out / "exploratory_skipday_oos.csv", index=False)
    print(ll.round(3).to_string())
    for h, d in fevd.items():
        print(h, pd.DataFrame(d).T.round(3).to_string())
    print(a.round(4).to_string())
    print(c.round(4).to_string())
    print(oos[oos["period"] == "2004-2025"].round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
