#include <pybind11/pybind11.h>

#include <stdexcept>
#include <string>

#include "optionpricer/binomial.hpp"
#include "optionpricer/black_scholes.hpp"
#include "optionpricer/monte_carlo.hpp"

namespace py = pybind11;
using namespace optionpricer;

namespace {

// Option dict keys: spot, strike, rate, vol, expiry, type ("call"/"put");
// optional: div_yield (default 0), style ("european"/"american", default "european").
Option parse_option(const py::dict& d) {
    auto num = [&](const char* key) {
        if (!d.contains(key)) throw std::invalid_argument(std::string("missing option field: ") + key);
        return d[key].cast<double>();
    };
    Option o;
    o.spot = num("spot");
    o.strike = num("strike");
    o.rate = num("rate");
    o.vol = num("vol");
    o.expiry = num("expiry");
    o.div_yield = d.contains("div_yield") ? d["div_yield"].cast<double>() : 0.0;

    if (!d.contains("type")) throw std::invalid_argument("missing option field: type");
    const std::string type = d["type"].cast<std::string>();
    if (type == "call") o.type = OptionType::Call;
    else if (type == "put") o.type = OptionType::Put;
    else throw std::invalid_argument("type must be 'call' or 'put'");

    const std::string style = d.contains("style") ? d["style"].cast<std::string>() : "european";
    if (style == "european") o.style = Exercise::European;
    else if (style == "american") o.style = Exercise::American;
    else throw std::invalid_argument("style must be 'european' or 'american'");
    return o;
}

py::dict to_dict(const PriceResult& r) {
    py::dict out;
    out["price"] = r.price;
    out["delta"] = r.greeks ? py::object(py::float_(r.greeks->delta)) : py::none();
    out["gamma"] = r.greeks ? py::object(py::float_(r.greeks->gamma)) : py::none();
    out["vega"] = r.greeks ? py::object(py::float_(r.greeks->vega)) : py::none();
    return out;
}

}  // namespace

PYBIND11_MODULE(optionpricer_cpp, m) {
    m.doc() = "C++ option pricing core (Black-Scholes, CRR binomial, Monte Carlo)";

    m.def("black_scholes", [](const py::dict& opt) { return to_dict(black_scholes(parse_option(opt))); },
          py::arg("option"));

    m.def("binomial_crr",
          [](const py::dict& opt, int steps, bool compute_greeks) {
              return to_dict(binomial_crr(parse_option(opt), steps, compute_greeks));
          },
          py::arg("option"), py::arg("steps"), py::arg("compute_greeks") = true);

    m.def("monte_carlo",
          [](const py::dict& opt, std::uint64_t paths, std::uint64_t seed, bool antithetic,
             bool compute_greeks) {
              PriceResult r = monte_carlo(parse_option(opt), McConfig{paths, seed, antithetic, compute_greeks});
              py::dict out = to_dict(r);
              out["std_error"] = r.std_error;
              out["ci95"] = py::make_tuple(r.price - 1.96 * r.std_error, r.price + 1.96 * r.std_error);
              return out;
          },
          py::arg("option"), py::arg("paths"), py::arg("seed"), py::arg("antithetic") = true,
          py::arg("compute_greeks") = true);
}
