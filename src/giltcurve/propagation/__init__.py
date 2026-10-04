"""Structural origins and the propagation of sovereign yield-curve movements.

A daily sign-restricted Bayesian VAR extracts the structural shocks behind each
day's cross-asset move (growth news, monetary news, common and hedging risk
premia, after Cieslak and Pang, 2021); the propagation tests then ask whether
the origin of a yield move predicts how the curve evolves over the following
1-20 trading days. The design and the pre-registered identification are in
``docs/research/structural-propagation/``.
"""
