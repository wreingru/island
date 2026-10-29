#!/usr/bin/env python3
"""Write course.json for course v2 (mesa-island-race-v2): wing swarm only, reef removed, squall-line boundary.

v1 lives on main. v2 keeps the island, runway lot, plane and hill tunnels, and drops everything the wing swarm
cannot use or that sat on the reef: the reef strip and its hold objective (N1b), the swim buoy, the drone gates
(gate C stood on the reef; the swarm does not fly) and the COTA loop / NPC cars. The new challenge is the boundary:
  * squall disc: a circle moving along the centreline at a fixed pace and shrinking; outside it energy drains fast
  * gust shore: the former reef bay is open water; the route runs a 6-stud strip between the water and a new cliff
    wall, with a crosswind toward the water; a bot whose centre enters the water is lost
Boundary numbers were tuned on seeds 0-11 (runner/tune_v2.py) and evaluated on held-out seeds (runner/eval_v2.py).
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "course.json")
prev = json.load(open(OUT))
W1 = prev["world"]
if prev["id"] != "mesa-island-race-v1" and "v1_world" in prev:
    W1 = prev["v1_world"]

CENTRELINE = [[-34, -44], [-12, -50], [-2, -56], [-2, -2], [-9.5, 8], [-9.5, 28], [-2, 40], [-2, 55], [-14, 48],
              [-22, 20], [-22, -28], [-2, -33], [7, -34.0], [33, -34.0], [37, -32], [33, -27.8], [16, -27.8],
              [16, -22], [24, -22], [24, -16], [20, -10]]
# vertex index where each node starts on the centreline
NODE_START_VERTEX = {"N1": 2, "N2": 4, "N3": 7, "N4": 12, "N5": 14, "N6": 20}
BOUNDARY = {
    "name": "squall line",
    "squall": {"pace_studs_s": 3.0, "R0": 14.0, "R_min": 3.0, "shrink": "linear in centreline progress",
               "outside_energy_drain_per_s": 6.0, "starts": "at the swarm's release, centre at the start pen"},
    "gust_shore": {"box": {"min": [6.0, -37.0], "max": [35.0, -31.0]}, "direction": [0, -1],
                   "ou_mean_studs_s": 3.0, "ou_sigma": 1.5, "ou_reversion_per_s": 0.5,
                   "water_rule": "a bot whose centre enters the bay is lost (DNF)"},
    "energy": {"E0": 100.0, "base_drain_per_s": 0.1, "effort_drain_per_s_per_speed2": 0.004, "downed_at": 0.0},
    "lane_half_width": {"default": 5.0, "plane_zone": 2.5, "gust_shore": 1.6, "hill": 0.6,
                        "corners": "min(hw, 0.6 + 0.35 x distance to a corner sharper than 40 deg)"},
    "tuning": {"seeds": "0-11", "grid": "gust mean {0,2,3,4,5,6} x R_min {3,4.5} at pace 3.0 (and pace 3.5 earlier)",
               "target": "40-70% bot completion", "chosen": "gust mean 3.0, R_min 3.0: 50% on the tuning seeds"},
    "why": ["The wing swarm's edge in v1 was raw speed (5.5 studs/s vs 1.5 to 1.9 for the beetles). A moving squall "
            "caps progress at its pace, so speed alone no longer wins: running ahead is outside the disc too.",
            "Keeping 15 bots inside a shrinking disc through 3-stud tunnels and a 6-stud shore strip forces the "
            "formation to stretch into a column and regroup, which is what the swarm work (quorum, formation) is about.",
            "The gust shore turns the old reef bay into the hazard: with the reef gone there is nowhere to stand, and "
            "the crosswind punishes bots on the water-side lane, so formation placement matters.",
            "Each part has one knob (pace, final radius, gust mean), so the course can be tuned to a target completion rate."],
}
NODES = [
    {"id": "N0", "name": "Start pen and approach", "type": "start", "parents": [], "children": ["N1"],
     "zone": {"kind": "circle", "c": [-34.0, -44.0], "r": 4.0}, "entry": "release (all bots together)",
     "exit": "reach the runway start line (centreline vertex 2)", "scoring": {"split": "release to runway start"}},
    {"id": "N1", "name": "Runway lot in the squall", "type": "obstacle_lane", "parents": ["N0"], "children": ["N2"],
     "zone": {"kind": "box", "min": [-14.0, -56.0], "max": [10.0, 8.0]}, "scoring": {"split": "entry to exit"},
     "note": "cars and the 1.0-1.5 stud pallets block; 0.5 stud pallets are stepped over"},
    {"id": "N2", "name": "Plane crossing (on foot)", "type": "obstacle_lane", "parents": ["N1"], "children": ["N3"],
     "zone": {"kind": "box", "min": [-14.0, 8.0], "max": [10.0, 56.0]}, "scoring": {"split": "entry to exit"},
     "note": "lane narrows to 2.5 studs round the fuselage; the low wing is stepped over"},
    {"id": "N3", "name": "West return leg", "type": "return_leg", "parents": ["N2"], "children": ["N4"],
     "zone": {"kind": "box", "min": [-26.0, -36.0], "max": [10.0, 56.0]}, "scoring": {"split": "entry to exit"}},
    {"id": "N4", "name": "Gust shore (former reef bay)", "type": "gust_shore", "parents": ["N3"], "children": ["N5"],
     "zone": {"kind": "box", "min": [6.0, -37.0], "max": [37.0, -31.0]}, "scoring": {"split": "entry to exit"},
     "note": "open water to the south (reef removed), cliff wall to the north, crosswind toward the water"},
    {"id": "N5", "name": "Hill tunnels", "type": "climb", "parents": ["N4"], "children": ["N6"],
     "zone": {"kind": "box", "min": [8.0, -30.0], "max": [32.0, -12.0]},
     "ridges": [{"z": -25.0, "x": [10.0, 30.0], "tunnel_x": 16.0}, {"z": -19.0, "x": [10.0, 30.0], "tunnel_x": 24.0}],
     "tunnel_width": 3.0, "scoring": {"split": "entry to exit"}},
    {"id": "N6", "name": "Finish (summit)", "type": "finish", "parents": ["N5"], "children": [],
     "zone": {"kind": "circle", "c": [20.0, -10.0], "r": 2.5}, "scoring": {"split": "0"}},
]
for n in NODES:
    if n["id"] in NODE_START_VERTEX: n["starts_at_centreline_vertex"] = NODE_START_VERTEX[n["id"]]

course = {
    "id": "mesa-island-race-v2", "title": "Mesa Island Race Course v2: wing swarm, no reef, squall line", "version": 2,
    "units": prev["units"],
    "host_targets": ["clawblox:clawblox/ (world.toml + main.lua, v2 logic)", "mesaworld:course_spec.json (engine-neutral)",
                     "sim:runner/squall_sim.py (15-bot swarm)"],
    "timing": {"clock": "one race clock from the swarm's release (no stagger)",
               "total": "finish time = sum of node splits; no penalties or bonuses in v2",
               "dnf": "lost in the water, downed (energy 0), or not at the summit by the cap (squall arrival + 60 s)"},
    "swarm": {"size_sim": 15, "size_live": 5, "formation": "5 rows x 3 lanes around the squall centre (sim); 5 lanes in one row (live)"},
    "centreline": CENTRELINE, "boundary": BOUNDARY, "nodes": NODES,
    "bot_models": [m for m in prev["bot_models"] if m["id"] == "wing_swarm"] or [{"id": "wing_swarm"}],
    "world": {
        "ground_note": W1["ground_note"],
        "bay": dict(W1["bay"], note="open water; the v1 reef strip is removed"),
        "runway": W1["runway"], "runway_obstacles": W1["runway_obstacles"],
        "cliff_wall": {"min": [6.0, -31.0], "max": [33.0, -30.0], "height": 6.0},
        "ridges": NODES[5]["ridges"], "ridge_height": 7.0, "summit": W1["summit"],
    },
}
course["bot_models"][0]["nodes"] = {n["id"]: "walk" for n in NODES[1:6]}
json.dump(course, open(OUT, "w"), indent=1)
print("wrote", OUT, course["id"])
