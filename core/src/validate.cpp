#include <cmath>
#include <stdexcept>

#include "optionpricer/types.hpp"

namespace optionpricer {

void validate(const Option& opt) {
    // Comparisons are written so that NaN fails them.
    // Infinity is rejected too: it would otherwise flow through to NaN prices.
    if (!(opt.spot > 0.0 && std::isfinite(opt.spot))) throw std::invalid_argument("spot must be finite and > 0");
    if (!(opt.strike > 0.0 && std::isfinite(opt.strike))) throw std::invalid_argument("strike must be finite and > 0");
    if (!(opt.vol >= 0.0 && std::isfinite(opt.vol))) throw std::invalid_argument("vol must be finite and >= 0");
    if (!(opt.expiry >= 0.0 && std::isfinite(opt.expiry))) throw std::invalid_argument("expiry must be finite and >= 0");
    if (!std::isfinite(opt.rate)) throw std::invalid_argument("rate must be finite");
    if (!std::isfinite(opt.div_yield)) throw std::invalid_argument("div_yield must be finite");
}

}  // namespace optionpricer
