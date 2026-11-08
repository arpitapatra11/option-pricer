#pragma once
#include <fstream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "optionpricer/types.hpp"

struct GoldenBlock {
    std::optional<double> price, delta, gamma, vega;
};

struct GoldenCase {
    std::string id;
    optionpricer::Option option;  // style defaults to European
    GoldenBlock european;
    std::optional<GoldenBlock> american;
    double tol;
    double american_tol;
    std::string source;
};

inline GoldenBlock parse_block(const nlohmann::json& j) {
    GoldenBlock b;
    if (j.contains("price")) b.price = j["price"].get<double>();
    if (j.contains("delta")) b.delta = j["delta"].get<double>();
    if (j.contains("gamma")) b.gamma = j["gamma"].get<double>();
    if (j.contains("vega")) b.vega = j["vega"].get<double>();
    return b;
}

inline std::vector<GoldenCase> load_golden(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open golden file: " + path);
    nlohmann::json root = nlohmann::json::parse(in);
    std::vector<GoldenCase> out;
    for (const auto& c : root.at("cases")) {
        GoldenCase g;
        g.id = c.at("id").get<std::string>();
        const auto& o = c.at("option");
        g.option.spot = o.at("spot").get<double>();
        g.option.strike = o.at("strike").get<double>();
        g.option.rate = o.at("rate").get<double>();
        g.option.vol = o.at("vol").get<double>();
        g.option.expiry = o.at("expiry").get<double>();
        g.option.div_yield = o.value("div_yield", 0.0);
        g.option.type = o.at("type").get<std::string>() == "call" ? optionpricer::OptionType::Call
                                                                  : optionpricer::OptionType::Put;
        g.option.style = optionpricer::Exercise::European;
        g.european = parse_block(c.at("european"));
        if (c.contains("american")) g.american = parse_block(c["american"]);
        g.tol = c.at("tol").get<double>();
        g.american_tol = c.value("american_tol", g.tol);
        g.source = c.value("source", "");
        out.push_back(g);
    }
    return out;
}
