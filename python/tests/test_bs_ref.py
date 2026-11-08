import math
import random

import pytest

from golden import load_cases
from optionpricer_ref.bs import black_scholes
from optionpricer_ref.types import Option


def test_hull_textbook():
    call = black_scholes(Option(42, 40, 0.10, 0.20, 0.5, "call"))
    put = black_scholes(Option(42, 40, 0.10, 0.20, 0.5, "put"))
    assert call["price"] == pytest.approx(4.76, abs=5e-3)
    assert put["price"] == pytest.approx(0.81, abs=5e-3)


def test_put_call_parity():
    rng = random.Random(7)
    for _ in range(20):
        s, k = rng.uniform(50, 150), rng.uniform(50, 150)
        r, q = rng.uniform(-0.02, 0.08), rng.uniform(0.0, 0.05)
        vol, t = rng.uniform(0.05, 0.8), rng.uniform(0.05, 3.0)
        c = black_scholes(Option(s, k, r, vol, t, "call", div_yield=q))["price"]
        p = black_scholes(Option(s, k, r, vol, t, "put", div_yield=q))["price"]
        assert c - p == pytest.approx(s * math.exp(-q * t) - k * math.exp(-r * t), abs=1e-10)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        black_scholes(Option(100, 100, 0.05, -0.1, 1.0, "call"))
    with pytest.raises(ValueError):
        black_scholes(Option(0, 100, 0.05, 0.2, 1.0, "call"))
    with pytest.raises(ValueError):
        black_scholes(Option(100, 100, 0.05, 0.2, 1.0, "call", style="american"))


def test_non_finite_inputs_raise():
    inf, nan = float("inf"), float("nan")
    for bad in (inf, nan):
        for kwargs in ({"spot": bad}, {"strike": bad}, {"vol": bad}, {"expiry": bad}):
            args = dict(spot=100.0, strike=100.0, rate=0.05, vol=0.2, expiry=1.0, **{"type": "call"})
            args.update(kwargs)
            with pytest.raises(ValueError):
                black_scholes(Option(**args))


def test_price_never_negative_across_deep_otm_sweep():
    k = 100.0
    while k <= 3000.0:
        for v in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
            for t in (0.01, 0.11, 0.51, 1.01, 2.0):
                call = black_scholes(Option(100.0, k, 0.03, v, t, "call"))["price"]
                put = black_scholes(Option(100.0, 10000.0 / k, 0.03, v, t, "put"))["price"]
                assert math.isfinite(call) and call >= 0.0
                assert math.isfinite(put) and put >= 0.0
        k *= 1.05


def test_degenerate_cases_are_finite():
    deep = black_scholes(Option(100, 1000, 0.05, 0.2, 0.1, "call"))
    assert 0.0 <= deep["price"] < 1e-12
    tiny = black_scholes(Option(100, 95, 0.05, 1e-6, 1e-8, "call"))
    expected = 100 * math.exp(0) - 95 * math.exp(-0.05 * 1e-8)
    assert tiny["price"] == pytest.approx(expected, abs=1e-9)
    zero_t = black_scholes(Option(100, 95, 0.05, 0.2, 0.0, "call"))
    assert zero_t["price"] == 5.0


def test_golden_european_cases():
    for case in load_cases():
        o = case["option"]
        opt = Option(o["spot"], o["strike"], o["rate"], o["vol"], o["expiry"], o["type"],
                     div_yield=o["div_yield"])
        res = black_scholes(opt)
        for key, expected in case["european"].items():
            assert res[key] == pytest.approx(expected, abs=case["tol"]), (case["id"], key)
