#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include <stdexcept>

#include "golden_loader.hpp"
#include "optionpricer/black_scholes.hpp"

using namespace optionpricer;
using Catch::Approx;

static Option make(double s, double k, double r, double v, double t, OptionType ty, double q = 0.0) {
    return Option{s, k, r, v, t, q, ty, Exercise::European};
}

TEST_CASE("golden european cases") {
    auto cases = load_golden(GOLDEN_PATH);
    REQUIRE(!cases.empty());
    for (const auto& c : cases) {
        INFO("case " << c.id);
        PriceResult r = black_scholes(c.option);
        if (c.european.price) REQUIRE(r.price == Approx(*c.european.price).margin(c.tol).epsilon(0));
        REQUIRE(r.greeks.has_value());
        if (c.european.delta) REQUIRE(r.greeks->delta == Approx(*c.european.delta).margin(c.tol).epsilon(0));
        if (c.european.gamma) REQUIRE(r.greeks->gamma == Approx(*c.european.gamma).margin(c.tol).epsilon(0));
        if (c.european.vega) REQUIRE(r.greeks->vega == Approx(*c.european.vega).margin(c.tol).epsilon(0));
    }
}

TEST_CASE("put-call parity with dividend yield") {
    const double s = 100, k = 95, r = 0.04, v = 0.3, t = 1.7, q = 0.025;
    double c = black_scholes(make(s, k, r, v, t, OptionType::Call, q)).price;
    double p = black_scholes(make(s, k, r, v, t, OptionType::Put, q)).price;
    REQUIRE(std::abs((c - p) - (s * std::exp(-q * t) - k * std::exp(-r * t))) < 1e-10);
}

TEST_CASE("negative rate keeps parity") {
    const double s = 100, k = 100, r = -0.01, v = 0.2, t = 1.0;
    double c = black_scholes(make(s, k, r, v, t, OptionType::Call)).price;
    double p = black_scholes(make(s, k, r, v, t, OptionType::Put)).price;
    REQUIRE(std::abs((c - p) - (s - k * std::exp(-r * t))) < 1e-10);
}

TEST_CASE("deep otm is finite and tiny") {
    PriceResult r = black_scholes(make(100, 1000, 0.05, 0.2, 0.1, OptionType::Call));
    REQUIRE(std::isfinite(r.price));
    REQUIRE(r.price >= 0.0);
    REQUIRE(r.price < 1e-12);
    REQUIRE(std::isfinite(r.greeks->gamma));
}

TEST_CASE("price is never negative or NaN across a deep-OTM sweep") {
    for (double k = 100.0; k <= 3000.0; k *= 1.05)
        for (double v = 0.05; v <= 0.6; v += 0.05)
            for (double t = 0.01; t <= 2.0; t += 0.1) {
                double price_call = black_scholes(make(100, k, 0.03, v, t, OptionType::Call)).price;
                double price_put = black_scholes(make(100, 10000.0 / k, 0.03, v, t, OptionType::Put)).price;
                REQUIRE(std::isfinite(price_call));
                REQUIRE(price_call >= 0.0);
                REQUIRE(std::isfinite(price_put));
                REQUIRE(price_put >= 0.0);
            }
}

TEST_CASE("tiny expiry and vol give the deterministic payoff") {
    PriceResult r = black_scholes(make(100, 95, 0.05, 1e-6, 1e-8, OptionType::Call));
    REQUIRE(std::isfinite(r.price));
    REQUIRE(std::abs(r.price - (100.0 - 95.0 * std::exp(-0.05 * 1e-8))) < 1e-9);
}

TEST_CASE("zero expiry returns intrinsic value") {
    REQUIRE(black_scholes(make(100, 95, 0.05, 0.2, 0.0, OptionType::Call)).price == 5.0);
    REQUIRE(black_scholes(make(100, 95, 0.05, 0.2, 0.0, OptionType::Put)).price == 0.0);
}

TEST_CASE("american style and invalid input are rejected") {
    Option o = make(100, 100, 0.05, 0.2, 1.0, OptionType::Call);
    o.style = Exercise::American;
    REQUIRE_THROWS_AS(black_scholes(o), std::invalid_argument);
    REQUIRE_THROWS_AS(black_scholes(make(100, 100, 0.05, -0.2, 1.0, OptionType::Call)), std::invalid_argument);
}
