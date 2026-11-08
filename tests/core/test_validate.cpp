#include <catch2/catch_test_macros.hpp>
#include <limits>
#include <stdexcept>
#include <string>
#include "optionpricer/types.hpp"

using namespace optionpricer;

static Option valid() {
    return Option{100.0, 100.0, 0.05, 0.2, 1.0, 0.0, OptionType::Call, Exercise::European};
}

TEST_CASE("valid option does not throw") {
    REQUIRE_NOTHROW(validate(valid()));
}
TEST_CASE("negative volatility rejected") {
    Option o = valid(); o.vol = -0.1;
    REQUIRE_THROWS_AS(validate(o), std::invalid_argument);
}
TEST_CASE("zero spot rejected") {
    Option o = valid(); o.spot = 0.0;
    REQUIRE_THROWS_AS(validate(o), std::invalid_argument);
}
TEST_CASE("negative strike rejected") {
    Option o = valid(); o.strike = -1.0;
    REQUIRE_THROWS_AS(validate(o), std::invalid_argument);
}
TEST_CASE("negative expiry rejected") {
    Option o = valid(); o.expiry = -1.0;
    REQUIRE_THROWS_AS(validate(o), std::invalid_argument);
}
TEST_CASE("error message names the bad field") {
    Option o = valid(); o.vol = -0.1;
    try { validate(o); FAIL("expected throw"); }
    catch (const std::invalid_argument& e) {
        REQUIRE(std::string(e.what()).find("vol") != std::string::npos);
    }
}

TEST_CASE("non-finite rate or dividend yield rejected") {
    Option o = valid(); o.rate = std::numeric_limits<double>::quiet_NaN();
    REQUIRE_THROWS_AS(validate(o), std::invalid_argument);
    Option p = valid(); p.div_yield = std::numeric_limits<double>::infinity();
    REQUIRE_THROWS_AS(validate(p), std::invalid_argument);
}
TEST_CASE("infinite or NaN spot, strike, vol, expiry rejected") {
    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();
    for (double bad : {inf, nan}) {
        Option a = valid(); a.spot = bad;
        Option b = valid(); b.strike = bad;
        Option c = valid(); c.vol = bad;
        Option d = valid(); d.expiry = bad;
        REQUIRE_THROWS_AS(validate(a), std::invalid_argument);
        REQUIRE_THROWS_AS(validate(b), std::invalid_argument);
        REQUIRE_THROWS_AS(validate(c), std::invalid_argument);
        REQUIRE_THROWS_AS(validate(d), std::invalid_argument);
    }
}
TEST_CASE("negative rate is accepted") {
    Option o = valid(); o.rate = -0.01;
    REQUIRE_NOTHROW(validate(o));
}
