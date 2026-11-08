"""C++ core (via pybind11) versus the independent pure-Python reference."""
import pytest

import optionpricer_cpp as cpp
from golden import load_cases
from optionpricer_ref.binomial import binomial_crr as ref_binomial
from optionpricer_ref.bs import black_scholes as ref_bs
from optionpricer_ref.mc import monte_carlo as ref_mc
from optionpricer_ref.types import Option


def to_ref(o, style="european"):
    return Option(o["spot"], o["strike"], o["rate"], o["vol"], o["expiry"], o["type"],
                  div_yield=o.get("div_yield", 0.0), style=style)


def test_cpp_black_scholes_matches_reference_and_golden():
    for case in load_cases():
        o = case["option"]
        got, ref = cpp.black_scholes(o), ref_bs(to_ref(o))
        for key in ("price", "delta", "gamma", "vega"):
            assert got[key] == pytest.approx(ref[key], abs=1e-9), (case["id"], key)
        for key, expected in case["european"].items():
            assert got[key] == pytest.approx(expected, abs=case["tol"]), (case["id"], key)


@pytest.mark.parametrize("style", ["european", "american"])
def test_cpp_binomial_matches_reference(style):
    for case in load_cases():
        o = dict(case["option"], style=style)
        got, ref = cpp.binomial_crr(o, 500), ref_binomial(to_ref(case["option"], style), 500)
        assert got["price"] == pytest.approx(ref["price"], abs=1e-9), case["id"]
        for key in ("delta", "gamma", "vega"):
            assert got[key] == pytest.approx(ref[key], abs=1e-6), (case["id"], key)


def test_cpp_binomial_golden_american():
    for case in [c for c in load_cases() if "american" in c]:
        got = cpp.binomial_crr(dict(case["option"], style="american"), 5000, compute_greeks=False)
        assert got["price"] == pytest.approx(case["american"]["price"], abs=case["american_tol"])
        assert got["delta"] is None


@pytest.mark.parametrize("type_", ["call", "put"])
def test_cpp_monte_carlo_within_three_se_of_black_scholes(type_):
    o = {"spot": 100, "strike": 100, "rate": 0.05, "vol": 0.2, "expiry": 1.0,
         "div_yield": 0.02, "type": type_}
    res = cpp.monte_carlo(o, 200000, 42, compute_greeks=False)
    assert abs(res["price"] - ref_bs(to_ref(o))["price"]) <= 3 * res["std_error"]
    lo, hi = res["ci95"]
    assert lo == pytest.approx(res["price"] - 1.96 * res["std_error"])
    assert hi == pytest.approx(res["price"] + 1.96 * res["std_error"])


def test_reference_and_cpp_monte_carlo_agree_statistically():
    o = {"spot": 100, "strike": 105, "rate": 0.03, "vol": 0.25, "expiry": 1.0, "type": "call"}
    a = cpp.monte_carlo(o, 400000, 1, compute_greeks=False)
    b = ref_mc(to_ref(o), 400000, 2, compute_greeks=False)
    assert abs(a["price"] - b["price"]) <= 4 * (a["std_error"] ** 2 + b["std_error"] ** 2) ** 0.5


def test_invalid_input_raises_value_error():
    good = {"spot": 100, "strike": 100, "rate": 0.05, "vol": 0.2, "expiry": 1.0, "type": "call"}
    with pytest.raises(ValueError):
        cpp.black_scholes(dict(good, vol=-0.1))
    with pytest.raises(ValueError):
        cpp.black_scholes(dict(good, style="american"))
    with pytest.raises(ValueError):
        cpp.binomial_crr(good, 0)
    with pytest.raises(ValueError):
        cpp.monte_carlo(good, 1, 1)
    with pytest.raises(ValueError):
        cpp.black_scholes(dict(good, type="straddle"))
    with pytest.raises((KeyError, ValueError)):
        cpp.black_scholes({"spot": 100})
