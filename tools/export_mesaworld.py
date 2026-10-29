#!/usr/bin/env python3
"""Write mesaworld/course_spec.json: an engine-neutral copy of the course for any Mesa World host.

"Mesa World" is the Clawblox world worlds/mesa-island (formerly worlds/mesa-world) in github.com/nacloos/clawblox,
so the Clawblox world in clawblox/ is the primary host. This file is for hosts that are not Clawblox
(or for patching the race into the stock mesa-island world): plain geometry, nodes, rules and the result schema id.
"""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
c = json.load(open(os.path.join(ROOT, "course.json")))
spec = {
    "spec": "island-race-course/v1",
    "course_id": c["id"], "course_version": c["version"], "title": c["title"],
    "coordinate_frame": {"origin": "Mesa island centre (Clawblox worlds/mesa-island)", "x": "east", "z": "north", "y": "up", "ground_top_y": 0, "unit": "stud"},
    "required_engine_features": ["static boxes (anchored parts)", "a walkable avatar with move-to", "per-tick position read for zone checks",
                                 "a kinematic hop (or any flight) for gate passes", "an event log per bot"],
    "timing": c["timing"],
    "nodes": [{k: n[k] for k in n if k not in ("source",)} for n in c["nodes"]],
    "bot_models": [{k: m[k] for k in ("id", "name", "modes", "speed_studs_s", "nodes")} for m in c["bot_models"]],
    "world": c["world"],
    "result_schema": "schema/result.schema.json",
    "event_log_format": "one JSON object per event: {ev: NODE_ENTER|NODE_EXIT|GATE|LAP|TUNNEL|PENALTY|FINISH, player, node, t}"
}
os.makedirs(os.path.join(ROOT, "mesaworld"), exist_ok=True)
json.dump(spec, open(os.path.join(ROOT, "mesaworld", "course_spec.json"), "w"), indent=1)
print("wrote mesaworld/course_spec.json")
