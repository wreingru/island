#!/usr/bin/env python3
"""Regenerate scoreboard/SCOREBOARD.md and scoreboard/leaderboard.json from scoreboard/results.jsonl (course v2).
Needs only the standard library (the CI job installs jsonschema only); the bootstrap CIs are read from runner/v2_eval.json."""
import json, os, statistics as st, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
course = json.load(open(os.path.join(ROOT, "course.json")))
ev = json.load(open(os.path.join(ROOT, "runner", "v2_eval.json")))
rows = [json.loads(l) for l in open(os.path.join(ROOT, "scoreboard", "results.jsonl")) if l.strip()]
sim = [r for r in rows if r["source"] == "sim-v2"]; live = [r for r in rows if r["source"] == "clawblox-live"]
fmt = lambda s: f"{int(s // 60)}:{s % 60:05.2f}"
nodes = ["N0", "N1", "N2", "N3", "N4", "N5"]
NAME = {n["id"]: n["name"] for n in course["nodes"]}
B = course["boundary"]
ci = lambda v, d=2: f"{v[0]:.{d}f} [{v[1]:.{d}f}, {v[2]:.{d}f}]"

L = [f"# Scoreboard: {course['title']} (course v{course['version']})", "",
     f"Branch `v2-wing-swarm`. Generated from `scoreboard/results.jsonl`: {len(rows)} rows ({len(sim)} sim-v2 rows in "
     f"{len({r['heat_id'] for r in sim})} heats, {len(live)} live rows in {len({r['heat_id'] for r in live})} heats). "
     "Wing swarm only; v1 (five models, reef) results are on `main`.", "",
     "Clock: one race clock from the swarm's release. Total = sum of node splits (no penalties or bonuses in v2). "
     "A DNF is listed at the node it was in, with the reason: water (lost in the bay), energy (downed), cap, or fell.", "",
     "## The boundary: squall line", "",
     f"- Squall disc: moves along the centreline at {B['squall']['pace_studs_s']} studs/s from the start pen, radius shrinking "
     f"from {B['squall']['R0']} to {B['squall']['R_min']} studs; outside it a bot loses {B['squall']['outside_energy_drain_per_s']} energy/s "
     f"(E0 {B['energy']['E0']}, plus {B['energy']['base_drain_per_s']} + {B['energy']['effort_drain_per_s_per_speed2']} v^2 per s).",
     f"- Gust shore (former reef bay, now open water): crosswind toward the water, OU mean {B['gust_shore']['ou_mean_studs_s']} studs/s, "
     f"sigma {B['gust_shore']['ou_sigma']}; a bot whose centre enters the bay is lost.",
     f"- Tuned on seeds {ev['tuning_seeds']} (`runner/v2_tuning.txt`), evaluated on held-out seeds {ev['eval_seeds']}; "
     f"{ev['n_bots']} bots per heat; 95% CIs from 10,000 bootstrap resamples over heats.", "",
     "## Held-out evaluation (sim, 40 heats per arm, paired seeds)", "",
     "| Metric (per heat unless noted) | Squall line (full) | Squall only (no gust) | Boundary off |", "|---|---|---|---|"]
A = ev["arms"] if "arms" in ev else {k: ev[k] for k in ("full", "squall", "off")}
lab = [("completion", "Completion (share of 15 bots)", 3), ("time_s", "Finish time of finishers (s)", 1), ("exits", "Squall-disc exits", 1),
       ("outside_s", "Bot-seconds outside the disc", 1), ("energy_end", "Energy left per bot (of 100)", 1), ("breaks", "Formation breaks", 2),
       ("lost", "Bots lost in the water", 2), ("downed", "Bots downed (energy 0)", 2)]
for k, name, d in lab:
    L.append(f"| {name} | " + " | ".join(ci(A[a][k], d) if k in A[a] else "-" for a in ("full", "squall", "off")) + " |")
D = {"full minus off": ev["paired_full_minus_off"], "full minus squall-only": ev["paired_full_minus_squall"]}
L += ["", "Paired differences (mean [95% CI]):", ""]
for dk, dv in D.items():
    L.append(f"- {dk}: " + "; ".join(f"{k} {ci(v, 3 if k == 'completion' else 1)}" for k, v in dv.items()))
L += ["", "Finishers arrive with the squall (path / pace = " f"{ev['path_len']} / {B['squall']['pace_studs_s']} s), so finish time is set by the squall, not by top speed.", ""]

def table(rs, title):
    out = [f"### {title}", "", "| Place | Bot | Total | Status | " + " | ".join(nodes) + " | Energy left | Outside (s) | Run |",
           "|---|---|---|---|" + "---|" * len(nodes) + "---|---|---|"]
    k = 0
    for r in sorted(rs, key=lambda r: (r["status"] != "finished", r["total_time_s"] if r["status"] == "finished" else -r["raw_time_s"])):
        fin = r["status"] == "finished"; k += fin
        out.append(f"| {k if fin else '-'} | {r['bot_name']} | {fmt(r['total_time_s']) if fin else 'DNF'} | "
                   f"{'finished' if fin else 'DNF at ' + r['dnf_at'] + ' (' + r['dnf_reason'] + ')'} | "
                   + " | ".join(str(r["node_splits"].get(n, "-")) for n in nodes) + f" | {r['boundary']['energy_end']:.1f} | {r['boundary']['outside_s']:.1f} | `{r['run_id']}` |")
    return out + [""]

L += ["## In-world Clawblox heats (source: clawblox-live)", "",
      "Five wing-swarm bots in the v2 Clawblox world (`clawblox/main.lua`), driven by `clawblox/race_live_v2.py`. The world moves the squall, "
      "blows the gust and decides lost / downed / finished; times are its own node log. Three earlier driver-development heats "
      "(s2001 to s2003, also 0 of 5 finished) are kept in `clawblox/live_v2/dev/` and are not scored.", ""]
for h in sorted({r["heat_id"] for r in live}):
    hr = [r for r in live if r["heat_id"] == h]
    L += table(hr, f"`{h}` (seed {hr[0]['seed']}, port {hr[0]['in_world']['port']}): {sum(r['status'] == 'finished' for r in hr)} of {len(hr)} finished, "
                   f"{hr[0]['boundary']['heat_formation_breaks']} formation breaks")
if not live: L += ["No live heats yet.", ""]

L += ["## Sim heats (source: sim-v2, held-out seeds)", "", "| Heat | Finished | Lost (water) | Downed | Cap | Formation breaks | Gust peak | Best | Median finisher |", "|---|---|---|---|---|---|---|---|---|"]
board = {"generated_from": "scoreboard/results.jsonl", "course_id": course["id"], "rows": len(rows), "heats": [], "live": [], "eval": A, "diffs": D}
for h in sorted({r["heat_id"] for r in sim}):
    hr = [r for r in sim if r["heat_id"] == h]; ft = [r["total_time_s"] for r in hr if r["status"] == "finished"]
    c = lambda why: sum(r.get("dnf_reason") == why for r in hr)
    L.append(f"| `{h}` | {len(ft)} / {len(hr)} | {c('water')} | {c('energy')} | {c('cap')} | {hr[0]['boundary']['heat_formation_breaks']} | "
             f"{hr[0]['boundary']['heat_gust_peak']} | {fmt(min(ft)) if ft else '-'} | {fmt(st.median(ft)) if ft else '-'} |")
    board["heats"].append({"heat_id": h, "finished": len(ft), "bots": len(hr), "lost": c("water"), "downed": c("energy"), "cap": c("cap"),
                           "best_s": min(ft) if ft else None, "formation_breaks": hr[0]["boundary"]["heat_formation_breaks"]})
L += ["", "## Where the swarm drops out (sim-v2, all held-out heats)", "", "| Node | DNF here: water | energy | cap | Median split of bots that completed it (s) |", "|---|---|---|---|---|"]
for n in nodes + ["N6"]:
    dn = [r for r in sim if r["dnf_at"] == n]
    sp = [r["node_splits"][n] for r in sim if n in r["node_splits"]]
    L.append(f"| {n} {NAME[n]} | {sum(r['dnf_reason'] == 'water' for r in dn)} | {sum(r['dnf_reason'] == 'energy' for r in dn)} | "
             f"{sum(r['dnf_reason'] == 'cap' for r in dn)} | {round(st.median(sp), 2) if sp else '-'} |")
board["live"] = [{k: r.get(k) for k in ("run_id", "heat_id", "bot_name", "status", "dnf_at", "dnf_reason", "total_time_s", "node_splits", "boundary")} for r in live]
L += ["", "## Read before using these numbers", "",
      "- The sim (`runner/squall_sim.py`) is a 2-D kinematic model of 15 bots at the Clawblox humanoid's 5.5 studs/s; it is not the Clawblox physics.",
      "- The live heat uses the same course and boundary numbers in the real world, but its bots also met engine problems the sim does not have "
      "(bots pinned on the plane-zone car, and collision launches in a crowd). Read the live result as a check of the world, not of the 40-70% target.",
      "- Energy units, drain rates and the gust strength are design choices, tuned on seeds 0-11 only."]
open(os.path.join(ROOT, "scoreboard", "SCOREBOARD.md"), "w").write("\n".join(L) + "\n")
json.dump(board, open(os.path.join(ROOT, "scoreboard", "leaderboard.json"), "w"), indent=1)
print("SCOREBOARD.md:", len(rows), "rows", f"({len(live)} live)")
