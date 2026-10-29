#!/usr/bin/env python3
"""Tune the v2 boundary on seeds 0-11 (never used for evaluation). Prints completion and failure modes per config.
Usage: python3 runner/tune_v2.py > runner/v2_tuning.txt"""
import json, sys, os, itertools, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import squall_sim as S
def job(a):
    cfg, sd = a; r = S.run(sd, cfg)
    return json.dumps(cfg, sort_keys=True), sum(r["finished"]), sum(r["lost_in_water"]), sum(r["downed"]), sum(r["exits"]), r["formation_breaks"]
if __name__ == "__main__":
    grid = [dict(S.CFG, gust_mu=g, R_min=rm) for g, rm in itertools.product([0.0, 2.0, 3.0, 4.0, 5.0, 6.0], [3.0, 4.5])]
    with mp.Pool(mp.cpu_count()) as p: res = p.map(job, [(c, sd) for c in grid for sd in range(12)])
    agg = {}
    for k, *v in res: agg.setdefault(k, []).append(v)
    print("tuning seeds 0-11, 15 bots, pace", S.CFG["v_b"])
    for k, v in agg.items():
        c = json.loads(k); n = len(v)
        print(f"gust_mu={c['gust_mu']} R_min={c['R_min']}: completion {sum(x[0] for x in v)/(S.N_BOTS*n):.2f} lost {sum(x[1] for x in v)/n:.1f} downed {sum(x[2] for x in v)/n:.1f} exits {sum(x[3] for x in v)/n:.1f} breaks {sum(x[4] for x in v)/n:.1f}")
