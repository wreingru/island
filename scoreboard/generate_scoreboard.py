#!/usr/bin/env python3
"""Regenerate scoreboard/SCOREBOARD.md and scoreboard/leaderboard.json from scoreboard/results.jsonl."""
import json, os, statistics as st, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
course = json.load(open(os.path.join(ROOT, "course.json")))
names = {m["id"]: m["name"] for m in course["bot_models"]}
rows = [json.loads(l) for l in open(os.path.join(ROOT, "scoreboard", "results.jsonl")) if l.strip()]
rows.sort(key=lambda r: (r["total_time_s"], r["run_id"]))
fmt = lambda s: f"{int(s // 60)}:{s % 60:05.2f}"
nodes = ["N1", "N1b", "N2", "N3", "N4", "N5", "N6"]
models = [m["id"] for m in course["bot_models"]]

L = [f"# Scoreboard: {course['title']} (course v{course['version']})", "",
     f"Generated from `scoreboard/results.jsonl`: {len(rows)} result rows, {len({r['heat_id'] for r in rows})} heats, "
     f"commits {', '.join(sorted({r['commit_sha'][:10] for r in rows}))}.", "",
     "Total = node splits + penalties - bonuses. Times are on each bot's own clock (released 15 s apart; transit legs between nodes are neutral).",
     "Rows come from `runner/run_race.py`, which resamples measured per-bot records from the earlier sims; see each row's `provenance`.", "",
     "## Overall top 15", "", "| # | Bot | Model | Seed | Total | Raw | Penalties | Bonus | Status | Run |", "|---|---|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows[:15], 1):
    L.append(f"| {i} | {r['bot_name']} | {names[r['bot_model']]} | {r['seed']} | {fmt(r['total_time_s'])} | {fmt(r['raw_time_s'])} | "
             f"{sum(p['s'] for p in r['penalties']):.0f} s | {sum(b['s'] for b in r['bonuses']):.0f} s | {r['status']} | `{r['run_id']}` |")
L += ["", "## By model", "", "| Model | Rows | Best | Median | Worst | Reef holds | Rescued | Pi sessions |", "|---|---|---|---|---|---|---|---|"]
board = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "rows": len(rows), "top": [], "models": []}
for m in models:
    mr = [r for r in rows if r["bot_model"] == m]
    if not mr:
        L.append(f"| {names[m]} | 0 | no data yet | | | | | |"); board["models"].append({"model": m, "rows": 0}); continue
    t = [r["total_time_s"] for r in mr]
    holds = sum(1 for r in mr if any(b["reason"] == "reef_held" for b in r["bonuses"]))
    resc = sum(r["status"] == "rescued" for r in mr)
    pis = sum(r["pi"]["real"] for r in mr)
    L.append(f"| {names[m]} | {len(mr)} | {fmt(min(t))} | {fmt(st.median(t))} | {fmt(max(t))} | {holds} | {resc} | {pis} real / {len(mr)} |")
    med = {n: round(st.median([r["node_splits"][n] for r in mr if n in r["node_splits"]]), 2) for n in nodes if any(n in r["node_splits"] for r in mr)}
    board["models"].append({"model": m, "rows": len(mr), "best_s": min(t), "median_s": round(st.median(t), 2), "worst_s": max(t),
                            "reef_holds": holds, "rescued": resc, "median_splits": med})
L += ["", "## Median node splits by model (seconds, before penalties)", "", "| Model | " + " | ".join(nodes) + " |", "|---|" + "---|" * len(nodes)]
for b in board["models"]:
    if b["rows"]:
        L.append(f"| {names[b['model']]} | " + " | ".join(str(b["median_splits"].get(n, "-")) for n in nodes) + " |")
L += ["", "## Heat winners", "", "| Heat | Winner | Total |", "|---|---|---|"]
for h in sorted({r["heat_id"] for r in rows}):
    w = min((r for r in rows if r["heat_id"] == h), key=lambda r: r["total_time_s"])
    L.append(f"| `{h}` | {w['bot_name']} | {fmt(w['total_time_s'])} |")
L += ["", "## Read before comparing models", "",
      "- Wing-swarm times are BeetleBot walking records scaled by 1.5/5.5 (an assumption: the Clawblox humanoid's MoveTo speed). It wins on that speed alone.",
      "- Hill times are BeetleBot crawl times divided by 72.5 (an assumption to match the 1.5 studs/s island speed).",
      "- Swim bypass, gate bypass and one walked COTA lap are derived from distance and speed, not measured. Penalty and bonus sizes are design choices.",
      "- Seed bot has no data and is not raced."]
board["top"] = [{k: r[k] for k in ("run_id", "bot_name", "bot_model", "seed", "total_time_s", "raw_time_s", "status")} for r in rows[:15]]
open(os.path.join(ROOT, "scoreboard", "SCOREBOARD.md"), "w").write("\n".join(L) + "\n")
json.dump(board, open(os.path.join(ROOT, "scoreboard", "leaderboard.json"), "w"), indent=1)
print("SCOREBOARD.md:", len(rows), "rows")
