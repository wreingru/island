# Mesa Island Race Course: version 2 (branch `v2-wing-swarm`)

Version 2 of the Mesa island race: **wing-swarm bots only, the reef removed, and a new boundary built to challenge the swarm**.
Version 1 (five bot models, reef swim and reef hold, drone gates, COTA loop, and its in-world heats) is on `main` and is unchanged.

What changed from v1:
- Bot models: only `wing_swarm` remains (course.json, the Clawblox world, the exports, the schema and the scoreboard). The bank, the v1 runner and the v1 live driver and rows were removed from this branch.
- Reef: removed everywhere: the reef strip, the N1b reef hold, the swim buoy, and the reef part in `clawblox/main.lua`, `mesaworld/course_spec.json` and the renderer scene. The bay is now open, lethal water. The drone gates (gate C sat on the reef; the swarm does not fly) and the COTA loop / NPC cars are gone too.
- Nodes: N0 start and approach, N1 runway lot, N2 plane crossing, N3 west return leg, N4 gust shore (former reef bay), N5 hill tunnels, N6 summit.

## The boundary: squall line

- **Squall disc.** A circle moves along the course centreline at 3.0 studs/s and shrinks from radius 14 to 3 studs. Outside it a bot loses 6 energy per second (start 100; base drain 0.1 + 0.004 v^2 per second). Energy 0 means downed.
- **Gust shore.** The route runs a 6-stud strip between the open bay and a new cliff wall. A crosswind (Ornstein-Uhlenbeck, mean 3.0 studs/s, sigma 1.5) pushes bots toward the water. A bot whose centre enters the bay is lost.

Why it challenges the wing swarm: in v1 the swarm won on speed alone (5.5 studs/s against 1.5 to 1.9 for the beetles). The squall caps progress at its own pace, and running ahead is outside the disc too. So the swarm has to hold a formation inside a shrinking circle through the plane zone, the shore strip and the 3-stud tunnels, and keep its water-side lane out of the bay with no reef to stand on. Each part has one knob (pace, final radius, gust mean), so completion can be tuned.

Tuning: `runner/tune_v2.py`, seeds 0-11 only (`runner/v2_tuning.txt`). The target was 40-70% completion, and the chosen config gave 50% on the tuning seeds. Evaluation: `runner/eval_v2.py`, held-out seeds 1000-1039, three arms on paired seeds (full boundary, squall only, boundary off), with 95% bootstrap CIs (10,000 resamples over heats). The result is in `runner/v2_eval.json` and the table in `scoreboard/SCOREBOARD.md`.

| Held-out (40 heats x 15 bots) | Squall line | Squall only | Off |
|---|---|---|---|
| Completion | 0.483 [0.442, 0.523] | 0.707 [0.658, 0.753] | 1.000 |
| Finish time of finishers (s) | 116.2 [116.2, 116.3] | 116.2 | 78.5 [78.3, 78.8] |
| Disc exits per heat | 23.4 [22.2, 24.7] | 30.3 | 0 |
| Energy left per bot | 56.8 [54.9, 58.7] | 50.2 | 84.9 |
| Formation breaks per heat | 7.38 [6.28, 8.57] | 7.28 | 4.65 [4.08, 5.25] |
| Lost in water per heat | 5.75 [5.17, 6.35] | 1.60 | 0 |

## Layout
| Path | What it is |
|---|---|
| `course.json` | v2 course: nodes N0-N6, centreline, boundary numbers, wing_swarm model, world without the reef. Built by `tools/build_course_v2.py`. |
| `runner/squall_sim.py` | 15-bot swarm sim with the squall line (lane controller, obstacle-aware carrot, separation, stall escape). |
| `runner/tune_v2.py`, `runner/eval_v2.py` | Tuning grid (seeds 0-11) and held-out evaluation (seeds 1000-1039) with bootstrap CIs. |
| `runner/v2_heats.json` | Per-bot results of the 40 held-out full-boundary heats (source of the `sim-v2` rows). |
| `runner/pi_record.mjs`, `runner/pi_util.py` | Pi session recorder: one parent session per heat plus one child per bot, node entries as a tree (`llm: false`). |
| `runner/pi_sessions/` | The v2 Pi session files (41 parents, 605 children). |
| `clawblox/` | v2 Clawblox world: `main.lua` moves the squall, blows the gust, drains energy and logs nodes; `API.md`; renderer. |
| `clawblox/race_live_v2.py` | Live heat driver: 5 wing-swarm bots over HTTP with the same lane controller. Writes `clawblox/live_v2/heat_s<seed>.json`; the world's own event log is saved next to it. |
| `clawblox/live_v2/dev/` | Three driver-development heats (s2001 to s2003), not scored. |
| `tools/build_v2_rows.py` | Builds all v2 rows (sim-v2 and clawblox-live) plus Pi sessions into `scoreboard/results.jsonl`. |
| `tools/render_v2_media.py` | `media/keyframe_v2.png` and `media/v2_heat_s1000.mp4` (dark-neon, from sim seed 1000). |
| `scoreboard/` | `results.jsonl` (v2 rows only), `SCOREBOARD.md`, `leaderboard.json`, `validate_results.py`, `generate_scoreboard.py`. |
| `.github/workflows/scoreboard.yml` | On push: validate against the schema, regenerate the scoreboard, commit it back. |

## Run
```
python3 tools/build_course_v2.py && python3 tools/export_clawblox.py && python3 tools/export_mesaworld.py
python3 runner/tune_v2.py > runner/v2_tuning.txt
python3 runner/eval_v2.py runner/v2_eval.json runner/v2_heats.json
# live heat (fresh server per heat; players cannot leave a running world)
clawblox run clawblox --port 8305 --datastore none
python3 clawblox/race_live_v2.py --port 8305 --seed 2005 --out clawblox/live_v2/heat_s2005.json
# then save the server's "RACE " lines as clawblox/live_v2/heat_s2005_world_log.jsonl
python3 tools/build_v2_rows.py && python3 scoreboard/validate_results.py && python3 scoreboard/generate_scoreboard.py
python3 tools/render_v2_media.py --video
```

## In-world (source `clawblox-live`)
One scored live heat, `irc-v2-live-s2005` on port 8305: **0 of 5 finished**. One bot was lost in the bay at N4, and four were downed (energy 0): two in the plane zone (N2) and two at the bay corner just before the shore strip (end of N3). The three earlier development heats also had 0 of 5 finishers. In the world, bots got pinned on the plane-zone car and launched by collisions in a crowd, which the sim does not model. So the live result shows the world and its boundary logic work end to end, but it is not a measurement of the 40-70% target.

## What is measured and what is assumed
- Measured: every sim and live time is a difference of logged node-entry times; live times come from the world's own node log.
- Assumed (design choices): the energy units, drain rates, squall pace and radii, and the gust strength. The sim is 2-D kinematics, not Clawblox physics.
