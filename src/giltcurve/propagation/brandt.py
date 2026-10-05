"""Cross-Atlantic daily BVAR after Brandt, Saint Guilhem, Schröder and Van Robays (2021).

ECB Working Paper 2560: five daily variables, five shocks, sign restrictions on impact,
conjugate normal-inverse-Wishart prior, uniform prior over rotations, four lags.

Variables (all changes between consecutive common trading days):

=============  ============================================================
``d_ea10``     euro-area 10-year rate (bp). Brandt et al. use the 10-year OIS;
               here the Bundesbank 10-year Svensson zero Bund yield, which they
               report gives similar results (their footnote 8)
``r_eq_ea``    euro-area equity log return (%): Euro Stoxx 50 from April 2007,
               back-filled with the average DAX/CAC 40 return (daily correlation
               with the Euro Stoxx 50 of 0.985 over 2007-2025)
``r_eq_us``    S&P 500 log return (%)
``d_fx``       log change of the dollar price of a euro (%): positive = euro appreciates
``d_spread``   change in the euro-area minus US 10-year spread (bp); the US leg is
               the Gürkaynak-Sack-Wright 10-year zero
=============  ============================================================

Table 1 of the paper (a positive shock; blank = unrestricted):

=========================  =====  =====  =====  =====  ======
                           EA MP  EA mac US MP  US mac global
=========================  =====  =====  =====  =====  ======
euro-area 10y rate          +      +      +      +      -
euro-area equity            -      +                    -
US equity                                 -      +      -
euro (vs dollar)            +      +      -      -      -
euro-area minus US spread   +      +      -      -      +
=========================  =====  =====  =====  =====  ======

The spread restriction is what identifies the country of origin: a domestic shock
moves the domestic long rate by more than the foreign one. The five sets are
mutually exclusive up to sign, so the column matching in
:func:`identification.match_columns` is unique.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.data import HOLDOUT_START, HoldoutSealedError, seal
from giltcurve.propagation.identification import sample_identified_set
from giltcurve.propagation.predictive import _stack, _valid, ols_nw, r2_only, wald

VARIABLES = ("d_ea10", "r_eq_ea", "r_eq_us", "d_fx", "d_spread")
SHOCKS = ("ea_monetary", "ea_macro", "us_monetary", "us_macro", "global_risk")
ORIGIN = {"ea": [0, 1], "us": [2, 3], "global": [4]}
SAMPLE_START = pd.Timestamp("1999-01-04")
LAGS = 4
HORIZONS = (1, 5, 10, 20)
OUTCOMES = ("ea10", "us10", "spread")

# Brandt et al. Table 2: event day and the shocks the authors expect to dominate.
EVENTS = [
    ("2008-09-15", "Lehman Brothers collapse", ("global_risk", "us_macro", "ea_macro")),
    ("2008-11-25", "LSAP1 announcement", ("us_monetary",)),
    ("2009-03-18", "LSAP1 expansion", ("us_monetary",)),
    ("2010-05-10", "Greek programme, EFSF, SMP", ("ea_monetary", "ea_macro")),
    ("2010-11-03", "LSAP2 announcement", ("us_monetary",)),
    ("2012-07-26", "Draghi 'whatever it takes'", ("ea_monetary", "global_risk")),
    ("2013-06-19", "FOMC, taper tantrum", ("us_monetary",)),
    ("2014-08-22", "Draghi Jackson Hole", ("ea_monetary",)),
    ("2014-09-04", "DFR cut, ABSPP/CBPP", ("ea_monetary",)),
    ("2015-01-22", "APP announcement", ("ea_monetary",)),
    ("2015-12-03", "DFR cut, APP extension", ("ea_monetary",)),
    ("2016-01-04", "Stock market sell-off", ("ea_macro", "global_risk")),
    ("2016-06-23", "Brexit referendum", ("ea_macro", "global_risk")),
    ("2016-11-08", "US presidential election", ("us_macro", "global_risk")),
    ("2017-04-23", "French election, first round", ("ea_macro", "global_risk")),
    ("2020-02-25", "COVID-19 intensifies", ("global_risk", "ea_macro", "us_macro")),
    ("2020-03-12", "ECB Governing Council", ("ea_monetary",)),
    ("2020-03-18", "PEPP announcement", ("ea_monetary",)),
]


def restriction_matrix(cols: np.ndarray) -> np.ndarray:
    """Boolean (..., 5): which of the five shocks each impact column satisfies."""
    ea10, eq_ea, eq_us, fx, spread = (cols[..., i] for i in range(5))
    ea_mp = (ea10 > 0) & (eq_ea < 0) & (fx > 0) & (spread > 0)
    ea_macro = (ea10 > 0) & (eq_ea > 0) & (fx > 0) & (spread > 0)
    us_mp = (ea10 > 0) & (eq_us < 0) & (fx < 0) & (spread < 0)
    us_macro = (ea10 > 0) & (eq_us > 0) & (fx < 0) & (spread < 0)
    risk = (ea10 < 0) & (eq_ea < 0) & (eq_us < 0) & (fx < 0) & (spread > 0)
    return np.stack([ea_mp, ea_macro, us_mp, us_macro, risk], axis=-1)


# ---------------------------------------------------------------- data
def euro_equity_log_level(es50: pd.Series, dax: pd.Series, cac: pd.Series) -> pd.Series:
    """Cumulative log return (%) of euro-area equity: Euro Stoxx 50 where it exists,
    the average DAX/CAC 40 log return before it."""
    r_es = np.log(es50).diff()
    r_proxy = pd.concat([np.log(dax).diff(), np.log(cac).diff()], axis=1, sort=True).mean(axis=1)
    first = es50.index.min()
    r = pd.concat([r_proxy[r_proxy.index <= first], r_es[r_es.index > first]]).sort_index()
    return (r.fillna(0.0).cumsum() * 100.0).rename("eq_ea")


def build_panel(bund10: pd.Series, ust10: pd.Series, eq_ea_log: pd.Series, eq_us: pd.Series,
                eurusd: pd.Series, *, start=SAMPLE_START,
                end=HOLDOUT_START - pd.Timedelta(days=1), unseal_holdout: bool = False) -> pd.DataFrame:
    """Align the five series on common days and form the model's daily changes.

    ``eq_ea_log`` is a cumulative log return in percent (see
    :func:`euro_equity_log_level`); ``eq_us`` and ``eurusd`` are levels.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end >= HOLDOUT_START and not unseal_holdout:
        raise HoldoutSealedError(f"end={end.date()} lies inside the sealed holdout")
    parts = {"ea10": bund10, "us10": ust10, "eq_ea": eq_ea_log,
             "eq_us": np.log(eq_us) * 100.0, "fx": np.log(eurusd) * 100.0}
    lv = pd.concat({k: seal(v.dropna(), unseal_holdout=unseal_holdout) for k, v in parts.items()},
                   axis=1, join="inner", sort=True).dropna()
    out = lv.copy()
    out["d_ea10"] = lv["ea10"].diff() * 100.0
    out["d_us10"] = lv["us10"].diff() * 100.0
    out["r_eq_ea"] = lv["eq_ea"].diff()
    out["r_eq_us"] = lv["eq_us"].diff()
    out["d_fx"] = lv["fx"].diff()
    out["d_spread"] = out["d_ea10"] - out["d_us10"]
    out = out.iloc[1:]
    return out.loc[(out.index >= start) & (out.index <= end)]


def load_panel(data_dir="data/raw", *, start=SAMPLE_START, end=HOLDOUT_START - pd.Timedelta(days=1),
               unseal_holdout: bool = False, max_age_days: float | None = 1.0) -> pd.DataFrame:
    from giltcurve.ingest.market import load_bund_zero, load_fred, load_yahoo_close
    from giltcurve.propagation.data import load_gsw_zero_yields
    kw = {"max_age_days": max_age_days}
    eq_ea = euro_equity_log_level(load_yahoo_close("^STOXX50E", data_dir, **kw),
                                  load_yahoo_close("^GDAXI", data_dir, **kw),
                                  load_yahoo_close("^FCHI", data_dir, **kw))
    ust10 = load_gsw_zero_yields(data_dir, unseal_holdout=True, tenors=(10,))["y10"]
    return build_panel(load_bund_zero(10, data_dir, **kw), ust10, eq_ea,
                       load_yahoo_close("^GSPC", data_dir, **kw), load_fred("DEXUSEU", data_dir, **kw),
                       start=start, end=end, unseal_holdout=unseal_holdout)


# ---------------------------------------------------------------- estimation
def identify(panel: pd.DataFrame, n_draws: int, rng: np.random.Generator, *, p: int = LAGS,
             lam: float = 0.2):
    post = fit_bvar(panel[list(VARIABLES)].to_numpy(), p=p, lam=lam)
    ident = sample_identified_set(post.draw, n_draws, rng, restriction=restriction_matrix,
                                  rotations_per_draw=500)
    return post, ident


def shocks_by_draw(panel: pd.DataFrame, ident, p: int = LAGS) -> list[np.ndarray]:
    Yd, Xd = design(panel[list(VARIABLES)].to_numpy(), p)
    return [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(len(ident.B))]


def origin_variance_shares(ident, stat=np.mean) -> dict:
    """Share of each variable's daily innovation variance by shock origin.

    This is the one-step-ahead forecast-error variance decomposition. Brandt et al.
    report it averaged over accepted draws, hence the default ``stat=np.mean``.
    """
    sh = ident.variance_shares()                                  # (J, n, K)
    out = {}
    for i, v in enumerate(VARIABLES):
        out[v] = {o: float(stat(sh[:, i, idx].sum(axis=1))) for o, idx in ORIGIN.items()}
    # The US 10-year is the euro-area rate minus the spread.
    b_us = ident.B[:, 0] - ident.B[:, 4]
    var_us = (b_us ** 2).sum(axis=1)
    out["d_us10"] = {o: float(stat((b_us[:, idx] ** 2).sum(axis=1) / var_us))
                     for o, idx in ORIGIN.items()}
    return out


def fevd_by_origin(ident, horizon: int, stat=np.mean) -> dict:
    """Forecast-error variance shares by shock origin at ``horizon`` days (1 = impact).

    Beyond one day the shares include the next-day catch-up of euro-area prices to US
    news that arrived after the euro-area close, which the one-step shares miss.
    """
    from giltcurve.propagation.bvar import impulse_responses
    n = len(VARIABLES)
    sel = {"d_ea10": np.eye(n)[0], "r_eq_ea": np.eye(n)[1], "r_eq_us": np.eye(n)[2],
           "d_fx": np.eye(n)[3], "d_spread": np.eye(n)[4], "d_us10": np.eye(n)[0] - np.eye(n)[4]}
    shares = {v: {o: [] for o in ORIGIN} for v in sel}
    for j in range(len(ident.B)):
        Psi = impulse_responses(ident.A[j], LAGS, horizon - 1)
        Theta = np.einsum("sij,jk->sik", Psi, ident.B[j])          # (h, n, K)
        for v, w in sel.items():
            contrib = (np.einsum("i,sik->sk", w, Theta) ** 2).sum(axis=0)   # (K,)
            for o, idx in ORIGIN.items():
                shares[v][o].append(contrib[idx].sum() / contrib.sum())
    return {v: {o: float(stat(x)) for o, x in d.items()} for v, d in shares.items()}


# ---------------------------------------------------------------- propagation
def outcome_levels(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"ea10": panel["ea10"] * 100.0, "us10": panel["us10"] * 100.0,
                         "spread": (panel["ea10"] - panel["us10"]) * 100.0}, index=panel.index)


def own_moves(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"ea10": panel["d_ea10"], "us10": panel["d_us10"],
                         "spread": panel["d_spread"]}, index=panel.index)


def forward_changes(panel: pd.DataFrame, horizons=HORIZONS, skip: int = 0) -> dict:
    """``{(outcome, h): x_{t+h} - x_{t+skip}}``. ``skip=1`` starts the window at the next
    close, after the euro-area market has caught up with US news from the afternoon of
    day t (euro-area prices close about five and a half hours before US prices)."""
    lv = outcome_levels(panel)
    return {(o, h): lv[o].shift(-h) - lv[o].shift(-skip) for o in OUTCOMES for h in horizons}


def controls(panel: pd.DataFrame) -> pd.DataFrame:
    """Curve state known at the close of day t: both 10-year levels and, for each, the
    change and the volatility over the previous 20 trading days (day t excluded)."""
    ea, us = panel["ea10"] * 100.0, panel["us10"] * 100.0
    return pd.DataFrame({
        "ea10": panel["ea10"], "us10": panel["us10"],
        "mom20_ea": ea.shift(1) - ea.shift(21), "mom20_us": us.shift(1) - us.shift(21),
        "vol20_ea": panel["d_ea10"].shift(1).rolling(20).std(),
        "vol20_us": panel["d_us10"].shift(1).rolling(20).std()}, index=panel.index)


def impact_on(B: np.ndarray, outcome: str) -> np.ndarray:
    if outcome == "ea10":
        return B[..., 0, :]
    if outcome == "spread":
        return B[..., 4, :]
    return B[..., 0, :] - B[..., 4, :]                            # us10


def other_innovations(U: np.ndarray, outcome: str) -> np.ndarray:
    """Four innovations that, with the outcome's own move, span all five."""
    return U[:, [1, 2, 3, 4]] if outcome == "ea10" else U[:, [0, 1, 2, 3]]


def origin_groups(outcome: str) -> tuple[list[int], list[int], list[int]]:
    """(domestic, foreign, global) shock indices for an outcome."""
    if outcome == "us10":
        return ORIGIN["us"], ORIGIN["ea"], ORIGIN["global"]
    return ORIGIN["ea"], ORIGIN["us"], ORIGIN["global"]


def origin_contributions(eps: np.ndarray, b: np.ndarray, outcome: str, groups=None):
    """Foreign-shock and global-shock parts of the outcome's day-t innovation."""
    _, foreign, glob = origin_groups(outcome) if groups is None else groups
    return eps[:, foreign] @ b[foreign], eps[:, glob] @ b[glob]


def origin_split_test(r, own, c_foreign, c_global, Z, h: int, *, with_se: bool = True) -> dict:
    """r on own move, foreign and global parts and Z. kappa = extra propagation of each
    part relative to the domestic part; H0: both zero (origin irrelevant)."""
    m = _valid(r, own, c_foreign, c_global, Z)
    X0 = _stack(own[m], Z[m])
    X1 = _stack(own[m], c_foreign[m], c_global[m], Z[m])
    r2_0 = r2_only(r[m], X0)
    if with_se:
        beta, V, r2_1 = ols_nw(r[m], X1, h)
        R = np.zeros((2, X1.shape[1]))
        R[0, 2], R[1, 3] = 1.0, 1.0
        W, pval = wald(beta, V, R)
        se = np.sqrt(np.diag(V))
        t_f, t_g = float(beta[2] / se[2]), float(beta[3] / se[3])
    else:
        beta = np.linalg.lstsq(X1, r[m], rcond=None)[0]
        r2_1, W, pval, t_f, t_g = r2_only(r[m], X1), np.nan, np.nan, np.nan, np.nan
    return {"theta_domestic": float(beta[1]), "kappa_foreign": float(beta[2]),
            "kappa_global": float(beta[3]), "t_foreign": t_f, "t_global": t_g,
            "wald": W, "p": pval, "incr_r2": r2_1 - r2_0}


# ---------------------------------------------------------------- real time
def pseudo_oos(panel: pd.DataFrame, *, years=range(2004, 2026), p: int = LAGS, lam: float = 0.2,
               n_draws: int = 200, horizons=HORIZONS, outcomes=OUTCOMES,
               seed: int = 20261008, skip: int = 0) -> pd.DataFrame:
    """Expanding-window real-time forecasts, as in the MVP but for the cross-Atlantic model.

    M0 no change; M1 own move; M2 plus curve state; M3 plus the foreign and global parts
    of today's innovation (averaged over the identified set); M4 plus all other
    innovations (identification-free upper bound).
    """
    rng = np.random.default_rng(seed)
    Yall = panel[list(VARIABLES)].to_numpy()
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
        ident = sample_identified_set(post.draw, n_draws, rng, restriction=restriction_matrix,
                                      rotations_per_draw=500)
        eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(n_draws)]
        for o in outcomes:
            x = own[o].to_numpy()
            b = impact_on(ident.B, o)
            parts = [origin_contributions(eps[j], b[j], o) for j in range(n_draws)]
            others = other_innovations(U, o)
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


# ---------------------------------------------------------------- synchronised data (LSEG)
SYNC_START = pd.Timestamp("2007-01-02")
OIS_SWITCH = pd.Timestamp("2020-01-02")


def spliced_ois(eonia_mid: pd.Series, estr_mid: pd.Series, switch=OIS_SWITCH) -> pd.Series:
    """10-year OIS level: EONIA before ``switch``, ESTR after, joined without a jump."""
    eon = eonia_mid.dropna()
    est = estr_mid.dropna()
    gap = eon[eon.index < switch].iloc[-1] - est[est.index < switch].iloc[-1]
    return pd.concat([eon[eon.index < switch], est[est.index >= switch] + gap]).rename("ois10")


def load_panel_sync(data_dir="data/raw", *, start=SYNC_START,
                    end=HOLDOUT_START - pd.Timedelta(days=1), unseal_holdout: bool = False,
                    rate: str = "ois") -> pd.DataFrame:
    """The cross-Atlantic panel on prices recorded at or near the New York close.

    ``rate="ois"`` (default) uses the 10-year EONIA/ESTR OIS composites, Brandt et al.'s
    own variable; ``rate="bund_future"`` uses the Euro Bund future's last trade, turned
    into a yield change with the 10-year benchmark's modified duration (robustness).
    Requires a Workspace session and ``LSEG_APP_KEY`` unless the series are cached.
    """
    from giltcurve.ingest.lseg import fetch_history, roll_adjusted_log_level
    from giltcurve.ingest.market import load_yahoo_close
    eon = fetch_history("EUREON10Y=", ["BID", "ASK"], data_dir)
    est = fetch_history("EUREST10Y=", ["MID_PRICE"], data_dir)
    fut_eq = fetch_history("STXEc1", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
    fut_eq2 = fetch_history("STXEc2", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
    fx = fetch_history("EUR=", ["MID_PRICE"], data_dir)["MID_PRICE"]
    us10 = fetch_history("US10YT=RR", ["MID_YLD_1"], data_dir)["MID_YLD_1"]
    eq_ea = roll_adjusted_log_level(fut_eq, fut_eq2, "fesx")
    if rate == "ois":
        ea10 = spliced_ois((eon["BID"] + eon["ASK"]) / 2.0, est["MID_PRICE"])
    elif rate == "bund_future":
        c1 = fetch_history("FGBLc1", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
        c2 = fetch_history("FGBLc2", ["TRDPRC_1"], data_dir)["TRDPRC_1"]
        dur = fetch_history("DE10YT=RR", ["MOD_DURTN"], data_dir)["MOD_DURTN"]
        logp = roll_adjusted_log_level(c1, c2, "fgbl")                 # percent
        d_y = -logp.diff() / dur.reindex(logp.index).ffill().shift(1)  # percentage points
        ea10 = d_y.fillna(0.0).cumsum().rename("bund_future_yield") + 4.0
    else:
        raise ValueError(rate)
    return build_panel(ea10, us10, eq_ea, load_yahoo_close("^GSPC", data_dir), fx,
                       start=start, end=end, unseal_holdout=unseal_holdout)
