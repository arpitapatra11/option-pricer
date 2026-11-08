"""Closed-form Black-Scholes (European options, continuous dividend yield q)."""
import math

from .types import Option


def _cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def deterministic(opt: Option) -> dict:
    """Discounted deterministic payoff, used when expiry == 0 or vol == 0."""
    fwd = opt.spot * math.exp(-opt.div_yield * opt.expiry) - opt.strike * math.exp(-opt.rate * opt.expiry)
    value = opt.sign * fwd
    price = max(value, 0.0)
    delta = opt.sign * math.exp(-opt.div_yield * opt.expiry) if value > 0.0 else 0.0
    return {"price": price, "delta": delta, "gamma": 0.0, "vega": 0.0}


def black_scholes(opt: Option) -> dict:
    if opt.style != "european":
        raise ValueError("Black-Scholes prices European options only")
    if opt.expiry == 0.0 or opt.vol == 0.0:
        return deterministic(opt)

    s, k, r, q, v, t = opt.spot, opt.strike, opt.rate, opt.div_yield, opt.vol, opt.expiry
    sqrt_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * v * v) * t) / (v * sqrt_t)
    d2 = d1 - v * sqrt_t
    disc_s = s * math.exp(-q * t)
    disc_k = k * math.exp(-r * t)
    if opt.type == "call":
        price = disc_s * _cdf(d1) - disc_k * _cdf(d2)
        delta = math.exp(-q * t) * _cdf(d1)
    else:
        price = disc_k * _cdf(-d2) - disc_s * _cdf(-d1)
        delta = -math.exp(-q * t) * _cdf(-d1)
    # Deep out-of-the-money, the two terms nearly cancel and rounding can leave a
    # tiny negative value; a European option price is never negative.
    price = max(price, 0.0)
    gamma = math.exp(-q * t) * _pdf(d1) / (s * v * sqrt_t)
    vega = disc_s * _pdf(d1) * sqrt_t
    return {"price": price, "delta": delta, "gamma": gamma, "vega": vega}
