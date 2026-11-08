"""Regenerate golden/vectors.json from the pure-Python reference.

Textbook cases (source 'hull') are hand-written inputs with published prices.
Derived cases (source 'python-ref') come from the reference implementations.
American cases are added by Task 4 (see AMERICAN_CASES below).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from optionpricer_ref.bs import black_scholes  # noqa: E402
from optionpricer_ref.types import Option  # noqa: E402

OUT = ROOT / "golden" / "vectors.json"


def opt_dict(spot, strike, rate, vol, expiry, type_, div_yield=0.0):
    return dict(spot=spot, strike=strike, rate=rate, vol=vol, expiry=expiry,
                div_yield=div_yield, type=type_)


# Hull, Options, Futures and Other Derivatives: S=42, K=40, r=10%, sigma=20%, T=0.5
HULL = [
    ("hull-call", opt_dict(42, 40, 0.10, 0.20, 0.5, "call"), 4.76),
    ("hull-put", opt_dict(42, 40, 0.10, 0.20, 0.5, "put"), 0.81),
]

DERIVED = [
    ("itm-call", opt_dict(110, 100, 0.05, 0.20, 1.0, "call")),
    ("atm-put", opt_dict(100, 100, 0.05, 0.25, 0.5, "put")),
    ("otm-call", opt_dict(90, 120, 0.03, 0.30, 2.0, "call")),
    ("otm-put", opt_dict(130, 100, 0.02, 0.15, 0.25, "put")),
    ("yield-call", opt_dict(100, 105, 0.05, 0.20, 1.0, "call", 0.03)),
    ("yield-put", opt_dict(100, 95, 0.04, 0.35, 1.5, "put", 0.02)),
    ("negrate-call", opt_dict(100, 100, -0.01, 0.20, 1.0, "call")),
    ("negrate-put", opt_dict(100, 110, -0.02, 0.25, 2.0, "put", 0.01)),
    ("short-expiry-call", opt_dict(100, 100, 0.05, 0.20, 0.02, "call")),
    ("high-vol-put", opt_dict(50, 60, 0.01, 0.80, 1.0, "put")),
]

# Filled in by Task 4: (id, option dict) pairs priced with the N=20000 binomial reference.
AMERICAN_CASES = [
    ("am-put-itm", opt_dict(90, 100, 0.05, 0.20, 1.0, "put")),
    ("am-put-atm", opt_dict(100, 100, 0.05, 0.30, 1.0, "put")),
    ("am-put-otm", opt_dict(110, 100, 0.08, 0.25, 0.5, "put")),
    ("am-put-yield", opt_dict(100, 100, 0.03, 0.20, 2.0, "put", 0.04)),
    ("am-call-yield", opt_dict(100, 95, 0.03, 0.25, 1.0, "call", 0.06)),
    ("am-call-highyield", opt_dict(120, 100, 0.02, 0.30, 1.5, "call", 0.08)),
]
AMERICAN_STEPS = 20000


def european_block(o):
    return black_scholes(Option(**o, style="european"))


def main():
    cases = []
    for cid, o, price in HULL:
        cases.append({"id": cid, "option": o, "european": {"price": price},
                      "tol": 5e-3, "source": "hull"})
    for cid, o in DERIVED:
        cases.append({"id": cid, "option": o, "european": european_block(o),
                      "tol": 1e-9, "source": "python-ref"})
    if AMERICAN_CASES:
        from optionpricer_ref.binomial import binomial_crr
        for cid, o in AMERICAN_CASES:
            am = binomial_crr(Option(**o, style="american"), AMERICAN_STEPS, compute_greeks=False)
            cases.append({"id": cid, "option": o, "european": european_block(o),
                          "american": {"price": am["price"]}, "tol": 1e-9,
                          "american_tol": 1e-2, "source": f"python-ref-N{AMERICAN_STEPS}"})
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"cases": cases}, f, indent=2)
        f.write("\n")
    print(f"wrote {len(cases)} cases to {OUT}")


if __name__ == "__main__":
    main()
