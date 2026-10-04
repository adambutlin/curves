"""Expanding-window pseudo out-of-sample evaluation (pre-registration, Section 6).

At each year-end T the VAR posterior, the identified set and every predictive
regression are re-estimated on data through T. A training pair (t, t+h) is
used only if day t+h is no later than T, so no training outcome is realised
after T. Forecasts for year T+1 use day-t information and parameters estimated
through T only: this is a real-time exercise.

Models: M0 zero change (martingale); M1 own move; M2 own move and the curve
state; M3 M2 plus the premium-shock part of today's innovation (forecasts
averaged over the identified set); M4 M2 plus all other reduced-form
innovations, the identification-free upper bound for a linear structural state.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.identification import VARIABLES, sample_identified_set
from giltcurve.propagation.predictive import (
    _OTHER_INNOVATIONS, EXPECTATIONS_IDX, HORIZONS, OUTCOMES, curve_controls,
    forward_changes, impact_on, large_part, ols_nw, own_moves, premium_contribution,
)
from giltcurve.propagation.regimes import (
    COMOVE, HEDGE, regime_identified_sets, regime_premium_contribution,
)

MODELS = ("m0", "m1", "m2", "m3", "m4")


def _fit_predict(y_tr, X_tr, X_te):
    beta, *_ = np.linalg.lstsq(X_tr, y_tr, rcond=None)
    return X_te @ beta


def _ones(n):
    return np.ones((n, 1))


def pseudo_oos(panel: pd.DataFrame, *, years=range(2000, 2026), p: int = 1, lam: float = 0.2,
               n_draws: int = 200, horizons=HORIZONS, outcomes=OUTCOMES,
               seed: int = 20261004) -> pd.DataFrame:
    """Real-time forecasts of r_{t,t+h} for every day of every forecast year."""
    rng = np.random.default_rng(seed)
    Yall = panel[list(VARIABLES)].to_numpy()
    Yd, Xd = design(Yall, p)
    dates = panel.index[p:]
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = {k: v.iloc[p:].to_numpy() for k, v in forward_changes(panel, horizons).items()}
    pos = np.arange(len(dates))
    rows = []
    for year in years:
        T_end = pd.Timestamp(year - 1, 12, 31)
        n_tr = int((dates <= T_end).sum())
        if n_tr < 250:
            continue
        test = np.flatnonzero(dates.year == year)
        if test.size == 0:
            continue
        post = fit_bvar(Yall[: n_tr + p], p=p, lam=lam)
        U_mean = Yd - Xd @ post.A_hat
        ident = sample_identified_set(post.draw, n_draws, rng)
        eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(n_draws)]
        for outcome in outcomes:
            x_own = own[outcome].to_numpy()
            others = U_mean[:, _OTHER_INNOVATIONS[outcome]]
            b = impact_on(ident.B, outcome)                          # (J, K)
            contrib = [premium_contribution(eps[j], b[j]) for j in range(n_draws)]
            for h in horizons:
                r = fwd[(outcome, h)]
                tr = (pos + h < n_tr) & np.isfinite(r) & np.isfinite(Z).all(1)
                te = test[np.isfinite(r[test]) & np.isfinite(Z[test]).all(1)]
                if te.size == 0 or tr.sum() < 100:
                    continue
                X1 = np.column_stack([_ones(len(r)), x_own])
                X2 = np.column_stack([X1, Z])
                X4 = np.column_stack([X2, others])
                f1 = _fit_predict(r[tr], X1[tr], X1[te])
                f2 = _fit_predict(r[tr], X2[tr], X2[te])
                f4 = _fit_predict(r[tr], X4[tr], X4[te])
                f3 = np.zeros(te.size)
                for j in range(n_draws):
                    X3 = np.column_stack([X2, contrib[j]])
                    f3 += _fit_predict(r[tr], X3[tr], X3[te])
                f3 /= n_draws
                rows.append(pd.DataFrame({
                    "date": dates[te], "year": year, "outcome": outcome, "h": h,
                    "actual": r[te], "m0": 0.0, "m1": f1, "m2": f2, "m3": f3, "m4": f4}))
    return pd.concat(rows, ignore_index=True)


def clark_west(actual, f_small, f_big, lags: int) -> tuple[float, float]:
    """Clark-West (2007) adjusted-MSE t-statistic and one-sided p-value (big beats small)."""
    e1 = actual - f_small
    e2 = actual - f_big
    f = e1 ** 2 - (e2 ** 2 - (f_small - f_big) ** 2)
    beta, V, _ = ols_nw(f, np.ones((len(f), 1)), lags)
    t = float(beta[0] / np.sqrt(V[0, 0]))
    return t, float(stats.norm.sf(t))


PERIODS = {"2000-2025": (2000, 2025), "2000-2007": (2000, 2007),
           "2008-2019": (2008, 2019), "2020-2025": (2020, 2025)}


def summarise(fc: pd.DataFrame, periods=PERIODS) -> pd.DataFrame:
    """Out-of-sample R^2 (vs M0 and vs M2), Clark-West tests and MAE ratios."""
    out = []
    for (outcome, h), g in fc.groupby(["outcome", "h"], sort=False):
        for label, (y0, y1) in periods.items():
            s = g[(g["year"] >= y0) & (g["year"] <= y1)].sort_values("date")
            if len(s) < 50:
                continue
            a = s["actual"].to_numpy()
            sse = {m: float(((a - s[m].to_numpy()) ** 2).sum()) for m in MODELS}
            mae = {m: float(np.abs(a - s[m].to_numpy()).mean()) for m in MODELS}
            row = {"outcome": outcome, "h": h, "period": label, "n": len(s)}
            for m in MODELS[1:]:
                row[f"r2_{m}_vs_m0"] = 1 - sse[m] / sse["m0"]
            for m in ("m3", "m4"):
                row[f"r2_{m}_vs_m2"] = 1 - sse[m] / sse["m2"]
                t, pv = clark_west(a, s["m2"].to_numpy(), s[m].to_numpy(), int(h))
                row[f"cw_t_{m}"], row[f"cw_p_{m}"] = t, pv
                row[f"mae_ratio_{m}_vs_m2"] = mae[m] / mae["m2"]
            out.append(row)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- Phase 2: regimes
REGIME_MODELS = ("m0", "m2", "m3r", "m4r")


def pseudo_oos_regime(panel: pd.DataFrame, regime: pd.Series, *, years=range(2000, 2026),
                      p: int = 1, lam: float = 0.2, n_draws: int = 200, horizons=HORIZONS,
                      outcomes=OUTCOMES, seed: int = 20261006,
                      curve_state: bool = True) -> pd.DataFrame:
    """Real-time forecasts with regime-specific identification (Phase 2, Section 5).

    ``regime`` (+1 hedge, -1 co-movement, NaN unknown) must itself be real-time,
    as ``regimes.regime_indicator`` is. Both impact matrices are estimated only
    on training days of their regime. ``curve_state=False`` drops the curve-state
    controls from every model (an exploratory variant, not pre-registered).
    """
    rng = np.random.default_rng(seed)
    Yall = panel[list(VARIABLES)].to_numpy()
    Yd, Xd = design(Yall, p)
    dates = panel.index[p:]
    reg = regime.reindex(panel.index).iloc[p:].to_numpy()
    dH, dC = (reg == HEDGE).astype(float), (reg == COMOVE).astype(float)
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = {k: v.iloc[p:].to_numpy() for k, v in forward_changes(panel, horizons).items()}
    pos = np.arange(len(dates))
    known = np.isfinite(reg)
    rows = []
    for year in years:
        T_end = pd.Timestamp(year - 1, 12, 31)
        n_tr = int((dates <= T_end).sum())
        test = np.flatnonzero(dates.year == year)
        if n_tr < 500 or test.size == 0:
            continue
        post = fit_bvar(Yall[: n_tr + p], p=p, lam=lam)
        U = Yd - Xd @ post.A_hat
        sets = regime_identified_sets(U, reg, n_draws, rng, mask=(pos < n_tr) & known)
        for outcome in outcomes:
            x_own = own[outcome].to_numpy()
            others = U[:, _OTHER_INNOVATIONS[outcome]]
            contrib = [regime_premium_contribution(U, reg, sets, j, outcome)
                       for j in range(n_draws)]
            for h in horizons:
                r = fwd[(outcome, h)]
                ok = np.isfinite(r) & np.isfinite(Z).all(1) & known
                tr = ok & (pos + h < n_tr)
                te = test[ok[test]]
                if te.size == 0 or tr.sum() < 100:
                    continue
                X2 = np.column_stack([np.ones(len(r)), x_own] + ([Z] if curve_state else []))
                X4 = np.column_stack([X2, others * dH[:, None], others * dC[:, None]])
                f2 = _fit_predict(r[tr], X2[tr], X2[te])
                f4 = _fit_predict(r[tr], X4[tr], X4[te])
                f3 = np.zeros(te.size)
                for j in range(n_draws):
                    X3 = np.column_stack([X2, contrib[j] * dH, contrib[j] * dC])
                    f3 += _fit_predict(r[tr], X3[tr], X3[te])
                f3 /= n_draws
                rows.append(pd.DataFrame({
                    "date": dates[te], "year": year, "regime": reg[te], "outcome": outcome,
                    "h": h, "actual": r[te], "m0": 0.0, "m2": f2, "m3r": f3, "m4r": f4}))
    return pd.concat(rows, ignore_index=True)


def summarise_regime(fc: pd.DataFrame) -> pd.DataFrame:
    """Out-of-sample R^2 and Clark-West tests for the regime models, overall and by regime."""
    groups = {"2000-2025": lambda d: d, "2020-2025": lambda d: d[d["year"] >= 2020],
              "hedge-regime days": lambda d: d[d["regime"] == 1],
              "co-movement-regime days": lambda d: d[d["regime"] == -1]}
    out = []
    for (outcome, h), g in fc.groupby(["outcome", "h"], sort=False):
        for label, sel in groups.items():
            s = sel(g).sort_values("date")
            if len(s) < 50:
                continue
            a = s["actual"].to_numpy()
            sse = {m: float(((a - s[m].to_numpy()) ** 2).sum()) for m in REGIME_MODELS}
            row = {"outcome": outcome, "h": h, "sample": label, "n": len(s)}
            for m in REGIME_MODELS[1:]:
                row[f"r2_{m}_vs_m0"] = 1 - sse[m] / sse["m0"]
            for m in ("m3r", "m4r"):
                row[f"r2_{m}_vs_m2"] = 1 - sse[m] / sse["m2"]
                t, pv = clark_west(a, s["m2"].to_numpy(), s[m].to_numpy(), int(h))
                row[f"cw_t_{m}"], row[f"cw_p_{m}"] = t, pv
            out.append(row)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- Phase 3: size of news
SIZE_MODELS = ("m0", "m2", "m3", "m5")


def pseudo_oos_size(panel: pd.DataFrame, *, years=range(2000, 2026), p: int = 1,
                    lam: float = 0.2, n_draws: int = 200, k: float = 2.0, horizons=HORIZONS,
                    outcomes=OUTCOMES, seed: int = 20261007) -> pd.DataFrame:
    """Real-time forecasts with the Phase 3 size terms (pre-registration, Section 3).

    The large-news thresholds use the standard deviation of each component over
    training days only.
    """
    rng = np.random.default_rng(seed)
    Yall = panel[list(VARIABLES)].to_numpy()
    Yd, Xd = design(Yall, p)
    dates = panel.index[p:]
    own = own_moves(panel).iloc[p:]
    Z = curve_controls(panel).iloc[p:].to_numpy()
    fwd = {key: v.iloc[p:].to_numpy() for key, v in forward_changes(panel, horizons).items()}
    pos = np.arange(len(dates))
    rows = []
    for year in years:
        T_end = pd.Timestamp(year - 1, 12, 31)
        n_tr = int((dates <= T_end).sum())
        test = np.flatnonzero(dates.year == year)
        if n_tr < 500 or test.size == 0:
            continue
        post = fit_bvar(Yall[: n_tr + p], p=p, lam=lam)
        ident = sample_identified_set(post.draw, n_draws, rng)
        eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(n_draws)]
        for outcome in outcomes:
            x_own = own[outcome].to_numpy()
            b = impact_on(ident.B, outcome)
            parts = []
            for j in range(n_draws):
                c_tp = premium_contribution(eps[j], b[j])
                c_eh = eps[j][:, EXPECTATIONS_IDX] @ b[j][EXPECTATIONS_IDX]
                tr_rows = pos < n_tr
                parts.append((c_tp, large_part(c_eh, c_eh[tr_rows].std(), k),
                              large_part(c_tp, c_tp[tr_rows].std(), k)))
            for h in horizons:
                r = fwd[(outcome, h)]
                ok = np.isfinite(r) & np.isfinite(Z).all(1)
                tr = ok & (pos + h < n_tr)
                te = test[ok[test]]
                if te.size == 0 or tr.sum() < 100:
                    continue
                X2 = np.column_stack([np.ones(len(r)), x_own, Z])
                f2 = _fit_predict(r[tr], X2[tr], X2[te])
                f3 = np.zeros(te.size)
                f5 = np.zeros(te.size)
                for c_tp, big_eh, big_tp in parts:
                    X3 = np.column_stack([X2, c_tp])
                    X5 = np.column_stack([X3, big_eh, big_tp])
                    f3 += _fit_predict(r[tr], X3[tr], X3[te])
                    f5 += _fit_predict(r[tr], X5[tr], X5[te])
                rows.append(pd.DataFrame({
                    "date": dates[te], "year": year, "outcome": outcome, "h": h,
                    "actual": r[te], "m0": 0.0, "m2": f2, "m3": f3 / n_draws, "m5": f5 / n_draws}))
    return pd.concat(rows, ignore_index=True)


def summarise_size(fc: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (outcome, h), g in fc.groupby(["outcome", "h"], sort=False):
        for label, (y0, y1) in {"2000-2025": (2000, 2025), "2020-2025": (2020, 2025)}.items():
            s = g[(g["year"] >= y0) & (g["year"] <= y1)].sort_values("date")
            a = s["actual"].to_numpy()
            sse = {m: float(((a - s[m].to_numpy()) ** 2).sum()) for m in SIZE_MODELS}
            row = {"outcome": outcome, "h": h, "period": label, "n": len(s)}
            for m in SIZE_MODELS[1:]:
                row[f"r2_{m}_vs_m0"] = 1 - sse[m] / sse["m0"]
            for big, small in (("m5", "m2"), ("m5", "m3")):
                row[f"r2_{big}_vs_{small}"] = 1 - sse[big] / sse[small]
                t, pv = clark_west(a, s[small].to_numpy(), s[big].to_numpy(), int(h))
                row[f"cw_p_{big}_vs_{small}"] = pv
            out.append(row)
    return pd.DataFrame(out)
