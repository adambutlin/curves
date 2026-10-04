# Structural origins and the propagation of sovereign yield-curve movements

**Question.** Does knowing *why* sovereign yields moved today (policy-rate news, growth
news, risk-premium shocks) say anything about *how* the curve moves over the next 1-20
trading days, beyond the size of today's move?

**Answer so far (US Treasuries 1983-2025; Bunds and Treasuries 1999-2025).** In sign, yes: moves driven by
news about the expected course of policy rates continue, and moves driven by risk-premium
shocks do not, most clearly when bonds and stocks fall together. As a forecasting claim
about the 10-year yield, no: across three pre-registered designs (constant
identification, regime-specific identification, size-dependent propagation) the effect
explains at most a fraction of a percent of subsequent variance, a random split of the
same news does about as well, and nothing beats a no-change forecast in real time. The
continuation that exists sits in ordinary-sized news; large, salient policy news is
priced at once. The cross-Atlantic model of Brandt et al. gives the same answer once a
closing-time artefact in daily European and US prices is removed.

**2026.** Through both frozen models, the selloff was led by US news: US monetary and
macro news account for about 60% of the rise in both the 10-year Treasury and the
10-year Bund from 27 February to 19 August, and the 2-year's rise was a repricing of the
expected course of US policy rates.

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
| [08-brandt-and-2026-preregistration.md](08-brandt-and-2026-preregistration.md) | The cross-Atlantic model (Brandt et al., 2021) on free data, and the protocol for applying both frozen models to 2026 |
| [09-brandt-results.md](09-brandt-results.md) | Cross-Atlantic replication, the closing-time artefact, and propagation once it is removed |
| [10-2026-application.md](10-2026-application.md) | The 2026 selloff through both frozen models |

## Audit trail

Each pre-registration was hashed (SHA-256) before the estimation it governs, because the
commits intended to timestamp them could not be made in the session:

| Document | UTC | SHA-256 |
|---|---|---|
| 01-research-design.md (as first written) | 2026-10-04 01:22 | `910f9b22...a2d5a` |
| 02-identification-preregistration.md (before the deviations log) | 2026-10-04 01:22 | `4c19a2a1...a8694b` |
| 04-phase2-regime-preregistration.md | 2026-10-04 01:50 | `2551f5e1...4cb5` |
| 06-phase3-size-preregistration.md | 2026-10-04 01:59 | `bc536fc2...3a759` |
| 08-brandt-and-2026-preregistration.md (committed `26bd4d4` before estimation) | 2026-10-04 12:34 | `3abe52df...1b4133` |

Frozen end-2025 models used for the 2026 application: US model (commit `3cf38c2`)
`cafa5f25144f8a4946f69cdf099c54be9709f8824b90f4c2aeb44d317765e7b8`; cross-Atlantic model
(commit `897dea3`) `2fd02b43a05f487410059d01e799d5e547e30ec07d29401fec6f658a75511185`.

## Reproduce

```bash
python scripts/run_structural_propagation.py                 # MVP (~2 min)
python scripts/explore_structural_propagation.py             # exploratory checks on the MVP
python scripts/run_phase2_regimes.py                         # Phase 2 (~1.5 min)
python scripts/explore_structural_propagation.py --phase2    # Phase 2 without curve-state controls
python scripts/run_phase3_size.py                            # Phase 3 (~2 min)
python scripts/explore_structural_propagation.py --phase3    # Phase 3 with trailing-volatility thresholds
python scripts/plot_structural_propagation.py                # figures 1-6
python scripts/run_brandt.py                                 # cross-Atlantic model (~1 min)
python scripts/explore_brandt_timing.py                      # closing-time checks
python scripts/run_2026_application.py --brandt-sha 2fd02b43a05f487410059d01e799d5e547e30ec07d29401fec6f658a75511185
python scripts/plot_brandt_2026.py                           # figures 7-11
```
