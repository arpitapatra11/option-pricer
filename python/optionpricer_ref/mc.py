"""European Monte Carlo under GBM with antithetic variates (numpy)."""
import math

import numpy as np

from .bs import deterministic
from .types import Option


def _estimate(opt: Option, z: np.ndarray, spot: float, vol: float, antithetic: bool):
    t = opt.expiry
    drift = (opt.rate - opt.div_yield - 0.5 * vol * vol) * t
    diffusion = vol * math.sqrt(t)
    disc = math.exp(-opt.rate * t)

    def payoff(zz):
        return np.maximum(opt.sign * (spot * np.exp(drift + diffusion * zz) - opt.strike), 0.0)

    x = 0.5 * (payoff(z) + payoff(-z)) if antithetic else payoff(z)
    n = x.size
    return disc * float(x.mean()), disc * float(x.std(ddof=1)) / math.sqrt(n)


def monte_carlo(opt: Option, paths: int, seed: int, antithetic: bool = True,
                compute_greeks: bool = True) -> dict:
    if opt.style != "european":
        raise ValueError("Monte Carlo prices European options only")
    # With antithetic variates an odd path count is rounded down to an even one
    # (paths // 2 pairs are simulated), matching the C++ core.
    n = paths // 2 if antithetic else paths
    if paths < 2 or n < 2:
        raise ValueError("too few paths: need at least 2 independent samples "
                         "(4 paths with antithetic variates)")

    if opt.expiry == 0.0 or opt.vol == 0.0:
        det = deterministic(opt)
        det.update(std_error=0.0, ci95=(det["price"], det["price"]))
        if not compute_greeks:
            det.update(delta=None, gamma=None, vega=None)
        return det

    z = np.random.default_rng(seed).standard_normal(n)  # common random numbers for all bumps
    price, se = _estimate(opt, z, opt.spot, opt.vol, antithetic)
    out = {"price": price, "std_error": se, "ci95": (price - 1.96 * se, price + 1.96 * se),
           "delta": None, "gamma": None, "vega": None}
    if not compute_greeks:
        return out

    h = 0.01 * opt.spot
    up = _estimate(opt, z, opt.spot + h, opt.vol, antithetic)[0]
    down = _estimate(opt, z, opt.spot - h, opt.vol, antithetic)[0]
    out["delta"] = (up - down) / (2.0 * h)
    out["gamma"] = (up - 2.0 * price + down) / (h * h)

    bump = 1e-3
    lo = opt.vol - bump if opt.vol - bump > 0.0 else opt.vol
    hi = opt.vol + bump
    out["vega"] = (_estimate(opt, z, opt.spot, hi, antithetic)[0]
                   - _estimate(opt, z, opt.spot, lo, antithetic)[0]) / (hi - lo)
    return out
