import json, math
from simulator import run_one_hop, run_two_hop, run_variant_scenario
from policy import make_policy

params = json.load(open("variant_params.json"))
T = params["grading"]["sim_time_ms"]
slo = params["slo"]

# Vérification des scénarios de référence (une fois implémentés)
print("one_hop", run_one_hop(params, T, 1013), "| attendu :", params["reference"]["expected"])
print("two_hop", run_two_hop(params, T, 1013), "| attendu :", params["reference"]["expected"])


# Scénario variant avec ta politique, sur plusieurs seeds
#for seed in params["experiment"]["seeds"]:      # 5013, 5113, ... (pas 7039-7041)

for seed in [7039,7040,7041]:
    r = run_variant_scenario(params, T, seed, make_policy(params))
    ok = (r["rate"] >= slo["min_rate"]
          and r["mean_fidelity"] >= slo["min_fidelity"]
          and r["p95_latency_ms"] <= slo["max_p95_latency_ms"])
    print(seed, {k: round(v, 3) for k, v in r.items()}, "SLO OK" if ok else "SLO NON")
