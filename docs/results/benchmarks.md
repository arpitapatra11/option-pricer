# Benchmarks

Machine: Windows-11-10.0.26300-SP0, Python 3.13.16, 12 CPU(s). Best of 3 run(s). Indicative numbers, not a rigorous study.

## Monte Carlo (2,000,000 paths, European put, prices only)

| Implementation | Time (ms) | Paths / sec |
|---|---:|---:|
| C++ antithetic | 74.8 | 26,731,642 |
| C++ plain | 113.3 | 17,655,243 |
| Python (numpy) antithetic | 106.8 | 18,728,977 |
| Python (numpy) plain | 119.4 | 16,753,309 |

Variance reduction (C++, same path count, seed 1):

| Metric | Plain | Antithetic |
|---|---:|---:|
| Standard error | 0.00612 | 0.00469 |
| Variance ratio (plain / antithetic) | | 1.71x |
| Time to reach equal standard error (plain / antithetic) | | 2.58x |

## Binomial (N = 3,000 steps, prices only)

| Implementation | Time (ms) | Steps / sec | Node updates / sec |
|---|---:|---:|---:|
| C++ European | 4.7 | 639,686 | 959,849,034 |
| C++ American | 7.9 | 378,224 | 567,525,656 |
| Python (numpy) European | 41.6 | 72,132 | 108,234,372 |
| Python (numpy) American | 148.4 | 20,213 | 30,329,511 |

## Notes

- C++ rows are timed through the pybind11 module, so they include a small fixed
  call overhead (dict parsing and result dict); it is negligible at these sizes.
- All Monte Carlo runs are single-threaded.
- C++ Monte Carlo is not much faster than numpy: both are dominated by normal
  random-number generation, and numpy's generator is already compiled code.
  The Binomial rows show the larger C++ advantage (a tight loop that numpy
  can only partly vectorise).
- Antithetic variates use half the normal draws per path, so they are cheaper per path
  and lower-variance; the variance table above is the fair way to compare them.
