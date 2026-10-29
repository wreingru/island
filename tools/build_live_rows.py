#!/usr/bin/env python3
"""Turn live Clawblox heat logs (clawblox/live/heat_s*.json, written by clawblox/race_live.py) into result rows,
record each heat as a Pi parent session with one child per bot, and append the rows to scoreboard/results.jsonl.
Only times from the world's own node log are used. A bot that did not finish is a DNF at the node it reached."""
import datetime, glob, json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runner"))
from run_race import record_pi  # same Pi recorder as the sim-bank rows
COURSE = json.load(open(os.path.join(ROOT, "course.json")))
NODES = {n["id"]: n for n in COURSE["nodes"]}
PARENT = {"N0": None, "N1": "N0", "N1b": "N1", "N2": "N1", "N3": "N2", "N4": "N3", "N5": "N4", "N6": "N5", "N7": "N6"}
BONUS = NODES["N1b"]["scoring"]["bonus_s"]

def sha():
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()

def main(paths):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    commit = sha(); rows, heats = [], []
    existing = {json.loads(l)["run_id"] for l in open(os.path.join(ROOT, "scoreboard", "results.jsonl")) if l.strip()}
    for p in paths:
        H = json.load(open(p)); seed = H["seed"]
        heat_id = f"irc-v{COURSE['version']}-live-s{seed:03d}"
        hb = []
        for slot, model in enumerate(H["order"]):
            name = f"{model}-s{seed}"; b = H["bots"][name]
            log = [e for e in b["NodeLog"] if "split" in e]
            splits = {e["node"]: round(e["split"], 2) for e in log}
            pen = [{"node": x["node"], "reason": x["reason"], "s": float(x["s"])} for x in b["Penalties"]]
            bon = [{"node": "N1b", "reason": "reef_held", "s": BONUS}] if "N1b" in splits else []
            finished = b["RaceState"] == "finished"
            order = [e["node"] for e in log]
            tree = []
            for e in log:
                nid = e["node"]
                kids = [c for c in NODES[nid]["children"] if c in order and nid != "N1b"]
                node = {"node_id": nid, "type": NODES[nid]["type"], "parent_node_id": PARENT[nid], "child_node_ids": kids,
                        "mode": e.get("mode") or "", "entered_s": e["enter"], "split_s": splits[nid], "exited_s": e["exit"],
                        "penalties_s": round(sum(x["s"] for x in pen if x["node"] == nid), 2),
                        "bonus_s": BONUS if nid == "N1b" else 0, "branch": nid == "N1b"}
                if nid == "N1b": node["rejoins"] = "N2"
                tree.append(node)
            raw = round(sum(splits.values()), 2)
            total = round(raw + sum(x["s"] for x in pen) - sum(x["s"] for x in bon), 2)
            dnf_at = None if finished else (b.get("CurrentNode") or (b["NodeLog"][-1]["node"] if b["NodeLog"] else "N0"))
            row = {"schema_version": 1, "run_id": f"{heat_id}-b{slot}", "heat_id": heat_id, "course_id": COURSE["id"],
                   "course_version": COURSE["version"], "bot_model": model, "bot_slot": slot, "bot_name": name, "seed": seed,
                   "release_offset_s": slot * COURSE["timing"]["stagger_s"], "node_splits": splits, "raw_time_s": raw,
                   "total_time_s": total, "penalties": pen, "bonuses": bon, "status": "finished" if finished else "dnf",
                   "dnf_at": dnf_at, "node_tree": tree, "source": "clawblox-live",
                   "provenance": {"kind": "measured in-world", "log": os.path.relpath(p, ROOT), "clock": "Lua os.clock from the bot's own Start"},
                   "in_world": {"port": H["port"], "speed_scale": H["speed_scale"], "cap_s": H["cap_s"], "gates": b["GateLog"],
                                "laps": b["Laps"], "energy_J_end": b["EnergyJ"], "reserve_J_start": b["reserve_J"],
                                "race_clock_end_s": b["RaceClock"], "driver_notes": len(b["notes"]), "reef_route": b["reef_route"]},
                   "commit_sha": commit, "generated_at": now,
                   "driver": "clawblox/race_live.py: fixed waypoint routes over HTTP, no LLM; times from the world's node log"}
            if row["run_id"] in existing: sys.exit(f"{row['run_id']} already in results.jsonl")
            rows.append(row)
            hb.append({"run_id": row["run_id"], "bot_name": name, "total_time_s": total, "nodes": [
                {"node_id": n["node_id"], "parent_node_id": n["parent_node_id"], "branch": n["branch"],
                 "data": {k: n[k] for k in ("node_id", "type", "mode", "entered_s", "split_s", "exited_s", "penalties_s", "bonus_s")}}
                for n in tree]})
        heats.append({"heat_id": heat_id, "model": "mixed (live)", "seed": seed, "course_id": COURSE["id"], "bots": hb})
    pi = record_pi(heats)
    if not pi: sys.exit("Pi recording failed; no rows written")
    for row in rows:
        rec = pi[row["run_id"]]
        row["pi"] = {"real": True, "llm": False, "pi_package": rec["pi_package"], **{k: rec[k] for k in (
            "session_id", "session_file", "parent_session_id", "parent_session_file")}}
        for n in row["node_tree"]:
            n["pi_entry_id"] = rec["entries"][n["node_id"]]["id"]; n["pi_parent_entry_id"] = rec["entries"][n["node_id"]]["parentId"]
        row["pi_session_ids"] = [row["pi"]["parent_session_id"], row["pi"]["session_id"]]
    with open(os.path.join(ROOT, "scoreboard", "results.jsonl"), "a") as fh:
        for row in rows: fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"appended {len(rows)} live rows ({len(heats)} heats); commit {commit}")

if __name__ == "__main__":
    main(sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "clawblox", "live", "heat_s*.json"))))
