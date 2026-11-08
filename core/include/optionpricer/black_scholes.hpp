#pragma once
#include "optionpricer/types.hpp"

namespace optionpricer {

// Closed-form European price with analytic Greeks and continuous dividend yield.
// Throws std::invalid_argument for invalid input or for American exercise.
// When expiry == 0 or vol == 0 the discounted deterministic payoff is returned.
PriceResult black_scholes(const Option& opt);

// Discounted deterministic payoff (shared by the other models for degenerate input).
PriceResult deterministic_payoff(const Option& opt);

}  // namespace optionpricer
