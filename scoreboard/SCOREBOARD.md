# Scoreboard: Mesa Island Race Course v2: wing swarm, no reef, squall line (course v2)

Branch `v2-wing-swarm`. Generated from `scoreboard/results.jsonl`: 605 rows (600 sim-v2 rows in 40 heats, 5 live rows in 1 heats). Wing swarm only; v1 (five models, reef) results are on `main`.

Clock: one race clock from the swarm's release. Total = sum of node splits (no penalties or bonuses in v2). A DNF is listed at the node it was in, with the reason: water (lost in the bay), energy (downed), cap, or fell.

## The boundary: squall line

- Squall disc: moves along the centreline at 3.0 studs/s from the start pen, radius shrinking from 14.0 to 3.0 studs; outside it a bot loses 6.0 energy/s (E0 100.0, plus 0.1 + 0.004 v^2 per s).
- Gust shore (former reef bay, now open water): crosswind toward the water, OU mean 3.0 studs/s, sigma 1.5; a bot whose centre enters the bay is lost.
- Tuned on seeds 0-11 (`runner/v2_tuning.txt`), evaluated on held-out seeds 1000-1039; 15 bots per heat; 95% CIs from 10,000 bootstrap resamples over heats.

## Held-out evaluation (sim, 40 heats per arm, paired seeds)

| Metric (per heat unless noted) | Squall line (full) | Squall only (no gust) | Boundary off |
|---|---|---|---|
| Completion (share of 15 bots) | 0.483 [0.442, 0.523] | 0.707 [0.658, 0.753] | 1.000 [1.000, 1.000] |
| Finish time of finishers (s) | 116.2 [116.2, 116.3] | 116.2 [116.2, 116.3] | 78.5 [78.3, 78.8] |
| Squall-disc exits | 23.4 [22.2, 24.7] | 30.3 [28.7, 31.9] | 0.0 [0.0, 0.0] |
| Bot-seconds outside the disc | 70.1 [65.4, 74.9] | 84.7 [81.2, 88.1] | 0.0 [0.0, 0.0] |
| Energy left per bot (of 100) | 56.8 [54.9, 58.7] | 50.2 [48.9, 51.6] | 84.9 [84.8, 84.9] |
| Formation breaks | 7.38 [6.28, 8.57] | 7.28 [6.17, 8.47] | 4.65 [4.08, 5.25] |
| Bots lost in the water | 5.75 [5.17, 6.35] | 1.60 [1.05, 2.20] | 0.00 [0.00, 0.00] |
| Bots downed (energy 0) | 2.00 [1.62, 2.40] | 2.80 [2.38, 3.23] | 0.00 [0.00, 0.00] |

Paired differences (mean [95% CI]):

- full minus off: completion -0.517 [-0.558, -0.477]; time_s 37.7 [37.4, 38.0]; energy_end -28.1 [-29.9, -26.2]; breaks 2.7 [1.4, 4.1]
- full minus squall-only: completion -0.223 [-0.260, -0.187]; lost 4.2 [3.5, 4.8]; downed -0.8 [-1.1, -0.5]; exits -6.9 [-8.4, -5.3]

Finishers arrive with the squall (path / pace = 351.1 / 3.0 s), so finish time is set by the squall, not by top speed.

## In-world Clawblox heats (source: clawblox-live)

Five wing-swarm bots in the v2 Clawblox world (`clawblox/main.lua`), driven by `clawblox/race_live_v2.py`. The world moves the squall, blows the gust and decides lost / downed / finished; times are its own node log. Three earlier driver-development heats (s2001 to s2003, also 0 of 5 finished) are kept in `clawblox/live_v2/dev/` and are not scored.

### `irc-v2-live-s2005` (seed 2005, port 8305): 0 of 5 finished, 2 formation breaks

| Place | Bot | Total | Status | N0 | N1 | N2 | N3 | N4 | N5 | Energy left | Outside (s) | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| - | wing_swarm-0 | DNF | DNF at N4 (water) | 10.19 | 21.7 | 20.93 | 37.02 | - | - | 8.2 | 12.6 | `irc-v2-live-s2005-b0` |
| - | wing_swarm-4 | DNF | DNF at N3 (energy) | 11.74 | 23.78 | 16.39 | - | - | - | -0.1 | 14.0 | `irc-v2-live-s2005-b4` |
| - | wing_swarm-1 | DNF | DNF at N3 (energy) | 10.09 | 23.01 | 16.28 | - | - | - | -0.0 | 13.8 | `irc-v2-live-s2005-b1` |
| - | wing_swarm-3 | DNF | DNF at N2 (energy) | 11.77 | 27.07 | - | - | - | - | -0.0 | 15.1 | `irc-v2-live-s2005-b3` |
| - | wing_swarm-2 | DNF | DNF at N2 (energy) | 11.75 | 21.05 | - | - | - | - | -0.1 | 15.0 | `irc-v2-live-s2005-b2` |

## Sim heats (source: sim-v2, held-out seeds)

| Heat | Finished | Lost (water) | Downed | Cap | Formation breaks | Gust peak | Best | Median finisher |
|---|---|---|---|---|---|---|---|---|
| `irc-v2-sim-s1000` | 7 / 15 | 6 | 2 | 0 | 3 | 7.01 | 1:54.70 | 1:56.10 |
| `irc-v2-sim-s1001` | 4 / 15 | 8 | 3 | 0 | 9 | 7.01 | 1:54.80 | 1:55.70 |
| `irc-v2-sim-s1002` | 9 / 15 | 5 | 1 | 0 | 10 | 5.68 | 1:54.90 | 1:56.30 |
| `irc-v2-sim-s1003` | 9 / 15 | 5 | 1 | 0 | 8 | 5.06 | 1:54.80 | 1:56.20 |
| `irc-v2-sim-s1004` | 5 / 15 | 5 | 5 | 0 | 11 | 6.42 | 1:55.40 | 1:56.00 |
| `irc-v2-sim-s1005` | 5 / 15 | 9 | 1 | 0 | 5 | 7.45 | 1:54.80 | 1:56.00 |
| `irc-v2-sim-s1006` | 10 / 15 | 3 | 2 | 0 | 5 | 4.05 | 1:55.40 | 1:56.35 |
| `irc-v2-sim-s1007` | 7 / 15 | 7 | 1 | 0 | 11 | 6.46 | 1:54.90 | 1:56.70 |
| `irc-v2-sim-s1008` | 4 / 15 | 9 | 2 | 0 | 13 | 6.53 | 1:55.50 | 1:56.40 |
| `irc-v2-sim-s1009` | 7 / 15 | 5 | 3 | 0 | 20 | 5.61 | 1:54.90 | 1:56.10 |
| `irc-v2-sim-s1010` | 5 / 15 | 5 | 5 | 0 | 2 | 5.64 | 1:55.30 | 1:56.70 |
| `irc-v2-sim-s1011` | 8 / 15 | 5 | 2 | 0 | 5 | 5.96 | 1:54.70 | 1:55.80 |
| `irc-v2-sim-s1012` | 9 / 15 | 6 | 0 | 0 | 9 | 6.06 | 1:54.80 | 1:56.20 |
| `irc-v2-sim-s1013` | 6 / 15 | 7 | 2 | 0 | 6 | 6.45 | 1:54.90 | 1:56.20 |
| `irc-v2-sim-s1014` | 10 / 15 | 5 | 0 | 0 | 8 | 4.41 | 1:54.80 | 1:56.10 |
| `irc-v2-sim-s1015` | 7 / 15 | 5 | 3 | 0 | 6 | 5.23 | 1:55.20 | 1:56.10 |
| `irc-v2-sim-s1016` | 9 / 15 | 5 | 1 | 0 | 5 | 5.53 | 1:54.70 | 1:56.20 |
| `irc-v2-sim-s1017` | 5 / 15 | 9 | 1 | 0 | 4 | 7.51 | 1:54.90 | 1:56.00 |
| `irc-v2-sim-s1018` | 8 / 15 | 5 | 2 | 0 | 5 | 6.36 | 1:54.90 | 1:56.10 |
| `irc-v2-sim-s1019` | 7 / 15 | 5 | 3 | 0 | 9 | 6.03 | 1:54.70 | 1:56.10 |
| `irc-v2-sim-s1020` | 7 / 15 | 8 | 0 | 0 | 4 | 6.72 | 1:54.80 | 1:56.30 |
| `irc-v2-sim-s1021` | 8 / 15 | 4 | 3 | 0 | 3 | 4.45 | 1:54.80 | 1:56.05 |
| `irc-v2-sim-s1022` | 8 / 15 | 5 | 2 | 0 | 11 | 5.57 | 1:54.80 | 1:56.40 |
| `irc-v2-sim-s1023` | 5 / 15 | 5 | 5 | 0 | 4 | 5.62 | 1:55.40 | 1:56.10 |
| `irc-v2-sim-s1024` | 4 / 15 | 8 | 3 | 0 | 6 | 6.89 | 1:54.70 | 1:55.80 |
| `irc-v2-sim-s1025` | 8 / 15 | 5 | 2 | 0 | 11 | 6.09 | 1:54.80 | 1:56.35 |
| `irc-v2-sim-s1026` | 5 / 15 | 9 | 1 | 0 | 3 | 7.69 | 1:54.80 | 1:56.00 |
| `irc-v2-sim-s1027` | 8 / 15 | 5 | 2 | 0 | 4 | 5.44 | 1:54.70 | 1:56.05 |
| `irc-v2-sim-s1028` | 8 / 15 | 5 | 2 | 0 | 12 | 5.92 | 1:55.40 | 1:56.30 |
| `irc-v2-sim-s1029` | 8 / 15 | 4 | 3 | 0 | 9 | 5.64 | 1:54.80 | 1:56.35 |
| `irc-v2-sim-s1030` | 6 / 15 | 5 | 4 | 0 | 5 | 6.47 | 1:54.80 | 1:55.75 |
| `irc-v2-sim-s1031` | 8 / 15 | 5 | 2 | 0 | 6 | 6.2 | 1:54.80 | 1:56.05 |
| `irc-v2-sim-s1032` | 9 / 15 | 5 | 1 | 0 | 5 | 5.93 | 1:54.80 | 1:56.10 |
| `irc-v2-sim-s1033` | 10 / 15 | 5 | 0 | 0 | 5 | 5.25 | 1:54.80 | 1:56.10 |
| `irc-v2-sim-s1034` | 13 / 15 | 0 | 2 | 0 | 7 | 4.46 | 1:54.50 | 1:56.20 |
| `irc-v2-sim-s1035` | 4 / 15 | 10 | 1 | 0 | 13 | 7.08 | 1:54.90 | 1:56.20 |
| `irc-v2-sim-s1036` | 8 / 15 | 6 | 1 | 0 | 9 | 7.72 | 1:54.80 | 1:56.40 |
| `irc-v2-sim-s1037` | 5 / 15 | 8 | 2 | 0 | 4 | 6.26 | 1:54.70 | 1:56.10 |
| `irc-v2-sim-s1038` | 8 / 15 | 5 | 2 | 0 | 8 | 4.8 | 1:55.30 | 1:56.40 |
| `irc-v2-sim-s1039` | 9 / 15 | 4 | 2 | 0 | 12 | 6.24 | 1:55.30 | 1:56.70 |

## Where the swarm drops out (sim-v2, all held-out heats)

| Node | DNF here: water | energy | cap | Median split of bots that completed it (s) |
|---|---|---|---|---|
| N0 Start pen and approach | 0 | 0 | 0 | 11.4 |
| N1 Runway lot in the squall | 0 | 0 | 0 | 22.1 |
| N2 Plane crossing (on foot) | 0 | 28 | 0 | 16.8 |
| N3 West return leg | 0 | 20 | 0 | 39.8 |
| N4 Gust shore (former reef bay) | 230 | 4 | 0 | 10.4 |
| N5 Hill tunnels | 0 | 28 | 0 | 15.7 |
| N6 Finish (summit) | 0 | 0 | 0 | 0.0 |

## Read before using these numbers

- The sim (`runner/squall_sim.py`) is a 2-D kinematic model of 15 bots at the Clawblox humanoid's 5.5 studs/s; it is not the Clawblox physics.
- The live heat uses the same course and boundary numbers in the real world, but its bots also met engine problems the sim does not have (bots pinned on the plane-zone car, and collision launches in a crowd). Read the live result as a check of the world, not of the 40-70% target.
- Energy units, drain rates and the gust strength are design choices, tuned on seeds 0-11 only.
