"""Forward- and zero-rate extraction (Step 3).

Thin reporting layer over :class:`DiscountCurve`. The numerical content lives in
the curve object; these helpers assemble the tidy tables the research report and
charts consume (spot curve, instantaneous-forward curve, 1y1y-style forwards).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .discount import DiscountCurve


def forward_table(curve: DiscountCurve, maturities) -> pd.DataFrame:
    """Spot rate, discount factor and instantaneous forward by maturity."""
    m = np.asarray(maturities, float)
    return pd.DataFrame(
        {
            "maturity": m,
            "discount_factor": curve.df(m),
            "zero_rate": curve.zero(m),
            "inst_forward": curve.inst_forward(m),
        }
    )


def one_period_forward(curve: DiscountCurve, start: float, tenor: float = 1.0) -> float:
    """Continuously-compounded forward rate from ``start`` over length ``tenor``."""
    return curve.forward(start, start + tenor)


def forward_rate_curve(curve: DiscountCurve, starts, tenor: float = 1.0) -> pd.DataFrame:
    """A curve of ``tenor``-length forward rates starting at each ``starts`` point."""
    s = np.asarray(starts, float)
    return pd.DataFrame(
        {"start": s, "end": s + tenor, "forward_rate": curve.forward(s, s + tenor)}
    )
