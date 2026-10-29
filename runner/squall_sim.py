#!/usr/bin/env python3
"""Course v2 sim: a wing swarm of 15 bots runs the Mesa island course inside the moving "squall line".

The boundary has two parts (both are course-design choices for v2, tuned below):
  1. Squall disc: a circle whose centre moves along the course centreline at a fixed pace (v_b studs/s) and
     shrinks from R0 to R_min. Outside it a bot drains energy fast. Running ahead is also outside, so the
     wing swarm's 5.5 studs/s top speed does not shorten the race; it has to stay together in the disc.
  2. Gust shore: the former reef bay is open water (no reef to stand on). The route runs along a 6-stud strip
     between the water and a new cliff wall, with a crosswind pushing bots toward the water. A bot whose centre
     enters the water is lost (the wing swarm cannot swim or fly).
Bots: point-mass discs (r 0.9), top speed 5.5 studs/s (wing-swarm MoveTo speed in island_paths), separation,
a formation slot around the disc centre, collision with the course's static parts. All rates below are assumptions.
"""
import json, math, sys
import numpy as np

import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COURSE = json.load(open(os.path.join(ROOT, "course.json")))
assert COURSE["version"] == 2, "squall_sim needs the v2 course.json"
BND = COURSE["boundary"]
V_MAX = 5.5; V_FREE = 4.5; R_BOT = 0.9; N_BOTS = COURSE["swarm"]["size_sim"]; DT = 0.1; E0 = BND["energy"]["E0"]
PATH = np.array(COURSE["centreline"], float)
NODE_AT = {n["id"]: n["starts_at_centreline_vertex"] for n in COURSE["nodes"] if "starts_at_centreline_vertex" in n}
_bay = COURSE["world"]["bay"]; WATER = (_bay["min"][0], _bay["max"][0], _bay["min"][1], _bay["max"][1])
_g = BND["gust_shore"]["box"]; GUST_BOX = (_g["min"][0], _g["max"][0], _g["min"][1], _g["max"][1])
SUMMIT, SUMMIT_R = np.array(COURSE["world"]["summit"], float), 2.5
HW = BND["lane_half_width"]
CFG = dict(v_b=BND["squall"]["pace_studs_s"], R0=BND["squall"]["R0"], R_min=BND["squall"]["R_min"],
           gust_mu=BND["gust_shore"]["ou_mean_studs_s"], gust_sigma=BND["gust_shore"]["ou_sigma"],
           out_drain=BND["squall"]["outside_energy_drain_per_s"], base_drain=BND["energy"]["base_drain_per_s"],
           effort=BND["energy"]["effort_drain_per_s_per_speed2"])

def rect(c, size, yaw):
    return (np.array(c, float), np.array(size, float) / 2, math.radians(yaw))

def obstacles(course=COURSE):
    W = course["world"]; obs = []
    for o in W["runway_obstacles"]:
        if o["size"][1] <= 0.6: continue          # 0.5-0.6 stud pallets and the low wing are stepped over
        obs.append(rect(o["c"], (o["size"][0], o["size"][2]), o["yaw"]))
    cw = W["cliff_wall"]                                   # v2 cliff wall along the shore
    obs.append(rect(((cw["min"][0] + cw["max"][0]) / 2, (cw["min"][1] + cw["max"][1]) / 2), (cw["max"][0] - cw["min"][0], cw["max"][1] - cw["min"][1]), 0))
    for r in W["ridges"]:                                  # hill ridges with 3-stud tunnels
        a, b = r["x"][0], r["tunnel_x"] - 1.5; obs.append(rect(((a + b) / 2, r["z"]), (b - a, 2.0), 0))
        a, b = r["tunnel_x"] + 1.5, r["x"][1]; obs.append(rect(((a + b) / 2, r["z"]), (b - a, 2.0), 0))
    return obs

def avoid(P, v, obs, reach=1.6):
    """repulsion from nearby obstacles plus a slide along their face, so bots flow round instead of pinning"""
    out = np.zeros_like(v)
    for c, h, yaw in obs:
        cs, sn = math.cos(yaw), math.sin(yaw); d = P - c
        lx = d[:, 0] * cs - d[:, 1] * sn; lz = d[:, 0] * sn + d[:, 1] * cs
        qx = np.clip(lx, -h[0], h[0]); qz = np.clip(lz, -h[1], h[1])
        nx, nz = lx - qx, lz - qz; g = np.hypot(nx, nz) - R_BOT
        near = g < reach
        if not near.any(): continue
        nn = np.maximum(np.hypot(nx, nz), 1e-6); nx, nz = nx / nn, nz / nn
        wx, wz = nx * cs + nz * sn, -nx * sn + nz * cs            # normal back in world frame
        n = np.stack([wx, wz], 1); tng = np.stack([-wz, wx], 1)
        vt = (v * tng).sum(1, keepdims=True); side = np.where(vt >= 0, 1.0, -1.0)
        k = np.clip((reach - g) / reach, 0, 1)[:, None] * near[:, None]
        vn = (v * n).sum(1, keepdims=True)
        out += k * (n * (np.maximum(0, -vn) + 1.0) + tng * side * np.abs(vn))
    return out

def clearance(Q, obs):
    """distance from points Q (..., 2) to the nearest obstacle surface (negative inside)"""
    best = np.full(Q.shape[:-1], 99.0)
    for c, h, yaw in obs:
        cs, sn = math.cos(yaw), math.sin(yaw); d = Q - c
        lx = np.abs(d[..., 0] * cs - d[..., 1] * sn) - h[0]; lz = np.abs(d[..., 0] * sn + d[..., 1] * cs) - h[1]
        out = np.hypot(np.maximum(lx, 0), np.maximum(lz, 0)); ins = np.minimum(np.maximum(lx, lz), 0)
        best = np.minimum(best, out + ins)
    return best

OFFS = np.linspace(-1.0, 1.0, 11)
def pick_carrot(P, p_t, nrm, hw, pref, obs):
    """carrot on the path normal at the bot's preferred offset, or the nearest offset whose point and straight
    approach are clear of obstacles (a local lane change)"""
    o = OFFS[None, :] * hw[:, None]                                   # (n, k) candidate lateral offsets
    Q = p_t[:, None, :] + nrm[:, None, :] * o[..., None]
    ok = clearance(Q, obs) > R_BOT + 0.3
    for f in (0.33, 0.66):
        ok &= clearance(P[:, None, :] + (Q - P[:, None, :]) * f, obs) > R_BOT + 0.1
    cost = np.abs(o - pref[:, None]) + np.where(ok, 0, 1e3)
    j = cost.argmin(1); return Q[np.arange(len(P)), j]

def push_out(P, obs):
    for c, h, yaw in obs:
        cs, sn = math.cos(yaw), math.sin(yaw)
        d = P - c
        lx = d[:, 0] * cs - d[:, 1] * sn; lz = d[:, 0] * sn + d[:, 1] * cs   # into the rect frame (yaw about y)
        ox = h[0] + R_BOT - np.abs(lx); oz = h[1] + R_BOT - np.abs(lz)
        hit = (ox > 0) & (oz > 0)
        if not hit.any(): continue
        mx = hit & (ox < oz); mz = hit & ~(ox < oz)
        lx = np.where(mx, np.sign(lx) * (h[0] + R_BOT), lx); lz = np.where(mz, np.sign(lz) * (h[1] + R_BOT), lz)
        P[hit, 0] = c[0] + (lx * cs + lz * sn)[hit]; P[hit, 1] = c[1] + (-lx * sn + lz * cs)[hit]
    return P

seg = np.diff(PATH, axis=0); seglen = np.linalg.norm(seg, axis=1); CUM = np.concatenate([[0], np.cumsum(seglen)]); L_PATH = CUM[-1]
def at(s):
    s = np.clip(s, 0, L_PATH); i = np.clip(np.searchsorted(CUM, s, side="right") - 1, 0, len(seg) - 1)
    f = ((s - CUM[i]) / seglen[i])[..., None]
    return PATH[i] + seg[i] * f, seg[i] / seglen[i][..., None]

_tans = seg / seglen[:, None]
_turn = np.degrees(np.arccos(np.clip((_tans[:-1] * _tans[1:]).sum(1), -1, 1)))
SHARP = CUM[1:-1][_turn > 40]          # arc positions of corners sharper than 40 degrees

def half_width(s):
    """corridor half-width the formation may use at arc length s (tighter in the plane zone, shore strip and tunnels)"""
    hw = np.full_like(s, HW["default"])
    hw = np.where((s >= CUM[4]) & (s < CUM[6]), HW["plane_zone"], hw)
    hw = np.where((s >= CUM[12] - 4) & (s < CUM[14]), HW["gust_shore"], hw)
    hw = np.where(s >= CUM[15], HW["hill"], hw)
    if len(SHARP):    # formation narrows into a column round sharp corners, so offset lanes do not fold over
        dmin = np.abs(np.asarray(s)[..., None] - SHARP).min(-1); hw = np.minimum(hw, 0.6 + 0.35 * dmin)
    return hw

def run(seed, cfg, boundary=True):
    rng = np.random.default_rng(seed)
    obs = obstacles()
    vb, R0, Rmin, g_mu, g_sig = cfg["v_b"], cfg["R0"], cfg["R_min"], cfg["gust_mu"], cfg["gust_sigma"]
    out_drain, base_drain, eff = cfg["out_drain"], cfg["base_drain"], cfg["effort"]
    # 15 bots in the start pen; formation slots: 5 rows x 3 columns (lateral, longitudinal), jittered per seed
    lat = np.tile([-1.0, 0.0, 1.0], 5) + rng.normal(0, 0.15, N_BOTS)
    lon = np.repeat([2.0, 1.0, 0.0, -1.0, -2.0], 3) * 1.8 + rng.normal(0, 0.3, N_BOTS)
    P = np.array([-34.0, -44.0]) + rng.normal(0, 1.5, (N_BOTS, 2))
    gain = rng.uniform(0.9, 1.1, N_BOTS)          # per-bot controller gain jitter
    E = np.full(N_BOTS, E0); alive = np.ones(N_BOTS, bool); fin = np.full(N_BOTS, np.nan)
    lost = np.zeros(N_BOTS, bool); downed = np.zeros(N_BOTS, bool); stop_t = np.full(N_BOTS, np.nan)
    s_bot = np.zeros(N_BOTS); out_s = np.zeros(N_BOTS); exits = np.zeros(N_BOTS, int); was_out = np.zeros(N_BOTS, bool)
    node_t = {k: np.full(N_BOTS, np.nan) for k in NODE_AT}
    gust = 0.0; breaks = 0; comp_prev = 1; gust_peak = 0.0
    T_CAP = L_PATH / vb + 60.0 if boundary else L_PATH / V_FREE + 120.0
    t = 0.0; frames = []; sc_free = 0.0
    last_s = np.zeros(N_BOTS); stall_t = np.zeros(N_BOTS); esc_left = np.zeros(N_BOTS); esc_pref = np.zeros(N_BOTS)
    while t < T_CAP and alive.any():
        # the formation anchor moves along the centreline: the squall centre (v_b), or with the boundary off a
        # virtual leader at V_FREE that waits if the swarm's median progress falls more than 8 studs behind
        if boundary:
            sc = min(vb * t, L_PATH)
        else:
            sc = min(sc_free + V_FREE * DT, np.median(s_bot[alive]) + 8.0 if alive.any() else L_PATH, L_PATH); sc_free = sc
        R = R0 + (Rmin - R0) * (sc / L_PATH)
        C, _ = at(np.array(sc))
        # each bot follows its own lane (formation slot offset, clipped to the local corridor) with a carrot 3 studs
        # ahead of its own progress; its speed along the lane holds its slot relative to the anchor
        s_tgt = np.clip(s_bot + 3.0, 0, L_PATH)
        p_t, tan = at(s_tgt); nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
        hw = half_width(s_tgt)
        # stall escape (same idea as the live driver's sidestep): no progress for 2 s -> try a random lane for 2 s
        stall_t = np.where(s_bot > last_s + 0.3, 0.0, stall_t + DT); last_s = np.where(stall_t == 0, s_bot, last_s)
        esc = stall_t > 2.0
        if esc.any():
            new = esc & (esc_left <= 0); esc_pref[new] = rng.uniform(-1, 1, new.sum()); esc_left[new] = 2.0
        esc_left -= DT; use = esc_left > 0
        pref = np.where(use, esc_pref, np.clip(lat, -1, 1))
        tgt = pick_carrot(P, p_t, nrm, hw, pref * hw, obs)
        dirn = tgt - P; dn_ = np.linalg.norm(dirn, axis=1, keepdims=True); dirn = dirn / np.maximum(dn_, 1e-6)
        v_des = np.clip(1.5 * gain * (sc + lon - s_bot) + (vb if boundary else V_FREE), 0, V_MAX)
        v = dirn * v_des[:, None]
        # lane keeping: proportional pull back onto the bot's lane at its own progress (counters drift and gusts)
        p0, tan0 = at(s_bot); n0 = np.stack([-tan0[:, 1], tan0[:, 0]], 1)
        lane_err = ((pref * half_width(s_bot))[:, None] - ((P - p0) * n0).sum(1, keepdims=True)) * n0
        v += 1.5 * lane_err
        # separation (only from bots still racing)
        D = P[:, None, :] - P[None, :, :]; dist = np.linalg.norm(D, axis=2) + np.eye(N_BOTS) * 99
        close = (dist < 2.0) & (alive & np.isnan(fin))[None, :]
        v += (D / dist[..., None] ** 2 * close[..., None]).sum(1) * 1.5
        v += avoid(P, v, obs)
        sp = np.linalg.norm(v, axis=1); v *= np.minimum(1, V_MAX / np.maximum(sp, 1e-9))[:, None]
        # gust band: crosswind toward the water (south, -z); OU process, seeded
        gust += BND['gust_shore']['ou_reversion_per_s'] * (g_mu - gust) * DT + g_sig * math.sqrt(DT) * rng.normal()
        gust = max(0.0, gust)
        in_g = (P[:, 0] > GUST_BOX[0]) & (P[:, 0] < GUST_BOX[1]) & (P[:, 1] > GUST_BOX[2]) & (P[:, 1] < GUST_BOX[3])
        ext = np.zeros_like(P)
        if boundary:
            ext[in_g, 1] = -gust; gust_peak = max(gust_peak, gust if in_g.any() else 0)
        mv = alive & np.isnan(fin)
        P[mv] = P[mv] + (v[mv] + ext[mv]) * DT
        P = push_out(P, obs)
        # progress along the centreline (nearest point within a window ahead of the last value)
        cand = s_bot[:, None] + np.linspace(-1, 5, 25)[None, :]
        q, _ = at(cand); dd = np.linalg.norm(q - P[:, None, :], axis=2)
        s_bot = np.where(mv, np.maximum(s_bot, cand[np.arange(N_BOTS), dd.argmin(1)]), s_bot)
        for k, i in NODE_AT.items():
            hitn = mv & np.isnan(node_t[k]) & (s_bot >= CUM[i] - 0.5); node_t[k][hitn] = t
        # energy and boundary
        spd = np.linalg.norm(v, axis=1)
        E[mv] -= (base_drain + eff * spd[mv] ** 2) * DT
        if boundary:
            outside = np.linalg.norm(P - C, axis=1) > R
            E[mv & outside] -= out_drain * DT; out_s[mv & outside] += DT
            exits += (mv & outside & ~was_out); was_out = outside & mv
            wet = mv & (P[:, 0] > WATER[0]) & (P[:, 0] < WATER[1]) & (P[:, 1] > WATER[2]) & (P[:, 1] < WATER[3])
            lost |= wet; alive &= ~wet; stop_t[wet] = t
        dn = mv & (E <= 0) & alive; downed |= dn; alive &= ~dn; stop_t[dn] = t
        done = mv & alive & ((np.linalg.norm(P - SUMMIT, axis=1) < SUMMIT_R) | (s_bot >= L_PATH - 1.0)); fin[done] = t
        # formation breaks: active bots' proximity graph (link <= 5 studs) splits
        act = np.where(alive & np.isnan(fin))[0]
        if len(act) > 1:
            A = (np.linalg.norm(P[act, None] - P[None, act], axis=2) <= 5.0); comp = n_components(A)
            if comp > 1 and comp_prev == 1: breaks += 1
            comp_prev = comp
        if run.record is not None and int(round(t / DT)) % 5 == 0:
            frames.append({"t": round(t, 1), "P": P.round(2).tolist(), "C": C.round(2).tolist(), "R": R,
                           "alive": alive.tolist(), "s": s_bot.round(2).tolist(), "tgt": tgt.round(2).tolist(), "E": E.round(1).tolist(), "fin": (~np.isnan(fin)).tolist(), "gust": round(gust, 2)})
        t += DT
    res = {"seed": seed, "boundary": boundary, "cfg": cfg, "t_cap": round(T_CAP, 1), "path_len": round(L_PATH, 1),
           "finished": (~np.isnan(fin)).tolist(), "finish_s": [None if np.isnan(x) else round(float(x), 2) for x in fin],
           "lost_in_water": lost.tolist(), "downed": downed.tolist(), "energy_end": E.round(2).tolist(),
           "outside_s": out_s.round(2).tolist(), "exits": exits.tolist(), "formation_breaks": breaks,
           "gust_peak": round(gust_peak, 2), "stop_s": [None if np.isnan(x) else round(float(x), 2) for x in stop_t], "node_t": {k: [None if np.isnan(x) else round(float(x), 2) for x in v_] for k, v_ in node_t.items()}}
    if run.record is not None: run.record.extend(frames)
    return res
run.record = None

def n_components(A):
    n = len(A); seen = np.zeros(n, bool); c = 0
    for i in range(n):
        if seen[i]: continue
        c += 1; st = [i]; seen[i] = True
        while st:
            j = st.pop(); nb = np.where(A[j] & ~seen)[0]; seen[nb] = True; st.extend(nb.tolist())
    return c

if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 0, CFG)
    print("finished", sum(r["finished"]), "lost", sum(r["lost_in_water"]), "downed", sum(r["downed"]), "breaks", r["formation_breaks"])
