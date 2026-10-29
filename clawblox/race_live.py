#!/usr/bin/env python3
"""Run one live heat in the Clawblox race world: 5 bots, one per bot model with data, released 15 s apart.

Usage: start a fresh world (see README), then
    python3 clawblox/race_live.py --port 8297 --seed 101 --out clawblox/live/heat_s101.json
The seed sets the release order and the flying beetle's starting energy reserve (U(10, 16) J, as in
island_drone_course). Every bot moves at its model's own speed (speed_scale 1). Routes are fixed waypoint
lists (no pathfinding). Times come only from the world's own node log; a bot that does not reach the summit
within the cap is a DNF at the node it was in.
"""
import argparse, json, math, random, threading, time, urllib.request

MODELS = ["beetle_walker", "flying_beetle", "triathlete", "curvity_scout", "wing_swarm"]
REEF_MODELS = {"beetle_walker", "flying_beetle", "curvity_scout"}
SPEED = {"beetle_walker": 1.5, "flying_beetle": 1.5, "triathlete": 1.55, "curvity_scout": 1.875, "wing_swarm": 5.5}
LANE_X, BACK_X = -11.0, -14.0   # north lane through the plane zone; separate return lane
CAP_S = 1500.0                  # race-clock cap per bot

def call(base, path, tok=None, body=None, method="GET"):
    req = urllib.request.Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Session": tok} if tok else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"{}")

def loop_route(L, laps):
    """COTA loop waypoints with detours around parts of the course the loop centreline runs into."""
    lap = []
    for i in list(range(1, len(L))) + [0]:
        if i == 6: lap.append(("move", (8.3, -25.0), 1.3))            # round the west end of ridge 1
        if i == 7: lap.append(("move", (8.3, -19.0), 1.3)); continue  # round the west end of ridge 2 (skip pt 7)
        if i == 12: lap.append(("move", (0.8, -4.6), 1.3)); continue  # round the parked car at (-3.4, -6)
        if i == 41: lap += [("move", (-3.5, 27.6), 1.3), ("move", (0.8, 27.6), 1.3)]; continue  # round the fuselage nose
        if i == 62: lap += [("move", (24.0, -16.5), 1.0), ("move", (24.0, -21.6), 1.0)]; continue  # tunnel 2
        lap.append(("move", tuple(L[i]), 2.5))
    out = []
    for k in range(laps):
        if k > 0: out += [("move", (16.0, -22.6), 1.0), ("move", (16.0, -27.6), 1.0)]  # back south through tunnel 1
        out += lap
    out += [("move", (16.0, -22.6), 1.0), ("move", (16.0, -27.6), 1.0), ("move", (25.0, -31.5), 1.3)]  # to T2
    return out

def route(model, reef, L):
    m = lambda x, z, tol=1.3: ("move", (x, z), tol)
    if model == "triathlete":
        R = [m(-12, -44.5), m(5, -44), m(10, -42), m(30.6, -44.0), m(24, -38.5), ("jump_move", (24, -35), 1.3), m(5, -36)]
    else:
        R = [m(-12, -44.5), m(5, -45), m(5, -35), m(24, -35), m(5, -35)]
        if reef: R += [m(5, -48.5), m(28.0, -48.5, 1.0), ("wait", 11), m(5, -48.5)]
    R += [m(5, -48.5), m(-2, -54), m(LANE_X, -52), m(LANE_X, 9)]
    if model == "flying_beetle": R += [("hop", (LANE_X, 27), 6.0)]
    R += [m(LANE_X, 57.5), m(BACK_X, 56), m(BACK_X, -36), m(-26, -40, 1.0)]
    if model == "flying_beetle":
        R += [("hop", (-8.5, -42.5), 5.6), m(5, -48.5), m(10.5, -48.5, 1.0), ("hop", (39.5, -44.5), 5.2),
              m(39, -35), m(17, -27.0, 1.0), ("hop", (35, -24), 6.4), m(37.5, -38), m(40, -47, 1.0),
              ("hop_or_walk", (40, -29.5), 7.0)]
    else:   # walk to the on-foot check-in pad of each gate (10 s bypass penalty each)
        R += [m(-18.5, -40, 0.8), m(-18.5, -43), m(-8.5, -42.5), m(5, -48.5), m(18.5, -48.5, 0.8), m(5, -48.5),
              m(5, -36), m(24.5, -26.8, 0.8), m(39, -35), m(37.5, -38), m(40, -39.8, 0.8), m(37.5, -38), m(40, -29.5)]
    R += [m(25, -31.5)]
    R += loop_route(L, 2 if model == "triathlete" else 1)
    R += [m(16, -28), m(16, -22), m(24, -21.5), m(24, -16), m(20, -10, 1.0)]
    return R

def drive(base, name, model, release_at, reserve, reef, L, out, log):
    tok = call(base, f"/join?name={name}", method="POST")["session"]
    inp = lambda t, d: call(base, "/input", tok, {"type": t, "data": d}, "POST")
    obs = lambda: call(base, "/observe", tok)["player"]
    sel = {"model": model, "speed_scale": 1}
    if reserve is not None: sel["reserve_J"] = reserve
    inp("SelectModel", sel)
    while time.time() < release_at: time.sleep(0.1)
    inp("Start", {}); T0 = time.time(); notes = []
    v = SPEED[model]
    def over(): return time.time() - T0 > CAP_S or obs()["attributes"].get("RaceState") == "finished"
    def goto(x, z, tol=1.3, jump=False):
        d0 = None; t_start = time.time(); detours = 0
        while True:
            inp("MoveTo", {"position": [x, 0, z]})
            p = obs()["position"]; d = math.hypot(p[0] - x, p[2] - z)
            if d0 is None: d0 = d
            if d < tol: return True
            last, t_last, reissue = p, time.time(), time.time()
            while True:
                time.sleep(0.25)
                if time.time() - reissue > 4: inp("MoveTo", {"position": [x, 0, z]}); reissue = time.time()
                p = obs()["position"]
                if math.hypot(p[0] - x, p[2] - z) < tol: return True
                if math.hypot(p[0] - last[0], p[2] - last[2]) > 0.3: last, t_last = p, time.time()
                elif time.time() - t_last > 2.0 or jump: break
                if time.time() - T0 > CAP_S: return False
            jump = False
            inp("Jump", {}); time.sleep(0.6)
            if time.time() - t_start > (d0 / v) * 2 + 25 or detours >= 6:
                notes.append(f"gave up reaching ({x},{z}) from ({p[0]:.1f},{p[2]:.1f})"); log(f"[{name}] gave up -> ({x},{z})"); return False
            # sidestep perpendicular to the heading, alternating sides, then retry
            hx, hz = x - p[0], z - p[2]; n = math.hypot(hx, hz) or 1
            side = 1 if detours % 2 == 0 else -1; detours += 1
            sx, sz = p[0] - hz / n * 3 * side, p[2] + hx / n * 3 * side
            notes.append(f"stall at ({p[0]:.1f},{p[2]:.1f}) -> sidestep to ({sx:.1f},{sz:.1f})")
            inp("MoveTo", {"position": [sx, 0, sz]}); time.sleep(min(4, 3 / v + 1))
    for step in route(model, reef, L):
        if over(): break
        kind = step[0]
        if kind in ("move", "jump_move"):
            goto(*step[1], tol=step[2], jump=(kind == "jump_move"))
        elif kind == "wait":
            time.sleep(step[1])
        elif kind in ("hop", "hop_or_walk"):
            (x, z), apex = step[1], step[2]
            inp("Hop", {"to": [x, 2.83, z], "apex": apex}); time.sleep(0.3)
            res = obs()["attributes"].get("LastActionResult")
            if res != "Hopping":
                notes.append(f"hop to ({x},{z}) -> {res}")
                if kind == "hop_or_walk": goto(37.5, -38); goto(40, -39.8, 0.8); goto(37.5, -38)
                goto(x, z)
            else:
                time.sleep(2.22 + 0.6)
        a = obs()["attributes"]
        log(f"[{name} {time.time() - T0:6.1f}s] {a.get('CurrentNode') or '-'} after {step[0]} {step[1]}")
    time.sleep(1)
    a = obs()["attributes"]
    out[name] = {"model": model, "release_at_s": round(release_at - out["_t0"], 2), "reserve_J": reserve, "reef_route": reef,
                 "RaceState": a.get("RaceState"), "CurrentNode": a.get("CurrentNode"), "RaceClock": a.get("RaceClock"),
                 "NodeLog": json.loads(a.get("NodeLog") or "[]"), "Penalties": json.loads(a.get("Penalties") or "[]"),
                 "GateLog": json.loads(a.get("GateLog") or "{}"), "Laps": a.get("Laps"), "EnergyJ": a.get("EnergyJ"),
                 "wall_s": round(time.time() - T0, 1), "notes": notes}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True); ap.add_argument("--seed", type=int, required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); base = f"http://localhost:{a.port}"
    rng = random.Random(a.seed)
    order = rng.sample(MODELS, len(MODELS))
    reserve = round(rng.uniform(10, 16), 2)
    L = json.load(open("course.json"))["world"]["cota_loop_centreline"]
    reef_bot = next(mm for mm in order if mm in REEF_MODELS)   # one bot per heat: first reef-capable bot released
    lock = threading.Lock()
    def log(s):
        with lock: print(s, flush=True)
    out = {"_t0": time.time() + 3}; th = []
    for i, model in enumerate(order):
        name = f"{model}-s{a.seed}"
        t = threading.Thread(target=drive, args=(base, name, model, out["_t0"] + i * 15.0, reserve if model == "flying_beetle" else None,
                                                 model == reef_bot, L, out, log))
        t.start(); th.append(t); time.sleep(0.3)
    for t in th: t.join()
    t0 = out.pop("_t0")
    res = {"seed": a.seed, "port": a.port, "order": order, "flyer_reserve_J": reserve, "reef_bot": reef_bot, "speed_scale": 1,
           "cap_s": CAP_S, "started_unix": round(t0, 1), "bots": out}
    import os; os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    for k, v in out.items():
        print(k, v["RaceState"], v["CurrentNode"], [(n["node"], n.get("split")) for n in v["NodeLog"]], v["Penalties"])
