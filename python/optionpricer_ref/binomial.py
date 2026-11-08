"""Cox-Ross-Rubinstein binomial tree (numpy-vectorised backward induction)."""
import math

import numpy as np

from .bs import deterministic
from .types import Option


def _tree(opt: Option, steps: int, vol: float):
    sign = opt.sign
    american = opt.style == "american"
    dt = opt.expiry / steps
    h = vol * math.sqrt(dt)
    # The deepest node is S * exp(h * steps); beyond ~exp(600) prices overflow to inf/NaN.
    if not h * steps < 600.0:
        raise ValueError("vol * sqrt(expiry * steps) too large: tree prices would overflow")
    u = math.exp(h)
    d = 1.0 / u
    disc = math.exp(-opt.rate * dt)
    p = (math.exp((opt.rate - opt.div_yield) * dt) - d) / (u - d)
    if not 0.0 <= p <= 1.0:
        raise ValueError("steps too low: risk-neutral probability outside [0, 1]")

    upow = np.exp(h * np.arange(-steps, steps + 1))  # upow[m + steps] = u**m
    v = np.maximum(sign * (opt.spot * upow[2 * np.arange(steps + 1)] - opt.strike), 0.0)

    v1 = v2 = None
    if steps == 2:
        v2 = v.copy()
    for i in range(steps - 1, -1, -1):
        v = disc * (p * v[1:i + 2] + (1.0 - p) * v[:i + 1])
        if american:
            nodes = opt.spot * upow[2 * np.arange(i + 1) - i + steps]
            v = np.maximum(v, sign * (nodes - opt.strike))
        if i == 2:
            v2 = v.copy()
        elif i == 1:
            v1 = v.copy()
    return float(v[0]), v1, v2, u


def _degenerate(opt: Option, steps: int) -> dict:
    if opt.style == "european" or opt.expiry == 0.0:
        return deterministic(opt)
    best = 0.0
    for i in range(steps + 1):
        t = opt.expiry * i / steps
        payoff = opt.sign * (opt.spot * math.exp((opt.rate - opt.div_yield) * t) - opt.strike)
        best = max(best, math.exp(-opt.rate * t) * max(payoff, 0.0))
    return {"price": best, "delta": None, "gamma": None, "vega": None}


def binomial_crr(opt: Option, steps: int, compute_greeks: bool = True) -> dict:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if opt.expiry == 0.0 or opt.vol == 0.0:
        return _degenerate(opt, steps)

    price, v1, v2, u = _tree(opt, steps, opt.vol)
    if not compute_greeks or steps < 2:
        return {"price": price, "delta": None, "gamma": None, "vega": None}

    d = 1.0 / u
    s, s_u, s_d = opt.spot, opt.spot * u, opt.spot * d
    s_uu, s_dd = opt.spot * u * u, opt.spot * d * d
    delta = (v1[1] - v1[0]) / (s_u - s_d)
    gamma = ((v2[2] - v2[1]) / (s_uu - s) - (v2[1] - v2[0]) / (s - s_dd)) / (0.5 * (s_uu - s_dd))

    bump = 1e-3
    lo = opt.vol - bump if opt.vol - bump > 0.0 else opt.vol
    hi = opt.vol + bump
    price_lo = price
    if lo != opt.vol:
        # Lowering vol can push p outside [0, 1] even though the base tree is valid;
        # fall back to a forward difference instead of losing the price.
        try:
            price_lo = _tree(opt, steps, lo)[0]
        except ValueError:
            lo = opt.vol
    vega = (_tree(opt, steps, hi)[0] - price_lo) / (hi - lo)
    return {"price": price, "delta": delta, "gamma": gamma, "vega": vega}
