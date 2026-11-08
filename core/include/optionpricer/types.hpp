#pragma once
#include <optional>

namespace optionpricer {

enum class OptionType { Call, Put };
enum class Exercise { European, American };

struct Option {
    double spot;
    double strike;
    double rate;
    double vol;
    double expiry;
    double div_yield = 0.0;
    OptionType type;
    Exercise style = Exercise::European;
};

// Vega is per 1.00 change in volatility.
struct Greeks {
    double delta;
    double gamma;
    double vega;
};

struct PriceResult {
    double price;
    std::optional<Greeks> greeks;
    double std_error = 0.0;
};

// Throws std::invalid_argument naming the offending field.
void validate(const Option& opt);

}  // namespace optionpricer
