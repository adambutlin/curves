"""Apply both frozen end-2025 models to 2026 (pre-registration 08, Section 5).

No parameter, restriction or draw is re-estimated: each day's 2026 shocks come from the
end-2025 VAR coefficients and impact matrices, draw by draw, and the predictive
regressions used to forecast 2026 are estimated on data through 2025 only. The frozen
model files are checked against their recorded SHA-256 before use.

Writes to ``reports/structural_propagation/application_2026/``.

Usage:  python scripts/run_2026_application.py [--data-dir DIR] [--n-forecast-draws N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation import brandt
from giltcurve.propagation.bvar import design
from giltcurve.propagation.data import load_us_panel
from giltcurve.propagation.identification import IdentifiedSet, SHOCKS, VARIABLES
from giltcurve.propagation.oos import clark_west
from giltcurve.propagation.predictive import (
    _OTHER_INNOVATIONS, curve_controls, forward_changes, impact_on, own_moves, premium_contribution,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "structural_propagation"
US_MODEL = (REPORTS / "model_end2025.npz",
            "cafa5f25144f8a4946f69cdf099c54be9709f8824b90f4c2aeb44d317765e7b8")
WINDOWS = {"2026 to date": ("2025-12-31", None), "27 Feb-19 Aug 2026": ("2026-02-27", "2026-08-19")}
START_2026 = pd.Timestamp("2026-01-01")


def load_frozen(path: Path, sha: str) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != sha:
        raise RuntimeError(f"{path.name} does not match its frozen SHA-256 ({digest} != {sha})")
    return dict(np.load(path, allow_pickle=False))


def shocks(panel, variables, model, p):
    Yd, Xd = design(panel[list(variables)].to_numpy(), p)
    eps = [np.linalg.solve(model["B"][j], (Yd - Xd @ model["A"][j]).T).T
           for j in range(len(model["B"]))]
    U_mean = Yd - Xd @ model["A_hat"]
    return panel.index[p:], eps, U_mean


def decompose(dates, eps, B, impact_fn, own, outcomes, shock_names, mt):
    """Daily contributions by shock (median-target draw) and window totals with bands."""
    daily, windows = {}, []
    for o in outcomes:
        b = impact_fn(B, o)                                        # (J, K)
        contrib = np.stack([eps[j] * b[j] for j in range(len(eps))])  # (J, T, K)
        daily[o] = pd.DataFrame(contrib[mt], index=dates, columns=shock_names)
        daily[o]["actual"] = own[o].reindex(dates).to_numpy()
        daily[o]["predictable"] = daily[o]["actual"] - daily[o][list(shock_names)].sum(axis=1)
        for label, (a, z) in WINDOWS.items():
            sel = (dates > pd.Timestamp(a)) & ((dates <= pd.Timestamp(z)) if z else True)
            if not sel.any():
                continue
            tot = contrib[:, sel, :].sum(axis=1)                  # (J, K)
            row = {"outcome": o, "window": label, "first_day": str(dates[sel][0].date()),
                   "last_day": str(dates[sel][-1].date()),
                   "actual_bp": float(daily[o]["actual"][sel].sum()),
                   "predictable_bp": float(daily[o]["predictable"][sel].sum())}
            for k, s in enumerate(shock_names):
                row[f"{s}_bp"] = float(tot[mt, k])
                row[f"{s}_p05"] = float(np.quantile(tot[:, k], 0.05))
                row[f"{s}_p95"] = float(np.quantile(tot[:, k], 0.95))
            windows.append(row)
    return daily, pd.DataFrame(windows)


def forecast_2026(dates, eps, B, U_mean, own, Z, fwd, outcomes, impact_fn, parts_fn, others_fn,
                  horizons, n_draws):
    """Forecasts of 2026 outcomes from regressions estimated on data through 2025."""
    pos = np.arange(len(dates))
    n_tr = int((dates < START_2026).sum())
    test = np.flatnonzero(dates >= START_2026)
    rows = []
    for o in outcomes:
        x = own[o].reindex(dates).to_numpy()
        b = impact_fn(B, o)
        parts = [parts_fn(eps[j], b[j], o) for j in range(n_draws)]
        others = others_fn(U_mean, o)
        for h in horizons:
            r = fwd[(o, h)]
            ok = np.isfinite(r) & np.isfinite(Z).all(1)
            tr = ok & (pos + h < n_tr)
            te = test[ok[test]]
            if te.size < 20:
                continue
            X1 = np.column_stack([np.ones(len(r)), x])
            X2 = np.column_stack([X1, Z])
            X4 = np.column_stack([X2, others])

            def fp(X):
                beta = np.linalg.lstsq(X[tr], r[tr], rcond=None)[0]
                return X[te] @ beta
            f3 = np.mean([fp(np.column_stack([X2] + list(pp))) for pp in parts], axis=0)
            a = r[te]
            f = {"m0": np.zeros(te.size), "m1": fp(X1), "m2": fp(X2), "m3": f3, "m4": fp(X4)}
            sse = {m: float(((a - v) ** 2).sum()) for m, v in f.items()}
            row = {"outcome": o, "h": h, "days": int(te.size)}
            for m in ("m1", "m2", "m3", "m4"):
                row[f"r2_{m}_vs_m0"] = 1 - sse[m] / sse["m0"]
            for m in ("m3", "m4"):
                row[f"cw_p_{m}_vs_m2"] = clark_west(a, f["m2"], f[m], int(h))[1]
            rows.append(row)
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(REPORTS / "application_2026"))
    ap.add_argument("--brandt-sha", required=True, help="SHA-256 recorded when the model was frozen")
    ap.add_argument("--n-forecast-draws", type=int, default=200)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    us_model = load_frozen(*US_MODEL)
    br_model = load_frozen(REPORTS / "brandt" / "model_brandt_end2025.npz", args.brandt_sha)
    summary = {"frozen_models_verified": True}

    # ---- US model (Cieslak-Pang): equity data end with the latest CRSP month.
    us = load_us_panel(args.data_dir, end="2026-12-31", unseal_holdout=True)
    d_us, eps_us, U_us = shocks(us, VARIABLES, us_model, 1)
    mt_us = IdentifiedSet(B=us_model["B"], Sigma=us_model["Sigma"], A=us_model["A"],
                          candidates=len(us_model["B"]), accepted=len(us_model["B"])).median_target()
    own_us = own_moves(us)
    daily_us, win_us = decompose(d_us, eps_us, us_model["B"], impact_on, own_us,
                                 ("y10", "y2", "slope"), SHOCKS, mt_us)
    win_us.insert(0, "model", "US (Cieslak-Pang)")
    fc_us = forecast_2026(
        d_us, eps_us, us_model["B"], U_us, own_us, curve_controls(us).iloc[1:].to_numpy(),
        {k: v.iloc[1:].to_numpy() for k, v in forward_changes(us).items()},
        ("y10", "y2", "slope"), impact_on,
        lambda e, b, o: (premium_contribution(e, b),),
        lambda U, o: U[:, _OTHER_INNOVATIONS[o]], (1, 5, 10, 20), args.n_forecast_draws)
    fc_us.insert(0, "model", "US (Cieslak-Pang)")
    summary["us_panel_last_day"] = str(us.index.max().date())

    # ---- Cross-Atlantic model (Brandt et al.).
    p = int(br_model["p"])
    br = brandt.load_panel(args.data_dir, end="2026-12-31", unseal_holdout=True)
    d_br, eps_br, U_br = shocks(br, brandt.VARIABLES, br_model, p)
    mt_br = IdentifiedSet(B=br_model["B"], Sigma=br_model["Sigma"], A=br_model["A"],
                          candidates=len(br_model["B"]), accepted=len(br_model["B"])).median_target()
    own_br = brandt.own_moves(br)
    daily_br, win_br = decompose(d_br, eps_br, br_model["B"], brandt.impact_on, own_br,
                                 brandt.OUTCOMES, brandt.SHOCKS, mt_br)
    win_br.insert(0, "model", "Cross-Atlantic (Brandt et al.)")
    fc_br = forecast_2026(
        d_br, eps_br, br_model["B"], U_br, own_br, brandt.controls(br).iloc[p:].to_numpy(),
        {k: v.iloc[p:].to_numpy() for k, v in brandt.forward_changes(br).items()},
        brandt.OUTCOMES, brandt.impact_on, brandt.origin_contributions,
        brandt.other_innovations, brandt.HORIZONS, args.n_forecast_draws)
    fc_br.insert(0, "model", "Cross-Atlantic (Brandt et al.)")
    summary["brandt_panel_last_day"] = str(br.index.max().date())

    pd.concat([win_us, win_br]).to_csv(out / "decomposition_windows.csv", index=False)
    pd.concat([fc_us, fc_br]).to_csv(out / "forecasts_2026.csv", index=False)
    for o, df in daily_us.items():
        df[df.index >= START_2026].to_csv(out / f"daily_us_{o}.csv")
    for o, df in daily_br.items():
        df[df.index >= START_2026].to_csv(out / f"daily_brandt_{o}.csv")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.set_option("display.width", 250)
    print(json.dumps(summary, indent=2))
    cols = ["model", "outcome", "window", "actual_bp", "predictable_bp"]
    print(pd.concat([win_us, win_br])[cols + [c for c in pd.concat([win_us, win_br]).columns
                                              if c.endswith("_bp") and c not in cols]].round(1).to_string())
    print(pd.concat([fc_us, fc_br]).round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
