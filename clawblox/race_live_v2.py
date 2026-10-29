#!/usr/bin/env python3
"""Run one live v2 heat in the Clawblox world: 5 wing-swarm bots against the squall line.

Usage: start a fresh v2 world (see README), then
    python3 clawblox/race_live_v2.py --port 8301 --seed 2001 --out clawblox/live/v2_heat_s2001.json
Control is the same lane controller as runner/squall_sim.py: each bot keeps its own lane (5 lanes across the
corridor half-width), aims its carrot at the squall centre's arc position, steps round obstacles, and makes a
short random lane change after 2 s with no progress. The world itself moves the squall, blows the gust, drains
energy and decides lost / downed / finished; times come only from the world's node log (NodeLog attribute).
"""
import argparse, json, math, os, random, sys, threading, time, urllib.request
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runner")); import squall_sim as S

LANES = [-0.8, -0.4, 0.0, 0.4, 0.8]
LON = [4.0, 2.0, 0.0, -2.0, -4.0]    # arc offsets from the squall centre: a staggered echelon, so bots do not pile up where lanes merge
SEP = 3.0                            # separation radius (character collisions in a crowd flung bots off the island in s2001-s2003)
WIDE = np.linspace(-5.0, 5.0, 21)
def carrot(P, s_t, lane_frac):
    """lane point at arc s_t; if it or the straight approach is blocked, the nearest clear lateral offset up to 5 studs
    (the sim's corridor half-width can be narrower than the car-free gap in the plane zone)"""
    pt, tan = S.at(np.array([s_t])); nrm = np.array([-tan[0, 1], tan[0, 0]])
    pref = lane_frac * float(S.half_width(np.array([s_t]))[0])
    Q = pt[0][None, :] + nrm[None, :] * WIDE[:, None]
    ok = S.clearance(Q, OBS) > S.R_BOT + 0.3
    for f in (0.33, 0.66):
        ok &= S.clearance(P[None, :] + (Q - P[None, :]) * f, OBS) > S.R_BOT + 0.1
    cost = np.abs(WIDE - pref) + np.where(ok, 0, 1e3)
    return Q[int(cost.argmin())]
OBS = S.obstacles()
# The driver plans with a wider body (1.3 studs vs the sim's 0.9) and with each yawed obstacle at both yaw signs,
# so its carrots stay clear whichever rotation convention the engine uses (bots pinned on the plane-zone car in heats s2001-s2002).
OBS = OBS + [(c, h, -y) for c, h, y in OBS if y]
S.R_BOT = 1.3

def call(base, path, tok=None, body=None, method="GET"):
    req = urllib.request.Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Session": tok} if tok else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"{}")

def drive(base, name, slot, seed, go, shared, out, log):
    tok = call(base, f"/join?name={name}", method="POST")["session"]
    inp = lambda t, d: call(base, "/input", tok, {"type": t, "data": d}, "POST")
    obs = lambda: call(base, "/observe", tok)["player"]
    rng = random.Random(seed * 10 + slot)
    go.wait(); inp("Start", {"seed": seed})
    pref = LANES[slot]; last_s, t_prog, escape_until = 0.0, time.time(), 0.0
    T0 = time.time()
    while True:
        o = obs(); a = o["attributes"]; p = o["position"]
        shared[name] = {"pos": [p[0], p[2]], "state": a.get("RaceState"), "E": a.get("Energy"), "s": a.get("Progress"),
                        "sq": [a.get("SquallX"), a.get("SquallZ"), a.get("SquallR")], "gust": a.get("Gust"), "t": a.get("RaceClock")}
        if a.get("RaceState") != "racing" or time.time() - T0 > 260: break
        s_bot, s_sq = float(a.get("Progress") or 0), float(a.get("SquallS") or 0)
        s_goal = s_sq + LON[slot]
        if s_bot > last_s + 0.3: last_s, t_prog = s_bot, time.time()
        lane = pref
        if s_bot > s_goal + 2.0: t_prog = time.time()          # holding behind the squall front is not a stall
        if time.time() - t_prog > 2.0 and time.time() > escape_until:
            # stall: back off 3 studs along the path on a random lane for 2 s, with a jump
            escape_until = time.time() + 2.0; lane_esc = rng.uniform(-1, 1)
            pt, tan = S.at(np.array([max(0.0, s_bot - 3.0)])); nrm = np.array([-tan[0, 1], tan[0, 0]])
            q = pt[0] + nrm * lane_esc * float(S.half_width(np.array([s_bot]))[0])
            inp("MoveTo", {"position": [float(q[0]), 0, float(q[1])]}); time.sleep(1.0)
            t_prog = time.time()
        if time.time() < escape_until: lane = lane_esc
        target = min(S.L_PATH, max(s_bot + 0.5, min(s_bot + 4.0, s_goal + 1.0)))
        if s_bot >= S.L_PATH - 3: target = S.L_PATH
        if s_bot > s_goal + 2.0 and s_bot < S.L_PATH - 3:
            inp("Stop", {})
        else:
            c = carrot(np.array([p[0], p[2]]), target, lane)
            for k, b in list(shared.items()):   # separation from racing neighbours within 2 studs
                if k != name and b.get("state") == "racing":
                    d = np.array([p[0] - b["pos"][0], p[2] - b["pos"][1]]); n = float(np.hypot(*d))
                    if 1e-3 < n < SEP: c = c + d / n * (SEP - n)
            inp("MoveTo", {"position": [float(c[0]), 0, float(c[1])]})
        time.sleep(0.25)
    time.sleep(0.5); a = obs()["attributes"]
    out[name] = {"slot": slot, "lane": pref, "RaceState": a.get("RaceState"), "CurrentNode": a.get("CurrentNode"),
                 "RaceClock": a.get("RaceClock"), "NodeLog": json.loads(a.get("NodeLog") or "[]"), "Energy": a.get("Energy"),
                 "OutsideS": a.get("OutsideS"), "Exits": a.get("Exits"), "Progress": a.get("Progress")}
    log(f"[{name}] {a.get('RaceState')} at {a.get('CurrentNode')} t={a.get('RaceClock')} E={a.get('Energy')}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True); ap.add_argument("--seed", type=int, required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); base = f"http://localhost:{a.port}"
    lock = threading.Lock()
    def log(s):
        with lock: print(s, flush=True)
    go = threading.Event(); shared, out, th = {}, {}, []
    for slot in range(5):
        t = threading.Thread(target=drive, args=(base, f"wing_swarm-{slot}", slot, a.seed, go, shared, out, log)); t.start(); th.append(t); time.sleep(0.5)
    time.sleep(3); go.set(); t0 = time.time(); frames = []
    while any(t.is_alive() for t in th):
        time.sleep(0.5)
        frames.append({"wall": round(time.time() - t0, 2), "bots": json.loads(json.dumps(shared))})
    for t in th: t.join()
    # formation breaks: proximity graph (link <= 5 studs) among racing bots goes from 1 component to more than 1
    def comps(pts):
        n = len(pts); seen, k = set(), 0
        for i in range(n):
            if i in seen: continue
            k += 1; st = [i]
            while st:
                j = st.pop()
                if j in seen: continue
                seen.add(j); st += [m for m in range(n) if m not in seen and math.dist(pts[j], pts[m]) <= 5]
        return k
    breaks, prev = 0, 1
    for f in frames:
        pts = [b["pos"] for b in f["bots"].values() if b.get("state") == "racing"]
        c = comps(pts) if len(pts) > 1 else 1
        if prev == 1 and c > 1: breaks += 1
        prev = c
    res = {"seed": a.seed, "port": a.port, "course_id": "mesa-island-race-v2", "bots": out, "formation_breaks": breaks,
           "frames": frames, "started_unix": round(t0, 1)}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True); json.dump(res, open(a.out, "w"))
    for k in sorted(out): v = out[k]; print(k, v["RaceState"], v["CurrentNode"], [(n["node"], n.get("split")) for n in v["NodeLog"]], v["Energy"])
    print("formation breaks", breaks)
