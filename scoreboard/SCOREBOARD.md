# Scoreboard: Mesa Island Race Course (course v1)

Generated from `scoreboard/results.jsonl`: 150 result rows, 30 heats, commits 423f231061.

Total = node splits + penalties - bonuses. Times are on each bot's own clock (released 15 s apart; transit legs between nodes are neutral).
Rows come from `runner/run_race.py`, which resamples measured per-bot records from the earlier sims; see each row's `provenance`.

## Overall top 15

| # | Bot | Model | Seed | Total | Raw | Penalties | Bonus | Status | Run |
|---|---|---|---|---|---|---|---|---|---|
| 1 | wing_swarm-3 | Wing-swarm bot (Clawblox humanoid) | 0 | 2:45.51 | 1:45.51 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s000-b3` |
| 2 | wing_swarm-0 | Wing-swarm bot (Clawblox humanoid) | 0 | 2:48.17 | 1:48.17 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s000-b0` |
| 3 | wing_swarm-3 | Wing-swarm bot (Clawblox humanoid) | 3 | 2:48.90 | 1:48.90 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s003-b3` |
| 4 | wing_swarm-2 | Wing-swarm bot (Clawblox humanoid) | 1 | 2:48.94 | 1:48.94 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s001-b2` |
| 5 | wing_swarm-0 | Wing-swarm bot (Clawblox humanoid) | 3 | 2:49.08 | 1:49.08 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s003-b0` |
| 6 | wing_swarm-3 | Wing-swarm bot (Clawblox humanoid) | 1 | 2:49.25 | 1:49.25 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s001-b3` |
| 7 | wing_swarm-2 | Wing-swarm bot (Clawblox humanoid) | 3 | 2:49.77 | 1:49.77 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s003-b2` |
| 8 | wing_swarm-1 | Wing-swarm bot (Clawblox humanoid) | 0 | 2:49.95 | 1:49.95 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s000-b1` |
| 9 | wing_swarm-1 | Wing-swarm bot (Clawblox humanoid) | 5 | 2:50.09 | 1:50.09 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s005-b1` |
| 10 | wing_swarm-3 | Wing-swarm bot (Clawblox humanoid) | 2 | 2:51.04 | 1:51.04 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s002-b3` |
| 11 | wing_swarm-3 | Wing-swarm bot (Clawblox humanoid) | 5 | 2:51.07 | 1:51.07 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s005-b3` |
| 12 | wing_swarm-1 | Wing-swarm bot (Clawblox humanoid) | 3 | 2:51.29 | 1:51.29 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s003-b1` |
| 13 | wing_swarm-2 | Wing-swarm bot (Clawblox humanoid) | 2 | 2:51.30 | 1:51.30 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s002-b2` |
| 14 | wing_swarm-2 | Wing-swarm bot (Clawblox humanoid) | 0 | 2:51.52 | 1:51.52 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s000-b2` |
| 15 | wing_swarm-2 | Wing-swarm bot (Clawblox humanoid) | 5 | 2:51.70 | 1:51.70 | 60 s | 0 s | finished | `irc-v1-wing_swarm-s005-b2` |

## By model

| Model | Rows | Best | Median | Worst | Reef holds | Rescued | Pi sessions |
|---|---|---|---|---|---|---|---|
| BeetleBot walker | 30 | 7:26.90 | 7:50.33 | 8:24.81 | 6 | 0 | 30 real / 30 |
| Flying beetle (walk + hop) | 30 | 6:48.57 | 7:07.31 | 7:52.42 | 6 | 0 | 30 real / 30 |
| Triathlete (swim, roll, run) | 30 | 7:03.32 | 7:26.78 | 8:09.47 | 0 | 0 | 30 real / 30 |
| Wing-swarm bot (Clawblox humanoid) | 30 | 2:45.51 | 2:51.90 | 3:01.31 | 0 | 0 | 30 real / 30 |
| Curvity scout (centre lane) | 30 | 6:44.96 | 6:59.08 | 7:23.27 | 6 | 0 | 30 real / 30 |
| Seed bot | 0 | no data yet | | | | | |

## Median node splits by model (seconds, before penalties)

| Model | N1 | N1b | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|---|
| BeetleBot walker | 12.0 | 61.11 | 80.0 | 21.2 | 73.33 | 170.8 | 52.28 |
| Flying beetle (walk + hop) | 12.0 | 61.11 | 77.2 | 18.8 | 75.7 | 170.8 | 52.28 |
| Triathlete (swim, roll, run) | 49.0 | - | 76.66 | 19.98 | 70.97 | 141.57 | 51.05 |
| Wing-swarm bot (Clawblox humanoid) | 3.27 | - | 21.82 | 5.78 | 20.0 | 46.58 | 14.26 |
| Curvity scout (centre lane) | 9.6 | 50.89 | 90.23 | 23.57 | 58.67 | 136.64 | 41.82 |

## Heat winners

| Heat | Winner | Total |
|---|---|---|
| `irc-v1-beetle_walker-s000` | beetle_walker-3 | 7:26.90 |
| `irc-v1-beetle_walker-s001` | beetle_walker-2 | 7:39.47 |
| `irc-v1-beetle_walker-s002` | beetle_walker-3 | 7:47.18 |
| `irc-v1-beetle_walker-s003` | beetle_walker-3 | 7:39.32 |
| `irc-v1-beetle_walker-s004` | beetle_walker-1 | 7:51.08 |
| `irc-v1-beetle_walker-s005` | beetle_walker-1 | 7:44.78 |
| `irc-v1-curvity_scout-s000` | curvity_scout-3 | 6:49.05 |
| `irc-v1-curvity_scout-s001` | curvity_scout-2 | 6:58.22 |
| `irc-v1-curvity_scout-s002` | curvity_scout-0 | 6:56.99 |
| `irc-v1-curvity_scout-s003` | curvity_scout-0 | 6:44.96 |
| `irc-v1-curvity_scout-s004` | curvity_scout-0 | 6:51.15 |
| `irc-v1-curvity_scout-s005` | curvity_scout-1 | 6:50.08 |
| `irc-v1-flying_beetle-s000` | flying_beetle-3 | 6:48.57 |
| `irc-v1-flying_beetle-s001` | flying_beetle-2 | 6:56.04 |
| `irc-v1-flying_beetle-s002` | flying_beetle-0 | 6:54.49 |
| `irc-v1-flying_beetle-s003` | flying_beetle-3 | 6:59.49 |
| `irc-v1-flying_beetle-s004` | flying_beetle-0 | 6:53.80 |
| `irc-v1-flying_beetle-s005` | flying_beetle-3 | 6:49.96 |
| `irc-v1-triathlete-s000` | Wren | 7:03.32 |
| `irc-v1-triathlete-s001` | Pike | 7:09.28 |
| `irc-v1-triathlete-s002` | Pike | 7:20.84 |
| `irc-v1-triathlete-s003` | Wren | 7:11.83 |
| `irc-v1-triathlete-s004` | Kestrel | 7:25.30 |
| `irc-v1-triathlete-s005` | Wren | 7:19.24 |
| `irc-v1-wing_swarm-s000` | wing_swarm-3 | 2:45.51 |
| `irc-v1-wing_swarm-s001` | wing_swarm-2 | 2:48.94 |
| `irc-v1-wing_swarm-s002` | wing_swarm-3 | 2:51.04 |
| `irc-v1-wing_swarm-s003` | wing_swarm-3 | 2:48.90 |
| `irc-v1-wing_swarm-s004` | wing_swarm-1 | 2:52.10 |
| `irc-v1-wing_swarm-s005` | wing_swarm-1 | 2:50.09 |

## Read before comparing models

- Wing-swarm times are BeetleBot walking records scaled by 1.5/5.5 (an assumption: the Clawblox humanoid's MoveTo speed). It wins on that speed alone.
- Hill times are BeetleBot crawl times divided by 72.5 (an assumption to match the 1.5 studs/s island speed).
- Swim bypass, gate bypass and one walked COTA lap are derived from distance and speed, not measured. Penalty and bonus sizes are design choices.
- Seed bot has no data and is not raced.
