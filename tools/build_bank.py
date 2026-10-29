#!/usr/bin/env python3
"""Build runner/bank.json: per-bot measured samples pulled straight from the earlier sim results.

Every number in the bank is copied from a results.json file on the box. Nothing is re-simulated.
Source folders (on the box this was built on): /workspace/<folder>/results.json.
If a folder is missing, the bank keeps whatever it already had (commit runner/bank.json to the repo).
"""
import json, os, sys, statistics as st

SRC = os.environ.get("ISLAND_SRC", "/workspace")
OUT = os.path.join(os.path.dirname(__file__), "..", "runner", "bank.json")

def load(folder):
    return json.load(open(os.path.join(SRC, folder, "results.json")))

bank = {"note": "Measured per-bot samples copied from earlier sims. See 'sources'.", "sources": {}, "samples": {}}

# Runway with curvity (flooded parking, condition A, kappa 0.6), walk and fly modes: island_runway_fly
rf = load("island_runway_fly")["runs"]
walk, fly = [], []
for r in rf:
    if r.get("cond") != "A":
        continue
    flights_by_bot = {}
    for f in r.get("flights") or []:
        flights_by_bot.setdefault(f["bot"], []).append({"E": f["E"], "tair": f["tair"]})
    for b, arr in enumerate(r["arrival_s"]):
        if arr is None:
            continue
        rec = {"seed": r["seed"], "bot": b, "arrival_s": arr, "zone_s": r["zone_s"][b],
               "approach_s": round(arr - r["zone_s"][b], 2)}
        if r["mode"] == "walk":
            walk.append(rec)
        else:
            rec.update(flyer=bool(r["flyer"][b]), reserve0_J=r["reserve0"][b],
                       hops=flights_by_bot.get(b, []))
            fly.append(rec)
bank["samples"]["runway_walk"] = walk
bank["samples"]["runway_fly"] = fly
bank["sources"]["runway_walk"] = bank["sources"]["runway_fly"] = "island_runway_fly/results.json (cond A, kappa 0.6, flooded lot)"

# Curvity scout on the runway: island_runway condition A, flooded, kappa 1.2
ru = load("island_runway")["runs"]
bank["samples"]["runway_scout"] = [
    {"seed": r["seed"], "scout_arrival_s": r["scout_arrival_s"], "impeded_events": r["impeded_events"]}
    for r in ru if r["cond"] == "A" and r.get("flood") and r.get("kappa") == 1.2 and r.get("scout_arrival_s") is not None]
bank["sources"]["runway_scout"] = "island_runway/results.json (cond A, flooded, kappa 1.2)"

# Triathlon (barrier=True runs): swim, T1+bike+T2, run splits per racer persona
tri = load("island_triathlon")["runs"]
trs = []
for r in tri:
    if not r["barrier"]:
        continue
    for rc in r["racers"]:
        s = rc["split"]
        trs.append({"seed": r["seed"], "bot": rc["bot"], "swim_s": s["swim"], "T1_s": s["T1"], "bike_s": s["bike"],
                    "bike_lap1_s": s["bike_lap1"], "bike_lap2_s": s["bike_lap2"], "T2_s": s["T2"], "run_s": s["run"],
                    "npc_passes": len(rc["npc_passes"]), "npc_contacts": len(rc["contacts_npc"]), "t_behind_s": rc["t_behind"]})
bank["samples"]["triathlon"] = trs
bank["sources"]["triathlon"] = "island_triathlon/results.json (barrier=True: NPC car pair on the COTA loop)"

# Reef bay: which bot held the reef, condition A (holdout seeds)
rb = load("island_reef_bay")["runs"]
bank["samples"]["reef_hold"] = [{"seed": r["seed"], "reef_bots": r["reef_bots"], "success": r["success"]}
                                for r in rb if r["cond"].startswith("A")]
bank["sources"]["reef_hold"] = "island_reef_bay/results.json (cond A_barriers_signal)"

# Drone gates, nominal wind
dr = load("island_drone_course")["runs"]
drs = []
for r in dr:
    if r["cond"] != "nominal":
        continue
    for b in r["bots"]:
        drs.append({"seed": r["seed"], "bot": b["bot"], "status": b["status"], "lap_s": b["lap_s"], "gates": b["gates"],
                    "complete": b["complete"], "reserve0_J": b["reserve0"], "E_fly_J": b["E_fly"],
                    "flights": [{"gate": f["gate"], "E": f["E"], "tair": f["tair"], "res": f["res"]} for f in b["flights"]]})
bank["samples"]["drone_gates"] = drs
bank["sources"]["drone_gates"] = "island_drone_course/results.json (cond nominal)"

# Hill with tunnels, swarm condition. Summit times are seconds after each bot's own release, 2 h cap.
bt = load("beetle_tunnels")["runs"]
hs = []
for r in bt:
    if r["cond"] != "swarm":
        continue
    for b, t in enumerate(r["summit_times"]):
        hs.append({"seed": r["seed"], "bot": b, "summit_s": t, "tunnel_uses_run": r["tunnel_uses"]})
bank["samples"]["hill_tunnels"] = hs
bank["sources"]["hill_tunnels"] = "beetle_tunnels/results.json (cond swarm; BeetleBot crawl time scale)"

json.dump(bank, open(OUT, "w"), indent=1)
for k, v in bank["samples"].items():
    print(f"{k:14s} {len(v)} samples")
