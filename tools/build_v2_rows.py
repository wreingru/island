#!/usr/bin/env python3
"""Build the v2 scoreboard rows and write scoreboard/results.jsonl (the v2 branch holds v2 rows only; v1 rows are on main).

Sources (no time is made up; every split is a difference of logged node-entry times):
  runner/v2_heats.json              held-out sim heats (runner/eval_v2.py, seeds 1000-1039, full boundary), 15 bots each
  clawblox/live_v2/heat_s*.json     live v2 heats (clawblox/race_live_v2.py), 5 bots each; stop times from the world log
Split rule: N0 = release to N1 entry; Nk = N(k+1) entry - Nk entry; N6 (finish) = 0. A DNF keeps the splits of the nodes
it completed and is recorded at the node it was in (dnf_at) with the reason (water, energy, cap, fell).
Each heat is one Pi parent session with one child session per bot (llm: false)."""
import datetime, glob, json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runner"))
from pi_util import record_pi
COURSE = json.load(open(os.path.join(ROOT, "course.json")))
NODES = {n["id"]: n for n in COURSE["nodes"]}
ORDER = ["N0", "N1", "N2", "N3", "N4", "N5", "N6"]
r2 = lambda x: round(float(x), 2)

def sha():
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()

def tree_and_splits(entry, stop_t, finished):
    """entry: {node: entry time} for nodes reached (N0 at 0). Returns splits (completed nodes), tree, dnf_at."""
    reached = [n for n in ORDER if entry.get(n) is not None]
    splits, tree = {}, []
    for i, nid in enumerate(reached):
        nxt = reached[i + 1] if i + 1 < len(reached) else None
        if nid == "N6":
            sp, ex = 0.0, entry[nid]
        elif nxt is not None:
            sp, ex = r2(entry[nxt] - entry[nid]), entry[nxt]
        else:
            sp, ex = None, stop_t
        node = {"node_id": nid, "type": NODES[nid]["type"], "parent_node_id": ORDER[ORDER.index(nid) - 1] if nid != "N0" else None,
                "child_node_ids": [nxt] if nxt else [], "mode": "release" if nid == "N0" else ("finish" if nid == "N6" else "walk"),
                "entered_s": r2(entry[nid]), "split_s": sp if sp is not None else r2(max(0.0, (stop_t if stop_t is not None else entry[nid]) - entry[nid])),
                "exited_s": r2(ex if ex is not None else entry[nid]), "penalties_s": 0, "bonus_s": 0, "branch": False}
        if sp is None: node["notes"] = {"partial": True, "stopped_s": stop_t, "note": "time in this node until the bot stopped; not a completed split"}
        else: splits[nid] = sp
        tree.append(node)
    dnf_at = None if finished else reached[-1]
    return splits, tree, dnf_at

def base_row(heat_id, slot, name, seed, splits, tree, status, dnf_at, reason, boundary, source, prov, driver, commit, now):
    raw = r2(sum(splits.values()))
    row = {"schema_version": 1, "run_id": f"{heat_id}-b{slot}", "heat_id": heat_id, "course_id": COURSE["id"], "course_version": 2,
           "bot_model": "wing_swarm", "bot_slot": slot, "bot_name": name, "seed": seed, "release_offset_s": 0.0,
           "speed_studs_s": 5.5, "node_splits": splits, "raw_time_s": raw, "total_time_s": raw, "penalties": [], "bonuses": [],
           "status": status, "dnf_at": dnf_at, "node_tree": tree, "boundary": boundary, "source": source, "provenance": prov,
           "commit_sha": commit, "generated_at": now, "driver": driver}
    if status == "dnf": row["dnf_reason"] = reason
    return row

def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"); commit = sha()
    rows, heats = [], []
    H = json.load(open(os.path.join(ROOT, "runner", "v2_heats.json")))
    for sd in sorted(H, key=int):
        h = H[sd]; seed = int(sd); heat_id = f"irc-v2-sim-s{seed:04d}"; hb = []
        for b in range(len(h["finished"])):
            entry = {"N0": 0.0, **{k: h["node_t"][k][b] for k in h["node_t"]}}
            fin = h["finished"][b]
            if fin: entry["N6"] = h["finish_s"][b]
            else: entry["N6"] = None
            reason = None if fin else ("water" if h["lost_in_water"][b] else "energy" if h["downed"][b] else "cap")
            stop = h["stop_s"][b] if not fin else None
            if reason == "cap": stop = h["t_cap"]
            splits, tree, dnf_at = tree_and_splits(entry, stop, fin)
            bnd = {"energy_end": h["energy_end"][b], "outside_s": h["outside_s"][b], "exits": int(h["exits"][b]),
                   "heat_formation_breaks": h["formation_breaks"], "heat_gust_peak": h["gust_peak"], "config": h["cfg"]}
            row = base_row(heat_id, b, f"wing_swarm-{b}", seed, splits, tree, "finished" if fin else "dnf", dnf_at, reason, bnd, "sim-v2",
                           {"kind": "simulated (held-out evaluation seed)", "file": "runner/v2_heats.json", "sim": "runner/squall_sim.py",
                            "tuning_seeds": "0-11", "eval_seeds": "1000-1039"},
                           "runner/squall_sim.py: 15-bot lane controller, no LLM; boundary = squall line + gust shore", commit, now)
            rows.append(row); hb.append(row)
        heats.append((heat_id, seed, hb))
    for p in sorted(glob.glob(os.path.join(ROOT, "clawblox", "live_v2", "heat_s*.json"))):
        L = json.load(open(p)); seed = L["seed"]; heat_id = f"irc-v2-live-s{seed:04d}"; hb = []
        wl = [json.loads(l[5:]) for l in open(p.replace(".json", "_world_log.jsonl"))]
        stops = {e["player"]: e for e in wl if e["ev"] in ("LOST", "DOWNED", "TIMEOUT")}
        for name in sorted(L["bots"]):
            b = L["bots"][name]; slot = b["slot"]
            entry = {e["node"]: e["enter"] for e in b["NodeLog"]}
            fin = b["RaceState"] == "finished"
            st = stops.get(name)
            reason = None if fin else {"water": "water", "fell": "fell", "energy": "energy", "cap": "cap"}[st["reason"]]
            splits, tree, dnf_at = tree_and_splits(entry, st["t"] if st else None, fin)
            bnd = {"energy_end": b["Energy"], "outside_s": b["OutsideS"], "exits": int(b["Exits"]), "heat_formation_breaks": L["formation_breaks"],
                   "heat_gust_peak": None, "config": {k: v for k, v in H[next(iter(H))]["cfg"].items()}}
            row = base_row(heat_id, slot, name, seed, splits, tree, "finished" if fin else "dnf", dnf_at, reason, bnd, "clawblox-live",
                           {"kind": "measured in-world", "log": os.path.relpath(p, ROOT), "world_log": os.path.relpath(p.replace(".json", "_world_log.jsonl"), ROOT),
                            "clock": "Lua os.clock from the swarm's release (first Start)", "port": L["port"]},
                           "clawblox/race_live_v2.py: lane controller over HTTP (MoveTo), no LLM; times from the world's node log", commit, now)
            row["in_world"] = {"port": L["port"], "race_state": b["RaceState"], "progress_studs": b["Progress"]}
            rows.append(row); hb.append(row)
        heats.append((heat_id, seed, hb))
    pi_in = [{"heat_id": hid, "model": "wing_swarm", "seed": seed, "course_id": COURSE["id"], "bots": [
        {"run_id": r["run_id"], "bot_name": r["bot_name"], "total_time_s": r["total_time_s"], "nodes": [
            {"node_id": n["node_id"], "parent_node_id": n["parent_node_id"], "branch": False,
             "data": {k: n[k] for k in ("node_id", "type", "mode", "entered_s", "split_s", "exited_s")}} for n in r["node_tree"]]}
        for r in hb]} for hid, seed, hb in heats]
    pi = record_pi(pi_in)
    if not pi: sys.exit("Pi recording failed; no rows written")
    for row in rows:
        rec = pi[row["run_id"]]
        row["pi"] = {"real": True, "llm": False, "pi_package": rec["pi_package"], **{k: rec[k] for k in ("session_id", "session_file", "parent_session_id", "parent_session_file")}}
        for n in row["node_tree"]:
            n["pi_entry_id"] = rec["entries"][n["node_id"]]["id"]; n["pi_parent_entry_id"] = rec["entries"][n["node_id"]]["parentId"]
        row["pi_session_ids"] = [row["pi"]["parent_session_id"], row["pi"]["session_id"]]
    with open(os.path.join(ROOT, "scoreboard", "results.jsonl"), "w") as fh:
        for row in rows: fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"wrote {len(rows)} v2 rows ({len(heats)} heats); commit {commit}")

if __name__ == "__main__":
    main()
