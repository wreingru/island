# Mesa Island Race Course

A race course on the Mesa World island that pulls together the last week's island and BeetleBot sims:
reef swim, reef-hold side objective, runway with curvity and a crashed plane, plane hop, drone gates (one on the reef),
COTA loop with an NPC car pair, and a hill with tunnels. Bot models are picked like the dashboard slider.
Each race is recorded as a Pi parent/child session tree, and results go to a scoreboard that GitHub Actions rebuilds.

## Layout
| Path | What it is |
|---|---|
| `course.json` | Single source: node graph (ids, types, entry/exit, scoring, allowed modes, parent/child links), bot models, island geometry. Built by `tools/build_course.py`. |
| `schema/result.schema.json` | JSON Schema for one result row. |
| `runner/bank.json` | Measured per-bot records copied from the earlier sims (`tools/build_bank.py`). |
| `runner/run_race.py` | Runs heats (5 bots of one model per seed) and appends rows to `scoreboard/results.jsonl`. |
| `runner/pi_record.mjs` | Writes each heat as Pi sessions: parent "race director" + one child per bot, node entries as a tree. |
| `runner/pi_sessions/` | The Pi session files (JSONL, Pi session format v3). |
| `clawblox/` | Clawblox world (`world.toml`, `main.lua`, `API.md`, renderer) with the course built in; `test_drive.py` drives bots through it; `test_run.json` is the last test run. |
| `mesaworld/` | Engine-neutral `course_spec.json` and notes on Mesa World hosting. |
| `clawblox/race_live.py` | Live heat driver: 5 bots (one per model) join a running Clawblox server and follow fixed waypoint routes over HTTP. Writes `clawblox/live/heat_s<seed>.json` with the world's own node log. |
| `tools/build_live_rows.py` | Turns `clawblox/live/heat_s*.json` into `clawblox-live` scoreboard rows (+ Pi parent/child sessions). |
| `tools/render_live_keyframe.py` | `media/keyframe.png`: course map + live node splits. |
| `scoreboard/` | `results.jsonl`, `SCOREBOARD.md`, `leaderboard.json`, `validate_results.py`, `generate_scoreboard.py`. |
| `.github/workflows/scoreboard.yml` | On push: validate results against the schema, regenerate the scoreboard, commit it back. |

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install jsonschema
python3 runner/run_race.py --models all --seeds 0-5        # appends rows; needs Node 22 + @earendil-works/pi-coding-agent for real Pi ids
.venv/bin/python scoreboard/validate_results.py
python3 scoreboard/generate_scoreboard.py
# Clawblox world (from a clawblox checkout with a release build):
./target/release/clawblox run /path/to/island_race_course/clawblox --port 8295 --datastore none
python3 clawblox/test_drive.py --port 8295
# live heat (one fresh server per heat: players cannot leave a running world)
python3 clawblox/race_live.py --port 8295 --seed 101 --out clawblox/live/heat_s101.json
python3 tools/build_live_rows.py   # appends source=clawblox-live rows, records Pi sessions
```
After editing `course.json` (or `tools/build_course.py`), run `python3 tools/export_clawblox.py` and `python3 tools/export_mesaworld.py`.

## In-world races (source `clawblox-live`)
The first live heats (seeds 101 to 103, 2026-10-29) ran on three local Clawblox servers. Times are the world's own Lua node
log at speed_scale 1, not the sim bank, so they are listed separately in `SCOREBOARD.md` and never ranked with sim rows.
A bot that does not reach the summit within the driver's 1500 s cap is a DNF at the node it was in (`dnf_at`).
The driver is a fixed waypoint script (no LLM); seed sets the release order, the flyer's energy reserve (U(10, 16) J) and
which reef-capable bot takes the reef.

## What is measured and what is assumed
- Node times for a model come from that body's measured per-bot records where they exist (see each row's `provenance`).
- Assumptions: the 1.5 studs/s island walking speed; hill times = BeetleBot crawl time / 72.5; wing-swarm = walker records x 1.5/5.5;
  scout = 1.25x walker speed; triathlete walking nodes = walker records x 1.5/(1.55 x run factor).
- Derived, not measured: shore-path swim bypass, on-foot gate bypass, one walked COTA lap, reef-hold time.
- Design choices: all penalty and bonus sizes, the node order, transit legs being untimed.
- Pi: the session files are real Pi `SessionManager` files, but no LLM drives the bots; `pi.llm` is false in every row.
- Seed bot has no data yet and is not raced.
