"""The 2026 gilt selloff through the frozen UK-US models A and B (pre-registration 13).

No re-estimation: 2026 shocks come from each end-2025 model, draw by draw, and are
decomposed through the VAR's dynamics. Aggregates go to
``reports/structural_propagation/application_2026/``; LSEG-derived daily series stay in
the git-ignored ``lseg_private/`` folder.

Usage:  python scripts/run_ukus_2026.py --sha-a <sha> --sha-b <sha> [--data-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_2026_application import (  # noqa: E402
    REPORTS, START_2026, decompose, forecast_2026, load_frozen, shocks,
)

from giltcurve.propagation import ukus  # noqa: E402
from giltcurve.propagation.identification import IdentifiedSet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def run(spec, sha, panel, out, n_draws):
    model = load_frozen(REPORTS / f"ukus_{spec.name}" / f"model_ukus_{spec.name}_end2025.npz", sha)
    p = int(model["p"])
    dates, eps, U = shocks(panel, spec.variables, model, p)
    mt = IdentifiedSet(B=model["B"], Sigma=model["Sigma"], A=model["A"], candidates=len(model["B"]),
                       accepted=len(model["B"])).median_target()
    own = ukus.own_moves(panel)
    weights = {o: ukus.outcome_weights(spec, o) for o in ukus.OUTCOMES}
    if "d_uk2" in spec.variables:
        own["uk2"] = panel["d_uk2"]
        weights["uk2"] = spec.e("d_uk2")
    daily, win = decompose(dates, eps, model, p, weights, own, spec.shocks, mt)
    win.insert(0, "model", f"UK-US model {spec.name}")
    fc = forecast_2026(dates, eps, model["B"], U, ukus.own_moves(panel),
                       ukus.controls(panel).iloc[p:].to_numpy(),
                       {k: v.iloc[p:].to_numpy() for k, v in ukus.forward_changes(panel).items()},
                       ukus.OUTCOMES, lambda B, o: ukus.impact_on(spec, B, o),
                       lambda e, b, o: ukus.origin_contributions(spec, e, b, o),
                       lambda U_, o: ukus.other_innovations(spec, U_, o), ukus.HORIZONS, n_draws)
    fc.insert(0, "model", f"UK-US model {spec.name}")
    private = out / "lseg_private"
    private.mkdir(parents=True, exist_ok=True)
    for o, df in daily.items():
        df[df.index >= START_2026].to_csv(private / f"daily_ukus_{spec.name}_{o}.csv")
    return win, fc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out-dir", default=str(REPORTS / "application_2026"))
    ap.add_argument("--sha-a", required=True)
    ap.add_argument("--sha-b", required=True)
    ap.add_argument("--n-forecast-draws", type=int, default=200)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    panel = ukus.load_panel(args.data_dir, end="2026-12-31", unseal_holdout=True)
    wins, fcs = [], []
    for spec, sha in ((ukus.SPEC_A, args.sha_a), (ukus.SPEC_B, args.sha_b)):
        w, f = run(spec, sha, panel, out, args.n_forecast_draws)
        wins.append(w)
        fcs.append(f)
    win, fc = pd.concat(wins), pd.concat(fcs)
    win.to_csv(out / "ukus_decomposition_windows.csv", index=False)
    fc.to_csv(out / "ukus_forecasts_2026.csv", index=False)
    (out / "ukus_summary.json").write_text(json.dumps(
        {"frozen_models_verified": True, "panel_last_day": str(panel.index.max().date())}, indent=2))
    pd.set_option("display.width", 260)
    cols = ["model", "outcome", "window", "actual_bp", "other_bp"] + [
        c for c in win.columns if c.endswith("_bp") and c not in ("actual_bp", "other_bp")]
    print("panel last day:", panel.index.max().date())
    print(win[cols].round(1).to_string())
    print(fc.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
