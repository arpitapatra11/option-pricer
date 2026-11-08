#include "optionpricer/binomial.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

#include "optionpricer/black_scholes.hpp"

namespace optionpricer {
namespace {

struct TreeResult {
    double price = 0.0;
    double v1[2] = {0.0, 0.0};  // option values at step 1 (down, up)
    double v2[3] = {0.0, 0.0, 0.0};  // option values at step 2 (dd, ud, uu)
    bool have_nodes = false;
};

double sign_of(OptionType t) { return t == OptionType::Call ? 1.0 : -1.0; }

TreeResult run_tree(const Option& opt, int steps, double vol) {
    const double sign = sign_of(opt.type);
    const bool american = opt.style == Exercise::American;
    const double dt = opt.expiry / steps;
    const double h = vol * std::sqrt(dt);
    // The deepest node is S * exp(h * steps); beyond ~exp(600) prices overflow to inf/NaN.
    if (!(h * steps < 600.0))
        throw std::invalid_argument("vol * sqrt(expiry * steps) too large: tree prices would overflow");
    const double u = std::exp(h);
    const double d = 1.0 / u;
    const double disc = std::exp(-opt.rate * dt);
    const double p = (std::exp((opt.rate - opt.div_yield) * dt) - d) / (u - d);
    if (!(p >= 0.0 && p <= 1.0))
        throw std::invalid_argument("steps too low: risk-neutral probability outside [0, 1]");

    // upow[m + steps] = u^m for m in [-steps, steps].
    std::vector<double> upow(2 * static_cast<size_t>(steps) + 1);
    for (int m = -steps; m <= steps; ++m) upow[static_cast<size_t>(m + steps)] = std::exp(h * m);

    std::vector<double> v(static_cast<size_t>(steps) + 1);
    for (int j = 0; j <= steps; ++j) {
        const double st = opt.spot * upow[static_cast<size_t>(2 * j)];
        v[static_cast<size_t>(j)] = std::max(sign * (st - opt.strike), 0.0);
    }

    TreeResult out;
    const bool want_nodes = steps >= 2;
    if (steps == 2 && want_nodes) std::copy(v.begin(), v.begin() + 3, out.v2);
    for (int i = steps - 1; i >= 0; --i) {
        for (int j = 0; j <= i; ++j) {
            double val = disc * (p * v[static_cast<size_t>(j) + 1] + (1.0 - p) * v[static_cast<size_t>(j)]);
            if (american) {
                const double st = opt.spot * upow[static_cast<size_t>(2 * j - i + steps)];
                val = std::max(val, sign * (st - opt.strike));
            }
            v[static_cast<size_t>(j)] = val;
        }
        if (want_nodes && i == 2) std::copy(v.begin(), v.begin() + 3, out.v2);
        if (want_nodes && i == 1) std::copy(v.begin(), v.begin() + 2, out.v1);
    }
    out.price = v[0];
    out.have_nodes = want_nodes;
    return out;
}

PriceResult degenerate(const Option& opt, int steps) {
    if (opt.style == Exercise::European || opt.expiry == 0.0) return deterministic_payoff(opt);
    // American, vol == 0: best discounted deterministic payoff over the step grid.
    const double sign = sign_of(opt.type);
    double best = 0.0;
    for (int i = 0; i <= steps; ++i) {
        const double t = opt.expiry * i / steps;
        const double payoff = sign * (opt.spot * std::exp((opt.rate - opt.div_yield) * t) - opt.strike);
        best = std::max(best, std::exp(-opt.rate * t) * std::max(payoff, 0.0));
    }
    PriceResult out;
    out.price = best;
    return out;
}

}  // namespace

PriceResult binomial_crr(const Option& opt, int steps, bool compute_greeks) {
    validate(opt);
    if (steps < 1) throw std::invalid_argument("steps must be >= 1");
    if (opt.expiry == 0.0 || opt.vol == 0.0) return degenerate(opt, steps);

    TreeResult base = run_tree(opt, steps, opt.vol);
    PriceResult out;
    out.price = base.price;
    if (!compute_greeks || !base.have_nodes) return out;

    const double dt = opt.expiry / steps;
    const double u = std::exp(opt.vol * std::sqrt(dt));
    const double d = 1.0 / u;
    const double s_u = opt.spot * u, s_d = opt.spot * d;
    const double s_uu = opt.spot * u * u, s_dd = opt.spot * d * d;

    Greeks g{};
    g.delta = (base.v1[1] - base.v1[0]) / (s_u - s_d);
    const double up_slope = (base.v2[2] - base.v2[1]) / (s_uu - opt.spot);
    const double down_slope = (base.v2[1] - base.v2[0]) / (opt.spot - s_dd);
    g.gamma = (up_slope - down_slope) / (0.5 * (s_uu - s_dd));

    const double bump = 1e-3;
    double lo = opt.vol - bump > 0.0 ? opt.vol - bump : opt.vol;
    const double hi = opt.vol + bump;
    double price_lo = base.price;
    if (lo != opt.vol) {
        // Lowering vol can push p outside [0, 1] even though the base tree is valid;
        // fall back to a forward difference instead of losing the price.
        try {
            price_lo = run_tree(opt, steps, lo).price;
        } catch (const std::invalid_argument&) {
            lo = opt.vol;
        }
    }
    g.vega = (run_tree(opt, steps, hi).price - price_lo) / (hi - lo);
    out.greeks = g;
    return out;
}

}  // namespace optionpricer
