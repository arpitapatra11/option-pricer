#pragma once
#include "optionpricer/types.hpp"

namespace optionpricer {

// Cox-Ross-Rubinstein tree, European or American exercise.
//   u = exp(vol*sqrt(dt)), d = 1/u, p = (exp((r-q)*dt) - d) / (u - d)
// Throws std::invalid_argument if steps < 1 or if p falls outside [0, 1]
// (too few steps for the drift/volatility).
// Delta and gamma are read from tree nodes at steps 1 and 2 (steps >= 2);
// vega is a central difference on vol with bump 1e-3 (forward when vol <= 1e-3).
// With compute_greeks == false (or steps < 2) result.greeks is empty.
// When expiry == 0 or vol == 0 the deterministic payoff is used (American: best
// discounted payoff over the step grid).
PriceResult binomial_crr(const Option& opt, int steps, bool compute_greeks = true);

}  // namespace optionpricer
