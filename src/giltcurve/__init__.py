"""giltcurve — UK SONIA OIS / gilt curve construction and monetary-policy analytics.

A research-grade, from-scratch (numpy/scipy) implementation of:
  * SONIA OIS discount-curve bootstrapping
  * forward- and zero-rate extraction
  * market-implied Bank Rate path (meeting-dated)
  * (roadmap) term-premium and breakeven-inflation decomposition

The core engine deliberately avoids heavyweight pricing libraries so the
mathematics is fully inspectable; ``rateslib`` / ``QuantLib`` are wired in
only as optional cross-validation (see ``pyproject.toml`` ``[validate]``).
"""

__version__ = "0.1.0"
