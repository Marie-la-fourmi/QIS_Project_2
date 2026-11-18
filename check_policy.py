"""
check_policy.py — check make_policy() against the variant SLOs.
Not part of the submission zip. Run from the repo root: python check_policy.py

AI assistance: Claude (Anthropic) wrote this check script.
"""

import json

from policy import make_policy
from simulator import run_variant_scenario

params = json.load(open("variant_params.json"))
T, slo = params["grading"]["sim_time_ms"], params["slo"]
seeds = [("grading", params["grading"]["seed"])] + [
    ("held-out", s) for s in params["grading"]["held_out_seeds"]]

print(f"SLO: rate >= {slo['min_rate']}, fidelity >= {slo['min_fidelity']}, "
      f"p95 <= {slo['max_p95_latency_ms']} ms\n")
grading_ok = True
for kind, seed in seeds:
    r = run_variant_scenario(params, T, seed, make_policy(params))
    checks = [r["rate"] >= slo["min_rate"],
              r["mean_fidelity"] >= slo["min_fidelity"],
              r["p95_latency_ms"] <= slo["max_p95_latency_ms"]]
    marks = ["ok" if c else "FAIL" for c in checks]
    print(f"{kind:8s} seed {seed}: rate {r['rate']:.2f} [{marks[0]}]  "
          f"fidelity {r['mean_fidelity']:.4f} [{marks[1]}]  "
          f"p95 {r['p95_latency_ms']:.1f} ms [{marks[2]}]  "
          f"pairs/delivery {r['pairs_consumed_per_delivery']:.2f}")
    if kind == "grading":
        grading_ok = all(checks)

seed = params["grading"]["seed"]
same = (run_variant_scenario(params, T, seed, make_policy(params))
        == run_variant_scenario(params, T, seed, make_policy(params)))
print(f"\ndeterministic (same seed twice): {'ok' if same else 'FAIL'}")
print(f"grading seed meets all SLOs:     {'ok' if grading_ok else 'FAIL'}")
