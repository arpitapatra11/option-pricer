#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include <stdexcept>

#include "golden_loader.hpp"
#include "optionpricer/binomial.hpp"
#include "optionpricer/black_scholes.hpp"

using namespace optionpricer;
using Catch::Approx;

static Option make(OptionType ty, Exercise ex = Exercise::European, double q = 0.0, double s = 100,
                   double k = 100, double r = 0.05, double v = 0.2, double t = 1.0) {
    return Option{s, k, r, v, t, q, ty, ex};
}

TEST_CASE("converges to Black-Scholes at N=5000") {
    for (OptionType ty : {OptionType::Call, OptionType::Put}) {
        Option o = make(ty);
        REQUIRE(binomial_crr(o, 5000, false).price == Approx(black_scholes(o).price).margin(1e-2).epsilon(0));
    }
}

TEST_CASE("american put >= european put, american >= intrinsic") {
    for (double q : {0.0, 0.03}) {
        double eu = binomial_crr(make(OptionType::Put, Exercise::European, q), 400, false).price;
        double am = binomial_crr(make(OptionType::Put, Exercise::American, q), 400, false).price;
        REQUIRE(am >= eu - 1e-12);
    }
    REQUIRE(binomial_crr(make(OptionType::Put, Exercise::American, 0.0, 60), 300, false).price >= 40.0 - 1e-12);
}

TEST_CASE("american call equals european call when q = 0") {
    double eu = binomial_crr(make(OptionType::Call), 500, false).price;
    double am = binomial_crr(make(OptionType::Call, Exercise::American), 500, false).price;
    REQUIRE(std::abs(am - eu) < 1e-9);
}

TEST_CASE("greeks match Black-Scholes at N=5000") {
    Option o = make(OptionType::Call);
    PriceResult tree = binomial_crr(o, 5000);
    PriceResult bs = black_scholes(o);
    REQUIRE(tree.greeks.has_value());
    REQUIRE(tree.greeks->delta == Approx(bs.greeks->delta).margin(1e-3).epsilon(0));
    REQUIRE(tree.greeks->gamma == Approx(bs.greeks->gamma).margin(1e-3).epsilon(0));
    REQUIRE(tree.greeks->vega == Approx(bs.greeks->vega).margin(1e-1).epsilon(0));
}

TEST_CASE("greeks are omitted when not requested") {
    REQUIRE(!binomial_crr(make(OptionType::Call), 100, false).greeks.has_value());
}

TEST_CASE("golden american cases") {
    int n = 0;
    for (const auto& c : load_golden(GOLDEN_PATH)) {
        if (!c.american) continue;
        ++n;
        Option o = c.option;
        o.style = Exercise::American;
        INFO("case " << c.id);
        REQUIRE(binomial_crr(o, 5000, false).price ==
                Approx(*c.american->price).margin(c.american_tol).epsilon(0));
    }
    REQUIRE(n == 6);
}

TEST_CASE("risk-neutral probability out of range throws") {
    REQUIRE_THROWS_AS(binomial_crr(make(OptionType::Call, Exercise::European, 0.0, 100, 100, 0.5, 0.01), 2),
                      std::invalid_argument);
}

TEST_CASE("greeks survive when the vol-down bump would make p invalid") {
    // Base tree is valid, but vol - 1e-3 pushes p above 1.
    Option o = make(OptionType::Call, Exercise::European, 0.0, 100, 100, 0.2, 0.02);
    REQUIRE_NOTHROW(binomial_crr(o, 100, false));
    PriceResult r;
    REQUIRE_NOTHROW(r = binomial_crr(o, 100, true));
    REQUIRE(r.greeks.has_value());
    REQUIRE(std::isfinite(r.greeks->vega));
}

TEST_CASE("tree overflow is rejected instead of returning inf/NaN") {
    REQUIRE_THROWS_AS(binomial_crr(make(OptionType::Call, Exercise::European, 0.0, 100, 100, 0.05, 5.0, 10.0), 5000),
                      std::invalid_argument);
}

TEST_CASE("invalid steps throw") {
    REQUIRE_THROWS_AS(binomial_crr(make(OptionType::Call), 0), std::invalid_argument);
}

TEST_CASE("zero vol is deterministic and finite") {
    PriceResult eu = binomial_crr(make(OptionType::Call, Exercise::European, 0.0, 110, 100, 0.05, 0.0), 100);
    REQUIRE(std::abs(eu.price - (110.0 - 100.0 * std::exp(-0.05))) < 1e-12);
    PriceResult am = binomial_crr(make(OptionType::Put, Exercise::American, 0.0, 80, 100, 0.05, 0.0), 100);
    REQUIRE(std::isfinite(am.price));
    REQUIRE(am.price >= 20.0 - 1e-12);
}
