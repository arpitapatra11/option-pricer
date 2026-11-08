"""Loader for the golden vectors shared by C++, Python and OCaml."""
import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "golden" / "vectors.json"


def load_cases(path=GOLDEN_PATH):
    with open(path) as f:
        return json.load(f)["cases"]
