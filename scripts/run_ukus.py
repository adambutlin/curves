"""UK-US models A and B (pre-registration 13): estimation, validation, propagation, freeze.

Writes ``reports/structural_propagation/ukus_{A,B}/`` and freezes each end-2025 model
(``model_ukus_{A,B}_end2025.npz`` with its SHA-256) before any 2026 observation is used.
Needs cached LSEG data or a Workspace session with ``LSEG_APP_KEY`` set.

Usage:  python scripts/run_ukus.py [--data-dir DIR] [--models A B] [--quick]
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
from giltcurve.propagation import ukus
from giltcurve.propagation.brandt import origin_split_test
from giltcurve.propagation.identification import random_rotations
from giltcurve.propagation.oos import summarise
from giltcurve.propagation.predictive import propagation_ratio_test, reduced_form_test_generic

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261010
P = ukus.LAGS


def propagation(spec, panel, post, ident, eps, rng, n_placebo):
    U = post.residuals()
    own = ukus.own_moves(panel).iloc[P:]
    Z = ukus.controls(panel).iloc[P:].to_numpy()
    fwd = ukus.forward_changes(panel)
    K = len(spec.shocks)
    Brand = random_rotations(post.sigma_mean, n_placebo, rng)
    eps_r = [np.linalg.solve(Brand[i], U.T).T for i in range(n_placebo)]
    sizes = [len(spec.origin["uk"]), len(spec.origin["us"])]
    perms = [rng.permutation(K) for _ in range(n_placebo)]
    a_rows, b_rows, c_rows = [], [], []
    for o in ukus.OUTCOMES:
        x = own[o].to_numpy()
        others = ukus.other_innovations(spec, U, o)
        b_all = ukus.impact_on(spec, ident.B, o)
        b_r = ukus.impact_on(spec, Brand, o)
        parts = [ukus.origin_contributions(spec, eps[j], b_all[j], o) for j in range(len(eps))]
        dom_n, for_n = (sizes[1], sizes[0]) if o == "us10" else (sizes[0], sizes[1])
        parts_r = [ukus.origin_contributions(spec, eps_r[i], b_r[i], o, groups=(
            list(perms[i][:dom_n]), list(perms[i][dom_n:dom_n + for_n]), list(perms[i][dom_n + for_n:])))
            for i in range(n_placebo)]
        for h in ukus.HORIZONS:
            r = fwd[(o, h)].iloc[P:].to_numpy()
            a_rows.append({"outcome": o, "h": h, **reduced_form_test_generic(r, x, others, Z, h)})
            g = np.array([propagation_ratio_test(r, eps[j], b_all[j], Z, h)["gamma"] for j in range(len(eps))])
            row = {"outcome": o, "h": h}
            for k, s in enumerate(spec.shocks):
                row[f"gamma_{s}_med"] = float(np.median(g[:, k]))
                row[f"gamma_{s}_p05"] = float(np.quantile(g[:, k], 0.05))
                row[f"gamma_{s}_p95"] = float(np.quantile(g[:, k], 0.95))
                row[f"share_gamma_{s}_pos"] = float((g[:, k] > 0).mean())
            b_rows.append(row)
            cs = pd.DataFrame([origin_split_test(r, x, cf, cg, Z, h) for cf, cg in parts])
            pl = np.array([origin_split_test(r, x, cf, cg, Z, h, with_se=False)["incr_r2"] for cf, cg in parts_r])
            p90 = float(np.quantile(pl, 0.9))
            c_rows.append({"outcome": o, "h": h,
                           "kappa_foreign_med": cs["kappa_foreign"].median(),
                           "kappa_foreign_p05": cs["kappa_foreign"].quantile(0.05),
                           "kappa_foreign_p95": cs["kappa_foreign"].quantile(0.95),
                           "kappa_global_med": cs["kappa_global"].median(),
                           "share_draws_p_lt_0.05": float((cs["p"] < 0.05).mean()),
                           "incr_r2_med": cs["incr_r2"].median(), "placebo_incr_r2_p90": p90,
                           "share_draws_beat_placebo_p90": float((cs["incr_r2"] > p90).mean())})
    return pd.DataFrame(a_rows), pd.DataFrame(b_rows), pd.DataFrame(c_rows)


def risk_validation(spec, panel, eps, data_dir):
    out = {}
    g = spec.shocks.index("global_risk")
    for name, series in (("VIX", load_fred("VIXCLS", data_dir)), ("MOVE", load_yahoo_close("^MOVE", data_dir))):
        d = series.reindex(panel.index).ffill().diff().iloc[P:].to_numpy()
        m = np.isfinite(d)
        corr = [np.corrcoef(e[m, g], d[m])[0, 1] for e in eps]
        out[name] = float(np.median(corr))
    return out


def run(spec, panel, args, rng, out: Path):
    n_draws, n_placebo, n_oos = (40, 40, 10) if args.quick else (1000, 1000, 200)
    summary = {"model": spec.name, "variables": list(spec.variables), "shocks": list(spec.shocks),
               "sample": [str(panel.index.min().date()), str(panel.index.max().date()), len(panel)],
               "timing": ukus.lead_lag(panel)}
    post, ident = ukus.identify(spec, panel, n_draws, rng)
    summary["acceptance_rate"] = ident.acceptance_rate
    eps = ukus.shocks_by_draw(spec, panel, ident)
    summary["variance_shares"] = ukus.origin_variance_shares(spec, ident)
    two = ukus.two_day_panel(panel)
    _, ident2 = ukus.identify(spec, two, max(n_draws // 2, 30), rng, p=2)
    summary["variance_shares_two_day"] = ukus.origin_variance_shares(spec, ident2)
    ev = ukus.event_study(spec, panel, ident, eps)
    ev.to_csv(out / "event_study.csv", index=False)
    rep = ev[ev["representable"]]
    summary["events_mean_share_draws_hit"] = float(rep["share_draws_hit"].mean())
    summary["events_hit_mt"] = f"{int(rep['hit_mt'].sum())} of {len(rep)}"
    summary["risk_validation"] = risk_validation(spec, panel, eps, args.data_dir)
    a, b, c = propagation(spec, panel, post, ident, eps, rng, n_placebo)
    a.to_csv(out / "test_a.csv", index=False)
    b.to_csv(out / "test_b.csv", index=False)
    c.to_csv(out / "test_c_origin.csv", index=False)
    fc = ukus.pseudo_oos(spec, panel, n_draws=n_oos)
    summarise(fc, periods={"2011-2025": (2011, 2025), "2020-2025": (2020, 2025)}).to_csv(
        out / "oos_summary.csv", index=False)
    model_path = out / f"model_ukus_{spec.name}_end2025.npz"
    np.savez_compressed(model_path, B=ident.B, Sigma=ident.Sigma, A=ident.A, A_hat=post.A_hat,
                        variables=np.array(spec.variables), shocks=np.array(spec.shocks), p=P)
    summary["frozen_model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-root", default=str(ROOT / "reports" / "structural_propagation"))
    ap.add_argument("--models", nargs="+", default=["A", "B"])
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)
    panel = ukus.load_panel(args.data_dir)                       # sealed: ends 2025-12-31
    for name in args.models:
        spec = {"A": ukus.SPEC_A, "B": ukus.SPEC_B}[name]
        out = Path(args.out_root) / f"ukus_{name}"
        out.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        s = run(spec, panel, args, np.random.default_rng(SEED), out)
        print(json.dumps({k: s[k] for k in ("model", "sample", "acceptance_rate", "events_hit_mt",
                                             "events_mean_share_draws_hit", "risk_validation",
                                             "frozen_model_sha256")}, indent=1),
              f"({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
