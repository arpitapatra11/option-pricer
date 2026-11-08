#include "optionpricer/monte_carlo.hpp"

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>

#include "optionpricer/black_scholes.hpp"

namespace optionpricer {
namespace {

struct Estimate {
    double price;
    double std_error;
};

// One full simulation with a fresh RNG, so every call sees the same random numbers.
Estimate simulate(const Option& opt, const McConfig& cfg, double spot, double vol) {
    const double sign = opt.type == OptionType::Call ? 1.0 : -1.0;
    const double t = opt.expiry;
    const double drift = (opt.rate - opt.div_yield - 0.5 * vol * vol) * t;
    const double diffusion = vol * std::sqrt(t);
    const double disc = std::exp(-opt.rate * t);
    const std::uint64_t n = cfg.antithetic ? cfg.paths / 2 : cfg.paths;

    std::mt19937_64 rng(cfg.seed);
    std::normal_distribution<double> normal(0.0, 1.0);

    auto payoff = [&](double z) {
        return std::max(sign * (spot * std::exp(drift + diffusion * z) - opt.strike), 0.0);
    };

    // Welford running mean / variance of the per-sample payoff.
    double mean = 0.0, m2 = 0.0;
    for (std::uint64_t i = 1; i <= n; ++i) {
        const double z = normal(rng);
        const double x = cfg.antithetic ? 0.5 * (payoff(z) + payoff(-z)) : payoff(z);
        const double delta = x - mean;
        mean += delta / static_cast<double>(i);
        m2 += delta * (x - mean);
    }
    const double var = m2 / static_cast<double>(n - 1);
    return {disc * mean, disc * std::sqrt(var / static_cast<double>(n))};
}

}  // namespace

PriceResult monte_carlo(const Option& opt, const McConfig& cfg) {
    validate(opt);
    if (opt.style != Exercise::European)
        throw std::invalid_argument("Monte Carlo prices European options only");
    const std::uint64_t n = cfg.antithetic ? cfg.paths / 2 : cfg.paths;
    if (cfg.paths < 2 || n < 2)
        throw std::invalid_argument("too few paths: need at least 2 independent samples "
                                    "(4 paths with antithetic variates)");

    if (opt.expiry == 0.0 || opt.vol == 0.0) {
        PriceResult det = deterministic_payoff(opt);
        det.std_error = 0.0;
        if (!cfg.compute_greeks) det.greeks.reset();
        return det;
    }

    const Estimate base = simulate(opt, cfg, opt.spot, opt.vol);
    PriceResult out;
    out.price = base.price;
    out.std_error = base.std_error;
    if (!cfg.compute_greeks) return out;

    const double h = 0.01 * opt.spot;
    const double up = simulate(opt, cfg, opt.spot + h, opt.vol).price;
    const double down = simulate(opt, cfg, opt.spot - h, opt.vol).price;
    Greeks g{};
    g.delta = (up - down) / (2.0 * h);
    g.gamma = (up - 2.0 * base.price + down) / (h * h);

    const double bump = 1e-3;
    const double lo = opt.vol - bump > 0.0 ? opt.vol - bump : opt.vol;
    const double hi = opt.vol + bump;
    g.vega = (simulate(opt, cfg, opt.spot, hi).price - simulate(opt, cfg, opt.spot, lo).price) / (hi - lo);
    out.greeks = g;
    return out;
}

}  // namespace optionpricer
