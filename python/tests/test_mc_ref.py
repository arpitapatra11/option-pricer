import math

import pytest

from optionpricer_ref.bs import black_scholes
from optionpricer_ref.mc import monte_carlo
from optionpricer_ref.types import Option


def opt(type_="call", q=0.0, s=100.0, k=100.0, r=0.05, v=0.2, t=1.0):
    return Option(s, k, r, v, t, type_, div_yield=q)


@pytest.mark.parametrize("type_", ["call", "put"])
@pytest.mark.parametrize("antithetic", [True, False])
def test_within_three_standard_errors(type_, antithetic):
    o = opt(type_, q=0.02)
    res = monte_carlo(o, 200000, 42, antithetic=antithetic, compute_greeks=False)
    assert res["std_error"] > 0
    assert abs(res["price"] - black_scholes(o)["price"]) <= 3 * res["std_error"]
    lo, hi = res["ci95"]
    assert lo < res["price"] < hi


def test_same_seed_same_result():
    a = monte_carlo(opt(), 50000, 7)
    b = monte_carlo(opt(), 50000, 7)
    assert a == b


def test_antithetic_reduces_standard_error():
    with_ = monte_carlo(opt(), 200000, 42, antithetic=True, compute_greeks=False)["std_error"]
    without = monte_carlo(opt(), 200000, 42, antithetic=False, compute_greeks=False)["std_error"]
    assert with_ < without


def test_greeks_close_to_black_scholes():
    res, bs = monte_carlo(opt(), 200000, 42), black_scholes(opt())
    assert res["delta"] == pytest.approx(bs["delta"], abs=3e-2)
    assert res["gamma"] == pytest.approx(bs["gamma"], abs=5e-2)
    assert res["vega"] == pytest.approx(bs["vega"], abs=1.0)


def test_too_few_paths_raise():
    for paths, anti in [(0, False), (1, False), (3, True)]:
        with pytest.raises(ValueError):
            monte_carlo(opt(), paths, 1, antithetic=anti, compute_greeks=False)
    monte_carlo(opt(), 4, 1, antithetic=True, compute_greeks=False)
    monte_carlo(opt(), 2, 1, antithetic=False, compute_greeks=False)


def test_american_rejected():
    with pytest.raises(ValueError):
        monte_carlo(Option(100, 100, 0.05, 0.2, 1.0, "put", style="american"), 1000, 1)


def test_zero_vol_is_deterministic():
    res = monte_carlo(opt(v=0.0, s=110.0), 1000, 1)
    assert res["price"] == pytest.approx(110.0 - 100.0 * math.exp(-0.05), abs=1e-12)
    assert res["std_error"] == 0.0
