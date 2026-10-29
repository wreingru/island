#!/usr/bin/env python3
"""Run island race heats and append result rows to scoreboard/results.jsonl.

How a race is computed (no physics is re-run here):
  * A heat = 5 bots of one model, one seed. One result row per bot.
  * Each node's time comes from a measured per-bot record in runner/bank.json (copied from the
    earlier sims), picked by seed index (seed mod number of source runs) and bot slot.
    Where no measured record exists for a model at a node, the time is derived from distance and the
    model's speed, and the row says so in `provenance`.
  * Each heat is recorded as a Pi session tree: one parent "race director" session per heat and one
    child session per bot (header.parentSession -> parent file); each visited node is a Pi `custom`
    entry chained by parentId, and the reef side objective is a Pi branch off the N1 entry.
    If Node or the Pi package is missing, ids fall back to "placeholder:" strings.

Usage: python3 runner/run_race.py --models all --seeds 0-5 [--out scoreboard/results.jsonl]
"""
import argparse, datetime, json, os, statistics as st, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COURSE = json.load(open(os.path.join(ROOT, "course.json")))
BANK = json.load(open(os.path.join(ROOT, "runner", "bank.json")))["samples"]
MODELS = {m["id"]: m for m in COURSE["bot_models"]}
NODES = {n["id"]: n for n in COURSE["nodes"]}
PERSONAS = ["Kestrel", "Rook", "Pike", "Wren", "Moss"]
WALKER_V = 1.5          # speed behind the measured BeetleBot walking samples
TIME_SCALE_HILL = 72.5  # assumption: 1.5 studs/s x 29 mm = 43.5 mm/s vs 0.6 mm/s crawl
REEF_LEN = 29.5 - 6.5
REEF_V_WALKER = 0.9     # reef walking speed used in island_reef_bay (0.6 x 1.5), assumed there
CAP_HILL_S = 7200.0

def pick(bank, seed, slot, key="seed", bot_key="bot", match=None):
    seeds = sorted({r[key] for r in BANK[bank]})
    s = seeds[seed % len(seeds)]
    rows = [r for r in BANK[bank] if r[key] == s]
    if match is not None:
        rows = [r for r in rows if r[bot_key] == match] or rows
        return rows[0], s
    if bot_key not in rows[0]:   # per-run bank (one record per source run)
        return rows[0], s
    rows = sorted(rows, key=lambda r: r[bot_key])
    return rows[slot % len(rows)], s

def speed(model, slot):
    m = MODELS[model]
    if model == "triathlete":
        return m["speed_studs_s"] * m["personas"][PERSONAS[slot]]["run"]
    return m["speed_studs_s"]

ZONE_SHARE = st.median(r["zone_s"] / r["arrival_s"] for r in BANK["runway_walk"])

def race_bot(model, seed, slot):
    v = speed(model, slot); f = WALKER_V / v
    splits, pen, bon, prov, modes, notes = {}, [], [], {}, {}, {}
    status = "finished"
    splits["N0"] = 0.0; modes["N0"] = "release"; prov["N0"] = {"kind": "rule", "stagger_s": COURSE["timing"]["stagger_s"]}
    # N1 reef swim
    if model == "triathlete":
        r, s = pick("triathlon", seed, slot, match=PERSONAS[slot])
        splits["N1"] = r["swim_s"]; modes["N1"] = "swim"; prov["N1"] = {"kind": "measured", "bank": "triathlon", "seed": s, "bot": r["bot"], "field": "swim_s"}
    else:
        splits["N1"] = round(18.0 / v, 2); modes["N1"] = "walk"
        pen.append({"node": "N1", "reason": "no_swim_shore_path", "s": NODES["N1"]["scoring"]["penalties"]["no_swim_shore_path_s"]})
        prov["N1"] = {"kind": "derived", "rule": "18 studs / speed", "speed": v}
    # N1b reef hold (side objective, one bot per heat)
    took_reef = False
    if model in NODES["N1b"]["allowed_models"]:
        r, s = pick("reef_hold", seed, slot, match=None)
        if r["reef_bots"] and r["reef_bots"][0] == slot:
            took_reef = True
            reef_v = REEF_V_WALKER / f
            splits["N1b"] = round(2 * REEF_LEN / reef_v + 10.0, 2); modes["N1b"] = modes["N1"]
            if r["success"]:
                bon.append({"node": "N1b", "reason": "reef_held", "s": NODES["N1b"]["scoring"]["bonus_s"]})
            notes["N1b"] = {"reef_success": r["success"]}
            prov["N1b"] = {"kind": "measured+derived", "bank": "reef_hold", "seed": s, "who_and_success": "measured", "time": "derived"}
    # N2 runway, N3 plane
    hop_E = 0.0
    if model == "curvity_scout":
        r, s = pick("runway_scout", seed, slot, match=None)
        splits["N2"] = round(r["scout_arrival_s"] * (1 - ZONE_SHARE), 2); splits["N3"] = round(r["scout_arrival_s"] * ZONE_SHARE, 2)
        modes["N2"] = modes["N3"] = "walk-centre"
        notes["N2"] = {"impeded_events": r["impeded_events"]}
        prov["N2"] = prov["N3"] = {"kind": "measured+derived", "bank": "runway_scout", "seed": s, "split_rule": f"plane-zone share {ZONE_SHARE:.3f} (median of walk samples)"}
    elif model == "flying_beetle":
        r, s = pick("runway_fly", seed, slot)
        splits["N2"] = r["approach_s"]; splits["N3"] = r["zone_s"]
        modes["N2"] = "walk"; modes["N3"] = "hop" if r["flyer"] else "walk"
        hop_E = round(sum(h["E"] for h in r["hops"]), 3)
        notes["N3"] = {"flew": r["flyer"], "hop_E_J": hop_E, "reserve0_J": r["reserve0_J"]}
        prov["N2"] = prov["N3"] = {"kind": "measured", "bank": "runway_fly", "seed": s, "bot": r["bot"]}
    else:
        r, s = pick("runway_walk", seed, slot)
        splits["N2"] = round(r["approach_s"] * f, 2); splits["N3"] = round(r["zone_s"] * f, 2)
        modes["N2"] = modes["N3"] = "run" if model == "triathlete" else "walk"
        k = "measured" if model == "beetle_walker" else "measured x speed ratio (assumption)"
        prov["N2"] = prov["N3"] = {"kind": k, "bank": "runway_walk", "seed": s, "bot": r["bot"], "scale": round(f, 4)}
    # N4 drone gates
    if model == "flying_beetle":
        r, s = pick("drone_gates", seed, slot)
        reserve = r["reserve0_J"] - hop_E
        gates, skipped = {}, 0
        flown = {fl["gate"]: fl for fl in r["flights"]}
        for g in ["D", "C", "B", "A"]:
            fl = flown.get(g)
            if fl and fl["res"] == "pass" and reserve >= 1.15 * fl["E"]:
                gates[g] = "pass"; reserve -= fl["E"]
            elif fl and fl["res"] != "pass":
                gates[g] = fl["res"]
                if fl["E"]: reserve -= fl["E"]
            else:
                gates[g] = "skipped"; skipped += 1
                pen.append({"node": "N4", "reason": f"gate_{g}_skipped", "s": 10.0})
        lap = r["lap_s"]
        if r["status"] != "finished" or lap is None:
            fin = [x["lap_s"] for x in BANK["drone_gates"] if x["status"] == "finished" and x["lap_s"]]
            lap = round(st.median(fin), 2); status = "rescued"
            pen.append({"node": "N4", "reason": f"rescued_{r['status']}", "s": 60.0})
        splits["N4"] = lap; modes["N4"] = "hop"
        notes["N4"] = {"gates": gates, "reserve_after_plane_J": round(r["reserve0_J"] - hop_E, 3), "source_status": r["status"]}
        prov["N4"] = {"kind": "measured (re-gated by reserve)", "bank": "drone_gates", "seed": s, "bot": r["bot"]}
    else:
        splits["N4"] = round(110.0 / v, 2); modes["N4"] = modes["N2"]
        for g in ["D", "C", "B", "A"]:
            pen.append({"node": "N4", "reason": f"gate_{g}_bypassed_on_foot", "s": 10.0})
        prov["N4"] = {"kind": "derived", "rule": "110 studs / speed", "speed": round(v, 3)}
    # N5 COTA loop
    if model == "triathlete":
        r, s = pick("triathlon", seed, slot, match=PERSONAS[slot])
        splits["N5"] = round(r["T1_s"] + r["bike_s"] + r["T2_s"], 2); modes["N5"] = "roll"
        notes["N5"] = {"npc_passes": r["npc_passes"], "npc_contacts": r["npc_contacts"], "t_behind_npc_s": r["t_behind_s"]}
        prov["N5"] = {"kind": "measured", "bank": "triathlon", "seed": s, "bot": r["bot"], "fields": ["T1_s", "bike_s", "T2_s"]}
    else:
        splits["N5"] = round(256.2 / v, 2); modes["N5"] = modes["N2"]
        prov["N5"] = {"kind": "derived", "rule": "one lap 256.2 studs / speed", "speed": round(v, 3)}
    # N6 hill with tunnels
    r, s = pick("hill_tunnels", seed, slot)
    if r["summit_s"] is None:
        splits["N6"] = round(CAP_HILL_S / TIME_SCALE_HILL * f, 2)
        pen.append({"node": "N6", "reason": "no_summit_in_cap", "s": 30.0}); status = "rescued"
    else:
        splits["N6"] = round(r["summit_s"] / TIME_SCALE_HILL * f, 2)
    modes["N6"] = "run" if model == "triathlete" else ("walk-centre" if model == "curvity_scout" else "walk")
    prov["N6"] = {"kind": "measured x time scale (assumption)", "bank": "hill_tunnels", "seed": s, "bot": r["bot"], "scale": round(f / TIME_SCALE_HILL, 6)}
    splits["N7"] = 0.0; modes["N7"] = "finish"; prov["N7"] = {"kind": "rule"}

    # node tree (bot clock; transit legs are neutral)
    order = ["N0", "N1"] + (["N1b"] if took_reef else []) + ["N2", "N3", "N4", "N5", "N6", "N7"]
    t, tree = 0.0, []
    for nid in order:
        sp = splits[nid]
        parent = {"N0": None, "N1": "N0", "N1b": "N1", "N2": "N1"}.get(nid, order[order.index(nid) - 1] if nid != "N3" else "N2")
        children = [c for c in NODES[nid]["children"] if c in order and not (nid == "N1b")]
        node = {"node_id": nid, "type": NODES[nid]["type"], "parent_node_id": parent,
                "child_node_ids": children, "mode": modes[nid], "entered_s": round(t, 2), "split_s": sp,
                "exited_s": round(t + sp, 2), "penalties_s": round(sum(p["s"] for p in pen if p["node"] == nid), 2),
                "bonus_s": round(sum(b["s"] for b in bon if b["node"] == nid), 2), "branch": nid == "N1b"}
        if nid == "N1b": node["rejoins"] = "N2"
        if nid in notes: node["notes"] = notes[nid]
        tree.append(node); t += sp
    raw = round(sum(splits.values()), 2)
    total = round(raw + sum(p["s"] for p in pen) - sum(b["s"] for b in bon), 2)
    return dict(node_splits=splits, raw_time_s=raw, total_time_s=total, penalties=pen, bonuses=bon,
                status=status, node_tree=tree, provenance=prov, speed_studs_s=round(v, 4))

def commit_sha():
    try:
        sha = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.check_output(["git", "-C", ROOT, "status", "--porcelain", "--", "runner", "course.json", "schema"], text=True).strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "uncommitted"

def record_pi(heats):
    node_bin = os.environ.get("NODE_BIN", "/workspace/island_swarm/tools/node-v22.20.0-linux-x64/bin/node")
    script = os.path.join(ROOT, "runner", "pi_record.mjs")
    import tempfile
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump({"root": ROOT, "heats": heats}, tf)
        out = subprocess.run([node_bin, script, tf.name], text=True,
                             capture_output=True, cwd=os.path.join(ROOT, "runner"), timeout=300)
        os.unlink(tf.name)
        if out.returncode != 0:
            raise RuntimeError(out.stderr[-500:])
        return json.loads(out.stdout)
    except Exception as e:
        print("Pi recording unavailable, using placeholders:", str(e)[:200], file=sys.stderr)
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="all")
    ap.add_argument("--seeds", default="0-5")
    ap.add_argument("--out", default=os.path.join(ROOT, "scoreboard", "results.jsonl"))
    a = ap.parse_args()
    models = [m for m in MODELS if MODELS[m].get("runnable", True)] if a.models == "all" else a.models.split(",")
    lo, _, hi = a.seeds.partition("-"); seeds = range(int(lo), int(hi or lo) + 1)
    sha = commit_sha(); now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    rows, heats = [], []
    for model in models:
        if not MODELS[model].get("runnable", True):
            print(f"skip {model}: no data"); continue
        for seed in seeds:
            heat_id = f"irc-v{COURSE['version']}-{model}-s{seed:03d}"
            hb = []
            for slot in range(5):
                res = race_bot(model, seed, slot)
                name = PERSONAS[slot] if model == "triathlete" else f"{model}-{slot}"
                row = {"schema_version": 1, "run_id": f"{heat_id}-b{slot}", "heat_id": heat_id, "course_id": COURSE["id"],
                       "course_version": COURSE["version"], "bot_model": model, "bot_slot": slot, "bot_name": name, "seed": seed,
                       "release_offset_s": slot * COURSE["timing"]["stagger_s"], **res, "commit_sha": sha, "generated_at": now,
                       "driver": "deterministic-runner: resampled measured sim records; no LLM, no live physics"}
                rows.append(row)
                hb.append({"run_id": row["run_id"], "bot_name": name, "nodes": [
                    {"node_id": n["node_id"], "parent_node_id": n["parent_node_id"], "branch": n["branch"],
                     "data": {k: n[k] for k in ("node_id", "type", "mode", "entered_s", "split_s", "exited_s", "penalties_s", "bonus_s")}}
                    for n in res["node_tree"]], "total_time_s": res["total_time_s"]})
            heats.append({"heat_id": heat_id, "model": model, "seed": seed, "course_id": COURSE["id"], "bots": hb})
    pi = record_pi(heats)
    for row in rows:
        rec = (pi or {}).get(row["run_id"])
        if rec:
            row["pi"] = {"real": True, "llm": False, "pi_package": rec["pi_package"], **{k: rec[k] for k in (
                "session_id", "session_file", "parent_session_id", "parent_session_file")}}
            for n in row["node_tree"]:
                n["pi_entry_id"] = rec["entries"][n["node_id"]]["id"]; n["pi_parent_entry_id"] = rec["entries"][n["node_id"]]["parentId"]
        else:
            row["pi"] = {"real": False, "llm": False, "pi_package": None, "session_id": f"placeholder:{row['run_id']}",
                         "session_file": None, "parent_session_id": f"placeholder:{row['heat_id']}", "parent_session_file": None}
            for n in row["node_tree"]:
                n["pi_entry_id"] = None; n["pi_parent_entry_id"] = None
        row["pi_session_ids"] = [row["pi"]["parent_session_id"], row["pi"]["session_id"]]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "a") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"wrote {len(rows)} rows ({len(heats)} heats) to {os.path.relpath(a.out, ROOT)}; commit {sha}; pi={'real' if pi else 'placeholder'}")

if __name__ == "__main__":
    main()
