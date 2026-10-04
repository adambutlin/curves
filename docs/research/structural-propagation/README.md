# Structural origins and the propagation of sovereign yield-curve movements

**Question.** Does knowing *why* sovereign yields moved today (policy-rate news, growth
news, risk-premium shocks) say anything about *how* the curve moves over the next 1-20
trading days, beyond the size of today's move?

**Answer so far (US Treasuries, 1983-2025, 2026 sealed).** In sign, yes: moves driven by
news about the expected course of policy rates continue, and moves driven by risk-premium
shocks do not, most clearly when bonds and stocks fall together. As a forecasting claim
about the 10-year yield, no: across three pre-registered designs (constant
identification, regime-specific identification, size-dependent propagation) the effect
explains at most a fraction of a percent of subsequent variance, a random split of the
same news does about as well, and nothing beats a no-change forecast in real time. The
continuation that exists sits in ordinary-sized news; large, salient policy news is
priced at once.

## Reading order

| Document | Content |
|---|---|
| [01-research-design.md](01-research-design.md) | The proposal and its assessment: why linear forecasts are invariant to the identification, what the null really tests, power, the partly seen 2026 holdout |
| [02-identification-preregistration.md](02-identification-preregistration.md) | MVP identification, tests and decision rules, fixed before estimation, with its deviations log |
| [03-mvp-results.md](03-mvp-results.md) | MVP: replication of Cieslak and Pang, the three propagation tests, real-time evaluation, verdict |
| [04-phase2-regime-preregistration.md](04-phase2-regime-preregistration.md) | Phase 2 design: identification within stock-bond correlation regimes |
| [05-phase2-results.md](05-phase2-results.md) | Phase 2 results: sharper in the co-movement regime, a real-time gain for the 2-year only |
| [06-phase3-size-preregistration.md](06-phase3-size-preregistration.md) | Phase 3 design: does large news propagate differently? |
| [07-phase3-results.md](07-phase3-results.md) | Phase 3 results: large policy news continues *less*; the size route is closed |

## Audit trail

Each pre-registration was hashed (SHA-256) before the estimation it governs, because the
commits intended to timestamp them could not be made in the session:

| Document | UTC | SHA-256 |
|---|---|---|
| 01-research-design.md (as first written) | 2026-10-04 01:22 | `910f9b22...a2d5a` |
| 02-identification-preregistration.md (before the deviations log) | 2026-10-04 01:22 | `4c19a2a1...a8694b` |
| 04-phase2-regime-preregistration.md | 2026-10-04 01:50 | `2551f5e1...4cb5` |
| 06-phase3-size-preregistration.md | 2026-10-04 01:59 | `bc536fc2...3a759` |

The frozen end-2025 model used for the holdout protocol has SHA-256
`cafa5f25144f8a4946f69cdf099c54be9709f8824b90f4c2aeb44d317765e7b8`.

## Reproduce

```bash
python scripts/run_structural_propagation.py                 # MVP (~2 min)
python scripts/explore_structural_propagation.py             # exploratory checks on the MVP
python scripts/run_phase2_regimes.py                         # Phase 2 (~1.5 min)
python scripts/explore_structural_propagation.py --phase2    # Phase 2 without curve-state controls
python scripts/run_phase3_size.py                            # Phase 3 (~2 min)
python scripts/explore_structural_propagation.py --phase3    # Phase 3 with trailing-volatility thresholds
python scripts/plot_structural_propagation.py                # figures
```
