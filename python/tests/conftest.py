import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Built pybind11 module lives here (Task 6 onwards).
sys.path.insert(0, os.environ.get("OPTIONPRICER_BUILD", str(ROOT / "build")))
