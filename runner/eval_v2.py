#!/usr/bin/env python3
"""Usage: python3 runner/eval_v2.py runner/v2_eval.json runner/v2_heats.json
Held-out paired evaluation of the v2 squall boundary. Tuning used seeds 0-11; these are seeds 1000-1039.
Each seed is run three ways (same seed -> same formation jitter, start scatter and gust draws):
  full   : squall disc + gust shore (the v2 boundary as tuned)
  squall : squall disc only (gust off)
  off    : no boundary (formation follows a 4.5 studs/s virtual leader; water still lethal)
95% CIs: percentile bootstrap over heats (10,000 resamples, numpy seed 7); paired diffs resample seeds jointly."""
import json, sys, multiprocessing as mp
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__))); import squall_sim as S

CFG = S.CFG
SEEDS = list(range(1000, 1040))
def job(a):
    arm, sd = a
    cfg = dict(CFG, gust_mu=0.0) if arm == 'squall' else CFG
    return arm, sd, S.run(sd, cfg, boundary=(arm != 'off'))
def metrics(r):
    f = np.array(r['finished']); t = [x for x in r['finish_s'] if x is not None]
    return dict(completion=f.mean(), time_s=np.mean(t) if t else np.nan, exits=float(np.sum(r['exits'])),
                outside_s=float(np.sum(r['outside_s'])), energy_end=float(np.mean(np.maximum(r['energy_end'], 0))),
                breaks=float(r['formation_breaks']), lost=float(np.sum(r['lost_in_water'])), downed=float(np.sum(r['downed'])))
if __name__ == '__main__':
    with mp.Pool(mp.cpu_count()) as p: res = p.map(job, [(a, s) for a in ('full', 'squall', 'off') for s in SEEDS])
    runs = {(a, s): r for a, s, r in res}
    M = {a: {k: np.array([metrics(runs[(a, s)])[k] for s in SEEDS]) for k in metrics(runs[(a, SEEDS[0])])} for a in ('full', 'squall', 'off')}
    rng = np.random.default_rng(7); B = rng.integers(0, len(SEEDS), (10000, len(SEEDS)))
    def ci(x):
        bs = np.nanmean(x[B], axis=1); return [round(float(np.nanmean(x)), 3), round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)]
    out = {"config": CFG, "tuning_seeds": "0-11", "eval_seeds": "1000-1039", "n_bots": S.N_BOTS, "path_len": round(float(S.L_PATH), 1),
           "arms": {a: {k: ci(v) for k, v in M[a].items()} for a in M},
           "paired_full_minus_off": {k: ci(M['full'][k] - M['off'][k]) for k in ('completion', 'time_s', 'energy_end', 'breaks')},
           "paired_full_minus_squall": {k: ci(M['full'][k] - M['squall'][k]) for k in ('completion', 'lost', 'downed', 'exits')},
           "per_seed_full": [dict(seed=s, **{k: (None if np.isnan(v) else round(float(v), 3)) for k, v in metrics(runs[('full', s)]).items()}) for s in SEEDS]}
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    json.dump({str(s): runs[('full', s)] for s in SEEDS}, open(sys.argv[2], 'w'))
    for a in out['arms']: print(a, out['arms'][a])
    print('full-off', out['paired_full_minus_off']); print('full-squall', out['paired_full_minus_squall'])
