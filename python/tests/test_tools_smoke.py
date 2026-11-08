"""Each tool must run end to end in --quick mode and write its outputs."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_tool(name, out_dir):
    env = dict(os.environ)
    build = os.environ.get("OPTIONPRICER_BUILD", str(ROOT / "build"))
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "python"), build, env.get("PYTHONPATH", "")])
    env["MPLBACKEND"] = "Agg"
    return subprocess.run([sys.executable, str(ROOT / "python" / "tools" / name), "--quick",
                           "--out", str(out_dir)], env=env, capture_output=True, text=True, timeout=300)


def test_plot_convergence_quick(tmp_path):
    res = run_tool("plot_convergence.py", tmp_path)
    assert res.returncode == 0, res.stderr
    for name in ("binomial_convergence.png", "mc_convergence.png"):
        f = tmp_path / name
        assert f.exists() and f.stat().st_size > 5000, name


def test_benchmark_quick(tmp_path):
    res = run_tool("benchmark.py", tmp_path)
    assert res.returncode == 0, res.stderr
    text = (tmp_path / "benchmarks.md").read_text()
    for needle in ("Monte Carlo", "Binomial", "C++", "Python"):
        assert needle in text, needle
