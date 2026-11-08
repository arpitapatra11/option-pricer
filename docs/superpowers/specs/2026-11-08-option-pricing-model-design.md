# Option Pricing Model: Design Spec

Date: 2026-11-08
Status: Implemented (C++ and Python). OCaml port descoped.

## 1. Purpose and success criteria

**Purpose.** Project #4 (Option Pricing Model), built as a portfolio piece for the Jane Street Insight program to demonstrate quant dev ability.

**Success criteria**
- Three pricing models (Black-Scholes, Binomial, Monte Carlo) implemented in a C++17 core and independently in Python.
- All implementations agree with each other and with shared golden test vectors within stated tolerances.
- Reviewer can read the README and see correctness evidence (convergence plots), performance evidence (benchmarks) and design reasoning in a few minutes.
- A finished C++/Python project ships even if the OCaml port is incomplete.

## 2. Scope

**In scope (option B)**
- European calls and puts under Black-Scholes, Binomial and Monte Carlo.
- American calls and puts under Binomial.
- Greeks: delta, gamma, vega.
- Python bindings, pure-Python reference, golden vectors, convergence plots, benchmarks.
- OCaml port (Phase 3), validated against the same golden vectors.

**Out of scope (optional stretch, not committed)**
- Implied volatility solver.
- Comparison against real market quotes.

**Modeling assumptions**
- One-factor geometric Brownian motion: S(t+dt) = S(t) * exp((r - q - sigma^2/2) dt + sigma sqrt(dt) Z), Z ~ N(0,1).
- Constant risk-free rate r and constant volatility sigma over the option's life.
- No stochastic volatility.
- Dividends modeled only as a continuous yield q (drift becomes r - q). No discrete dividends.

## 3. Architecture

```
optionpricer/
  core/        C++17 pricing library, no external dependencies
  bindings/    pybind11 wrapper over core
  python/      pure-Python reference implementations, tests, plotting, benchmarks
  golden/      vectors.json, shared by C++, Python and OCaml tests
  ocaml/       Phase 3 port
  docs/        spec, plan, README assets
```

Each model is a self-contained unit with one purpose, a uniform interface and no dependency on the other models.

## 4. Components (C++ core)

**Inputs.** One struct shared by all models: spot S, strike K, rate r, volatility sigma, time to expiry T (years), dividend yield q (default 0), option type (call or put), exercise style (European or American).

**Result.** Price, optional Greeks (delta, gamma, vega), and diagnostics (for example standard error and confidence interval for Monte Carlo, step count for Binomial).

**Black-Scholes.** Closed-form European price and analytic Greeks, including continuous yield q. Serves as ground truth.

**Binomial (Cox-Ross-Rubinstein).**
- u = exp(sigma sqrt(dt)), d = 1/u, p = (exp((r - q) dt) - d) / (u - d).
- Configurable step count N. Supports European and American exercise (early-exercise check at each node).
- Delta and gamma read from the first two tree steps. Vega by bump-and-reprice.

**Monte Carlo.**
- European options only. Simulates terminal prices under GBM with a seedable RNG.
- Antithetic variates. Reports standard error and 95% confidence interval.
- Greeks by bump-and-reprice using common random numbers.

**Common interface.** Every model exposes the same pricing call so the harness and tests treat models uniformly. Unsupported combinations (for example American via Monte Carlo) return a clear error.

## 5. Data flow

1. `golden/vectors.json` holds inputs and expected outputs.
2. C++ tests, Python reference tests and (later) OCaml tests all read the same file.
3. The Python harness calls C++ through the bindings, compares against the pure-Python reference and against Black-Scholes.
4. The harness generates convergence plots and the benchmark table used in the README.

## 6. Error handling

- Reject invalid inputs up front with explicit errors: sigma < 0, S <= 0, K <= 0, T < 0, N < 1, paths < 1.
- Edge cases (T = 0, sigma = 0) return intrinsic value (or the discounted deterministic payoff) instead of NaN.
- Monte Carlo is deterministic given a seed.

## 7. Testing

**Correctness**
- Match known textbook reference prices (in golden vectors).
- Put-call parity for European options: C - P = S e^(-qT) - K e^(-rT).
- Binomial European price converges to Black-Scholes as N grows (tolerance 1e-2 absolute at N = 5000 for standard test cases).
- Monte Carlo price lies within 3 standard errors of Black-Scholes at a fixed seed.
- American put >= European put; American price >= intrinsic value.
- With q = 0, American call equals European call.
- Greeks agree with finite-difference checks against Black-Scholes.

**Cross-implementation**
- C++, Python reference and OCaml must all match the golden vectors within tolerance.

**Performance**
- Benchmarks: Monte Carlo paths per second (with and without antithetic variates), Binomial steps per second, C++ versus pure Python.

## 8. Phases

1. **C++ core** with all three models and unit tests.
2. **Python layer:** bindings, pure-Python reference, golden vectors, convergence plots, benchmarks.
3. **OCaml port,** strictly after phases 1-2 pass. Order: Black-Scholes, Binomial, Monte Carlo. Monte Carlo is the first item to drop if time is short.
4. **README:** results, design trade-offs, and a "what I would do next" section (stochastic volatility, discrete dividends, implied volatility).

## 9. Risks

- OCaml port scope creep: mitigated by strict phase ordering and golden-vector validation.
- Monte Carlo gamma noise under bump-and-reprice: mitigated by common random numbers and a documented tolerance.
- Binomial oscillation in convergence: documented in plots rather than hidden.
