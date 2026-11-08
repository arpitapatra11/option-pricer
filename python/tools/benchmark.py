"""Throughput benchmarks: C++ core versus the pure-Python (numpy) reference."""
import argparse
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, os.environ.get("OPTIONPRICER_BUILD", str(ROOT / "build")))

import optionpricer_cpp as cpp  # noqa: E402
from optionpricer_ref.binomial import binomial_crr as ref_binomial  # noqa: E402
from optionpricer_ref.mc import monte_carlo as ref_mc  # noqa: E402
from optionpricer_ref.types import Option  # noqa: E402

OPT = {"spot": 100.0, "strike": 100.0, "rate": 0.05, "vol": 0.2, "expiry": 1.0,
       "div_yield": 0.0, "type": "put"}


def best_time(fn, repeats):
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "docs" / "results"))
    args = ap.parse_args()
    paths = 20_000 if args.quick else 2_000_000
    steps = 200 if args.quick else 3000
    repeats = 1 if args.quick else 3
    ref_eu = Option(**OPT)
    ref_am = Option(**OPT, style="american")

    mc_rows = [
        ("C++ antithetic", lambda: cpp.monte_carlo(OPT, paths, 1, True, False)),
        ("C++ plain", lambda: cpp.monte_carlo(OPT, paths, 1, False, False)),
        ("Python (numpy) antithetic", lambda: ref_mc(ref_eu, paths, 1, True, False)),
        ("Python (numpy) plain", lambda: ref_mc(ref_eu, paths, 1, False, False)),
    ]
    bi_rows = [
        ("C++ European", lambda: cpp.binomial_crr(OPT, steps, False)),
        ("C++ American", lambda: cpp.binomial_crr(dict(OPT, style="american"), steps, False)),
        ("Python (numpy) European", lambda: ref_binomial(ref_eu, steps, False)),
        ("Python (numpy) American", lambda: ref_binomial(ref_am, steps, False)),
    ]

    lines = [
        "# Benchmarks", "",
        f"Machine: {platform.platform()}, Python {platform.python_version()}, "
        f"{os.cpu_count()} CPU(s). Best of {repeats} run(s). Indicative numbers, not a rigorous study.", "",
        f"## Monte Carlo ({paths:,} paths, European put, prices only)", "",
        "| Implementation | Time (ms) | Paths / sec |", "|---|---:|---:|",
    ]
    times = {}
    for name, fn in mc_rows:
        t = best_time(fn, repeats)
        times[name] = t
        lines.append(f"| {name} | {t * 1e3:,.1f} | {paths / t:,.0f} |")

    # Paths/sec hides the point of antithetic variates: lower variance at equal paths.
    se_anti = cpp.monte_carlo(OPT, paths, 1, True, False)["std_error"]
    se_plain = cpp.monte_carlo(OPT, paths, 1, False, False)["std_error"]
    var_ratio = (se_plain / se_anti) ** 2
    cost_ratio = (times["C++ plain"] * se_plain ** 2) / (times["C++ antithetic"] * se_anti ** 2)
    lines += ["", "Variance reduction (C++, same path count, seed 1):", "",
              "| Metric | Plain | Antithetic |", "|---|---:|---:|",
              f"| Standard error | {se_plain:.5f} | {se_anti:.5f} |",
              f"| Variance ratio (plain / antithetic) | | {var_ratio:.2f}x |",
              f"| Time to reach equal standard error (plain / antithetic) | | {cost_ratio:.2f}x |"]
    lines += ["", f"## Binomial (N = {steps:,} steps, prices only)", "",
              "| Implementation | Time (ms) | Steps / sec | Node updates / sec |", "|---|---:|---:|---:|"]
    nodes = steps * (steps + 1) / 2
    for name, fn in bi_rows:
        t = best_time(fn, repeats)
        lines.append(f"| {name} | {t * 1e3:,.1f} | {steps / t:,.0f} | {nodes / t:,.0f} |")

    lines += ["", "## Notes", "",
              "- C++ rows are timed through the pybind11 module, so they include a small fixed",
              "  call overhead (dict parsing and result dict); it is negligible at these sizes.",
              "- All Monte Carlo runs are single-threaded.",
              "- C++ Monte Carlo is not much faster than numpy: both are dominated by normal",
              "  random-number generation, and numpy's generator is already compiled code.",
              "  The Binomial rows show the larger C++ advantage (a tight loop that numpy",
              "  can only partly vectorise).",
              "- Antithetic variates use half the normal draws per path, so they are cheaper per path",
              "  and lower-variance; the variance table above is the fair way to compare them."]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmarks.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
