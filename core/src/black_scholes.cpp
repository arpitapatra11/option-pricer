#include "optionpricer/black_scholes.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace optionpricer {
namespace {

constexpr double kInvSqrt2 = 0.70710678118654752440;
constexpr double kInvSqrt2Pi = 0.39894228040143267794;

double cdf(double x) { return 0.5 * std::erfc(-x * kInvSqrt2); }
double pdf(double x) { return kInvSqrt2Pi * std::exp(-0.5 * x * x); }

double sign_of(OptionType t) { return t == OptionType::Call ? 1.0 : -1.0; }

}  // namespace

PriceResult deterministic_payoff(const Option& opt) {
    const double sign = sign_of(opt.type);
    const double fwd = opt.spot * std::exp(-opt.div_yield * opt.expiry) -
                       opt.strike * std::exp(-opt.rate * opt.expiry);
    const double value = sign * fwd;
    PriceResult out;
    out.price = std::max(value, 0.0);
    out.greeks = Greeks{value > 0.0 ? sign * std::exp(-opt.div_yield * opt.expiry) : 0.0, 0.0, 0.0};
    return out;
}

PriceResult black_scholes(const Option& opt) {
    validate(opt);
    if (opt.style != Exercise::European)
        throw std::invalid_argument("Black-Scholes prices European options only");
    if (opt.expiry == 0.0 || opt.vol == 0.0) return deterministic_payoff(opt);

    const double s = opt.spot, k = opt.strike, r = opt.rate, q = opt.div_yield;
    const double v = opt.vol, t = opt.expiry;
    const double sqrt_t = std::sqrt(t);
    const double d1 = (std::log(s / k) + (r - q + 0.5 * v * v) * t) / (v * sqrt_t);
    const double d2 = d1 - v * sqrt_t;
    const double disc_s = s * std::exp(-q * t);
    const double disc_k = k * std::exp(-r * t);

    PriceResult out;
    Greeks g{};
    if (opt.type == OptionType::Call) {
        out.price = disc_s * cdf(d1) - disc_k * cdf(d2);
        g.delta = std::exp(-q * t) * cdf(d1);
    } else {
        out.price = disc_k * cdf(-d2) - disc_s * cdf(-d1);
        g.delta = -std::exp(-q * t) * cdf(-d1);
    }
    // Deep out-of-the-money, the two terms nearly cancel and rounding can leave a
    // tiny negative value; a European option price is never negative.
    out.price = std::max(out.price, 0.0);
    g.gamma = std::exp(-q * t) * pdf(d1) / (s * v * sqrt_t);
    g.vega = disc_s * pdf(d1) * sqrt_t;
    out.greeks = g;
    return out;
}

}  // namespace optionpricer
