"""Convergence plots: Binomial and Monte Carlo against the Black-Scholes price."""
import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, os.environ.get("OPTIONPRICER_BUILD", str(ROOT / "build")))

import optionpricer_cpp as cpp  # noqa: E402

OPT = {"spot": 100.0, "strike": 100.0, "rate": 0.05, "vol": 0.2, "expiry": 1.0,
       "div_yield": 0.0, "type": "call"}


def binomial_plot(out: Path, quick: bool):
    bs = cpp.black_scholes(OPT)["price"]
    n_fine = list(range(10, 101 if quick else 401))
    n_wide = np.unique(np.logspace(1, 3 if quick else 4, 15 if quick else 40).astype(int))
    err = lambda n: cpp.binomial_crr(OPT, int(n), compute_greeks=False)["price"] - bs  # noqa: E731

    fine = [err(n) for n in n_fine]
    wide = np.array([abs(err(n)) for n in n_wide])

    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4))
    a.plot(n_fine, fine, lw=1)
    a.axhline(0, color="k", lw=0.5)
    a.set_xlabel("steps N")
    a.set_ylabel("binomial price - Black-Scholes")
    a.set_title("CRR error oscillates with N")
    b.loglog(n_wide, wide, "o-", ms=3, label="|error|")
    b.loglog(n_wide, wide[0] * n_wide[0] / n_wide, "--", color="gray", label="~ 1/N")
    b.set_xlabel("steps N")
    b.set_ylabel("|error|")
    b.set_title("Convergence to Black-Scholes (European call)")
    b.legend()
    fig.suptitle("S=100 K=100 r=5% sigma=20% T=1", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "binomial_convergence.png", dpi=130)
    plt.close(fig)


def mc_plot(out: Path, quick: bool):
    bs = cpp.black_scholes(OPT)["price"]
    paths = np.unique(np.logspace(3, 5 if quick else 7, 6 if quick else 12).astype(int))
    seeds = range(1, 6 if quick else 21)  # a single seed's error is one random draw; use many
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for anti, color in ((True, "C0"), (False, "C1")):
        label = "antithetic" if anti else "plain"
        rms, mean_se = [], []
        for n in paths:
            res = [cpp.monte_carlo(OPT, int(n), s, antithetic=anti, compute_greeks=False) for s in seeds]
            rms.append(float(np.sqrt(np.mean([(r["price"] - bs) ** 2 for r in res]))))
            mean_se.append(float(np.mean([r["std_error"] for r in res])))
        ax.loglog(paths, rms, "o", ms=4, color=color, label=f"RMS error ({label})")
        ax.loglog(paths, mean_se, "-", color=color, label=f"mean standard error ({label})")
    ref = cpp.monte_carlo(OPT, int(paths[0]), 1, antithetic=False, compute_greeks=False)["std_error"]
    ax.loglog(paths, ref * np.sqrt(paths[0] / paths), "--", color="gray", label="~ 1/sqrt(paths)")
    ax.set_xlabel("paths")
    ax.set_ylabel("error vs Black-Scholes")
    ax.set_title(f"Monte Carlo convergence (European call, RMS over {len(seeds)} seeds)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "mc_convergence.png", dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="small sizes for smoke testing")
    ap.add_argument("--out", default=str(ROOT / "docs" / "results"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    binomial_plot(out, args.quick)
    mc_plot(out, args.quick)
    print(f"wrote plots to {out}")


if __name__ == "__main__":
    main()
