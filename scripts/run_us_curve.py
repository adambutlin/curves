"""The US Treasury curve through the frozen cross-Atlantic model (pre-registration 15).

Three steps, run in order:

  freeze    estimate the tenor and ACM loadings on 2007-2025 (2026 sealed) and save them
            with their SHA-256 (commit before ``apply``)
  apply     the four objects for 2026, from the frozen model and frozen loadings
  forecast  real-time forecasts, 2012-2025 (expanding window) and 2026 (frozen)

Writes to ``reports/structural_propagation/us_curve/``. LSEG-derived daily series stay in
its ``lseg_private/`` subfolder (git-ignored).

Usage:  python scripts/run_us_curve.py freeze
        python scripts/run_us_curve.py apply --loadings-sha <sha>
        python scripts/run_us_curve.py forecast --loadings-sha <sha>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation import brandt, uscurve as uc
from giltcurve.propagation.bvar import design, fit_bvar
from giltcurve.propagation.identification import IdentifiedSet, sample_identified_set
from giltcurve.propagation.oos import clark_west

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "structural_propagation"
OUT = REPORTS / "us_curve"
MODEL = (REPORTS / "brandt_sync" / "model_brandt_sync_end2025.npz",
         "4b204619f83696e265a5b188c4ee31892662718fb7894f4b9783d2432e79d489")
LOADINGS = OUT / "loadings_end2025.npz"
SHOCKS = list(brandt.SHOCKS)
K = len(SHOCKS)
START_2026 = pd.Timestamp("2026-01-01")
WINDOWS = {"2026 to date": ("2025-12-31", None), "27 Feb-19 Aug 2026": ("2026-02-27", "2026-08-19")}
YIELDS = [f"y{t}" for t in uc.TENORS]
ACM = [f"{k}{t}" for t in uc.ACM_TENORS for k in ("rn", "tp", "acm")]
OUTCOMES = YIELDS + ACM
SEED = 20261015


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen(path: Path, digest: str) -> dict:
    if sha(path) != digest:
        raise RuntimeError(f"{path.name} does not match its frozen SHA-256")
    return dict(np.load(path, allow_pickle=False))


def model_shocks(panel: pd.DataFrame, model: dict) -> tuple[pd.DatetimeIndex, list[np.ndarray]]:
    p = int(model["p"])
    Yd, Xd = design(panel[list(brandt.VARIABLES)].to_numpy(), p)
    eps = [np.linalg.solve(model["B"][j], (Yd - Xd @ model["A"][j]).T).T
           for j in range(len(model["B"]))]
    return panel.index[p:], eps


def outcome_changes(dates, data_dir, unseal) -> pd.DataFrame:
    lv = pd.concat([uc.load_yields(data_dir, unseal_holdout=unseal),
                    uc.load_acm_daily(data_dir, unseal_holdout=unseal)], axis=1, sort=True)
    return uc.changes_on(lv, dates)[OUTCOMES]


def median_target(model: dict) -> int:
    return IdentifiedSet(B=model["B"], Sigma=model["Sigma"], A=model["A"],
                         candidates=len(model["B"]), accepted=len(model["B"])).median_target()


# ---------------------------------------------------------------- freeze
def freeze(args) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    model = load_frozen(*MODEL)
    panel = brandt.load_panel_sync(args.data_dir)                # sealed: ends 2025-12-31
    dates, eps = model_shocks(panel, model)
    dy = outcome_changes(dates, args.data_dir, unseal=False)
    J = len(eps)
    theta = np.stack([[uc.fit_loadings(eps[j], dy[o].to_numpy()) for o in OUTCOMES]
                      for j in range(J)])                          # (J, n_out, 1+K*(L+1))
    mt = median_target(model)
    fit = {}
    for i, o in enumerate(OUTCOMES):
        a = dy[o].to_numpy()
        r2_1, r2_5, rm_1, rm_5 = [], [], [], []
        for j in range(J):
            f = theta[j, i, 0] + uc.contributions(eps[j], theta[j, i]).sum(axis=1)
            s1 = uc.fit_stats(a, f)
            m = np.isfinite(a)
            s5 = uc.fit_stats(uc.window_sums(np.where(m, a, 0.0), 5), uc.window_sums(np.where(m, f, 0.0), 5))
            r2_1.append(s1["r2"]); rm_1.append(s1["rmse_bp"]); r2_5.append(s5["r2"]); rm_5.append(s5["rmse_bp"])
        fit[o] = {"r2_daily_mt": r2_1[mt], "r2_daily_median": float(np.median(r2_1)),
                  "rmse_daily_mt": rm_1[mt], "sd_daily": s1["sd_bp"],
                  "r2_5d_mt": r2_5[mt], "rmse_5d_mt": rm_5[mt], "sd_5d": s5["sd_bp"]}
    np.savez_compressed(LOADINGS, theta=theta, outcomes=np.array(OUTCOMES), shocks=np.array(SHOCKS),
                        lags=uc.LAGS, model_sha=MODEL[1])
    summary = {"model_sha256": MODEL[1], "median_target_draw": mt, "draws": J,
               "sample": [str(dates.min().date()), str(dates.max().date()), len(dates)],
               "in_sample_fit": fit, "loadings_sha256": sha(LOADINGS)}
    (OUT / "freeze_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------- apply
def window_mask(dates, a, z):
    m = dates > pd.Timestamp(a)
    return m & (dates <= pd.Timestamp(z)) if z else m


def apply(args) -> int:
    model = load_frozen(*MODEL)
    fz = load_frozen(LOADINGS, args.loadings_sha)
    theta = fz["theta"]
    panel = brandt.load_panel_sync(args.data_dir, end="2026-12-31", unseal_holdout=True)
    dates, eps = model_shocks(panel, model)
    dy = outcome_changes(dates, args.data_dir, unseal=True)
    J, mt = len(eps), median_target(model)
    first = int(np.searchsorted(dates, START_2026))
    d26 = dates[first:]
    # contributions (J, T26, n_out, K), from the frozen loadings
    C = np.stack([np.stack([uc.contributions(eps[j], theta[j, i])[first:] for i in range(len(OUTCOMES))],
                           axis=1) for j in range(J)])
    A = dy.iloc[first:].to_numpy()                                    # (T26, n_out)
    last = str(d26[np.isfinite(A[:, 0])][-1].date())
    private = OUT / "lseg_private"
    private.mkdir(parents=True, exist_ok=True)

    combos = {o: {o: 1.0} for o in OUTCOMES}
    combos["s2s10"] = {"y10": 1.0, "y2": -1.0}
    combos["s10s30"] = {"y30": 1.0, "y10": -1.0}
    combos["s2s30"] = {"y30": 1.0, "y2": -1.0}
    idx = {o: i for i, o in enumerate(OUTCOMES)}

    def comb(arr, w):
        return sum(c * arr[..., idx[o], :] if arr.ndim == 4 else c * arr[..., idx[o]] for o, c in w.items())

    # 1. cumulative windows, 3. slopes
    rows = []
    for name, w in combos.items():
        a = comb(np.nan_to_num(A), w)
        c = comb(C, w)                                                # (J, T26, K)
        for label, (a0, z) in WINDOWS.items():
            m = window_mask(d26, a0, z)
            tot = c[:, m, :].sum(axis=1)
            row = {"outcome": name, "window": label, "actual_bp": float(a[m].sum())}
            for k, s in enumerate(SHOCKS):
                row[f"{s}_bp"] = float(tot[mt, k])
                row[f"{s}_p05"] = float(np.quantile(tot[:, k], 0.05))
                row[f"{s}_p95"] = float(np.quantile(tot[:, k], 0.95))
            for o, ks in (("us", [2, 3]), ("ea", [0, 1]), ("global", [4])):
                g = tot[:, ks].sum(axis=1)
                row[f"{o}_bp"] = float(g[mt])
                row[f"{o}_p05"] = float(np.quantile(g, 0.05))
                row[f"{o}_p95"] = float(np.quantile(g, 0.95))
            row["unspanned_bp"] = row["actual_bp"] - float(tot[mt].sum())
            rows.append(row)
        daily = pd.DataFrame(c[mt], index=d26, columns=SHOCKS)
        daily["actual"] = a
        daily["unspanned"] = daily["actual"] - daily[SHOCKS].sum(axis=1)
        daily.to_csv(private / f"daily_{name}.csv")
    win = pd.DataFrame(rows)
    win.to_csv(OUT / "decomposition_windows.csv", index=False)

    # 2. time variation: monthly leaders and rolling 20-day leaders
    mon_rows, roll_rows = [], []
    months = d26.to_period("M")
    for name in YIELDS + ["s2s10", "s10s30"]:
        c = comb(C, combos[name])
        for per in months.unique():
            m = np.asarray(months == per)
            tot = c[:, m, :].sum(axis=1)                              # (J, K)
            lead = np.abs(tot).argmax(axis=1)
            row = {"outcome": name, "month": str(per), "actual_bp": float(comb(np.nan_to_num(A), combos[name])[m].sum()),
                   "leader_mt": SHOCKS[int(lead[mt])], "share_draws_leader": float((lead == lead[mt]).mean())}
            row.update({f"{s}_bp": float(tot[mt, k]) for k, s in enumerate(SHOCKS)})
            mon_rows.append(row)
        cs = np.cumsum(c, axis=1)
        for t in range(19, len(d26)):
            tot = cs[:, t] - (cs[:, t - 20] if t >= 20 else 0)
            lead = np.abs(tot).argmax(axis=1)
            roll_rows.append({"outcome": name, "date": d26[t], "leader_mt": SHOCKS[int(lead[mt])],
                              "share_draws_leader": float((lead == lead[mt]).mean()),
                              **{f"{s}_bp": float(tot[mt, k]) for k, s in enumerate(SHOCKS)}})
    mon = pd.DataFrame(mon_rows)
    mon.to_csv(OUT / "monthly_leaders.csv", index=False)
    roll = pd.DataFrame(roll_rows)
    roll.to_csv(private / "rolling20_leaders.csv", index=False)
    switches = []
    for name, g in roll.groupby("outcome", sort=False):
        lead = g["leader_mt"].to_numpy()
        cur, start = lead[0], 0
        for i in range(1, len(lead) + 1):
            if i == len(lead) or lead[i] != cur:
                if i - start >= 10:
                    switches.append({"outcome": name, "leader": cur, "from": str(g["date"].iloc[start].date()),
                                     "to": str(g["date"].iloc[i - 1].date()), "days": i - start})
                if i < len(lead):
                    cur, start = lead[i], i
    pd.DataFrame(switches).to_csv(OUT / "regimes.csv", index=False)

    # 3. curve signatures (impact loading per 1-sd shock, summed over lags; 2007-2025 estimates)
    sig = np.stack([[uc.impact_signature(theta[j, idx[o]]) for o in OUTCOMES] for j in range(J)])
    srows = []
    for o in OUTCOMES:
        for k, s in enumerate(SHOCKS):
            x = sig[:, idx[o], k]
            srows.append({"outcome": o, "shock": s, "bp_per_sd_mt": float(x[mt]),
                          "p05": float(np.quantile(x, 0.05)), "p95": float(np.quantile(x, 0.95))})
    pd.DataFrame(srows).to_csv(OUT / "signatures.csv", index=False)

    # explanatory fit in 2026 (frozen loadings)
    fit26 = {}
    for o in OUTCOMES:
        i = idx[o]
        a = A[:, i]
        f = C[mt, :, i, :].sum(axis=1) + theta[mt, i, 0]
        m = np.isfinite(a)
        fit26[o] = {"daily": uc.fit_stats(a, f),
                    "5d": uc.fit_stats(uc.window_sums(np.where(m, a, 0.0), 5),
                                       uc.window_sums(np.where(m, f, 0.0), 5))}
    # exploratory (not pre-registered): monthly US-news part of the ACM fitted 10-year against
    # monthly changes in ACM expected rates and term premium, 2007-2025 and 2026
    i10 = idx["acm10"]
    us_part = pd.Series(uc.contributions(eps[mt], theta[mt, i10])[:, [2, 3]].sum(1), index=dates)
    per = dates.to_period("M")
    mb = pd.DataFrame({"us_part": us_part.values, "rn10": dy["rn10"].fillna(0).values,
                       "tp10": dy["tp10"].fillna(0).values}, index=per).groupby(level=0).sum()
    mb["period"] = np.where(mb.index < pd.Period("2026-01", "M"), "2007-2025", "2026")
    mb.to_csv(private / "monthly_bridge.csv")
    bridge = {p_: {c: float(g["us_part"].corr(g[c])) for c in ("rn10", "tp10")} for p_, g in mb.groupby("period")}
    summary = {"model_sha256": MODEL[1], "loadings_sha256": args.loadings_sha, "last_day": last,
               "median_target_draw": mt, "fit_2026": fit26, "exploratory_monthly_bridge_corr": bridge}
    print("monthly bridge", bridge)
    (OUT / "apply_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    pd.set_option("display.width", 250)
    cols = ["outcome", "window", "actual_bp"] + [f"{s}_bp" for s in SHOCKS] + ["unspanned_bp"]
    print(win[cols].round(1).to_string())
    print(pd.DataFrame(switches).to_string())
    print(json.dumps({o: {k: round(v["r2"], 3) for k, v in d.items()} for o, d in fit26.items()}))
    return 0


# ---------------------------------------------------------------- forecast
HORIZONS = (1, 5, 20)


def features(panel, dates, eps_list, thetas, dy, levels):
    """Per outcome: own move, curve state, origin parts (averaged over draws), innovations."""
    out = {}
    lv = levels.reindex(dates).ffill() * 100.0
    state_base = np.column_stack([lv["y2"], lv["y10"], lv["y30"]])
    for i, o in enumerate(YIELDS):
        x = dy[o].to_numpy()
        mom = (lv[o].shift(1) - lv[o].shift(21)).to_numpy()
        vol = dy[o].shift(1).rolling(20, min_periods=15).std().to_numpy()
        Z = np.column_stack([state_base, mom, vol])
        parts = np.mean([np.column_stack([
            uc.contributions(e, th[i])[:, [2, 3]].sum(1), uc.contributions(e, th[i])[:, [0, 1]].sum(1),
            uc.contributions(e, th[i])[:, 4]]) for e, th in zip(eps_list, thetas)], axis=0)
        out[o] = (x, Z, parts)
    return out


def fwd(levels, dates, o, h, skip=1):
    lv = levels.reindex(dates).ffill()[o].to_numpy() * 100.0
    n = len(lv)
    r = np.full(n, np.nan)
    i = np.arange(n - skip - h)
    r[i] = lv[i + skip + h] - lv[i + skip]
    return r


def forecast(args) -> int:
    model = load_frozen(*MODEL)
    fz = load_frozen(LOADINGS, args.loadings_sha)
    rng = np.random.default_rng(SEED)
    panel = brandt.load_panel_sync(args.data_dir, end="2026-12-31", unseal_holdout=True)
    p = int(model["p"])
    Yall = panel[list(brandt.VARIABLES)].to_numpy()
    Yd, Xd = design(Yall, p)
    dates = panel.index[p:]
    levels = uc.load_yields(args.data_dir, unseal_holdout=True)
    dy = uc.changes_on(levels, dates)[YIELDS]
    pos = np.arange(len(dates))
    rows = []
    t0 = time.time()
    for year in list(range(2012, 2026)) + [2026]:
        n_tr = int((dates < pd.Timestamp(year, 1, 1)).sum())
        test = np.flatnonzero(dates.year == year)
        if year < 2026:
            post = fit_bvar(Yall[: n_tr + p], p=p, lam=0.2)
            ident = sample_identified_set(post.draw, args.n_draws, rng, restriction=brandt.restriction_matrix,
                                          rotations_per_draw=500)
            eps = [np.linalg.solve(ident.B[j], (Yd - Xd @ ident.A[j]).T).T for j in range(args.n_draws)]
            thetas = [np.stack([uc.fit_loadings(e[:n_tr], dy[o].to_numpy()[:n_tr]) for o in YIELDS]) for e in eps]
            U = Yd - Xd @ post.A_hat
        else:
            sel = np.random.default_rng(SEED).choice(len(model["B"]), args.n_draws, replace=False)
            eps = [np.linalg.solve(model["B"][j], (Yd - Xd @ model["A"][j]).T).T for j in sel]
            thetas = [fz["theta"][j][[OUTCOMES.index(o) for o in YIELDS]] for j in sel]
            U = Yd - Xd @ model["A_hat"]
        feats = features(panel, dates, eps, thetas, dy, levels)
        for o in YIELDS:
            x, Z, parts = feats[o]
            for skip, hs in ((1, HORIZONS), (0, (1,))):
                for h in hs:
                    r = fwd(levels, dates, o, h, skip)
                    X1 = np.column_stack([np.ones(len(r)), np.nan_to_num(x)])
                    X2 = np.column_stack([X1, Z])
                    X3 = np.column_stack([X2, parts])
                    X4 = np.column_stack([X2, U])
                    ok = np.isfinite(r) & np.isfinite(X3).all(1) & np.isfinite(X4).all(1)
                    tr = ok & (pos + skip + h < n_tr)
                    te = test[ok[test]]
                    if te.size < 20:
                        continue

                    def fp(X):
                        b = np.linalg.lstsq(X[tr], r[tr], rcond=None)[0]
                        return X[te] @ b
                    rows.append(pd.DataFrame({"date": dates[te], "year": year, "outcome": o, "h": h,
                                              "from": "next close" if skip else "same close",
                                              "actual": r[te], "m0": 0.0, "m1": fp(X1), "m2": fp(X2),
                                              "m3": fp(X3), "m4": fp(X4)}))
        print(year, f"{time.time() - t0:.0f}s", flush=True)
    fc = pd.concat(rows, ignore_index=True)
    (OUT / "lseg_private").mkdir(parents=True, exist_ok=True)
    fc.to_csv(OUT / "lseg_private" / "forecasts.csv.gz", index=False)
    summ = []
    for (o, h, frm), g in fc.groupby(["outcome", "h", "from"], sort=False):
        for label, (y0, y1) in {"2012-2025": (2012, 2025), "2026": (2026, 2026)}.items():
            s = g[(g.year >= y0) & (g.year <= y1)].sort_values("date")
            a = s["actual"].to_numpy()
            row = {"outcome": o, "h": h, "from": frm, "period": label, "n": len(s),
                   "rmse_m0": float(np.sqrt((a ** 2).mean()))}
            for m in ("m1", "m2", "m3", "m4"):
                e = a - s[m].to_numpy()
                row[f"r2_{m}"] = float(1 - (e ** 2).sum() / (a ** 2).sum())
                row[f"rmse_{m}"] = float(np.sqrt((e ** 2).mean()))
            for m in ("m3", "m4"):
                row[f"cw_p_{m}_vs_m2"] = clark_west(a, s["m2"].to_numpy(), s[m].to_numpy(), int(h))[1]
            row["cw_p_m3_vs_m0"] = clark_west(a, np.zeros_like(a), s["m3"].to_numpy(), int(h))[1]
            summ.append(row)
    summ = pd.DataFrame(summ)
    summ.to_csv(OUT / "forecast_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(summ.round(4).to_string())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["freeze", "apply", "forecast"])
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--loadings-sha", default=None)
    ap.add_argument("--n-draws", type=int, default=200)
    args = ap.parse_args(argv)
    return {"freeze": freeze, "apply": apply, "forecast": forecast}[args.step](args)


if __name__ == "__main__":
    raise SystemExit(main())
