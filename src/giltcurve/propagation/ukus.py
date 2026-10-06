"""UK-US daily BVAR (pre-registration 13).

Model A is Brandt et al.'s (2021) cross-Atlantic model with the UK in place of the euro
area: UK monetary, UK macro, US monetary, US macro and global-risk shocks, identified on
the 10-year gilt yield, UK and US equity, sterling and the UK minus US 10-year spread.

Model B adds the 2-year gilt yield and a sixth shock, the **UK risk premium**: gilt
yields rise relative to Treasuries while sterling falls. In Brandt et al.'s table every
domestic shock strengthens the home currency, so Model A cannot represent a
fiscal-credibility scare or a UK-specific inflation-risk repricing; Model B can, though
it cannot tell those two apart.

=========================  =====  =====  ======  =====  =====  ======
Model B, positive shock    UK 2y  UK10y  UK eq   US eq  GBP    UK-US
=========================  =====  =====  ======  =====  =====  ======
UK monetary                  +      +      -              +      +
UK macro                     +      +      +              +      +
UK risk premium                     +                     -      +
US monetary                         +             -       -      -
US macro                            +             +       -      -
Global risk                         -      -      -       -      +
=========================  =====  =====  ======  =====  =====  ======

Model A is the same table without the UK 2-year column and the risk-premium row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.data import HOLDOUT_START, TRAIN_END, HoldoutSealedError, seal
from giltcurve.propagation.identification import sample_identified_set
from giltcurve.propagation.predictive import ols_nw

LAGS = 4
SAMPLE_START = pd.Timestamp("2007-01-02")
HORIZONS = (1, 5, 10, 20)
OUTCOMES = ("uk10", "us10", "spread")


def restriction_a(cols: np.ndarray) -> np.ndarray:
    uk10, eq_uk, eq_us, fx, spread = (cols[..., i] for i in range(5))
    return np.stack([
        (uk10 > 0) & (eq_uk < 0) & (fx > 0) & (spread > 0),                  # UK monetary
        (uk10 > 0) & (eq_uk > 0) & (fx > 0) & (spread > 0),                  # UK macro
        (uk10 > 0) & (eq_us < 0) & (fx < 0) & (spread < 0),                  # US monetary
        (uk10 > 0) & (eq_us > 0) & (fx < 0) & (spread < 0),                  # US macro
        (uk10 < 0) & (eq_uk < 0) & (eq_us < 0) & (fx < 0) & (spread > 0),    # global risk
    ], axis=-1)


def restriction_b(cols: np.ndarray) -> np.ndarray:
    uk2, uk10, eq_uk, eq_us, fx, spread = (cols[..., i] for i in range(6))
    return np.stack([
        (uk2 > 0) & (uk10 > 0) & (eq_uk < 0) & (fx > 0) & (spread > 0),      # UK monetary
        (uk2 > 0) & (uk10 > 0) & (eq_uk > 0) & (fx > 0) & (spread > 0),      # UK macro
        (uk10 > 0) & (fx < 0) & (spread > 0),                                 # UK risk premium
        (uk10 > 0) & (eq_us < 0) & (fx < 0) & (spread < 0),                  # US monetary
        (uk10 > 0) & (eq_us > 0) & (fx < 0) & (spread < 0),                  # US macro
        (uk10 < 0) & (eq_uk < 0) & (eq_us < 0) & (fx < 0) & (spread > 0),    # global risk
    ], axis=-1)


@dataclass(frozen=True)
class Spec:
    name: str
    variables: tuple
    shocks: tuple
    restriction: Callable = field(repr=False)
    origin: dict = field(repr=False)

    def e(self, var: str) -> np.ndarray:
        w = np.zeros(len(self.variables))
        w[self.variables.index(var)] = 1.0
        return w


SPEC_A = Spec("A", ("d_uk10", "r_eq_uk", "r_eq_us", "d_fx", "d_spread"),
              ("uk_monetary", "uk_macro", "us_monetary", "us_macro", "global_risk"),
              restriction_a, {"uk": [0, 1], "us": [2, 3], "global": [4]})
SPEC_B = Spec("B", ("d_uk2", "d_uk10", "r_eq_uk", "r_eq_us", "d_fx", "d_spread"),
              ("uk_monetary", "uk_macro", "uk_risk_premium", "us_monetary", "us_macro", "global_risk"),
              restriction_b, {"uk": [0, 1, 2], "us": [3, 4], "global": [5]})

EVENTS = [
    ("2008-11-25", "Fed LSAP1", ("us_monetary",)),
    ("2013-06-19", "Taper tantrum FOMC", ("us_monetary",)),
    ("2016-06-24", "Brexit referendum result", ("uk_macro", "global_risk")),
    ("2016-08-04", "BoE package (cut, QE)", ("uk_monetary",)),
    ("2017-11-02", "BoE first hike since 2007", ("uk_monetary",)),
    ("2020-03-19", "BoE emergency cut and QE", ("uk_monetary",)),
    ("2021-12-16", "BoE surprise hike", ("uk_monetary",)),
    ("2022-09-23", "Mini-budget", ("uk_risk_premium",)),
    ("2022-09-26", "Gilt and sterling rout continues", ("uk_risk_premium",)),
    ("2022-09-28", "BoE gilt purchases", ("uk_risk_premium", "uk_monetary")),
    ("2022-10-17", "Mini-budget reversed", ("uk_risk_premium",)),
    ("2023-06-22", "BoE 50bp hike", ("uk_monetary",)),
]


# ---------------------------------------------------------------- data
def build_panel(uk2: pd.Series, uk10: pd.Series, us10: pd.Series, eq_uk_log: pd.Series,
                eq_us: pd.Series, gbpusd: pd.Series, *, start=SAMPLE_START,
                end=TRAIN_END, unseal_holdout: bool = False) -> pd.DataFrame:
    """Common-day panel: yields in percent, changes in bp, log returns in percent."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end >= HOLDOUT_START and not unseal_holdout:
        raise HoldoutSealedError(f"end={end.date()} lies inside the sealed holdout")
    parts = {"uk2": uk2, "uk10": uk10, "us10": us10, "eq_uk": eq_uk_log,
             "eq_us": np.log(eq_us) * 100.0, "fx": np.log(gbpusd) * 100.0}
    lv = pd.concat({k: seal(v.dropna(), unseal_holdout=unseal_holdout) for k, v in parts.items()},
                   axis=1, join="inner", sort=True).dropna()
    out = lv.copy()
    for k in ("uk2", "uk10", "us10"):
        out[f"d_{k}"] = lv[k].diff() * 100.0
    out["r_eq_uk"] = lv["eq_uk"].diff()
    out["r_eq_us"] = lv["eq_us"].diff()
    out["d_fx"] = lv["fx"].diff()
    out["d_spread"] = out["d_uk10"] - out["d_us10"]
    out = out.iloc[1:]
    return out.loc[(out.index >= start) & (out.index <= end)]


def load_panel(data_dir="data/raw", *, start=SAMPLE_START, end=TRAIN_END,
               unseal_holdout: bool = False) -> pd.DataFrame:
    """LSEG gilts, Treasury, FTSE 100 future (last trade, roll-adjusted), sterling; S&P 500 (Yahoo)."""
    from giltcurve.ingest.lseg import fetch_history, roll_adjusted_log_level
    from giltcurve.ingest.market import load_yahoo_close
    uk2 = fetch_history("GB2YT=RR", ["MID_YLD_1"], data_dir)["MID_YLD_1"]
    uk10 = fetch_history("GB10YT=RR", ["MID_YLD_1"], data_dir)["MID_YLD_1"]
    us10 = fetch_history("US10YT=RR", ["MID_YLD_1"], data_dir)["MID_YLD_1"]
    f1 = fetch_history("FFIc1", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
    f2 = fetch_history("FFIc2", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
    gbp = fetch_history("GBP=", ["MID_PRICE"], data_dir)["MID_PRICE"]
    eq_uk = roll_adjusted_log_level(f1, f2, "fesx")       # FTSE 100 futures expire on the third Friday
    return build_panel(uk2, uk10, us10, eq_uk, load_yahoo_close("^GSPC", data_dir), gbp,
                       start=start, end=end, unseal_holdout=unseal_holdout)


# ---------------------------------------------------------------- outcomes
def outcome_weights(spec: Spec, outcome: str) -> np.ndarray:
    if outcome == "uk10":
        return spec.e("d_uk10")
    if outcome == "spread":
        return spec.e("d_spread")
    return spec.e("d_uk10") - spec.e("d_spread")                     # us10


def impact_on(spec: Spec, B: np.ndarray, outcome: str) -> np.ndarray:
    return np.einsum("i,...ik->...k", outcome_weights(spec, outcome), B)


def other_innovations(spec: Spec, U: np.ndarray, outcome: str) -> np.ndarray:
    drop = spec.variables.index("d_uk10" if outcome == "uk10" else "d_spread")
    return U[:, [i for i in range(len(spec.variables)) if i != drop]]


def origin_groups(spec: Spec, outcome: str):
    if outcome == "us10":
        return spec.origin["us"], spec.origin["uk"], spec.origin["global"]
    return spec.origin["uk"], spec.origin["us"], spec.origin["global"]


def origin_contributions(spec: Spec, eps, b, outcome, groups=None):
    _, foreign, glob = origin_groups(spec, outcome) if groups is None else groups
    return eps[:, foreign] @ b[foreign], eps[:, glob] @ b[glob]


def outcome_levels(panel):
    return pd.DataFrame({"uk10": panel["uk10"] * 100.0, "us10": panel["us10"] * 100.0,
                         "spread": (panel["uk10"] - panel["us10"]) * 100.0}, index=panel.index)


def own_moves(panel):
    return pd.DataFrame({"uk10": panel["d_uk10"], "us10": panel["d_us10"],
                         "spread": panel["d_spread"]}, index=panel.index)


def forward_changes(panel, horizons=HORIZONS, skip: int = 0) -> dict:
    lv = outcome_levels(panel)
    return {(o, h): lv[o].shift(-h) - lv[o].shift(-skip) for o in OUTCOMES for h in horizons}


def controls(panel) -> pd.DataFrame:
    uk, us = panel["uk10"] * 100.0, panel["us10"] * 100.0
    return pd.DataFrame({
        "uk10": panel["uk10"], "us10": panel["us10"],
        "mom20_uk": uk.shift(1) - uk.shift(21), "mom20_us": us.shift(1) - us.shift(21),
        "vol20_uk": panel["d_uk10"].shift(1).rolling(20).std(),
        "vol20_us": panel["d_us10"].shift(1).rolling(20).std()}, index=panel.index)


# ---------------------------------------------------------------- estimation
def identify(spec: Spec, panel, n_draws, rng, *, p: int = LAGS, lam: float = 0.2):
    post = fit_bvar(panel[list(spec.variables)].to_numpy(), p=p, lam=lam)
    ident = sample_identified_set(post.draw, n_draws, rng, restriction=spec.restriction,
                                  rotations_per_draw=500)
    return post, ident


def shocks_by_draw(spec: Spec, panel, ident, p: int = LAGS):
    Yd, Xd = design(panel[list(spec.variables)].to_numpy(), p)
    return [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(len(ident.B))]


def origin_variance_shares(spec: Spec, ident, stat=np.mean) -> dict:
    """One-step variance shares by shock and by origin (mean over admissible draws)."""
    out = {}
    targets = {v: spec.e(v) for v in spec.variables}
    targets["d_us10"] = outcome_weights(spec, "us10")
    for v, w in targets.items():
        b = np.einsum("i,jik->jk", w, ident.B)                      # (J, K)
        tot = (b ** 2).sum(axis=1)
        out[v] = {"by_origin": {o: float(stat((b[:, idx] ** 2).sum(axis=1) / tot))
                                for o, idx in spec.origin.items()},
                  "by_shock": {s: float(stat(b[:, k] ** 2 / tot)) for k, s in enumerate(spec.shocks)}}
    return out


def event_study(spec: Spec, panel, ident, eps, events=EVENTS, p: int = LAGS) -> pd.DataFrame:
    dates = panel.index[p:]
    b = impact_on(spec, ident.B, "uk10")
    j_mt = ident.median_target()
    rows = []
    for day, name, expected in events:
        i = int(np.searchsorted(dates, pd.Timestamp(day)))
        if i + 1 >= len(dates):
            continue
        contrib = np.array([(eps[j][[i, i + 1]] * b[j]).sum(axis=0) for j in range(len(eps))])
        exp_idx = [spec.shocks.index(s) for s in expected if s in spec.shocks]
        top = np.abs(contrib).argmax(axis=1)
        rows.append({"date": str(dates[i].date()), "event": name, "expected": "/".join(expected),
                     "representable": bool(exp_idx),
                     "actual_2d_bp": float(panel["d_uk10"].iloc[p + i] + panel["d_uk10"].iloc[p + i + 1]),
                     **{f"{s}_bp": float(contrib[j_mt, k]) for k, s in enumerate(spec.shocks)},
                     "dominant_mt": spec.shocks[int(top[j_mt])],
                     "hit_mt": bool(top[j_mt] in exp_idx) if exp_idx else None,
                     "share_draws_hit": float(np.isin(top, exp_idx).mean()) if exp_idx else None})
    return pd.DataFrame(rows)


def lead_lag(panel) -> dict:
    out = {}
    for tgt, col in (("d_uk10", "d_us10"), ("r_eq_uk", "r_eq_us"), ("d_fx", "r_eq_us")):
        nxt = panel[tgt].shift(-1)
        m = nxt.notna().to_numpy()
        X = np.column_stack([np.ones(m.sum()), panel[col].to_numpy()[m]])
        b, V, _ = ols_nw(nxt.to_numpy()[m], X, 1)
        out[f"next_day_{tgt}_on_{col}"] = {"coef": float(b[1]), "t": float(b[1] / np.sqrt(V[1, 1]))}
    out["same_day_corr_uk10_us10"] = float(panel["d_uk10"].corr(panel["d_us10"]))
    return out


def two_day_panel(panel) -> pd.DataFrame:
    """Non-overlapping two-day changes, for the timing robustness check."""
    lv = panel[["uk2", "uk10", "us10", "eq_uk", "eq_us", "fx"]].iloc[::2]
    q = pd.DataFrame(index=lv.index[1:])
    for k in ("uk2", "uk10", "us10"):
        q[f"d_{k}"] = lv[k].diff().iloc[1:] * 100
    q["r_eq_uk"] = lv["eq_uk"].diff().iloc[1:]
    q["r_eq_us"] = lv["eq_us"].diff().iloc[1:]
    q["d_fx"] = lv["fx"].diff().iloc[1:]
    q["d_spread"] = q["d_uk10"] - q["d_us10"]
    return q


def pseudo_oos(spec: Spec, panel, *, years=range(2011, 2026), p: int = LAGS, lam: float = 0.2,
               n_draws: int = 200, horizons=HORIZONS, outcomes=OUTCOMES, seed: int = 20261011,
               skip: int = 0) -> pd.DataFrame:
    """Expanding-window real-time forecasts, models M0-M4 as in the MVP."""
    rng = np.random.default_rng(seed)
    Yall = panel[list(spec.variables)].to_numpy()
    Yd, Xd = design(Yall, p)
    dates = panel.index[p:]
    own = own_moves(panel).iloc[p:]
    Z = controls(panel).iloc[p:].to_numpy()
    fwd = {k: v.iloc[p:].to_numpy() for k, v in forward_changes(panel, horizons, skip).items()}
    pos = np.arange(len(dates))
    rows = []
    for year in years:
        n_tr = int((dates <= pd.Timestamp(year - 1, 12, 31)).sum())
        test = np.flatnonzero(dates.year == year)
        if n_tr < 500 or test.size == 0:
            continue
        post = fit_bvar(Yall[: n_tr + p], p=p, lam=lam)
        U = Yd - Xd @ post.A_hat
        ident = sample_identified_set(post.draw, n_draws, rng, restriction=spec.restriction,
                                      rotations_per_draw=500)
        eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(n_draws)]
        for o in outcomes:
            x = own[o].to_numpy()
            b = impact_on(spec, ident.B, o)
            parts = [origin_contributions(spec, eps[j], b[j], o) for j in range(n_draws)]
            others = other_innovations(spec, U, o)
            for h in horizons:
                r = fwd[(o, h)]
                ok = np.isfinite(r) & np.isfinite(Z).all(1)
                tr = ok & (pos + h < n_tr)
                te = test[ok[test]]
                if te.size == 0 or tr.sum() < 100:
                    continue
                X1 = np.column_stack([np.ones(len(r)), x])
                X2 = np.column_stack([X1, Z])
                X4 = np.column_stack([X2, others])

                def fp(X):
                    beta = np.linalg.lstsq(X[tr], r[tr], rcond=None)[0]
                    return X[te] @ beta
                f3 = np.mean([fp(np.column_stack([X2, cf, cg])) for cf, cg in parts], axis=0)
                rows.append(pd.DataFrame({
                    "date": dates[te], "year": year, "outcome": o, "h": h, "actual": r[te],
                    "m0": 0.0, "m1": fp(X1), "m2": fp(X2), "m3": f3, "m4": fp(X4)}))
    return pd.concat(rows, ignore_index=True)
