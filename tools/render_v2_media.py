#!/usr/bin/env python3
"""Render media/keyframe_v2.png (and media/v2_heat_s1000.mp4 with --video) from a recorded sim heat.
Dark-neon palette: background rgb(12,14,20), magenta rgb(255,110,200) for the squall, cyan rgb(80,220,255) for bots and gust.
The heat is re-simulated from runner/squall_sim.py (held-out seed 1000, the chosen boundary), so frames match the scoreboard row data."""
import json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runner")); import squall_sim as S
BG, MAG, CYAN, WHITE, DIM = (12, 14, 20), (255, 110, 200), (80, 220, 255), (230, 235, 245), (70, 78, 96)
SEED = 1000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def frames():
    S.run.record = []; res = S.run(SEED, S.CFG); fr = S.run.record; S.run.record = None
    return res, fr

def draw(fr, res, W=1600, H=900, title=True):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img, "RGBA")
    x0, x1, z0, z1 = -40, 42, -60, 60          # world window (x east, z north)
    sc = min((W * 0.62) / (x1 - x0), (H - 60) / (z1 - z0)); ox, oy = 40, 30
    P = lambda x, z: (ox + (x - x0) * sc, oy + (z1 - z) * sc)
    f = lambda v: max(10, int(v * W / 1600))
    C = S.COURSE["world"]
    bay = C["bay"]; a, b = P(bay["min"][0], bay["max"][1]), P(bay["max"][0], bay["min"][1])
    d.rectangle([a, b], fill=(20, 40, 70, 255), outline=CYAN + (120,), width=2)
    gb = S.BND["gust_shore"]["box"]; a, b = P(gb["min"][0], gb["max"][1]), P(gb["max"][0], gb["min"][1])
    d.rectangle([a, b], fill=CYAN + (28,))
    for c, h, yaw in S.obstacles():
        cs, sn = math.cos(yaw), math.sin(yaw)
        pts = [P(c[0] + lx * cs + lz * sn, c[1] - lx * sn + lz * cs) for lx, lz in ((-h[0], -h[1]), (h[0], -h[1]), (h[0], h[1]), (-h[0], h[1]))]
        d.polygon(pts, fill=DIM + (255,))
    path = [P(x, z) for x, z in S.PATH]; d.line(path, fill=WHITE + (60,), width=2)
    sx, sz = C["summit"]; r = 2.5 * sc; q = P(sx, sz); d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=WHITE + (200,), width=2)
    # squall disc
    cx, cz = fr["C"]; R = fr["R"] * sc; q = P(cx, cz)
    for k, al in ((1.0, 40), (0.97, 90)):
        d.ellipse([q[0] - R * k, q[1] - R * k, q[0] + R * k, q[1] + R * k], fill=MAG + (14,), outline=MAG + (al + 120,), width=3)
    # gust arrows
    if fr["gust"] > 0:
        for gx in range(9, 34, 5):
            p0 = P(gx, -32.0); p1 = P(gx, -32.0 - min(4.5, fr["gust"]))
            d.line([p0, p1], fill=CYAN + (170,), width=2); d.polygon([(p1[0] - 5, p1[1] - 6), (p1[0] + 5, p1[1] - 6), (p1[0], p1[1] + 2)], fill=CYAN + (170,))
    # bots
    for i, (x, z) in enumerate(fr["P"]):
        q = P(x, z); rr = max(4, 0.9 * sc)
        if fr["fin"][i]: d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], outline=WHITE, width=2)
        elif fr["alive"][i]:
            d.ellipse([q[0] - rr * 2, q[1] - rr * 2, q[0] + rr * 2, q[1] + rr * 2], fill=CYAN + (40,))
            d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=CYAN)
        else:
            d.line([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=MAG + (200,), width=2); d.line([q[0] - rr, q[1] + rr, q[0] + rr, q[1] - rr], fill=MAG + (200,), width=2)
    # side panel
    px = ox + (x1 - x0) * sc + 40; F = ImageFont.truetype(FONTB, f(30)); f2 = ImageFont.truetype(FONT, f(19)); f3 = ImageFont.truetype(FONT, f(16))
    y = 40
    if title:
        d.text((px, y), "MESA ISLAND v2", font=F, fill=MAG); y += f(42)
        d.text((px, y), "wing swarm only / no reef", font=f2, fill=WHITE); y += f(30)
        d.text((px, y), "boundary: squall line", font=f2, fill=CYAN); y += f(46)
    alive = sum(a and not fi for a, fi in zip(fr["alive"], fr["fin"])); fin = sum(fr["fin"]); down = len(fr["alive"]) - alive - fin
    E = [e for e, a, fi in zip(fr["E"], fr["alive"], fr["fin"]) if a and not fi]
    for k, v, col in (("t", f"{fr['t']:.1f} s", WHITE), ("squall radius", f"{fr['R']:.1f} studs", MAG), ("gust", f"{fr['gust']:.1f} studs/s", CYAN),
                      ("racing", str(alive), CYAN), ("finished", str(fin), WHITE), ("lost / downed", str(down), MAG),
                      ("mean energy", f"{np.mean(E):.0f} / 100" if E else "-", WHITE)):
        d.text((px, y), f"{k:<14}", font=f2, fill=DIM); d.text((px + f(190), y), v, font=f2, fill=col); y += f(30)
    y += f(20)
    if title:
        for line in ["held-out eval, 40 heats x 15 bots:", "completion 0.48 [0.44, 0.52]", "boundary off: 1.00",
                     "lost in water 5.8 / heat", "formation breaks 7.4 / heat", "", f"sim seed {SEED} (squall_sim.py)"]:
            d.text((px, y), line, font=f3, fill=WHITE if line and line[0] != "s" else DIM); y += f(24)
    return img

if __name__ == "__main__":
    res, fr = frames()
    # keyframe: the swarm at the gust shore (squall centre inside the gust box)
    k = max(range(len(fr)), key=lambda i: (6 < fr[i]["C"][0] < 30 and -37 < fr[i]["C"][1] < -31) * 1000 + sum(fr[i]["alive"]) * 0 - abs(fr[i]["C"][0] - 18))
    out = os.path.join(ROOT, "media", "keyframe_v2.png"); draw(fr[k], res).save(out); print("wrote", out, "t =", fr[k]["t"])
    if "--video" in sys.argv:
        tmp = tempfile.mkdtemp()
        for i, f_ in enumerate(fr): draw(f_, res, 1280, 720).save(os.path.join(tmp, f"f{i:04d}.png"))
        mp4 = os.path.join(ROOT, "media", f"v2_heat_s{SEED}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "16", "-i", os.path.join(tmp, "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", mp4], check=True)
        print("wrote", mp4, len(fr), "frames")
