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
    currency is dropped (its differential vs itself is zero).
    """
    at = panel[panel["maturity"] == float(tenor)]
    base_rows = at[at["currency"] == base].set_index("date")
    out = []
    for ccy, grp in at[at["currency"] != base].groupby("currency"):
        g = grp.set_index("date")
        joined = g.join(base_rows[["expected_rate", "term_premium"]],
                        rsuffix="_base", how="inner")
        for date, row in joined.iterrows():
            out.append({
                "date": date, "currency": ccy,
                "exp_rate_diff": row["expected_rate"] - row["expected_rate_base"],
                "term_premium_diff": row["term_premium"] - row["term_premium_base"],
            })
    return pd.DataFrame(out, columns=["date", "currency", "exp_rate_diff", "term_premium_diff"])
