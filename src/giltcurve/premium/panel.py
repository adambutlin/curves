"""Downstream-ready decomposed panel and cross-currency component differentials.

This is the hand-off surface to the downstream cross-currency basis project. It
exposes the decomposed rate components keyed by (date, currency, maturity) and a
helper returning, per tenor, each currency's expected-rate and term-premium
differential versus USD.

HARD CONSTRAINT (do not remove): this module must NOT regress any currency's
cross-currency basis on its own term premium over time — that is circular and out
of scope. This module only PRODUCES decomposed rate components. Cross-sectional
basis modelling happens downstream, ACROSS currencies, not here.
"""
from __future__ import annotations

import pandas as pd

_COLUMNS = ["date", "currency", "maturity", "observed", "fitted",
            "expected_rate", "term_premium"]


def decomposed_panel(per_currency_frames) -> pd.DataFrame:
    """Concatenate per-currency `decompose()` outputs into one tidy panel."""
    panel = pd.concat(list(per_currency_frames), ignore_index=True)
    return panel[_COLUMNS].sort_values(["currency", "date", "maturity"]).reset_index(drop=True)


def cross_currency_differentials(panel: pd.DataFrame, tenor: float, base: str = "USD") -> pd.DataFrame:
    """Per (date, currency) differential of each component vs ``base`` at ``tenor``.

    Returns columns: date, currency, exp_rate_diff, term_premium_diff. The base
    currency is dropped (its differential vs itself is zero). Dates are
    inner-joined against ``base``, so a currency with shorter history than
    ``base`` contributes only the dates both cover.
    """
    # Exact float equality on maturity is safe only because decompose() casts
    # integer-year tenors via float(m); pass tenors from that same grid.
    at_tenor = panel[panel["maturity"] == float(tenor)]
    if at_tenor.empty:
        raise ValueError(f"no rows at maturity {tenor} in panel")
    base_rows = at_tenor[at_tenor["currency"] == base].set_index("date")
    if base_rows.empty:
        raise ValueError(f"base currency {base!r} not found in panel at maturity {tenor}")

    cols = ["date", "currency", "exp_rate_diff", "term_premium_diff"]
    out = []
    for ccy, grp in at_tenor[at_tenor["currency"] != base].groupby("currency"):
        joined = grp.set_index("date").join(
            base_rows[["expected_rate", "term_premium"]], rsuffix="_base", how="inner"
        )
        joined["exp_rate_diff"] = joined["expected_rate"] - joined["expected_rate_base"]
        joined["term_premium_diff"] = joined["term_premium"] - joined["term_premium_base"]
        out.append(joined.reset_index()[cols])
    if not out:
        return pd.DataFrame(columns=cols)
    return pd.concat(out, ignore_index=True)
