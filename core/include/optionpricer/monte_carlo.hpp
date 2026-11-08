#pragma once
#include <cstdint>

#include "optionpricer/types.hpp"

namespace optionpricer {

struct McConfig {
    std::uint64_t paths;  // total simulated paths
    std::uint64_t seed;
    bool antithetic = true;
    bool compute_greeks = true;
};

// European Monte Carlo under GBM (terminal price only).
//  * Antithetic variates pair each draw Z with -Z; the standard error is then taken
//    over the pair means (paths / 2 independent samples).
//  * With antithetic variates an odd path count is rounded down to an even one
//    (paths / 2 pairs are simulated), so paths = 1001 behaves like 1000.
//  * std_error is the standard error of the discounted price estimate.
//  * Greeks are bump-and-reprice with common random numbers (same seed per
//    evaluation): spot bump 1% of spot, vol bump 1e-3 (forward when vol <= 1e-3).
// Throws std::invalid_argument for invalid input, American exercise, or when fewer
// than two independent samples would be drawn (paths < 2, or paths < 4 with
// antithetic variates), since the standard error would be undefined.
// When expiry == 0 or vol == 0 the deterministic payoff is returned with std_error 0.
PriceResult monte_carlo(const Option& opt, const McConfig& cfg);

}  // namespace optionpricer
