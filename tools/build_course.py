#!/usr/bin/env python3
"""Write course.json, the single source for the race course.

course.json feeds: runner/run_race.py, tools/export_clawblox.py (Clawblox Lua world),
tools/export_mesaworld.py (engine-neutral spec), the schema checks and the scoreboard.
Coordinates are Clawblox studs on the Mesa island (x east, z north, ground top y = 0).
Loop and swim centrelines are copied from /workspace/island_triathlon/course.py when it exists.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "course.json")

loop, swim = None, None
tri = "/workspace/island_triathlon"
if os.path.isdir(tri):
    sys.path.insert(0, tri)
    try:
        import course as C  # needs numpy + scipy
        step = len(C.BIKE_XZ) // 64
        loop = [[round(float(x), 2), round(float(z), 2)] for x, z in C.BIKE_XZ[::step]]
        sstep = max(1, len(C.SWIM_XZ) // 16)
        swim = [[round(float(x), 2), round(float(z), 2)] for x, z in C.SWIM_XZ[::sstep]]
    except Exception as e:  # keep previous geometry
        print("triathlon geometry not loaded:", e)
if loop is None:
    prev = json.load(open(OUT))
    loop, swim = prev["world"]["cota_loop_centreline"], prev["world"]["swim_centreline"]

RUNWAY_X = -2.0
course = {
  "id": "mesa-island-race-v1",
  "title": "Mesa Island Race Course",
  "version": 1,
  "units": {"length": "stud", "time": "s", "note": "1 stud = 29 mm in the BeetleBot sims (assumed scale)"},
  "host_targets": ["clawblox:worlds/island-race (adapted from worlds/mesa-island-wings)", "mesaworld:course_spec.json (engine-neutral)"],
  "timing": {
    "clock": "each bot's clock starts at its own release from the start pen",
    "stagger_s": 15.0,
    "transit_legs": "untimed (neutral) between a node's exit and the next node's entry; Clawblox logs them as TRANSIT",
    "total": "sum of node splits + penalties - bonuses"
  },
  "nodes": [
    {"id": "N0", "name": "Start pen", "type": "start", "parents": [], "children": ["N1"], "optional": False,
     "zone": {"kind": "circle", "c": [-34.0, -44.0], "r": 4.0},
     "entry": "bot spawns or is placed in the pen", "exit": "release signal; bot i released at i x stagger_s",
     "scoring": {"split": "0 (stagger is not counted)"},
     "allowed_modes": ["walk", "hop", "swim", "roll", "run", "walk-centre"],
     "source": "15 s stagger from island_drone_course"},
    {"id": "N1", "name": "Reef bay swim", "type": "swim", "parents": ["N0"], "children": ["N1b", "N2"], "optional": False,
     "zone": {"kind": "box", "min": [7.0, -50.0], "max": [34.0, -37.0]},
     "waypoints": {"buoy": [30.6, -45.2], "buoy_r": 2.5, "beach_exit": [24.0, -37.0], "shore_path": [[6.0, -35.0], [24.0, -35.0]]},
     "entry": "enter the bay water (swimmers) or the shore path start (others)",
     "exit": "reach the beach exit after rounding the buoy (swimmers) or reach the end of the shore path (others)",
     "scoring": {"split": "entry to exit", "penalties": {"no_swim_shore_path_s": 20.0}},
     "allowed_modes": ["swim", "walk", "walk-centre", "run"],
     "mode_rules": {"swim": "triathlon swim split, measured", "others": "shore path 18 studs at the bot's speed + no_swim penalty (derived)"},
     "source": "island_triathlon swim leg (37.5 studs)"},
    {"id": "N1b", "name": "Reef hold (side objective)", "type": "side_objective", "parents": ["N1"], "children": ["N2"], "optional": True,
     "zone": {"kind": "circle", "c": [28.3, -48.5], "r": 1.5},
     "entry": "step onto the reef tip beacon (walk the reef from its root at x = 6.5)",
     "exit": "hold the tip for 10 s, then walk back to the root",
     "scoring": {"split": "time from leaving N1 to returning to the reef root", "bonus_s": 60.0,
                 "rule": "only one bot per heat may hold the reef; bonus only if the hold succeeds"},
     "allowed_modes": ["walk", "walk-centre"],
     "allowed_models": ["beetle_walker", "flying_beetle", "curvity_scout"],
     "mode_rules": {"walk": "which bot goes and whether it succeeds come from the matching island_reef_bay condition A run (measured); the time is reef length x 2 at 0.9 studs/s + 10 s hold (derived)"},
     "source": "island_reef_bay (one bot on the reef in 60/60 runs; success 38/60)"},
    {"id": "N2", "name": "Runway with curvity", "type": "obstacle_lane", "parents": ["N1", "N1b"], "children": ["N3"], "optional": False,
     "zone": {"kind": "box", "min": [RUNWAY_X - 12, -56.0], "max": [RUNWAY_X + 12, 8.0]},
     "entry": "cross the start line z = -56", "exit": "enter the plane zone (z = 8)",
     "scoring": {"split": "entry to exit"},
     "allowed_modes": ["walk", "hop", "walk-centre", "run"],
     "mode_rules": {"walk": "island_runway_fly walk arrival minus plane-zone time (measured)",
                    "walk-centre": "island_runway scout arrival x (1 - median plane-zone share) (derived split)"},
     "source": "island_runway / island_runway_fly"},
    {"id": "N3", "name": "Plane crossing (hop or walk)", "type": "hop", "parents": ["N2"], "children": ["N4"], "optional": False,
     "zone": {"kind": "box", "min": [RUNWAY_X - 12, 8.0], "max": [RUNWAY_X + 12, 56.0]},
     "entry": "enter the plane zone", "exit": "cross the runway goal line z = 56",
     "scoring": {"split": "entry to exit", "hop_rule": "hop only if reserve >= 1.15 x hop cost"},
     "allowed_modes": ["walk", "hop", "walk-centre", "run"],
     "note": "In Clawblox this node runs to the goal line; the runner folds the short runway tail into N2.",
     "source": "island_runway_fly (2.61 J and 2.22 s airborne per hop)"},
    {"id": "N4", "name": "Drone gates D-C-B-A (C is on the reef)", "type": "gates", "parents": ["N3"], "children": ["N5"], "optional": False,
     "zone": {"kind": "circle", "c": [-26.0, -40.0], "r": 2.5},
     "gates": [
        {"id": "D", "c": [-17.0, -40.0], "h": 5.6, "takeoff": [-26.0, -40.0], "landing": [-8.5, -42.5]},
        {"id": "C", "c": [20.0, -48.5], "h": 4.4, "takeoff": [10.5, -48.5], "landing": [39.5, -44.5]},
        {"id": "B", "c": [26.0, -26.0], "h": 6.4, "takeoff": [17.0, -26.0], "landing": [35.0, -24.0]},
        {"id": "A", "c": [40.0, -38.0], "h": 7.0, "takeoff": [40.0, -47.0], "landing": [40.0, -29.5]}],
     "gate_opening": 6.0,
     "entry": "reach the gate D take-off pad", "exit": "reach the gate A landing pad",
     "scoring": {"split": "entry to exit", "penalties": {"gate_skipped_s": 10.0, "gate_bypassed_on_foot_s": 10.0, "rescued_from_water_s": 60.0}},
     "allowed_modes": ["hop", "walk", "walk-centre", "run"],
     "mode_rules": {"hop": "island_drone_course nominal per-bot record; reserve reduced by energy spent at N3 (measured, re-gated)",
                    "others": "walk to a check-in pad under each gate; time = 110 studs at the bot's speed + 4 bypass penalties (derived)"},
     "source": "island_drone_course (nominal: 141/200 through all four gates)"},
    {"id": "N5", "name": "COTA loop with NPC car pair", "type": "loop", "parents": ["N4"], "children": ["N6"], "optional": False,
     "zone": {"kind": "circle", "c": [25.0, -31.5], "r": 3.0},
     "laps": {"roll": 2, "others": 1}, "checkpoints_per_lap": 4,
     "entry": "enter the transition zone (T1)", "exit": "return to the transition zone after the required laps (T2)",
     "scoring": {"split": "T1 + laps + T2"},
     "allowed_modes": ["roll", "walk", "walk-centre", "run"],
     "mode_rules": {"roll": "island_triathlon barrier run: T1 + bike + T2 splits (measured)",
                    "others": "one lap of 256.2 studs at the bot's speed (derived; no measured walking lap)"},
     "npc": {"pairs": 2, "speed": 2.4, "note": "NPC speed from island_triathlon sim parameters"},
     "source": "island_triathlon (barrier cost 8.81 s per racer)"},
    {"id": "N6", "name": "Hill climb with tunnels", "type": "climb", "parents": ["N5"], "children": ["N7"], "optional": False,
     "zone": {"kind": "box", "min": [8.0, -30.0], "max": [32.0, -12.0]},
     "ridges": [{"z": -25.0, "x": [10.0, 30.0], "tunnel_x": 16.0}, {"z": -19.0, "x": [10.0, 30.0], "tunnel_x": 24.0}],
     "tunnel_width": 3.0,
     "entry": "leave the transition zone heading north", "exit": "reach the summit pad",
     "scoring": {"split": "entry to exit", "penalties": {"no_summit_in_cap_s": 30.0}},
     "allowed_modes": ["walk", "hop", "walk-centre", "run"],
     "mode_rules": {"walk": "beetle_tunnels swarm summit time / 72.5 (time-scale assumption: 0.6 mm/s crawl vs 1.5 studs/s)"},
     "source": "beetle_tunnels (swarm 96/100 summited, 2 h cap)"},
    {"id": "N7", "name": "Finish (summit)", "type": "finish", "parents": ["N6"], "children": [], "optional": False,
     "zone": {"kind": "circle", "c": [20.0, -10.0], "r": 2.5},
     "entry": "reach the summit pad", "exit": "none", "scoring": {"split": "0"},
     "allowed_modes": ["walk", "hop", "swim", "roll", "run", "walk-centre"], "source": "summit (20, -10) from the reef bay sims"}
  ],
  "bot_models": [
    {"id": "beetle_walker", "name": "BeetleBot walker", "body": "BeetleBot", "modes": ["walk"], "speed_studs_s": 1.5,
     "speed_basis": "assumed island speed (0.6 studs per 0.4 s stride) from island_runway",
     "headline": [
        "beetle_swarm: 97/100 bots summited, median 138.5 min (finishers)",
        "beetle_tunnels: 96/100 summited in the 2 h cap, mean 67.6 min",
        "island_runway: all 5 arrived in 20/20 flooded runs, mean 132.4 s at kappa 1.2"],
     "nodes": {"N1": "walk", "N1b": "walk", "N2": "walk", "N3": "walk", "N4": "walk", "N5": "walk", "N6": "walk"}},
    {"id": "flying_beetle", "name": "Flying beetle (walk + hop)", "body": "BeetleBot with wings", "modes": ["walk", "hop"], "speed_studs_s": 1.5,
     "speed_basis": "same walking speed as the walker",
     "headline": [
        "island_runway_fly: mean arrival 94.0 s flying vs 101.1 s walking (-7.1 s, CI -9.5 to -4.7)",
        "2.61 J and 2.22 s airborne per hop; 19.8 s saved per flyer at the plane",
        "island_drone_course: 141/200 (70.5%) through all four gates, nominal wind"],
     "nodes": {"N1": "walk", "N1b": "walk", "N2": "walk", "N3": "hop", "N4": "hop", "N5": "walk", "N6": "walk"}},
    {"id": "triathlete", "name": "Triathlete (swim, roll, run)", "body": "Triathlon bot (Kestrel, Rook, Pike, Wren, Moss)", "modes": ["swim", "roll", "run"],
     "speed_studs_s": 1.55, "speed_basis": "base run 1.55, swim 0.75, bike 5.0 studs/s (sim parameters) x per-bot factors",
     "headline": [
        "island_triathlon: mean race 264.9 s with the NPC barrier vs 256.1 s without",
        "barrier cost 8.81 s per racer (CI 7.63 to 10.06)",
        "1.74 NPC passes per racer"],
     "personas": {"Kestrel": {"swim": 1.00, "bike": 1.045, "run": 0.975}, "Rook": {"swim": 1.04, "bike": 1.0, "run": 1.0},
                  "Pike": {"swim": 0.98, "bike": 1.025, "run": 1.015}, "Wren": {"swim": 1.02, "bike": 0.975, "run": 1.04},
                  "Moss": {"swim": 0.97, "bike": 0.99, "run": 0.995}},
     "nodes": {"N1": "swim", "N2": "run", "N3": "run", "N4": "run", "N5": "roll", "N6": "run"}},
    {"id": "wing_swarm", "name": "Wing-swarm bot (Clawblox humanoid)", "body": "Wing swarm bot", "modes": ["walk"], "speed_studs_s": 5.5,
     "speed_basis": "follower MoveTo speed in island_paths; the wings flap but do not fly",
     "headline": [
        "island_paths: flap phase lock in 21/24 runs (r 0.90 to 0.96)",
        "island_swarm: 15/15 Pi sessions in formation by tick 39 of 44, 0 blocked",
        "island_quorum: all 15 arrived by tick 51"],
     "nodes": {"N1": "walk", "N2": "walk", "N3": "walk", "N4": "walk", "N5": "walk", "N6": "walk"}},
    {"id": "curvity_scout", "name": "Curvity scout (centre lane)", "body": "BeetleBot, kappa < 0 in the centre lane", "modes": ["walk-centre"],
     "speed_studs_s": 1.875, "speed_basis": "0.75 stud stride vs 0.6 for the walker (x 1.25)",
     "headline": [
        "island_runway: scout raised IMPEDED 3.6 times per run",
        "kappa > 0 bots hugged the edge 93.1% of the time; the scout keeps the centre lane",
        "obstacle contacts fell from 8.35 to 2.65 per run with curvity"],
     "nodes": {"N1": "walk-centre", "N1b": "walk-centre", "N2": "walk-centre", "N3": "walk-centre", "N4": "walk-centre", "N5": "walk-centre", "N6": "walk-centre"}},
    {"id": "seed_bot", "name": "Seed bot", "body": "Seed bot", "modes": [], "speed_studs_s": None,
     "speed_basis": "no data", "headline": ["No seed-bot data yet"], "nodes": {}, "runnable": False}
  ],
  "world": {
    "ground_note": "Mesa island ground boxes from worlds/mesa-island-wings; the centre box is split so the bay x 7..34, z -50..-37 is open water",
    "bay": {"min": [7.0, -50.0], "max": [34.0, -37.0], "swim_floor_y": -1.0},
    "reef": {"min": [6.5, -49.8], "max": [29.5, -47.2], "top_y": 0.0},
    "runway": {"x": RUNWAY_X, "z": [-61.0, 61.0], "width": 16.0},
    "runway_obstacles": [
        {"kind": "car", "c": [-5.0, -40.0], "size": [2.0, 1.5, 4.4], "yaw": 25}, {"kind": "car", "c": [1.2, -28.0], "size": [2.0, 1.5, 4.4], "yaw": -15},
        {"kind": "car", "c": [4.7, -16.0], "size": [2.0, 1.5, 4.4], "yaw": 0}, {"kind": "car", "c": [-3.4, -6.0], "size": [2.0, 1.5, 4.4], "yaw": 55},
        {"kind": "car", "c": [-5.6, 35.0], "size": [2.0, 1.5, 4.4], "yaw": -20}, {"kind": "car", "c": [0.9, 44.0], "size": [2.0, 1.5, 4.4], "yaw": 30},
        {"kind": "pallet", "c": [-1.8, -34.0], "size": [1.2, 1.0, 1.6], "yaw": 10}, {"kind": "pallet", "c": [-4.8, -22.0], "size": [1.2, 0.5, 1.6], "yaw": 70},
        {"kind": "pallet", "c": [-7.6, -13.5], "size": [1.2, 1.5, 1.6], "yaw": 0}, {"kind": "pallet", "c": [1.6, 3.0], "size": [1.2, 0.5, 1.6], "yaw": 40},
        {"kind": "pallet", "c": [-1.4, 30.0], "size": [1.2, 1.0, 1.6], "yaw": -20}, {"kind": "pallet", "c": [3.4, 47.0], "size": [1.2, 0.5, 1.6], "yaw": 90},
        {"kind": "plane_fuselage", "c": [-1.5, 18.0], "size": [2.4, 2.4, 15.0], "yaw": 8},
        {"kind": "plane_wing_left", "c": [-5.0, 17.0], "size": [5.6, 0.6, 2.6], "yaw": 8}],
    "runway_obstacles_note": "nominal layout of island_runway seed jitter = 0 (u offsets converted to x = -2 + u)",
    "cota_loop_centreline": loop,
    "swim_centreline": swim,
    "summit": [20.0, -10.0]
  }
}
json.dump(course, open(OUT, "w"), indent=1)
print("wrote", OUT, len(loop), "loop pts", len(swim), "swim pts")
