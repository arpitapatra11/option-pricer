import math

import pytest

from golden import load_cases
from optionpricer_ref.binomial import binomial_crr
from optionpricer_ref.bs import black_scholes
from optionpricer_ref.types import Option


def opt(style="european", type_="call", q=0.0, s=100.0, k=100.0, r=0.05, v=0.2, t=1.0):
    return Option(s, k, r, v, t, type_, div_yield=q, style=style)


@pytest.mark.parametrize("type_", ["call", "put"])
def test_converges_to_black_scholes(type_):
    o = opt(type_=type_)
    assert binomial_crr(o, 5000, compute_greeks=False)["price"] == pytest.approx(
        black_scholes(o)["price"], abs=1e-2)


def test_american_put_at_least_european_put():
    for q in (0.0, 0.03):
        eu = binomial_crr(opt(type_="put", q=q), 400, compute_greeks=False)["price"]
        am = binomial_crr(opt("american", "put", q=q), 400, compute_greeks=False)["price"]
        assert am >= eu - 1e-12


def test_american_at_least_intrinsic():
    o = opt("american", "put", s=60.0, k=100.0)
    assert binomial_crr(o, 300, compute_greeks=False)["price"] >= 40.0 - 1e-12


def test_american_call_equals_european_call_without_dividends():
    eu = binomial_crr(opt(), 500, compute_greeks=False)["price"]
    am = binomial_crr(opt("american"), 500, compute_greeks=False)["price"]
    assert am == pytest.approx(eu, abs=1e-9)


def test_greeks_match_black_scholes():
    o = opt()
    tree, bs = binomial_crr(o, 5000), black_scholes(o)
    assert tree["delta"] == pytest.approx(bs["delta"], abs=1e-3)
    assert tree["gamma"] == pytest.approx(bs["gamma"], abs=1e-3)
    assert tree["vega"] == pytest.approx(bs["vega"], abs=1e-1)


def test_p_out_of_range_raises():
    with pytest.raises(ValueError):
        binomial_crr(opt(r=0.5, v=0.01), 2)


def test_greeks_survive_when_vol_down_bump_makes_p_invalid():
    # Base tree is valid, but vol - 1e-3 pushes p above 1.
    o = opt(r=0.2, v=0.02)
    binomial_crr(o, 100, compute_greeks=False)
    res = binomial_crr(o, 100)
    assert res["vega"] is not None and math.isfinite(res["vega"])


def test_tree_overflow_is_rejected():
    with pytest.raises(ValueError):
        binomial_crr(opt(v=5.0, t=10.0), 5000)


def test_invalid_steps_raise():
    with pytest.raises(ValueError):
        binomial_crr(opt(), 0)


def test_zero_vol_is_deterministic_and_finite():
    eu = binomial_crr(opt(v=0.0, s=110.0), 100)
    assert eu["price"] == pytest.approx(110.0 - 100.0 * math.exp(-0.05), abs=1e-12)
    am = binomial_crr(opt("american", "put", v=0.0, s=80.0), 100)
    assert math.isfinite(am["price"]) and am["price"] >= 20.0 - 1e-12


def test_golden_american_cases():
    cases = [c for c in load_cases() if "american" in c]
    assert len(cases) == 6
    for c in cases:
        o = c["option"]
        am = binomial_crr(Option(o["spot"], o["strike"], o["rate"], o["vol"], o["expiry"],
                                 o["type"], div_yield=o["div_yield"], style="american"),
                          5000, compute_greeks=False)
        assert am["price"] == pytest.approx(c["american"]["price"], abs=c["american_tol"]), c["id"]
