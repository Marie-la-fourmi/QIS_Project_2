"""
experiments.py — QIS-NET Project 2 sensitivity experiment (STUDENT FILE).

Implement run_sensitivity: one-at-a-time (OAT) sensitivity of the variant
scenario's delivered RATE to memory T2 over params['experiment']['t2_grid_ms'],
using >= params['experiment']['seeds_per_point'] seeds per grid point.

Output contract (autograded): write experiment_results.json containing
{
  "parameter": "t2_ms",
  "grid": [...],
  "seeds_per_point": int,
  "points": [
     {"t2_ms": x, "rate_mean": m, "rate_ci95": h, "n_seeds": k}, ...
  ]
}
CI: 95% t-interval half-width over the per-seed rates.

AI assistance: Claude (Anthropic) was used to review and test run_sensitivity.
"""

import json
import math
from copy import deepcopy

import numpy as np

from policy import make_policy
from simulator import run_variant_scenario


def mean_ci95(values):
    """Return (mean, 95% CI half-width) using the t-distribution."""
    n = len(values)
    m = float(np.mean(values))
    if n < 2:
        return m, 0.0
    s = float(np.std(values, ddof=1))
    # t_{0.975, df} for small df (table lookup, no scipy needed)
    t_table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
               6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}
    t = t_table.get(n - 1, 1.96)
    return m, t * s / math.sqrt(n)


def run_sensitivity(params, seeds) -> dict:
    """Run the OAT sweep described above.
    For each t2 in params['experiment']['t2_grid_ms']:
      - deep-copy params, set params_copy['physics']['t2_ms'] = t2
      - for each seed in seeds[:seeds_per_point]: run the variant scenario
        with your policy (make_policy(params_copy)) and record 'rate'
      - append {"t2_ms": ..., "rate_mean": ..., "rate_ci95": ..., "n_seeds": ...}
    Write the results dict to experiment_results.json and return it.
    """
    experiment = params["experiment"]
    seeds_per_point = experiment["seeds_per_point"]
    if seeds_per_point < 1:
        raise ValueError("seeds_per_point must be positive")
    # Use the same seeds at every T2 value for a consistent comparison.
    selected_seeds = list(seeds)[:seeds_per_point]
    if len(selected_seeds) < seeds_per_point:
        raise ValueError("Not enough seeds for the requested seeds_per_point")

    results = {
        "parameter": "t2_ms",
        "grid": list(experiment["t2_grid_ms"]),
        "seeds_per_point": seeds_per_point,
        "points": [],
    }
    for t2 in results["grid"]:
        # Change only T2 and preserve the original configuration.
        params_copy = deepcopy(params)
        params_copy["physics"]["t2_ms"] = t2
        rates = []
        for seed in selected_seeds:
            # Start each run with a fresh policy to avoid carrying over state.
            policy = make_policy(params_copy)
            metrics = run_variant_scenario(
                params_copy, params_copy["grading"]["sim_time_ms"], seed, policy
            )
            rates.append(metrics["rate"])
        # Summarise the per-seed rates with a mean and 95% CI half-width.
        mean, half_width = mean_ci95(rates)
        results["points"].append({
            "t2_ms": t2,
            "rate_mean": mean,
            "rate_ci95": half_width,
            "n_seeds": len(rates),
        })

    # Write the experiment artefact in the required grading format.
    with open("experiment_results.json", "w", encoding="utf-8") as output:
        json.dump(results, output, indent=2, allow_nan=False)
        output.write("\n")
    return results


if __name__ == "__main__":
    import sys
    params = json.load(open(sys.argv[1] if len(sys.argv) > 1
                            else "variant_params.json"))
    exp = params["experiment"]
    seeds = exp["seeds"]
    out = run_sensitivity(params, seeds)
    print(json.dumps(out, indent=2))
