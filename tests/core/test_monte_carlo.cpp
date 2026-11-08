#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include <stdexcept>

#include "optionpricer/black_scholes.hpp"
#include "optionpricer/monte_carlo.hpp"

using namespace optionpricer;
using Catch::Approx;

static Option make(OptionType ty, double q = 0.0, double s = 100, double k = 100, double r = 0.05,
                   double v = 0.2, double t = 1.0) {
    return Option{s, k, r, v, t, q, ty, Exercise::European};
}

TEST_CASE("price is within three standard errors of Black-Scholes") {
    for (OptionType ty : {OptionType::Call, OptionType::Put}) {
        for (bool anti : {true, false}) {
            Option o = make(ty, 0.02);
            McConfig cfg{200000, 42, anti, false};
            PriceResult mc = monte_carlo(o, cfg);
            double bs = black_scholes(o).price;
            INFO("type " << (ty == OptionType::Call ? "call" : "put") << " antithetic " << anti
                         << " mc " << mc.price << " bs " << bs << " se " << mc.std_error);
            REQUIRE(mc.std_error > 0.0);
            REQUIRE(std::abs(mc.price - bs) <= 3.0 * mc.std_error);
        }
    }
}

TEST_CASE("same seed gives the same result") {
    Option o = make(OptionType::Call);
    McConfig cfg{50000, 7, true, true};
    PriceResult a = monte_carlo(o, cfg), b = monte_carlo(o, cfg);
    REQUIRE(a.price == b.price);
    REQUIRE(a.std_error == b.std_error);
    REQUIRE(a.greeks->delta == b.greeks->delta);
}

TEST_CASE("antithetic variates reduce the standard error") {
    Option o = make(OptionType::Call);
    double with = monte_carlo(o, McConfig{200000, 42, true, false}).std_error;
    double without = monte_carlo(o, McConfig{200000, 42, false, false}).std_error;
    REQUIRE(with < without);
}

TEST_CASE("greeks are close to Black-Scholes") {
    Option o = make(OptionType::Call);
    PriceResult mc = monte_carlo(o, McConfig{200000, 42, true, true});
    PriceResult bs = black_scholes(o);
    REQUIRE(mc.greeks.has_value());
    INFO("delta " << mc.greeks->delta << " gamma " << mc.greeks->gamma << " vega " << mc.greeks->vega);
    REQUIRE(std::abs(mc.greeks->delta - bs.greeks->delta) < 3e-2);
    REQUIRE(std::abs(mc.greeks->gamma - bs.greeks->gamma) < 5e-2);
    REQUIRE(std::abs(mc.greeks->vega - bs.greeks->vega) < 1.0);
}

TEST_CASE("greeks omitted when not requested") {
    REQUIRE(!monte_carlo(make(OptionType::Call), McConfig{1000, 1, true, false}).greeks.has_value());
}

TEST_CASE("too few paths throw") {
    Option o = make(OptionType::Call);
    REQUIRE_THROWS_AS(monte_carlo(o, McConfig{0, 1, false, false}), std::invalid_argument);
    REQUIRE_THROWS_AS(monte_carlo(o, McConfig{1, 1, false, false}), std::invalid_argument);
    // With antithetic pairs a standard error needs at least two pairs.
    REQUIRE_THROWS_AS(monte_carlo(o, McConfig{3, 1, true, false}), std::invalid_argument);
    REQUIRE_NOTHROW(monte_carlo(o, McConfig{4, 1, true, false}));
    REQUIRE_NOTHROW(monte_carlo(o, McConfig{2, 1, false, false}));
}

TEST_CASE("american exercise and invalid input are rejected") {
    Option o = make(OptionType::Put);
    o.style = Exercise::American;
    REQUIRE_THROWS_AS(monte_carlo(o, McConfig{1000, 1}), std::invalid_argument);
    REQUIRE_THROWS_AS(monte_carlo(make(OptionType::Call, 0.0, 100, 100, 0.05, -0.2), McConfig{1000, 1}),
                      std::invalid_argument);
}

TEST_CASE("zero vol returns the deterministic payoff with no error") {
    PriceResult r = monte_carlo(make(OptionType::Call, 0.0, 110, 100, 0.05, 0.0), McConfig{1000, 1});
    REQUIRE(std::abs(r.price - (110.0 - 100.0 * std::exp(-0.05))) < 1e-12);
    REQUIRE(r.std_error == 0.0);
}
