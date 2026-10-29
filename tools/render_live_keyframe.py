#!/usr/bin/env python3
"""Keyframe for the first in-world heats: course map (left) and each bot's node splits from the Lua node log (right).
Dark-neon palette. Usage: python3 tools/render_live_keyframe.py  ->  media/keyframe.png"""
import json, glob, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG, MAG, CYAN, DIM, TXT = (12, 14, 20), (255, 110, 200), (80, 220, 255), (40, 46, 60), (210, 220, 235)
NODE_COL = {"N1": (80, 220, 255), "N1b": (120, 255, 170), "N2": (255, 110, 200), "N3": (190, 140, 255), "N4": (255, 200, 90),
            "N5": (90, 160, 255), "N6": (255, 140, 110)}
def font(sz):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

def draw_map(d, course, box, reef=True, extra=None):
    x0, y0, x1, y1 = box; W = course["world"]
    sx = (x1 - x0) / 100.0; sz = (y1 - y0) / 130.0
    P = lambda x, z: (x0 + (x + 50) * sx, y1 - (z + 65) * sz)
    d.rectangle([P(-50, 63), P(46, -61)], outline=DIM, width=2)
    b = W["bay"]; d.rectangle([P(b["min"][0], b["max"][1]), P(b["max"][0], b["min"][1])], fill=(14, 40, 70), outline=CYAN)
    if reef:
        r = W["reef"]; d.rectangle([P(r["min"][0], r["max"][1]), P(r["max"][0], r["min"][1])], fill=(60, 90, 70))
    rw = W["runway"]; d.rectangle([P(rw["x"] - rw["width"] / 2, 61), P(rw["x"] + rw["width"] / 2, -61)], outline=(70, 76, 95), width=2)
    for o in W["runway_obstacles"]:
        c = o["c"]; d.ellipse([P(c[0] - 1.2, c[1] + 1.2), P(c[0] + 1.2, c[1] - 1.2)], fill=MAG if o["kind"] != "pallet" else (150, 80, 130))
    pts = [P(*p) for p in W["cota_loop_centreline"]]; d.line(pts + [pts[0]], fill=(60, 110, 160), width=2)
    for z, tx in ((-25, 16), (-19, 24)):
        d.line([P(10, z), P(tx - 1.5, z)], fill=TXT, width=4); d.line([P(tx + 1.5, z), P(30, z)], fill=TXT, width=4)
    s = W["summit"]; d.ellipse([P(s[0] - 2.5, s[1] + 2.5), P(s[0] + 2.5, s[1] - 2.5)], outline=(255, 215, 0), width=3)
    if extra: extra(d, P)
    return P

def main():
    course = json.load(open(os.path.join(ROOT, "course.json")))
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "scoreboard", "results.jsonl")) if '"clawblox-live"' in l]
    img = Image.new("RGB", (1600, 900), BG); d = ImageDraw.Draw(img)
    d.text((40, 24), "Mesa Island Race Course v1: first in-world Clawblox heats", font=font(34), fill=TXT)
    d.text((40, 68), "3 heats x 5 bots, splits from the world's Lua node log (no LLM driver)", font=font(20), fill=CYAN)
    P = draw_map(d, course, (40, 110, 560, 870))
    for n in course["nodes"]:
        z = n.get("zone", {})
        if z.get("kind") == "circle":
            c = z["c"]; d.text(P(c[0] + 2, c[1] + 2), n["id"], font=font(16), fill=NODE_COL.get(n["id"], TXT))
    heats = sorted({r["heat_id"] for r in rows}); y = 120; tmax = 800.0; X0, X1 = 820, 1560
    for h in heats:
        hr = sorted((r for r in rows if r["heat_id"] == h), key=lambda r: (r["status"] != "finished", r["total_time_s"]))
        d.text((600, y), f"seed {hr[0]['seed']}", font=font(20), fill=MAG); y += 30
        for r in hr:
            d.text((600, y + 2), r["bot_name"].split("-s")[0], font=font(16), fill=TXT)
            x = X0
            for n, sp in r["node_splits"].items():
                if not sp: continue
                w = sp / tmax * (X1 - X0); d.rectangle([x, y, x + w, y + 18], fill=NODE_COL.get(n, DIM)); x += w
            pen = sum(p["s"] for p in r["penalties"]) - sum(b["s"] for b in r["bonuses"])
            lab = f"{r['total_time_s']:.0f} s" if r["status"] == "finished" else f"DNF at {r['dnf_at']}"
            d.text((x + 8, y), lab + (f"  ({pen:+.0f} s pen/bonus)" if r["status"] == "finished" else ""), font=font(15), fill=CYAN if r["status"] == "finished" else MAG)
            y += 24
        y += 14
    lx = 820
    for n, c in NODE_COL.items():
        d.rectangle([lx, 860, lx + 16, 876], fill=c); d.text((lx + 22, 858), n, font=font(15), fill=TXT); lx += 90
    d.text((600, 858), "bars = node splits", font=font(15), fill=DIM)
    out = os.path.join(ROOT, "media", "keyframe.png"); img.save(out); print(out)
if __name__ == "__main__":
    main()
