"""
check_policy.py — check make_policy() against the variant SLOs (same output format as run_var.py).
Not part of the submission zip. Run from the repo root: python check_policy.py

AI assistance: Claude (Anthropic) wrote this check script.
"""

import json

from simulator import run_one_hop, run_two_hop, run_variant_scenario
from policy import make_policy

params = json.load(open("variant_params.json"))
T = params["grading"]["sim_time_ms"]
slo = params["slo"]

# Reference scenarios (validation) on the grading seed
for name, fn in [("one_hop", run_one_hop), ("two_hop", run_two_hop)]:
    try:
        print(name, fn(params, T, 1013), "| expected :", params["reference"]["expected"])
    except Exception as e:  # keep going so the SLO check still runs
        print(name, ": ERROR", type(e).__name__, e)

# Variant scenario with our policy: grading seed + held-out seeds
print("SLO:", slo)
for seed in [params["grading"]["seed"], *params["grading"]["held_out_seeds"]]:   # 1013, 7039, 7040, 7041
    r = run_variant_scenario(params, T, seed, make_policy(params))
    ok = (r["rate"] >= slo["min_rate"]
          and r["mean_fidelity"] >= slo["min_fidelity"]
          and r["p95_latency_ms"] <= slo["max_p95_latency_ms"])
    print(seed, {k: round(v, 3) for k, v in r.items()}, "SLO OK" if ok else "SLO NON")
