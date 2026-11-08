# Option Pricing Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build Black-Scholes, Binomial and Monte Carlo option pricers in a C++17 core with a Python reference and harness, then port them to OCaml.

**Architecture:** A dependency-free C++ library exposes one free function per model over a shared `Option` struct. A pure-Python reference (numpy only) re-implements each model independently. Both, and later OCaml, are validated against one shared `golden/vectors.json`. pybind11 exposes the C++ core to the Python harness for cross-checks, plots and benchmarks.

**Tech Stack:** C++17, CMake, Catch2 v3 (tests only), pybind11, Python 3.10+, numpy, pytest, matplotlib, OCaml with dune and yojson.

**Spec:** `docs/superpowers/specs/2026-11-08-option-pricing-model-design.md`

## Global Constraints

- C++17 core with no external dependencies (Catch2 and pybind11 only in tests and bindings).
- Model: one-factor GBM, `S(t+dt) = S(t) * exp((r - q - sigma^2/2) dt + sigma sqrt(dt) Z)`; constant r and sigma; continuous dividend yield q only; no stochastic volatility.
- Scope: European (all three models) and American (Binomial only); Greeks are delta, gamma, vega. Vega is per 1.00 change in sigma.
- Invalid inputs rejected up front with explicit errors: sigma < 0, S <= 0, K <= 0, T < 0, N < 1, paths < 1.
- Edge cases (T = 0, sigma = 0) return intrinsic value or the discounted deterministic payoff, never NaN.
- Binomial is Cox-Ross-Rubinstein: `u = exp(sigma sqrt(dt))`, `d = 1/u`, `p = (exp((r - q) dt) - d) / (u - d)`.
- Monte Carlo: seedable RNG, antithetic variates, reports standard error and 95% confidence interval, European only.
- Tolerances: Binomial vs Black-Scholes 1e-2 absolute at N = 5000; Monte Carlo within 3 standard errors at a fixed seed.
- Phase order is strict: C++ and Python pass everything before OCaml starts. OCaml order: Black-Scholes, Binomial, Monte Carlo (Monte Carlo is first to drop).

## Review Focus

1. Deep in/out-of-the-money options: price near zero, parity still holds, no NaN. (Task 3)
2. Tiny T or sigma (T = 1e-8, sigma = 1e-6): finite result equal to the deterministic payoff. (Task 3)
3. Binomial step count too low for the drift (`p` outside [0,1]): clear error, not a silent bad price. (Task 4)
4. Monte Carlo with `paths < 2`: rejected, since standard error is undefined. (Task 5)
5. Negative risk-free rate: accepted by all models and still arbitrage-consistent (parity holds). (Task 3)

---

### Task 1: Scaffold, shared types, validation

**Files:**
- Create: `CMakeLists.txt`, `core/include/optionpricer/types.hpp`, `core/src/validate.cpp`, `tests/core/test_validate.cpp`, `.gitignore`

**Interfaces:**
- Produces (namespace `optionpricer`):
  - `enum class OptionType { Call, Put }`, `enum class Exercise { European, American }`
  - `struct Option { double spot, strike, rate, vol, expiry, div_yield = 0.0; OptionType type; Exercise style = Exercise::European; }`
  - `struct Greeks { double delta, gamma, vega; }`
  - `struct PriceResult { double price; std::optional<Greeks> greeks; double std_error = 0.0; }`
  - `void validate(const Option&)` throws `std::invalid_argument` with a message naming the bad field.

- [x] **Step 1: Write failing tests** in `test_validate.cpp`: one `TEST_CASE` per rejected input (sigma = -0.1, S = 0, K = -1, T = -1) expecting `std::invalid_argument`, plus one valid option expecting no throw.
- [x] **Step 2: Run** `cmake -B build && cmake --build build && ctest --test-dir build` — Expected: build fails or tests FAIL (`validate` undefined).
- [x] **Step 3: Implement** `validate` in `validate.cpp`; define the types in `types.hpp`; CMake builds `optionpricer_core` as a static library and a Catch2 test target via FetchContent.
- [x] **Step 4: Run** the same command — Expected: all tests PASS.
- [x] **Step 5: Commit** — `git init`, then `git add . && git commit -m "feat: scaffold core, shared types, validation"`.

### Task 2: Python reference Black-Scholes and golden vectors

**Files:**
- Create: `python/optionpricer_ref/__init__.py`, `python/optionpricer_ref/types.py`, `python/optionpricer_ref/bs.py`, `python/tools/make_golden.py`, `golden/vectors.json`, `python/tests/test_bs_ref.py`, `python/tests/golden.py`

**Interfaces:**
- Produces:
  - `types.Option` dataclass with the same fields and defaults as the C++ struct (`type` is `"call"` or `"put"`, `style` is `"european"` or `"american"`).
  - `bs.black_scholes(opt: Option) -> dict` with keys `price, delta, gamma, vega`.
  - `golden.load_cases() -> list[dict]`. Each case: `id`, `option` (fields above), `european: {price, delta, gamma, vega}`, optional `american: {price}`, `tol`, `source`.
  - `make_golden.py` regenerates all derived entries; textbook entries are hand-written inputs.

- [x] **Step 1: Write failing test** `test_bs_ref.py::test_hull_textbook`: Hull example (S=42, K=40, r=0.10, sigma=0.20, T=0.5, q=0) gives call 4.76 and put 0.81, each within 5e-3. Add `test_put_call_parity` over 20 random valid options with q > 0, tolerance 1e-10.
- [x] **Step 2: Run** `pytest python/tests/test_bs_ref.py -v` — Expected: FAIL (module missing).
- [x] **Step 3: Implement** `black_scholes` using `math.erf` for the normal CDF (no scipy); gamma and vega analytic with q.
- [x] **Step 4: Run** the same command — Expected: PASS.
- [x] **Step 5: Implement** `make_golden.py` producing `vectors.json` with 12 cases: the Hull case (`tol` 5e-3, source `hull`) and 11 derived European cases spanning ITM/ATM/OTM, q = 0 and q > 0, and a negative rate (`tol` 1e-9, source `python-ref`).
- [x] **Step 6: Commit** — `git add python golden && git commit -m "feat: python Black-Scholes reference and golden vectors"`.

### Task 3: C++ Black-Scholes

**Files:**
- Create: `core/include/optionpricer/black_scholes.hpp`, `core/src/black_scholes.cpp`, `tests/core/test_black_scholes.cpp`, `tests/core/golden_loader.hpp`

**Interfaces:**
- Consumes: types and `validate` from Task 1; `golden/vectors.json` from Task 2.
- Produces: `PriceResult black_scholes(const Option&)` (European only; throws `std::invalid_argument` if `style == American`). `golden_loader.hpp` provides `std::vector<GoldenCase> load_golden(const std::string& path)`; add `nlohmann/json` single header to tests only via FetchContent.

- [x] **Step 1: Write failing tests:** `golden_european_cases` (every golden case matches price, delta, gamma, vega within the case `tol`); `put_call_parity` (`C - P == S e^{-qT} - K e^{-rT}` within 1e-10); Review Focus tests: `deep_otm_not_nan` (S=100, K=1000, T=0.1: price finite, >= 0, < 1e-12), `tiny_expiry_and_vol` (T=1e-8 and sigma=1e-6 return intrinsic/deterministic payoff), `negative_rate_parity` (r=-0.01).
- [x] **Step 2: Run** `ctest --test-dir build -R black_scholes` — Expected: FAIL (undefined).
- [x] **Step 3: Implement** `black_scholes` with `erfc`-based normal CDF; short-circuit T = 0 or sigma = 0 to the deterministic payoff `max(±(S e^{-qT} - K e^{-rT}), 0)`.
- [x] **Step 4: Run** the same command — Expected: PASS.
- [x] **Step 5: Commit** — `git commit -am "feat: C++ Black-Scholes with golden-vector tests"`.

### Task 4: Binomial (C++ and Python reference)

**Files:**
- Create: `core/include/optionpricer/binomial.hpp`, `core/src/binomial.cpp`, `tests/core/test_binomial.cpp`, `python/optionpricer_ref/binomial.py`, `python/tests/test_binomial_ref.py`
- Modify: `python/tools/make_golden.py` (add American cases), `golden/vectors.json` (regenerate)

**Interfaces:**
- Consumes: Task 1 types and `black_scholes`.
- Produces: `PriceResult binomial_crr(const Option&, int steps)`; throws `std::invalid_argument` if `steps < 1` or if `p` falls outside [0,1]. Python: `binomial.binomial_crr(opt: Option, steps: int) -> dict` (`price, delta, gamma, vega`; numpy-vectorized backward induction). Delta and gamma come from tree nodes at steps 1 and 2; vega by central difference on sigma with h = 1e-3.

- [x] **Step 1: Write failing tests (C++):** `converges_to_black_scholes` (N=5000, within 1e-2, call and put); `american_put_ge_european_put`; `american_ge_intrinsic`; `american_call_equals_european_call_when_q_zero` (within 1e-9 at the same N); `greeks_match_black_scholes` (N=5000, delta 1e-3, gamma 1e-3, vega 1e-1); `golden_american_cases`; Review Focus: `p_out_of_range_throws` (r=0.5, sigma=0.01, T=1, N=2).
- [x] **Step 2: Write the matching Python tests** in `test_binomial_ref.py` (convergence, American >= European, golden cases).
- [x] **Step 3: Run** `ctest --test-dir build -R binomial` and `pytest python/tests/test_binomial_ref.py` — Expected: FAIL.
- [x] **Step 4: Implement** `binomial_crr` (C++, single reusable value array of size N+1, early-exercise `max` at each node for American) and the Python equivalent; extend `make_golden.py` with 4 American put and 2 American call-with-q cases computed by the Python reference at N = 20000 (`tol` 1e-2, source `python-ref-N20000`); regenerate `vectors.json`.
- [x] **Step 5: Run** both commands — Expected: PASS.
- [x] **Step 6: Commit** — `git add -A && git commit -m "feat: binomial CRR in C++ and Python with American exercise"`.

### Task 5: Monte Carlo (C++ and Python reference)

**Files:**
- Create: `core/include/optionpricer/monte_carlo.hpp`, `core/src/monte_carlo.cpp`, `tests/core/test_monte_carlo.cpp`, `python/optionpricer_ref/mc.py`, `python/tests/test_mc_ref.py`

**Interfaces:**
- Consumes: Task 1 types, `black_scholes`.
- Produces: `struct McConfig { std::uint64_t paths; std::uint64_t seed; bool antithetic = true; }`; `PriceResult monte_carlo(const Option&, const McConfig&)` with `std_error` set; throws `std::invalid_argument` if `paths < 2` or `style == American`. Python: `mc.monte_carlo(opt, paths, seed, antithetic=True) -> dict` with `price, std_error, ci95, delta, gamma, vega`. Terminal-price sampling only (no path storage). With antithetic, standard error is computed over pair means. Greeks by bump-and-reprice with common random numbers: spot bump 1% of S, sigma bump 1e-3.

- [x] **Step 1: Write failing tests (C++):** `within_three_se_of_black_scholes` (200000 paths, seed 42, call and put, with and without antithetic); `deterministic_given_seed`; `antithetic_reduces_std_error`; `greeks_close_to_black_scholes` (delta 3e-2, vega 1.0, gamma 5e-2 as documented loose bounds); Review Focus: `paths_below_two_throws`.
- [x] **Step 2: Write matching Python tests** in `test_mc_ref.py`.
- [x] **Step 3: Run** `ctest --test-dir build -R monte_carlo` and `pytest python/tests/test_mc_ref.py` — Expected: FAIL.
- [x] **Step 4: Implement** both (`std::mt19937_64` with `std::normal_distribution<double>` in C++; `numpy.random.default_rng(seed)` in Python).
- [x] **Step 5: Run** both commands — Expected: PASS.
- [x] **Step 6: Commit** — `git add -A && git commit -m "feat: Monte Carlo with antithetic variates and standard error"`.

### Task 6: pybind11 bindings and cross-implementation tests

**Files:**
- Create: `bindings/module.cpp`, `python/tests/test_cross_impl.py`
- Modify: `CMakeLists.txt` (add `optionpricer_cpp` module target)

**Interfaces:**
- Consumes: all C++ functions above.
- Produces: Python module `optionpricer_cpp` exposing `black_scholes(option_dict)`, `binomial_crr(option_dict, steps)`, `monte_carlo(option_dict, paths, seed, antithetic=True)`, each returning the same dict shape as the Python reference.

- [x] **Step 1: Write failing tests:** `test_cpp_matches_reference_on_golden` (all golden cases, BS and Binomial identical to reference within 1e-9 / 1e-6 at equal N); `test_mc_cpp_within_3se_of_bs`; `test_invalid_input_raises_valueerror`.
- [x] **Step 2: Run** `pytest python/tests/test_cross_impl.py -v` — Expected: FAIL (module not found).
- [x] **Step 3: Implement** the bindings; map `std::invalid_argument` to `ValueError`.
- [x] **Step 4: Run** `cmake --build build && PYTHONPATH=build pytest python/tests -v` — Expected: all PASS.
- [x] **Step 5: Commit** — `git add -A && git commit -m "feat: pybind11 bindings and cross-implementation tests"`.

### Task 7: Convergence plots and benchmarks

**Files:**
- Create: `python/tools/plot_convergence.py`, `python/tools/benchmark.py`, `docs/results/` (output PNGs and `benchmarks.md`)

**Interfaces:**
- Consumes: `optionpricer_cpp` and `optionpricer_ref`.
- Produces: `docs/results/binomial_convergence.png` (error vs N, log scale, shows CRR oscillation), `docs/results/mc_convergence.png` (error and standard error vs paths), `docs/results/benchmarks.md` (table: Monte Carlo paths/sec with and without antithetic, Binomial steps/sec, C++ vs Python).

- [x] **Step 1: Write failing test** `python/tests/test_tools_smoke.py`: running each tool with `--quick` exits 0 and creates its output file.
- [x] **Step 2: Run** `pytest python/tests/test_tools_smoke.py` — Expected: FAIL.
- [x] **Step 3: Implement** both tools with a `--quick` flag (small N and path counts) and a full mode for README numbers.
- [x] **Step 4: Run** the smoke test — Expected: PASS; then run both tools in full mode and inspect the outputs.
- [x] **Step 5: Commit** — `git add -A && git commit -m "feat: convergence plots and benchmarks"`.

### Task 8: OCaml port - DESCOPED (not implemented; C++ and Python shipped first, as planned)

**Files:**
- Create: `ocaml/dune-project`, `ocaml/lib/{types,black_scholes,binomial,monte_carlo}.ml`, `ocaml/test/test_golden.ml`

**Interfaces:**
- Consumes: `golden/vectors.json`.
- Produces: `Black_scholes.price : Types.option_ -> Types.result`, `Binomial.price : Types.option_ -> steps:int -> Types.result`, `Monte_carlo.price : Types.option_ -> paths:int -> seed:int -> Types.result`, with the same semantics, errors (`Invalid_argument`) and Greek conventions as the C++ core.

- [ ] **Step 1: Write failing test** `test_golden.ml` for Black-Scholes (all European golden cases within `tol`) and run `dune test` — Expected: FAIL.
- [ ] **Step 2: Implement** Black-Scholes; run `dune test` — Expected: PASS; commit `feat: OCaml Black-Scholes`.
- [ ] **Step 3: Repeat** for Binomial (European and American golden cases, convergence test at N=5000); commit `feat: OCaml binomial`.
- [ ] **Step 4: Repeat** for Monte Carlo (within 3 standard errors of Black-Scholes at a fixed seed; exact RNG parity with C++ is not required); commit `feat: OCaml Monte Carlo`. Drop this step if time is short.

### Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write** the README: one-paragraph purpose, build and test commands for C++, Python and OCaml, the benchmark table and both plots from `docs/results/`, a design-decisions section (why CRR, why antithetic, why shared golden vectors), assumptions and limits from the spec, and a "what I would do next" section (stochastic volatility, discrete dividends, implied volatility).
- [ ] **Step 2: Verify** by following the README's commands from a clean clone; Expected: every command in it succeeds.
- [ ] **Step 3: Commit** — `git add README.md && git commit -m "docs: README with results and design notes"`.

---

**Self-review notes:** every spec requirement maps to a task (models: 3-5; American and Greeks: 4-5; bindings, reference, golden vectors: 2, 6; plots and benchmarks: 7; OCaml: 8; README: 9; error handling and edge cases: 1, 3-5). Signatures are consistent across tasks (`Option`, `PriceResult`, `McConfig`, `binomial_crr`, `monte_carlo`).
