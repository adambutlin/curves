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
from giltcurve.propagation.bvar import design, historical_contributions, impulse_responses
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


def decompose(dates, eps, model, p, weights, own, shock_names, mt, horizon=20):
    """Historical decomposition of 2026 moves by shock, through the VAR's dynamics.

    Each day's contribution of shock k is sum_{s<=horizon} w' Psi_s B[:, k] eps_{t-s,k},
    where ``w`` picks the outcome from the VAR's variables. Working through the dynamics
    matters for the cross-Atlantic model: euro-area prices close before US prices, so
    part of a US shock reaches the Bund only the next day, through the VAR's lags.
    "other" is what the shocks of the previous ``horizon`` days do not explain
    (intercepts and older shocks).
    """
    first = int(np.searchsorted(dates, START_2026))
    i0 = max(first - horizon, 0)
    sub_dates = dates[first:]
    daily, windows = {}, []
    totals = {o: [] for o in weights}
    for j in range(len(eps)):
        Psi = impulse_responses(model["A"][j], p, horizon)
        Theta = np.einsum("sij,jk->sik", Psi, model["B"][j])
        hc = historical_contributions(eps[j][i0:], Theta)[first - i0:]     # (T26, n, K)
        for o, w in weights.items():
            totals[o].append(np.einsum("i,tik->tk", w, hc))               # (T26, K)
    for o in weights:
        contrib = np.stack(totals[o])                                     # (J, T26, K)
        df = pd.DataFrame(contrib[mt], index=sub_dates, columns=shock_names)
        df["actual"] = own[o].reindex(sub_dates).to_numpy()
        df["other"] = df["actual"] - df[list(shock_names)].sum(axis=1)
        daily[o] = df
        for label, (a, z) in WINDOWS.items():
            sel = (sub_dates > pd.Timestamp(a)) & ((sub_dates <= pd.Timestamp(z)) if z else True)
            if not sel.any():
                continue
            tot = contrib[:, sel, :].sum(axis=1)                          # (J, K)
            row = {"outcome": o, "window": label, "first_day": str(sub_dates[sel][0].date()),
                   "last_day": str(sub_dates[sel][-1].date()),
                   "actual_bp": float(df["actual"][sel].sum()),
                   "other_bp": float(df["other"][sel].sum())}
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
    w_us = {"y10": np.eye(4)[2], "y2": np.eye(4)[0], "slope": np.eye(4)[2] - np.eye(4)[0]}
    daily_us, win_us = decompose(d_us, eps_us, us_model, 1, w_us, own_us, SHOCKS, mt_us)
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
    w_br = {"ea10": np.eye(5)[0], "us10": np.eye(5)[0] - np.eye(5)[4], "spread": np.eye(5)[4]}
    daily_br, win_br = decompose(d_br, eps_br, br_model, p, w_br, own_br, brandt.SHOCKS, mt_br)
    win_br.insert(0, "model", "Cross-Atlantic (Brandt et al.)")
    fc_br = forecast_2026(
        d_br, eps_br, br_model["B"], U_br, own_br, brandt.controls(br).iloc[p:].to_numpy(),
        {k: v.iloc[p:].to_numpy() for k, v in brandt.forward_changes(br).items()},
        brandt.OUTCOMES, brandt.impact_on, brandt.origin_contributions,
        brandt.other_innovations, brandt.HORIZONS, args.n_forecast_draws)
    fc_br.insert(0, "model", "Cross-Atlantic (Brandt et al.)")
    # The euro-area close precedes the US close, so next-day Bund moves partly catch up with
    # US afternoon news; the economically interpretable test starts at the next close.
    fc_br_skip = forecast_2026(
        d_br, eps_br, br_model["B"], U_br, own_br, brandt.controls(br).iloc[p:].to_numpy(),
        {k: v.iloc[p:].to_numpy() for k, v in brandt.forward_changes(br, (2, 5, 10, 20), skip=1).items()},
        brandt.OUTCOMES, brandt.impact_on, brandt.origin_contributions,
        brandt.other_innovations, (2, 5, 10, 20), args.n_forecast_draws)
    fc_br_skip.insert(0, "model", "Cross-Atlantic, from the next close")
    fc_br = pd.concat([fc_br, fc_br_skip])
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
    cols = ["model", "outcome", "window", "actual_bp", "other_bp"]
    print(pd.concat([win_us, win_br])[cols + [c for c in pd.concat([win_us, win_br]).columns
                                              if c.endswith("_bp") and c not in cols]].round(1).to_string())
    print(pd.concat([fc_us, fc_br]).round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
