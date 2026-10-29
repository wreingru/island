#!/usr/bin/env python3
"""Drive bots through the Clawblox race world over HTTP and save their node logs.

Usage: start the world (see README), then  python3 clawblox/test_drive.py --port 8295
The route is a fixed list of waypoints per model (no pathfinding). Bots that stall get one Jump and a retry.
"""
import argparse, json, math, threading, time, urllib.request

def call(base, path, tok=None, body=None, method="GET"):
    req = urllib.request.Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Session": tok} if tok else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"{}")

LANE_X = -11.0  # clear lane just west of the runway (obstacles sit on the runway)

def route(model):
    R = [("move", (-12, -44.5)), ("move", (5, -45)), ("move", (5, -35))]
    if model == "triathlete":
        R = [("move", (-12, -44.5)), ("move", (5, -44)), ("move", (10, -42)), ("move", (30.6, -44.0)), ("move", (24, -38.5)), ("jump_move", (24, -35))]
        R += [("move", (5, -36)), ("move", (5, -48.5))]
    else:
        R += [("move", (24, -35)),                                    # shore path end (N1 exit)
              ("move", (5, -35)), ("move", (5, -48.5)), ("move", (28.0, -48.5)), ("wait", 11), ("move", (5, -48.5))]  # reef hold
    R += [("move", (-2, -54)), ("move", (LANE_X, -52)), ("move", (LANE_X, 9))]
    if model == "flying_beetle":
        R += [("hop", (LANE_X, 27), 6.0)]
    R += [("move", (LANE_X, 57.5)), ("move", (LANE_X, -36)), ("move", (-26, -40))]
    if model == "flying_beetle":
        R += [("hop", (-8.5, -42.5), 5.6), ("move", (5, -48.5)), ("move", (10.5, -48.5)), ("hop", (39.5, -44.5), 5.2),
              ("move", (39, -35)), ("move", (17, -26)), ("hop", (35, -24), 6.4),
              ("hop_or_walk", (40, -29.5), 7.0, (41.5, -38)), ("move", (40, -29.5))]
    else:
        R += [("move", (-15.5, -40)), ("move", (-8.5, -42.5)), ("move", (5, -48.5)), ("move", (21.5, -48.5)), ("move", (5, -48.5)),
              ("move", (5, -36)), ("move", (27.5, -26)), ("move", (39, -35)), ("move", (41.5, -38)), ("move", (40, -29.5))]
    R += [("move", (25, -31.5)), ("loop", None), ("move", (25, -31.5))]
    R += [("move", (16, -28)), ("move", (16, -22)), ("move", (24, -21)), ("move", (24, -16)), ("move", (20, -10))]
    return R

def drive(base, name, model, scale, loop_pts, laps, out):
    tok = call(base, f"/join?name={name}", method="POST")["session"]
    inp = lambda t, d: call(base, "/input", tok, {"type": t, "data": d}, "POST")
    obs = lambda: call(base, "/observe", tok)["player"]
    inp("SelectModel", {"model": model, "speed_scale": scale}); time.sleep(0.5); inp("Start", {})
    notes = []
    def goto(x, z, jump=False):
        for attempt in range(3):
            inp("MoveTo", {"position": [x, 0, z]})
            p = obs()["position"]; d0 = math.hypot(p[0] - x, p[2] - z); t0 = time.time(); last = (p, time.time())
            reissue = time.time()
            while time.time() - t0 < d0 / 1.2 + 6:
                time.sleep(0.25)
                if time.time() - reissue > 5:   # Humanoid:MoveTo gives up after about 8 s, so re-issue it
                    inp("MoveTo", {"position": [x, 0, z]}); reissue = time.time()
                p = obs()["position"]
                if math.hypot(p[0] - x, p[2] - z) < 1.3:
                    return True
                if math.hypot(p[0] - last[0][0], p[2] - last[0][2]) > 0.3: last = (p, time.time())
                elif time.time() - last[1] > 1.5 or jump:
                    inp("Jump", {}); inp("MoveTo", {"position": [x, 0, z]}); last = (p, time.time()); jump = False
            print(f"[{name}] stall near ({p[0]:.1f},{p[2]:.1f}) -> ({x},{z})", flush=True); notes.append(f"stall near ({p[0]:.1f},{p[2]:.1f}) heading to ({x},{z}) attempt {attempt + 1}")
        return False
    T0 = time.time()
    for step in route(model):
        kind = step[0]
        p = obs(); print(f"[{name} {time.time() - T0:6.1f}s] {p['attributes'].get('CurrentNode') or '-'} at ({p['position'][0]:.1f},{p['position'][2]:.1f}) -> {step}", flush=True)
        if kind in ("move", "jump_move"):
            goto(*step[1], jump=(kind == "jump_move"))
        elif kind == "wait":
            time.sleep(step[1])
        elif kind in ("hop", "hop_or_walk"):
            (x, z), apex = step[1], step[2]
            inp("Hop", {"to": [x, 2.83, z], "apex": apex}); time.sleep(0.3)
            res = obs()["attributes"].get("LastActionResult")
            if res != "Hopping":
                notes.append(f"hop to ({x},{z}) -> {res}")
                if kind == "hop_or_walk": goto(*step[3])
                goto(x, z)
            else:
                time.sleep(2.4 / scale + 0.5)
        elif kind == "loop":
            for _ in range(laps[model]):
                for i in list(range(1, len(loop_pts))) + [0]:
                    goto(*loop_pts[i])
    time.sleep(1)
    a = obs()["attributes"]
    out[name] = {"model": model, "speed_scale": scale, "RaceState": a.get("RaceState"), "NodeLog": json.loads(a.get("NodeLog") or "[]"),
                 "Penalties": json.loads(a.get("Penalties") or "[]"), "GateLog": json.loads(a.get("GateLog") or "{}"),
                 "Laps": a.get("Laps"), "EnergyJ": a.get("EnergyJ"), "notes": notes}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8295); ap.add_argument("--out", default="clawblox/test_run.json")
    a = ap.parse_args(); base = f"http://localhost:{a.port}"
    course = json.load(open("course.json"))
    loop_pts = [tuple(p) for p in course["world"]["cota_loop_centreline"]]
    laps = {"triathlete": 2, "flying_beetle": 1}
    out, th = {}, []
    for name, model, scale in [("fly1", "flying_beetle", 4.0), ("tri1", "triathlete", 3.0)]:
        t = threading.Thread(target=drive, args=(base, name, model, scale, loop_pts, laps, out)); t.start(); th.append(t)
    for t in th: t.join()
    json.dump(out, open(a.out, "w"), indent=1)
    for k, v in out.items():
        print(k, v["model"], v["RaceState"], [(n["node"], n.get("split")) for n in v["NodeLog"]], v["GateLog"], v["Penalties"], v["notes"][:6])
